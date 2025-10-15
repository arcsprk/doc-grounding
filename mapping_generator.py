"""
문서 매핑 생성 통합 도구
- PromptManager를 사용하여 YAML 기반 LLM 프롬프트 생성
- LLM API 호출 및 매핑 결과 파싱
"""

import json
from typing import Dict, List, Any, Optional
import anthropic  # Anthropic SDK


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


def convert_mapping_to_array(
    mappings: Dict[str, Any],
    source_documents: List[Dict[str, Any]],
    processed_document: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    generated_doc_to_source_doc 형식의 매핑을 mappings 배열로 변환

    Args:
        mappings: generated_doc_to_source_doc, source_doc_to_generated_doc 포함한 매핑 딕셔너리
        source_documents: 소스 문서 리스트
        processed_document: 생성된 문서

    Returns:
        mappings 배열 (각 항목: source_sentence, target_sentence, type, confidence 등)
    """
    result = []

    # 문장 ID → 문장 텍스트 매핑 생성
    source_sentences = {}
    for doc in source_documents:
        for sent in doc.get('content', {}).get('sentences', []):
            source_sentences[sent['id']] = sent['text']

    target_sentences = {}
    for sent in processed_document.get('content', {}).get('sentences', []):
        target_sentences[sent['id']] = sent['text']

    # generated_doc_to_source_doc를 mappings 배열로 변환
    generated_to_source = mappings.get('generated_doc_to_source_doc', {})
    for target_id, source_ids in generated_to_source.items():
        target_text = target_sentences.get(target_id, '')

        for source_id in source_ids:
            source_text = source_sentences.get(source_id, '')

            if source_text and target_text:
                result.append({
                    'source_id': source_id,
                    'target_id': target_id,
                    'source_sentence': source_text,
                    'target_sentence': target_text,
                    'type': 'summary',
                    'confidence': 85  # 기본값
                })

    return result


def generate_mappings_with_anthropic(
    source_documents: List[Dict[str, Any]],
    processed_document: Dict[str, Any],
    api_key: str,
    existing_mappings: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    processing_type: str = "generic",
    original_texts: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Anthropic SDK를 사용하여 문서 간 매핑 생성

    Args:
        source_documents: 소스 문서 리스트
        processed_document: 처리된 문서
        api_key: Anthropic API 키
        existing_mappings: 기존 매핑 (선택)
        model: 사용할 모델 (기본: claude-3-5-sonnet-20241022)
        processing_type: 처리 유형 (summary, translation, paraphrase 등)
        original_texts: 원본 텍스트 딕셔너리 (선택)

    Returns:
        매핑 정보 딕셔너리
    """
    # 기본 모델 설정
    if model is None:
        model = "claude-3-5-sonnet-20241022"

    # PromptManager를 사용하여 YAML 템플릿 렌더링
    from app.core.prompts.prompt_manager import get_prompt_manager

    prompt_manager = get_prompt_manager()

    # 문서 구조화된 데이터 준비 (Jinja2 템플릿 변수)
    template_variables = {
        'structured_source_docs': source_documents,
        'structured_generated_doc': processed_document,
        'existing_mappings': existing_mappings
    }

    # YAML 템플릿 렌더링
    prompt = prompt_manager.render(
        yaml_file='mapping_prompts.yaml',
        task_id='document_mapping_generation',
        variables=template_variables
    )

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text
    mappings = parse_mapping_response(response_text)

    return mappings


def generate_mappings_with_requests(
    structured_source_docs: List[Dict[str, Any]],
    structured_processed_doc: Dict[str, Any],
    api_key: str,
    existing_mappings: Optional[Dict[str, Any]] = None,
    model: str = "claude-3-5-sonnet-20241022",
    provider: str = "anthropic",
    processing_type: str = "generic",
    original_texts: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    HTTP requests를 사용하여 문서 간 매핑 생성 (SDK 없이)

    Args:
        structured_source_docs: 구조화된 소스 문서 리스트
        structured_processed_doc: 구조화된 처리 문서
        api_key: API 키
        existing_mappings: 기존 매핑 정보
        model: 모델명
        provider: "anthropic" 또는 "openai"
        processing_type: 처리 유형 (선택)
        original_texts: 원본 텍스트 딕셔너리 (선택)

    Returns:
        생성된 매핑 정보
    """
    import requests

    # PromptManager를 사용하여 YAML 템플릿 렌더링
    from app.core.prompts.prompt_manager import get_prompt_manager

    prompt_manager = get_prompt_manager()

    # 문서 구조화된 데이터 준비 (Jinja2 템플릿 변수)
    template_variables = {
        'structured_source_docs': structured_source_docs,
        'structured_generated_doc': structured_processed_doc,
        'existing_mappings': existing_mappings
    }

    # YAML 템플릿 렌더링
    prompt = prompt_manager.render(
        yaml_file='mapping_prompts.yaml',
        task_id='document_mapping_generation',
        variables=template_variables
    )
    
    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        response_text = result["content"][0]["text"]
        
    elif provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or "gpt-4",
            "messages": [
                {"role": "system", "content": "당신은 문서 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        response_text = result["choices"][0]["message"]["content"]
        
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    mappings = parse_mapping_response(response_text)
    return mappings


# 하위 호환성을 위한 별칭
def generate_mappings_with_llm(
    structured_source_docs: List[Dict[str, Any]],
    structured_processed_doc: Dict[str, Any],
    api_key: str,
    existing_mappings: Optional[Dict[str, Any]] = None,
    model: str = "claude-3-5-sonnet-20241022"
) -> Dict[str, Any]:
    """
    LLM을 사용하여 문서 간 매핑 생성 (Anthropic 기본)
    """
    return generate_mappings_with_anthropic(
        structured_source_docs,
        structured_processed_doc,
        api_key,
        existing_mappings,
        model
    )


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
    
    # generated_doc_to_source_doc 검증
    for proc_id, source_ids in mappings.get('generated_doc_to_source_doc', {}).items():
        if proc_id not in processed_sentence_ids:
            errors.append(f"존재하지 않는 처리 문서 문장 ID: {proc_id}")
        
        for source_id in source_ids:
            if source_id not in source_sentence_ids:
                errors.append(f"존재하지 않는 소스 문장 ID: {source_id}")
    
    # source_doc_to_generated_doc 검증
    for source_id, proc_ids in mappings.get('source_doc_to_generated_doc', {}).items():
        if source_id not in source_sentence_ids:
            errors.append(f"존재하지 않는 소스 문장 ID: {source_id}")
        
        for proc_id in proc_ids:
            if proc_id not in processed_sentence_ids:
                errors.append(f"존재하지 않는 처리 문서 문장 ID: {proc_id}")
    
    # 양방향 일관성 검증
    for proc_id, source_ids in mappings.get('generated_doc_to_source_doc', {}).items():
        for source_id in source_ids:
            reverse_mapping = mappings.get('source_doc_to_generated_doc', {}).get(source_id, [])
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
        "doc_id": "gen_001",
        "metadata": {"title": "AI 윤리 요약"},
        "content": {
            "sentences": [
                {"id": "gen_001_s1", "text": "AI 윤리와 투명성이 중요하다.", "lines": [1]}
            ]
        }
    }

    # 1. 프롬프트 생성 (PromptManager 사용)
    from app.core.prompts.prompt_manager import get_prompt_manager

    prompt_manager = get_prompt_manager()
    template_variables = {
        'structured_source_docs': source_docs,
        'structured_generated_doc': processed_doc,
        'existing_mappings': None
    }
    prompt = prompt_manager.render(
        yaml_file='mapping_prompts.yaml',
        task_id='document_mapping_generation',
        variables=template_variables
    )
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
        "generated_doc_to_source_doc": {
            "gen_001_s1": ["src_001_s1", "src_001_s2"]
        },
        "source_doc_to_generated_doc": {
            "src_001_s1": ["gen_001_s1"],
            "src_001_s2": ["gen_001_s1"]
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
    source_documents: List[Dict[str, Any]],
    processed_document: Dict[str, Any],
    api_key: str,
    existing_mappings: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    processing_type: str = "generic",
    original_texts: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    OpenAI를 사용하여 문서 간 매핑 생성 (최신 SDK 사용)

    새로운 프롬프트 템플릿 시스템을 사용합니다.

    Args:
        source_documents: 소스 문서 리스트
        processed_document: 처리된 문서
        api_key: OpenAI API 키
        existing_mappings: 기존 매핑 (선택)
        model: 사용할 모델 (기본: gpt-4o-mini)
        processing_type: 처리 유형 (summary, translation, paraphrase 등)
        original_texts: 원본 텍스트 딕셔너리 (선택)

    Returns:
        매핑 정보 딕셔너리
    """
    from openai import OpenAI

    # 기본 모델 설정
    if model is None:
        model = "gpt-4o-mini"

    # PromptManager를 사용하여 YAML 템플릿 렌더링
    from app.core.prompts.prompt_manager import get_prompt_manager

    prompt_manager = get_prompt_manager()

    # 문서 구조화된 데이터 준비 (Jinja2 템플릿 변수)
    template_variables = {
        'structured_source_docs': source_documents,
        'structured_generated_doc': processed_document,
        'existing_mappings': None  # 기존 매핑이 있으면 전달 가능
    }

    # YAML 템플릿 렌더링
    prompt = prompt_manager.render(
        yaml_file='mapping_prompts.yaml',
        task_id='document_mapping_generation',
        variables=template_variables
    )

    # OpenAI API 호출 (최신 SDK)
    print(f"🤖 OpenAI API 호출 시작 - 모델: {model}")
    print(f"📝 프롬프트 길이: {len(prompt)} 문자")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 문서 분석 전문가입니다. 항상 정확한 JSON 형식으로 응답하세요."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=4096
    )

    response_text = response.choices[0].message.content
    print(f"✅ OpenAI 응답 받음 - 길이: {len(response_text)} 문자")
    print(f"📄 응답 미리보기: {response_text[:200]}...")

    # 응답 파싱
    mappings = parse_mapping_response(response_text)
    print(f"📊 파싱 완료 - generated_doc_to_source_doc: {len(mappings.get('generated_doc_to_source_doc', {}))} 항목")

    # generated_doc_to_source_doc 형식을 mappings 배열로 변환
    mappings_array = convert_mapping_to_array(mappings, source_documents, processed_document)
    print(f"📊 변환된 매핑 수: {len(mappings_array)}")

    # 최종 형식으로 반환
    return {
        "mappings": mappings_array,
        "generated_doc_to_source_doc": mappings.get('generated_doc_to_source_doc', {}),
        "source_doc_to_generated_doc": mappings.get('source_doc_to_generated_doc', {})
    }


# ============================================================================
# 배치 처리 유틸리티
# ============================================================================

def update_mapping_single(
    data_file: str,
    output_file: str,
    api_key: str,
    force_regenerate: bool = False,
    llm_provider: str = "anthropic",
    model: Optional[str] = None
) -> bool:
    """
    단일 문서의 매핑 생성/업데이트

    Args:
        data_file: 입력 JSON 파일 경로
        output_file: 출력 JSON 파일 경로
        api_key: LLM API 키
        force_regenerate: 기존 매핑이 있어도 재생성할지 여부
        llm_provider: LLM 제공자 (anthropic/openai)
        model: 사용할 모델명 (선택)

    Returns:
        성공 여부 (True/False)
    """
    # 데이터 로드
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    source_docs = data.get('source_documents', [])
    processed_doc = data.get('processed_document')
    existing_mappings = data.get('mappings') if not force_regenerate else None

    print(f"📄 문서 로드: {data_file}")
    print(f"  - 소스 문서: {len(source_docs)}개")
    print(f"  - 생성 문서: {processed_doc['metadata']['title']}")

    # 매핑 생성
    print("\n🔄 매핑 생성 중...")
    try:
        if llm_provider == "anthropic":
            mappings = generate_mappings_with_anthropic(
                source_docs,
                processed_doc,
                api_key,
                existing_mappings,
                model
            )
        elif llm_provider == "openai":
            mappings = generate_mappings_with_openai(
                source_docs,
                processed_doc,
                api_key,
                existing_mappings,
                model
            )
        else:
            raise ValueError(f"Unknown provider: {llm_provider}")

        print("✅ 매핑 생성 완료!")
    except Exception as e:
        print(f"❌ 매핑 생성 실패: {e}")
        return False

    # 검증
    print("\n🔍 매핑 검증 중...")
    validation = validate_mappings(mappings, source_docs, processed_doc)

    if validation['errors']:
        print(f"❌ 검증 실패: {len(validation['errors'])}개 오류")
        for error in validation['errors']:
            print(f"  - {error}")
        return False

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

    print(f"✅ 결과 저장: {output_file}")

    # 통계 출력
    generated_count = len(mappings.get('generated_doc_to_source_doc', {}))
    source_count = len(mappings.get('source_doc_to_generated_doc', {}))
    print(f"📊 매핑 통계: 생성 {generated_count}개, 소스 {source_count}개")

    return True


def update_mappings_batch(
    data_files: List[str],
    output_dir: str,
    api_key: str,
    force_regenerate: bool = False,
    llm_provider: str = "anthropic",
    model: Optional[str] = None,
    continue_on_error: bool = True
) -> Dict[str, Any]:
    """
    여러 문서의 매핑을 일괄 생성/업데이트 (진짜 배치 처리)

    Args:
        data_files: 입력 JSON 파일 경로 리스트
        output_dir: 출력 디렉토리 경로
        api_key: LLM API 키
        force_regenerate: 기존 매핑이 있어도 재생성할지 여부
        llm_provider: LLM 제공자 (anthropic/openai)
        model: 사용할 모델명 (선택)
        continue_on_error: 에러 발생 시 계속 진행 여부

    Returns:
        배치 처리 결과 통계
    """
    import os
    from pathlib import Path

    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"🚀 배치 매핑 생성 시작")
    print(f"{'='*70}")
    print(f"📁 입력 파일: {len(data_files)}개")
    print(f"📁 출력 디렉토리: {output_dir}")
    print(f"🤖 LLM 제공자: {llm_provider}")
    if model:
        print(f"🎯 모델: {model}")
    print(f"{'='*70}\n")

    # 결과 추적
    results = {
        'total': len(data_files),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }

    # 각 파일 처리
    for idx, data_file in enumerate(data_files, 1):
        print(f"\n{'─'*70}")
        print(f"[{idx}/{len(data_files)}] 처리 중: {os.path.basename(data_file)}")
        print(f"{'─'*70}")

        # 출력 파일명 생성
        input_name = Path(data_file).stem
        output_file = output_path / f"{input_name}_mapped.json"

        try:
            # 단일 문서 처리
            success = update_mapping_single(
                data_file=data_file,
                output_file=str(output_file),
                api_key=api_key,
                force_regenerate=force_regenerate,
                llm_provider=llm_provider,
                model=model
            )

            if success:
                results['success'] += 1
                results['details'].append({
                    'file': data_file,
                    'status': 'success',
                    'output': str(output_file)
                })
            else:
                results['failed'] += 1
                results['details'].append({
                    'file': data_file,
                    'status': 'failed',
                    'error': 'Validation failed'
                })

                if not continue_on_error:
                    print(f"\n❌ 에러로 인해 배치 처리 중단")
                    break

        except Exception as e:
            results['failed'] += 1
            results['details'].append({
                'file': data_file,
                'status': 'failed',
                'error': str(e)
            })
            print(f"❌ 예외 발생: {e}")

            if not continue_on_error:
                print(f"\n❌ 에러로 인해 배치 처리 중단")
                break

    # 최종 결과 요약
    print(f"\n{'='*70}")
    print(f"📊 배치 처리 완료")
    print(f"{'='*70}")
    print(f"✅ 성공: {results['success']}/{results['total']}")
    print(f"❌ 실패: {results['failed']}/{results['total']}")
    if results['skipped'] > 0:
        print(f"⏭️  스킵: {results['skipped']}/{results['total']}")
    print(f"{'='*70}\n")

    return results


# ============================================================================
# CLI 인터페이스
# ============================================================================

if __name__ == "__main__" and len(__import__('sys').argv) > 1:
    import sys
    import argparse
    import glob

    parser = argparse.ArgumentParser(
        description='문서 매핑 생성 도구 (단일/배치 처리)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 단일 파일 처리
  python mapping_generator.py input.json output.json --api-key YOUR_KEY

  # 배치 처리 (디렉토리)
  python mapping_generator.py "data/*.json" output_dir/ --api-key YOUR_KEY --batch

  # 배치 처리 (파일 리스트)
  python mapping_generator.py file1.json file2.json file3.json output_dir/ --api-key YOUR_KEY --batch
        """
    )

    parser.add_argument('input', nargs='+', help='입력 JSON 파일 (단일) 또는 파일들/패턴 (배치)')
    parser.add_argument('output', help='출력 JSON 파일 (단일) 또는 출력 디렉토리 (배치)')
    parser.add_argument('--api-key', required=True, help='LLM API 키')
    parser.add_argument('--provider', default='anthropic', choices=['anthropic', 'openai'],
                        help='LLM 제공자 (기본: anthropic)')
    parser.add_argument('--model', help='사용할 모델 (기본: provider별 기본 모델)')
    parser.add_argument('--force', action='store_true', help='기존 매핑 무시하고 재생성')
    parser.add_argument('--batch', action='store_true', help='배치 처리 모드')
    parser.add_argument('--continue-on-error', action='store_true', default=True,
                        help='배치 처리 시 에러 발생해도 계속 진행 (기본: True)')

    args = parser.parse_args()

    if args.batch:
        # 배치 처리 모드
        data_files = []

        # 입력 파일 리스트 확장 (glob 패턴 지원)
        for pattern in args.input:
            matches = glob.glob(pattern)
            if matches:
                data_files.extend(matches)
            else:
                data_files.append(pattern)  # glob 매치 없으면 원본 경로 사용

        if not data_files:
            print("❌ 에러: 입력 파일을 찾을 수 없습니다.")
            sys.exit(1)

        print(f"📁 발견된 파일: {len(data_files)}개")

        # 배치 처리 실행
        results = update_mappings_batch(
            data_files=data_files,
            output_dir=args.output,
            api_key=args.api_key,
            force_regenerate=args.force,
            llm_provider=args.provider,
            model=args.model,
            continue_on_error=args.continue_on_error
        )

        # 종료 코드 설정
        sys.exit(0 if results['failed'] == 0 else 1)

    else:
        # 단일 파일 처리 모드
        if len(args.input) > 1:
            print("❌ 에러: 단일 파일 모드에서는 입력 파일 1개만 지정하세요.")
            print("  (여러 파일 처리하려면 --batch 옵션 사용)")
            sys.exit(1)

        success = update_mapping_single(
            data_file=args.input[0],
            output_file=args.output,
            api_key=args.api_key,
            force_regenerate=args.force,
            llm_provider=args.provider,
            model=args.model
        )

        sys.exit(0 if success else 1)