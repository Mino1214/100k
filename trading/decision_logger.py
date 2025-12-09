"""결정 로거 - 모든 거래 결정과 이유를 상세히 로깅"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from utils.logger import get_logger
import json
from pathlib import Path

logger = get_logger(__name__)


class DecisionLogger:
    """결정 로거 - 거래 결정 상세 로깅"""
    
    def __init__(self, config: Dict[str, Any], output_path: str = "./logs/decisions/"):
        """
        결정 로거 초기화
        
        Args:
            config: 설정
            output_path: 로그 출력 경로
        """
        self.config = config
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # 결정 로그
        self.decision_log: List[Dict[str, Any]] = []
        self.max_memory_logs = 1000
        
        logger.info(f"결정 로거 초기화: {self.output_path}")
    
    def log_entry_decision(
        self,
        decision: Dict[str, Any],
        market_data: Dict[str, Any],
        entry_conditions: Dict[str, Any],
    ):
        """
        진입 결정 로깅
        
        Args:
            decision: 결정 정보 (trading_mind의 생각)
            market_data: 시장 데이터
            entry_conditions: 진입 조건
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "entry_decision",
            "decision": decision.get("decision", "unknown"),
            "confidence": decision.get("confidence", 0.0),
            "mood": decision.get("mood", "neutral"),
            "market_data": market_data,
            "entry_conditions": entry_conditions,
            "reasoning": decision.get("reasoning", []),
            "concerns": decision.get("concerns", []),
            "detailed_reason": decision.get("detailed_reason", ""),
        }
        
        self.decision_log.append(log_entry)
        
        # 메모리 로그 관리
        if len(self.decision_log) > self.max_memory_logs:
            self.decision_log.pop(0)
        
        # 파일에 저장
        self._save_to_file(log_entry)
        
        # 콘솔 출력
        logger.info("📝 진입 결정 로그:")
        logger.info(f"  결정: {log_entry['decision']}")
        logger.info(f"  신뢰도: {log_entry['confidence']:.1%}")
        logger.info(f"  기분: {log_entry['mood']}")
        if log_entry["detailed_reason"]:
            logger.info(f"  상세 이유:\n{log_entry['detailed_reason']}")
    
    def log_trade_result(
        self,
        trade_result: Dict[str, Any],
        entry_decision: Dict[str, Any],
    ):
        """
        거래 결과 로깅
        
        Args:
            trade_result: 거래 결과
            entry_decision: 진입 결정
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "trade_result",
            "trade_result": trade_result,
            "entry_decision": entry_decision,
            "was_correct": trade_result.get("pnl", 0.0) > 0,
        }
        
        self.decision_log.append(log_entry)
        
        # 파일에 저장
        self._save_to_file(log_entry)
        
        # 콘솔 출력
        pnl = trade_result.get("pnl", 0.0)
        logger.info("📊 거래 결과 로그:")
        logger.info(f"  손익: {pnl:+.2f}")
        logger.info(f"  예상 승률: {entry_decision.get('predicted_win_rate', 0.0):.1%}")
        logger.info(f"  실제 결과: {'승리' if pnl > 0 else '손실'}")
    
    def _save_to_file(self, log_entry: Dict[str, Any]):
        """파일에 저장"""
        date_str = datetime.now().strftime("%Y%m%d")
        filename = self.output_path / f"decisions_{date_str}.jsonl"
        
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"결정 로그 저장 실패: {e}")
    
    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """최근 결정 반환"""
        return self.decision_log[-limit:] if self.decision_log else []

