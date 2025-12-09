"""거래량 지표 모듈"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from indicators.base import BaseIndicator
from indicators.trend import SMA, EMA
from utils.logger import get_logger

logger = get_logger(__name__)


class VolumeMA(BaseIndicator):
    """거래량 이동 평균"""
    
    def __init__(
        self,
        period: int = 20,
        type: str = "sma",
        config: Dict[str, Any] = None,
    ):
        """
        Volume MA 초기화
        
        Args:
            period: 기간
            type: 이동 평균 타입 (sma, ema)
            config: 추가 설정
        """
        config = config or {}
        config["period"] = period
        config["type"] = type
        super().__init__(f"VolumeMA_{period}_{type}", config)
        self.period = period
        self.type = type
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """Volume MA 계산"""
        if "volume" not in df.columns:
            raise ValueError("'volume' 컬럼이 없습니다.")
        
        if self.type == "sma":
            return df["volume"].rolling(window=self.period).mean()
        elif self.type == "ema":
            return df["volume"].ewm(span=self.period, adjust=False).mean()
        else:
            raise ValueError(f"알 수 없는 type: {self.type}")


class OBV(BaseIndicator):
    """On-Balance Volume"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        OBV 초기화
        
        Args:
            config: 추가 설정
        """
        config = config or {}
        super().__init__("OBV", config)
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """OBV 계산"""
        if "close" not in df.columns or "volume" not in df.columns:
            raise ValueError("'close' 또는 'volume' 컬럼이 없습니다.")
        
        price_change = df["close"].diff()
        obv = (df["volume"] * np.sign(price_change)).fillna(0).cumsum()
        return obv


class VWAP(BaseIndicator):
    """Volume Weighted Average Price"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        VWAP 초기화
        
        Args:
            config: 추가 설정
        """
        config = config or {}
        super().__init__("VWAP", config)
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """VWAP 계산 (일일 기준)"""
        if "close" not in df.columns or "volume" not in df.columns:
            raise ValueError("'close' 또는 'volume' 컬럼이 없습니다.")
        
        # 일일 VWAP 계산
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        pv = typical_price * df["volume"]
        
        # 날짜별로 그룹화하여 계산
        if isinstance(df.index, pd.DatetimeIndex):
            daily_vwap = pv.groupby(df.index.date).cumsum() / df["volume"].groupby(df.index.date).cumsum()
            return daily_vwap
        else:
            # 날짜 인덱스가 없으면 전체 기간 VWAP
            return pv.cumsum() / df["volume"].cumsum()

