"""드로다운 분석 차트 모듈"""

import pandas as pd
import plotly.graph_objects as go
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def create_drawdown_analysis(equity_curve_df: pd.DataFrame) -> go.Figure:
    """
    드로다운 분석 차트 생성
    
    Args:
        equity_curve_df: 자산 곡선 데이터프레임
        
    Returns:
        Plotly Figure
    """
    equity_series = equity_curve_df["equity"]
    
    # 드로다운 계산
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max
    
    # 드로다운 기간 계산
    drawdown_periods = []
    in_drawdown = False
    dd_start = None
    
    for i, dd in enumerate(drawdown):
        if dd < -0.01:  # 1% 이상 드로다운
            if not in_drawdown:
                in_drawdown = True
                dd_start = i
        else:
            if in_drawdown:
                in_drawdown = False
                if dd_start is not None:
                    drawdown_periods.append({
                        "start": drawdown.index[dd_start],
                        "end": drawdown.index[i - 1],
                        "duration": i - dd_start,
                        "max_dd": drawdown.iloc[dd_start:i].min(),
                    })
                dd_start = None
    
    # 차트 생성
    fig = go.Figure()
    
    # 드로다운 곡선
    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown * 100,
            name="Drawdown",
            fill="tozeroy",
            line=dict(color="red", width=1),
        )
    )
    
    # 드로다운 기간 표시
    for period in drawdown_periods:
        fig.add_vrect(
            x0=period["start"],
            x1=period["end"],
            fillcolor="rgba(255, 0, 0, 0.1)",
            layer="below",
            line_width=0,
        )
    
    fig.update_layout(
        title="드로다운 분석",
        xaxis_title="시간",
        yaxis_title="드로다운 (%)",
        height=400,
    )
    
    return fig

