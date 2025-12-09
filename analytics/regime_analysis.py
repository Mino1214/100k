"""레짐별 분석 모듈"""

import pandas as pd
from typing import Dict, Any, List
from analytics.metrics import PerformanceMetrics, calculate_metrics
from strategy.base_strategy import Regime
from utils.logger import get_logger

logger = get_logger(__name__)


class RegimeAnalyzer:
    """레짐별 분석 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        레짐 분석기 초기화
        
        Args:
            config: 레짐 분석 설정
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.metrics_per_regime = config.get("metrics_per_regime", True)
        self.transition_analysis = config.get("transition_analysis", True)
        logger.info("레짐 분석기 초기화 완료")
    
    def analyze(
        self,
        trades_df: pd.DataFrame,
        equity_curve_df: pd.DataFrame,
        regime_series: pd.Series,
        initial_capital: float,
    ) -> Dict[str, Any]:
        """
        레짐별 분석 실행
        
        Args:
            trades_df: 거래 기록 데이터프레임
            equity_curve_df: 자산 곡선 데이터프레임
            regime_series: 레짐 시리즈
            initial_capital: 초기 자본
            
        Returns:
            레짐별 분석 결과
        """
        if not self.enabled:
            return {}
        
        results = {}
        
        if self.metrics_per_regime:
            results["regime_metrics"] = self._calculate_regime_metrics(
                trades_df,
                equity_curve_df,
                regime_series,
                initial_capital,
            )
        
        if self.transition_analysis:
            results["transition_analysis"] = self._analyze_transitions(
                trades_df,
                regime_series,
            )
        
        return results
    
    def _calculate_regime_metrics(
        self,
        trades_df: pd.DataFrame,
        equity_curve_df: pd.DataFrame,
        regime_series: pd.Series,
        initial_capital: float,
    ) -> Dict[str, PerformanceMetrics]:
        """레짐별 성능 지표 계산"""
        regime_metrics = {}
        
        for regime in [Regime.BULL, Regime.BEAR, Regime.SIDEWAYS]:
            regime_name = regime.value
            
            # 레짐별 거래 필터링
            regime_trades = self._filter_trades_by_regime(trades_df, regime_series, regime)
            
            # 레짐별 자산 곡선 필터링
            regime_equity = self._filter_equity_by_regime(equity_curve_df, regime_series, regime)
            
            if len(regime_trades) > 0 or len(regime_equity) > 0:
                metrics = calculate_metrics(regime_trades, regime_equity, initial_capital)
                regime_metrics[regime_name] = metrics
        
        return regime_metrics
    
    def _filter_trades_by_regime(
        self,
        trades_df: pd.DataFrame,
        regime_series: pd.Series,
        regime: Regime,
    ) -> pd.DataFrame:
        """레짐별 거래 필터링"""
        if trades_df.empty:
            return trades_df
        
        filtered_trades = []
        for _, trade in trades_df.iterrows():
            entry_time = trade["entry_time"]
            if entry_time in regime_series.index:
                trade_regime = regime_series.loc[entry_time]
                if trade_regime == regime:
                    filtered_trades.append(trade)
        
        if filtered_trades:
            return pd.DataFrame(filtered_trades)
        else:
            return pd.DataFrame()
    
    def _filter_equity_by_regime(
        self,
        equity_curve_df: pd.DataFrame,
        regime_series: pd.Series,
        regime: Regime,
    ) -> pd.DataFrame:
        """레짐별 자산 곡선 필터링"""
        if equity_curve_df.empty:
            return equity_curve_df
        
        # 레짐 시리즈와 인덱스 매칭
        common_index = equity_curve_df.index.intersection(regime_series.index)
        if len(common_index) == 0:
            return pd.DataFrame()
        
        regime_mask = regime_series.loc[common_index] == regime
        filtered_equity = equity_curve_df.loc[common_index][regime_mask]
        
        return filtered_equity
    
    def _analyze_transitions(
        self,
        trades_df: pd.DataFrame,
        regime_series: pd.Series,
    ) -> Dict[str, Any]:
        """레짐 전환 분석"""
        if trades_df.empty or regime_series.empty:
            return {}
        
        # 레짐 전환 지점 찾기
        transitions = []
        prev_regime = None
        
        for timestamp, regime in regime_series.items():
            if prev_regime is not None and regime != prev_regime:
                transitions.append({
                    "timestamp": timestamp,
                    "from_regime": prev_regime.value if hasattr(prev_regime, 'value') else str(prev_regime),
                    "to_regime": regime.value if hasattr(regime, 'value') else str(regime),
                })
            prev_regime = regime
        
        # 전환 후 거래 성과 분석
        transition_performance = []
        for transition in transitions:
            transition_time = transition["timestamp"]
            # 전환 후 일정 기간 거래 필터링
            post_transition_trades = trades_df[trades_df["entry_time"] >= transition_time]
            if len(post_transition_trades) > 0:
                avg_return = post_transition_trades["return_pct"].mean()
                transition_performance.append({
                    **transition,
                    "avg_return": avg_return,
                    "trade_count": len(post_transition_trades),
                })
        
        return {
            "transitions": transitions,
            "transition_performance": transition_performance,
        }

