"""실시간 데이터 피드 모듈"""

import asyncio
import ccxt
import time
from typing import Callable, Optional, Dict, Any
from datetime import datetime
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)


class RealtimeFeed:
    """실시간 데이터 피드 클래스 (확장용)"""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        exchange_name: Optional[str] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        callback: Optional[Callable] = None,
    ):
        """
        실시간 피드 초기화
        
        Args:
            config: 데이터 설정 (우선 사용)
            exchange_name: 거래소 이름 (config가 없을 때)
            symbol: 거래 심볼 (config가 없을 때)
            timeframe: 타임프레임 (config가 없을 때)
            callback: 데이터 수신 콜백 함수
        """
        if config:
            api_config = config.get("api", {})
            self.exchange_name = api_config.get("exchange", "binance")
            self.symbol = config.get("symbol", "BTCUSDT")
            self.timeframe = config.get("timeframe", "1m")
        else:
            self.exchange_name = exchange_name or "binance"
            self.symbol = symbol or "BTCUSDT"
            self.timeframe = timeframe or "1m"
        
        self.callback = callback
        self.on_bar_close: Optional[Callable] = None  # 봉 마감 콜백
        
        # Exchange 초기화
        exchange_class = getattr(ccxt, self.exchange_name)
        self.exchange = exchange_class({
            "enableRateLimit": True,
        })
        
        self.running = False
        self.latest_bar: Optional[Dict[str, Any]] = None
        self.last_bar_timestamp: Optional[datetime] = None
        
        logger.info(f"실시간 피드 초기화: {self.exchange_name}, {self.symbol}, {self.timeframe}")
    
    def start(self):
        """실시간 피드 시작 (동기 버전)"""
        self.running = True
        logger.info("실시간 피드 시작")
        
        # 별도 스레드에서 실행
        import threading
        self.thread = threading.Thread(target=self._feed_loop, daemon=True)
        self.thread.start()
    
    def _feed_loop(self):
        """피드 루프 (별도 스레드에서 실행)"""
        while self.running:
            try:
                # 최신 OHLCV 데이터 가져오기
                ohlcv = self.exchange.fetch_ohlcv(
                    self.symbol,
                    self.timeframe,
                    limit=2,  # 이전 봉과 현재 봉 비교용
                )
                
                if ohlcv and len(ohlcv) >= 1:
                    # 데이터프레임으로 변환
                    df = pd.DataFrame(
                        ohlcv,
                        columns=["timestamp", "open", "high", "low", "close", "volume"],
                    )
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    
                    latest_bar = df.iloc[-1].to_dict()
                    latest_bar["timestamp"] = df.iloc[-1]["timestamp"]
                    
                    # 봉 마감 감지 (이전 봉과 타임스탬프 비교)
                    current_timestamp = latest_bar["timestamp"]
                    
                    if self.last_bar_timestamp is None:
                        self.last_bar_timestamp = current_timestamp
                    elif current_timestamp > self.last_bar_timestamp:
                        # 새 봉 시작 = 이전 봉 마감
                        if len(ohlcv) >= 2:
                            prev_bar = df.iloc[-2].to_dict()
                            prev_bar["timestamp"] = df.iloc[-2]["timestamp"]
                            
                            # 봉 마감 이벤트 호출
                            if self.on_bar_close:
                                self.on_bar_close(prev_bar)
                        
                        self.last_bar_timestamp = current_timestamp
                    
                    # 최신 봉 저장
                    self.latest_bar = latest_bar
                    
                    # 일반 콜백 호출
                    if self.callback:
                        self.callback(latest_bar)
                
                # 타임프레임에 따라 대기
                time.sleep(self._get_sleep_seconds())
                
            except Exception as e:
                logger.error(f"실시간 피드 에러: {e}")
                time.sleep(5)
    
    async def start_async(self):
        """실시간 피드 시작 (비동기 버전)"""
        self.running = True
        logger.info("실시간 피드 시작 (비동기)")
        
        while self.running:
            try:
                # 최신 OHLCV 데이터 가져오기
                ohlcv = self.exchange.fetch_ohlcv(
                    self.symbol,
                    self.timeframe,
                    limit=1,
                )
                
                if ohlcv:
                    # 데이터프레임으로 변환
                    df = pd.DataFrame(
                        ohlcv,
                        columns=["timestamp", "open", "high", "low", "close", "volume"],
                    )
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    
                    latest_bar = df.iloc[-1].to_dict()
                    latest_bar["timestamp"] = df.iloc[-1]["timestamp"]
                    self.latest_bar = latest_bar
                    
                    # 콜백 호출
                    if self.callback:
                        self.callback(latest_bar)
                
                # 타임프레임에 따라 대기
                await asyncio.sleep(self._get_sleep_seconds())
                
            except Exception as e:
                logger.error(f"실시간 피드 에러: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """실시간 피드 중지"""
        self.running = False
        logger.info("실시간 피드 중지")
    
    def _get_sleep_seconds(self) -> int:
        """타임프레임에 따른 대기 시간 계산"""
        timeframe_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "1d": 86400,
        }
        return timeframe_map.get(self.timeframe, 60)
    
    def get_latest_bar(self) -> Optional[Dict[str, Any]]:
        """최신 봉 데이터 가져오기"""
        return self.latest_bar

