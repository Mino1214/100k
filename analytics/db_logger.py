"""데이터베이스 결과 저장 모듈"""

import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseLogger:
    """데이터베이스 결과 저장 클래스"""
    
    def __init__(self, connection_string: str, project_prefix: str = "myno"):
        """
        데이터베이스 로거 초기화
        
        Args:
            connection_string: 데이터베이스 연결 문자열
            project_prefix: 테이블명 접두사
        """
        self.connection_string = connection_string
        self.project_prefix = project_prefix
        self.engine = create_engine(connection_string)
        self._ensure_tables()
        logger.info(f"데이터베이스 로거 초기화: prefix={project_prefix}")
    
    def _ensure_tables(self):
        """필요한 테이블 생성"""
        try:
            with self.engine.connect() as conn:
                # 백테스트 결과 테이블
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.project_prefix}_backtest_results (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(100) NOT NULL,
                        run_date DATETIME NOT NULL,
                        symbol VARCHAR(20) NOT NULL,
                        timeframe VARCHAR(10) NOT NULL,
                        start_date DATE,
                        end_date DATE,
                        strategy_name VARCHAR(100),
                        initial_capital DECIMAL(20, 2),
                        final_equity DECIMAL(20, 2),
                        total_return DECIMAL(10, 6),
                        annualized_return DECIMAL(10, 6),
                        sharpe_ratio DECIMAL(10, 4),
                        sortino_ratio DECIMAL(10, 4),
                        max_drawdown DECIMAL(10, 6),
                        win_rate DECIMAL(10, 4),
                        profit_factor DECIMAL(10, 4),
                        total_trades INT,
                        winning_trades INT,
                        losing_trades INT,
                        avg_win DECIMAL(20, 2),
                        avg_loss DECIMAL(20, 2),
                        expectancy DECIMAL(20, 2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_session (session_id),
                        INDEX idx_run_date (run_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                
                # 자기반성 일지 테이블
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.project_prefix}_reflection_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(100) NOT NULL,
                        run_date DATETIME NOT NULL,
                        reflection_date DATE NOT NULL,
                        performance_rating INT COMMENT '성과 평가 (1-10)',
                        strengths TEXT COMMENT '강점',
                        weaknesses TEXT COMMENT '약점',
                        lessons_learned TEXT COMMENT '배운 점',
                        improvements TEXT COMMENT '개선 사항',
                        next_actions TEXT COMMENT '다음 행동 계획',
                        emotional_state VARCHAR(50) COMMENT '감정 상태',
                        notes TEXT COMMENT '기타 메모',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_session (session_id),
                        INDEX idx_reflection_date (reflection_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                
                # 거래 상세 기록 테이블
                # 최적화 스냅샷 테이블
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.project_prefix}_optimization_snapshots (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(100) NOT NULL,
                        snapshot_timestamp DATETIME NOT NULL,
                        start_date VARCHAR(50) NOT NULL,
                        end_date VARCHAR(50) NOT NULL,
                        ema_fast INT,
                        ema_mid INT,
                        ema_slow INT,
                        atr_multiplier DECIMAL(10, 2),
                        win_rate DECIMAL(10, 4),
                        total_return DECIMAL(10, 6),
                        sharpe_ratio DECIMAL(10, 4),
                        profit_factor DECIMAL(10, 4),
                        max_drawdown DECIMAL(10, 6),
                        total_trades INT,
                        achieved_win_rate BOOLEAN,
                        achieved_return BOOLEAN,
                        params_json TEXT,
                        metrics_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_session (session_id),
                        INDEX idx_timestamp (snapshot_timestamp),
                        INDEX idx_win_rate (win_rate),
                        INDEX idx_total_return (total_return)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.project_prefix}_trade_details (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(100) NOT NULL,
                        trade_id INT,
                        entry_time DATETIME NOT NULL,
                        exit_time DATETIME,
                        direction VARCHAR(10),
                        entry_price DECIMAL(20, 8),
                        exit_price DECIMAL(20, 8),
                        quantity DECIMAL(20, 8),
                        pnl DECIMAL(20, 2),
                        return_pct DECIMAL(10, 6),
                        duration_bars INT,
                        commission DECIMAL(20, 2),
                        slippage DECIMAL(20, 2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_session (session_id),
                        INDEX idx_entry_time (entry_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                
                conn.commit()
                logger.info("데이터베이스 테이블 생성 완료")
        except SQLAlchemyError as e:
            logger.error(f"테이블 생성 실패: {e}")
            raise
    
    def save_backtest_result(
        self,
        session_id: str,
        metrics: Any,
        config: Dict[str, Any],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """
        백테스트 결과 저장
        
        Args:
            session_id: 세션 ID
            metrics: 성능 지표
            config: 설정
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            저장된 레코드 ID
        """
        try:
            data_config = config.get("data", {})
            strategy_config = config.get("strategy", {})
            backtest_config = config.get("backtest", {})
            engine_config = backtest_config.get("engine", {})
            
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    INSERT INTO {self.project_prefix}_backtest_results (
                        session_id, run_date, symbol, timeframe, start_date, end_date,
                        strategy_name, initial_capital, final_equity, total_return,
                        annualized_return, sharpe_ratio, sortino_ratio, max_drawdown,
                        win_rate, profit_factor, total_trades, winning_trades, losing_trades,
                        avg_win, avg_loss, expectancy
                    ) VALUES (
                        :session_id, :run_date, :symbol, :timeframe, :start_date, :end_date,
                        :strategy_name, :initial_capital, :final_equity, :total_return,
                        :annualized_return, :sharpe_ratio, :sortino_ratio, :max_drawdown,
                        :win_rate, :profit_factor, :total_trades, :winning_trades, :losing_trades,
                        :avg_win, :avg_loss, :expectancy
                    )
                """), {
                    "session_id": session_id,
                    "run_date": datetime.now(),
                    "symbol": data_config.get("symbol", ""),
                    "timeframe": data_config.get("timeframe", ""),
                    "start_date": pd.to_datetime(start_date).date() if start_date else None,
                    "end_date": pd.to_datetime(end_date).date() if end_date else None,
                    "strategy_name": strategy_config.get("name", ""),
                    "initial_capital": float(engine_config.get("initial_capital", 0)),
                    "final_equity": float(metrics.final_equity) if hasattr(metrics, 'final_equity') else float(metrics.total_return * engine_config.get("initial_capital", 100000) + engine_config.get("initial_capital", 100000)),
                    "total_return": float(metrics.total_return),
                    "annualized_return": float(metrics.annualized_return),
                    "sharpe_ratio": float(metrics.sharpe_ratio),
                    "sortino_ratio": float(metrics.sortino_ratio),
                    "max_drawdown": float(metrics.max_drawdown),
                    "win_rate": float(metrics.win_rate),
                    "profit_factor": float(metrics.profit_factor),
                    "total_trades": int(metrics.total_trades),
                    "winning_trades": int(metrics.winning_trades),
                    "losing_trades": int(metrics.losing_trades),
                    "avg_win": float(metrics.avg_win),
                    "avg_loss": float(metrics.avg_loss),
                    "expectancy": float(metrics.expectancy),
                })
                conn.commit()
                record_id = result.lastrowid
                logger.info(f"백테스트 결과 저장 완료: session_id={session_id}, id={record_id}")
                return record_id
        except SQLAlchemyError as e:
            logger.error(f"백테스트 결과 저장 실패: {e}")
            raise
    
    def save_trades(
        self,
        session_id: str,
        trades_df: pd.DataFrame,
    ):
        """
        거래 상세 기록 저장
        
        Args:
            session_id: 세션 ID
            trades_df: 거래 데이터프레임
        """
        if trades_df.empty:
            logger.warning("저장할 거래가 없습니다.")
            return
        
        try:
            with self.engine.connect() as conn:
                for idx, trade in trades_df.iterrows():
                    conn.execute(text(f"""
                        INSERT INTO {self.project_prefix}_trade_details (
                            session_id, entry_time, exit_time, direction,
                            entry_price, exit_price, quantity, pnl, return_pct,
                            duration_bars, commission, slippage
                        ) VALUES (
                            :session_id, :entry_time, :exit_time, :direction,
                            :entry_price, :exit_price, :quantity, :pnl, :return_pct,
                            :duration_bars, :commission, :slippage
                        )
                    """), {
                        "session_id": session_id,
                        "entry_time": trade.get("entry_time"),
                        "exit_time": trade.get("exit_time"),
                        "direction": trade.get("direction"),
                        "entry_price": float(trade.get("entry_price", 0)),
                        "exit_price": float(trade.get("exit_price", 0)),
                        "quantity": float(trade.get("quantity", 0)),
                        "pnl": float(trade.get("pnl", 0)),
                        "return_pct": float(trade.get("return_pct", 0)),
                        "duration_bars": int(trade.get("duration_bars", 0)),
                        "commission": float(trade.get("commission", 0)),
                        "slippage": float(trade.get("slippage", 0)),
                    })
                conn.commit()
                logger.info(f"거래 기록 저장 완료: {len(trades_df)}건")
        except SQLAlchemyError as e:
            logger.error(f"거래 기록 저장 실패: {e}")
            raise
    
    def save_reflection(
        self,
        session_id: str,
        performance_rating: int,
        strengths: str = "",
        weaknesses: str = "",
        lessons_learned: str = "",
        improvements: str = "",
        next_actions: str = "",
        emotional_state: str = "",
        notes: str = "",
    ) -> int:
        """
        자기반성 일지 저장
        
        Args:
            session_id: 세션 ID
            performance_rating: 성과 평가 (1-10)
            strengths: 강점
            weaknesses: 약점
            lessons_learned: 배운 점
            improvements: 개선 사항
            next_actions: 다음 행동 계획
            emotional_state: 감정 상태
            notes: 기타 메모
            
        Returns:
            저장된 레코드 ID
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    INSERT INTO {self.project_prefix}_reflection_logs (
                        session_id, run_date, reflection_date,
                        performance_rating, strengths, weaknesses,
                        lessons_learned, improvements, next_actions,
                        emotional_state, notes
                    ) VALUES (
                        :session_id, :run_date, :reflection_date,
                        :performance_rating, :strengths, :weaknesses,
                        :lessons_learned, :improvements, :next_actions,
                        :emotional_state, :notes
                    )
                """), {
                    "session_id": session_id,
                    "run_date": datetime.now(),
                    "reflection_date": datetime.now().date(),
                    "performance_rating": performance_rating,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "lessons_learned": lessons_learned,
                    "improvements": improvements,
                    "next_actions": next_actions,
                    "emotional_state": emotional_state,
                    "notes": notes,
                })
                conn.commit()
                record_id = result.lastrowid
                logger.info(f"자기반성 일지 저장 완료: session_id={session_id}, id={record_id}")
                return record_id
        except SQLAlchemyError as e:
            logger.error(f"자기반성 일지 저장 실패: {e}")
            raise
    
    def get_latest_session_id(self) -> Optional[str]:
        """최신 세션 ID 조회"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT session_id 
                    FROM {self.project_prefix}_backtest_results 
                    ORDER BY run_date DESC 
                    LIMIT 1
                """))
                row = result.fetchone()
                return row[0] if row else None
        except SQLAlchemyError as e:
            logger.error(f"세션 ID 조회 실패: {e}")
            return None
    
    def get_session_count(self) -> int:
        """총 세션 수 조회"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT COUNT(DISTINCT session_id) 
                    FROM {self.project_prefix}_backtest_results
                """))
                return result.fetchone()[0] or 0
        except SQLAlchemyError as e:
            logger.error(f"세션 수 조회 실패: {e}")
            return 0

