"""그리드 서치 최적화 모듈"""

from typing import Dict, Any, List, Callable
import itertools
from tqdm import tqdm
from utils.logger import get_logger

logger = get_logger(__name__)


class GridSearchOptimizer:
    """그리드 서치 최적화 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        그리드 서치 최적화기 초기화
        
        Args:
            config: 최적화 설정
        """
        self.config = config
        self.parameters = config.get("parameters", {})
        self.objective = config.get("objective", {})
        self.constraints = self.objective.get("constraints", {})
        logger.info("그리드 서치 최적화기 초기화 완료")
    
    def optimize(self, objective_func: Callable) -> Dict[str, Any]:
        """
        그리드 서치 최적화 실행
        
        Args:
            objective_func: 목적 함수 (파라미터 딕셔너리를 받아 점수를 반환)
            
        Returns:
            최적화 결과
        """
        # 파라미터 그리드 생성
        param_grid = self._generate_param_grid()
        
        best_score = float('-inf')
        best_params = None
        results = []
        
        total_combinations = len(list(itertools.product(*param_grid.values())))
        logger.info(f"총 {total_combinations}개 조합 테스트 시작")
        
        # 모든 조합 테스트
        for params in tqdm(itertools.product(*param_grid.values()), total=total_combinations, desc="최적화 진행"):
            param_dict = dict(zip(param_grid.keys(), params))
            
            # 제약 조건 확인
            if not self._check_constraints(param_dict):
                continue
            
            # 목적 함수 평가
            try:
                score = objective_func(param_dict)
                
                results.append({
                    "params": param_dict,
                    "score": score,
                })
                
                if score > best_score:
                    best_score = score
                    best_params = param_dict
            except Exception as e:
                logger.warning(f"파라미터 평가 실패: {param_dict}, 에러: {e}")
                continue
        
        logger.info(f"최적 파라미터: {best_params}, 점수: {best_score}")
        
        return {
            "best_params": best_params,
            "best_score": best_score,
            "all_results": results,
        }
    
    def _generate_param_grid(self) -> Dict[str, List]:
        """파라미터 그리드 생성"""
        param_grid = {}
        
        for param_name, param_config in self.parameters.items():
            param_type = param_config.get("type")
            
            if param_type == "range":
                min_val = param_config.get("min")
                max_val = param_config.get("max")
                step = param_config.get("step", 1)
                param_grid[param_name] = list(range(min_val, max_val + 1, step))
            elif param_type == "choice":
                param_grid[param_name] = param_config.get("values", [])
            else:
                logger.warning(f"알 수 없는 파라미터 타입: {param_type}")
        
        return param_grid
    
    def _check_constraints(self, params: Dict[str, Any]) -> bool:
        """제약 조건 확인"""
        # 간단한 구현 (실제로는 백테스트 결과를 확인해야 함)
        return True

