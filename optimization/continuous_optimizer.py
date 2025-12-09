"""연속 최적화 모듈 - 목표 달성 시 자동 스냅샷 저장"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from analytics.metrics import PerformanceMetrics
from analytics.db_logger import DatabaseLogger
from utils.logger import get_logger
import pandas as pd
import time

logger = get_logger(__name__)


class ContinuousOptimizer:
    """연속 최적화 클래스 - 목표 달성 시 자동 기록"""
    
    def __init__(
        self,
        config: Dict[str, Any],
        db_logger: Optional[DatabaseLogger] = None,
        target_win_rate: float = 0.5,
        target_return: float = 0.0,
        base_ema: Optional[List[int]] = None,
        variation_range: int = 20,
        step_size: int = 5,
    ):
        """
        연속 최적화기 초기화
        
        Args:
            config: 설정
            db_logger: 데이터베이스 로거
            target_win_rate: 목표 승률 (기본 50%)
            target_return: 목표 수익률 (기본 0%)
            base_ema: 기준 EMA 값 [fast, mid, slow] (예: [20, 40, 80] 또는 [50, 100, 200])
            variation_range: 기준값에서 ±변동 범위 (기본 20)
            step_size: 조정 단위 (기본 5)
        """
        self.config = config
        self.db_logger = db_logger
        self.target_win_rate = target_win_rate
        self.target_return = target_return
        self.step_size = step_size
        
        # 기준 EMA 값 설정
        if base_ema is None:
            # 설정에서 가져오거나 기본값 사용
            indicators_config = config.get("indicators", {})
            ema_config = indicators_config.get("ema", {})
            periods = ema_config.get("periods", [20, 40, 80])
            self.base_ema = periods
        else:
            self.base_ema = base_ema
        
        self.variation_range = variation_range
        
        # 조합 생성
        self.param_combinations = self._generate_param_combinations()
        self.current_combination_idx = 0
        
        # 현재 최적 파라미터
        self.current_best_params = self._get_initial_params(config)
        self.optimization_history: List[Dict[str, Any]] = []
        self.snapshots: List[Dict[str, Any]] = []
        
        logger.info(f"연속 최적화기 초기화: 목표 승률={target_win_rate:.1%}, 목표 수익률={target_return:.1%}")
        logger.info(f"기준 EMA: {self.base_ema}, 변동 범위: ±{variation_range}, 단위: {step_size}")
        logger.info(f"총 {len(self.param_combinations)}개 조합 생성됨")
    
    def _generate_param_combinations(self) -> List[Dict[str, int]]:
        """기준값을 중심으로 5단위 조합 생성"""
        combinations = []
        
        # 각 EMA에 대해 기준값 ± variation_range 범위에서 step_size 단위로 생성
        fast_range = range(
            max(5, self.base_ema[0] - self.variation_range),
            min(200, self.base_ema[0] + self.variation_range + 1),
            self.step_size
        )
        mid_range = range(
            max(10, self.base_ema[1] - self.variation_range),
            min(200, self.base_ema[1] + self.variation_range + 1),
            self.step_size
        )
        slow_range = range(
            max(20, self.base_ema[2] - self.variation_range),
            min(200, self.base_ema[2] + self.variation_range + 1),
            self.step_size
        )
        
        # 모든 조합 생성 (fast < mid < slow 조건 유지)
        for fast in fast_range:
            for mid in mid_range:
                for slow in slow_range:
                    if fast < mid < slow:  # 순서 조건
                        combinations.append({
                            "ema_fast": fast,
                            "ema_mid": mid,
                            "ema_slow": slow,
                        })
        
        logger.info(f"총 {len(combinations)}개의 유효한 조합 생성됨")
        return combinations
    
    def _get_initial_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """초기 파라미터 추출"""
        # 첫 번째 조합 사용
        if self.param_combinations:
            params = self.param_combinations[0].copy()
        else:
            params = {
                "ema_fast": self.base_ema[0],
                "ema_mid": self.base_ema[1],
                "ema_slow": self.base_ema[2],
            }
        
        strategy_config = config.get("strategy", {})
        exit_config = strategy_config.get("exit", {})
        stop_loss_config = exit_config.get("stop_loss", {})
        params["atr_multiplier"] = stop_loss_config.get("atr_multiplier", 2.0)
        
        return params
    
    def get_next_params(self) -> Optional[Dict[str, Any]]:
        """
        다음 조합 파라미터 가져오기
        
        Returns:
            다음 파라미터 조합 (없으면 None)
        """
        if self.current_combination_idx >= len(self.param_combinations):
            return None
        
        params = self.param_combinations[self.current_combination_idx].copy()
        
        # ATR multiplier 추가
        strategy_config = self.config.get("strategy", {})
        exit_config = strategy_config.get("exit", {})
        stop_loss_config = exit_config.get("stop_loss", {})
        params["atr_multiplier"] = stop_loss_config.get("atr_multiplier", 2.0)
        
        self.current_combination_idx += 1
        return params
    
    def optimize_continuously(
        self,
        start_date: str,
        end_date: str,
        max_iterations: int = 100,
        step_size: int = 5,
    ) -> Dict[str, Any]:
        """
        연속적으로 최적화하며 목표 달성 시 스냅샷 저장
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD HH:MM)
            end_date: 종료 날짜 (YYYY-MM-DD HH:MM)
            max_iterations: 최대 반복 횟수
            step_size: 파라미터 조정 단위 (사용 안 함, 조합 사용)
            
        Returns:
            최적화 결과
        """
        # 다음 조합 가져오기
        next_params = self.get_next_params()
        if next_params:
            self.current_best_params = next_params
            return {
                "best_params": self.current_best_params,
                "best_score": 0.0,
                "iterations": self.current_combination_idx,
                "snapshots": self.snapshots,
            }
        else:
            # 모든 조합 완료
            return {
                "best_params": self.current_best_params,
                "best_score": 0.0,
                "iterations": len(self.param_combinations),
                "snapshots": self.snapshots,
            }
    
    def check_and_save_snapshot(
        self,
        metrics: PerformanceMetrics,
        params: Dict[str, Any],
        start_date: str,
        end_date: str,
        session_id: str,
    ) -> bool:
        """
        목표 달성 여부 확인 및 스냅샷 저장
        
        Args:
            metrics: 성능 지표
            params: 사용된 파라미터
            start_date: 시작 날짜
            end_date: 종료 날짜
            session_id: 세션 ID
            
        Returns:
            스냅샷 저장 여부
        """
        # 목표 달성 확인
        win_rate_achieved = metrics.win_rate >= self.target_win_rate
        return_achieved = metrics.total_return >= self.target_return
        
        if win_rate_achieved or return_achieved:
            snapshot = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "start_date": start_date,
                "end_date": end_date,
                "params": params.copy(),
                "metrics": {
                    "win_rate": metrics.win_rate,
                    "total_return": metrics.total_return,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "profit_factor": metrics.profit_factor,
                    "max_drawdown": metrics.max_drawdown,
                    "total_trades": metrics.total_trades,
                },
                "achieved_targets": {
                    "win_rate": win_rate_achieved,
                    "return": return_achieved,
                },
            }
            
            self.snapshots.append(snapshot)
            
            # DB에 저장
            if self.db_logger:
                try:
                    self._save_snapshot_to_db(snapshot)
                except Exception as e:
                    logger.error(f"스냅샷 DB 저장 실패: {e}")
            
            logger.info("=" * 60)
            logger.info("🎯 목표 달성! 스냅샷 저장됨")
            logger.info(f"승률: {metrics.win_rate:.2%} (목표: {self.target_win_rate:.1%})")
            logger.info(f"수익률: {metrics.total_return:.2%} (목표: {self.target_return:.1%})")
            logger.info(f"파라미터: {params}")
            logger.info("=" * 60)
            
            return True
        
        return False
    
    def _save_snapshot_to_db(self, snapshot: Dict[str, Any]):
        """스냅샷을 DB에 저장"""
        if self.db_logger:
            self.db_logger.save_optimization_snapshot(
                session_id=snapshot["session_id"],
                start_date=snapshot["start_date"],
                end_date=snapshot["end_date"],
                params=snapshot["params"],
                metrics=snapshot["metrics"],
                achieved_targets=snapshot["achieved_targets"],
            )
    
    def _adjust_params(
        self,
        current_params: Dict[str, Any],
        direction: Dict[str, str],
        step_size: int,
    ) -> Dict[str, Any]:
        """파라미터 조정 (더 이상 사용 안 함, 조합 방식 사용)"""
        # 이 메서드는 이제 사용하지 않지만 호환성을 위해 유지
        return current_params
    
    def apply_params_to_config(
        self,
        config: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """파라미터를 설정에 적용"""
        new_config = self._deep_copy_config(config)
        
        # EMA 기간 적용
        indicators_config = new_config.setdefault("indicators", {})
        ema_config = indicators_config.setdefault("ema", {})
        ema_config["periods"] = [
            params.get("ema_fast", 20),
            params.get("ema_mid", 40),
            params.get("ema_slow", 80),
        ]
        
        # ATR multiplier 적용
        strategy_config = new_config.setdefault("strategy", {})
        exit_config = strategy_config.setdefault("exit", {})
        stop_loss_config = exit_config.setdefault("stop_loss", {})
        stop_loss_config["atr_multiplier"] = params.get("atr_multiplier", 2.0)
        
        return new_config
    
    def _deep_copy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """설정 딕셔너리 깊은 복사"""
        import copy
        return copy.deepcopy(config)
    
    def get_current_best_params(self) -> Dict[str, Any]:
        """현재 최적 파라미터 반환"""
        return self.current_best_params.copy()
    
    def get_snapshots_summary(self) -> str:
        """스냅샷 요약 반환"""
        if not self.snapshots:
            return "저장된 스냅샷이 없습니다."
        
        summary = f"\n{'='*60}\n"
        summary += f"총 {len(self.snapshots)}개의 목표 달성 스냅샷\n"
        summary += f"{'='*60}\n"
        
        for i, snapshot in enumerate(self.snapshots, 1):
            summary += f"\n스냅샷 {i}:\n"
            summary += f"  기간: {snapshot['start_date']} ~ {snapshot['end_date']}\n"
            summary += f"  승률: {snapshot['metrics']['win_rate']:.2%}\n"
            summary += f"  수익률: {snapshot['metrics']['total_return']:.2%}\n"
            summary += f"  파라미터:\n"
            summary += f"    Fast EMA: {snapshot['params']['ema_fast']}\n"
            summary += f"    Mid EMA: {snapshot['params']['ema_mid']}\n"
            summary += f"    Slow EMA: {snapshot['params']['ema_slow']}\n"
            summary += f"    ATR Multiplier: {snapshot['params']['atr_multiplier']:.2f}\n"
        
        return summary

