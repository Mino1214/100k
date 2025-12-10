"""TradingView 웹훅 핸들러 - 봉 마감 데이터 수신"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
from flask import Blueprint, request, jsonify
from utils.logger import get_logger
import hmac
import hashlib
import json

logger = get_logger(__name__)

# TradingView 웹훅을 받을 전역 콜백
_tradingview_callback: Optional[Callable] = None


def set_tradingview_callback(callback: Callable):
    """TradingView 웹훅 콜백 설정"""
    global _tradingview_callback
    _tradingview_callback = callback
    logger.info("TradingView 웹훅 콜백 설정 완료")


tradingview_bp = Blueprint('tradingview', __name__)


@tradingview_bp.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    """
    TradingView 웹훅 엔드포인트
    
    TradingView Alert에서 다음과 같은 형식으로 데이터를 보내야 함:
    {
        "symbol": "{{ticker}}",
        "exchange": "{{exchange}}",
        "timeframe": "{{interval}}",
        "timestamp": "{{time}}",
        "open": {{open}},
        "high": {{high}},
        "low": {{low}},
        "close": {{close}},
        "volume": {{volume}},
        "action": "{{strategy.order.action}}",  // "buy" or "sell" (선택)
        "strategy_name": "{{strategy.name}}"  // 선택
    }
    
    또는 간단한 형식:
    {
        "ticker": "{{ticker}}",
        "price": {{close}},
        "time": "{{time}}",
        "volume": {{volume}}
    }
    """
    try:
        # 요청 데이터 파싱
        if request.is_json:
            data = request.get_json()
        else:
            # Form 데이터인 경우
            data = request.form.to_dict()
            # JSON 문자열인 경우 파싱
            if 'data' in data:
                data = json.loads(data['data'])
        
        logger.info(f"TradingView 웹훅 수신: {data}")
        
        # 데이터 검증
        if not data:
            return jsonify({"error": "데이터가 없습니다"}), 400
        
        # TradingView 데이터 형식 변환
        bar_data = _parse_tradingview_data(data)
        
        if not bar_data:
            return jsonify({"error": "데이터 파싱 실패"}), 400
        
        # 웹훅 시크릿 검증 (선택적)
        webhook_secret = request.headers.get('X-Webhook-Secret')
        if webhook_secret:
            # 시크릿 검증 로직 (필요시 구현)
            pass
        
        # 콜백 호출
        if _tradingview_callback:
            try:
                _tradingview_callback(bar_data)
                logger.info(f"웹훅 콜백 실행 완료: {bar_data.get('timestamp')}")
            except Exception as e:
                logger.error(f"웹훅 콜백 실행 실패: {e}")
                return jsonify({"error": f"콜백 실행 실패: {str(e)}"}), 500
        
        return jsonify({
            "status": "success",
            "message": "웹훅 처리 완료",
            "data": bar_data
        }), 200
        
    except Exception as e:
        logger.error(f"TradingView 웹훅 처리 실패: {e}")
        return jsonify({"error": str(e)}), 500


def _parse_tradingview_data(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    TradingView 데이터를 표준 형식으로 변환
    
    Args:
        data: TradingView 웹훅 데이터
        
    Returns:
        표준화된 봉 데이터
    """
    try:
        # 다양한 TradingView 데이터 형식 지원
        
        # 형식 1: 상세 형식
        if "symbol" in data or "ticker" in data:
            symbol = data.get("symbol") or data.get("ticker", "UNKNOWN")
            exchange = data.get("exchange", "BINANCE")
            timeframe = data.get("timeframe") or data.get("interval", "1m")
            
            # 템플릿 변수가 치환되지 않은 경우 처리
            if symbol.startswith("{{") and symbol.endswith("}}"):
                logger.warning(f"템플릿 변수가 치환되지 않음: {symbol}. Alert 메시지 설정을 확인하세요.")
                symbol = "UNKNOWN"  # 기본값 사용
            if exchange.startswith("{{") and exchange.endswith("}}"):
                logger.warning(f"템플릿 변수가 치환되지 않음: {exchange}. Alert 메시지 설정을 확인하세요.")
                exchange = "BINANCE"  # 기본값 사용
            if timeframe.startswith("{{") and timeframe.endswith("}}"):
                logger.warning(f"템플릿 변수가 치환되지 않음: {timeframe}. Alert 메시지 설정을 확인하세요.")
                timeframe = "1m"  # 기본값 사용
            
            # 타임스탬프 파싱
            timestamp_str = data.get("timestamp") or data.get("time")
            if isinstance(timestamp_str, str):
                # 템플릿 변수 체크
                if timestamp_str.startswith("{{") and timestamp_str.endswith("}}"):
                    logger.warning(f"템플릿 변수가 치환되지 않음: {timestamp_str}. Alert 메시지 설정을 확인하세요.")
                    timestamp = datetime.now()
                else:
                    # Unix timestamp 문자열 (초, 밀리초, 또는 마이크로초)
                    try:
                        ts_value = float(timestamp_str)
                        # 마이크로초인지 확인 (16자리 이상이면 마이크로초)
                        if ts_value > 1e15:  # 마이크로초
                            timestamp = datetime.fromtimestamp(ts_value / 1000000)
                        elif ts_value > 1e12:  # 밀리초
                            timestamp = datetime.fromtimestamp(ts_value / 1000)
                        else:  # 초 단위
                            timestamp = datetime.fromtimestamp(ts_value)
                    except:
                        # ISO 형식
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        except:
                            timestamp = datetime.now()
            elif isinstance(timestamp_str, (int, float)):
                # 마이크로초인지 확인 (16자리 이상이면 마이크로초)
                if timestamp_str > 1e15:  # 마이크로초
                    timestamp = datetime.fromtimestamp(timestamp_str / 1000000)
                elif timestamp_str > 1e12:  # 밀리초
                    timestamp = datetime.fromtimestamp(timestamp_str / 1000)
                else:  # 초 단위
                    timestamp = datetime.fromtimestamp(timestamp_str)
            else:
                timestamp = datetime.now()
            
            # OHLCV 데이터
            open_price = float(data.get("open", data.get("price", 0.0)))
            high = float(data.get("high", open_price))
            low = float(data.get("low", open_price))
            close = float(data.get("close", data.get("price", open_price)))
            volume = float(data.get("volume", 0.0))
            
            return {
                "symbol": symbol,
                "exchange": exchange,
                "timeframe": timeframe,
                "timestamp": timestamp.isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "action": data.get("action"),  # "buy" or "sell" (선택)
                "strategy_name": data.get("strategy_name"),
                "raw_data": data,  # 원본 데이터 보관
            }
        
        # 형식 2: 간단한 형식
        elif "price" in data:
            return {
                "symbol": data.get("ticker", "UNKNOWN"),
                "exchange": "BINANCE",
                "timeframe": "1m",
                "timestamp": datetime.now().isoformat(),
                "open": float(data.get("price", 0.0)),
                "high": float(data.get("price", 0.0)),
                "low": float(data.get("price", 0.0)),
                "close": float(data.get("price", 0.0)),
                "volume": float(data.get("volume", 0.0)),
                "raw_data": data,
            }
        
        # 형식 3: Pine Script 기본 형식
        else:
            # 가능한 모든 필드 확인
            price = None
            for key in ["close", "price", "value"]:
                if key in data:
                    price = float(data[key])
                    break
            
            if price is None:
                logger.warning(f"가격 데이터를 찾을 수 없음: {data}")
                return None
            
            return {
                "symbol": data.get("ticker", data.get("symbol", "UNKNOWN")),
                "exchange": "BINANCE",
                "timeframe": data.get("interval", "1m"),
                "timestamp": datetime.now().isoformat(),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": float(data.get("volume", 0.0)),
                "raw_data": data,
            }
            
    except Exception as e:
        logger.error(f"TradingView 데이터 파싱 실패: {e}, 데이터: {data}")
        return None


@tradingview_bp.route('/webhook/tradingview/test', methods=['GET', 'POST'])
def tradingview_webhook_test():
    """웹훅 테스트 엔드포인트"""
    return jsonify({
        "status": "ok",
        "message": "TradingView 웹훅 엔드포인트가 정상 작동 중입니다",
        "endpoint": "/webhook/tradingview",
        "method": "POST",
        "example": {
            "symbol": "ETHUSDT",
            "exchange": "BINANCE",
            "timeframe": "1m",
            "timestamp": datetime.now().isoformat(),
            "open": 2500.0,
            "high": 2510.0,
            "low": 2490.0,
            "close": 2505.0,
            "volume": 1000.0
        }
    }), 200

