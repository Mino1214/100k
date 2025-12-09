"""몬테카를로 시뮬레이션 모듈"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)


class MonteCarloSimulator:
    """몬테카를로 시뮬레이터 클래스"""
    
    def __init__(self, n_runs: int = 1000):
        """
        몬테카를로 시뮬레이터 초기화
        
        Args:
            n_runs: 시뮬레이션 횟수
        """
        self.n_runs = n_runs
        logger.info(f"몬테카를로 시뮬레이터 초기화: {n_runs}회")
    
    def simulate(
        self,
        trades_df: pd.DataFrame,
        initial_capital: float,
    ) -> Dict[str, Any]:
        """
        몬테카를로 시뮬레이션 실행
        
        Args:
            trades_df: 거래 기록 데이터프레임
            initial_capital: 초기 자본
            
        Returns:
            시뮬레이션 결과
        """
        if trades_df.empty:
            logger.warning("거래 기록이 없습니다.")
            return {}
        
        # 거래 수익률 추출
        trade_returns = trades_df["return_pct"].values
        
        # 시뮬레이션 실행
        final_equities = []
        for _ in range(self.n_runs):
            # 무작위 순서로 거래 재배열
            shuffled_returns = np.random.permutation(trade_returns)
            cumulative_return = np.prod(1 + shuffled_returns)
            final_equity = initial_capital * cumulative_return
            final_equities.append(final_equity)
        
        final_equities = np.array(final_equities)
        
        # 통계 계산
        mean_equity = np.mean(final_equities)
        std_equity = np.std(final_equities)
        median_equity = np.median(final_equities)
        
        # 신뢰구간
        confidence_95_lower = np.percentile(final_equities, 2.5)
        confidence_95_upper = np.percentile(final_equities, 97.5)
        
        # 최악/최선 시나리오
        worst_case = np.min(final_equities)
        best_case = np.max(final_equities)
        
        return {
            "n_runs": self.n_runs,
            "mean_final_equity": float(mean_equity),
            "std_final_equity": float(std_equity),
            "median_final_equity": float(median_equity),
            "confidence_95": [float(confidence_95_lower), float(confidence_95_upper)],
            "worst_case": float(worst_case),
            "best_case": float(best_case),
            "all_results": final_equities.tolist(),
        }

