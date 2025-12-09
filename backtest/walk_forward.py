"""Walk-Forward 분석 모듈"""

import pandas as pd
from typing import Dict, Any, List
from datetime import timedelta
from backtest.engine import BacktestEngine
from strategy.base_strategy import BaseStrategy
from utils.logger import get_logger

logger = get_logger(__name__)


class WalkForwardAnalyzer:
    """Walk-Forward 분석 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Walk-Forward 분석기 초기화
        
        Args:
            config: Walk-Forward 설정
        """
        self.config = config
        period_config = config.get("period", {})
        walk_forward_config = period_config.get("walk_forward", {})
        
        self.in_sample_days = walk_forward_config.get("in_sample_days", 180)
        self.out_of_sample_days = walk_forward_config.get("out_of_sample_days", 30)
        self.anchored = walk_forward_config.get("anchored", False)
        
        logger.info(
            f"Walk-Forward 분석기 초기화: "
            f"in_sample={self.in_sample_days}일, "
            f"out_sample={self.out_of_sample_days}일"
        )
    
    def analyze(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        backtest_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Walk-Forward 분석 실행
        
        Args:
            strategy: 전략 인스턴스
            df: 데이터프레임
            backtest_config: 백테스트 설정
            
        Returns:
            Walk-Forward 분석 결과
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("데이터프레임 인덱스가 DatetimeIndex가 아닙니다.")
        
        results = []
        start_date = df.index[0]
        end_date = df.index[-1]
        
        current_start = start_date
        in_sample_end = None
        
        logger.info("Walk-Forward 분석 시작...")
        
        while current_start < end_date:
            # In-sample 기간
            if self.anchored:
                in_sample_start = start_date
            else:
                in_sample_start = current_start
            
            in_sample_end = in_sample_start + timedelta(days=self.in_sample_days)
            
            if in_sample_end > end_date:
                break
            
            # Out-of-sample 기간
            out_sample_start = in_sample_end
            out_sample_end = out_sample_start + timedelta(days=self.out_of_sample_days)
            
            if out_sample_end > end_date:
                out_sample_end = end_date
            
            # In-sample 데이터
            in_sample_df = df[(df.index >= in_sample_start) & (df.index < in_sample_end)]
            
            # Out-of-sample 데이터
            out_sample_df = df[(df.index >= out_sample_start) & (df.index < out_sample_end)]
            
            if len(in_sample_df) == 0 or len(out_sample_df) == 0:
                current_start = out_sample_end
                continue
            
            logger.info(
                f"In-sample: {in_sample_start.date()} ~ {in_sample_end.date()}, "
                f"Out-sample: {out_sample_start.date()} ~ {out_sample_end.date()}"
            )
            
            # In-sample 백테스트
            in_sample_engine = BacktestEngine(strategy, backtest_config)
            in_sample_result = in_sample_engine.run(in_sample_df)
            
            # Out-of-sample 백테스트
            out_sample_engine = BacktestEngine(strategy, backtest_config)
            out_sample_result = out_sample_engine.run(out_sample_df)
            
            results.append({
                "in_sample_start": in_sample_start,
                "in_sample_end": in_sample_end,
                "out_sample_start": out_sample_start,
                "out_sample_end": out_sample_end,
                "in_sample_result": in_sample_result,
                "out_sample_result": out_sample_result,
            })
            
            # 다음 기간으로 이동
            if self.anchored:
                current_start = out_sample_end
            else:
                current_start = in_sample_end
        
        logger.info(f"Walk-Forward 분석 완료: {len(results)}개 기간")
        
        return {
            "results": results,
            "summary": self._compile_summary(results),
        }
    
    def _compile_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        요약 통계 계산
        
        Args:
            results: Walk-Forward 결과 리스트
            
        Returns:
            요약 통계
        """
        in_sample_returns = [r["in_sample_result"]["total_return"] for r in results]
        out_sample_returns = [r["out_sample_result"]["total_return"] for r in results]
        
        return {
            "periods": len(results),
            "avg_in_sample_return": sum(in_sample_returns) / len(in_sample_returns) if in_sample_returns else 0,
            "avg_out_sample_return": sum(out_sample_returns) / len(out_sample_returns) if out_sample_returns else 0,
            "in_sample_returns": in_sample_returns,
            "out_sample_returns": out_sample_returns,
        }

