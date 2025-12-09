"""Reflection 기반 자동 최적화 모듈"""

from typing import Dict, Any, List, Optional
from analytics.reflection_prompt import ReflectionGenerator
from analytics.metrics import PerformanceMetrics
from analytics.db_logger import DatabaseLogger
from utils.logger import get_logger
import pandas as pd

logger = get_logger(__name__)


class ReflectionOptimizer:
    """Reflection 기반 자동 최적화 클래스"""
    
    def __init__(self, config: Dict[str, Any], db_logger: Optional[DatabaseLogger] = None):
        """
        Reflection 최적화기 초기화
        
        Args:
            config: 설정
            db_logger: 데이터베이스 로거 (선택)
        """
        self.config = config
        self.db_logger = db_logger
        self.reflection_gen = ReflectionGenerator()
        self.optimization_history: List[Dict[str, Any]] = []
        logger.info("Reflection 기반 최적화기 초기화 완료")
    
    def optimize_from_reflection(
        self,
        metrics: PerformanceMetrics,
        session_id: str,
        current_config: Dict[str, Any],
        max_iterations: int = 5,
    ) -> Dict[str, Any]:
        """
        Reflection 결과를 기반으로 파라미터 자동 조정 및 최적화
        
        Args:
            metrics: 현재 성능 지표
            session_id: 현재 세션 ID
            current_config: 현재 설정
            max_iterations: 최대 반복 횟수
            
        Returns:
            최적화된 설정 및 결과
        """
        logger.info(f"Reflection 기반 최적화 시작 (최대 {max_iterations}회 반복)")
        
        best_config = current_config.copy()
        best_score = self._calculate_score(metrics)
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"반복 {iteration}/{max_iterations}")
            logger.info(f"{'='*60}")
            
            # Reflection 생성
            reflection = self.reflection_gen.generate_reflection(
                metrics, session_id, best_config
            )
            
            logger.info(f"성과 평가: {reflection['performance_rating']}/10")
            logger.info(f"강점: {reflection['strengths']}")
            logger.info(f"약점: {reflection['weaknesses']}")
            logger.info(f"개선 사항: {reflection['improvements']}")
            
            # 파라미터 조정 방향 결정
            adjustments = self._determine_adjustments(reflection, metrics, best_config)
            
            if not adjustments:
                logger.info("더 이상 개선할 수 없습니다.")
                break
            
            # 파라미터 조정
            new_config = self._apply_adjustments(best_config, adjustments)
            
            # 조정된 설정 저장
            self.optimization_history.append({
                "iteration": iteration,
                "config": new_config.copy(),
                "reflection": reflection,
                "adjustments": adjustments,
            })
            
            logger.info(f"파라미터 조정: {adjustments}")
            
            # 새로운 설정 반환 (실제 백테스트는 호출자가 실행)
            best_config = new_config
            
            # 성과가 충분히 좋으면 조기 종료
            if reflection['performance_rating'] >= 8:
                logger.info("목표 성과 달성! 조기 종료")
                break
        
        logger.info(f"\n최적화 완료! 총 {iteration}회 반복")
        
        return {
            "best_config": best_config,
            "best_score": best_score,
            "iterations": iteration,
            "history": self.optimization_history,
        }
    
    def _calculate_score(self, metrics: PerformanceMetrics) -> float:
        """종합 점수 계산"""
        score = 0.0
        
        # Sharpe 비율 (가중치: 0.4)
        if metrics.sharpe_ratio is not None:
            score += metrics.sharpe_ratio * 0.4
        
        # 수익률 (가중치: 0.3)
        score += metrics.total_return * 0.3
        
        # Profit Factor (가중치: 0.2)
        if metrics.profit_factor is not None:
            score += (metrics.profit_factor - 1) * 0.2
        
        # 드로다운 (가중치: -0.1, 음수이므로 빼기)
        score += metrics.max_drawdown * 0.1
        
        return score
    
    def _determine_adjustments(
        self,
        reflection: Dict[str, Any],
        metrics: PerformanceMetrics,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Reflection 결과를 기반으로 파라미터 조정 방향 결정
        
        Args:
            reflection: Reflection 결과
            metrics: 성능 지표
            config: 현재 설정
            
        Returns:
            조정할 파라미터 딕셔너리
        """
        adjustments = {}
        
        # 약점 분석 기반 조정
        weaknesses = reflection.get("weaknesses", "")
        improvements = reflection.get("improvements", "")
        
        # 승률이 낮은 경우
        if metrics.win_rate < 0.4:
            # 진입 조건을 더 엄격하게 (EMA 기간 증가)
            adjustments["ema_fast"] = self._adjust_ema_period(
                config, "ema_fast", direction="increase", amount=5
            )
            adjustments["ema_mid"] = self._adjust_ema_period(
                config, "ema_mid", direction="increase", amount=10
            )
        
        # Profit Factor가 낮은 경우
        if metrics.profit_factor < 1.0:
            # 스탑로스 거리 조정 (ATR multiplier 증가)
            adjustments["atr_multiplier"] = self._adjust_atr_multiplier(
                config, direction="increase", amount=0.5
            )
        
        # 드로다운이 큰 경우
        if metrics.max_drawdown < -0.2:
            # 포지션 사이징 감소 또는 스탑로스 강화
            adjustments["atr_multiplier"] = self._adjust_atr_multiplier(
                config, direction="decrease", amount=0.3
            )
            adjustments["risk_per_trade"] = self._adjust_risk_per_trade(
                config, direction="decrease", amount=0.5
            )
        
        # 거래 수가 너무 적은 경우
        if metrics.total_trades < 20:
            # 진입 조건 완화 (EMA 기간 감소)
            adjustments["ema_fast"] = self._adjust_ema_period(
                config, "ema_fast", direction="decrease", amount=5
            )
        
        # Sharpe 비율이 낮은 경우
        if metrics.sharpe_ratio < 0.5:
            # 변동성 필터 강화 (BB period 증가)
            adjustments["bb_period"] = self._adjust_bb_period(
                config, direction="increase", amount=5
            )
        
        # 수익률이 음수인 경우
        if metrics.total_return < 0:
            # 전략 방향 재검토 (EMA 기간 조정)
            if "ema_fast" not in adjustments:
                adjustments["ema_fast"] = self._adjust_ema_period(
                    config, "ema_fast", direction="increase", amount=5
                )
        
        return adjustments
    
    def _adjust_ema_period(
        self,
        config: Dict[str, Any],
        ema_key: str,
        direction: str,
        amount: int,
    ) -> int:
        """EMA 기간 조정"""
        indicators_config = config.get("indicators", {})
        ema_config = indicators_config.get("ema", {})
        periods = ema_config.get("periods", [20, 40, 80])
        
        if ema_key == "ema_fast":
            current = periods[0]
        elif ema_key == "ema_mid":
            current = periods[1]
        elif ema_key == "ema_slow":
            current = periods[2]
        else:
            return periods[0]
        
        if direction == "increase":
            new_value = min(current + amount, 200)  # 최대 200
        else:
            new_value = max(current - amount, 5)  # 최소 5
        
        return new_value
    
    def _adjust_atr_multiplier(
        self,
        config: Dict[str, Any],
        direction: str,
        amount: float,
    ) -> float:
        """ATR multiplier 조정"""
        strategy_config = config.get("strategy", {})
        exit_config = strategy_config.get("exit", {})
        stop_loss_config = exit_config.get("stop_loss", {})
        current = stop_loss_config.get("atr_multiplier", 2.0)
        
        if direction == "increase":
            new_value = min(current + amount, 5.0)  # 최대 5.0
        else:
            new_value = max(current - amount, 0.5)  # 최소 0.5
        
        return new_value
    
    def _adjust_bb_period(
        self,
        config: Dict[str, Any],
        direction: str,
        amount: int,
    ) -> int:
        """Bollinger Bands 기간 조정"""
        indicators_config = config.get("indicators", {})
        bb_config = indicators_config.get("bollinger", {})
        current = bb_config.get("period", 20)
        
        if direction == "increase":
            new_value = min(current + amount, 50)  # 최대 50
        else:
            new_value = max(current - amount, 10)  # 최소 10
        
        return new_value
    
    def _adjust_risk_per_trade(
        self,
        config: Dict[str, Any],
        direction: str,
        amount: float,
    ) -> float:
        """거래당 리스크 조정"""
        risk_config = config.get("risk", {})
        position_sizing = risk_config.get("position_sizing", {})
        current = position_sizing.get("risk_per_trade", 0.02)  # 2%
        
        if direction == "increase":
            new_value = min(current + amount, 0.05)  # 최대 5%
        else:
            new_value = max(current - amount, 0.01)  # 최소 1%
        
        return new_value
    
    def _apply_adjustments(
        self,
        config: Dict[str, Any],
        adjustments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """파라미터 조정 적용"""
        new_config = self._deep_copy_config(config)
        
        # EMA 기간 조정
        if "ema_fast" in adjustments or "ema_mid" in adjustments or "ema_slow" in adjustments:
            indicators_config = new_config.setdefault("indicators", {})
            ema_config = indicators_config.setdefault("ema", {})
            periods = ema_config.get("periods", [20, 40, 80]).copy()
            
            if "ema_fast" in adjustments:
                periods[0] = adjustments["ema_fast"]
            if "ema_mid" in adjustments:
                periods[1] = adjustments["ema_mid"]
            if "ema_slow" in adjustments:
                periods[2] = adjustments["ema_slow"]
            
            ema_config["periods"] = periods
        
        # ATR multiplier 조정
        if "atr_multiplier" in adjustments:
            strategy_config = new_config.setdefault("strategy", {})
            exit_config = strategy_config.setdefault("exit", {})
            stop_loss_config = exit_config.setdefault("stop_loss", {})
            stop_loss_config["atr_multiplier"] = adjustments["atr_multiplier"]
        
        # BB period 조정
        if "bb_period" in adjustments:
            indicators_config = new_config.setdefault("indicators", {})
            bb_config = indicators_config.setdefault("bollinger", {})
            bb_config["period"] = adjustments["bb_period"]
        
        # Risk per trade 조정
        if "risk_per_trade" in adjustments:
            risk_config = new_config.setdefault("risk", {})
            position_sizing = risk_config.setdefault("position_sizing", {})
            position_sizing["risk_per_trade"] = adjustments["risk_per_trade"]
        
        return new_config
    
    def _deep_copy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """설정 딕셔너리 깊은 복사"""
        import copy
        return copy.deepcopy(config)
    
    def get_optimization_summary(self) -> str:
        """최적화 요약 반환"""
        if not self.optimization_history:
            return "최적화 이력이 없습니다."
        
        summary = "Reflection 기반 최적화 요약:\n"
        summary += "=" * 60 + "\n"
        
        for entry in self.optimization_history:
            summary += f"\n반복 {entry['iteration']}:\n"
            summary += f"  조정 사항: {entry['adjustments']}\n"
            summary += f"  성과 평가: {entry['reflection']['performance_rating']}/10\n"
            summary += f"  약점: {entry['reflection']['weaknesses']}\n"
        
        return summary

