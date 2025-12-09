"""스마트 청산 모듈 - 수익 극대화 및 손실 최소화"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
from strategy.base_strategy import Position
from utils.logger import get_logger

logger = get_logger(__name__)


class SmartExit:
    """스마트 청산 클래스 - 수익 극대화"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        스마트 청산 초기화
        
        Args:
            config: 청산 설정
        """
        self.config = config
        exit_config = config.get("strategy", {}).get("exit", {})
        
        # 트레일링 스탑 설정
        trailing_config = exit_config.get("trailing_stop", {})
        self.use_trailing_stop = trailing_config.get("enabled", True)
        self.trailing_activation = trailing_config.get("activation_pct", 0.02)  # 2% 수익 시 활성화
        self.trailing_distance = trailing_config.get("distance_pct", 0.01)  # 1% 거리
        
        # 부분 청산 설정
        partial_exit_config = exit_config.get("partial_exit", {})
        self.use_partial_exit = partial_exit_config.get("enabled", True)
        self.partial_exit_levels = partial_exit_config.get("levels", [
            {"profit_pct": 0.03, "exit_pct": 0.5},  # 3% 수익 시 50% 청산
            {"profit_pct": 0.05, "exit_pct": 0.3},  # 5% 수익 시 30% 청산
        ])
        
        # 시간 기반 청산
        time_exit_config = exit_config.get("time_exit", {})
        self.max_hold_hours = time_exit_config.get("max_hours", 24)
        
        logger.info("스마트 청산 초기화 완료")
        logger.info(f"트레일링 스탑: {self.use_trailing_stop}")
        logger.info(f"부분 청산: {self.use_partial_exit}")
    
    def calculate_trailing_stop(
        self,
        position: Position,
        current_price: float,
        atr_value: float,
    ) -> float:
        """
        트레일링 스탑 계산
        
        Args:
            position: 현재 포지션
            current_price: 현재 가격
            atr_value: ATR 값
            
        Returns:
            새로운 스탑로스 가격
        """
        if not self.use_trailing_stop:
            return position.stop_loss
        
        # 수익률 계산
        if position.direction == "long":
            profit_pct = (current_price - position.entry_price) / position.entry_price
        else:
            profit_pct = (position.entry_price - current_price) / position.entry_price
        
        # 트레일링 스탑 활성화 확인
        if profit_pct < self.trailing_activation:
            return position.stop_loss  # 아직 활성화 안 됨
        
        # 트레일링 스탑 계산
        if position.direction == "long":
            # Long: 현재 가격에서 trailing_distance만큼 아래
            new_stop = current_price * (1 - self.trailing_distance)
            # 기존 스탑로스보다 높아야 함 (손실 방지)
            return max(new_stop, position.stop_loss)
        else:
            # Short: 현재 가격에서 trailing_distance만큼 위
            new_stop = current_price * (1 + self.trailing_distance)
            # 기존 스탑로스보다 낮아야 함 (손실 방지)
            return min(new_stop, position.stop_loss)
    
    def check_partial_exit(
        self,
        position: Position,
        current_price: float,
    ) -> tuple[bool, float]:
        """
        부분 청산 확인
        
        Args:
            position: 현재 포지션
            current_price: 현재 가격
            
        Returns:
            (부분 청산 필요 여부, 청산 비율)
        """
        if not self.use_partial_exit:
            return False, 0.0
        
        # 수익률 계산
        if position.direction == "long":
            profit_pct = (current_price - position.entry_price) / position.entry_price
        else:
            profit_pct = (position.entry_price - current_price) / position.entry_price
        
        # 부분 청산 레벨 확인
        for level in self.partial_exit_levels:
            if profit_pct >= level["profit_pct"]:
                # 이미 부분 청산했는지 확인 (메타데이터에 기록)
                if not hasattr(position, 'metadata'):
                    position.metadata = {}
                
                level_key = f"partial_exit_{level['profit_pct']}"
                if not position.metadata.get(level_key, False):
                    position.metadata[level_key] = True
                    return True, level["exit_pct"]
        
        return False, 0.0
    
    def should_take_profit(
        self,
        position: Position,
        current_price: float,
        atr_value: float,
    ) -> tuple[bool, str]:
        """
        익절 확인
        
        Args:
            position: 현재 포지션
            current_price: 현재 가격
            atr_value: ATR 값
            
        Returns:
            (익절 필요 여부, 이유)
        """
        # 수익률 계산
        if position.direction == "long":
            profit_pct = (current_price - position.entry_price) / position.entry_price
        else:
            profit_pct = (position.entry_price - current_price) / position.entry_price
        
        # 익절 레벨 확인 (ATR 기반)
        take_profit_atr_multiplier = 3.0  # 3 ATR = 익절
        take_profit_pct = (atr_value * take_profit_atr_multiplier) / position.entry_price
        
        if profit_pct >= take_profit_pct:
            return True, f"익절 레벨 도달: {profit_pct:.2%} >= {take_profit_pct:.2%}"
        
        # 고정 익절 레벨 (5%)
        if profit_pct >= 0.05:
            return True, f"고정 익절 레벨 도달: {profit_pct:.2%}"
        
        return False, "OK"
    
    def should_cut_loss_early(
        self,
        position: Position,
        current_price: float,
        entry_time: datetime,
        current_time: datetime,
    ) -> tuple[bool, str]:
        """
        조기 손절 확인 (시간 기반)
        
        Args:
            position: 현재 포지션
            current_price: 현재 가격
            entry_time: 진입 시간
            current_time: 현재 시간
            
        Returns:
            (조기 손절 필요 여부, 이유)
        """
        # 보유 시간
        hold_duration = (current_time - entry_time).total_seconds() / 3600  # 시간
        
        # 수익률 계산
        if position.direction == "long":
            profit_pct = (current_price - position.entry_price) / position.entry_price
        else:
            profit_pct = (position.entry_price - current_price) / position.entry_price
        
        # 오래 보유했는데 수익이 없으면 청산
        if hold_duration > 12 and profit_pct < 0.01:  # 12시간 이상, 1% 미만 수익
            return True, f"장기 보유 + 저수익: {hold_duration:.1f}시간, {profit_pct:.2%}"
        
        # 최대 보유 시간 초과
        if hold_duration > self.max_hold_hours:
            return True, f"최대 보유 시간 초과: {hold_duration:.1f}시간"
        
        return False, "OK"

