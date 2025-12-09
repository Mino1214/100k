"""거래 기록 모듈"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from backtest.portfolio import Trade
from utils.logger import get_logger

logger = get_logger(__name__)


class TradeLogger:
    """거래 기록 클래스"""
    
    def __init__(self, output_dir: str = "./logs/"):
        """
        거래 기록자 초기화
        
        Args:
            output_dir: 출력 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trades: List[Trade] = []
        logger.info(f"거래 기록자 초기화: {output_dir}")
    
    def log_trade(self, trade: Trade):
        """
        거래 기록
        
        Args:
            trade: 거래 정보
        """
        self.trades.append(trade)
        logger.debug(f"거래 기록: {trade.direction} @ {trade.entry_price}")
    
    def save_to_csv(self, filename: str = "trades.csv"):
        """
        CSV 파일로 저장
        
        Args:
            filename: 파일명
        """
        if not self.trades:
            logger.warning("저장할 거래가 없습니다.")
            return
        
        filepath = self.output_dir / filename
        
        # 데이터 준비
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
        
        # CSV 저장
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"거래 기록 CSV 저장: {filepath}")
    
    def save_to_json(self, filename: str = "trades.json"):
        """
        JSON 파일로 저장
        
        Args:
            filename: 파일명
        """
        if not self.trades:
            logger.warning("저장할 거래가 없습니다.")
            return
        
        filepath = self.output_dir / filename
        
        # 데이터 준비
        data = []
        for trade in self.trades:
            data.append({
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat(),
                "direction": trade.direction,
                "entry_price": float(trade.entry_price),
                "exit_price": float(trade.exit_price),
                "quantity": float(trade.quantity),
                "pnl": float(trade.pnl),
                "return_pct": float(trade.return_pct),
                "duration_bars": float(trade.duration_bars),
                "commission": float(trade.commission),
                "slippage": float(trade.slippage),
                "metadata": trade.metadata,
            })
        
        # JSON 저장
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"거래 기록 JSON 저장: {filepath}")
    
    def clear(self):
        """기록 초기화"""
        self.trades.clear()
        logger.debug("거래 기록 초기화")

