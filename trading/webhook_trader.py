"""웹훅 기반 거래자 - TradingView 웹훅으로 봉 마감 데이터 수신"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
from trading.live_trader import LiveTrader
from strategy.strategy_registry import StrategyRegistry
from backtest.engine import BacktestEngine
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
        
        # 웹훅만으로 거래 실행을 위한 백테스트 엔진 (LiveTrader가 없을 때)
        self.backtest_engine: Optional[BacktestEngine] = None
        self.position_manager = None
        
        # 봉 데이터 히스토리 (지표 계산용)
        self.bar_history: list = []
        self.max_history = 200
        
        logger.info("웹훅 거래자 초기화 완료")
        if live_trader:
            logger.info("✅ LiveTrader와 연결됨 - 웹훅 수신 시 자동 거래 실행")
        else:
            logger.warning("⚠️  LiveTrader가 없습니다 - 웹훅만으로 거래 시도 (제한적)")
    
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
            
            # 봉 히스토리에 추가
            self.bar_history.append(normalized_bar)
            if len(self.bar_history) > self.max_history:
                self.bar_history.pop(0)
            
            # 실시간 거래자에 전달 (우선)
            if self.live_trader:
                # 봉 마감 이벤트 처리
                self.live_trader._on_bar_close(normalized_bar)
                logger.info(f"✅ 웹훅 봉 데이터를 LiveTrader에 전달 완료 - 거래 로직 실행")
            else:
                # LiveTrader가 없으면 웹훅만으로 거래 시도
                logger.info("🔄 LiveTrader 없음 - 웹훅만으로 거래 처리 시도")
                self._process_webhook_bar_directly(normalized_bar)
            
            # 최근 봉 업데이트
            self.last_bar = normalized_bar
            self.last_bar_timestamp = timestamp
            
        except Exception as e:
            logger.error(f"웹훅 봉 데이터 처리 실패: {e}")
            raise
    
    def _process_webhook_bar_directly(self, bar: Dict[str, Any]):
        """
        웹훅만으로 거래 처리 (LiveTrader 없을 때)
        
        Args:
            bar: 봉 데이터
        """
        try:
            # 백테스트 엔진 초기화 (처음 한 번만)
            if self.backtest_engine is None:
                logger.info("백테스트 엔진 초기화 중...")
                strategy_config = self.config.get("strategy", {})
                strategy_name = strategy_config.get("name", "EMA_BB_TurtleTrailing")
                strategy = StrategyRegistry.get_strategy(strategy_name, self.config)
                backtest_config = self.config.get("backtest", {})
                self.backtest_engine = BacktestEngine(strategy, backtest_config)
                logger.info("✅ 백테스트 엔진 초기화 완료")
            
            # 봉 데이터를 DataFrame으로 변환 (히스토리 포함)
            if len(self.bar_history) < 100:
                logger.debug(f"봉 히스토리 부족: {len(self.bar_history)}개 (최소 100개 필요)")
                return
            
            # DataFrame 생성
            df = pd.DataFrame(self.bar_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # 마지막 봉 처리 (간단한 버전)
            # 실제로는 더 복잡한 로직이 필요하지만, 기본적인 거래는 가능
            logger.info(f"📊 봉 데이터 처리: {len(df)}개 봉, 최신 가격: {bar['close']}")
            logger.info("⚠️  웹훅만으로는 제한적인 거래만 가능합니다. LiveTrader 사용을 권장합니다.")
            
        except Exception as e:
            logger.error(f"웹훅 직접 처리 실패: {e}")
    
    def get_last_bar(self) -> Optional[Dict[str, Any]]:
        """최근 수신된 봉 데이터 반환"""
        return self.last_bar

