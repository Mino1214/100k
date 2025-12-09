"""트레이딩 마인드 - 사람처럼 생각하고 결정하는 시스템"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from utils.logger import get_logger
import json

logger = get_logger(__name__)


class TradingMind:
    """트레이딩 마인드 - 거래 결정을 내리는 "마음" 시스템"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        트레이딩 마인드 초기화
        
        Args:
            config: 설정
        """
        self.config = config
        
        # 생각 로그
        self.thought_log: List[Dict[str, Any]] = []
        self.max_thoughts = 500
        
        # 현재 상태
        self.current_mood = "neutral"  # neutral, cautious, confident, greedy, fearful
        self.confidence_level = 0.5
        
        logger.info("트레이딩 마인드 초기화 완료")
    
    def think_about_entry(
        self,
        market_data: Dict[str, Any],
        entry_conditions: Dict[str, Any],
        predicted_win_rate: float,
        risk_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        진입에 대해 생각하고 결정
        
        Args:
            market_data: 시장 데이터
            entry_conditions: 진입 조건
            risk_assessment: 리스크 평가
            
        Returns:
            생각과 결정
        """
        thought = {
            "timestamp": datetime.now().isoformat(),
            "type": "entry_decision",
            "market_situation": self._analyze_market_situation(market_data),
            "entry_conditions": entry_conditions,
            "predicted_win_rate": predicted_win_rate,
            "risk_assessment": risk_assessment,
            "reasoning": [],
            "concerns": [],
            "confidence": 0.0,
            "decision": "pending",
            "detailed_reason": "",
        }
        
        # 1. 시장 상황 분석
        market_analysis = self._analyze_market_situation(market_data)
        thought["reasoning"].append(f"시장 상황: {market_analysis['summary']}")
        
        # 2. 진입 조건 평가
        condition_eval = self._evaluate_entry_conditions(entry_conditions)
        thought["reasoning"].extend(condition_eval["reasons"])
        thought["concerns"].extend(condition_eval["concerns"])
        
        # 3. 승률 평가
        if predicted_win_rate >= 0.70:
            thought["reasoning"].append(f"높은 예상 승률: {predicted_win_rate:.1%} - 강한 진입 신호")
            thought["confidence"] += 0.3
        elif predicted_win_rate >= 0.60:
            thought["reasoning"].append(f"양호한 예상 승률: {predicted_win_rate:.1%} - 진입 고려")
            thought["confidence"] += 0.2
        elif predicted_win_rate >= 0.50:
            thought["reasoning"].append(f"보통 예상 승률: {predicted_win_rate:.1%} - 신중한 접근 필요")
            thought["confidence"] += 0.1
        else:
            thought["concerns"].append(f"낮은 예상 승률: {predicted_win_rate:.1%} - 진입 위험")
            thought["confidence"] -= 0.2
        
        # 4. 리스크 평가
        risk_eval = self._evaluate_risk(risk_assessment)
        thought["reasoning"].extend(risk_eval["reasons"])
        thought["concerns"].extend(risk_eval["concerns"])
        thought["confidence"] += risk_eval["confidence_adjustment"]
        
        # 5. 최종 결정
        thought["confidence"] = max(0.0, min(1.0, thought["confidence"]))
        
        if thought["confidence"] >= 0.7 and len(thought["concerns"]) == 0:
            thought["decision"] = "enter"
            thought["mood"] = "confident"
        elif thought["confidence"] >= 0.6 and len(thought["concerns"]) <= 1:
            thought["decision"] = "enter"
            thought["mood"] = "cautious"
        elif thought["confidence"] >= 0.5:
            thought["decision"] = "wait"
            thought["mood"] = "cautious"
        else:
            thought["decision"] = "skip"
            thought["mood"] = "fearful"
        
        # 6. 상세한 진입 이유 생성
        thought["detailed_reason"] = self._generate_detailed_reason(thought)
        
        # 생각 로그에 추가
        self._log_thought(thought)
        
        # 기분 업데이트
        self.current_mood = thought.get("mood", "neutral")
        self.confidence_level = thought["confidence"]
        
        return thought
    
    def _analyze_market_situation(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """시장 상황 분석"""
        regime = market_data.get("regime", "unknown")
        price = market_data.get("price", 0.0)
        volume = market_data.get("volume", 0.0)
        volume_ma = market_data.get("volume_ma", volume)
        atr = market_data.get("atr", 0.0)
        price_change = market_data.get("price_change_pct", 0.0)
        
        summary_parts = []
        
        # 레짐 분석
        if regime == "bull":
            summary_parts.append("강세장")
        elif regime == "bear":
            summary_parts.append("약세장")
        else:
            summary_parts.append("횡보장")
        
        # 변동성 분석
        volatility_pct = (atr / price * 100) if price > 0 else 0.0
        if volatility_pct > 3.0:
            summary_parts.append("고변동성")
        elif volatility_pct < 1.0:
            summary_parts.append("저변동성")
        
        # 거래량 분석
        if volume_ma > 0:
            volume_ratio = volume / volume_ma
            if volume_ratio > 1.5:
                summary_parts.append("거래량 급증")
            elif volume_ratio < 0.5:
                summary_parts.append("거래량 부족")
        
        # 가격 움직임
        if abs(price_change) > 2.0:
            summary_parts.append(f"가격 급변 ({price_change:+.1f}%)")
        
        return {
            "regime": regime,
            "volatility_pct": volatility_pct,
            "volume_ratio": volume / volume_ma if volume_ma > 0 else 1.0,
            "price_change_pct": price_change,
            "summary": ", ".join(summary_parts) if summary_parts else "정상",
        }
    
    def _evaluate_entry_conditions(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """진입 조건 평가"""
        reasons = []
        concerns = []
        
        # 레짐 확인
        regime = conditions.get("regime")
        if regime == "bull":
            reasons.append("강세장 레짐 확인 - Long 진입에 유리")
        elif regime == "bear":
            reasons.append("약세장 레짐 확인 - Short 진입에 유리")
        else:
            concerns.append("횡보장 - 진입 신중 필요")
        
        # 볼린저 밴드 위치
        bb_position = conditions.get("bb_position")
        if bb_position == "lower_touch":
            reasons.append("가격이 볼린저 밴드 하단 터치 - 반등 가능성")
        elif bb_position == "upper_touch":
            reasons.append("가격이 볼린저 밴드 상단 터치 - 조정 가능성")
        
        # EMA 정렬
        ema_alignment = conditions.get("ema_alignment")
        if ema_alignment:
            reasons.append(f"EMA 정렬 확인: {ema_alignment}")
        
        # 신뢰도
        confidence = conditions.get("confidence", 0.0)
        if confidence >= 0.8:
            reasons.append(f"높은 신뢰도: {confidence:.1%}")
        elif confidence < 0.6:
            concerns.append(f"낮은 신뢰도: {confidence:.1%}")
        
        return {
            "reasons": reasons,
            "concerns": concerns,
        }
    
    def _evaluate_risk(self, risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """리스크 평가"""
        reasons = []
        concerns = []
        confidence_adjustment = 0.0
        
        # 시드 단계
        stage = risk_assessment.get("stage", "unknown")
        if stage == "seedling":
            reasons.append("초기 시드 단계 - 보수적 접근")
            concerns.append("시드가 작아 리스크 관리 중요")
        elif stage == "prosperous":
            reasons.append("번영 단계 - 여유 있는 리스크 관리 가능")
            confidence_adjustment += 0.1
        
        # 일일 리스크
        daily_risk_ratio = risk_assessment.get("daily_risk_ratio", 0.0)
        if daily_risk_ratio > 0.8:
            concerns.append(f"일일 리스크 거의 소진: {daily_risk_ratio:.1%}")
            confidence_adjustment -= 0.2
        elif daily_risk_ratio < 0.3:
            reasons.append(f"일일 리스크 여유: {daily_risk_ratio:.1%}")
            confidence_adjustment += 0.1
        
        # 연속 손실
        consecutive_losses = risk_assessment.get("consecutive_losses", 0)
        if consecutive_losses >= 2:
            concerns.append(f"연속 손실 {consecutive_losses}회 - 신중 필요")
            confidence_adjustment -= 0.15
        
        return {
            "reasons": reasons,
            "concerns": concerns,
            "confidence_adjustment": confidence_adjustment,
        }
    
    def _generate_detailed_reason(self, thought: Dict[str, Any]) -> str:
        """상세한 진입 이유 생성 (텍스트)"""
        parts = []
        
        # 시장 상황
        market = thought.get("market_situation", {})
        parts.append(f"【시장 상황】{market.get('summary', '분석 중')}")
        
        # 진입 조건
        parts.append("\n【진입 조건 분석】")
        for reason in thought.get("reasoning", []):
            if "시장 상황" not in reason:
                parts.append(f"  ✓ {reason}")
        
        # 우려사항
        if thought.get("concerns"):
            parts.append("\n【우려사항】")
            for concern in thought["concerns"]:
                parts.append(f"  ⚠ {concern}")
        
        # 승률
        win_rate = thought.get("predicted_win_rate", 0.0)
        parts.append(f"\n【예상 승률】{win_rate:.1%}")
        
        # 신뢰도
        confidence = thought.get("confidence", 0.0)
        parts.append(f"【신뢰도】{confidence:.1%}")
        
        # 최종 결정
        decision = thought.get("decision", "pending")
        decision_text = {
            "enter": "진입 결정",
            "wait": "대기 결정",
            "skip": "진입 포기",
        }.get(decision, "미결정")
        parts.append(f"\n【최종 결정】{decision_text}")
        
        if decision == "enter":
            parts.append("\n이 거래는 다음 이유로 진입합니다:")
            parts.append("  1. 시장 조건이 진입에 유리함")
            parts.append("  2. 예상 승률이 임계값을 초과함")
            parts.append("  3. 리스크가 허용 범위 내임")
        elif decision == "wait":
            parts.append("\n더 나은 기회를 기다립니다.")
        elif decision == "skip":
            parts.append("\n리스크가 너무 크거나 조건이 불충분합니다.")
        
        return "\n".join(parts)
    
    def _log_thought(self, thought: Dict[str, Any]):
        """생각 로그에 추가"""
        self.thought_log.append(thought)
        
        # 최근 생각만 유지
        if len(self.thought_log) > self.max_thoughts:
            self.thought_log.pop(0)
        
        # 로그 출력
        logger.info("=" * 60)
        logger.info("🧠 트레이딩 마인드 생각:")
        logger.info(thought["detailed_reason"])
        logger.info("=" * 60)
    
    def get_recent_thoughts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 생각 반환"""
        return self.thought_log[-limit:] if self.thought_log else []

