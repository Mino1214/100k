"""로깅 유틸리티 모듈"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    error_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> None:
    """
    로거 설정
    
    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 일반 로그 파일 경로
        error_file: 에러 로그 파일 경로
        rotation: 로그 파일 로테이션 크기
        retention: 로그 파일 보관 기간
    """
    # 기본 로거 제거
    logger.remove()
    
    # 콘솔 핸들러 추가
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=log_level,
        colorize=True,
    )
    
    # 파일 핸들러 추가
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
        )
    
    # 에러 파일 핸들러 추가
    if error_file:
        error_path = Path(error_file)
        error_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            error_file,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="ERROR",
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
        )


def get_logger(name: str = __name__):
    """
    로거 인스턴스 반환
    
    Args:
        name: 로거 이름
        
    Returns:
        로거 인스턴스
    """
    return logger.bind(name=name)

