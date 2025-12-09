"""웹훅 기반 거래자 - TradingView 웹훅으로 봉 마감 데이터 수신"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
from trading.live_trader import LiveTrader
from utils.logger import get_logger

logger = get_logger(__name__)


class WebhookTrader:
    """웹훅 기반 거래자 - TradingView에서 봉 마감 데이터 수신"""
    
    def __init__(
        self,
        config: Dict[str, Any],
        live_trader: Optional[LiveTrader] = None,
    ):
        """
        웹훅 거래자 초기화
        
        Args:
            config: 설정
            live_trader: 실시간 거래자 인스턴스 (선택적)
        """
        self.config = config
        self.live_trader = live_trader
        
        # 최근 수신된 봉 데이터
        self.last_bar: Optional[Dict[str, Any]] = None
        self.last_bar_timestamp: Optional[datetime] = None
        
        logger.info("웹훅 거래자 초기화 완료")
    
    def process_webhook_bar(self, bar_data: Dict[str, Any]):
        """
        웹훅으로 받은 봉 데이터 처리
        
        Args:
            bar_data: TradingView에서 받은 봉 데이터
        """
        try:
            # 타임스탬프 파싱
            timestamp_str = bar_data.get("timestamp")
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # 중복 봉 체크 (같은 타임스탬프면 무시)
            if self.last_bar_timestamp and timestamp <= self.last_bar_timestamp:
                logger.debug(f"중복 봉 무시: {timestamp}")
                return
            
            # 봉 데이터 정규화
            normalized_bar = {
                "timestamp": timestamp,
                "open": float(bar_data.get("open", 0.0)),
                "high": float(bar_data.get("high", 0.0)),
                "low": float(bar_data.get("low", 0.0)),
                "close": float(bar_data.get("close", 0.0)),
                "volume": float(bar_data.get("volume", 0.0)),
                "symbol": bar_data.get("symbol", "ETHUSDT"),
                "timeframe": bar_data.get("timeframe", "1m"),
            }
            
            logger.info(f"웹훅 봉 데이터 수신: {normalized_bar['symbol']} @ {timestamp}, Close: {normalized_bar['close']}")
            
            # 실시간 거래자에 전달
            if self.live_trader:
                # 봉 마감 이벤트 처리
                self.live_trader._on_bar_close(normalized_bar)
            else:
                logger.warning("실시간 거래자가 설정되지 않음")
            
            # 최근 봉 업데이트
            self.last_bar = normalized_bar
            self.last_bar_timestamp = timestamp
            
        except Exception as e:
            logger.error(f"웹훅 봉 데이터 처리 실패: {e}")
            raise
    
    def get_last_bar(self) -> Optional[Dict[str, Any]]:
        """최근 수신된 봉 데이터 반환"""
        return self.last_bar

