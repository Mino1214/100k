"""실패 분석기 - 거래 실패 원인을 상세히 분석하고 기록"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from utils.logger import get_logger
import pandas as pd
import numpy as np

logger = get_logger(__name__)


class FailureAnalyzer:
    """실패 분석기 - 왜 틀렸는지 상세 분석"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        실패 분석기 초기화
        
        Args:
            config: 설정
        """
        self.config = config
        
        # 실패 패턴 데이터베이스
        self.failure_patterns: List[Dict[str, Any]] = []
        self.max_patterns = 500
        
        logger.info("실패 분석기 초기화 완료")
    
    def analyze_trade_failure(
        self,
        trade_result: Dict[str, Any],
        entry_data: Dict[str, Any],
        exit_data: Dict[str, Any],
        market_history: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        거래 실패 상세 분석
        
        Args:
            trade_result: 거래 결과 (pnl, win/loss 등)
            entry_data: 진입 시점 데이터
            exit_data: 청산 시점 데이터
            market_history: 시장 이력 (진입 전후 데이터)
            
        Returns:
            실패 분석 결과
        """
        if trade_result.get("pnl", 0.0) >= 0:
            # 수익 거래는 분석하지 않음
            return {}
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": trade_result.get("trade_id", "unknown"),
            "pnl": trade_result.get("pnl", 0.0),
            "entry_time": entry_data.get("timestamp"),
            "exit_time": exit_data.get("timestamp"),
            "failure_reasons": [],
            "market_conditions": {},
            "decision_mistakes": [],
            "risk_mistakes": [],
            "timing_mistakes": [],
            "detailed_journal": "",
        }
        
        # 1. 시장 상황 분석
        market_analysis = self._analyze_market_conditions(
            entry_data, exit_data, market_history
        )
        analysis["market_conditions"] = market_analysis
        
        # 2. 거래량 분석
        volume_analysis = self._analyze_volume_pattern(
            entry_data, exit_data, market_history
        )
        if volume_analysis.get("issues"):
            analysis["failure_reasons"].extend(volume_analysis["issues"])
            analysis["decision_mistakes"].extend(volume_analysis.get("mistakes", []))
        
        # 3. 물타기 분석
        averaging_analysis = self._analyze_averaging_down(
            trade_result, entry_data, market_history
        )
        if averaging_analysis.get("detected"):
            analysis["failure_reasons"].append(averaging_analysis["reason"])
            analysis["risk_mistakes"].extend(averaging_analysis.get("mistakes", []))
        
        # 4. 타이밍 분석
        timing_analysis = self._analyze_timing(
            entry_data, exit_data, market_history
        )
        if timing_analysis.get("issues"):
            analysis["failure_reasons"].extend(timing_analysis["issues"])
            analysis["timing_mistakes"].extend(timing_analysis.get("mistakes", []))
        
        # 5. 리스크 관리 분석
        risk_analysis = self._analyze_risk_management(
            trade_result, entry_data, exit_data
        )
        if risk_analysis.get("issues"):
            analysis["failure_reasons"].extend(risk_analysis["issues"])
            analysis["risk_mistakes"].extend(risk_analysis.get("mistakes", []))
        
        # 6. 레짐 전환 분석
        regime_analysis = self._analyze_regime_change(
            entry_data, exit_data, market_history
        )
        if regime_analysis.get("detected"):
            analysis["failure_reasons"].append(regime_analysis["reason"])
            analysis["decision_mistakes"].extend(regime_analysis.get("mistakes", []))
        
        # 7. 상세 일지 생성
        analysis["detailed_journal"] = self._generate_detailed_journal(analysis)
        
        # 패턴 저장
        self.failure_patterns.append(analysis)
        if len(self.failure_patterns) > self.max_patterns:
            self.failure_patterns.pop(0)
        
        return analysis
    
    def _analyze_market_conditions(
        self,
        entry_data: Dict[str, Any],
        exit_data: Dict[str, Any],
        market_history: pd.DataFrame,
    ) -> Dict[str, Any]:
        """시장 상황 분석"""
        conditions = {
            "entry_volatility": 0.0,
            "exit_volatility": 0.0,
            "volatility_change": 0.0,
            "entry_volume": 0.0,
            "exit_volume": 0.0,
            "volume_change": 0.0,
            "trend_direction": "unknown",
            "trend_reversal": False,
        }
        
        if market_history.empty:
            return conditions
        
        # 변동성 계산
        if "atr" in market_history.columns:
            entry_atr = entry_data.get("atr", 0.0)
            exit_atr = exit_data.get("atr", 0.0)
            entry_price = entry_data.get("price", 0.0)
            exit_price = exit_data.get("price", 0.0)
            
            if entry_price > 0:
                conditions["entry_volatility"] = (entry_atr / entry_price) * 100
            if exit_price > 0:
                conditions["exit_volatility"] = (exit_atr / exit_price) * 100
            conditions["volatility_change"] = conditions["exit_volatility"] - conditions["entry_volatility"]
        
        # 거래량 분석
        conditions["entry_volume"] = entry_data.get("volume", 0.0)
        conditions["exit_volume"] = exit_data.get("volume", 0.0)
        if conditions["entry_volume"] > 0:
            conditions["volume_change"] = (
                (conditions["exit_volume"] - conditions["entry_volume"]) / conditions["entry_volume"]
            ) * 100
        
        # 트렌드 분석
        if len(market_history) >= 20:
            recent_prices = market_history["close"].tail(20).values
            price_change = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
            
            if price_change > 2:
                conditions["trend_direction"] = "strong_up"
            elif price_change > 0.5:
                conditions["trend_direction"] = "up"
            elif price_change < -2:
                conditions["trend_direction"] = "strong_down"
            elif price_change < -0.5:
                conditions["trend_direction"] = "down"
            else:
                conditions["trend_direction"] = "sideways"
        
        return conditions
    
    def _analyze_volume_pattern(
        self,
        entry_data: Dict[str, Any],
        exit_data: Dict[str, Any],
        market_history: pd.DataFrame,
    ) -> Dict[str, Any]:
        """거래량 패턴 분석"""
        issues = []
        mistakes = []
        
        entry_volume = entry_data.get("volume", 0.0)
        entry_volume_ma = entry_data.get("volume_ma", entry_volume)
        exit_volume = exit_data.get("volume", 0.0)
        exit_volume_ma = exit_data.get("volume_ma", exit_volume)
        
        # 진입 시 거래량 부족
        if entry_volume_ma > 0:
            entry_volume_ratio = entry_volume / entry_volume_ma
            if entry_volume_ratio < 0.5:
                issues.append(f"진입 시 거래량 부족: 평균의 {entry_volume_ratio:.1%}")
                mistakes.append("거래량이 평균의 50% 미만인데 진입함 - 유동성 부족으로 불리한 가격 체결 가능")
            elif entry_volume_ratio < 0.7:
                issues.append(f"진입 시 거래량 낮음: 평균의 {entry_volume_ratio:.1%}")
        
        # 청산 시 거래량 급증 (반대 신호)
        if exit_volume_ma > 0 and entry_volume_ma > 0:
            exit_volume_ratio = exit_volume / exit_volume_ma
            entry_volume_ratio = entry_volume / entry_volume_ma
            
            if exit_volume_ratio > 1.5 and entry_volume_ratio < 1.0:
                issues.append(f"청산 시 거래량 급증: {exit_volume_ratio:.1%} (진입 시: {entry_volume_ratio:.1%})")
                mistakes.append("청산 시점에 거래량이 급증했는데 이미 손실 포지션 - 반대 방향으로 강한 움직임 신호를 놓침")
        
        # 거래량 급등 후 손실
        if exit_volume > 0 and entry_volume > 0:
            volume_surge = (exit_volume - entry_volume) / entry_volume
            if volume_surge > 2.0:  # 거래량 2배 이상 증가
                issues.append(f"거래량 급등: {volume_surge:.1%} 증가")
                mistakes.append("거래량이 급등했는데 손실 포지션 유지 - 시장이 반대 방향으로 강하게 움직임을 놓침")
        
        return {
            "issues": issues,
            "mistakes": mistakes,
        }
    
    def _analyze_averaging_down(
        self,
        trade_result: Dict[str, Any],
        entry_data: Dict[str, Any],
        market_history: pd.DataFrame,
    ) -> Dict[str, Any]:
        """물타기 분석"""
        # 실제로는 거래 이력에서 물타기 여부 확인 필요
        # 여기서는 간단히 포지션 크기와 손실 정도로 추정
        
        pnl = trade_result.get("pnl", 0.0)
        position_size = trade_result.get("position_size", 0.0)
        entry_price = entry_data.get("price", 0.0)
        exit_price = trade_result.get("exit_price", entry_price)
        
        # 큰 손실 + 큰 포지션 = 물타기 가능성
        if pnl < -100 and position_size > 1.0:
            # 손실률 계산
            if entry_price > 0:
                loss_pct = abs((exit_price - entry_price) / entry_price) * 100
                
                if loss_pct > 5.0:  # 5% 이상 손실
                    return {
                        "detected": True,
                        "reason": f"물타기로 인한 대규모 손실: {pnl:.2f} (손실률 {loss_pct:.1f}%)",
                        "mistakes": [
                            "손실 포지션에 물타기를 해서 손실 확대",
                            f"손실률 {loss_pct:.1f}%까지 방치 - 조기 손절 필요했음",
                            "리스크 관리 원칙 위반",
                        ],
                    }
        
        return {"detected": False}
    
    def _analyze_timing(
        self,
        entry_data: Dict[str, Any],
        exit_data: Dict[str, Any],
        market_history: pd.DataFrame,
    ) -> Dict[str, Any]:
        """타이밍 분석"""
        issues = []
        mistakes = []
        
        entry_time = pd.Timestamp(entry_data.get("timestamp"))
        exit_time = pd.Timestamp(exit_data.get("timestamp"))
        duration = (exit_time - entry_time).total_seconds() / 3600  # 시간
        
        # 너무 오래 보유
        if duration > 24:
            issues.append(f"장기 보유: {duration:.1f}시간")
            mistakes.append(f"{duration:.1f}시간 동안 손실 포지션 보유 - 조기 청산 필요했음")
        
        # 너무 빨리 청산 (익절 기회 놓침)
        if duration < 1 and exit_data.get("pnl", 0.0) < 0:
            # 진입 후 1시간 이내 손실 청산
            issues.append(f"조기 청산: {duration:.1f}시간")
            mistakes.append("너무 빨리 청산 - 노이즈에 반응했을 가능성")
        
        # 진입 타이밍 (진입 후 가격 움직임 확인)
        if not market_history.empty and len(market_history) >= 10:
            entry_idx = None
            for idx, row in market_history.iterrows():
                if pd.Timestamp(row.get("timestamp", idx)) >= entry_time:
                    entry_idx = idx
                    break
            
            if entry_idx is not None:
                # 진입 후 5바 데이터
                post_entry = market_history.loc[market_history.index >= entry_idx].head(5)
                if len(post_entry) >= 3:
                    entry_price = entry_data.get("price", 0.0)
                    post_prices = post_entry["close"].values
                    
                    # 진입 직후 가격이 더 불리하게 움직임
                    if len(post_prices) >= 2:
                        immediate_move = ((post_prices[1] - entry_price) / entry_price) * 100
                        if immediate_move < -1.0:  # 1% 이상 즉시 하락
                            issues.append(f"나쁜 진입 타이밍: 진입 직후 {immediate_move:.1f}% 하락")
                            mistakes.append("진입 직후 가격이 불리하게 움직임 - 진입 신호가 약했거나 노이즈에 반응")
        
        return {
            "issues": issues,
            "mistakes": mistakes,
        }
    
    def _analyze_risk_management(
        self,
        trade_result: Dict[str, Any],
        entry_data: Dict[str, Any],
        exit_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """리스크 관리 분석"""
        issues = []
        mistakes = []
        
        pnl = trade_result.get("pnl", 0.0)
        entry_price = entry_data.get("price", 0.0)
        stop_loss = entry_data.get("stop_loss", entry_price)
        exit_price = exit_data.get("price", entry_price)
        
        # 스탑로스 설정 문제
        if entry_price > 0 and stop_loss != entry_price:
            stop_distance = abs(entry_price - stop_loss) / entry_price * 100
            
            # 스탑로스가 너무 멀리
            if stop_distance > 5.0:
                issues.append(f"스탑로스 너무 멀리: {stop_distance:.1f}%")
                mistakes.append(f"스탑로스가 {stop_distance:.1f}%나 멀어서 손실 확대")
            
            # 실제 청산이 스탑로스보다 더 큰 손실
            actual_loss = abs(entry_price - exit_price) / entry_price * 100
            if actual_loss > stop_distance * 1.2:
                issues.append(f"스탑로스 미준수: 설정 {stop_distance:.1f}%, 실제 {actual_loss:.1f}%")
                mistakes.append("스탑로스를 설정했지만 더 큰 손실로 청산 - 슬리피지나 갭 발생")
        
        # 포지션 사이즈 문제
        position_size = trade_result.get("position_size", 0.0)
        account_equity = trade_result.get("account_equity", 100000)
        
        if account_equity > 0:
            position_value = position_size * entry_price
            position_ratio = position_value / account_equity
            
            if position_ratio > 0.3:  # 자산의 30% 이상
                issues.append(f"과도한 포지션: 자산의 {position_ratio:.1%}")
                mistakes.append(f"포지션이 자산의 {position_ratio:.1%}로 너무 큼 - 리스크 과다")
        
        return {
            "issues": issues,
            "mistakes": mistakes,
        }
    
    def _analyze_regime_change(
        self,
        entry_data: Dict[str, Any],
        exit_data: Dict[str, Any],
        market_history: pd.DataFrame,
    ) -> Dict[str, Any]:
        """레짐 전환 분석"""
        entry_regime = entry_data.get("regime", "unknown")
        exit_regime = exit_data.get("regime", "unknown")
        
        if entry_regime != exit_regime and entry_regime != "unknown" and exit_regime != "unknown":
            return {
                "detected": True,
                "reason": f"레짐 전환: {entry_regime} → {exit_regime}",
                "mistakes": [
                    f"진입 시 {entry_regime} 레짐이었지만 {exit_regime}로 전환됨",
                    "레짐 전환 신호를 놓치고 포지션 유지",
                    "레짐 전환 시 즉시 청산해야 함",
                ],
            }
        
        return {"detected": False}
    
    def _generate_detailed_journal(self, analysis: Dict[str, Any]) -> str:
        """상세 일지 생성"""
        journal_parts = []
        
        journal_parts.append("=" * 60)
        journal_parts.append("📝 거래 실패 분석 일지")
        journal_parts.append("=" * 60)
        
        # 기본 정보
        journal_parts.append(f"\n【거래 정보】")
        journal_parts.append(f"  손익: {analysis['pnl']:.2f}")
        journal_parts.append(f"  진입: {analysis['entry_time']}")
        journal_parts.append(f"  청산: {analysis['exit_time']}")
        
        # 실패 원인
        if analysis["failure_reasons"]:
            journal_parts.append(f"\n【실패 원인】")
            for i, reason in enumerate(analysis["failure_reasons"], 1):
                journal_parts.append(f"  {i}. {reason}")
        
        # 시장 상황
        market = analysis.get("market_conditions", {})
        if market:
            journal_parts.append(f"\n【시장 상황】")
            journal_parts.append(f"  진입 시 변동성: {market.get('entry_volatility', 0):.2f}%")
            journal_parts.append(f"  청산 시 변동성: {market.get('exit_volatility', 0):.2f}%")
            journal_parts.append(f"  변동성 변화: {market.get('volatility_change', 0):+.2f}%")
            journal_parts.append(f"  거래량 변화: {market.get('volume_change', 0):+.1f}%")
            journal_parts.append(f"  트렌드: {market.get('trend_direction', 'unknown')}")
        
        # 결정 실수
        if analysis["decision_mistakes"]:
            journal_parts.append(f"\n【결정 실수】")
            for i, mistake in enumerate(analysis["decision_mistakes"], 1):
                journal_parts.append(f"  {i}. {mistake}")
        
        # 리스크 실수
        if analysis["risk_mistakes"]:
            journal_parts.append(f"\n【리스크 관리 실수】")
            for i, mistake in enumerate(analysis["risk_mistakes"], 1):
                journal_parts.append(f"  {i}. {mistake}")
        
        # 타이밍 실수
        if analysis["timing_mistakes"]:
            journal_parts.append(f"\n【타이밍 실수】")
            for i, mistake in enumerate(analysis["timing_mistakes"], 1):
                journal_parts.append(f"  {i}. {mistake}")
        
        # 교훈
        journal_parts.append(f"\n【교훈】")
        if analysis["failure_reasons"]:
            journal_parts.append("  다음 거래에서는:")
            for reason in analysis["failure_reasons"][:3]:  # 상위 3개만
                journal_parts.append(f"    - {reason}을(를) 피해야 함")
        else:
            journal_parts.append("  특별한 실수는 없었지만 손실 발생 - 시장 노이즈 가능성")
        
        journal_parts.append("=" * 60)
        
        return "\n".join(journal_parts)
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """실패 통계 반환"""
        if not self.failure_patterns:
            return {}
        
        # 실패 원인별 빈도
        reason_counts = {}
        for pattern in self.failure_patterns:
            for reason in pattern.get("failure_reasons", []):
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        # 가장 흔한 실수
        top_mistakes = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_failures": len(self.failure_patterns),
            "top_failure_reasons": top_mistakes,
            "recent_failures": self.failure_patterns[-10:] if len(self.failure_patterns) >= 10 else self.failure_patterns,
        }

