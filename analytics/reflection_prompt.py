"""자기반성 일지 생성 모듈"""

from typing import Dict, Any
from datetime import datetime
from analytics.metrics import PerformanceMetrics
from utils.logger import get_logger

logger = get_logger(__name__)


class ReflectionGenerator:
    """자기반성 일지 생성 클래스"""
    
    def __init__(self):
        """자기반성 일지 생성기 초기화"""
        logger.info("자기반성 일지 생성기 초기화 완료")
    
    def generate_reflection(
        self,
        metrics: PerformanceMetrics,
        session_id: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        자기반성 일지 생성
        
        Args:
            metrics: 성능 지표
            session_id: 세션 ID
            config: 설정
            
        Returns:
            자기반성 일지 딕셔너리
        """
        # 성과 평가 (1-10)
        performance_rating = self._calculate_performance_rating(metrics)
        
        # 강점 분석
        strengths = self._analyze_strengths(metrics)
        
        # 약점 분석
        weaknesses = self._analyze_weaknesses(metrics)
        
        # 배운 점
        lessons_learned = self._extract_lessons(metrics)
        
        # 개선 사항
        improvements = self._suggest_improvements(metrics, config)
        
        # 다음 행동 계획
        next_actions = self._plan_next_actions(metrics, performance_rating)
        
        # 감정 상태 (성과 기반)
        emotional_state = self._assess_emotional_state(metrics, performance_rating)
        
        # 종합 메모
        notes = self._generate_summary_notes(metrics, session_id)
        
        return {
            "performance_rating": performance_rating,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "lessons_learned": lessons_learned,
            "improvements": improvements,
            "next_actions": next_actions,
            "emotional_state": emotional_state,
            "notes": notes,
        }
    
    def _calculate_performance_rating(self, metrics: PerformanceMetrics) -> int:
        """성과 평가 점수 계산 (1-10)"""
        score = 5  # 기본 점수
        
        # 수익률 기반 점수
        if metrics.total_return > 0.2:  # 20% 이상
            score += 2
        elif metrics.total_return > 0.1:  # 10% 이상
            score += 1
        elif metrics.total_return < -0.1:  # -10% 미만
            score -= 2
        elif metrics.total_return < 0:  # 음수
            score -= 1
        
        # Sharpe 비율 기반
        if metrics.sharpe_ratio > 2:
            score += 1
        elif metrics.sharpe_ratio > 1:
            score += 0.5
        elif metrics.sharpe_ratio < 0:
            score -= 1
        
        # 승률 기반
        if metrics.win_rate > 0.6:
            score += 0.5
        elif metrics.win_rate < 0.4:
            score -= 0.5
        
        # Profit Factor 기반
        if metrics.profit_factor > 2:
            score += 0.5
        elif metrics.profit_factor < 1:
            score -= 1
        
        # 드로다운 기반
        if metrics.max_drawdown < -0.1:  # -10% 미만
            score -= 1
        elif metrics.max_drawdown < -0.2:  # -20% 미만
            score -= 2
        
        # 거래 수 기반 (충분한 샘플)
        if metrics.total_trades < 10:
            score -= 1
        
        # 1-10 범위로 제한
        return max(1, min(10, int(score)))
    
    def _analyze_strengths(self, metrics: PerformanceMetrics) -> str:
        """강점 분석"""
        strengths = []
        
        if metrics.total_return > 0:
            strengths.append(f"양의 수익률 달성 ({metrics.total_return:.2%})")
        
        if metrics.sharpe_ratio > 1:
            strengths.append(f"우수한 리스크 조정 수익률 (Sharpe: {metrics.sharpe_ratio:.2f})")
        
        if metrics.win_rate > 0.5:
            strengths.append(f"높은 승률 ({metrics.win_rate:.2%})")
        
        if metrics.profit_factor > 1.5:
            strengths.append(f"양호한 Profit Factor ({metrics.profit_factor:.2f})")
        
        if metrics.max_drawdown > -0.15:
            strengths.append(f"안정적인 드로다운 관리 (Max DD: {metrics.max_drawdown:.2%})")
        
        if metrics.total_trades > 50:
            strengths.append(f"충분한 거래 샘플 ({metrics.total_trades}건)")
        
        if metrics.expectancy > 0:
            strengths.append(f"양의 기대값 ({metrics.expectancy:.2f})")
        
        return "; ".join(strengths) if strengths else "특별한 강점이 발견되지 않았습니다."
    
    def _analyze_weaknesses(self, metrics: PerformanceMetrics) -> str:
        """약점 분석"""
        weaknesses = []
        
        if metrics.total_return < 0:
            weaknesses.append(f"음의 수익률 ({metrics.total_return:.2%})")
        
        if metrics.sharpe_ratio < 0.5:
            weaknesses.append(f"낮은 리스크 조정 수익률 (Sharpe: {metrics.sharpe_ratio:.2f})")
        
        if metrics.win_rate < 0.4:
            weaknesses.append(f"낮은 승률 ({metrics.win_rate:.2%})")
        
        if metrics.profit_factor < 1:
            weaknesses.append(f"부정적인 Profit Factor ({metrics.profit_factor:.2f})")
        
        if metrics.max_drawdown < -0.2:
            weaknesses.append(f"큰 드로다운 (Max DD: {metrics.max_drawdown:.2%})")
        
        if metrics.total_trades < 20:
            weaknesses.append(f"부족한 거래 샘플 ({metrics.total_trades}건)")
        
        if metrics.expectancy < 0:
            weaknesses.append(f"음의 기대값 ({metrics.expectancy:.2f})")
        
        if abs(metrics.avg_loss) > abs(metrics.avg_win) * 1.5:
            weaknesses.append("평균 손실이 평균 수익보다 크게 발생")
        
        return "; ".join(weaknesses) if weaknesses else "명확한 약점이 발견되지 않았습니다."
    
    def _extract_lessons(self, metrics: PerformanceMetrics) -> str:
        """배운 점 추출"""
        lessons = []
        
        if metrics.total_trades > 0:
            lessons.append(f"총 {metrics.total_trades}건의 거래를 통해 전략의 실효성을 검증했습니다.")
        
        if metrics.win_rate > 0.5:
            lessons.append("승률이 50%를 넘어 전략의 방향성이 올바른 것으로 판단됩니다.")
        else:
            lessons.append("승률이 낮아 진입 조건을 재검토해야 합니다.")
        
        if metrics.profit_factor > 1.5:
            lessons.append("Profit Factor가 양호하여 수익 거래가 손실 거래를 상회합니다.")
        else:
            lessons.append("손익 비율을 개선하기 위해 리스크 관리가 필요합니다.")
        
        if metrics.max_drawdown < -0.15:
            lessons.append("드로다운이 크게 발생하여 포지션 사이징과 스탑로스 설정을 재검토해야 합니다.")
        
        return " ".join(lessons)
    
    def _suggest_improvements(self, metrics: PerformanceMetrics, config: Dict[str, Any]) -> str:
        """개선 사항 제안"""
        improvements = []
        
        if metrics.win_rate < 0.4:
            improvements.append("진입 조건을 더 엄격하게 설정하여 승률을 높입니다.")
        
        if metrics.profit_factor < 1:
            improvements.append("트레일링 스탑을 조정하여 수익 거래의 이익을 극대화합니다.")
        
        if metrics.max_drawdown < -0.2:
            improvements.append("포지션 사이징을 줄이거나 스탑로스 거리를 조정합니다.")
        
        if metrics.total_trades < 20:
            improvements.append("더 많은 거래 기회를 확보하기 위해 진입 조건을 완화합니다.")
        
        if metrics.sharpe_ratio < 0.5:
            improvements.append("변동성을 줄이기 위해 레짐 필터를 강화합니다.")
        
        # 설정 기반 개선 사항
        risk_config = config.get("risk", {})
        position_sizing = risk_config.get("position_sizing", {})
        if position_sizing.get("method") == "fixed":
            improvements.append("고정 포지션 사이징 대신 리스크 기반 사이징을 고려합니다.")
        
        return "; ".join(improvements) if improvements else "현재 설정이 적절합니다."
    
    def _plan_next_actions(self, metrics: PerformanceMetrics, rating: int) -> str:
        """다음 행동 계획"""
        actions = []
        
        if rating >= 7:
            actions.append("현재 전략을 유지하면서 파라미터 미세 조정을 진행합니다.")
            actions.append("실전 거래를 위한 소액 테스트를 고려합니다.")
        elif rating >= 5:
            actions.append("주요 파라미터를 최적화하여 성과를 개선합니다.")
            actions.append("다른 시장 조건에서의 백테스트를 추가로 진행합니다.")
        else:
            actions.append("전략의 핵심 로직을 재검토합니다.")
            actions.append("다른 전략 접근법을 탐색합니다.")
        
        actions.append("다음 백테스트에서는 개선된 파라미터로 재실행합니다.")
        
        return "; ".join(actions)
    
    def _assess_emotional_state(self, metrics: PerformanceMetrics, rating: int) -> str:
        """감정 상태 평가"""
        if rating >= 8:
            return "매우 긍정적"
        elif rating >= 6:
            return "긍정적"
        elif rating >= 4:
            return "중립적"
        elif rating >= 2:
            return "부정적"
        else:
            return "매우 부정적"
    
    def _generate_summary_notes(self, metrics: PerformanceMetrics, session_id: str) -> str:
        """종합 메모 생성"""
        return f"""
세션 ID: {session_id}
실행 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

주요 성과:
- 총 수익률: {metrics.total_return:.2%}
- 연환산 수익률: {metrics.annualized_return:.2%}
- Sharpe 비율: {metrics.sharpe_ratio:.2f}
- 최대 드로다운: {metrics.max_drawdown:.2%}
- 승률: {metrics.win_rate:.2%}
- Profit Factor: {metrics.profit_factor:.2f}
- 총 거래 수: {metrics.total_trades}건
- 기대값: {metrics.expectancy:.2f}

이번 백테스트를 통해 전략의 성과를 객관적으로 평가하고, 
개선점을 도출하여 다음 단계로 나아갈 수 있는 기반을 마련했습니다.
        """.strip()

