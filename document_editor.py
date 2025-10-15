"""
구조화된 문서 편집 모듈
문장 단위 편집 (삽입/삭제/수정) 기능 제공
"""
from typing import Dict, Any, List, Optional, Union
import copy


class StructuredDocumentEditor:
    """구조화된 문서 편집기"""

    def __init__(self, structured_doc: Dict[str, Any]):
        """
        Args:
            structured_doc: structure_document()로 생성된 구조화 문서
        """
        self.doc = copy.deepcopy(structured_doc)

    def delete_sentences(self, sentence_ids: List[str]) -> Dict[str, Any]:
        """
        문장 삭제

        Args:
            sentence_ids: 삭제할 문장 ID 리스트

        Returns:
            수정된 문서
        """
        sentences = self.doc['content']['sentences']

        # 삭제할 문장 필터링
        remaining_sentences = [
            sent for sent in sentences
            if sent['sentence_id'] not in sentence_ids
        ]

        self.doc['content']['sentences'] = remaining_sentences
        return self.doc

    def insert_sentence(
        self,
        new_sentence: str,
        position: Union[str, int],
        placement: str = "after"
    ) -> Dict[str, Any]:
        """
        문장 삽입

        Args:
            new_sentence: 삽입할 문장 텍스트
            position: 기준 문장 ID 또는 라인 번호
            placement: "before", "after", "replace"

        Returns:
            수정된 문서
        """
        sentences = self.doc['content']['sentences']

        # 위치 찾기
        insert_idx = None
        if isinstance(position, str):
            # 문장 ID로 찾기
            for idx, sent in enumerate(sentences):
                if sent['sentence_id'] == position:
                    insert_idx = idx
                    break
        else:
            # 인덱스로 찾기
            insert_idx = position

        if insert_idx is None:
            raise ValueError(f"Position {position} not found")

        # 새 문장 객체 생성
        new_sent_obj = {
            "sentence_id": f"inserted_{len(sentences)}",
            "text": new_sentence,
            "start_char": 0,
            "end_char": len(new_sentence)
        }

        # 삽입
        if placement == "before":
            sentences.insert(insert_idx, new_sent_obj)
        elif placement == "after":
            sentences.insert(insert_idx + 1, new_sent_obj)
        elif placement == "replace":
            sentences[insert_idx] = new_sent_obj
        else:
            raise ValueError(f"Invalid placement: {placement}")

        self.doc['content']['sentences'] = sentences
        return self.doc

    def update_sentence(self, sentence_id: str, new_text: str) -> Dict[str, Any]:
        """
        문장 수정

        Args:
            sentence_id: 수정할 문장 ID
            new_text: 새 문장 텍스트

        Returns:
            수정된 문서
        """
        sentences = self.doc['content']['sentences']

        for sent in sentences:
            if sent['sentence_id'] == sentence_id:
                sent['text'] = new_text
                sent['end_char'] = sent['start_char'] + len(new_text)
                break

        self.doc['content']['sentences'] = sentences
        return self.doc

    def get_document(self) -> Dict[str, Any]:
        """수정된 문서 반환"""
        return self.doc


def structured_to_original(structured_doc: Dict[str, Any]) -> str:
    """
    구조화된 문서를 원본 텍스트로 복원

    Args:
        structured_doc: 구조화된 문서

    Returns:
        복원된 텍스트
    """
    sentences = structured_doc['content']['sentences']
    return ' '.join(sent['text'] for sent in sentences)


def delete_sentences_from_doc(
    structured_doc: Dict[str, Any],
    sentence_ids: List[str]
) -> Dict[str, Any]:
    """
    문서에서 문장 삭제 (헬퍼 함수)

    Args:
        structured_doc: 구조화된 문서
        sentence_ids: 삭제할 문장 ID 리스트

    Returns:
        수정된 문서
    """
    editor = StructuredDocumentEditor(structured_doc)
    return editor.delete_sentences(sentence_ids)


def insert_sentence_to_doc(
    structured_doc: Dict[str, Any],
    new_sentence: str,
    position: Union[str, int],
    placement: str = "after"
) -> Dict[str, Any]:
    """
    문서에 문장 삽입 (헬퍼 함수)

    Args:
        structured_doc: 구조화된 문서
        new_sentence: 삽입할 문장
        position: 기준 위치
        placement: 배치 방법

    Returns:
        수정된 문서
    """
    editor = StructuredDocumentEditor(structured_doc)
    return editor.insert_sentence(new_sentence, position, placement)


def update_sentence_in_doc(
    structured_doc: Dict[str, Any],
    sentence_id: str,
    new_text: str
) -> Dict[str, Any]:
    """
    문서의 문장 수정 (헬퍼 함수)

    Args:
        structured_doc: 구조화된 문서
        sentence_id: 수정할 문장 ID
        new_text: 새 텍스트

    Returns:
        수정된 문서
    """
    editor = StructuredDocumentEditor(structured_doc)
    return editor.update_sentence(sentence_id, new_text)
