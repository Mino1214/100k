"""슬리피지 모델 모듈"""

from typing import Dict, Any, Optional
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


class SlippageModel:
    """슬리피지 모델 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        슬리피지 모델 초기화
        
        Args:
            config: 슬리피지 설정
        """
        self.config = config
        self.model = config.get("model", "fixed_pct")
        logger.info(f"슬리피지 모델 초기화: {self.model}")
    
    def calculate_slippage(
        self,
        price: float,
        quantity: float,
        side: str,
        volume: Optional[float] = None,
    ) -> float:
        """
        슬리피지 계산
        
        Args:
            price: 주문 가격
            quantity: 주문 수량
            side: 주문 방향 (buy/sell)
            volume: 거래량 (volume_based 모델용)
            
        Returns:
            슬리피지 금액
        """
        if self.model == "none":
            return 0.0
        elif self.model == "fixed_pct":
            return self._calculate_fixed_pct(price)
        elif self.model == "volume_based":
            return self._calculate_volume_based(price, quantity, volume)
        elif self.model == "historical":
            return self._calculate_historical(price, quantity, side)
        else:
            logger.warning(f"알 수 없는 슬리피지 모델: {self.model}, fixed_pct 사용")
            return self._calculate_fixed_pct(price)
    
    def _calculate_fixed_pct(self, price: float) -> float:
        """고정 퍼센트 슬리피지"""
        fixed_pct = self.config.get("fixed_pct", 0.0001)
        return price * fixed_pct
    
    def _calculate_volume_based(
        self,
        price: float,
        quantity: float,
        volume: Optional[float],
    ) -> float:
        """거래량 기반 슬리피지"""
        if volume is None or volume == 0:
            return self._calculate_fixed_pct(price)
        
        base_slippage = self.config.get("volume_based", {}).get("base_slippage", 0.0001)
        volume_impact = self.config.get("volume_based", {}).get("volume_impact", 0.00001)
        
        # 거래량 비율에 따른 슬리피지 증가
        volume_ratio = quantity / volume
        slippage_pct = base_slippage + (volume_ratio * volume_impact)
        
        return price * slippage_pct
    
    def _calculate_historical(
        self,
        price: float,
        quantity: float,
        side: str,
    ) -> float:
        """과거 데이터 기반 슬리피지 (간단한 구현)"""
        # 실제로는 과거 거래 데이터를 분석하여 계산
        # 여기서는 fixed_pct 사용
        return self._calculate_fixed_pct(price)

