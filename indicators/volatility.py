"""변동성 지표 모듈"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from indicators.base import BaseIndicator
from utils.logger import get_logger

logger = get_logger(__name__)


class ATR(BaseIndicator):
    """평균 진폭 범위 (Average True Range)"""
    
    def __init__(
        self,
        period: int = 14,
        method: str = "wilder",
        config: Dict[str, Any] = None,
    ):
        """
        ATR 초기화
        
        Args:
            period: 기간
            method: 계산 방법 (wilder, sma, ema)
            config: 추가 설정
        """
        config = config or {}
        config["period"] = period
        config["method"] = method
        super().__init__(f"ATR_{period}_{method}", config)
        self.period = period
        self.method = method
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """ATR 계산"""
        required_cols = ["high", "low", "close"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"필수 컬럼 '{col}'이(가) 없습니다.")
        
        # True Range 계산
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift(1))
        low_close = abs(df["low"] - df["close"].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # ATR 계산
        if self.method == "wilder":
            # Wilder's smoothing (EMA with alpha = 1/period)
            atr = true_range.ewm(alpha=1.0 / self.period, adjust=False).mean()
        elif self.method == "sma":
            atr = true_range.rolling(window=self.period).mean()
        elif self.method == "ema":
            atr = true_range.ewm(span=self.period, adjust=False).mean()
        else:
            raise ValueError(f"알 수 없는 method: {self.method}")
        
        return atr


class BollingerBands(BaseIndicator):
    """볼린저 밴드"""
    
    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        source: str = "close",
        config: Dict[str, Any] = None,
    ):
        """
        Bollinger Bands 초기화
        
        Args:
            period: 기간
            std_dev: 표준편차 배수
            source: 소스 컬럼
            config: 추가 설정
        """
        config = config or {}
        config["period"] = period
        config["std_dev"] = std_dev
        config["source"] = source
        super().__init__(f"BB_{period}_{std_dev}", config)
        self.period = period
        self.std_dev = std_dev
        self.source = source
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """Bollinger Bands 중간선 (SMA) 계산"""
        if self.source not in df.columns:
            raise ValueError(f"소스 컬럼 '{self.source}'이(가) 없습니다.")
        
        return df[self.source].rolling(window=self.period).mean()
    
    def calculate_full(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Bollinger Bands 전체 계산 (중간선, 상단선, 하단선)
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            중간선, 상단선, 하단선이 포함된 데이터프레임
        """
        if self.source not in df.columns:
            raise ValueError(f"소스 컬럼 '{self.source}'이(가) 없습니다.")
        
        sma = df[self.source].rolling(window=self.period).mean()
        std = df[self.source].rolling(window=self.period).std()
        
        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)
        
        return pd.DataFrame({
            "bb_middle": sma,
            "bb_upper": upper_band,
            "bb_lower": lower_band,
        })


class KeltnerChannels(BaseIndicator):
    """켈트너 채널"""
    
    def __init__(
        self,
        period: int = 20,
        atr_multiplier: float = 2.0,
        atr_period: int = 14,
        config: Dict[str, Any] = None,
    ):
        """
        Keltner Channels 초기화
        
        Args:
            period: EMA 기간
            atr_multiplier: ATR 배수
            atr_period: ATR 기간
            config: 추가 설정
        """
        config = config or {}
        config["period"] = period
        config["atr_multiplier"] = atr_multiplier
        config["atr_period"] = atr_period
        super().__init__(f"KC_{period}_{atr_multiplier}", config)
        self.period = period
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """Keltner Channels 중간선 (EMA) 계산"""
        return df["close"].ewm(span=self.period, adjust=False).mean()
    
    def calculate_full(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Keltner Channels 전체 계산
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            중간선, 상단선, 하단선이 포함된 데이터프레임
        """
        # ATR 계산
        atr_indicator = ATR(period=self.atr_period)
        atr = atr_indicator.calculate(df)
        
        # EMA 계산
        ema = df["close"].ewm(span=self.period, adjust=False).mean()
        
        # 채널 계산
        upper_channel = ema + (atr * self.atr_multiplier)
        lower_channel = ema - (atr * self.atr_multiplier)
        
        return pd.DataFrame({
            "kc_middle": ema,
            "kc_upper": upper_channel,
            "kc_lower": lower_channel,
        })

