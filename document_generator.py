"""
사용자 요구사항 기반 커스텀 문서 생성 모듈
"""

import os
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
import anthropic

from app.core.prompts.prompt_manager import get_prompt_manager


def generate_custom_document_with_openai(
    source_documents: List[Dict[str, Any]],
    user_requirements: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    OpenAI를 사용하여 커스텀 문서 생성

    Args:
        source_documents: 소스 문서 배열 (구조화된 형식)
        user_requirements: 사용자 요구사항 (자유 텍스트)
        api_key: OpenAI API 키
        model: 사용할 모델 (기본값: gpt-4o-mini)

    Returns:
        {
            "title": str,
            "content": str,
            "sentences": [
                {
                    "text": str,
                    "source_references": List[str]
                }
            ],
            "metadata": Dict[str, Any]
        }
    """
    # API 키 확인
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")

    # 기본 모델 설정
    if model is None:
        model = "gpt-4o-mini"

    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=api_key)

    # 프롬프트 생성
    prompt_manager = get_prompt_manager()

    template_variables = {
        'source_documents': source_documents,
        'user_requirements': user_requirements
    }

    prompt = prompt_manager.render(
        yaml_file='custom_generation_prompts.yaml',
        task_id='custom_document_generation',
        variables=template_variables
    )

    print(f"🤖 OpenAI 커스텀 문서 생성 시작 - 모델: {model}")
    print(f"📝 소스 문서 수: {len(source_documents)}")
    print(f"📋 요구사항 길이: {len(user_requirements)} 문자")
    print(f"📝 프롬프트 길이: {len(prompt)} 문자")

    # OpenAI API 호출
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "당신은 전문 문서 작성 전문가입니다. JSON 형식으로 정확하게 응답합니다."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.5,  # 창의성과 일관성의 균형
        max_tokens=4000,
        response_format={"type": "json_object"}  # JSON 모드 강제
    )

    response_text = response.choices[0].message.content.strip()

    print(f"✅ OpenAI 응답 받음 - 길이: {len(response_text)} 문자")

    # JSON 파싱
    try:
        result = json.loads(response_text)
        print(f"✅ JSON 파싱 성공")
        print(f"📄 생성된 문서 제목: {result.get('title', 'N/A')}")
        print(f"📊 생성된 문장 수: {len(result.get('sentences', []))}")

        # 검증
        if 'title' not in result or 'content' not in result or 'sentences' not in result:
            raise ValueError("필수 필드(title, content, sentences)가 누락되었습니다")

        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        print(f"응답 내용: {response_text[:500]}...")
        raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}")


def generate_custom_document_with_anthropic(
    source_documents: List[Dict[str, Any]],
    user_requirements: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Anthropic Claude를 사용하여 커스텀 문서 생성

    Args:
        source_documents: 소스 문서 배열
        user_requirements: 사용자 요구사항
        api_key: Anthropic API 키
        model: 사용할 모델 (기본값: claude-3-5-sonnet-20241022)

    Returns:
        생성 결과 딕셔너리
    """
    # API 키 확인
    if api_key is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다")

    # 기본 모델 설정
    if model is None:
        model = "claude-3-5-sonnet-20241022"

    # Anthropic 클라이언트 초기화
    client = anthropic.Anthropic(api_key=api_key)

    # 프롬프트 생성 (OpenAI와 동일한 템플릿 사용)
    prompt_manager = get_prompt_manager()

    template_variables = {
        'source_documents': source_documents,
        'user_requirements': user_requirements
    }

    prompt = prompt_manager.render(
        yaml_file='custom_generation_prompts.yaml',
        task_id='custom_document_generation',
        variables=template_variables
    )

    print(f"🤖 Anthropic 커스텀 문서 생성 시작 - 모델: {model}")
    print(f"📝 소스 문서 수: {len(source_documents)}")
    print(f"📋 요구사항 길이: {len(user_requirements)} 문자")

    # API 호출
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        temperature=0.5,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    response_text = response.content[0].text.strip()

    print(f"✅ Anthropic 응답 받음 - 길이: {len(response_text)} 문자")

    # JSON 파싱
    try:
        # Claude는 가끔 ```json ... ``` 형태로 감쌀 수 있으므로 제거
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()

        result = json.loads(response_text)
        print(f"✅ JSON 파싱 성공")
        print(f"📄 생성된 문서 제목: {result.get('title', 'N/A')}")
        print(f"📊 생성된 문장 수: {len(result.get('sentences', []))}")

        # 검증
        if 'title' not in result or 'content' not in result or 'sentences' not in result:
            raise ValueError("필수 필드가 누락되었습니다")

        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        print(f"응답 내용: {response_text[:500]}...")
        raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}")


def generate_custom_document(
    source_documents: List[Dict[str, Any]],
    user_requirements: str,
    llm_provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    LLM 제공자에 따라 커스텀 문서 생성

    Args:
        source_documents: 소스 문서 배열
        user_requirements: 사용자 요구사항
        llm_provider: LLM 제공자 (openai, anthropic)
        api_key: API 키
        model: 모델명

    Returns:
        생성 결과
    """
    if llm_provider == "openai":
        return generate_custom_document_with_openai(
            source_documents=source_documents,
            user_requirements=user_requirements,
            api_key=api_key,
            model=model
        )
    elif llm_provider == "anthropic":
        return generate_custom_document_with_anthropic(
            source_documents=source_documents,
            user_requirements=user_requirements,
            api_key=api_key,
            model=model
        )
    else:
        raise ValueError(f"지원하지 않는 LLM 제공자: {llm_provider}")
