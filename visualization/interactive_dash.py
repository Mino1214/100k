"""인터랙티브 대시보드 모듈 (Dash)"""

from typing import Dict, Any, Optional
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from visualization.charts import create_main_chart, create_equity_chart, create_drawdown_chart
from utils.logger import get_logger

logger = get_logger(__name__)


def create_dashboard(
    df: pd.DataFrame,
    trades_df: pd.DataFrame,
    equity_curve_df: pd.DataFrame,
    regime_series: Optional[pd.Series] = None,
    port: int = 8050,
) -> None:
    """
    인터랙티브 대시보드 생성 및 실행
    
    Args:
        df: OHLCV 데이터프레임
        trades_df: 거래 기록 데이터프레임
        equity_curve_df: 자산 곡선 데이터프레임
        regime_series: 레짐 시리즈
        port: 포트 번호
    """
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("백테스트 대시보드"),
        
        dcc.Graph(
            id="main-chart",
            figure=create_main_chart(df, trades_df, regime_series),
        ),
        
        dcc.Graph(
            id="equity-chart",
            figure=create_equity_chart(equity_curve_df),
        ),
        
        dcc.Graph(
            id="drawdown-chart",
            figure=create_drawdown_chart(equity_curve_df),
        ),
    ])
    
    logger.info(f"대시보드 실행: http://localhost:{port}")
    app.run_server(debug=False, port=port)

