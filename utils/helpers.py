"""공통 헬퍼 함수"""

from typing import Any, Dict, Optional
from pathlib import Path
import yaml
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    YAML 파일 로드
    
    Args:
        file_path: YAML 파일 경로
        
    Returns:
        설정 딕셔너리
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    logger.debug(f"YAML 파일 로드 완료: {file_path}")
    return config


def save_yaml(data: Dict[str, Any], file_path: str) -> None:
    """
    YAML 파일 저장
    
    Args:
        data: 저장할 데이터
        file_path: 저장할 파일 경로
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    logger.debug(f"YAML 파일 저장 완료: {file_path}")


def format_number(value: float, decimals: int = 2, percentage: bool = False) -> str:
    """
    숫자 포맷팅
    
    Args:
        value: 포맷팅할 숫자
        decimals: 소수점 자릿수
        percentage: 퍼센트 형식 여부
        
    Returns:
        포맷팅된 문자열
    """
    if percentage:
        return f"{value * 100:.{decimals}f}%"
    return f"{value:.{decimals}f}"


def parse_timestamp(timestamp: Any, format: Optional[str] = None) -> pd.Timestamp:
    """
    타임스탬프 파싱
    
    Args:
        timestamp: 파싱할 타임스탬프
        format: 날짜 형식 (None이면 자동 감지)
        
    Returns:
        pandas Timestamp
    """
    if isinstance(timestamp, pd.Timestamp):
        return timestamp
    
    if format:
        return pd.to_datetime(timestamp, format=format)
    else:
        return pd.to_datetime(timestamp)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    안전한 나눗셈 (0으로 나누기 방지)
    
    Args:
        numerator: 분자
        denominator: 분모
        default: 분모가 0일 때 반환할 기본값
        
    Returns:
        나눗셈 결과
    """
    if denominator == 0:
        return default
    return numerator / denominator

