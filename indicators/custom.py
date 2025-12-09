"""커스텀 지표 모듈 (확장용)"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from indicators.base import BaseIndicator
from utils.logger import get_logger

logger = get_logger(__name__)


class RSI(BaseIndicator):
    """상대 강도 지수 (Relative Strength Index)"""
    
    def __init__(self, period: int = 14, config: Dict[str, Any] = None):
        """
        RSI 초기화
        
        Args:
            period: 기간
            config: 추가 설정
        """
        config = config or {}
        config["period"] = period
        super().__init__(f"RSI_{period}", config)
        self.period = period
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """RSI 계산"""
        if "close" not in df.columns:
            raise ValueError("'close' 컬럼이 없습니다.")
        
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

