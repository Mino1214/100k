"""베이지안 최적화 모듈"""

from typing import Dict, Any, Callable
import optuna
from utils.logger import get_logger

logger = get_logger(__name__)


class BayesianOptimizer:
    """베이지안 최적화 클래스 (Optuna 사용)"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        베이지안 최적화기 초기화
        
        Args:
            config: 최적화 설정
        """
        self.config = config
        self.parameters = config.get("parameters", {})
        self.objective = config.get("objective", {})
        self.n_trials = config.get("n_trials", 100)
        logger.info(f"베이지안 최적화기 초기화: {self.n_trials}회 시도")
    
    def optimize(self, objective_func: Callable) -> Dict[str, Any]:
        """
        베이지안 최적화 실행
        
        Args:
            objective_func: 목적 함수 (파라미터 딕셔너리를 받아 점수를 반환)
            
        Returns:
            최적화 결과
        """
        def optuna_objective(trial):
            # 파라미터 제안
            params = {}
            for param_name, param_config in self.parameters.items():
                param_type = param_config.get("type")
                
                if param_type == "range":
                    min_val = param_config.get("min")
                    max_val = param_config.get("max")
                    params[param_name] = trial.suggest_int(param_name, min_val, max_val)
                elif param_type == "choice":
                    values = param_config.get("values", [])
                    params[param_name] = trial.suggest_categorical(param_name, values)
                else:
                    logger.warning(f"알 수 없는 파라미터 타입: {param_type}")
            
            # 목적 함수 평가
            return objective_func(params)
        
        # Optuna 스터디 생성
        study = optuna.create_study(direction="maximize")
        study.optimize(optuna_objective, n_trials=self.n_trials)
        
        logger.info(f"최적 파라미터: {study.best_params}, 점수: {study.best_value}")
        
        return {
            "best_params": study.best_params,
            "best_score": study.best_value,
            "study": study,
        }

