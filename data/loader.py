"""데이터 로더 모듈"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
import ccxt
from sqlalchemy import create_engine, text
from utils.logger import get_logger
from data.cache_manager import CacheManager
from data.preprocessor import DataPreprocessor

logger = get_logger(__name__)


class DataLoader:
    """데이터 로더 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        데이터 로더 초기화
        
        Args:
            config: 데이터 설정
        """
        self.config = config
        self.source = config.get("source", "csv")
        self.symbol = config.get("symbol", "BTCUSDT")
        self.timeframe = config.get("timeframe", "1m")
        
        # 캐시 관리자
        cache_config = config.get("cache", {})
        if cache_config.get("enabled", True):
            self.cache = CacheManager(
                cache_dir=cache_config.get("path", "./data/cache/"),
                expiry_hours=cache_config.get("expiry_hours", 24),
            )
        else:
            self.cache = None
        
        # 전처리기
        self.preprocessor = DataPreprocessor(config)
        
        logger.info(f"데이터 로더 초기화: source={self.source}, symbol={self.symbol}")
    
    def load(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        데이터 로드
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            use_cache: 캐시 사용 여부
            
        Returns:
            로드된 데이터프레임
        """
        # 캐시 키 생성
        cache_key = f"{self.source}_{self.symbol}_{self.timeframe}_{start_date}_{end_date}"
        
        # 캐시에서 가져오기
        if use_cache and self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.info("캐시에서 데이터 로드 완료")
                return cached_data
        
        # 소스별 로드
        if self.source == "csv":
            df = self._load_from_csv(start_date, end_date)
        elif self.source == "binance_api":
            df = self._load_from_binance(start_date, end_date)
        elif self.source == "database":
            df = self._load_from_database(start_date, end_date)
        else:
            raise ValueError(f"지원하지 않는 데이터 소스: {self.source}")
        
        # 전처리
        df = self.preprocessor.preprocess(df)
        
        # 날짜 필터링
        if start_date or end_date:
            df = self._filter_by_date(df, start_date, end_date)
        
        # 캐시에 저장
        if use_cache and self.cache:
            self.cache.set(cache_key, df)
        
        logger.info(f"데이터 로드 완료: {len(df)}행")
        return df
    
    def _load_from_csv(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        CSV 파일에서 데이터 로드
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            데이터프레임
        """
        csv_config = self.config.get("csv", {})
        csv_path = Path(csv_config.get("path", f"./data/raw/{self.symbol}_{self.timeframe}.csv"))
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
        
        date_column = csv_config.get("date_column", "timestamp")
        date_format = csv_config.get("date_format", "%Y-%m-%d %H:%M:%S")
        
        logger.info(f"CSV 파일 로드: {csv_path}")
        
        # CSV 읽기
        df = pd.read_csv(csv_path)
        
        # 타임스탬프 컬럼 설정
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column], format=date_format)
        
        return df
    
    def _load_from_binance(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Binance API에서 데이터 로드
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            데이터프레임
        """
        api_config = self.config.get("api", {})
        exchange_name = api_config.get("exchange", "binance")
        rate_limit = api_config.get("rate_limit", 1200)
        
        logger.info(f"Binance API에서 데이터 로드: {self.symbol}")
        
        # Exchange 초기화
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            "rateLimit": 60000 / rate_limit,  # ms per request
            "enableRateLimit": True,
        })
        
        # 날짜 변환
        since = None
        if start_date:
            since = int(pd.to_datetime(start_date).timestamp() * 1000)
        
        # OHLCV 데이터 가져오기
        ohlcv = exchange.fetch_ohlcv(
            self.symbol,
            self.timeframe,
            since=since,
            limit=None,
        )
        
        # 데이터프레임 생성
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        
        # 종료 날짜 필터링
        if end_date:
            end_ts = pd.to_datetime(end_date)
            df = df[df["timestamp"] <= end_ts]
        
        logger.info(f"Binance API에서 {len(df)}행 로드 완료")
        return df
    
    def _load_from_database(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        데이터베이스에서 데이터 로드
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            데이터프레임
        """
        db_config = self.config.get("database", {})
        connection_string = db_config.get("connection_string")
        
        if not connection_string:
            raise ValueError("데이터베이스 connection_string이 설정되지 않았습니다.")
        
        logger.info(f"데이터베이스에서 데이터 로드: {self.symbol}")
        
        # 엔진 생성
        engine = create_engine(connection_string)
        
        # 쿼리 구성
        table_name = db_config.get("table_name", "ohlcv_data")
        timestamp_column = db_config.get("timestamp_column", "timestamp")
        
        # 테이블 구조에 따라 쿼리 조정
        # ETHUSDT1m 테이블은 이미 특정 심볼/타임프레임이므로 WHERE 절에서 제외
        query = f"""
        SELECT {timestamp_column} as timestamp, open, high, low, close, volume
        FROM {table_name}
        WHERE 1=1
        """
        params = {}
        
        if start_date:
            query += f" AND {timestamp_column} >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            query += f" AND {timestamp_column} <= :end_date"
            params["end_date"] = end_date
        
        query += f" ORDER BY {timestamp_column}"
        
        # 데이터 로드
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        logger.info(f"데이터베이스에서 {len(df)}행 로드 완료")
        return df
    
    def _filter_by_date(
        self,
        df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        날짜로 데이터 필터링
        
        Args:
            df: 데이터프레임
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            필터링된 데이터프레임
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            if "timestamp" in df.columns:
                df = df.set_index("timestamp")
            else:
                logger.warning("날짜 인덱스가 없어 필터링을 건너뜁니다.")
                return df
        
        if start_date:
            start_ts = pd.to_datetime(start_date)
            df = df[df.index >= start_ts]
        
        if end_date:
            end_ts = pd.to_datetime(end_date)
            df = df[df.index <= end_ts]
        
        return df
    
    def generate_sample_data(
        self,
        start_date: str = "2024-01-01",
        end_date: str = "2024-12-31",
        initial_price: float = 50000.0,
    ) -> pd.DataFrame:
        """
        샘플 데이터 생성 (테스트용)
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            initial_price: 초기 가격
            
        Returns:
            샘플 데이터프레임
        """
        logger.info("샘플 데이터 생성 중...")
        
        # 타임스탬프 생성 (1분 간격)
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        timestamps = pd.date_range(start, end, freq="1min")
        
        # 랜덤 워크로 가격 생성
        np.random.seed(42)
        returns = np.random.normal(0, 0.001, len(timestamps))  # 0.1% 변동성
        prices = initial_price * np.exp(np.cumsum(returns))
        
        # OHLCV 생성
        data = []
        for i, (ts, close) in enumerate(zip(timestamps, prices)):
            # 간단한 OHLC 생성
            high = close * (1 + abs(np.random.normal(0, 0.002)))
            low = close * (1 - abs(np.random.normal(0, 0.002)))
            open_price = prices[i - 1] if i > 0 else close
            volume = np.random.uniform(100, 1000)
            
            data.append({
                "timestamp": ts,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            })
        
        df = pd.DataFrame(data)
        df = df.set_index("timestamp")
        
        logger.info(f"샘플 데이터 생성 완료: {len(df)}행")
        return df

