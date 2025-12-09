"""레짐 히트맵 모듈"""

import pandas as pd
import plotly.graph_objects as go
from typing import Optional
from strategy.base_strategy import Regime
from utils.logger import get_logger

logger = get_logger(__name__)


def create_regime_heatmap(
    regime_series: pd.Series,
    timeframe: str = "1D",
) -> go.Figure:
    """
    레짐 히트맵 생성
    
    Args:
        regime_series: 레짐 시리즈
        timeframe: 집계 타임프레임
        
    Returns:
        Plotly Figure
    """
    # 레짐을 숫자로 변환
    regime_map = {
        Regime.BULL: 1,
        Regime.BEAR: -1,
        Regime.SIDEWAYS: 0,
    }
    
    regime_numeric = regime_series.map(lambda x: regime_map.get(x, 0))
    
    # 일별 집계
    if isinstance(regime_series.index, pd.DatetimeIndex):
        daily_regime = regime_numeric.resample("1D").mean()
        
        # 월별 히트맵 데이터 준비
        daily_regime.index = pd.to_datetime(daily_regime.index)
        daily_regime["year"] = daily_regime.index.year
        daily_regime["month"] = daily_regime.index.month
        daily_regime["day"] = daily_regime.index.day
        
        # 히트맵 생성 (간단한 구현)
        fig = go.Figure(data=go.Scatter(
            x=daily_regime.index,
            y=daily_regime.values,
            mode="markers",
            marker=dict(
                size=10,
                color=daily_regime.values,
                colorscale="RdYlGn",
                showscale=True,
            ),
        ))
        
        fig.update_layout(
            title="레짐 분포",
            xaxis_title="날짜",
            yaxis_title="레짐",
            height=400,
        )
        
        return fig
    else:
        logger.warning("DatetimeIndex가 아닙니다.")
        return go.Figure()

