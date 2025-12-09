"""거래 일지 생성기 - 모든 거래를 상세히 기록"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from utils.logger import get_logger
import json
from pathlib import Path
import pandas as pd

logger = get_logger(__name__)


class TradeJournal:
    """거래 일지 생성기 - 상세한 거래 기록"""
    
    def __init__(self, config: Dict[str, Any], output_path: str = "./logs/journals/"):
        """
        거래 일지 생성기 초기화
        
        Args:
            config: 설정
            output_path: 출력 경로
        """
        self.config = config
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # 일지 데이터
        self.journals: List[Dict[str, Any]] = []
        self.max_journals = 1000
        
        logger.info(f"거래 일지 생성기 초기화: {self.output_path}")
    
    def create_journal_entry(
        self,
        trade_result: Dict[str, Any],
        entry_decision: Dict[str, Any],
        market_data_at_entry: Dict[str, Any],
        market_data_at_exit: Dict[str, Any],
        failure_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        거래 일지 항목 생성
        
        Args:
            trade_result: 거래 결과
            entry_decision: 진입 결정 (트레이딩 마인드의 생각)
            market_data_at_entry: 진입 시 시장 데이터
            market_data_at_exit: 청산 시 시장 데이터
            failure_analysis: 실패 분석 (손실 거래인 경우)
            
        Returns:
            일지 항목
        """
        journal = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_result.get("trade_id", f"trade_{datetime.now().timestamp()}"),
            "result": "win" if trade_result.get("pnl", 0.0) > 0 else "loss",
            "pnl": trade_result.get("pnl", 0.0),
            "pnl_pct": trade_result.get("pnl_pct", 0.0),
            "entry": {
                "timestamp": market_data_at_entry.get("timestamp"),
                "price": market_data_at_entry.get("price", 0.0),
                "volume": market_data_at_entry.get("volume", 0.0),
                "volume_ma": market_data_at_entry.get("volume_ma", 0.0),
                "volume_ratio": market_data_at_entry.get("volume", 0.0) / market_data_at_entry.get("volume_ma", 1.0) if market_data_at_entry.get("volume_ma", 0.0) > 0 else 1.0,
                "atr": market_data_at_entry.get("atr", 0.0),
                "volatility_pct": (market_data_at_entry.get("atr", 0.0) / market_data_at_entry.get("price", 1.0)) * 100 if market_data_at_entry.get("price", 0.0) > 0 else 0.0,
                "regime": market_data_at_entry.get("regime", "unknown"),
                "decision_reason": entry_decision.get("detailed_reason", ""),
                "confidence": entry_decision.get("confidence", 0.0),
                "predicted_win_rate": entry_decision.get("predicted_win_rate", 0.0),
            },
            "exit": {
                "timestamp": market_data_at_exit.get("timestamp"),
                "price": market_data_at_exit.get("price", 0.0),
                "volume": market_data_at_exit.get("volume", 0.0),
                "volume_ma": market_data_at_exit.get("volume_ma", 0.0),
                "volume_ratio": market_data_at_exit.get("volume", 0.0) / market_data_at_exit.get("volume_ma", 1.0) if market_data_at_exit.get("volume_ma", 0.0) > 0 else 1.0,
                "atr": market_data_at_exit.get("atr", 0.0),
                "volatility_pct": (market_data_at_exit.get("atr", 0.0) / market_data_at_exit.get("price", 1.0)) * 100 if market_data_at_exit.get("price", 0.0) > 0 else 0.0,
                "regime": market_data_at_exit.get("regime", "unknown"),
                "reason": trade_result.get("exit_reason", "unknown"),
            },
            "duration_hours": 0.0,
            "failure_analysis": failure_analysis,
            "lessons_learned": [],
            "detailed_narrative": "",
        }
        
        # 보유 시간 계산
        entry_time = pd.Timestamp(journal["entry"]["timestamp"]) if journal["entry"]["timestamp"] else None
        exit_time = pd.Timestamp(journal["exit"]["timestamp"]) if journal["exit"]["timestamp"] else None
        if entry_time and exit_time:
            journal["duration_hours"] = (exit_time - entry_time).total_seconds() / 3600
        
        # 상세 서술 생성
        journal["detailed_narrative"] = self._generate_narrative(journal)
        
        # 교훈 추출
        if failure_analysis:
            journal["lessons_learned"] = self._extract_lessons(failure_analysis)
        
        # 일지 저장
        self.journals.append(journal)
        if len(self.journals) > self.max_journals:
            self.journals.pop(0)
        
        # 파일에 저장
        self._save_to_file(journal)
        
        # 로그 출력
        logger.info("📔 거래 일지 생성:")
        logger.info(journal["detailed_narrative"])
        
        return journal
    
    def _generate_narrative(self, journal: Dict[str, Any]) -> str:
        """상세 서술 생성"""
        narrative_parts = []
        
        narrative_parts.append("=" * 70)
        narrative_parts.append("📔 거래 일지")
        narrative_parts.append("=" * 70)
        
        # 거래 결과
        result_emoji = "✅" if journal["result"] == "win" else "❌"
        narrative_parts.append(f"\n{result_emoji} 거래 결과: {journal['result'].upper()}")
        narrative_parts.append(f"   손익: {journal['pnl']:+.2f} ({journal['pnl_pct']:+.2f}%)")
        narrative_parts.append(f"   보유 시간: {journal['duration_hours']:.1f}시간")
        
        # 진입 상황
        narrative_parts.append(f"\n【진입 상황】")
        entry = journal["entry"]
        narrative_parts.append(f"  시간: {entry['timestamp']}")
        narrative_parts.append(f"  가격: {entry['price']:.2f}")
        narrative_parts.append(f"  거래량: {entry['volume']:.2f} (평균 대비 {entry['volume_ratio']:.1%})")
        narrative_parts.append(f"  변동성: {entry['volatility_pct']:.2f}%")
        narrative_parts.append(f"  레짐: {entry['regime']}")
        narrative_parts.append(f"  예상 승률: {entry['predicted_win_rate']:.1%}")
        narrative_parts.append(f"  신뢰도: {entry['confidence']:.1%}")
        
        # 진입 이유
        if entry.get("decision_reason"):
            narrative_parts.append(f"\n  진입 이유:")
            for line in entry["decision_reason"].split("\n"):
                if line.strip():
                    narrative_parts.append(f"    {line}")
        
        # 청산 상황
        narrative_parts.append(f"\n【청산 상황】")
        exit_data = journal["exit"]
        narrative_parts.append(f"  시간: {exit_data['timestamp']}")
        narrative_parts.append(f"  가격: {exit_data['price']:.2f}")
        narrative_parts.append(f"  거래량: {exit_data['volume']:.2f} (평균 대비 {exit_data['volume_ratio']:.1%})")
        narrative_parts.append(f"  변동성: {exit_data['volatility_pct']:.2f}%")
        narrative_parts.append(f"  레짐: {exit_data['regime']}")
        narrative_parts.append(f"  청산 이유: {exit_data['reason']}")
        
        # 거래량 변화 분석
        volume_change = exit_data['volume_ratio'] - entry['volume_ratio']
        if abs(volume_change) > 0.5:
            if volume_change > 0:
                narrative_parts.append(f"\n  ⚠️ 거래량 급증: {volume_change:+.1%} 증가")
                if journal["result"] == "loss":
                    narrative_parts.append(f"     → 거래량이 급증했는데 손실 포지션 유지 - 반대 방향 신호를 놓침")
            else:
                narrative_parts.append(f"\n  📉 거래량 감소: {volume_change:+.1%} 감소")
        
        # 레짐 변화
        if entry['regime'] != exit_data['regime']:
            narrative_parts.append(f"\n  🔄 레짐 전환: {entry['regime']} → {exit_data['regime']}")
            if journal["result"] == "loss":
                narrative_parts.append(f"     → 레짐이 전환되었는데 포지션 유지 - 조기 청산 필요했음")
        
        # 실패 분석 (손실 거래인 경우)
        if journal.get("failure_analysis"):
            narrative_parts.append(f"\n【실패 분석】")
            failure = journal["failure_analysis"]
            
            if failure.get("failure_reasons"):
                narrative_parts.append(f"  실패 원인:")
                for reason in failure["failure_reasons"]:
                    narrative_parts.append(f"    • {reason}")
            
            # 구체적인 실수들
            if failure.get("decision_mistakes"):
                narrative_parts.append(f"\n  결정 실수:")
                for mistake in failure["decision_mistakes"]:
                    narrative_parts.append(f"    - {mistake}")
            
            if failure.get("risk_mistakes"):
                narrative_parts.append(f"\n  리스크 관리 실수:")
                for mistake in failure["risk_mistakes"]:
                    narrative_parts.append(f"    - {mistake}")
        
        # 교훈
        if journal.get("lessons_learned"):
            narrative_parts.append(f"\n【교훈】")
            for lesson in journal["lessons_learned"]:
                narrative_parts.append(f"  💡 {lesson}")
        
        narrative_parts.append("=" * 70)
        
        return "\n".join(narrative_parts)
    
    def _extract_lessons(self, failure_analysis: Dict[str, Any]) -> List[str]:
        """교훈 추출"""
        lessons = []
        
        # 거래량 관련 교훈
        volume_issues = [r for r in failure_analysis.get("failure_reasons", []) if "거래량" in r]
        if volume_issues:
            lessons.append("거래량 패턴을 더 주의 깊게 관찰해야 함")
            if any("급증" in r for r in volume_issues):
                lessons.append("거래량 급증 시 반대 방향 움직임 가능성 고려")
        
        # 물타기 관련 교훈
        if any("물타기" in r for r in failure_analysis.get("failure_reasons", [])):
            lessons.append("손실 포지션에 물타기하지 말 것")
            lessons.append("조기 손절 원칙 준수")
        
        # 타이밍 관련 교훈
        timing_issues = [r for r in failure_analysis.get("failure_reasons", []) if "타이밍" in r or "보유" in r]
        if timing_issues:
            lessons.append("진입 타이밍을 더 신중하게 선택해야 함")
            lessons.append("손실 포지션은 오래 보유하지 말 것")
        
        # 리스크 관리 교훈
        risk_issues = [r for r in failure_analysis.get("failure_reasons", []) if "리스크" in r or "스탑로스" in r]
        if risk_issues:
            lessons.append("리스크 관리 원칙을 더 엄격하게 준수해야 함")
            lessons.append("스탑로스를 적절히 설정하고 반드시 준수")
        
        return lessons if lessons else ["이 거래에서 배울 점을 찾아야 함"]
    
    def _save_to_file(self, journal: Dict[str, Any]):
        """파일에 저장"""
        date_str = datetime.now().strftime("%Y%m%d")
        filename = self.output_path / f"journal_{date_str}.jsonl"
        
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(json.dumps(journal, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.error(f"일지 저장 실패: {e}")
    
    def get_recent_journals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """최근 일지 반환"""
        return self.journals[-limit:] if self.journals else []

