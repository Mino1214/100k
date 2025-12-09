"""지표 베이스 클래스"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseIndicator(ABC):
    """지표 베이스 추상 클래스"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        지표 초기화
        
        Args:
            name: 지표 이름
            config: 지표 설정
        """
        self.name = name
        self.config = config
        self._cache: Optional[pd.Series] = None
    
    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        지표 계산 (추상 메서드)
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            계산된 지표 시리즈
        """
        pass
    
    def __call__(self, df: pd.DataFrame, use_cache: bool = True) -> pd.Series:
        """
        지표 계산 호출
        
        Args:
            df: OHLCV 데이터프레임
            use_cache: 캐시 사용 여부
            
        Returns:
            계산된 지표 시리즈
        """
        if use_cache and self._cache is not None and len(self._cache) == len(df):
            return self._cache
        
        result = self.calculate(df)
        self._cache = result
        return result
    
    def reset_cache(self):
        """캐시 초기화"""
        self._cache = None
    
    def get_config(self) -> Dict[str, Any]:
        """설정 반환"""
        return self.config

