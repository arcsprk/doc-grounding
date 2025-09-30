"""
문서 매핑 생성 통합 도구
- Jinja2 템플릿을 사용하여 LLM 프롬프트 생성
- LLM API 호출 및 매핑 결과 파싱
"""

import json
from typing import Dict, List, Any, Optional
from jinja2 import Template
import anthropic  # 또는 openai 등 다른 LLM 라이브러리


# Jinja2 템플릿 정의
MAPPING_PROMPT_TEMPLATE = """
당신은 문서 분석 전문가입니다. 처리된 문서(요약문)와 원본 소스 문서들 간의 관계를 정확하게 매핑해야 합니다.

## 작업 개요
- **처리된 문서**: {{ structured_processed_doc.metadata.title }}
- **소스 문서 수**: {{ structured_source_docs|length }}개
- **매핑 방식**: 처리된 문서의 각 문장이 어느 소스 문서의 어떤 문장들을 참조/요약했는지 식별

## 소스 문서들

{% for source_doc in structured_source_docs %}
### 소스 문서 {{ loop.index }}: {{ source_doc.metadata.title }}
**문서 ID**: `{{ source_doc.doc_id }}`
**문장 목록**:
{% for sentence in source_doc.content.sentences %}
- `{{ sentence.id }}` (라인 {{ sentence.lines|join(', ') }}): {{ sentence.text }}
{% endfor %}

{% endfor %}

## 처리된 문서 (요약문)

**문서 ID**: `{{ structured_processed_doc.doc_id }}`
**제목**: {{ structured_processed_doc.metadata.title }}
**문장 목록**:
{% for sentence in structured_processed_doc.content.sentences %}
- `{{ sentence.id }}` (라인 {{ sentence.lines|join(', ') }}): {{ sentence.text }}
{% endfor %}

{% if existing_mappings %}
## 기존 매핑 정보 (참고용)

### 요약문 → 소스 문서 매핑
```json
{{ existing_mappings.summary_to_source | tojson(indent=2) }}
```

### 소스 문서 → 요약문 매핑
```json
{{ existing_mappings.source_to_summary | tojson(indent=2) }}
```

**주의**: 기존 매핑이 정확하지 않을 수 있습니다. 반드시 검증하고 수정하세요.
{% endif %}

## 매핑 규칙

1. **정확성**: 요약문의 각 문장이 실제로 참조하는 소스 문장들만 매핑
2. **완전성**: 모든 요약문 문장에 대해 매핑 제공 (매핑이 없으면 빈 배열)
3. **다중 참조**: 하나의 요약문 문장이 여러 소스 문장을 참조할 수 있음
4. **교차 문서**: 여러 소스 문서의 문장들을 통합한 경우 모두 포함
5. **양방향**: summary_to_source와 source_to_summary 모두 생성

## 출력 형식

다음 JSON 형식으로 매핑 정보를 반환하세요:

```json
{
  "summary_to_source": {
    "처리된문서_문장ID": ["소스문서_문장ID1", "소스문서_문장ID2", ...],
    ...
  },
  "source_to_summary": {
    "소스문서_문장ID": ["처리된문서_문장ID1", ...],
    ...
  }
}
```

## 분석 프로세스

1. 각 요약문 문장을 읽고 핵심 내용 파악
2. 해당 내용이 어느 소스 문서의 어떤 문장에서 유래했는지 식별
3. 의미적 유사성과 키워드 일치를 기준으로 매핑
4. 여러 문장이 통합된 경우 모두 포함
5. 양방향 매핑의 일관성 검증

---

이제 위 문서들을 분석하여 **완전하고 정확한 매핑 정보를 JSON 형식으로만** 출력하세요. 추가 설명 없이 JSON만 반환하세요.
"""


def generate_mapping_prompt(
    structured_source_docs: List[Dict[str, Any]],
    structured_processed_doc: Dict[str, Any],
    existing_mappings: Optional[Dict[str, Any]] = None
) -> str:
    """
    Jinja2 템플릿을 사용하여 매핑 생성 프롬프트 생성
    
    Args:
        structured_source_docs: 구조화된 소스 문서 리스트
        structured_processed_doc: 구조화된 처리 문서
        existing_mappings: 기존 매핑 정보 (선택사항)
    
    Returns:
        LLM에 전달할 프롬프트 문자열
    """
    template = Template(MAPPING_PROMPT_TEMPLATE)
    
    prompt = template.render(
        structured_source_docs=structured_source_docs,
        structured_processed_doc=structured_processed_doc,
        existing_mappings=existing_mappings
    )
    
    return prompt


def parse_mapping_response(response_text: str) -> Dict[str, Any]:
    """
    LLM 응답에서 JSON 매핑 정보 추출
    
    Args:
        response_text: LLM의 응답 텍스트
    
    Returns:
        파싱된 매핑 딕셔너리
    """
    # JSON 코드 블록에서 추출
    import re
    
    # ```json ... ``` 또는 ``` ... ``` 형식 찾기
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1)
    else:
        # 코드 블록이 없으면 전체 텍스트에서 JSON 찾기
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            raise ValueError("응답에서 JSON을 찾을 수 없습니다.")
    
    try:
        mappings = json.loads(json_str)
        return mappings
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}")


def generate_mappings_with_llm(
    structured_source_docs: List[Dict[str, Any]],
    structured_processed_doc: Dict[str, Any],
    api_key: str,
    existing_mappings: Optional[Dict[str, Any]] = None,
    model: str = "claude-3-5-sonnet-20241022"
) -> Dict[str, Any]:
    """
    LLM을 사용하여 문서 간 매핑 생성
    
    Args:
        structured_source_docs: 구조화된 소스 문서 리스트
        structured_processed_doc: 구조화된 처리 문서
        api_key: Anthropic API 키
        existing_mappings: 기존 매핑 정보 (선택사항)
        model: 사용할 모델명
    
    Returns:
        생성된 매핑 정보
    """
    # 프롬프트 생성
    prompt = generate_mapping_prompt(
        structured_source_docs,
        structured_processed_doc,
        existing_mappings
    )
    
    # Anthropic API 호출
    client = anthropic.Anthropic(api_key=api_key)
    
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = message.content[0].text
    
    # 응답 파싱
    mappings = parse_mapping_response(response_text)
    
    return mappings


def validate_mappings(
    mappings: Dict[str, Any],
    structured_source_docs: List[Dict[str, Any]],
    structured_processed_doc: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    매핑의 유효성 검증
    
    Args:
        mappings: 검증할 매핑 정보
        structured_source_docs: 소스 문서 리스트
        structured_processed_doc: 처리 문서
    
    Returns:
        검증 결과 (errors와 warnings)
    """
    errors = []
    warnings = []
    
    # 모든 문장 ID 수집
    source_sentence_ids = set()
    for doc in structured_source_docs:
        for sent in doc['content']['sentences']:
            source_sentence_ids.add(sent['id'])
    
    processed_sentence_ids = set(
        s['id'] for s in structured_processed_doc['content']['sentences']
    )
    
    # summary_to_source 검증
    for proc_id, source_ids in mappings.get('summary_to_source', {}).items():
        if proc_id not in processed_sentence_ids:
            errors.append(f"존재하지 않는 처리 문서 문장 ID: {proc_id}")
        
        for source_id in source_ids:
            if source_id not in source_sentence_ids:
                errors.append(f"존재하지 않는 소스 문장 ID: {source_id}")
    
    # source_to_summary 검증
    for source_id, proc_ids in mappings.get('source_to_summary', {}).items():
        if source_id not in source_sentence_ids:
            errors.append(f"존재하지 않는 소스 문장 ID: {source_id}")
        
        for proc_id in proc_ids:
            if proc_id not in processed_sentence_ids:
                errors.append(f"존재하지 않는 처리 문서 문장 ID: {proc_id}")
    
    # 양방향 일관성 검증
    for proc_id, source_ids in mappings.get('summary_to_source', {}).items():
        for source_id in source_ids:
            reverse_mapping = mappings.get('source_to_summary', {}).get(source_id, [])
            if proc_id not in reverse_mapping:
                warnings.append(
                    f"양방향 불일치: {proc_id} → {source_id}는 있지만 역방향 매핑 없음"
                )
    
    return {
        "errors": errors,
        "warnings": warnings
    }


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    # 예시 데이터 (이전 structure_document 함수로 생성된 것 가정)
    source_docs = [
        {
            "doc_id": "src_001",
            "metadata": {"title": "AI 윤리 가이드라인"},
            "content": {
                "sentences": [
                    {"id": "src_001_s1", "text": "AI 윤리 원칙의 중요성", "lines": [1]},
                    {"id": "src_001_s2", "text": "투명성과 공정성이 필수적입니다.", "lines": [2]}
                ]
            }
        }
    ]
    
    processed_doc = {
        "doc_id": "proc_001",
        "metadata": {"title": "AI 윤리 요약"},
        "content": {
            "sentences": [
                {"id": "proc_s1", "text": "AI 윤리와 투명성이 중요하다.", "lines": [1]}
            ]
        }
    }
    
    # 1. 프롬프트 생성
    prompt = generate_mapping_prompt(source_docs, processed_doc)
    print("생성된 프롬프트:")
    print(prompt[:500] + "...\n")
    
    # 2. LLM으로 매핑 생성 (API 키 필요)
    # mappings = generate_mappings_with_llm(
    #     source_docs,
    #     processed_doc,
    #     api_key="your-api-key"
    # )
    
    # 3. 수동으로 작성한 매핑 예시
    mappings = {
        "summary_to_source": {
            "proc_s1": ["src_001_s1", "src_001_s2"]
        },
        "source_to_summary": {
            "src_001_s1": ["proc_s1"],
            "src_001_s2": ["proc_s1"]
        }
    }
    
    # 4. 매핑 검증
    validation_result = validate_mappings(mappings, source_docs, processed_doc)
    
    print("✅ 매핑 검증 완료!")
    if validation_result['errors']:
        print(f"❌ 오류: {len(validation_result['errors'])}개")
        for error in validation_result['errors']:
            print(f"  - {error}")
    else:
        print("  오류 없음")
    
    if validation_result['warnings']:
        print(f"⚠️  경고: {len(validation_result['warnings'])}개")
        for warning in validation_result['warnings']:
            print(f"  - {warning}")
    else:
        print("  경고 없음")
    
    # 5. 전체 데이터 구조에 매핑 추가
    full_data = {
        "source_documents": source_docs,
        "processed_document": processed_doc,
        "mappings": mappings
    }
    
    print("\n✅ 최종 데이터 구조:")
    print(json.dumps(full_data, ensure_ascii=False, indent=2))


# ============================================================================
# OpenAI 사용 버전 (선택)
# ============================================================================

def generate_mappings_with_openai(
    structured_source_docs: List[Dict[str, Any]],
    structured_processed_doc: Dict[str, Any],
    api_key: str,
    existing_mappings: Optional[Dict[str, Any]] = None,
    model: str = "gpt-4"
) -> Dict[str, Any]:
    """
    OpenAI를 사용하여 문서 간 매핑 생성
    """
    import openai
    
    # 프롬프트 생성
    prompt = generate_mapping_prompt(
        structured_source_docs,
        structured_processed_doc,
        existing_mappings
    )
    
    # OpenAI API 호출
    openai.api_key = api_key
    
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 문서 분석 전문가입니다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    
    response_text = response.choices[0].message.content
    
    # 응답 파싱
    mappings = parse_mapping_response(response_text)
    
    return mappings


# ============================================================================
# 배치 처리 유틸리티
# ============================================================================

def update_mappings_batch(
    data_file: str,
    output_file: str,
    api_key: str,
    force_regenerate: bool = False
):
    """
    여러 문서의 매핑을 일괄 생성/업데이트
    
    Args:
        data_file: 입력 JSON 파일 경로
        output_file: 출력 JSON 파일 경로
        api_key: LLM API 키
        force_regenerate: 기존 매핑이 있어도 재생성할지 여부
    """
    # 데이터 로드
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    source_docs = data.get('source_documents', [])
    processed_doc = data.get('processed_document')
    existing_mappings = data.get('mappings') if not force_regenerate else None
    
    print(f"📄 문서 로드 완료:")
    print(f"  - 소스 문서: {len(source_docs)}개")
    print(f"  - 처리 문서: {processed_doc['metadata']['title']}")
    
    # 매핑 생성
    print("\n🔄 매핑 생성 중...")
    try:
        mappings = generate_mappings_with_llm(
            source_docs,
            processed_doc,
            api_key,
            existing_mappings
        )
        print("✅ 매핑 생성 완료!")
    except Exception as e:
        print(f"❌ 매핑 생성 실패: {e}")
        return
    
    # 검증
    print("\n🔍 매핑 검증 중...")
    validation = validate_mappings(mappings, source_docs, processed_doc)
    
    if validation['errors']:
        print(f"❌ 검증 실패: {len(validation['errors'])}개 오류")
        for error in validation['errors']:
            print(f"  - {error}")
        return
    
    if validation['warnings']:
        print(f"⚠️  {len(validation['warnings'])}개 경고:")
        for warning in validation['warnings'][:5]:
            print(f"  - {warning}")
        if len(validation['warnings']) > 5:
            print(f"  ... 외 {len(validation['warnings']) - 5}개")
    
    # 결과 저장
    data['mappings'] = mappings
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 결과 저장 완료: {output_file}")
    
    # 통계 출력
    summary_count = len(mappings.get('summary_to_source', {}))
    source_count = len(mappings.get('source_to_summary', {}))
    print(f"\n📊 매핑 통계:")
    print(f"  - 요약문 문장: {summary_count}개")
    print(f"  - 매핑된 소스 문장: {source_count}개")


# ============================================================================
# CLI 인터페이스
# ============================================================================

if __name__ == "__main__" and len(__import__('sys').argv) > 1:
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='문서 매핑 생성 도구')
    parser.add_argument('input', help='입력 JSON 파일')
    parser.add_argument('output', help='출력 JSON 파일')
    parser.add_argument('--api-key', required=True, help='LLM API 키')
    parser.add_argument('--force', action='store_true', help='기존 매핑 무시하고 재생성')
    parser.add_argument('--model', default='claude-3-5-sonnet-20241022', help='사용할 모델')
    
    args = parser.parse_args()
    
    update_mappings_batch(
        args.input,
        args.output,
        args.api_key,
        args.force
    )
