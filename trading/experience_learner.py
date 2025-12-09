"""경험 학습자 - 거래 경험을 학습하고 진입 기준을 진화시킴"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from utils.logger import get_logger
import numpy as np
from collections import defaultdict

logger = get_logger(__name__)


class ExperienceLearner:
    """경험 학습자 - 승률이 높을 때만 배팅하도록 진화"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        경험 학습자 초기화
        
        Args:
            config: 설정
        """
        self.config = config
        
        # 학습 데이터
        self.trade_history: List[Dict[str, Any]] = []
        self.max_history = 1000
        
        # 패턴 분석
        self.pattern_performance: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
        })
        
        # 진입 조건별 성과
        self.condition_performance: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
        })
        
        # 최소 승률 임계값 (점진적으로 증가)
        self.min_win_rate_threshold = 0.40  # 초기 40%
        self.target_win_rate = 0.60  # 목표 60%
        self.learning_rate = 0.01  # 학습률
        
        # 최근 성과 추적
        self.recent_performance_window = 50  # 최근 50개 거래
        self.recent_win_rate = 0.0
        self.recent_avg_pnl = 0.0
        
        logger.info("경험 학습자 초기화 완료")
        logger.info(f"초기 최소 승률: {self.min_win_rate_threshold:.1%}")
        logger.info(f"목표 승률: {self.target_win_rate:.1%}")
    
    def record_trade(
        self,
        trade_result: Dict[str, Any],
        entry_conditions: Dict[str, Any],
        entry_reason: str,
    ):
        """
        거래 기록 및 학습
        
        Args:
            trade_result: 거래 결과 (pnl, win/loss 등)
            entry_conditions: 진입 조건 (레짐, 지표 값 등)
            entry_reason: 진입 이유
        """
        is_win = trade_result.get("pnl", 0.0) > 0
        
        # 거래 이력 추가
        trade_record = {
            "timestamp": datetime.now(),
            "pnl": trade_result.get("pnl", 0.0),
            "is_win": is_win,
            "entry_conditions": entry_conditions,
            "entry_reason": entry_reason,
            "confidence": entry_conditions.get("confidence", 0.0),
        }
        
        self.trade_history.append(trade_record)
        
        # 최근 이력만 유지
        if len(self.trade_history) > self.max_history:
            self.trade_history.pop(0)
        
        # 패턴 분석
        pattern_key = self._extract_pattern_key(entry_conditions)
        if pattern_key:
            pattern_stats = self.pattern_performance[pattern_key]
            if is_win:
                pattern_stats["wins"] += 1
            else:
                pattern_stats["losses"] += 1
            pattern_stats["total_pnl"] += trade_result.get("pnl", 0.0)
            pattern_stats["avg_pnl"] = pattern_stats["total_pnl"] / (pattern_stats["wins"] + pattern_stats["losses"])
        
        # 조건별 성과 분석
        for condition_key, condition_value in entry_conditions.items():
            if isinstance(condition_value, (int, float, str, bool)):
                condition_stats = self.condition_performance[f"{condition_key}:{condition_value}"]
                if is_win:
                    condition_stats["wins"] += 1
                else:
                    condition_stats["losses"] += 1
                condition_stats["total_pnl"] += trade_result.get("pnl", 0.0)
        
        # 최근 성과 업데이트
        self._update_recent_performance()
        
        # 최소 승률 임계값 조정 (학습)
        self._adjust_win_rate_threshold()
    
    def _extract_pattern_key(self, conditions: Dict[str, Any]) -> Optional[str]:
        """패턴 키 추출"""
        key_parts = []
        
        # 레짐
        if "regime" in conditions:
            key_parts.append(f"regime:{conditions['regime']}")
        
        # 신뢰도 구간
        confidence = conditions.get("confidence", 0.0)
        if confidence >= 0.9:
            key_parts.append("conf:high")
        elif confidence >= 0.75:
            key_parts.append("conf:mid")
        else:
            key_parts.append("conf:low")
        
        # 볼린저 밴드 위치
        if "bb_position" in conditions:
            key_parts.append(f"bb:{conditions['bb_position']}")
        
        return "_".join(key_parts) if key_parts else None
    
    def _update_recent_performance(self):
        """최근 성과 업데이트"""
        if len(self.trade_history) < 10:
            return
        
        recent_trades = self.trade_history[-self.recent_performance_window:]
        wins = sum(1 for t in recent_trades if t["is_win"])
        self.recent_win_rate = wins / len(recent_trades) if recent_trades else 0.0
        
        total_pnl = sum(t["pnl"] for t in recent_trades)
        self.recent_avg_pnl = total_pnl / len(recent_trades) if recent_trades else 0.0
    
    def _adjust_win_rate_threshold(self):
        """승률 임계값 조정 (학습)"""
        if len(self.trade_history) < 20:
            return
        
        # 최근 성과가 좋으면 임계값 상승
        if self.recent_win_rate > self.target_win_rate:
            # 목표 달성 시 임계값 상승
            self.min_win_rate_threshold += self.learning_rate
            self.min_win_rate_threshold = min(self.min_win_rate_threshold, 0.70)  # 최대 70%
        elif self.recent_win_rate < self.min_win_rate_threshold:
            # 성과가 나쁘면 임계값 하락 (하지만 너무 낮아지지 않도록)
            self.min_win_rate_threshold -= self.learning_rate * 0.5
            self.min_win_rate_threshold = max(self.min_win_rate_threshold, 0.30)  # 최소 30%
    
    def should_enter(
        self,
        entry_conditions: Dict[str, Any],
        predicted_win_rate: float,
    ) -> tuple[bool, str, Dict[str, Any]]:
        """
        진입 여부 결정 (학습된 기준 적용)
        
        Args:
            entry_conditions: 진입 조건
            predicted_win_rate: 예상 승률
            
        Returns:
            (진입 가능 여부, 이유, 상세 정보)
        """
        # 1. 최소 승률 임계값 확인
        if predicted_win_rate < self.min_win_rate_threshold:
            return False, f"예상 승률 부족: {predicted_win_rate:.1%} < {self.min_win_rate_threshold:.1%}", {
                "reason": "win_rate_threshold",
                "predicted": predicted_win_rate,
                "threshold": self.min_win_rate_threshold,
            }
        
        # 2. 패턴 성과 확인
        pattern_key = self._extract_pattern_key(entry_conditions)
        if pattern_key and pattern_key in self.pattern_performance:
            pattern_stats = self.pattern_performance[pattern_key]
            total_trades = pattern_stats["wins"] + pattern_stats["losses"]
            
            if total_trades >= 5:  # 충분한 데이터가 있을 때
                pattern_win_rate = pattern_stats["wins"] / total_trades if total_trades > 0 else 0.0
                
                if pattern_win_rate < self.min_win_rate_threshold:
                    return False, f"패턴 승률 부족: {pattern_win_rate:.1%} < {self.min_win_rate_threshold:.1%}", {
                        "reason": "pattern_win_rate",
                        "pattern": pattern_key,
                        "win_rate": pattern_win_rate,
                        "threshold": self.min_win_rate_threshold,
                    }
                
                # 평균 손익 확인
                if pattern_stats["avg_pnl"] < 0:
                    return False, f"패턴 평균 손익 음수: {pattern_stats['avg_pnl']:.2f}", {
                        "reason": "pattern_avg_pnl",
                        "pattern": pattern_key,
                        "avg_pnl": pattern_stats["avg_pnl"],
                    }
        
        # 3. 최근 성과 확인 (너무 나쁘면 거래 중단)
        if len(self.trade_history) >= 20:
            if self.recent_win_rate < 0.30 and self.recent_avg_pnl < 0:
                return False, f"최근 성과 불량: 승률 {self.recent_win_rate:.1%}, 평균 손익 {self.recent_avg_pnl:.2f}", {
                    "reason": "recent_performance",
                    "win_rate": self.recent_win_rate,
                    "avg_pnl": self.recent_avg_pnl,
                }
        
        return True, "OK", {
            "reason": "approved",
            "predicted_win_rate": predicted_win_rate,
            "threshold": self.min_win_rate_threshold,
        }
    
    def predict_win_rate(self, entry_conditions: Dict[str, Any]) -> float:
        """
        예상 승률 예측 (과거 패턴 기반)
        
        Args:
            entry_conditions: 진입 조건
            
        Returns:
            예상 승률 (0.0 ~ 1.0)
        """
        if len(self.trade_history) < 10:
            # 데이터가 부족하면 기본값
            return 0.50
        
        pattern_key = self._extract_pattern_key(entry_conditions)
        
        if pattern_key and pattern_key in self.pattern_performance:
            pattern_stats = self.pattern_performance[pattern_key]
            total_trades = pattern_stats["wins"] + pattern_stats["losses"]
            
            if total_trades >= 3:
                win_rate = pattern_stats["wins"] / total_trades
                # 신뢰도 가중 (거래 수가 많을수록 신뢰)
                confidence_weight = min(total_trades / 20, 1.0)
                return win_rate * confidence_weight + 0.50 * (1 - confidence_weight)
        
        # 패턴이 없으면 최근 전체 승률 사용
        return self.recent_win_rate if self.recent_win_rate > 0 else 0.50
    
    def get_learning_status(self) -> Dict[str, Any]:
        """학습 상태 반환"""
        return {
            "total_trades": len(self.trade_history),
            "min_win_rate_threshold": self.min_win_rate_threshold,
            "target_win_rate": self.target_win_rate,
            "recent_win_rate": self.recent_win_rate,
            "recent_avg_pnl": self.recent_avg_pnl,
            "learned_patterns": len(self.pattern_performance),
            "top_patterns": sorted(
                [
                    {
                        "pattern": k,
                        "win_rate": v["wins"] / (v["wins"] + v["losses"]) if (v["wins"] + v["losses"]) > 0 else 0.0,
                        "avg_pnl": v["avg_pnl"],
                        "trades": v["wins"] + v["losses"],
                    }
                    for k, v in self.pattern_performance.items()
                    if (v["wins"] + v["losses"]) >= 3
                ],
                key=lambda x: x["win_rate"],
                reverse=True,
            )[:5],
        }

