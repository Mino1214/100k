"""전략 레지스트리 모듈"""

from typing import Dict, Type, Any
from strategy.base_strategy import BaseStrategy
from strategy.ema_bb_turtle import EMABBTurtleStrategy
from utils.logger import get_logger

logger = get_logger(__name__)


class StrategyRegistry:
    """전략 레지스트리 클래스"""
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: Type[BaseStrategy]):
        """
        전략 등록
        
        Args:
            name: 전략 이름
            strategy_class: 전략 클래스
        """
        cls._strategies[name] = strategy_class
        logger.info(f"전략 등록: {name}")
    
    @classmethod
    def get_strategy(cls, name: str, config: Dict[str, Any]) -> BaseStrategy:
        """
        전략 인스턴스 생성
        
        Args:
            name: 전략 이름
            config: 전략 설정
            
        Returns:
            전략 인스턴스
        """
        if name not in cls._strategies:
            raise ValueError(f"등록되지 않은 전략: {name}")
        
        strategy_class = cls._strategies[name]
        return strategy_class(config)
    
    @classmethod
    def list_strategies(cls) -> list:
        """
        등록된 전략 목록 반환
        
        Returns:
            전략 이름 목록
        """
        return list(cls._strategies.keys())


# 기본 전략 등록
StrategyRegistry.register("EMA_BB_TurtleTrailing", EMABBTurtleStrategy)

