"""리스크 가디언 모듈 - 실전 거래를 위한 정교한 리스크 관리"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from analytics.metrics import PerformanceMetrics
from utils.logger import get_logger
import pandas as pd

logger = get_logger(__name__)


class RiskGuardian:
    """리스크 가디언 클래스 - 실전 거래 보호"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        리스크 가디언 초기화
        
        Args:
            config: 리스크 설정
        """
        self.config = config
        risk_config = config.get("risk", {})
        
        # 일일 리스크 제한
        self.daily_loss_limit = risk_config.get("daily_loss_limit", 0.02)  # 2%
        self.daily_trade_limit = risk_config.get("daily_trade_limit", 10)  # 최대 10회
        
        # 연속 손실 제한
        self.max_consecutive_losses = risk_config.get("max_consecutive_losses", 3)
        self.consecutive_losses = 0
        
        # 드로다운 제한
        self.max_drawdown_limit = risk_config.get("max_drawdown_limit", 0.10)  # 10%
        self.initial_capital = risk_config.get("initial_capital", 100000)
        self.peak_equity = self.initial_capital
        
        # 거래 시간 제한
        self.max_position_duration_hours = risk_config.get("max_position_duration_hours", 24)
        
        # 변동성 필터
        self.volatility_filter = risk_config.get("volatility_filter", {})
        self.max_volatility_multiplier = self.volatility_filter.get("max_multiplier", 3.0)
        
        # 일일 통계
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.current_date = datetime.now().date()
        
        # 거래 이력
        self.recent_trades: List[Dict[str, Any]] = []
        self.max_recent_trades = 100
        
        logger.info("리스크 가디언 초기화 완료")
        logger.info(f"일일 손실 한도: {self.daily_loss_limit:.1%}")
        logger.info(f"최대 연속 손실: {self.max_consecutive_losses}회")
        logger.info(f"최대 드로다운: {self.max_drawdown_limit:.1%}")
    
    def can_open_position(
        self,
        current_equity: float,
        current_price: float,
        atr_value: float,
        volume: float,
        volume_ma: float,
    ) -> tuple[bool, str]:
        """
        포지션 오픈 가능 여부 확인
        
        Args:
            current_equity: 현재 자산
            current_price: 현재 가격
            atr_value: ATR 값
            volume: 현재 거래량
            volume_ma: 거래량 이동평균
            
        Returns:
            (가능 여부, 이유)
        """
        # 일일 손실 한도 확인
        if self.daily_pnl <= -self.daily_loss_limit * self.initial_capital:
            return False, f"일일 손실 한도 도달: {self.daily_pnl:.2f}"
        
        # 일일 거래 수 제한
        if self.daily_trades >= self.daily_trade_limit:
            return False, f"일일 거래 수 제한 도달: {self.daily_trades}회"
        
        # 연속 손실 확인
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"연속 손실 한도 도달: {self.consecutive_losses}회"
        
        # 드로다운 확인
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        if drawdown >= self.max_drawdown_limit:
            return False, f"최대 드로다운 도달: {drawdown:.1%}"
        
        # 변동성 필터 (ATR 기반)
        if atr_value > 0:
            price_volatility = atr_value / current_price
            avg_volatility = self._get_average_volatility()
            if avg_volatility > 0:
                volatility_ratio = price_volatility / avg_volatility
                if volatility_ratio > self.max_volatility_multiplier:
                    return False, f"변동성 과다: {volatility_ratio:.2f}x 평균"
        
        # 거래량 필터
        if volume_ma > 0:
            volume_ratio = volume / volume_ma
            if volume_ratio < 0.5:  # 거래량이 평균의 50% 미만
                return False, f"거래량 부족: {volume_ratio:.2f}x 평균"
        
        return True, "OK"
    
    def calculate_safe_position_size(
        self,
        equity: float,
        entry_price: float,
        stop_loss_price: float,
        direction: str,
        atr_value: float,
    ) -> float:
        """
        안전한 포지션 사이즈 계산 (리스크 최소화)
        
        Args:
            equity: 현재 자산
            entry_price: 진입 가격
            stop_loss_price: 스탑로스 가격
            direction: 방향 (long/short)
            atr_value: ATR 값
            
        Returns:
            포지션 사이즈 (수량)
        """
        # 리스크 설정
        risk_config = self.config.get("risk", {})
        position_sizing = risk_config.get("position_sizing", {})
        risk_per_trade = position_sizing.get("risk_per_trade", 0.01)  # 1% 기본
        
        # 드로다운이 크면 리스크 감소
        drawdown = (self.peak_equity - equity) / self.peak_equity
        if drawdown > 0.05:  # 5% 이상 드로다운
            risk_per_trade *= 0.5  # 리스크 절반으로
        
        # 연속 손실 시 리스크 감소
        if self.consecutive_losses >= 2:
            risk_per_trade *= 0.5
        
        # 손실 금액 계산
        if direction == "long":
            price_diff = abs(entry_price - stop_loss_price)
        else:
            price_diff = abs(stop_loss_price - entry_price)
        
        if price_diff == 0:
            return 0.0
        
        # 리스크 금액
        risk_amount = equity * risk_per_trade
        
        # 포지션 사이즈 계산
        position_size = risk_amount / price_diff
        
        # 최대 포지션 사이즈 제한 (자산의 20% 이하)
        max_position_value = equity * 0.20
        max_position_size = max_position_value / entry_price
        
        position_size = min(position_size, max_position_size)
        
        # 최소 거래 단위 확인 (소수점 처리)
        min_trade_size = 0.001  # 최소 거래량
        if position_size < min_trade_size:
            return 0.0
        
        return round(position_size, 3)
    
    def should_close_position(
        self,
        position: Any,
        current_price: float,
        current_time: Any,  # datetime
        current_equity: float,
    ) -> tuple[bool, str]:
        """
        포지션 청산 필요 여부 확인
        
        Args:
            position: 현재 포지션
            current_price: 현재 가격
            current_time: 현재 시간
            current_equity: 현재 자산
            
        Returns:
            (청산 필요 여부, 이유)
        """
        # 스탑로스 확인
        if position.direction == "long":
            if current_price <= position.stop_loss:
                return True, f"스탑로스 도달: {current_price:.2f} <= {position.stop_loss:.2f}"
        else:
            if current_price >= position.stop_loss:
                return True, f"스탑로스 도달: {current_price:.2f} >= {position.stop_loss:.2f}"
        
        # 최대 보유 시간 확인
        position_duration = current_time - position.entry_time
        if position_duration.total_seconds() / 3600 > self.max_position_duration_hours:
            return True, f"최대 보유 시간 초과: {position_duration}"
        
        # 일일 손실 한도 확인 (포지션 포함)
        if self.daily_pnl <= -self.daily_loss_limit * self.initial_capital:
            return True, "일일 손실 한도 도달"
        
        return False, "OK"
    
    def update_after_trade(
        self,
        trade_result: Dict[str, Any],
        current_equity: float,
    ):
        """
        거래 후 상태 업데이트
        
        Args:
            trade_result: 거래 결과
            current_equity: 현재 자산
        """
        # 일일 통계 업데이트
        today = datetime.now().date()
        if today != self.current_date:
            # 새 날 시작
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.current_date = today
        
        pnl = trade_result.get("pnl", 0.0)
        self.daily_pnl += pnl
        self.daily_trades += 1
        
        # 연속 손실 업데이트
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # 피크 자산 업데이트
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        # 거래 이력 추가
        self.recent_trades.append({
            "timestamp": datetime.now(),
            "pnl": pnl,
            "direction": trade_result.get("direction"),
        })
        
        # 최근 거래만 유지
        if len(self.recent_trades) > self.max_recent_trades:
            self.recent_trades.pop(0)
    
    def _get_average_volatility(self) -> float:
        """평균 변동성 계산 (최근 거래 기반)"""
        if not self.recent_trades:
            return 0.0
        
        # 최근 20개 거래의 변동성 평균
        # 실제로는 ATR의 이동평균을 사용해야 함
        return 0.02  # 기본값 2%
    
    def get_risk_status(self) -> Dict[str, Any]:
        """현재 리스크 상태 반환"""
        return {
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "consecutive_losses": self.consecutive_losses,
            "peak_equity": self.peak_equity,
            "current_drawdown": (self.peak_equity - self.initial_capital) / self.initial_capital if self.peak_equity > 0 else 0.0,
            "can_trade": self.consecutive_losses < self.max_consecutive_losses and self.daily_trades < self.daily_trade_limit,
        }

