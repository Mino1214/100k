"""시그널 생성 모듈"""

import pandas as pd
from typing import Dict, Any, Optional
from strategy.base_strategy import Signal, SignalType, Regime, Position
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalGenerator:
    """시그널 생성기 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        시그널 생성기 초기화
        
        Args:
            config: 시그널 생성 설정
        """
        self.config = config
        self.entry_config = config.get("entry", {})
        self.exit_config = config.get("exit", {})
        logger.info("시그널 생성기 초기화 완료")
    
    def check_entry_conditions(
        self,
        df: pd.DataFrame,
        idx: int,
        regime: Regime,
        direction: str,
    ) -> bool:
        """
        진입 조건 확인
        
        Args:
            df: 지표가 포함된 데이터프레임
            idx: 현재 인덱스
            regime: 현재 레짐
            direction: 진입 방향 (long/short)
            
        Returns:
            진입 조건 만족 여부
        """
        if idx >= len(df):
            return False
        
        direction_config = self.entry_config.get(direction, {})
        required_regime = direction_config.get("regime")
        
        # 레짐 확인
        if required_regime and regime.value != required_regime:
            return False
        
        # 조건 확인
        conditions = direction_config.get("conditions", [])
        for condition in conditions:
            if not self._check_condition(df, idx, condition):
                return False
        
        return True
    
    def _check_condition(
        self,
        df: pd.DataFrame,
        idx: int,
        condition: Dict[str, Any],
    ) -> bool:
        """
        개별 조건 확인
        
        Args:
            df: 데이터프레임
            idx: 인덱스
            condition: 조건 딕셔너리
            
        Returns:
            조건 만족 여부
        """
        condition_type = condition.get("type")
        
        if condition_type == "price_cross":
            return self._check_price_cross(df, idx, condition)
        elif condition_type == "volume_filter":
            return self._check_volume_filter(df, idx, condition)
        else:
            logger.warning(f"알 수 없는 조건 타입: {condition_type}")
            return False
    
    def _check_price_cross(
        self,
        df: pd.DataFrame,
        idx: int,
        condition: Dict[str, Any],
    ) -> bool:
        """가격 교차 조건 확인"""
        indicator_name = condition.get("indicator")
        direction = condition.get("direction")
        
        if idx == 0:
            return False
        
        current_price = df.iloc[idx]["close"]
        prev_price = df.iloc[idx - 1]["close"]
        
        # 지표 값 찾기
        indicator_col = None
        for col in df.columns:
            if indicator_name.lower() in col.lower():
                indicator_col = col
                break
        
        if indicator_col is None:
            return False
        
        current_indicator = df.iloc[idx][indicator_col]
        prev_indicator = df.iloc[idx - 1][indicator_col]
        
        if direction == "below_or_equal":
            # 가격이 지표 아래로 교차
            return prev_price > prev_indicator and current_price <= current_indicator
        elif direction == "above_or_equal":
            # 가격이 지표 위로 교차
            return prev_price < prev_indicator and current_price >= current_indicator
        else:
            return False
    
    def _check_volume_filter(
        self,
        df: pd.DataFrame,
        idx: int,
        condition: Dict[str, Any],
    ) -> bool:
        """거래량 필터 조건 확인"""
        min_ratio = condition.get("min_ratio", 0.5)
        max_ratio = condition.get("max_ratio", 3.0)
        
        if "volume" not in df.columns:
            return True  # 거래량 데이터가 없으면 통과
        
        current_volume = df.iloc[idx]["volume"]
        
        # Volume MA 찾기
        volume_ma_col = None
        for col in df.columns:
            if "volume" in col.lower() and "ma" in col.lower():
                volume_ma_col = col
                break
        
        if volume_ma_col is None:
            return True  # Volume MA가 없으면 통과
        
        volume_ma = df.iloc[idx][volume_ma_col]
        if volume_ma == 0:
            return True
        
        ratio = current_volume / volume_ma
        return min_ratio <= ratio <= max_ratio
    
    def check_exit_conditions(
        self,
        df: pd.DataFrame,
        idx: int,
        position: Position,
        regime: Regime,
    ) -> bool:
        """
        청산 조건 확인
        
        Args:
            df: 데이터프레임
            idx: 인덱스
            position: 현재 포지션
            regime: 현재 레짐
            
        Returns:
            청산 조건 만족 여부
        """
        exit_config = self.exit_config
        
        # 스탑로스 확인
        current_price = df.iloc[idx]["close"]
        if position.direction == "long":
            if current_price <= position.stop_loss:
                return True
        else:  # short
            if current_price >= position.stop_loss:
                return True
        
        # 레짐 전환 확인
        if exit_config.get("regime_exit", {}).get("enabled", False):
            if regime != position.regime_at_entry:
                return True
        
        # 시간 기반 청산
        time_exit_config = exit_config.get("time_exit", {})
        if time_exit_config.get("enabled", False):
            max_bars = time_exit_config.get("max_bars", 1440)
            bars_held = idx - df.index.get_loc(position.entry_time)
            if bars_held >= max_bars:
                return True
        
        return False

