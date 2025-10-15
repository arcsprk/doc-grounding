"""
문서 구조화 및 매핑 생성 도구
- 텍스트 문서를 구조화된 JSON 형식으로 변환
- LLM을 사용하여 요약문과 원본 문서 간의 매핑 생성

개선 버전 (v2):
- 정확한 여러 줄 문장 처리
- 문자 위치 기반 라인 매핑
- Fuzzy 검색 지원
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
import nltk
from nltk.tokenize import sent_tokenize
from difflib import SequenceMatcher

# NLTK 데이터 다운로드 (최초 1회)
# nltk.download('punkt')


def fuzzy_search(text: str, pattern: str, start_pos: int = 0) -> int:
    """
    Fuzzy 문자열 검색 - 공백/줄바꿈 차이를 무시하고 문장 위치 찾기

    Args:
        text: 검색 대상 텍스트
        pattern: 찾을 패턴 (문장)
        start_pos: 검색 시작 위치

    Returns:
        찾은 위치 (못 찾으면 -1)
    """
    # 공백 정규화
    pattern_normalized = ' '.join(pattern.split())

    # 슬라이딩 윈도우로 검색
    pattern_len = len(pattern)
    search_window = pattern_len + 50  # 여유 공간

    for i in range(start_pos, len(text) - pattern_len + 1):
        window = text[i:i + search_window]
        window_normalized = ' '.join(window.split())

        # 유사도 계산
        similarity = SequenceMatcher(None, pattern_normalized, window_normalized).ratio()

        if similarity > 0.9:  # 90% 이상 유사
            return i

    return -1


def build_char_to_line_map(lines_text: List[str]) -> Tuple[Dict[int, int], List[Dict[str, Any]]]:
    """
    문자 위치 → 라인 번호 매핑 테이블 생성

    Args:
        lines_text: 라인 텍스트 리스트

    Returns:
        (char_to_line_map, line_data)
        - char_to_line_map: {문자위치: 라인번호}
        - line_data: 라인 정보 리스트
    """
    char_to_line_map = {}
    line_data = []
    current_char_pos = 0

    for line_num, line_text in enumerate(lines_text, 1):
        line_start = current_char_pos
        line_end = current_char_pos + len(line_text)

        # 이 라인의 각 문자 위치 기록
        for char_pos in range(line_start, line_end):
            char_to_line_map[char_pos] = line_num

        line_data.append({
            "line_num": line_num,
            "text": line_text,
            "start": line_start,
            "end": line_end,
            "sentence_ids": []
        })

        current_char_pos = line_end + 1  # +1 for '\n'

    return char_to_line_map, line_data


def structure_document(
    text: str,
    doc_id: str,
    title: str,
    doc_type: str = "source",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    텍스트 문서를 구조화된 JSON 형식으로 변환 (개선 버전 v2)

    알고리즘:
    1. 문자 위치 → 라인 번호 매핑 테이블 생성
    2. NLTK로 전체 텍스트의 문장 분리
    3. 각 문장의 원본 텍스트 내 위치 찾기 (Fuzzy 검색 포함)
    4. 문장이 걸친 라인들을 정확히 계산
    5. 라인별 sentence_ids 업데이트

    Args:
        text: 원본 텍스트 (줄바꿈 포함)
        doc_id: 문서 고유 ID (예: "src_001", "gen_001")
        title: 문서 제목
        doc_type: 문서 타입 ("source" 또는 "generated")
        metadata: 추가 메타데이터 (선택사항)

    Returns:
        구조화된 문서 딕셔너리
    """
    # === 1단계: 문자 위치 → 라인 번호 매핑 테이블 생성 ===
    lines_text = text.split('\n')
    char_to_line_map, line_data = build_char_to_line_map(lines_text)

    # === 2단계: 전체 텍스트의 문장 분리 (NLTK) ===
    try:
        sentences_texts = sent_tokenize(text)
    except Exception as e:
        print(f"⚠️ NLTK 문장 분리 실패, 정규식 사용: {e}")
        # NLTK 실패 시 간단한 정규식 사용
        sentences_texts = re.split(r'(?<=[.!?])\s+', text)

    sentence_data = []
    search_pos = 0

    # === 3단계: 각 문장의 위치 찾기 및 라인 매핑 ===
    for sent_idx, sent_text in enumerate(sentences_texts):
        sent_text = sent_text.strip()
        if not sent_text:
            continue

        # 원본 텍스트에서 문장 위치 찾기
        sent_start = text.find(sent_text, search_pos)

        if sent_start == -1:
            # 공백/줄바꿈 차이로 못 찾으면 Fuzzy 검색
            sent_start = fuzzy_search(text, sent_text, search_pos)

        if sent_start == -1:
            # 그래도 못 찾으면 스킵 (매우 드문 경우)
            print(f"⚠️ 문장을 찾을 수 없음: {sent_text[:50]}...")
            continue

        sent_end = sent_start + len(sent_text)

        # === 4단계: 이 문장이 걸친 라인들 계산 ===
        covered_lines = set()
        for char_pos in range(sent_start, min(sent_end, len(text))):
            if char_pos in char_to_line_map:
                covered_lines.add(char_to_line_map[char_pos])

        sent_id = f"{doc_id}_s{sent_idx + 1}"
        covered_lines_list = sorted(list(covered_lines))

        # === 5단계: 라인별 sentence_ids 업데이트 ===
        for line_num in covered_lines_list:
            if 1 <= line_num <= len(line_data):
                line_data[line_num - 1]["sentence_ids"].append(sent_id)

        sentence_data.append({
            "id": sent_id,
            "text": sent_text,
            "lines": covered_lines_list,
            "doc_id": doc_id
        })

        search_pos = sent_end

    # === 결과 구조 생성 ===
    result = {
        "doc_id": doc_id,
        "metadata": {
            "title": title,
            "total_lines": len(line_data),
            "total_sentences": len(sentence_data),
            "algorithm_version": "v2",
            **(metadata or {})
        },
        "content": {
            "lines": line_data,
            "sentences": sentence_data
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