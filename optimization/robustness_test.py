"""견고성 테스트 모듈"""

from typing import Dict, Any, Callable, List
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


class RobustnessTester:
    """견고성 테스트 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        견고성 테스트기 초기화
        
        Args:
            config: 견고성 테스트 설정
        """
        self.config = config
        self.monte_carlo_runs = config.get("monte_carlo_runs", 1000)
        self.parameter_sensitivity = config.get("parameter_sensitivity", True)
        logger.info("견고성 테스트기 초기화 완료")
    
    def test(
        self,
        base_params: Dict[str, Any],
        objective_func: Callable,
        param_ranges: Dict[str, tuple],
    ) -> Dict[str, Any]:
        """
        견고성 테스트 실행
        
        Args:
            base_params: 기본 파라미터
            objective_func: 목적 함수
            param_ranges: 파라미터 범위 (min, max)
            
        Returns:
            견고성 테스트 결과
        """
        results = {}
        
        # 파라미터 민감도 분석
        if self.parameter_sensitivity:
            results["sensitivity"] = self._parameter_sensitivity_analysis(
                base_params,
                objective_func,
                param_ranges,
            )
        
        return results
    
    def _parameter_sensitivity_analysis(
        self,
        base_params: Dict[str, Any],
        objective_func: Callable,
        param_ranges: Dict[str, tuple],
    ) -> Dict[str, Any]:
        """파라미터 민감도 분석"""
        sensitivity_results = {}
        base_score = objective_func(base_params)
        
        for param_name, (min_val, max_val) in param_ranges.items():
            if param_name not in base_params:
                continue
            
            # 파라미터 값 범위에서 테스트
            test_values = np.linspace(min_val, max_val, 10)
            scores = []
            
            for test_val in test_values:
                test_params = base_params.copy()
                test_params[param_name] = test_val
                try:
                    score = objective_func(test_params)
                    scores.append(score)
                except Exception as e:
                    logger.warning(f"파라미터 테스트 실패: {param_name}={test_val}, 에러: {e}")
                    scores.append(base_score)
            
            sensitivity_results[param_name] = {
                "values": test_values.tolist(),
                "scores": scores,
                "sensitivity": np.std(scores) / base_score if base_score != 0 else 0,
            }
        
        return sensitivity_results

