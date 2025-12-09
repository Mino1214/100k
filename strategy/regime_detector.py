"""레짐 탐지 모듈"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from strategy.base_strategy import Regime
from utils.logger import get_logger

logger = get_logger(__name__)


class RegimeDetector:
    """레짐 탐지 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        레짐 탐지기 초기화
        
        Args:
            config: 레짐 탐지 설정
        """
        self.config = config
        self.method = config.get("method", "ema_alignment")
        self.ema_config = config.get("ema_alignment", {})
        self.transition_config = config.get("transition", {})
        logger.info(f"레짐 탐지기 초기화: method={self.method}")
    
    def detect(self, df: pd.DataFrame) -> pd.Series:
        """
        레짐 탐지
        
        Args:
            df: 지표가 포함된 데이터프레임
            
        Returns:
            레짐 시리즈
        """
        if self.method == "ema_alignment":
            return self._detect_ema_alignment(df)
        else:
            raise ValueError(f"지원하지 않는 레짐 탐지 방법: {self.method}")
    
    def _detect_ema_alignment(self, df: pd.DataFrame) -> pd.Series:
        """
        EMA 정렬 기반 레짐 탐지 (최적화: 벡터화 연산)
        
        Args:
            df: 지표가 포함된 데이터프레임
            
        Returns:
            레짐 시리즈
        """
        # EMA 컬럼 확인 (최적화: 한 번만 순회)
        ema20_col = None
        ema40_col = None
        ema80_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if "ema_20" in col_lower or col == "EMA_20":
                ema20_col = col
            elif "ema_40" in col_lower or col == "EMA_40":
                ema40_col = col
            elif "ema_80" in col_lower or col == "EMA_80":
                ema80_col = col
        
        if not all([ema20_col, ema40_col, ema80_col]):
            raise ValueError("EMA 지표가 계산되지 않았습니다. EMA_20, EMA_40, EMA_80이 필요합니다.")
        
        # 벡터화 연산 (numpy 배열로 변환하여 빠른 계산)
        ema20 = df[ema20_col].values
        ema40 = df[ema40_col].values
        ema80 = df[ema80_col].values
        
        # Bull 조건: EMA20 > EMA40 > EMA80 (벡터화 연산)
        bull_config = self.ema_config.get("bull", {})
        min_separation_pct = bull_config.get("min_separation_pct", 0.1)
        
        # numpy 배열 연산으로 최적화
        import numpy as np
        ema20_arr = np.array(ema20)
        ema40_arr = np.array(ema40)
        ema80_arr = np.array(ema80)
        
        # 0으로 나누기 방지
        ema40_safe = np.where(ema40_arr != 0, ema40_arr, 1)
        ema80_safe = np.where(ema80_arr != 0, ema80_arr, 1)
        
        bull_condition = (
            (ema20_arr > ema40_arr) &
            (ema40_arr > ema80_arr) &
            ((ema20_arr - ema40_arr) / ema40_safe * 100 >= min_separation_pct) &
            ((ema40_arr - ema80_arr) / ema80_safe * 100 >= min_separation_pct)
        )
        
        # Bear 조건: EMA20 < EMA40 < EMA80
        bear_config = self.ema_config.get("bear", {})
        ema20_safe = np.where(ema20_arr != 0, ema20_arr, 1)
        bear_condition = (
            (ema20_arr < ema40_arr) &
            (ema40_arr < ema80_arr) &
            ((ema40_arr - ema20_arr) / ema20_safe * 100 >= min_separation_pct) &
            ((ema80_arr - ema40_arr) / ema40_safe * 100 >= min_separation_pct)
        )
        
        # 레짐 할당 (벡터화)
        regime_values = np.where(bull_condition, Regime.BULL, 
                         np.where(bear_condition, Regime.BEAR, Regime.SIDEWAYS))
        regime = pd.Series(regime_values, index=df.index)
        
        # 레짐 전환 필터 적용
        regime = self._apply_transition_filter(regime)
        
        return regime
    
    def _apply_transition_filter(self, regime: pd.Series) -> pd.Series:
        """
        레짐 전환 필터 적용 (노이즈 제거)
        
        Args:
            regime: 원본 레짐 시리즈
            
        Returns:
            필터링된 레짐 시리즈
        """
        min_bars = self.transition_config.get("min_bars", 5)
        confirmation_bars = self.transition_config.get("confirmation_bars", 3)
        
        filtered_regime = regime.copy()
        
        # 최소 유지 기간 필터
        for i in range(len(regime) - min_bars + 1):
            window = regime.iloc[i:i + min_bars]
            if len(window.unique()) == 1:
                # 일관된 레짐이면 유지
                continue
            else:
                # 불일치하면 이전 레짐 유지
                if i > 0:
                    filtered_regime.iloc[i:i + min_bars - 1] = filtered_regime.iloc[i - 1]
        
        # 확인 기간 필터
        for i in range(confirmation_bars, len(filtered_regime)):
            recent_regimes = filtered_regime.iloc[i - confirmation_bars:i]
            if len(recent_regimes.unique()) == 1:
                # 최근 레짐이 일관되면 유지
                continue
            else:
                # 불일치하면 이전 레짐 유지
                filtered_regime.iloc[i] = filtered_regime.iloc[i - 1]
        
        return filtered_regime

