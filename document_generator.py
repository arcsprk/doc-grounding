"""
사용자 요구사항 기반 커스텀 문서 생성 모듈
"""

import os
import json
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import requests
from openai import OpenAI
import anthropic

from app.core.prompts.prompt_manager import get_prompt_manager


def generate_custom_document(
    source_documents: Optional[List[str]] = None,
    structured_source_documents: Optional[List[Dict[str, Any]]] = None,
    user_requirements: str = "",
    yaml_file: str = "custom_generation_prompts.yaml",
    task_id: str = "custom_document_generation",
    output_format: str = "dict",
    model_override: Optional[str] = None  # REST API에서 모델 동적 지정용
) -> Union[Dict[str, Any], str]:
    """
    커스텀 문서 생성

    Args:
        source_documents: Plain text 문서 리스트 (선택)
        structured_source_documents: 구조화된 문서 리스트 (선택)
        user_requirements: 사용자 요구사항
        yaml_file: YAML 템플릿 파일명
        task_id: 사용할 템플릿 ID
        output_format: 반환 형식 ("dict" 또는 "text")
        model_override: 모델 오버라이드 (REST API용)

    Returns:
        생성된 문서 (dict 또는 text)

    Note:
        - source_documents와 structured_source_documents 중 하나는 반드시 필요
        - 둘 다 제공되면 모두 사용
        - model_override가 지정되면 YAML의 model 설정을 무시
    """
    # 1. 입력 검증
    if not source_documents and not structured_source_documents:
        raise ValueError("최소 하나의 문서 입력이 필요합니다 (source_documents 또는 structured_source_documents)")

    # 입력 타입 검증
    if source_documents and not isinstance(source_documents, list):
        raise TypeError("source_documents는 리스트 타입이어야 합니다")

    if structured_source_documents and not isinstance(structured_source_documents, list):
        raise TypeError("structured_source_documents는 리스트 타입이어야 합니다")

    # 2. YAML에서 템플릿과 LLM 설정 로드
    prompt_manager = get_prompt_manager()
    template_info = prompt_manager.get_template(yaml_file, task_id)

    llm_provider = template_info.get('llm_provider')
    # model_override가 있으면 사용, 없으면 YAML의 model 사용
    model = model_override if model_override else template_info.get('model')
    parameters = template_info.get('parameters', {})

    print(f"🤖 문서 생성 시작 - Provider: {llm_provider}, Model: {model}")

    # 문서 수 로깅
    if source_documents:
        print(f"📄 Plain text 문서: {len(source_documents)}개")
    if structured_source_documents:
        print(f"📊 구조화된 문서: {len(structured_source_documents)}개")

    # 3. 프롬프트 렌더링
    template_variables = {
        'source_documents': source_documents or [],
        'structured_source_documents': structured_source_documents or [],
        'user_requirements': user_requirements
    }

    prompt = prompt_manager.render(yaml_file, task_id, template_variables)

    print(f"📝 프롬프트 길이: {len(prompt)} 문자")

    # 4. Provider별 처리
    if llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")
        result = _call_openai(prompt, model, parameters, api_key)

    elif llm_provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다")
        result = _call_anthropic(prompt, model, parameters, api_key)

    elif llm_provider == "rest_api":
        result = _call_rest_endpoint(prompt, model, parameters)

    else:
        raise ValueError(f"지원하지 않는 LLM provider: {llm_provider}")

    # 5. 반환 형식 처리
    if output_format == "text":
        if isinstance(result, dict):
            return result.get("content", "")
        return str(result)

    return result


def _call_openai(
    prompt: str,
    model: str,
    parameters: Dict[str, Any],
    api_key: str
) -> Dict[str, Any]:
    """
    OpenAI API 호출 (내부용)

    Args:
        prompt: 프롬프트
        model: 모델명
        parameters: API 파라미터
        api_key: API 키

    Returns:
        파싱된 응답
    """
    client = OpenAI(api_key=api_key)

    print(f"🤖 OpenAI API 호출 시작 - 모델: {model}")

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
        **parameters  # temperature, max_tokens, response_format 등
    )

    response_text = response.choices[0].message.content.strip()

    print(f"✅ OpenAI 응답 받음 - 길이: {len(response_text)} 문자")

    # JSON 파싱
    try:
        result = json.loads(response_text)
        print(f"✅ JSON 파싱 성공")

        # 검증
        if 'title' not in result or 'content' not in result or 'sentences' not in result:
            raise ValueError("필수 필드(title, content, sentences)가 누락되었습니다")

        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        print(f"응답 내용: {response_text[:500]}...")
        raise ValueError(f"OpenAI 응답을 JSON으로 파싱할 수 없습니다: {e}")


def _call_anthropic(
    prompt: str,
    model: str,
    parameters: Dict[str, Any],
    api_key: str
) -> Dict[str, Any]:
    """
    Anthropic Claude API 호출 (내부용)

    Args:
        prompt: 프롬프트
        model: 모델명
        parameters: API 파라미터
        api_key: API 키

    Returns:
        파싱된 응답
    """
    client = anthropic.Anthropic(api_key=api_key)

    print(f"🤖 Anthropic API 호출 시작 - 모델: {model}")

    # Anthropic API 호출
    response = client.messages.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        **parameters  # temperature, max_tokens 등
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

        # 검증
        if 'title' not in result or 'content' not in result or 'sentences' not in result:
            raise ValueError("필수 필드가 누락되었습니다")

        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        print(f"응답 내용: {response_text[:500]}...")
        raise ValueError(f"Anthropic 응답을 JSON으로 파싱할 수 없습니다: {e}")


def _call_rest_endpoint(
    prompt: str,
    model: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    REST API 엔드포인트 호출

    Args:
        prompt: 프롬프트
        model: 모델명
        parameters: API 파라미터

    Returns:
        파싱된 응답
    """
    # Model catalog에서 설정 로드
    config = _get_rest_api_config(model)

    # API 키 가져오기
    api_key_env = config.get('api_key_env')
    api_key = os.getenv(api_key_env) if api_key_env else None

    print(f"🤖 REST API 호출 시작 - Model: {model}, Endpoint: {config.get('endpoint')}")

    # 헤더 준비 (환경변수 치환 지원)
    headers = {}
    for key, value in config.get('headers', {}).items():
        # ${VAR_NAME} 형식의 환경변수 치환
        if isinstance(value, str) and '${' in value:
            import re
            pattern = r'\$\{(\w+)\}'
            matches = re.findall(pattern, value)
            for var_name in matches:
                env_value = os.getenv(var_name, '')
                value = value.replace(f'${{{var_name}}}', env_value)
        headers[key] = value

    # API 키 추가
    if api_key:
        headers['Authorization'] = f"Bearer {api_key}"

    # 요청 형식에 따라 페이로드 구성
    request_format = config.get('request_format', 'openai')

    if request_format == 'openai':
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "전문 문서 작성 전문가"},
                {"role": "user", "content": prompt}
            ],
            **parameters
        }
    elif request_format == 'anthropic':
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **parameters
        }
    else:  # custom
        payload = _build_custom_payload(config, prompt, model, parameters)

    # API 호출
    try:
        response = requests.post(
            config['endpoint'],
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"❌ REST API 호출 실패: {e}")
        raise ValueError(f"REST API 호출 실패: {e}")

    print(f"✅ REST API 응답 받음 - 상태 코드: {response.status_code}")

    # 응답 파싱
    try:
        result = response.json()

        # OpenAI 형식 응답 처리
        if request_format == 'openai' and 'choices' in result:
            content = result['choices'][0]['message']['content']
            # response_format이 json_object인 경우 파싱
            if parameters.get('response_format', {}).get('type') == 'json_object':
                result = json.loads(content)
            else:
                result = {"content": content}

        # Anthropic 형식 응답 처리
        elif request_format == 'anthropic' and 'content' in result:
            content = result['content'][0]['text'] if isinstance(result['content'], list) else result['content']
            result = json.loads(content) if content.startswith('{') else {"content": content}

        # Custom 형식은 그대로 반환

        print(f"✅ 응답 파싱 성공")
        return result

    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ 응답 파싱 실패: {e}")
        raise ValueError(f"REST API 응답 파싱 실패: {e}")


def _get_rest_api_config(model: str) -> Dict[str, Any]:
    """
    Model catalog에서 REST API 설정 로드

    Args:
        model: 모델명

    Returns:
        REST API 설정
    """
    # 옵션 1: model_catalog.yaml 파일에서 로드
    catalog_path = Path(__file__).parent / "model_catalog.yaml"
    if catalog_path.exists():
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = yaml.safe_load(f)
                if 'rest_api_models' in catalog and model in catalog['rest_api_models']:
                    config = catalog['rest_api_models'][model]

                    # endpoint에 환경변수 치환 지원
                    endpoint = config.get('endpoint', '')
                    if '${' in endpoint:
                        import re
                        matches = re.findall(r'\$\{(\w+)\}', endpoint)
                        for var_name in matches:
                            env_value = os.getenv(var_name, '')
                            endpoint = endpoint.replace(f'${{{var_name}}}', env_value)
                        config['endpoint'] = endpoint

                    return config
        except Exception as e:
            print(f"⚠️ model_catalog.yaml 로드 실패: {e}")

    # 옵션 2: 환경변수에서 로드
    model_upper = model.upper().replace('-', '_')
    endpoint = os.getenv(f"REST_API_{model_upper}_ENDPOINT")

    if endpoint:
        return {
            'endpoint': endpoint,
            'api_key_env': f"REST_API_{model_upper}_API_KEY",
            'request_format': os.getenv(f"REST_API_{model_upper}_FORMAT", "openai"),
            'headers': {"Content-Type": "application/json"}
        }

    raise ValueError(f"REST API 모델 '{model}' 설정을 찾을 수 없습니다. model_catalog.yaml 또는 환경변수를 확인하세요.")


def _build_custom_payload(
    config: Dict[str, Any],
    prompt: str,
    model: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Custom 형식의 페이로드 구성

    Args:
        config: REST API 설정
        prompt: 프롬프트
        model: 모델명
        parameters: API 파라미터

    Returns:
        커스텀 페이로드
    """
    request_template = config.get('request_template', {})
    payload = {}

    for key, value in request_template.items():
        if value == "${MODEL}":
            payload[key] = model
        elif value == "${PROMPT}":
            payload[key] = prompt
        elif value == "${PARAMETERS}":
            payload[key] = parameters
        elif value == "${MESSAGES}":
            # OpenAI 스타일 메시지 형식
            payload[key] = [
                {"role": "system", "content": "전문 문서 작성 전문가"},
                {"role": "user", "content": prompt}
            ]
        else:
            payload[key] = value

    # 파라미터 병합 (템플릿에 없는 경우)
    if "${PARAMETERS}" not in request_template.values():
        payload.update(parameters)

    return payload
