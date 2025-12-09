"""데이터 캐싱 관리자"""

import pickle
import hashlib
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """데이터 캐싱 관리자"""
    
    def __init__(self, cache_dir: str = "./data/cache/", expiry_hours: int = 24):
        """
        캐시 관리자 초기화
        
        Args:
            cache_dir: 캐시 디렉토리 경로
            expiry_hours: 캐시 만료 시간 (시간)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.expiry_hours = expiry_hours
        logger.info(f"캐시 관리자 초기화: {cache_dir}, 만료 시간: {expiry_hours}시간")
    
    def _get_cache_key(self, key: str) -> str:
        """
        캐시 키 생성 (해시)
        
        Args:
            key: 원본 키
            
        Returns:
            해시된 키
        """
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """
        캐시 파일 경로 반환
        
        Args:
            key: 캐시 키
            
        Returns:
            캐시 파일 경로
        """
        cache_key = self._get_cache_key(key)
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _is_expired(self, cache_path: Path) -> bool:
        """
        캐시 만료 여부 확인
        
        Args:
            cache_path: 캐시 파일 경로
            
        Returns:
            만료 여부
        """
        if not cache_path.exists():
            return True
        
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_time = file_time + timedelta(hours=self.expiry_hours)
        return datetime.now() > expiry_time
    
    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 데이터 가져오기
        
        Args:
            key: 캐시 키
            
        Returns:
            캐시된 데이터 (없거나 만료된 경우 None)
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            logger.debug(f"캐시 미존재: {key}")
            return None
        
        if self._is_expired(cache_path):
            logger.debug(f"캐시 만료: {key}")
            cache_path.unlink()
            return None
        
        try:
            with open(cache_path, "rb") as f:
                data = pickle.load(f)
            logger.debug(f"캐시 히트: {key}")
            return data
        except Exception as e:
            logger.error(f"캐시 로드 실패: {key}, 에러: {e}")
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """
        캐시에 데이터 저장
        
        Args:
            key: 캐시 키
            value: 저장할 데이터
            
        Returns:
            저장 성공 여부
        """
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(value, f)
            logger.debug(f"캐시 저장: {key}")
            return True
        except Exception as e:
            logger.error(f"캐시 저장 실패: {key}, 에러: {e}")
            return False
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        캐시 삭제
        
        Args:
            pattern: 삭제할 패턴 (None이면 전체 삭제)
            
        Returns:
            삭제된 파일 수
        """
        deleted = 0
        if pattern:
            for cache_file in self.cache_dir.glob(f"*{pattern}*"):
                cache_file.unlink()
                deleted += 1
        else:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
                deleted += 1
        
        logger.info(f"캐시 삭제 완료: {deleted}개 파일")
        return deleted
    
    def get_cache_info(self) -> dict:
        """
        캐시 정보 반환
        
        Returns:
            캐시 통계 정보
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)
        expired_count = sum(1 for f in cache_files if self._is_expired(f))
        
        return {
            "total_files": len(cache_files),
            "total_size_mb": total_size / (1024 * 1024),
            "expired_files": expired_count,
            "cache_dir": str(self.cache_dir),
        }

