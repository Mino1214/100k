"""API 엔드포인트 모듈"""

from flask import Blueprint, jsonify
from analytics.db_logger import DatabaseLogger
from utils.helpers import load_yaml
from utils.logger import get_logger
from .status import get_backtest_status
from datetime import datetime, timedelta
import json

logger = get_logger(__name__)

api_bp = Blueprint("api", __name__)

# 전역 DB 로거 (초기화는 필요시)
_db_logger = None


def get_db_logger():
    """데이터베이스 로거 인스턴스 반환"""
    global _db_logger
    if _db_logger is None:
        try:
            config = load_yaml("config/settings.yaml")
            db_config = config.get("data", {}).get("database", {})
            connection_string = db_config.get("connection_string")
            if connection_string:
                _db_logger = DatabaseLogger(connection_string, "myno")
        except Exception as e:
            logger.error(f"DB 로거 초기화 실패: {e}")
    return _db_logger


@api_bp.route("/status")
def get_status():
    """백테스트 상태 조회"""
    status = get_backtest_status()
    
    # 진행률 계산
    if status.get("total_bars", 0) > 0:
        progress = (status.get("current_bar", 0) / status.get("total_bars", 1)) * 100
    else:
        progress = 0
    
    # 예상 남은 시간 계산
    eta = None
    if status.get("running") and status.get("current_bar", 0) > 0:
        elapsed = (datetime.now() - datetime.fromisoformat(status.get("start_time", datetime.now().isoformat()))).total_seconds()
        if elapsed > 0:
            rate = status.get("current_bar", 0) / elapsed
            remaining_bars = status.get("total_bars", 0) - status.get("current_bar", 0)
            if rate > 0:
                remaining_seconds = remaining_bars / rate
                eta = f"{int(remaining_seconds // 60)}분 {int(remaining_seconds % 60)}초"
    
    return jsonify({
        "running": status.get("running", False),
        "progress": progress,
        "current_bar": status.get("current_bar", 0),
        "total_bars": status.get("total_bars", 0),
        "session_id": status.get("session_id"),
        "start_time": status.get("start_time"),
        "estimated_time_remaining": eta,
        "message": status.get("message", "대기 중"),
    })


@api_bp.route("/results/latest")
def get_latest_results():
    """최신 백테스트 결과 조회"""
    db_logger = get_db_logger()
    if not db_logger:
        return jsonify([])
    
    try:
        with db_logger.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT * FROM myno_backtest_results 
                ORDER BY run_date DESC 
                LIMIT 20
            """))
            
            rows = result.fetchall()
            columns = result.keys()
            
            results = []
            for row in rows:
                result_dict = dict(zip(columns, row))
                # datetime 객체를 문자열로 변환
                for key, value in result_dict.items():
                    if isinstance(value, datetime):
                        result_dict[key] = value.isoformat()
                    elif isinstance(value, (int, float)) and value is None:
                        result_dict[key] = 0
                results.append(result_dict)
            
            return jsonify(results)
    except Exception as e:
        logger.error(f"결과 조회 실패: {e}")
        return jsonify([])


@api_bp.route("/results/<session_id>")
def get_result_by_session(session_id):
    """특정 세션의 결과 조회"""
    db_logger = get_db_logger()
    if not db_logger:
        return jsonify({})
    
    try:
        with db_logger.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT * FROM myno_backtest_results 
                WHERE session_id = :session_id
            """), {"session_id": session_id})
            
            row = result.fetchone()
            if row:
                columns = result.keys()
                result_dict = dict(zip(columns, row))
                for key, value in result_dict.items():
                    if isinstance(value, datetime):
                        result_dict[key] = value.isoformat()
                return jsonify(result_dict)
            else:
                return jsonify({}), 404
    except Exception as e:
        logger.error(f"결과 조회 실패: {e}")
        return jsonify({}), 500


@api_bp.route("/reflection/latest")
def get_latest_reflection():
    """최신 자기반성 일지 조회"""
    db_logger = get_db_logger()
    if not db_logger:
        return jsonify({})
    
    try:
        with db_logger.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT * FROM myno_reflection_logs 
                ORDER BY reflection_date DESC, created_at DESC 
                LIMIT 1
            """))
            
            row = result.fetchone()
            if row:
                columns = result.keys()
                result_dict = dict(zip(columns, row))
                for key, value in result_dict.items():
                    if isinstance(value, datetime):
                        result_dict[key] = value.isoformat()
                return jsonify(result_dict)
            else:
                return jsonify({})
    except Exception as e:
        logger.error(f"일지 조회 실패: {e}")
        return jsonify({})


@api_bp.route("/reflection/<session_id>")
def get_reflection_by_session(session_id):
    """특정 세션의 자기반성 일지 조회"""
    db_logger = get_db_logger()
    if not db_logger:
        return jsonify({})
    
    try:
        with db_logger.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT * FROM myno_reflection_logs 
                WHERE session_id = :session_id
                ORDER BY created_at DESC 
                LIMIT 1
            """), {"session_id": session_id})
            
            row = result.fetchone()
            if row:
                columns = result.keys()
                result_dict = dict(zip(columns, row))
                for key, value in result_dict.items():
                    if isinstance(value, datetime):
                        result_dict[key] = value.isoformat()
                return jsonify(result_dict)
            else:
                return jsonify({}), 404
    except Exception as e:
        logger.error(f"일지 조회 실패: {e}")
        return jsonify({}), 500


@api_bp.route("/trades/<session_id>")
def get_trades_by_session(session_id):
    """특정 세션의 거래 기록 조회"""
    db_logger = get_db_logger()
    if not db_logger:
        return jsonify([])
    
    try:
        with db_logger.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT * FROM myno_trade_details 
                WHERE session_id = :session_id
                ORDER BY entry_time
            """), {"session_id": session_id})
            
            rows = result.fetchall()
            columns = result.keys()
            
            trades = []
            for row in rows:
                trade_dict = dict(zip(columns, row))
                for key, value in trade_dict.items():
                    if isinstance(value, datetime):
                        trade_dict[key] = value.isoformat()
                trades.append(trade_dict)
            
            return jsonify(trades)
    except Exception as e:
        logger.error(f"거래 기록 조회 실패: {e}")
        return jsonify([])


@api_bp.route("/health")
def health_check():
    """헬스 체크"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
    })


@api_bp.route("/live-trading/status")
def get_live_trading_status():
    """실시간 거래 상태 조회"""
    try:
        from web.server import get_webhook_trader
    except ImportError:
        # 순환 import 방지
        import sys
        from web import server
        get_webhook_trader = server.get_webhook_trader
    
    webhook_trader = get_webhook_trader()
    if not webhook_trader:
        return jsonify({
            "status": "not_configured",
            "message": "웹훅 거래자가 설정되지 않았습니다",
        })
    
    live_trader = webhook_trader.live_trader
    if not live_trader:
        return jsonify({
            "status": "no_live_trader",
            "message": "LiveTrader가 실행되지 않았습니다",
            "webhook_enabled": True,
            "last_bar": webhook_trader.get_last_bar(),
        })
    
    # LiveTrader 상태 가져오기
    trader_status = live_trader.get_status()
    
    # 현재 포지션 정보
    current_position = None
    if hasattr(live_trader, 'current_position') and live_trader.current_position:
        pos = live_trader.current_position
        current_position = {
            "direction": pos.direction if hasattr(pos, 'direction') else None,
            "entry_price": pos.entry_price if hasattr(pos, 'entry_price') else None,
            "quantity": pos.quantity if hasattr(pos, 'quantity') else None,
            "entry_time": pos.entry_time.isoformat() if hasattr(pos, 'entry_time') and pos.entry_time else None,
        }
    
    return jsonify({
        "status": "active",
        "is_trading": trader_status.get("is_trading", False),
        "current_params": trader_status.get("current_params", {}),
        "last_optimization": trader_status.get("last_optimization"),
        "optimization_count": trader_status.get("optimization_count", 0),
        "current_position": current_position,
        "last_bar": webhook_trader.get_last_bar(),
        "webhook_enabled": True,
    })

