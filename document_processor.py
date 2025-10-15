"""
문서 구조화 및 매핑 생성 도구
- 텍스트 문서를 구조화된 JSON 형식으로 변환
- LLM을 사용하여 요약문과 원본 문서 간의 매핑 생성
"""

import re
import json
from typing import List, Dict, Any, Optional
import nltk
from nltk.tokenize import sent_tokenize

# NLTK 데이터 다운로드 (최초 1회)
# nltk.download('punkt')


def structure_document(
    text: str,
    doc_id: str,
    title: str,
    doc_type: str = "source",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    텍스트 문서를 구조화된 JSON 형식으로 변환
    
    Args:
        text: 원본 텍스트 (줄바꿈 포함)
        doc_id: 문서 고유 ID (예: "src_001", "gen_001")
        title: 문서 제목
        doc_type: 문서 타입 ("source" 또는 "generated")
        metadata: 추가 메타데이터 (선택사항)
    
    Returns:
        구조화된 문서 딕셔너리
    """
    lines_text = text.split('\n')
    lines = []
    sentences = []
    sentence_counter = 1
    
    # 각 라인을 처리
    for line_num, line_content in enumerate(lines_text, start=1):
        line_sentences = []
        
        if not line_content.strip():
            # 빈 줄
            lines.append({
                "line_num": line_num,
                "text": line_content,
                "sentence_ids": []
            })
            continue
        
        # 문장 분리 (NLTK 사용)
        try:
            sents = sent_tokenize(line_content)
        except:
            # NLTK 실패 시 간단한 정규식 사용
            sents = re.split(r'(?<=[.!?])\s+', line_content)
        
        current_pos = 0
        for sent_text in sents:
            sent_text = sent_text.strip()
            if not sent_text:
                continue
            
            sentence_id = f"{doc_id}_s{sentence_counter}"
            
            # 라인 내에서 문장의 위치 찾기
            sent_start = line_content.find(sent_text, current_pos)
            if sent_start == -1:
                sent_start = current_pos
            
            # 문장이 이 라인에서 어디까지 포함되는지 확인
            sent_end = sent_start + len(sent_text)
            
            # 문장이 다음 라인으로 이어지는지 확인
            lines_covered = [line_num]
            remaining_text = sent_text
            
            # 현재 라인에 포함된 부분 계산
            if sent_end > len(line_content):
                # 문장이 다음 라인으로 이어짐 (여러 라인에 걸침)
                # 이 경우는 후처리에서 처리
                pass
            
            line_sentences.append(sentence_id)
            
            sentences.append({
                "id": sentence_id,
                "text": sent_text,
                "lines": lines_covered,
                "doc_id": doc_id
            })
            
            sentence_counter += 1
            current_pos = sent_end
        
        lines.append({
            "line_num": line_num,
            "text": line_content,
            "sentence_ids": line_sentences
        })
    
    # 여러 라인에 걸친 문장 후처리
    sentences = post_process_multiline_sentences(lines, sentences)
    
    # 결과 구조 생성
    result = {
        "doc_id": doc_id,
        "metadata": {
            "title": title,
            "total_lines": len(lines),
            **(metadata or {})
        },
        "content": {
            "lines": lines,
            "sentences": sentences
        }
    }
    
    return result


def post_process_multiline_sentences(
    lines: List[Dict],
    sentences: List[Dict]
) -> List[Dict]:
    """
    여러 라인에 걸친 문장을 감지하고 lines 정보를 업데이트
    
    Args:
        lines: 라인 정보 리스트
        sentences: 문장 정보 리스트
    
    Returns:
        업데이트된 문장 리스트
    """
    # 각 문장에 대해 실제로 어느 라인들에 걸쳐있는지 확인
    for sentence in sentences:
        sent_text = sentence['text']
        found_lines = []
        remaining_text = sent_text
        
        for line in lines:
            if not line['text'].strip():
                continue
            
            # 문장의 일부가 이 라인에 있는지 확인
            if any(word in line['text'] for word in sent_text.split()[:3]):
                # 문장 시작 부분이 이 라인에 있음
                found_lines.append(line['line_num'])
            elif found_lines and any(word in line['text'] for word in sent_text.split()[-3:]):
                # 이미 시작을 찾았고, 끝 부분이 이 라인에 있음
                found_lines.append(line['line_num'])
        
        if len(found_lines) > 1:
            sentence['lines'] = found_lines
    
    return sentences


def create_mapping_dict(
    source_docs: List[Dict[str, Any]],
    generated_doc: Dict[str, Any],
    mappings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    매핑 정보를 포함한 전체 데이터 구조 생성

    Args:
        source_docs: 소스 문서들의 리스트
        generated_doc: 생성된 문서 (요약문, 번역문 등)
        mappings: 기존 매핑 정보 (선택사항)

    Returns:
        전체 데이터 구조 (source_documents, generated_document, mappings)
    """
    result = {
        "source_documents": source_docs,
        "generated_document": generated_doc,
        "mappings": mappings or {
            "generated_doc_to_source_doc": {},
            "source_doc_to_generated_doc": {}
        }
    }

    return result


def export_to_json(data: Dict[str, Any], filepath: str, indent: int = 2):
    """JSON 파일로 저장"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def import_from_json(filepath: str) -> Dict[str, Any]:
    """JSON 파일에서 불러오기"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    # 예시 1: 소스 문서 구조화
    source_text = """AI 윤리 원칙의 중요성
인공지능 기술이 사회 전반에 미치는 영향이 커지면서 윤리적 고려가 필수적입니다. AI 시스템은 투명하고
공정해야 하며, 인간의 가치를 존중해야 합니다. 편향성 문제는 특히 중요한 이슈입니다.

데이터 프라이버시와 보안
개인정보 보호는 AI 개발의 핵심 요소입니다. 사용자 데이터는 적법하게 수집되어야 하며, 명확한 동의 절차가
필요합니다. 데이터 암호화와 익명화 기술을 활용해야 합니다."""

    source_doc = structure_document(
        text=source_text,
        doc_id="src_001",
        title="AI 윤리 가이드라인",
        doc_type="source",
        metadata={"doc_type": "정책 문서", "author": "AI 윤리위원회"}
    )
    
    # 예시 2: 요약문 구조화
    summary_text = """AI 윤리의 기본 방향
AI 기술의 사회적 영향이 증가하면서 윤리적 고려와 투명성, 공정성이 필수적입니다. 편향성 문제 해결이
핵심 과제로 부상했습니다.

프라이버시와 데이터 보안
개인정보 보호와 적법한 데이터 수집이 중요합니다. 암호화 기술 활용 및 접근 권한 관리와
정기 보안 감사가 필수입니다."""

    generated_doc = structure_document(
        text=summary_text,
        doc_id="gen_001",
        title="AI 윤리 및 보안 종합 요약",
        doc_type="generated",
        metadata={
            "processing_type": "summary",
            "source_doc_ids": ["src_001"]
        }
    )

    # 예시 3: 전체 구조 생성
    full_data = create_mapping_dict(
        source_docs=[source_doc],
        generated_doc=generated_doc
    )

    # JSON으로 저장
    export_to_json(full_data, "structured_documents.json")

    print("✅ 문서 구조화 완료!")
    print(f"소스 문서: {len(source_doc['content']['sentences'])}개 문장")
    print(f"생성된 문서: {len(generated_doc['content']['sentences'])}개 문장")
    print("\n구조화된 데이터 미리보기:")
    print(json.dumps(full_data, ensure_ascii=False, indent=2)[:500] + "...")