"""스마트 진입 모듈 - 승률 향상을 위한 정교한 진입 조건"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from strategy.base_strategy import Regime, Signal
from utils.logger import get_logger

logger = get_logger(__name__)


class SmartEntry:
    """스마트 진입 클래스 - 승률 최대화"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        스마트 진입 초기화
        
        Args:
            config: 진입 설정
        """
        self.config = config
        entry_config = config.get("strategy", {}).get("entry", {})
        
        # 진입 필터 설정
        self.filters = entry_config.get("filters", {})
        self.min_confidence = self.filters.get("min_confidence", 0.7)  # 최소 신뢰도
        self.require_regime_confirmation = self.filters.get("require_regime_confirmation", True)
        self.require_volume_confirmation = self.filters.get("require_volume_confirmation", True)
        self.require_trend_alignment = self.filters.get("require_trend_alignment", True)
        
        # 다중 확인 (여러 바에 걸쳐 확인)
        self.confirmation_bars = self.filters.get("confirmation_bars", 2)  # 2바 확인
        
        logger.info("스마트 진입 초기화 완료")
        logger.info(f"최소 신뢰도: {self.min_confidence:.1%}")
        logger.info(f"확인 바 수: {self.confirmation_bars}")
    
    def evaluate_entry_quality(
        self,
        df: pd.DataFrame,
        idx: int,
        signal: Signal,
        regime: Regime,
    ) -> tuple[bool, float, str]:
        """
        진입 품질 평가
        
        Args:
            df: 데이터프레임
            idx: 현재 인덱스
            signal: 시그널
            regime: 레짐
            
        Returns:
            (진입 가능 여부, 신뢰도, 이유)
        """
        if idx < self.confirmation_bars:
            return False, 0.0, "확인 바 수 부족"
        
        confidence = 0.0
        reasons = []
        
        # 1. 레짐 확인 (30%)
        if self.require_regime_confirmation:
            regime_score = self._check_regime_quality(df, idx, signal, regime)
            confidence += regime_score * 0.3
            if regime_score > 0.8:
                reasons.append("강한 레짐 확인")
            elif regime_score < 0.5:
                return False, 0.0, "레짐 불확실"
        
        # 2. 트렌드 정렬 확인 (25%)
        if self.require_trend_alignment:
            trend_score = self._check_trend_alignment(df, idx, signal)
            confidence += trend_score * 0.25
            if trend_score > 0.8:
                reasons.append("트렌드 정렬 우수")
            elif trend_score < 0.5:
                return False, 0.0, "트렌드 불일치"
        
        # 3. 거래량 확인 (20%)
        if self.require_volume_confirmation:
            volume_score = self._check_volume_quality(df, idx)
            confidence += volume_score * 0.2
            if volume_score > 0.8:
                reasons.append("거래량 증가")
            elif volume_score < 0.5:
                return False, 0.0, "거래량 부족"
        
        # 4. 모멘텀 확인 (15%)
        momentum_score = self._check_momentum(df, idx, signal)
        confidence += momentum_score * 0.15
        if momentum_score > 0.8:
            reasons.append("강한 모멘텀")
        
        # 5. 지지/저항 확인 (10%)
        support_resistance_score = self._check_support_resistance(df, idx, signal)
        confidence += support_resistance_score * 0.1
        if support_resistance_score > 0.8:
            reasons.append("지지/저항 확인")
        
        # 최소 신뢰도 확인
        if confidence < self.min_confidence:
            return False, confidence, f"신뢰도 부족: {confidence:.1%} < {self.min_confidence:.1%}"
        
        reason_str = ", ".join(reasons) if reasons else "기본 조건 만족"
        return True, confidence, reason_str
    
    def _check_regime_quality(
        self,
        df: pd.DataFrame,
        idx: int,
        signal: Signal,
        regime: Regime,
    ) -> float:
        """레짐 품질 확인"""
        if idx < 5:
            return 0.5
        
        # 최근 5바의 레짐 일관성 확인
        recent_regimes = []
        for i in range(max(0, idx - 4), idx + 1):
            if "regime" in df.columns:
                recent_regimes.append(df.iloc[i].get("regime"))
        
        # 레짐 일관성 계산
        if signal.type.value.startswith("long"):
            target_regime = Regime.BULL
        else:
            target_regime = Regime.BEAR
        
        consistent_count = sum(1 for r in recent_regimes if r == target_regime)
        consistency = consistent_count / len(recent_regimes) if recent_regimes else 0.0
        
        return consistency
    
    def _check_trend_alignment(
        self,
        df: pd.DataFrame,
        idx: int,
        signal: Signal,
    ) -> float:
        """트렌드 정렬 확인"""
        if idx < 2:
            return 0.5
        
        # EMA 정렬 확인
        ema_fast_col = None
        ema_slow_col = None
        
        for col in df.columns:
            if "EMA" in col and "20" in col or "fast" in col.lower():
                ema_fast_col = col
            if "EMA" in col and ("80" in col or "slow" in col.lower()):
                ema_slow_col = col
        
        if ema_fast_col is None or ema_slow_col is None:
            return 0.5
        
        current_fast = df.iloc[idx][ema_fast_col]
        current_slow = df.iloc[idx][ema_slow_col]
        prev_fast = df.iloc[idx - 1][ema_fast_col]
        prev_slow = df.iloc[idx - 1][ema_slow_col]
        
        if signal.type.value.startswith("long"):
            # Long: fast > slow 이고 상승 중
            alignment = 1.0 if current_fast > current_slow else 0.0
            momentum = 1.0 if current_fast > prev_fast and current_slow > prev_slow else 0.5
        else:
            # Short: fast < slow 이고 하락 중
            alignment = 1.0 if current_fast < current_slow else 0.0
            momentum = 1.0 if current_fast < prev_fast and current_slow < prev_slow else 0.5
        
        return (alignment + momentum) / 2.0
    
    def _check_volume_quality(self, df: pd.DataFrame, idx: int) -> float:
        """거래량 품질 확인"""
        if "volume" not in df.columns or idx < 20:
            return 0.5
        
        current_volume = df.iloc[idx]["volume"]
        
        # Volume MA 찾기
        volume_ma_col = None
        for col in df.columns:
            if "volume" in col.lower() and "ma" in col.lower():
                volume_ma_col = col
                break
        
        if volume_ma_col is None:
            return 0.5
        
        volume_ma = df.iloc[idx][volume_ma_col]
        if volume_ma == 0:
            return 0.5
        
        volume_ratio = current_volume / volume_ma
        
        # 거래량이 평균의 1.2배 이상이면 좋음
        if volume_ratio >= 1.2:
            return 1.0
        elif volume_ratio >= 0.8:
            return 0.7
        elif volume_ratio >= 0.5:
            return 0.5
        else:
            return 0.3
    
    def _check_momentum(self, df: pd.DataFrame, idx: int, signal: Signal) -> float:
        """모멘텀 확인"""
        if idx < 5:
            return 0.5
        
        current_price = df.iloc[idx]["close"]
        prices = df.iloc[max(0, idx - 5):idx + 1]["close"].values
        
        # 가격 모멘텀 계산
        if len(prices) >= 3:
            price_change = (prices[-1] - prices[0]) / prices[0]
            
            if signal.type.value.startswith("long"):
                # Long: 상승 모멘텀
                momentum = max(0.0, min(1.0, price_change * 100))  # 정규화
            else:
                # Short: 하락 모멘텀
                momentum = max(0.0, min(1.0, -price_change * 100))
        else:
            momentum = 0.5
        
        return momentum
    
    def _check_support_resistance(
        self,
        df: pd.DataFrame,
        idx: int,
        signal: Signal,
    ) -> float:
        """지지/저항 확인"""
        if idx < 20:
            return 0.5
        
        current_price = df.iloc[idx]["close"]
        
        # 최근 20바의 고점/저점 확인
        recent_high = df.iloc[max(0, idx - 20):idx + 1]["high"].max()
        recent_low = df.iloc[max(0, idx - 20):idx + 1]["low"].min()
        
        if signal.type.value.startswith("long"):
            # Long: 저점 근처에서 진입 (지지선)
            distance_to_low = abs(current_price - recent_low) / recent_low
            if distance_to_low < 0.01:  # 1% 이내
                return 1.0
            elif distance_to_low < 0.02:  # 2% 이내
                return 0.7
            else:
                return 0.5
        else:
            # Short: 고점 근처에서 진입 (저항선)
            distance_to_high = abs(current_price - recent_high) / recent_high
            if distance_to_high < 0.01:  # 1% 이내
                return 1.0
            elif distance_to_high < 0.02:  # 2% 이내
                return 0.7
            else:
                return 0.5

