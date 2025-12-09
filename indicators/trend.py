"""트렌드 지표 모듈"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from indicators.base import BaseIndicator
from utils.logger import get_logger

logger = get_logger(__name__)


class EMA(BaseIndicator):
    """지수 이동 평균 (Exponential Moving Average)"""
    
    def __init__(self, period: int, source: str = "close", config: Dict[str, Any] = None):
        """
        EMA 초기화
        
        Args:
            period: 기간
            source: 소스 컬럼 (open, high, low, close)
            config: 추가 설정
        """
        config = config or {}
        config["period"] = period
        config["source"] = source
        super().__init__(f"EMA_{period}", config)
        self.period = period
        self.source = source
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """EMA 계산"""
        if self.source not in df.columns:
            raise ValueError(f"소스 컬럼 '{self.source}'이(가) 없습니다.")
        
        return df[self.source].ewm(span=self.period, adjust=False).mean()


class SMA(BaseIndicator):
    """단순 이동 평균 (Simple Moving Average)"""
    
    def __init__(self, period: int, source: str = "close", config: Dict[str, Any] = None):
        """
        SMA 초기화
        
        Args:
            period: 기간
            source: 소스 컬럼
            config: 추가 설정
        """
        config = config or {}
        config["period"] = period
        config["source"] = source
        super().__init__(f"SMA_{period}", config)
        self.period = period
        self.source = source
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """SMA 계산"""
        if self.source not in df.columns:
            raise ValueError(f"소스 컬럼 '{self.source}'이(가) 없습니다.")
        
        return df[self.source].rolling(window=self.period).mean()


class MACD(BaseIndicator):
    """MACD 지표"""
    
    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        source: str = "close",
        config: Dict[str, Any] = None,
    ):
        """
        MACD 초기화
        
        Args:
            fast: 빠른 EMA 기간
            slow: 느린 EMA 기간
            signal: 시그널 라인 기간
            source: 소스 컬럼
            config: 추가 설정
        """
        config = config or {}
        config["fast"] = fast
        config["slow"] = slow
        config["signal"] = signal
        config["source"] = source
        super().__init__(f"MACD_{fast}_{slow}_{signal}", config)
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.source = source
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """MACD 계산"""
        if self.source not in df.columns:
            raise ValueError(f"소스 컬럼 '{self.source}'이(가) 없습니다.")
        
        ema_fast = df[self.source].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df[self.source].ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        # MACD 라인 반환 (다른 값들은 별도로 접근 가능하도록 확장 가능)
        return macd_line
    
    def calculate_full(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        MACD 전체 계산 (MACD, Signal, Histogram)
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            MACD, Signal, Histogram이 포함된 데이터프레임
        """
        if self.source not in df.columns:
            raise ValueError(f"소스 컬럼 '{self.source}'이(가) 없습니다.")
        
        ema_fast = df[self.source].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df[self.source].ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            "MACD": macd_line,
            "Signal": signal_line,
            "Histogram": histogram,
        })

