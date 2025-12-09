"""백테스트 상태 관리 모듈"""

from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

# 전역 변수로 백테스트 상태 관리
backtest_status = {
    "running": False,
    "progress": 0,
    "current_bar": 0,
    "total_bars": 0,
    "session_id": None,
    "start_time": None,
    "estimated_time_remaining": None,
    "message": "대기 중",
}


def update_backtest_status(**kwargs):
    """백테스트 상태 업데이트"""
    global backtest_status
    backtest_status.update(kwargs)
    if kwargs.get("running"):
        backtest_status["start_time"] = datetime.now().isoformat()


def get_backtest_status():
    """백테스트 상태 반환"""
    return backtest_status

