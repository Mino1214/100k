"""통계 검정 모듈"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)


class StatisticalTester:
    """통계 검정 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        통계 검정기 초기화
        
        Args:
            config: 통계 검정 설정
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.tests = config.get("tests", [])
        logger.info("통계 검정기 초기화 완료")
    
    def run_tests(
        self,
        returns: pd.Series,
        trades_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        통계 검정 실행
        
        Args:
            returns: 수익률 시리즈
            trades_df: 거래 기록 데이터프레임
            
        Returns:
            검정 결과
        """
        if not self.enabled:
            return {}
        
        results = {}
        
        for test_name in self.tests:
            if test_name == "t_test":
                results["t_test"] = self._t_test(returns)
            elif test_name == "bootstrap":
                results["bootstrap"] = self._bootstrap(returns)
            elif test_name == "autocorrelation":
                results["autocorrelation"] = self._autocorrelation_test(returns)
            else:
                logger.warning(f"알 수 없는 검정: {test_name}")
        
        return results
    
    def _t_test(self, returns: pd.Series) -> Dict[str, Any]:
        """t-검정: 수익률이 0보다 유의하게 큰지"""
        if len(returns) == 0:
            return {"error": "데이터가 없습니다."}
        
        t_stat, p_value = stats.ttest_1samp(returns, 0)
        
        return {
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "significant": p_value < 0.05,
            "null_hypothesis": "mean return = 0",
        }
    
    def _bootstrap(self, returns: pd.Series, n_samples: int = 1000, confidence: float = 0.95) -> Dict[str, Any]:
        """Bootstrap 신뢰구간 계산"""
        if len(returns) == 0:
            return {"error": "데이터가 없습니다."}
        
        bootstrap_means = []
        for _ in range(n_samples):
            sample = returns.sample(n=len(returns), replace=True)
            bootstrap_means.append(sample.mean())
        
        bootstrap_means = np.array(bootstrap_means)
        alpha = 1 - confidence
        lower = np.percentile(bootstrap_means, 100 * alpha / 2)
        upper = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))
        
        return {
            "mean": float(returns.mean()),
            "confidence_interval": [float(lower), float(upper)],
            "confidence_level": confidence,
        }
    
    def _autocorrelation_test(self, returns: pd.Series, max_lag: int = 10) -> Dict[str, Any]:
        """자기상관 검정"""
        if len(returns) == 0:
            return {"error": "데이터가 없습니다."}
        
        autocorrs = []
        for lag in range(1, max_lag + 1):
            corr = returns.autocorr(lag=lag)
            autocorrs.append({
                "lag": lag,
                "correlation": float(corr) if not pd.isna(corr) else 0.0,
            })
        
        return {
            "autocorrelations": autocorrs,
            "max_lag": max_lag,
        }

