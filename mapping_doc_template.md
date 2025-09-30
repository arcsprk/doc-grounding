{# 
문서 매핑 생성을 위한 LLM 프롬프트 템플릿
- structured_source_docs: 소스 문서 리스트
- structured_processed_doc: 처리된 문서 (요약문 등)
- existing_mappings: 기존 매핑 정보 (선택사항)
#}

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

## 예시

**요약문 문장**: "AI 윤리와 투명성이 중요하다."
**소스 문장 1**: "AI 윤리 원칙의 중요성"
**소스 문장 2**: "AI 시스템은 투명하고 공정해야 한다."

→ 매핑: `proc_s1 → [src_001_s1, src_001_s2]`

---

이제 위 문서들을 분석하여 **완전하고 정확한 매핑 정보를 JSON 형식으로만** 출력하세요. 추가 설명 없이 JSON만 반환하세요.
