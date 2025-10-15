"""
Prompt Manager - YAML 기반 템플릿 관리 시스템

YAML 파일에서 프롬프트 템플릿을 로드하고 Jinja2로 렌더링합니다.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Template


class PromptManager:
    """
    프롬프트 템플릿 관리자

    YAML 파일에서 템플릿을 로드하고 Jinja2로 렌더링하는 단일 책임 클래스
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Args:
            templates_dir: YAML 템플릿 파일이 있는 디렉토리 경로
        """
        if templates_dir is None:
            # 기본 경로: 현재 파일과 같은 디렉토리
            templates_dir = Path(__file__).parent

        self.templates_dir = Path(templates_dir)
        self._templates_cache: Dict[str, Dict[str, Any]] = {}

    def load_templates(self, yaml_file: str) -> Dict[str, Dict[str, Any]]:
        """
        YAML 파일에서 템플릿 로드

        Args:
            yaml_file: YAML 파일명 (예: 'mapping_prompts.yaml')

        Returns:
            task_id를 키로 하는 템플릿 딕셔너리
        """
        # 캐시 확인
        if yaml_file in self._templates_cache:
            return self._templates_cache[yaml_file]

        yaml_path = self.templates_dir / yaml_file

        if not yaml_path.exists():
            raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # task_id를 키로 하는 딕셔너리로 변환
        templates = {}
        for template_info in data.get('templates', []):
            task_id = template_info.get('task_id')
            if task_id:
                templates[task_id] = template_info

        # 캐시 저장
        self._templates_cache[yaml_file] = templates

        return templates

    def get_template(self, yaml_file: str, task_id: str) -> Dict[str, Any]:
        """
        특정 task_id의 템플릿 정보 가져오기

        Args:
            yaml_file: YAML 파일명
            task_id: 템플릿 ID

        Returns:
            템플릿 정보 딕셔너리
        """
        templates = self.load_templates(yaml_file)

        if task_id not in templates:
            available_ids = list(templates.keys())
            raise KeyError(
                f"템플릿 ID '{task_id}'를 찾을 수 없습니다. "
                f"사용 가능한 ID: {available_ids}"
            )

        return templates[task_id]

    def render(
        self,
        yaml_file: str,
        task_id: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        템플릿 렌더링

        Args:
            yaml_file: YAML 파일명
            task_id: 템플릿 ID
            variables: Jinja2 템플릿에 전달할 변수들

        Returns:
            렌더링된 프롬프트 문자열
        """
        template_info = self.get_template(yaml_file, task_id)
        template_string = template_info.get('template', '')

        if not template_string:
            raise ValueError(f"템플릿 '{task_id}'의 내용이 비어있습니다")

        # Jinja2 템플릿 렌더링
        template = Template(template_string)
        rendered = template.render(**variables)

        return rendered

    def get_template_info(self, yaml_file: str, task_id: str) -> Dict[str, Any]:
        """
        템플릿 메타데이터 가져오기 (description, version 등)

        Args:
            yaml_file: YAML 파일명
            task_id: 템플릿 ID

        Returns:
            템플릿 메타데이터
        """
        template_info = self.get_template(yaml_file, task_id)
        return {
            'name': template_info.get('name'),
            'description': template_info.get('description'),
            'version': template_info.get('version'),
            'last_updated': template_info.get('last_updated'),
            'prompt_role': template_info.get('prompt_role'),
        }

    def list_templates(self, yaml_file: str) -> list:
        """
        YAML 파일의 모든 템플릿 목록 가져오기

        Args:
            yaml_file: YAML 파일명

        Returns:
            (task_id, name, description) 튜플 리스트
        """
        templates = self.load_templates(yaml_file)
        return [
            (
                task_id,
                info.get('name', ''),
                info.get('description', '')
            )
            for task_id, info in templates.items()
        ]

    def clear_cache(self):
        """캐시 초기화"""
        self._templates_cache.clear()


# 싱글톤 인스턴스
_default_manager = PromptManager()


def get_prompt_manager() -> PromptManager:
    """기본 PromptManager 인스턴스 가져오기"""
    return _default_manager
