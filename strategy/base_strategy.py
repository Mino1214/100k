"""전략 베이스 클래스"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)


class Regime(Enum):
    """시장 레짐"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"


class SignalType(Enum):
    """시그널 타입"""
    LONG_ENTRY = "long_entry"
    SHORT_ENTRY = "short_entry"
    LONG_EXIT = "long_exit"
    SHORT_EXIT = "short_exit"
    NO_ACTION = "no_action"


@dataclass
class Signal:
    """시그널 데이터 클래스"""
    type: SignalType
    price: float
    timestamp: pd.Timestamp
    regime: Regime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Optional[Dict] = None


@dataclass
class Position:
    """포지션 데이터 클래스"""
    entry_price: float
    entry_time: pd.Timestamp
    direction: str  # "long" or "short"
    quantity: float
    stop_loss: float
    regime_at_entry: Regime
    metadata: Optional[Dict] = None


class BaseStrategy(ABC):
    """전략 기본 추상 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        전략 초기화
        
        Args:
            config: 전략 설정
        """
        self.config = config
        self.name = config.get("name", "UnnamedStrategy")
        self.version = config.get("version", "1.0")
        logger.info(f"전략 초기화: {self.name} v{self.version}")
    
    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        지표 계산
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            지표가 추가된 데이터프레임
        """
        pass
    
    @abstractmethod
    def detect_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        레짐 탐지
        
        Args:
            df: 지표가 포함된 데이터프레임
            
        Returns:
            레짐 시리즈 (각 바별 레짐)
        """
        pass
    
    @abstractmethod
    def generate_entry_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        current_position: Optional[Position],
    ) -> Signal:
        """
        진입 시그널 생성
        
        Args:
            df: 지표가 포함된 데이터프레임
            idx: 현재 인덱스
            current_position: 현재 포지션 (없으면 None)
            
        Returns:
            진입 시그널
        """
        pass
    
    @abstractmethod
    def generate_exit_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        position: Position,
    ) -> Signal:
        """
        청산 시그널 생성
        
        Args:
            df: 지표가 포함된 데이터프레임
            idx: 현재 인덱스
            position: 현재 포지션
            
        Returns:
            청산 시그널
        """
        pass
    
    @abstractmethod
    def update_stop_loss(
        self,
        df: pd.DataFrame,
        idx: int,
        position: Position,
    ) -> float:
        """
        트레일링 스탑 업데이트
        
        Args:
            df: 지표가 포함된 데이터프레임
            idx: 현재 인덱스
            position: 현재 포지션
            
        Returns:
            업데이트된 스탑로스 가격
        """
        pass
    
    def validate_config(self) -> bool:
        """
        설정 검증
        
        Returns:
            검증 성공 여부
        """
        strategy_config = self.config.get("strategy", {})
        required_keys = ["entry", "exit"]
        missing_keys = [key for key in required_keys if key not in strategy_config]
        
        if missing_keys:
            raise ValueError(f"필수 설정 키가 없습니다: {missing_keys}")
        
        return True

