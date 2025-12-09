"""리스크 관리 모듈"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from strategy.base_strategy import Position
from utils.logger import get_logger
from utils.helpers import safe_divide

logger = get_logger(__name__)


class RiskManager:
    """리스크 관리자 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        리스크 관리자 초기화
        
        Args:
            config: 리스크 설정
        """
        self.config = config
        self.position_sizing_config = config.get("position_sizing", {})
        self.portfolio_config = config.get("portfolio", {})
        
        # 포트폴리오 리스크 제한
        self.max_drawdown_limit = self.portfolio_config.get("max_drawdown_limit", 0.20)
        self.daily_loss_limit = self.portfolio_config.get("daily_loss_limit", 0.05)
        self.max_daily_trades = self.portfolio_config.get("max_daily_trades", 50)
        
        # 거래 통계 (Kelly 계산용)
        self.trade_history: List[Dict[str, Any]] = []
        
        logger.info("리스크 관리자 초기화 완료")
    
    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        direction: str,
    ) -> float:
        """
        포지션 사이즈 계산
        
        Args:
            account_balance: 계좌 잔고
            entry_price: 진입 가격
            stop_loss: 스탑로스 가격
            direction: 포지션 방향 (long/short)
            
        Returns:
            포지션 사이즈 (수량)
        """
        method = self.position_sizing_config.get("method", "fixed")
        
        if method == "fixed":
            return self._calculate_fixed_size()
        elif method == "risk_pct":
            return self._calculate_risk_pct_size(account_balance, entry_price, stop_loss, direction)
        elif method == "kelly":
            return self._calculate_kelly_size(account_balance, entry_price, stop_loss, direction)
        elif method == "volatility_adjusted":
            return self._calculate_volatility_adjusted_size(account_balance)
        else:
            logger.warning(f"알 수 없는 포지션 사이징 방법: {method}, fixed 사용")
            return self._calculate_fixed_size()
    
    def _calculate_fixed_size(self) -> float:
        """고정 사이즈 계산"""
        fixed_config = self.position_sizing_config.get("fixed", {})
        return fixed_config.get("quantity", 1.0)
    
    def _calculate_risk_pct_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        direction: str,
    ) -> float:
        """리스크 퍼센트 기반 사이즈 계산"""
        risk_config = self.position_sizing_config.get("risk_pct", {})
        account_risk_per_trade = risk_config.get("account_risk_per_trade", 0.01)
        
        # 손실 금액 계산
        if direction == "long":
            risk_per_unit = entry_price - stop_loss
        else:  # short
            risk_per_unit = stop_loss - entry_price
        
        if risk_per_unit <= 0:
            logger.warning("스탑로스가 진입가보다 불리합니다.")
            return 0.0
        
        # 리스크 금액
        risk_amount = account_balance * account_risk_per_trade
        
        # 포지션 사이즈
        position_size = risk_amount / risk_per_unit
        
        return position_size
    
    def _calculate_kelly_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        direction: str,
    ) -> float:
        """Kelly 기준 사이즈 계산"""
        kelly_config = self.position_sizing_config.get("kelly", {})
        fraction = kelly_config.get("fraction", 0.25)  # Half Kelly
        lookback_trades = kelly_config.get("lookback_trades", 100)
        
        if len(self.trade_history) < lookback_trades:
            # 충분한 거래 이력이 없으면 리스크 퍼센트 사용
            return self._calculate_risk_pct_size(account_balance, entry_price, stop_loss, direction)
        
        # 최근 거래 이력
        recent_trades = self.trade_history[-lookback_trades:]
        
        # 승률 및 평균 손익 계산
        wins = [t for t in recent_trades if t.get("pnl", 0) > 0]
        losses = [t for t in recent_trades if t.get("pnl", 0) <= 0]
        
        if not wins or not losses:
            return self._calculate_risk_pct_size(account_balance, entry_price, stop_loss, direction)
        
        win_rate = len(wins) / len(recent_trades)
        avg_win = np.mean([t["pnl"] for t in wins])
        avg_loss = abs(np.mean([t["pnl"] for t in losses]))
        
        if avg_loss == 0:
            return self._calculate_risk_pct_size(account_balance, entry_price, stop_loss, direction)
        
        # Kelly 비율 계산
        win_loss_ratio = avg_win / avg_loss
        kelly_percent = win_rate - ((1 - win_rate) / win_loss_ratio)
        kelly_percent = max(0, min(kelly_percent, 1))  # 0-1 범위로 제한
        
        # Fraction Kelly 적용
        position_size_pct = kelly_percent * fraction
        
        # 포지션 사이즈 계산
        position_size = account_balance * position_size_pct / entry_price
        
        return position_size
    
    def _calculate_volatility_adjusted_size(self, account_balance: float) -> float:
        """변동성 조정 사이즈 계산"""
        vol_config = self.position_sizing_config.get("volatility_adjusted", {})
        base_size = vol_config.get("base_size", 1.0)
        target_volatility = vol_config.get("target_volatility", 0.02)
        
        # 간단한 구현 (실제로는 현재 변동성을 계산해야 함)
        # 여기서는 기본 사이즈 반환
        return base_size
    
    def check_portfolio_risk(
        self,
        current_equity: float,
        initial_capital: float,
        daily_pnl: float,
        daily_trades: int,
    ) -> bool:
        """
        포트폴리오 리스크 확인
        
        Args:
            current_equity: 현재 자산
            initial_capital: 초기 자본
            daily_pnl: 일일 손익
            daily_trades: 일일 거래 횟수
            
        Returns:
            거래 가능 여부 (True면 거래 가능)
        """
        # 최대 드로다운 확인
        drawdown = (initial_capital - current_equity) / initial_capital
        if drawdown >= self.max_drawdown_limit:
            logger.warning(f"최대 드로다운 한도 도달: {drawdown:.2%}")
            return False
        
        # 일일 손실 한도 확인
        daily_loss_pct = abs(daily_pnl) / initial_capital if daily_pnl < 0 else 0
        if daily_loss_pct >= self.daily_loss_limit:
            logger.warning(f"일일 손실 한도 도달: {daily_loss_pct:.2%}")
            return False
        
        # 일일 거래 횟수 확인
        if daily_trades >= self.max_daily_trades:
            logger.warning(f"일일 거래 횟수 한도 도달: {daily_trades}")
            return False
        
        return True
    
    def record_trade(self, trade_info: Dict[str, Any]):
        """
        거래 기록 (Kelly 계산용)
        
        Args:
            trade_info: 거래 정보 (entry_price, exit_price, direction, pnl 등)
        """
        self.trade_history.append(trade_info)
        # 최근 거래만 유지 (메모리 관리)
        max_history = 1000
        if len(self.trade_history) > max_history:
            self.trade_history = self.trade_history[-max_history:]

