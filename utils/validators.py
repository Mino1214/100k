"""설정 및 데이터 검증 유틸리티"""

from typing import Dict, Any, List, Optional
import pandas as pd
from pydantic import BaseModel, ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)


class DataConfig(BaseModel):
    """데이터 설정 스키마"""
    source: str
    symbol: str
    timeframe: str
    csv: Optional[Dict[str, Any]] = None
    api: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    cache: Optional[Dict[str, Any]] = None


class StrategyConfig(BaseModel):
    """전략 설정 스키마"""
    name: str
    version: str
    entry: Dict[str, Any]
    exit: Dict[str, Any]


def validate_config(config: Dict[str, Any]) -> bool:
    """
    설정 파일 검증
    
    Args:
        config: 설정 딕셔너리
        
    Returns:
        검증 성공 여부
        
    Raises:
        ValidationError: 설정 검증 실패 시
    """
    try:
        # 필수 섹션 확인
        required_sections = ["data", "strategy", "backtest"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"필수 섹션 '{section}'이(가) 없습니다.")
        
        # 데이터 설정 검증
        if "data" in config:
            DataConfig(**config["data"])
        
        # 전략 설정 검증
        if "strategy" in config:
            StrategyConfig(**config["strategy"])
        
        logger.info("설정 파일 검증 완료")
        return True
        
    except ValidationError as e:
        logger.error(f"설정 검증 실패: {e}")
        raise
    except ValueError as e:
        logger.error(f"설정 검증 실패: {e}")
        raise


def validate_data(
    df: pd.DataFrame,
    required_columns: List[str] = None,
    check_missing: bool = True,
    check_duplicates: bool = True,
    check_time_order: bool = True,
) -> bool:
    """
    데이터프레임 검증
    
    Args:
        df: 검증할 데이터프레임
        required_columns: 필수 컬럼 목록
        check_missing: 결측치 확인 여부
        check_duplicates: 중복 확인 여부
        check_time_order: 시간 순서 확인 여부
        
    Returns:
        검증 성공 여부
        
    Raises:
        ValueError: 검증 실패 시
    """
    if required_columns is None:
        required_columns = ["open", "high", "low", "close", "volume"]
    
    # 필수 컬럼 확인
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    # 결측치 확인
    if check_missing:
        missing_count = df[required_columns].isnull().sum().sum()
        if missing_count > 0:
            logger.warning(f"결측치 발견: {missing_count}개")
            # 결측치가 있는 행 출력
            missing_rows = df[df[required_columns].isnull().any(axis=1)]
            logger.debug(f"결측치가 있는 행:\n{missing_rows}")
    
    # 중복 확인
    if check_duplicates:
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            logger.warning(f"중복 행 발견: {duplicates}개")
    
    # 시간 순서 확인
    if check_time_order and "timestamp" in df.columns:
        if not df["timestamp"].is_monotonic_increasing:
            logger.warning("타임스탬프가 시간 순서대로 정렬되지 않았습니다.")
    
    logger.info(f"데이터 검증 완료: {len(df)}행, {len(df.columns)}컬럼")
    return True

