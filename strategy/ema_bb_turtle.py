"""EMA + Bollinger Bands + Turtle Trailing 전략"""

import pandas as pd
from typing import Dict, Any, Optional
from strategy.base_strategy import BaseStrategy, Regime, Signal, SignalType, Position
from strategy.regime_detector import RegimeDetector
from strategy.signal_generator import SignalGenerator
from indicators.trend import EMA
from indicators.volatility import BollingerBands, ATR
from indicators.volume import VolumeMA
from utils.logger import get_logger

logger = get_logger(__name__)


class EMABBTurtleStrategy(BaseStrategy):
    """EMA + Bollinger Bands + Turtle Trailing 전략"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        전략 초기화
        
        Args:
            config: 전략 설정
        """
        super().__init__(config)
        
        # 지표 설정
        indicators_config = config.get("indicators", {})
        ema_config = indicators_config.get("ema", {})
        bb_config = indicators_config.get("bollinger", {})
        atr_config = indicators_config.get("atr", {})
        volume_config = indicators_config.get("volume_ma", {})
        
        # EMA 기간 설정 (동적 파라미터 지원)
        ema_periods = ema_config.get("periods", [20, 40, 80])
        if len(ema_periods) < 3:
            ema_periods = ema_periods + [80] * (3 - len(ema_periods))  # 기본값으로 채우기
        
        # 지표 인스턴스 생성
        self.ema20 = EMA(period=ema_periods[0], source="close")
        self.ema40 = EMA(period=ema_periods[1], source="close")
        self.ema80 = EMA(period=ema_periods[2], source="close")
        self.bb = BollingerBands(
            period=bb_config.get("period", 20),
            std_dev=bb_config.get("std_dev", 2.0),
        )
        self.atr = ATR(
            period=atr_config.get("period", 20),
            method=atr_config.get("method", "wilder"),
        )
        self.volume_ma = VolumeMA(
            period=volume_config.get("period", 20),
            type=volume_config.get("type", "sma"),
        )
        
        # 레짐 탐지기
        regime_config = config.get("regime", {})
        self.regime_detector = RegimeDetector(regime_config)
        
        # 시그널 생성기
        strategy_config = config.get("strategy", {})
        self.signal_generator = SignalGenerator(strategy_config)
        
        # 스탑로스 설정
        strategy_config = config.get("strategy", {})
        exit_config = strategy_config.get("exit", {})
        stop_loss_config = exit_config.get("stop_loss", {})
        self.atr_multiplier = stop_loss_config.get("atr_multiplier", 2.0)
        self.update_on = stop_loss_config.get("update_on", "favorable_move")
        
        self.validate_config()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """지표 계산"""
        result_df = df.copy()
        
        # EMA 계산
        result_df["EMA_20"] = self.ema20(result_df)
        result_df["EMA_40"] = self.ema40(result_df)
        result_df["EMA_80"] = self.ema80(result_df)
        
        # Bollinger Bands 계산
        bb_result = self.bb.calculate_full(result_df)
        result_df["bb_middle"] = bb_result["bb_middle"]
        result_df["bb_upper"] = bb_result["bb_upper"]
        result_df["bb_lower"] = bb_result["bb_lower"]
        
        # ATR 계산
        result_df["ATR"] = self.atr(result_df)
        
        # Volume MA 계산
        result_df["VolumeMA"] = self.volume_ma(result_df)
        
        return result_df
    
    def detect_regime(self, df: pd.DataFrame) -> pd.Series:
        """레짐 탐지"""
        return self.regime_detector.detect(df)
    
    def generate_entry_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        current_position: Optional[Position],
    ) -> Signal:
        """진입 시그널 생성 (최적화)"""
        if current_position is not None:
            return Signal(
                type=SignalType.NO_ACTION,
                price=df.iloc[idx]["close"],
                timestamp=df.index[idx],
                regime=Regime.SIDEWAYS,
            )
        
        if idx >= len(df):
            return Signal(
                type=SignalType.NO_ACTION,
                price=df.iloc[-1]["close"],
                timestamp=df.index[-1],
                regime=Regime.SIDEWAYS,
            )
        
        # 레짐 확인 (캐싱 활용)
        if not hasattr(self, '_regime_cache') or self._regime_cache is None or len(self._regime_cache) != len(df):
            self._regime_cache = self.detect_regime(df)
        current_regime = self._regime_cache.iloc[idx]
        
        # Long 진입 확인
        if self.signal_generator.check_entry_conditions(df, idx, current_regime, "long"):
            entry_price = df.iloc[idx]["close"]
            atr_value = df.iloc[idx]["ATR"]
            stop_loss = entry_price - (atr_value * self.atr_multiplier)
            
            return Signal(
                type=SignalType.LONG_ENTRY,
                price=entry_price,
                timestamp=df.index[idx],
                regime=current_regime,
                stop_loss=stop_loss,
            )
        
        # Short 진입 확인
        if self.signal_generator.check_entry_conditions(df, idx, current_regime, "short"):
            entry_price = df.iloc[idx]["close"]
            atr_value = df.iloc[idx]["ATR"]
            stop_loss = entry_price + (atr_value * self.atr_multiplier)
            
            return Signal(
                type=SignalType.SHORT_ENTRY,
                price=entry_price,
                timestamp=df.index[idx],
                regime=current_regime,
                stop_loss=stop_loss,
            )
        
        return Signal(
            type=SignalType.NO_ACTION,
            price=df.iloc[idx]["close"],
            timestamp=df.index[idx],
            regime=current_regime,
        )
    
    def generate_exit_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        position: Position,
    ) -> Signal:
        """청산 시그널 생성 (최적화)"""
        if idx >= len(df):
            return Signal(
                type=SignalType.NO_ACTION,
                price=df.iloc[-1]["close"],
                timestamp=df.index[-1],
                regime=Regime.SIDEWAYS,
            )
        
        # 레짐 확인 (캐싱 활용)
        if not hasattr(self, '_regime_cache') or self._regime_cache is None or len(self._regime_cache) != len(df):
            self._regime_cache = self.detect_regime(df)
        current_regime = self._regime_cache.iloc[idx]
        
        # 청산 조건 확인
        if self.signal_generator.check_exit_conditions(df, idx, position, current_regime):
            exit_price = df.iloc[idx]["close"]
            exit_type = SignalType.LONG_EXIT if position.direction == "long" else SignalType.SHORT_EXIT
            
            return Signal(
                type=exit_type,
                price=exit_price,
                timestamp=df.index[idx],
                regime=current_regime,
            )
        
        return Signal(
            type=SignalType.NO_ACTION,
            price=df.iloc[idx]["close"],
            timestamp=df.index[idx],
            regime=current_regime,
        )
    
    def update_stop_loss(
        self,
        df: pd.DataFrame,
        idx: int,
        position: Position,
    ) -> float:
        """트레일링 스탑 업데이트"""
        if idx >= len(df):
            return position.stop_loss
        
        current_price = df.iloc[idx]["close"]
        atr_value = df.iloc[idx]["ATR"]
        
        if pd.isna(atr_value) or atr_value == 0:
            return position.stop_loss
        
        if position.direction == "long":
            # Long 포지션: 가격이 상승할 때만 스탑로스 상향 조정
            new_stop = current_price - (atr_value * self.atr_multiplier)
            
            if self.update_on == "always":
                return max(new_stop, position.stop_loss)  # 항상 상향만
            elif self.update_on == "favorable_move":
                # 유리한 방향으로 움직일 때만 업데이트
                if current_price > position.entry_price:
                    return max(new_stop, position.stop_loss)
                else:
                    return position.stop_loss
            else:
                return position.stop_loss
        
        else:  # short
            # Short 포지션: 가격이 하락할 때만 스탑로스 하향 조정
            new_stop = current_price + (atr_value * self.atr_multiplier)
            
            if self.update_on == "always":
                return min(new_stop, position.stop_loss)  # 항상 하향만
            elif self.update_on == "favorable_move":
                # 유리한 방향으로 움직일 때만 업데이트
                if current_price < position.entry_price:
                    return min(new_stop, position.stop_loss)
                else:
                    return position.stop_loss
            else:
                return position.stop_loss

