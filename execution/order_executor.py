"""주문 실행 시뮬레이터 모듈"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from utils.logger import get_logger
from execution.slippage_model import SlippageModel

logger = get_logger(__name__)


@dataclass
class Order:
    """주문 데이터 클래스"""
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    order_type: str  # "market" or "limit"
    limit_price: Optional[float] = None
    timestamp: Optional[Any] = None


@dataclass
class Fill:
    """체결 데이터 클래스"""
    order: Order
    fill_price: float
    fill_quantity: float
    commission: float
    slippage: float
    timestamp: Any


class OrderExecutor:
    """주문 실행 시뮬레이터 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        주문 실행자 초기화
        
        Args:
            config: 실행 설정
        """
        self.config = config
        self.commission_config = config.get("commission", {})
        self.order_config = config.get("order", {})
        
        # 슬리피지 모델
        slippage_config = config.get("slippage", {})
        self.slippage_model = SlippageModel(slippage_config)
        
        logger.info("주문 실행자 초기화 완료")
    
    def execute_order(
        self,
        order: Order,
        current_price: float,
        volume: Optional[float] = None,
    ) -> Fill:
        """
        주문 실행
        
        Args:
            order: 실행할 주문
            current_price: 현재 가격
            volume: 거래량 (슬리피지 계산용)
            
        Returns:
            체결 정보
        """
        # 주문 타입에 따른 가격 결정
        if order.order_type == "market":
            fill_price = current_price
        elif order.order_type == "limit":
            if order.limit_price is None:
                raise ValueError("Limit 주문에는 limit_price가 필요합니다.")
            fill_price = order.limit_price
        else:
            raise ValueError(f"알 수 없는 주문 타입: {order.order_type}")
        
        # 슬리피지 적용
        slippage = self.slippage_model.calculate_slippage(
            fill_price,
            order.quantity,
            order.side,
            volume,
        )
        
        if order.side == "buy":
            fill_price += slippage
        else:  # sell
            fill_price -= slippage
        
        # 수수료 계산
        commission = self._calculate_commission(fill_price * order.quantity)
        
        fill = Fill(
            order=order,
            fill_price=fill_price,
            fill_quantity=order.quantity,
            commission=commission,
            slippage=slippage,
            timestamp=order.timestamp,
        )
        
        logger.debug(
            f"주문 체결: {order.side} {order.quantity} @ {fill_price:.2f}, "
            f"수수료: {commission:.4f}, 슬리피지: {slippage:.4f}"
        )
        
        return fill
    
    def _calculate_commission(self, trade_value: float) -> float:
        """
        수수료 계산
        
        Args:
            trade_value: 거래 금액
            
        Returns:
            수수료 금액
        """
        commission_type = self.commission_config.get("type", "percentage")
        
        if commission_type == "percentage":
            # Market 주문은 taker 수수료
            commission_rate = self.commission_config.get("taker", 0.0004)
            return trade_value * commission_rate
        elif commission_type == "fixed":
            return self.commission_config.get("fixed", 0.0)
        else:
            raise ValueError(f"알 수 없는 수수료 타입: {commission_type}")

