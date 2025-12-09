"""백테스트 엔진 모듈"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from tqdm import tqdm
from strategy.base_strategy import BaseStrategy, Position, Signal, SignalType
from execution.position_manager import PositionManager
from execution.risk_manager import RiskManager
from execution.order_executor import OrderExecutor, Order
from backtest.portfolio import Portfolio
from backtest.trade_logger import TradeLogger
from utils.logger import get_logger

# 실전 거래 모듈 (선택적)
try:
    from trading.risk_guardian import RiskGuardian
    from trading.smart_entry import SmartEntry
    from trading.smart_exit import SmartExit
    from trading.adaptive_risk_manager import AdaptiveRiskManager
    from trading.experience_learner import ExperienceLearner
    from trading.trading_mind import TradingMind
    from trading.decision_logger import DecisionLogger
    from trading.failure_analyzer import FailureAnalyzer
    from trading.trade_journal import TradeJournal
    TRADING_MODULES_AVAILABLE = True
except ImportError:
    TRADING_MODULES_AVAILABLE = False
    RiskGuardian = None
    SmartEntry = None
    SmartExit = None
    AdaptiveRiskManager = None
    ExperienceLearner = None
    TradingMind = None
    DecisionLogger = None
    FailureAnalyzer = None
    TradeJournal = None

logger = get_logger(__name__)

# 웹 서버 상태 업데이트를 위한 전역 함수
_update_status_func = None


def set_status_updater(update_func):
    """상태 업데이트 함수 설정"""
    global _update_status_func
    _update_status_func = update_func


class BacktestEngine:
    """백테스트 엔진 클래스"""
    
    def __init__(
        self,
        strategy: BaseStrategy,
        config: Dict[str, Any],
    ):
        """
        백테스트 엔진 초기화
        
        Args:
            strategy: 전략 인스턴스
            config: 백테스트 설정
        """
        self.strategy = strategy
        self.config = config
        
        # 엔진 설정
        engine_config = config.get("engine", {})
        self.initial_capital = engine_config.get("initial_capital", 100000)
        self.currency = engine_config.get("currency", "USDT")
        
        # 워밍업
        warmup_config = config.get("warmup", {})
        self.warmup_bars = warmup_config.get("bars", 100)
        
        # 포트폴리오
        self.portfolio = Portfolio(self.initial_capital, self.currency)
        
        # 포지션 관리자
        risk_config = config.get("risk", {})
        portfolio_config = risk_config.get("portfolio", {})
        max_open_positions = portfolio_config.get("max_open_positions", 1)
        self.position_manager = PositionManager(max_open_positions)
        
        # 리스크 관리자
        self.risk_manager = RiskManager(risk_config)
        
        # 주문 실행자
        execution_config = config.get("execution", {})
        self.order_executor = OrderExecutor(execution_config)
        
        # 거래 기록자
        analytics_config = config.get("analytics", {})
        report_config = analytics_config.get("report", {})
        output_path = report_config.get("output_path", "./reports/")
        self.trade_logger = TradeLogger(output_path)
        
        # 일일 통계
        self.daily_trades = 0
        self.current_date: Optional[pd.Timestamp] = None
        
        # 최적화: 미리 계산된 데이터 저장
        self._precomputed_data = None
        
        # 실전 거래 모듈 (선택적)
        self.use_smart_trading = config.get("use_smart_trading", False)
        if self.use_smart_trading and TRADING_MODULES_AVAILABLE:
            self.risk_guardian = RiskGuardian(config)
            self.adaptive_risk = AdaptiveRiskManager(config)
            self.experience_learner = ExperienceLearner(config)
            self.trading_mind = TradingMind(config)
            self.decision_logger = DecisionLogger(config)
            self.failure_analyzer = FailureAnalyzer(config)
            self.trade_journal = TradeJournal(config)
            self.smart_entry = SmartEntry(config)
            self.smart_exit = SmartExit(config)
            logger.info("스마트 거래 모듈 활성화 (학습 시스템 + 실패 분석 포함)")
        else:
            self.risk_guardian = None
            self.adaptive_risk = None
            self.experience_learner = None
            self.trading_mind = None
            self.decision_logger = None
            self.failure_analyzer = None
            self.trade_journal = None
            self.smart_entry = None
            self.smart_exit = None
        
        # 거래 이력 저장 (실패 분석용)
        self.trade_history_for_analysis: List[Dict[str, Any]] = []
        
        logger.info(f"백테스트 엔진 초기화: 초기 자본 {self.initial_capital} {self.currency}")
    
    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        백테스트 실행
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            백테스트 결과
        """
        logger.info(f"백테스트 시작: {len(df)}행")
        
        # 지표 계산
        logger.info("지표 계산 중...")
        df_with_indicators = self.strategy.calculate_indicators(df)
        
        # 레짐 탐지 (벡터화 연산)
        logger.info("레짐 탐지 중...")
        regime_series = self.strategy.detect_regime(df_with_indicators)
        df_with_indicators["regime"] = regime_series
        
        # 전략에 레짐 캐시 설정 (중복 계산 방지)
        if hasattr(self.strategy, '_regime_cache'):
            self.strategy._regime_cache = regime_series
        
        # 워밍업 바 건너뛰기
        start_idx = self.warmup_bars
        if start_idx >= len(df_with_indicators):
            raise ValueError("워밍업 바가 데이터 길이보다 큽니다.")
        
        # 웹 서버 상태 업데이트
        total_bars = len(df_with_indicators) - start_idx
        if _update_status_func:
            _update_status_func(
                running=True,
                current_bar=0,
                total_bars=total_bars,
                session_id=f"{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}_{self.strategy.name}",
                message="백테스트 시작",
            )
        
        # 백테스트 루프 (최적화: 모든 데이터를 배열로 미리 추출)
        logger.info("백테스트 실행 중...")
        
        # 모든 필요한 데이터를 배열로 미리 추출 (iloc 접근 완전 제거)
        df_slice = df_with_indicators.iloc[start_idx:].copy()
        prices = df_slice["close"].values
        timestamps = df_slice.index.values
        volumes = df_slice["volume"].values if "volume" in df_slice.columns else np.zeros(len(df_slice))
        regimes = df_slice["regime"].values if "regime" in df_slice.columns else np.full(len(df_slice), None)
        
        # 지표 값들도 미리 추출 (시그널 생성 시 사용)
        if "EMA_20" in df_slice.columns:
            ema20_values = df_slice["EMA_20"].values
        else:
            ema20_values = None
        if "EMA_40" in df_slice.columns:
            ema40_values = df_slice["EMA_40"].values
        else:
            ema40_values = None
        if "bb_upper" in df_slice.columns:
            bb_upper_values = df_slice["bb_upper"].values
            bb_lower_values = df_slice["bb_lower"].values
        else:
            bb_upper_values = None
            bb_lower_values = None
        if "ATR" in df_slice.columns:
            atr_values = df_slice["ATR"].values
        else:
            atr_values = None
        
        # 전략에 배열 데이터 전달 (iloc 접근 완전 제거)
        self._precomputed_data = {
            "prices": prices,
            "volumes": volumes,
            "regimes": regimes,
            "timestamps": timestamps,
            "ema20": ema20_values,
            "ema40": ema40_values,
            "bb_upper": bb_upper_values,
            "bb_lower": bb_lower_values,
            "atr": atr_values,
        }
        
        # 배치 크기 (상태 업데이트 빈도 조정)
        batch_size = 5000  # 5000바마다 상태 업데이트 (더 큰 배치)
        
        for batch_start in tqdm(range(0, total_bars, batch_size), desc="백테스트 진행"):
            batch_end = min(batch_start + batch_size, total_bars)
            
            # 배치 처리
            for local_idx in range(batch_start, batch_end):
                global_idx = start_idx + local_idx
                # 배열에서 직접 접근 (iloc 완전 제거)
                current_price = prices[local_idx]
                current_timestamp = pd.Timestamp(timestamps[local_idx])
                current_volume = volumes[local_idx]
                current_regime = regimes[local_idx]
                
                self._process_bar_internal(
                    df_with_indicators,
                    global_idx,
                    local_idx,  # 배열 인덱스 전달
                    current_price,
                    current_timestamp,
                    current_volume,
                    current_regime,
                )
            
            # 웹 서버 상태 업데이트 (배치마다)
            if _update_status_func:
                _update_status_func(
                    running=True,
                    current_bar=batch_end,
                    total_bars=total_bars,
                    message=f"백테스트 진행 중... ({batch_end}/{total_bars})",
                )
        
        # 최종 자산 업데이트
        final_price = df_with_indicators.iloc[-1]["close"]
        final_timestamp = df_with_indicators.index[-1]
        self.portfolio.update_equity(final_price, final_timestamp)
        
        # 결과 정리
        result = self._compile_results(df_with_indicators)
        
        # 웹 서버 상태 업데이트 (완료)
        if _update_status_func:
            _update_status_func(
                running=False,
                current_bar=total_bars,
                total_bars=total_bars,
                message="백테스트 완료",
            )
        
        logger.info("백테스트 완료")
        return result
    
    def _process_bar(self, df: pd.DataFrame, idx: int):
        """
        바별 처리 (호환성 유지)
        
        Args:
            df: 지표가 포함된 데이터프레임
            idx: 현재 인덱스
        """
        current_bar = df.iloc[idx]
        current_price = current_bar["close"]
        current_timestamp = df.index[idx]
        current_volume = current_bar.get("volume", 0)
        current_regime = current_bar.get("regime") if "regime" in df.columns else None
        
        self._process_bar_internal(
            df, idx, idx, current_price, current_timestamp, current_volume, current_regime
        )
    
    def _process_bar_internal(
        self,
        df: pd.DataFrame,
        idx: int,
        array_idx: int,  # 배열 인덱스
        current_price: float,
        current_timestamp: pd.Timestamp,
        current_volume: float,
        current_regime: Any,
    ):
        """
        바별 처리 내부 로직 (최적화)
        
        Args:
            df: 지표가 포함된 데이터프레임
            idx: 현재 인덱스
            current_price: 현재 가격
            current_timestamp: 현재 타임스탬프
            current_volume: 현재 거래량
            current_regime: 현재 레짐
        """
        # 날짜 변경 확인 (최적화: date() 호출 최소화)
        if self.current_date is None:
            self.current_date = current_timestamp
        elif current_timestamp.date() != self.current_date.date():
            self.daily_trades = 0
            self.current_date = current_timestamp
        
        # 자산 업데이트 (최적화: 불필요한 equity_curve 기록 빈도 줄이기)
        # 매 10바마다만 기록 (또는 포지션이 있을 때만)
        record_equity = (
            self.position_manager.has_position() or 
            (idx % 10 == 0) or 
            (idx == len(df) - 1)
        )
        self.portfolio.update_equity(
            current_price, 
            current_timestamp if record_equity else None
        )
        
        # 포트폴리오 리스크 확인
        if not self.risk_manager.check_portfolio_risk(
            self.portfolio.equity,
            self.portfolio.initial_capital,
            self.portfolio.daily_pnl,
            self.daily_trades,
        ):
            # 리스크 한도 도달 시 거래 중단
            if self.position_manager.has_position():
                # 기존 포지션 청산
                position = self.position_manager.get_position()
                exit_signal = self.strategy.generate_exit_signal(df, idx, position)
                if exit_signal.type != SignalType.NO_ACTION:
                    self._close_position(df, idx, exit_signal, current_volume)
            return
        
        # 현재 포지션 확인
        current_position = self.position_manager.get_position()
        
        # 포지션이 있는 경우
        if current_position:
            # 스마트 청산 확인 (활성화된 경우)
            if self.smart_exit:
                # 트레일링 스탑 업데이트
                atr_value = self._precomputed_data.get("atr")[array_idx] if self._precomputed_data and self._precomputed_data.get("atr") is not None else current_price * 0.02
                new_stop_loss = self.smart_exit.calculate_trailing_stop(
                    current_position,
                    current_price,
                    atr_value,
                )
                self.position_manager.update_position_stop_loss(current_position, new_stop_loss)
                
                # 부분 청산 확인
                should_partial_exit, partial_exit_pct = self.smart_exit.check_partial_exit(
                    current_position,
                    current_price,
                )
                if should_partial_exit:
                    logger.info(f"부분 청산: {partial_exit_pct:.1%}")
                    # 부분 청산 로직 (간단히 전체 청산으로 처리)
                    # 실제로는 포지션 수량을 부분만 줄여야 함
                
                # 익절 확인
                should_take_profit, profit_reason = self.smart_exit.should_take_profit(
                    current_position,
                    current_price,
                    atr_value,
                )
                if should_take_profit:
                    exit_signal = Signal(
                        type=SignalType.LONG_EXIT if current_position.direction == "long" else SignalType.SHORT_EXIT,
                        price=current_price,
                        timestamp=current_timestamp,
                        regime=current_regime,
                    )
                    self._close_position_optimized(
                        array_idx, exit_signal, current_price, current_timestamp, current_volume, current_position
                    )
                    return
                
                # 조기 손절 확인
                should_cut_loss, cut_reason = self.smart_exit.should_cut_loss_early(
                    current_position,
                    current_price,
                    current_position.entry_time,
                    current_timestamp,
                )
                if should_cut_loss:
                    exit_signal = Signal(
                        type=SignalType.LONG_EXIT if current_position.direction == "long" else SignalType.SHORT_EXIT,
                        price=current_price,
                        timestamp=current_timestamp,
                        regime=current_regime,
                    )
                    self._close_position_optimized(
                        array_idx, exit_signal, current_price, current_timestamp, current_volume, current_position
                    )
                    return
            else:
                # 기본 스탑로스 업데이트
                new_stop_loss = self.strategy.update_stop_loss(df, idx, current_position)
                self.position_manager.update_position_stop_loss(current_position, new_stop_loss)
            
            # 리스크 가디언 청산 확인
            if self.risk_guardian:
                should_close, reason = self.risk_guardian.should_close_position(
                    current_position,
                    current_price,
                    current_timestamp,
                    self.portfolio.equity,
                )
                if should_close:
                    exit_signal = Signal(
                        type=SignalType.LONG_EXIT if current_position.direction == "long" else SignalType.SHORT_EXIT,
                        price=current_price,
                        timestamp=current_timestamp,
                        regime=current_regime,
                    )
                    self._close_position_optimized(
                        array_idx, exit_signal, current_price, current_timestamp, current_volume, current_position
                    )
                    return
            
            # 스탑로스 체크 (먼저 확인 - 더 빠름)
            should_exit = False
            exit_signal = None
            
            if current_position.direction == "long":
                if current_price <= current_position.stop_loss:
                    should_exit = True
                    exit_signal = Signal(
                        type=SignalType.LONG_EXIT,
                        price=current_price,
                        timestamp=current_timestamp,
                        regime=current_regime,
                    )
            else:  # short
                if current_price >= current_position.stop_loss:
                    should_exit = True
                    exit_signal = Signal(
                        type=SignalType.SHORT_EXIT,
                        price=current_price,
                        timestamp=current_timestamp,
                        regime=current_regime,
                    )
            
            if should_exit:
                self._close_position_optimized(
                    array_idx, exit_signal, current_price, current_timestamp, current_volume, current_position
                )
            else:
                # 청산 시그널 확인 (스탑로스가 아닌 경우만)
                exit_signal = self._generate_exit_signal_optimized(
                    array_idx, current_price, current_position, current_regime
                )
                if exit_signal and exit_signal.type != SignalType.NO_ACTION:
                    self._close_position_optimized(
                        array_idx, exit_signal, current_price, current_timestamp, current_volume, current_position
                    )
        
        # 포지션이 없는 경우
        else:
            # 진입 시그널 확인 (최적화: 배열 데이터 사용)
            entry_signal = self._generate_entry_signal_optimized(
                array_idx, current_price, current_regime, current_volume
            )
            if entry_signal and entry_signal.type in [SignalType.LONG_ENTRY, SignalType.SHORT_ENTRY]:
                self._open_position_optimized(
                    array_idx, entry_signal, current_price, current_timestamp, current_volume
                )
    
    def _generate_entry_signal_optimized(
        self, array_idx: int, current_price: float, current_regime: Any, current_volume: float
    ) -> Optional[Signal]:
        """최적화된 진입 시그널 생성 (iloc 없이)"""
        if self._precomputed_data is None:
            return None
        
        # 간단한 조건만 체크 (복잡한 로직은 기존 방식 사용)
        # 실제로는 전략의 로직을 배열 기반으로 재구현해야 함
        # 여기서는 빠른 체크만 수행
        try:
            # 레짐 확인
            if current_regime is None:
                return None
            
            # 볼린저 밴드 조건 (배열에서 직접)
            bb_upper = self._precomputed_data.get("bb_upper")
            bb_lower = self._precomputed_data.get("bb_lower")
            atr = self._precomputed_data.get("atr")
            volumes = self._precomputed_data.get("volumes")
            volume_ma = None  # Volume MA는 별도 계산 필요
            
            if bb_upper is not None and bb_lower is not None:
                signal = None
                
                # Long: 가격이 하단 밴드 터치
                if current_price <= bb_lower[array_idx] and current_regime.value == "bull":
                    stop_loss = current_price - (atr[array_idx] * 2.0) if atr is not None else current_price * 0.98
                    timestamps = self._precomputed_data.get("timestamps")
                    timestamp = pd.Timestamp(timestamps[array_idx]) if timestamps is not None else pd.Timestamp.now()
                    signal = Signal(
                        type=SignalType.LONG_ENTRY,
                        price=current_price,
                        timestamp=timestamp,
                        regime=current_regime,
                        stop_loss=stop_loss,
                    )
                # Short: 가격이 상단 밴드 터치
                elif current_price >= bb_upper[array_idx] and current_regime.value == "bear":
                    stop_loss = current_price + (atr[array_idx] * 2.0) if atr is not None else current_price * 1.02
                    timestamps = self._precomputed_data.get("timestamps")
                    timestamp = pd.Timestamp(timestamps[array_idx]) if timestamps is not None else pd.Timestamp.now()
                    signal = Signal(
                        type=SignalType.SHORT_ENTRY,
                        price=current_price,
                        timestamp=timestamp,
                        regime=current_regime,
                        stop_loss=stop_loss,
                    )
                
                # 스마트 진입 필터 적용 (활성화된 경우)
                if signal and self.smart_entry:
                    # 적응형 리스크 관리자 업데이트
                    if self.adaptive_risk:
                        self.adaptive_risk.update_equity(self.portfolio.equity)
                    
                    # 경험 학습자로 예상 승률 예측
                    entry_conditions = {
                        "regime": current_regime.value if current_regime else "unknown",
                        "confidence": 0.7,  # 실제로는 계산 필요
                        "bb_position": "lower_touch" if signal.type == SignalType.LONG_ENTRY else "upper_touch",
                    }
                    
                    predicted_win_rate = 0.5
                    if self.experience_learner:
                        predicted_win_rate = self.experience_learner.predict_win_rate(entry_conditions)
                        
                        # 학습된 기준으로 진입 여부 확인
                        should_enter, learn_reason, learn_info = self.experience_learner.should_enter(
                            entry_conditions,
                            predicted_win_rate,
                        )
                        if not should_enter:
                            logger.debug(f"경험 학습자: 진입 차단 - {learn_reason}")
                            return None
                    
                    # 트레이딩 마인드로 생각하고 결정
                    if self.trading_mind:
                        market_data = {
                            "price": current_price,
                            "volume": current_volume,
                            "regime": current_regime.value if current_regime else "unknown",
                            "atr": atr[array_idx] if atr is not None else 0.0,
                        }
                        
                        risk_status = self.adaptive_risk.get_risk_status() if self.adaptive_risk else {}
                        thought = self.trading_mind.think_about_entry(
                            market_data,
                            entry_conditions,
                            predicted_win_rate,
                            {
                                "stage": risk_status.get("current_stage", "unknown"),
                                "daily_risk_ratio": risk_status.get("daily_risk_ratio", 0.0),
                                "consecutive_losses": risk_status.get("consecutive_losses", 0),
                            },
                        )
                        
                        # 결정 로깅
                        if self.decision_logger:
                            self.decision_logger.log_entry_decision(thought, market_data, entry_conditions)
                        
                        # 진입 결정 확인
                        if thought["decision"] != "enter":
                            logger.debug(f"트레이딩 마인드: {thought['decision']} 결정")
                            return None
                    
                    # 리스크 가디언 확인
                    if self.risk_guardian:
                        can_trade, reason = self.risk_guardian.can_open_position(
                            current_equity=self.portfolio.equity,
                            current_price=current_price,
                            atr_value=atr[array_idx] if atr is not None else 0.0,
                            volume=current_volume,
                            volume_ma=volume_ma or current_volume,
                        )
                        if not can_trade:
                            logger.debug(f"리스크 가디언: 진입 차단 - {reason}")
                            return None
                
                return signal
        except (IndexError, KeyError, AttributeError) as e:
            logger.debug(f"진입 시그널 생성 에러: {e}")
        
        return None
    
    def _generate_exit_signal_optimized(
        self, array_idx: int, current_price: float, position: Position, current_regime: Any
    ) -> Optional[Signal]:
        """최적화된 청산 시그널 생성"""
        # 스탑로스는 이미 체크됨
        # 레짐 전환 체크만
        if current_regime and position.regime_at_entry and current_regime != position.regime_at_entry:
            timestamps = self._precomputed_data.get("timestamps") if self._precomputed_data else None
            timestamp = pd.Timestamp(timestamps[array_idx]) if timestamps is not None else pd.Timestamp.now()
            return Signal(
                type=SignalType.LONG_EXIT if position.direction == "long" else SignalType.SHORT_EXIT,
                price=current_price,
                timestamp=timestamp,
                regime=current_regime,
            )
        return None
    
    def _open_position_optimized(
        self, array_idx: int, signal: Signal, current_price: float, 
        current_timestamp: pd.Timestamp, current_volume: float
    ):
        """최적화된 포지션 오픈"""
        # 포지션 사이즈 계산
        position_size = self.risk_manager.calculate_position_size(
            self.portfolio.equity,
            current_price,
            signal.stop_loss or current_price,
            "long" if signal.type == SignalType.LONG_ENTRY else "short",
        )
        
        if position_size <= 0:
            return
        
        # 주문 생성
        order = Order(
            symbol="ETHUSDT",
            side="buy" if signal.type == SignalType.LONG_ENTRY else "sell",
            quantity=position_size,
            order_type="market",
            timestamp=current_timestamp,
        )
        
        # 주문 실행
        fill = self.order_executor.execute_order(order, current_price, current_volume)
        
        # 포지션 생성 (수량 계산 수정)
        position = Position(
            direction="long" if signal.type == SignalType.LONG_ENTRY else "short",
            entry_price=fill.fill_price,
            quantity=position_size,  # 수량은 이미 계산됨
            entry_time=current_timestamp,
            stop_loss=signal.stop_loss or current_price,
            regime_at_entry=signal.regime,
        )
        
        # 포지션 추가
        if not self.position_manager.add_position(position):
            return  # 포지션 추가 실패 시 종료
        self.portfolio.open_position(position, fill.fill_price, fill.commission, fill.slippage)
    
    def _close_position_optimized(
        self, array_idx: int, signal: Signal, current_price: float,
        current_timestamp: pd.Timestamp, current_volume: float, position: Position
    ):
        """최적화된 포지션 클로즈 (상세 분석 포함)"""
        if position is None:
            return
        
        # 주문 생성
        order = Order(
            symbol="ETHUSDT",
            side="sell" if position.direction == "long" else "buy",
            quantity=position.quantity,
            order_type="market",
            timestamp=current_timestamp,
        )
        
        # 주문 실행
        fill = self.order_executor.execute_order(order, current_price, current_volume)
        
        # 포지션 클로즈
        trade = self.portfolio.close_position(
            fill.fill_price, fill.commission, fill.slippage, current_timestamp
        )
        
        # 상세 분석을 위한 데이터 수집
        if self.use_smart_trading and self.failure_analyzer:
            # 진입 시점 데이터 (포지션 metadata에서 가져오기)
            entry_volume = current_volume
            entry_volume_ma = current_volume
            if hasattr(position, 'metadata') and position.metadata:
                entry_volume = position.metadata.get("entry_volume", current_volume)
                entry_volume_ma = position.metadata.get("entry_volume_ma", current_volume)
            
            entry_data = {
                "timestamp": position.entry_time.isoformat() if hasattr(position.entry_time, 'isoformat') else str(position.entry_time),
                "price": position.entry_price,
                "volume": entry_volume,
                "volume_ma": entry_volume_ma,
                "atr": abs(position.entry_price - position.stop_loss) / 2.0 if position.stop_loss else 0.0,
                "regime": position.regime_at_entry.value if position.regime_at_entry else "unknown",
                "stop_loss": position.stop_loss,
            }
            
            # 청산 시점 데이터
            exit_data = {
                "timestamp": current_timestamp.isoformat() if hasattr(current_timestamp, 'isoformat') else str(current_timestamp),
                "price": current_price,
                "volume": current_volume,
                "volume_ma": current_volume,  # 실제로는 계산 필요
                "atr": self._precomputed_data.get("atr")[array_idx] if self._precomputed_data and self._precomputed_data.get("atr") is not None else 0.0,
                "regime": "unknown",  # 실제로는 계산 필요
            }
            
            # 시장 이력 (간단한 버전)
            market_history = pd.DataFrame()  # 실제로는 전체 데이터 전달 필요
            
            # 실패 분석 (손실 거래인 경우)
            if trade.pnl < 0:
                failure_analysis = self.failure_analyzer.analyze_trade_failure(
                    {
                        "trade_id": f"trade_{current_timestamp.timestamp()}",
                        "pnl": trade.pnl,
                        "exit_price": fill.fill_price,
                        "position_size": position.quantity,
                    },
                    entry_data,
                    exit_data,
                    market_history,
                )
                
                # 일지 생성
                if self.trade_journal:
                    entry_decision = {}
                    if self.trading_mind and self.trading_mind.thought_log:
                        for thought in reversed(self.trading_mind.thought_log[-10:]):
                            if thought.get("type") == "entry_decision" and thought.get("decision") == "enter":
                                entry_decision = thought
                                break
                    
                    self.trade_journal.create_journal_entry(
                        {
                            "trade_id": f"trade_{current_timestamp.timestamp()}",
                            "pnl": trade.pnl,
                            "pnl_pct": (trade.pnl / self.portfolio.initial_capital) * 100 if self.portfolio.initial_capital > 0 else 0.0,
                            "exit_price": fill.fill_price,
                            "exit_reason": signal.type.value if signal else "unknown",
                        },
                        entry_decision,
                        entry_data,
                        exit_data,
                        failure_analysis,
                    )
        
        # 포지션 제거
        self.position_manager.remove_position(position)
        self.trade_logger.log_trade(trade)
        self.daily_trades += 1
    
    def _open_position(self, df: pd.DataFrame, idx: int, signal: Signal, volume: float):
        """
        포지션 오픈 (최적화)
        
        Args:
            df: 데이터프레임
            idx: 인덱스
            signal: 진입 시그널
            volume: 거래량
        """
        current_price = signal.price
        
        # 포지션 사이즈 계산
        position_size = self.risk_manager.calculate_position_size(
            self.portfolio.equity,
            current_price,
            signal.stop_loss or current_price,
            "long" if signal.type == SignalType.LONG_ENTRY else "short",
        )
        
        if position_size <= 0:
            return
        
        # 주문 생성
        order = Order(
            symbol="BTCUSDT",
            side="buy" if signal.type == SignalType.LONG_ENTRY else "sell",
            quantity=position_size,
            order_type="market",
            timestamp=signal.timestamp,
        )
        
        # 주문 실행
        fill = self.order_executor.execute_order(order, current_price, volume)
        
        # 포지션 생성
        position = Position(
            entry_price=fill.fill_price,
            entry_time=signal.timestamp,
            direction="long" if signal.type == SignalType.LONG_ENTRY else "short",
            quantity=fill.fill_quantity,
            stop_loss=signal.stop_loss or fill.fill_price,
            regime_at_entry=signal.regime,
        )
        
        # 포지션 추가
        if self.position_manager.add_position(position):
            self.portfolio.open_position(position, fill.fill_price, fill.commission, fill.slippage)
            self.daily_trades += 1
    
    def _close_position(self, df: pd.DataFrame, idx: int, signal: Signal, volume: float):
        """
        포지션 클로즈
        
        Args:
            df: 데이터프레임
            idx: 인덱스
            signal: 청산 시그널
            volume: 거래량
        """
        current_position = self.position_manager.get_position()
        if current_position is None:
            return
        
        # 주문 생성
        order = Order(
            symbol="BTCUSDT",
            side="sell" if current_position.direction == "long" else "buy",
            quantity=current_position.quantity,
            order_type="market",
            timestamp=signal.timestamp,
        )
        
        # 주문 실행
        fill = self.order_executor.execute_order(order, signal.price, volume)
        
        # 포지션 클로즈
        trade = self.portfolio.close_position(
            fill.fill_price,
            fill.commission,
            fill.slippage,
            signal.timestamp,
        )
        
        # 거래 기록
        self.trade_logger.log_trade(trade)
        
        # 리스크 관리자에 거래 기록
        self.risk_manager.record_trade({
            "entry_price": current_position.entry_price,
            "exit_price": fill.fill_price,
            "direction": current_position.direction,
            "pnl": trade.pnl,
        })
        
        # 포지션 제거
        self.position_manager.remove_position(current_position)
        self.daily_trades += 1
    
    def _compile_results(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        결과 정리
        
        Args:
            df: 데이터프레임
            
        Returns:
            백테스트 결과
        """
        return {
            "portfolio": self.portfolio,
            "trades": self.portfolio.get_trades_df(),
            "equity_curve": self.portfolio.get_equity_curve_df(),
            "total_return": self.portfolio.get_total_return(),
            "final_equity": self.portfolio.equity,
            "total_trades": len(self.portfolio.trades),
        }

