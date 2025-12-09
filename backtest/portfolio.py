"""포트폴리오 추적 모듈"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
from strategy.base_strategy import Position
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Trade:
    """거래 기록"""
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    commission: float
    slippage: float
    return_pct: float
    duration_bars: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class Portfolio:
    """포트폴리오 추적 클래스"""
    
    def __init__(self, initial_capital: float, currency: str = "USDT"):
        """
        포트폴리오 초기화
        
        Args:
            initial_capital: 초기 자본
            currency: 통화
        """
        self.initial_capital = initial_capital
        self.currency = currency
        self.cash = initial_capital
        self.equity = initial_capital
        self.position: Optional[Position] = None
        
        # 거래 기록
        self.trades: List[Trade] = []
        
        # 일일 통계
        self.daily_stats: List[Dict[str, Any]] = []
        self.current_date: Optional[pd.Timestamp] = None
        self.daily_pnl = 0.0
        self.daily_trades = 0
        
        # 자산 곡선
        self.equity_curve: List[Dict[str, Any]] = []
        
        logger.info(f"포트폴리오 초기화: 초기 자본 {initial_capital} {currency}")
    
    def open_position(
        self,
        position: Position,
        fill_price: float,
        commission: float,
        slippage: float,
    ):
        """
        포지션 오픈
        
        Args:
            position: 포지션 정보
            fill_price: 체결 가격
            commission: 수수료
            slippage: 슬리피지
        """
        self.position = position
        cost = fill_price * position.quantity + commission
        self.cash -= cost
        
        logger.debug(
            f"포지션 오픈: {position.direction} {position.quantity} @ {fill_price}, "
            f"비용: {cost:.2f}"
        )
    
    def close_position(
        self,
        exit_price: float,
        commission: float,
        slippage: float,
        timestamp: pd.Timestamp,
    ) -> Trade:
        """
        포지션 클로즈
        
        Args:
            exit_price: 청산 가격
            commission: 수수료
            slippage: 슬리피지
            timestamp: 청산 시간
            
        Returns:
            거래 기록
        """
        if self.position is None:
            raise ValueError("포지션이 없습니다.")
        
        # 손익 계산
        if self.position.direction == "long":
            pnl = (exit_price - self.position.entry_price) * self.position.quantity
        else:  # short
            pnl = (self.position.entry_price - exit_price) * self.position.quantity
        
        pnl -= commission  # 수수료 차감
        pnl -= slippage * self.position.quantity  # 슬리피지 차감
        
        # 수익률 계산
        entry_cost = self.position.entry_price * self.position.quantity
        return_pct = pnl / entry_cost if entry_cost > 0 else 0.0
        
        # 기간 계산
        duration_bars = (timestamp - self.position.entry_time).total_seconds() / 60  # 분 단위
        
        # 거래 기록 생성
        trade = Trade(
            entry_time=self.position.entry_time,
            exit_time=timestamp,
            direction=self.position.direction,
            entry_price=self.position.entry_price,
            exit_price=exit_price,
            quantity=self.position.quantity,
            pnl=pnl,
            commission=commission,
            slippage=slippage,
            return_pct=return_pct,
            duration_bars=duration_bars,
            metadata=self.position.metadata or {},
        )
        
        # 현금 업데이트
        if self.position.direction == "long":
            self.cash += exit_price * self.position.quantity - commission
        else:  # short
            self.cash += self.position.entry_price * self.position.quantity + pnl
        
        # 거래 기록 추가
        self.trades.append(trade)
        
        # 일일 통계 업데이트
        self.daily_pnl += pnl
        self.daily_trades += 1
        
        logger.debug(
            f"포지션 클로즈: {self.position.direction} @ {exit_price}, "
            f"손익: {pnl:.2f} ({return_pct:.2%})"
        )
        
        # 포지션 초기화
        self.position = None
        
        return trade
    
    def update_equity(self, current_price: Optional[float] = None, timestamp: Optional[pd.Timestamp] = None):
        """
        자산 업데이트 (최적화 버전)
        
        Args:
            current_price: 현재 가격 (포지션이 있을 때)
            timestamp: 현재 시간 (None이면 기록 안 함)
        """
        # 미실현 손익 계산 (포지션이 있을 때만)
        if self.position and current_price:
            if self.position.direction == "long":
                unrealized_pnl = (current_price - self.position.entry_price) * self.position.quantity
            else:  # short
                unrealized_pnl = (self.position.entry_price - current_price) * self.position.quantity
            self.equity = self.cash + unrealized_pnl
        else:
            # 포지션이 없으면 현금 = 자산
            self.equity = self.cash
        
        # 자산 곡선 기록 (timestamp가 있을 때만)
        if timestamp:
            unrealized_pnl = 0.0
            if self.position and current_price:
                if self.position.direction == "long":
                    unrealized_pnl = (current_price - self.position.entry_price) * self.position.quantity
                else:
                    unrealized_pnl = (self.position.entry_price - current_price) * self.position.quantity
            
            self.equity_curve.append({
                "timestamp": timestamp,
                "equity": self.equity,
                "cash": self.cash,
                "unrealized_pnl": unrealized_pnl,
            })
            
            # 일일 통계 업데이트 (날짜 변경 시에만)
            if self.current_date is None or timestamp.date() != self.current_date.date():
                if self.current_date is not None:
                    self.daily_stats.append({
                        "date": self.current_date.date(),
                        "pnl": self.daily_pnl,
                        "trades": self.daily_trades,
                        "equity": self.equity,
                    })
                self.current_date = timestamp
                self.daily_pnl = 0.0
                self.daily_trades = 0
    
    def get_total_return(self) -> float:
        """총 수익률 반환"""
        return (self.equity - self.initial_capital) / self.initial_capital
    
    def get_trades_df(self) -> pd.DataFrame:
        """거래 기록을 데이터프레임으로 반환"""
        if not self.trades:
            return pd.DataFrame()
        
        data = []
        for trade in self.trades:
            data.append({
                "entry_time": trade.entry_time,
                "exit_time": trade.exit_time,
                "direction": trade.direction,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "quantity": trade.quantity,
                "pnl": trade.pnl,
                "return_pct": trade.return_pct,
                "duration_bars": trade.duration_bars,
                "commission": trade.commission,
                "slippage": trade.slippage,
            })
        
        return pd.DataFrame(data)
    
    def get_equity_curve_df(self) -> pd.DataFrame:
        """자산 곡선을 데이터프레임으로 반환"""
        if not self.equity_curve:
            return pd.DataFrame()
        
        return pd.DataFrame(self.equity_curve).set_index("timestamp")

