"""성능 지표 계산 모듈"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from utils.logger import get_logger
from utils.helpers import safe_divide

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """백테스트 성능 지표"""
    # 수익률 지표
    total_return: float
    annualized_return: float
    
    # 리스크 조정 수익률
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # 드로다운
    max_drawdown: float
    max_drawdown_duration: int  # bars
    avg_drawdown: float
    
    # 거래 통계
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # 손익 분석
    gross_profit: float
    gross_loss: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    
    # 기대값
    expectancy: float
    
    # 기타
    avg_trade_duration: float  # bars
    exposure_time: float  # percentage
    
    # 레짐별 지표 (Optional)
    regime_metrics: Optional[Dict[str, 'PerformanceMetrics']] = None
    
    # 최종 자산 (DB 저장용)
    final_equity: Optional[float] = None


def calculate_metrics(
    trades_df: pd.DataFrame,
    equity_curve_df: pd.DataFrame,
    initial_capital: float,
    periods_per_year: int = 525600,  # 1분봉 기준 1년
) -> PerformanceMetrics:
    """
    성능 지표 계산
    
    Args:
        trades_df: 거래 기록 데이터프레임
        equity_curve_df: 자산 곡선 데이터프레임
        initial_capital: 초기 자본
        periods_per_year: 연간 기간 수
        
    Returns:
        성능 지표
    """
    if trades_df.empty:
        logger.warning("거래 기록이 없습니다.")
        return _create_empty_metrics()
    
    # 기본 수익률 계산
    final_equity = equity_curve_df["equity"].iloc[-1] if not equity_curve_df.empty else initial_capital
    total_return = (final_equity - initial_capital) / initial_capital
    
    # 연환산 수익률
    if not equity_curve_df.empty:
        total_periods = len(equity_curve_df)
        years = total_periods / periods_per_year
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    else:
        annualized_return = 0
    
    # 드로다운 계산
    equity_series = equity_curve_df["equity"] if not equity_curve_df.empty else pd.Series([initial_capital])
    drawdown_series = _calculate_drawdown(equity_series)
    max_drawdown = abs(drawdown_series.min()) if not drawdown_series.empty else 0
    
    # 최대 드로다운 기간
    max_dd_duration = _calculate_max_drawdown_duration(drawdown_series)
    
    # 평균 드로다운
    avg_drawdown = abs(drawdown_series[drawdown_series < 0].mean()) if len(drawdown_series[drawdown_series < 0]) > 0 else 0
    
    # 거래 통계
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df["pnl"] > 0])
    losing_trades = len(trades_df[trades_df["pnl"] <= 0])
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # 손익 분석
    gross_profit = trades_df[trades_df["pnl"] > 0]["pnl"].sum() if winning_trades > 0 else 0
    gross_loss = abs(trades_df[trades_df["pnl"] <= 0]["pnl"].sum()) if losing_trades > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
    
    avg_win = gross_profit / winning_trades if winning_trades > 0 else 0
    avg_loss = gross_loss / losing_trades if losing_trades > 0 else 0
    largest_win = trades_df["pnl"].max() if total_trades > 0 else 0
    largest_loss = trades_df["pnl"].min() if total_trades > 0 else 0
    
    # 기대값
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    # 평균 거래 기간
    avg_trade_duration = trades_df["duration_bars"].mean() if total_trades > 0 else 0
    
    # 노출 시간
    if not equity_curve_df.empty:
        total_bars = len(equity_curve_df)
        exposure_bars = trades_df["duration_bars"].sum() if total_trades > 0 else 0
        exposure_time = exposure_bars / total_bars if total_bars > 0 else 0
    else:
        exposure_time = 0
    
    # 리스크 조정 수익률
    returns = equity_curve_df["equity"].pct_change().dropna() if not equity_curve_df.empty else pd.Series()
    sharpe_ratio = _calculate_sharpe_ratio(returns, periods_per_year)
    sortino_ratio = _calculate_sortino_ratio(returns, periods_per_year)
    calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
    
    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_duration=max_dd_duration,
        avg_drawdown=avg_drawdown,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
        expectancy=expectancy,
        avg_trade_duration=avg_trade_duration,
        exposure_time=exposure_time,
        regime_metrics=None,
    )


def _calculate_drawdown(equity_series: pd.Series) -> pd.Series:
    """드로다운 계산"""
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max
    return drawdown


def _calculate_max_drawdown_duration(drawdown_series: pd.Series) -> int:
    """최대 드로다운 기간 계산"""
    if drawdown_series.empty:
        return 0
    
    max_dd = drawdown_series.min()
    if max_dd >= 0:
        return 0
    
    # 최대 드로다운 시작점 찾기
    dd_start = None
    dd_end = None
    
    for i, dd in enumerate(drawdown_series):
        if dd <= max_dd * 0.99:  # 최대 드로다운 근처
            if dd_start is None:
                dd_start = i
            dd_end = i
        elif dd_start is not None and dd > max_dd * 0.5:
            break
    
    if dd_start is not None and dd_end is not None:
        return dd_end - dd_start
    
    return 0


def _calculate_sharpe_ratio(returns: pd.Series, periods_per_year: int, risk_free_rate: float = 0.0) -> float:
    """Sharpe 비율 계산"""
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    excess_returns = returns.mean() - (risk_free_rate / periods_per_year)
    return np.sqrt(periods_per_year) * excess_returns / returns.std()


def _calculate_sortino_ratio(returns: pd.Series, periods_per_year: int, risk_free_rate: float = 0.0) -> float:
    """Sortino 비율 계산"""
    if len(returns) == 0:
        return 0.0
    
    excess_returns = returns.mean() - (risk_free_rate / periods_per_year)
    downside_returns = returns[returns < 0]
    
    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0
    
    downside_std = downside_returns.std()
    return np.sqrt(periods_per_year) * excess_returns / downside_std


def _create_empty_metrics() -> PerformanceMetrics:
    """빈 성능 지표 생성"""
    return PerformanceMetrics(
        total_return=0.0,
        annualized_return=0.0,
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        calmar_ratio=0.0,
        max_drawdown=0.0,
        max_drawdown_duration=0,
        avg_drawdown=0.0,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=0.0,
        gross_profit=0.0,
        gross_loss=0.0,
        profit_factor=0.0,
        avg_win=0.0,
        avg_loss=0.0,
        largest_win=0.0,
        largest_loss=0.0,
        expectancy=0.0,
        avg_trade_duration=0.0,
        exposure_time=0.0,
        regime_metrics=None,
    )

