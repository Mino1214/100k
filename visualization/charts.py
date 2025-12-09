"""차트 생성 모듈"""

import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def create_main_chart(
    df: pd.DataFrame,
    trades_df: Optional[pd.DataFrame] = None,
    regime_series: Optional[pd.Series] = None,
    config: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """
    메인 차트 생성 (Plotly)
    
    Args:
        df: OHLCV 데이터프레임 (지표 포함)
        trades_df: 거래 기록 데이터프레임
        regime_series: 레짐 시리즈
        config: 차트 설정
        
    Returns:
        Plotly Figure
    """
    if config is None:
        config = {}
    
    chart_type = config.get("type", "interactive")
    library = config.get("library", "plotly")
    
    if library == "plotly":
        return _create_plotly_main_chart(df, trades_df, regime_series, config)
    else:
        return _create_matplotlib_main_chart(df, trades_df, regime_series, config)


def _create_plotly_main_chart(
    df: pd.DataFrame,
    trades_df: Optional[pd.DataFrame],
    regime_series: Optional[pd.Series],
    config: Dict[str, Any],
) -> go.Figure:
    """Plotly 메인 차트 생성"""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=("가격 차트", "거래량"),
    )
    
    # 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
        ),
        row=1,
        col=1,
    )
    
    # EMA 라인
    for col in df.columns:
        if "EMA" in col or "ema" in col:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[col],
                    name=col,
                    line=dict(width=1),
                ),
                row=1,
                col=1,
            )
    
    # Bollinger Bands
    if "bb_upper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["bb_upper"],
                name="BB Upper",
                line=dict(color="gray", width=1, dash="dash"),
                showlegend=False,
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["bb_lower"],
                name="BB Lower",
                line=dict(color="gray", width=1, dash="dash"),
                fill="tonexty",
                fillcolor="rgba(128,128,128,0.1)",
                showlegend=False,
            ),
            row=1,
            col=1,
        )
    
    # 진입/청산 마커
    if trades_df is not None and not trades_df.empty:
        # Long 진입
        long_entries = trades_df[trades_df["direction"] == "long"]
        if not long_entries.empty:
            fig.add_trace(
                go.Scatter(
                    x=long_entries["entry_time"],
                    y=long_entries["entry_price"],
                    mode="markers",
                    name="Long Entry",
                    marker=dict(symbol="triangle-up", size=10, color="green"),
                ),
                row=1,
                col=1,
            )
        
        # Short 진입
        short_entries = trades_df[trades_df["direction"] == "short"]
        if not short_entries.empty:
            fig.add_trace(
                go.Scatter(
                    x=short_entries["entry_time"],
                    y=short_entries["entry_price"],
                    mode="markers",
                    name="Short Entry",
                    marker=dict(symbol="triangle-down", size=10, color="red"),
                ),
                row=1,
                col=1,
            )
    
    # 거래량
    if "volume" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["volume"],
                name="Volume",
                marker_color="blue",
            ),
            row=2,
            col=1,
        )
    
    # 레짐 배경색
    if regime_series is not None:
        _add_regime_background(fig, df.index, regime_series, config)
    
    fig.update_layout(
        title="백테스트 차트",
        xaxis_rangeslider_visible=False,
        height=800,
    )
    
    return fig


def _create_matplotlib_main_chart(
    df: pd.DataFrame,
    trades_df: Optional[pd.DataFrame],
    regime_series: Optional[pd.Series],
    config: Dict[str, Any],
) -> plt.Figure:
    """Matplotlib 메인 차트 생성"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    
    # 캔들스틱 (간단한 구현)
    ax1.plot(df.index, df["close"], label="Close", linewidth=1)
    
    # EMA
    for col in df.columns:
        if "EMA" in col or "ema" in col:
            ax1.plot(df.index, df[col], label=col, linewidth=1)
    
    ax1.set_ylabel("Price")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 거래량
    if "volume" in df.columns:
        ax2.bar(df.index, df["volume"], alpha=0.3)
        ax2.set_ylabel("Volume")
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def _add_regime_background(fig: go.Figure, index: pd.DatetimeIndex, regime_series: pd.Series, config: Dict[str, Any]):
    """레짐 배경색 추가"""
    regime_colors = config.get("regime_colors", {
        "bull": "rgba(0, 255, 0, 0.1)",
        "bear": "rgba(255, 0, 0, 0.1)",
        "sideways": "rgba(128, 128, 128, 0.1)",
    })
    
    # 레짐별 영역 표시 (간단한 구현)
    # 실제로는 각 레짐 구간별로 shape를 추가해야 함
    pass


def create_equity_chart(equity_curve_df: pd.DataFrame) -> go.Figure:
    """자산 곡선 차트 생성"""
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=equity_curve_df.index,
            y=equity_curve_df["equity"],
            name="Equity",
            line=dict(color="blue", width=2),
        )
    )
    
    fig.update_layout(
        title="자산 곡선",
        xaxis_title="시간",
        yaxis_title="자산",
        height=400,
    )
    
    return fig


def create_drawdown_chart(equity_curve_df: pd.DataFrame) -> go.Figure:
    """드로다운 차트 생성"""
    equity_series = equity_curve_df["equity"]
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown * 100,
            name="Drawdown",
            fill="tozeroy",
            line=dict(color="red", width=1),
        )
    )
    
    fig.update_layout(
        title="드로다운",
        xaxis_title="시간",
        yaxis_title="드로다운 (%)",
        height=400,
    )
    
    return fig

