"""적응형 리스크 관리자 - 시드에 따라 사람처럼 리스크를 관리"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from utils.logger import get_logger
import numpy as np

logger = get_logger(__name__)


class AdaptiveRiskManager:
    """적응형 리스크 관리자 - 시드 기반 동적 리스크 조정"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        적응형 리스크 관리자 초기화
        
        Args:
            config: 리스크 설정
        """
        self.config = config
        risk_config = config.get("risk", {})
        
        # 시드 기반 리스크 관리
        self.initial_capital = risk_config.get("initial_capital", 100000)
        self.current_equity = self.initial_capital
        self.peak_equity = self.initial_capital
        
        # 시드 단계별 리스크 (사람처럼)
        self.seed_stages = {
            "seedling": {  # 초기 단계 (시드의 10% 이하)
                "max_risk_per_trade": 0.005,  # 0.5%
                "max_daily_risk": 0.01,  # 1%
                "min_confidence": 0.85,  # 높은 신뢰도만
                "max_trades_per_day": 3,
            },
            "growing": {  # 성장 단계 (시드의 10-50%)
                "max_risk_per_trade": 0.01,  # 1%
                "max_daily_risk": 0.02,  # 2%
                "min_confidence": 0.75,
                "max_trades_per_day": 5,
            },
            "mature": {  # 성숙 단계 (시드의 50-100%)
                "max_risk_per_trade": 0.015,  # 1.5%
                "max_daily_risk": 0.03,  # 3%
                "min_confidence": 0.70,
                "max_trades_per_day": 8,
            },
            "prosperous": {  # 번영 단계 (시드의 100% 이상)
                "max_risk_per_trade": 0.02,  # 2%
                "max_daily_risk": 0.05,  # 5%
                "min_confidence": 0.65,
                "max_trades_per_day": 10,
            },
        }
        
        # 현재 시드 단계
        self.current_stage = "seedling"
        
        # 일일 통계
        self.daily_risk_used = 0.0
        self.daily_trades = 0
        self.current_date = datetime.now().date()
        
        # 연속 손실 추적
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        # 최근 거래 이력 (학습용)
        self.recent_trades: List[Dict[str, Any]] = []
        self.max_recent_trades = 50
        
        logger.info("적응형 리스크 관리자 초기화 완료")
        logger.info(f"초기 시드: {self.initial_capital:,.0f}")
        logger.info(f"현재 단계: {self.current_stage}")
    
    def update_equity(self, equity: float):
        """자산 업데이트 및 시드 단계 재계산"""
        self.current_equity = equity
        
        # 피크 자산 업데이트
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        # 시드 단계 결정 (현재 자산 / 초기 자산 비율)
        equity_ratio = equity / self.initial_capital
        
        if equity_ratio < 0.1:
            new_stage = "seedling"
        elif equity_ratio < 0.5:
            new_stage = "growing"
        elif equity_ratio < 1.0:
            new_stage = "mature"
        else:
            new_stage = "prosperous"
        
        if new_stage != self.current_stage:
            logger.info(f"시드 단계 변경: {self.current_stage} → {new_stage} (자산 비율: {equity_ratio:.1%})")
            self.current_stage = new_stage
    
    def get_current_stage_config(self) -> Dict[str, Any]:
        """현재 시드 단계의 설정 반환"""
        return self.seed_stages[self.current_stage]
    
    def can_take_risk(
        self,
        risk_amount: float,
        confidence: float,
    ) -> tuple[bool, str, Dict[str, Any]]:
        """
        리스크를 감수할 수 있는지 확인
        
        Args:
            risk_amount: 리스크 금액
            confidence: 거래 신뢰도
            
        Returns:
            (가능 여부, 이유, 상세 정보)
        """
        # 일일 리셋
        today = datetime.now().date()
        if today != self.current_date:
            self.daily_risk_used = 0.0
            self.daily_trades = 0
            self.current_date = today
        
        stage_config = self.get_current_stage_config()
        
        # 리스크 비율 계산
        risk_ratio = risk_amount / self.current_equity if self.current_equity > 0 else 0.0
        
        # 1. 거래당 최대 리스크 확인
        if risk_ratio > stage_config["max_risk_per_trade"]:
            return False, f"거래당 리스크 초과: {risk_ratio:.2%} > {stage_config['max_risk_per_trade']:.2%}", {
                "reason": "max_risk_per_trade",
                "current": risk_ratio,
                "limit": stage_config["max_risk_per_trade"],
            }
        
        # 2. 일일 최대 리스크 확인
        daily_risk_ratio = (self.daily_risk_used + risk_amount) / self.current_equity
        if daily_risk_ratio > stage_config["max_daily_risk"]:
            return False, f"일일 리스크 초과: {daily_risk_ratio:.2%} > {stage_config['max_daily_risk']:.2%}", {
                "reason": "max_daily_risk",
                "current": daily_risk_ratio,
                "limit": stage_config["max_daily_risk"],
            }
        
        # 3. 신뢰도 확인
        if confidence < stage_config["min_confidence"]:
            return False, f"신뢰도 부족: {confidence:.1%} < {stage_config['min_confidence']:.1%}", {
                "reason": "min_confidence",
                "current": confidence,
                "limit": stage_config["min_confidence"],
            }
        
        # 4. 일일 거래 수 확인
        if self.daily_trades >= stage_config["max_trades_per_day"]:
            return False, f"일일 거래 수 초과: {self.daily_trades} >= {stage_config['max_trades_per_day']}", {
                "reason": "max_trades_per_day",
                "current": self.daily_trades,
                "limit": stage_config["max_trades_per_day"],
            }
        
        # 5. 연속 손실 확인 (시드 단계에 따라)
        if self.current_stage == "seedling" and self.consecutive_losses >= 2:
            return False, f"연속 손실로 인한 거래 중단: {self.consecutive_losses}회", {
                "reason": "consecutive_losses",
                "current": self.consecutive_losses,
                "limit": 2,
            }
        elif self.consecutive_losses >= 3:
            return False, f"연속 손실로 인한 거래 중단: {self.consecutive_losses}회", {
                "reason": "consecutive_losses",
                "current": self.consecutive_losses,
                "limit": 3,
            }
        
        # 모든 조건 통과
        return True, "OK", {
            "reason": "approved",
            "risk_ratio": risk_ratio,
            "daily_risk_ratio": daily_risk_ratio,
            "confidence": confidence,
        }
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        direction: str,
        confidence: float,
    ) -> float:
        """
        포지션 사이즈 계산 (시드 단계에 따라)
        
        Args:
            entry_price: 진입 가격
            stop_loss_price: 스탑로스 가격
            direction: 방향 (long/short)
            confidence: 거래 신뢰도
            
        Returns:
            포지션 사이즈 (수량)
        """
        stage_config = self.get_current_stage_config()
        
        # 손실 금액 계산
        if direction == "long":
            price_diff = abs(entry_price - stop_loss_price)
        else:
            price_diff = abs(stop_loss_price - entry_price)
        
        if price_diff == 0:
            return 0.0
        
        # 신뢰도에 따른 리스크 조정
        confidence_multiplier = confidence / stage_config["min_confidence"]
        confidence_multiplier = min(confidence_multiplier, 1.5)  # 최대 1.5배
        
        # 리스크 금액 계산
        base_risk = stage_config["max_risk_per_trade"] * self.current_equity
        adjusted_risk = base_risk * confidence_multiplier
        
        # 포지션 사이즈
        position_size = adjusted_risk / price_diff
        
        # 최대 포지션 사이즈 제한 (자산의 30% 이하)
        max_position_value = self.current_equity * 0.30
        max_position_size = max_position_value / entry_price
        
        position_size = min(position_size, max_position_size)
        
        # 최소 거래 단위
        min_trade_size = 0.001
        if position_size < min_trade_size:
            return 0.0
        
        return round(position_size, 3)
    
    def record_trade(
        self,
        risk_amount: float,
        pnl: float,
        confidence: float,
    ):
        """거래 기록 및 통계 업데이트"""
        # 일일 통계 업데이트
        self.daily_risk_used += risk_amount
        self.daily_trades += 1
        
        # 연속 손실/수익 업데이트
        if pnl < 0:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        else:
            self.consecutive_losses = 0
            self.consecutive_wins += 1
        
        # 거래 이력 추가
        self.recent_trades.append({
            "timestamp": datetime.now(),
            "risk_amount": risk_amount,
            "pnl": pnl,
            "confidence": confidence,
            "stage": self.current_stage,
        })
        
        # 최근 거래만 유지
        if len(self.recent_trades) > self.max_recent_trades:
            self.recent_trades.pop(0)
    
    def get_risk_status(self) -> Dict[str, Any]:
        """현재 리스크 상태 반환"""
        stage_config = self.get_current_stage_config()
        
        return {
            "current_stage": self.current_stage,
            "current_equity": self.current_equity,
            "equity_ratio": self.current_equity / self.initial_capital,
            "daily_risk_used": self.daily_risk_used,
            "daily_risk_ratio": self.daily_risk_used / self.current_equity if self.current_equity > 0 else 0.0,
            "daily_trades": self.daily_trades,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "stage_config": stage_config,
        }

