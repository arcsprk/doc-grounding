"""Redis 캐시 관리 모듈"""
import json
import redis
from typing import Optional, Any
from datetime import timedelta
import sys
import os

# 부모 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings


class RedisCache:
    """Redis 캐시 클래스"""

    def __init__(self):
        """Redis 연결 초기화"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # 연결 테스트
            self.redis_client.ping()
            self.is_available = True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"Redis 연결 실패: {e}")
            self.is_available = False
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        if not self.is_available:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"캐시 조회 오류: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        expiration: Optional[int] = None,
    ) -> bool:
        """캐시에 값 저장"""
        if not self.is_available:
            return False

        try:
            serialized_value = json.dumps(value)
            if expiration:
                self.redis_client.setex(
                    key,
                    timedelta(seconds=expiration),
                    serialized_value,
                )
            else:
                self.redis_client.set(key, serialized_value)
            return True
        except Exception as e:
            print(f"캐시 저장 오류: {e}")
            return False

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if not self.is_available:
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"캐시 삭제 오류: {e}")
            return False

    def exists(self, key: str) -> bool:
        """캐시 키 존재 확인"""
        if not self.is_available:
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"캐시 확인 오류: {e}")
            return False

    def clear_all(self) -> bool:
        """모든 캐시 삭제 (주의!)"""
        if not self.is_available:
            return False

        try:
            self.redis_client.flushdb()
            return True
        except Exception as e:
            print(f"캐시 전체 삭제 오류: {e}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """캐시 만료 시간 조회 (초)"""
        if not self.is_available:
            return None

        try:
            ttl = self.redis_client.ttl(key)
            return ttl if ttl > 0 else None
        except Exception as e:
            print(f"TTL 조회 오류: {e}")
            return None


# 글로벌 캐시 인스턴스
cache = RedisCache()


def get_cache() -> RedisCache:
    """캐시 인스턴스 반환"""
    return cache
