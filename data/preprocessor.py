"""데이터 전처리 모듈"""

import pandas as pd
from typing import Dict, Any, Optional, List
from utils.logger import get_logger
from utils.validators import validate_data

logger = get_logger(__name__)


class DataPreprocessor:
    """데이터 전처리 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        전처리기 초기화
        
        Args:
            config: 전처리 설정
        """
        self.config = config
        self.validation_config = config.get("validation", {})
        logger.info("데이터 전처리기 초기화 완료")
    
    def preprocess(
        self,
        df: pd.DataFrame,
        required_columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        데이터 전처리 수행
        
        Args:
            df: 원본 데이터프레임
            required_columns: 필수 컬럼 목록
            
        Returns:
            전처리된 데이터프레임
        """
        if required_columns is None:
            required_columns = ["open", "high", "low", "close", "volume"]
        
        # 타임스탬프 인덱스 설정
        if "timestamp" in df.columns:
            df = df.set_index("timestamp")
            df.index = pd.to_datetime(df.index)
        
        # 타임스탬프로 정렬
        if not df.index.is_monotonic_increasing:
            df = df.sort_index()
            logger.debug("타임스탬프로 정렬 완료")
        
        # 결측치 처리
        if self.validation_config.get("check_missing", True):
            df = self._handle_missing(df, required_columns)
        
        # 중복 제거
        if df.duplicated().any():
            original_len = len(df)
            df = df.drop_duplicates()
            logger.info(f"중복 제거: {original_len} -> {len(df)}행")
        
        # 데이터 검증
        validate_data(
            df.reset_index(),
            required_columns=required_columns,
            check_missing=False,  # 이미 처리함
            check_duplicates=False,  # 이미 처리함
            check_time_order=False,  # 이미 정렬함
        )
        
        logger.info(f"전처리 완료: {len(df)}행, {len(df.columns)}컬럼")
        return df
    
    def _handle_missing(self, df: pd.DataFrame, required_columns: List[str]) -> pd.DataFrame:
        """
        결측치 처리
        
        Args:
            df: 데이터프레임
            required_columns: 필수 컬럼 목록
            
        Returns:
            결측치 처리된 데이터프레임
        """
        fill_method = self.validation_config.get("fill_method", "ffill")
        missing_count = df[required_columns].isnull().sum().sum()
        
        if missing_count == 0:
            return df
        
        logger.warning(f"결측치 발견: {missing_count}개")
        
        if fill_method == "ffill":
            df[required_columns] = df[required_columns].fillna(method="ffill")
            logger.debug("Forward fill 적용")
        elif fill_method == "bfill":
            df[required_columns] = df[required_columns].fillna(method="bfill")
            logger.debug("Backward fill 적용")
        elif fill_method == "interpolate":
            df[required_columns] = df[required_columns].interpolate(method="linear")
            logger.debug("Interpolation 적용")
        elif fill_method == "drop":
            df = df.dropna(subset=required_columns)
            logger.debug("결측치 행 삭제")
        else:
            logger.warning(f"알 수 없는 fill_method: {fill_method}, ffill 사용")
            df[required_columns] = df[required_columns].fillna(method="ffill")
        
        remaining_missing = df[required_columns].isnull().sum().sum()
        if remaining_missing > 0:
            logger.warning(f"처리 후 남은 결측치: {remaining_missing}개")
        
        return df
    
    def resample(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        데이터 리샘플링
        
        Args:
            df: 데이터프레임
            timeframe: 목표 타임프레임 (예: "5m", "1h", "1d")
            
        Returns:
            리샘플링된 데이터프레임
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("인덱스가 DatetimeIndex가 아닙니다.")
        
        # OHLCV 집계 규칙
        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
        
        # 기존 컬럼 중 집계 가능한 것만 선택
        available_cols = {k: v for k, v in agg_dict.items() if k in df.columns}
        
        if not available_cols:
            raise ValueError("집계 가능한 컬럼이 없습니다.")
        
        resampled = df.resample(timeframe).agg(available_cols)
        resampled = resampled.dropna()
        
        logger.info(f"리샘플링 완료: {timeframe}, {len(df)} -> {len(resampled)}행")
        return resampled

