"""포지션 관리 모듈"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
from strategy.base_strategy import Position
from utils.logger import get_logger

logger = get_logger(__name__)


class PositionManager:
    """포지션 관리자 클래스"""
    
    def __init__(self, max_open_positions: int = 1):
        """
        포지션 관리자 초기화
        
        Args:
            max_open_positions: 최대 동시 포지션 수
        """
        self.max_open_positions = max_open_positions
        self.positions: List[Position] = []
        logger.info(f"포지션 관리자 초기화: max_open_positions={max_open_positions}")
    
    def add_position(self, position: Position) -> bool:
        """
        포지션 추가
        
        Args:
            position: 추가할 포지션
            
        Returns:
            추가 성공 여부
        """
        if len(self.positions) >= self.max_open_positions:
            logger.warning("최대 포지션 수에 도달했습니다.")
            return False
        
        self.positions.append(position)
        # 로그 제거 (너무 많은 로그 방지)
        return True
    
    def remove_position(self, position: Position) -> bool:
        """
        포지션 제거
        
        Args:
            position: 제거할 포지션
            
        Returns:
            제거 성공 여부
        """
        if position in self.positions:
            self.positions.remove(position)
            # 로그 제거 (너무 많은 로그 방지)
            return True
        return False
    
    def get_position(self, direction: Optional[str] = None) -> Optional[Position]:
        """
        포지션 가져오기
        
        Args:
            direction: 포지션 방향 (long/short, None이면 첫 번째 포지션)
            
        Returns:
            포지션 (없으면 None)
        """
        if not self.positions:
            return None
        
        if direction:
            for pos in self.positions:
                if pos.direction == direction:
                    return pos
            return None
        else:
            return self.positions[0]
    
    def has_position(self, direction: Optional[str] = None) -> bool:
        """
        포지션 존재 여부 확인
        
        Args:
            direction: 포지션 방향 (None이면 어떤 포지션이든)
            
        Returns:
            포지션 존재 여부
        """
        if not self.positions:
            return False
        
        if direction:
            return any(pos.direction == direction for pos in self.positions)
        else:
            return True
    
    def update_position_stop_loss(self, position: Position, new_stop_loss: float):
        """
        포지션 스탑로스 업데이트
        
        Args:
            position: 업데이트할 포지션
            new_stop_loss: 새로운 스탑로스 가격
        """
        if position in self.positions:
            position.stop_loss = new_stop_loss
            logger.debug(f"스탑로스 업데이트: {new_stop_loss}")
    
    def clear_all(self):
        """모든 포지션 제거"""
        self.positions.clear()
        # 로그 제거 (너무 많은 로그 방지)
    
    def get_positions_count(self) -> int:
        """현재 포지션 수 반환"""
        return len(self.positions)
    
    def get_all_positions(self) -> List[Position]:
        """모든 포지션 반환"""
        return self.positions.copy()

