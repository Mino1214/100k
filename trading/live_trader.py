"""실시간 거래 모듈 - 봉 마감 기반 자동 학습 및 거래"""

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
import pandas as pd
import time
from threading import Thread, Event
from data.realtime_feed import RealtimeFeed
from strategy.strategy_registry import StrategyRegistry
from backtest.engine import BacktestEngine
from analytics.metrics import calculate_metrics
from analytics.db_logger import DatabaseLogger
from optimization.continuous_optimizer import ContinuousOptimizer
from trading.risk_guardian import RiskGuardian
from trading.smart_entry import SmartEntry
from trading.smart_exit import SmartExit
from trading.adaptive_risk_manager import AdaptiveRiskManager
from trading.experience_learner import ExperienceLearner
from trading.trading_mind import TradingMind
from trading.decision_logger import DecisionLogger
from utils.logger import get_logger

logger = get_logger(__name__)


class LiveTrader:
    """실시간 거래 클래스 - 봉 마감 기반 자동 학습 및 거래"""
    
    def __init__(
        self,
        config: Dict[str, Any],
        db_logger: Optional[DatabaseLogger] = None,
        optimization_window_days: int = 30,
        reoptimize_frequency: str = "daily",  # daily, weekly, on_bar_close
    ):
        """
        실시간 거래자 초기화
        
        Args:
            config: 설정
            db_logger: 데이터베이스 로거
            optimization_window_days: 최적화에 사용할 과거 데이터 기간 (일)
            reoptimize_frequency: 재최적화 빈도 (daily, weekly, on_bar_close)
        """
        self.config = config
        self.db_logger = db_logger
        self.optimization_window_days = optimization_window_days
        self.reoptimize_frequency = reoptimize_frequency
        
        # 실시간 데이터 피드
        data_config = config.get("data", {})
        self.realtime_feed = RealtimeFeed(config=data_config)
        
        # 리스크 관리자
        self.risk_guardian = RiskGuardian(config)
        
        # 적응형 리스크 관리자 (시드 기반)
        self.adaptive_risk = AdaptiveRiskManager(config)
        
        # 경험 학습자
        self.experience_learner = ExperienceLearner(config)
        
        # 트레이딩 마인드
        self.trading_mind = TradingMind(config)
        
        # 결정 로거
        self.decision_logger = DecisionLogger(config)
        
        # 스마트 진입/청산
        self.smart_entry = SmartEntry(config)
        self.smart_exit = SmartExit(config)
        
        # 현재 사용 중인 파라미터
        self.current_params = self._get_current_params(config)
        
        # 최적화 이력
        self.optimization_history: List[Dict[str, Any]] = []
        self.last_optimization_time: Optional[datetime] = None
        
        # 거래 상태
        self.is_trading = False
        self.stop_event = Event()
        
        # 백테스트 엔진 (실시간 거래용)
        self.backtest_engine: Optional[BacktestEngine] = None
        
        # 현재 포지션
        self.current_position: Optional[Any] = None
        
        logger.info("실시간 거래자 초기화 완료")
        logger.info(f"재최적화 빈도: {reoptimize_frequency}")
        logger.info(f"최적화 윈도우: {optimization_window_days}일")
        logger.info("리스크 가디언 및 스마트 진입/청산 활성화")
    
    def _get_current_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """현재 파라미터 추출"""
        indicators_config = config.get("indicators", {})
        ema_config = indicators_config.get("ema", {})
        periods = ema_config.get("periods", [20, 40, 80])
        
        strategy_config = config.get("strategy", {})
        exit_config = strategy_config.get("exit", {})
        stop_loss_config = exit_config.get("stop_loss", {})
        atr_multiplier = stop_loss_config.get("atr_multiplier", 2.0)
        
        return {
            "ema_fast": periods[0],
            "ema_mid": periods[1],
            "ema_slow": periods[2],
            "atr_multiplier": atr_multiplier,
        }
    
    def start_trading(
        self,
        auto_optimize: bool = True,
        paper_trading: bool = True,
    ):
        """
        실시간 거래 시작
        
        Args:
            auto_optimize: 자동 최적화 활성화
            paper_trading: 페이퍼 트레이딩 모드 (실거래 안 함)
        """
        logger.info("=" * 60)
        logger.info("실시간 거래 시작")
        logger.info(f"자동 최적화: {auto_optimize}")
        logger.info(f"페이퍼 트레이딩: {paper_trading}")
        logger.info("=" * 60)
        
        self.is_trading = True
        self.paper_trading = paper_trading
        
        # 초기 최적화 (과거 데이터로)
        if auto_optimize:
            self._run_optimization()
        
        # 실시간 데이터 수신 시작 (웹훅 모드에서는 선택적)
        # 웹훅을 사용하는 경우 RealtimeFeed는 사용하지 않음
        use_realtime_feed = not hasattr(self, '_webhook_mode') or not getattr(self, '_webhook_mode', False)
        
        if use_realtime_feed:
            self.realtime_feed.start()
            # 봉 마감 이벤트 핸들러 등록
            self.realtime_feed.on_bar_close = self._on_bar_close
            
            # 메인 루프 시작
            try:
                self._trading_loop()
            except KeyboardInterrupt:
                logger.info("거래 중지 요청됨")
            finally:
                self.stop()
        else:
            # 웹훅 모드: RealtimeFeed 없이 웹훅으로만 데이터 수신
            logger.info("웹훅 모드 - RealtimeFeed 없이 웹훅으로만 데이터 수신")
            logger.info("웹훅이 들어오면 자동으로 거래 로직이 실행됩니다")
            
            # 초기 최적화만 실행
            if auto_optimize:
                self._run_optimization()
            
            # 웹훅 모드에서는 메인 루프를 실행하지 않고 대기
            # 웹훅이 들어오면 _on_bar_close가 호출됨
            try:
                while not self.stop_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("거래 중지 요청됨")
            finally:
                self.stop()
    
    def _trading_loop(self):
        """거래 메인 루프"""
        logger.info("거래 루프 시작...")
        
        while not self.stop_event.is_set():
            try:
                # 실시간 데이터 확인
                latest_bar = self.realtime_feed.get_latest_bar()
                
                if latest_bar is not None:
                    # 현재 파라미터로 전략 실행
                    self._process_realtime_bar(latest_bar)
                
                # 재최적화 체크
                if self._should_reoptimize():
                    logger.info("재최적화 시점 도달 - 최적화 실행 중...")
                    self._run_optimization()
                
                # 짧은 대기
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"거래 루프 에러: {e}")
                time.sleep(5)
    
    def _on_bar_close(self, bar: Dict[str, Any]):
        """
        봉 마감 이벤트 핸들러
        
        Args:
            bar: 마감된 봉 데이터
        """
        logger.info(f"봉 마감: {bar.get('timestamp')} - Close: {bar.get('close')}")
        
        # 봉 마감 시마다 재최적화 (설정된 경우)
        if self.reoptimize_frequency == "on_bar_close":
            logger.info("봉 마감 기반 재최적화 실행...")
            self._run_optimization()
        
        # 현재 파라미터로 거래 시그널 확인
        self._process_realtime_bar(bar)
    
    def _should_reoptimize(self) -> bool:
        """재최적화가 필요한지 확인"""
        if not self.last_optimization_time:
            return True
        
        now = datetime.now()
        
        if self.reoptimize_frequency == "daily":
            # 매일 자정에 재최적화
            if now.date() > self.last_optimization_time.date():
                return True
        elif self.reoptimize_frequency == "weekly":
            # 매주 월요일 자정에 재최적화
            if now.isoweekday() == 1 and now.date() > self.last_optimization_time.date():
                return True
        
        return False
    
    def _run_optimization(self):
        """과거 데이터로 최적화 실행"""
        logger.info("=" * 60)
        logger.info("자동 최적화 시작")
        logger.info("=" * 60)
        
        try:
            # 최적화 기간 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.optimization_window_days)
            
            # 데이터 로드
            from data.loader import DataLoader
            data_config = self.config.get("data", {})
            data_loader = DataLoader(data_config)
            df = data_loader.load(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
            )
            
            if df.empty:
                logger.warning("최적화할 데이터가 없습니다.")
                return
            
            logger.info(f"최적화 데이터: {len(df)}행 ({start_date.date()} ~ {end_date.date()})")
            
            # 연속 최적화 실행
            continuous_optimizer = ContinuousOptimizer(
                self.config,
                self.db_logger,
                target_win_rate=0.5,
                target_return=0.0,
                base_ema=None,  # 현재 파라미터 사용
                variation_range=15,
                step_size=5,
            )
            
            # 빠른 최적화 (최대 20개 조합만 테스트)
            best_params = None
            best_score = -999.0
            
            for i in range(min(20, len(continuous_optimizer.param_combinations))):
                opt_result = continuous_optimizer.optimize_continuously(
                    start_date.strftime("%Y-%m-%d %H:%M"),
                    end_date.strftime("%Y-%m-%d %H:%M"),
                    max_iterations=1,
                    step_size=5,
                )
                
                if opt_result["best_params"] is None:
                    break
                
                params = opt_result["best_params"]
                
                # 백테스트 실행
                optimized_config = continuous_optimizer.apply_params_to_config(
                    self.config, params
                )
                
                strategy_config = self.config.get("strategy", {})
                strategy_name = strategy_config.get("name", "EMA_BB_TurtleTrailing")
                strategy = StrategyRegistry.get_strategy(strategy_name, optimized_config)
                
                backtest_config = self.config.get("backtest", {})
                engine = BacktestEngine(strategy, backtest_config)
                result = engine.run(df)
                
                if result["trades"].empty:
                    continue
                
                metrics = calculate_metrics(
                    result["trades"],
                    result["equity_curve"],
                    engine.initial_capital,
                )
                
                # 점수 계산 (Sharpe 비율 우선)
                score = metrics.sharpe_ratio if metrics.sharpe_ratio else -999.0
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    logger.info(f"새로운 최적 파라미터 발견: {params}, Sharpe={score:.2f}")
            
            # 최적 파라미터 적용
            if best_params:
                logger.info("=" * 60)
                logger.info("최적 파라미터 업데이트:")
                logger.info(f"  Fast EMA: {self.current_params['ema_fast']} → {best_params['ema_fast']}")
                logger.info(f"  Mid EMA: {self.current_params['ema_mid']} → {best_params['ema_mid']}")
                logger.info(f"  Slow EMA: {self.current_params['ema_slow']} → {best_params['ema_slow']}")
                logger.info(f"  ATR Multiplier: {self.current_params['atr_multiplier']:.2f} → {best_params['atr_multiplier']:.2f}")
                logger.info("=" * 60)
                
                self.current_params = best_params
                self.last_optimization_time = datetime.now()
                
                # 전략 재생성
                optimized_config = continuous_optimizer.apply_params_to_config(
                    self.config, best_params
                )
                strategy = StrategyRegistry.get_strategy(strategy_name, optimized_config)
                backtest_config = self.config.get("backtest", {})
                self.backtest_engine = BacktestEngine(strategy, backtest_config)
                
                # 최적화 이력 저장
                self.optimization_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "params": best_params.copy(),
                    "score": best_score,
                })
                
        except Exception as e:
            logger.error(f"최적화 실행 실패: {e}")
    
    def _process_realtime_bar(self, bar: Dict[str, Any]):
        """
        실시간 봉 처리 및 거래 시그널 확인 (정교한 로직)
        
        Args:
            bar: 봉 데이터
        """
        if self.backtest_engine is None:
            # 초기 전략 생성
            optimized_config = self._apply_params_to_config(self.current_params)
            strategy_config = self.config.get("strategy", {})
            strategy_name = strategy_config.get("name", "EMA_BB_TurtleTrailing")
            strategy = StrategyRegistry.get_strategy(strategy_name, optimized_config)
            backtest_config = self.config.get("backtest", {})
            self.backtest_engine = BacktestEngine(strategy, backtest_config)
        
        # 현재 포지션이 있으면 청산 확인
        if self.current_position:
            self._check_exit_conditions(bar)
        else:
            # 진입 시그널 확인
            self._check_entry_conditions(bar)
    
    def _check_entry_conditions(self, bar: Dict[str, Any]):
        """진입 조건 확인 (스마트 진입 사용)"""
        # 리스크 가디언 확인
        risk_status = self.risk_guardian.get_risk_status()
        if not risk_status["can_trade"]:
            logger.info(f"⚠️ 리스크 가디언: 거래 불가 - {risk_status.get('reason', '알 수 없음')}")
            return
        
        # 봉 데이터를 DataFrame으로 변환 (히스토리 필요)
        # 현재는 단일 봉만 있으므로 실제 전략 실행은 제한적
        # 하지만 진입 조건 체크는 가능
        
        logger.info(f"🔍 진입 조건 확인 중: {bar.get('timestamp')}, Close: {bar.get('close')}")
        logger.info(f"   현재 포지션: {'있음' if self.current_position else '없음'}")
        logger.info(f"   리스크 상태: {risk_status}")
        
        # TODO: 실제 전략 시그널 생성 및 진입 로직 구현 필요
        # 현재는 봉 데이터만 받고 있어서 지표 계산이 어려움
        # 웹훅으로 받은 봉 데이터를 누적해서 DataFrame을 만들어야 함
    
    def _check_exit_conditions(self, bar: Dict[str, Any]):
        """청산 조건 확인 (스마트 청산 사용)"""
        if not self.current_position:
            return
        
        current_price = bar.get("close")
        current_time = pd.Timestamp(bar.get("timestamp"))
        
        # 스마트 청산 확인
        # 1. 트레일링 스탑 업데이트
        # 2. 부분 청산 확인
        # 3. 익절 확인
        # 4. 조기 손절 확인
        
        # 리스크 가디언 확인
        should_close, reason = self.risk_guardian.should_close_position(
            self.current_position,
            current_price,
            current_time,
            self.risk_guardian.peak_equity,
        )
        
        if should_close:
            logger.info(f"청산 신호: {reason}")
            # 실제 청산 로직 실행
    
    def _apply_params_to_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """파라미터를 설정에 적용"""
        import copy
        new_config = copy.deepcopy(self.config)
        
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
    
    def stop(self):
        """거래 중지"""
        logger.info("거래 중지 중...")
        self.is_trading = False
        self.stop_event.set()
        self.realtime_feed.stop()
        logger.info("거래 중지 완료")
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        return {
            "is_trading": self.is_trading,
            "current_params": self.current_params,
            "last_optimization": self.last_optimization_time.isoformat() if self.last_optimization_time else None,
            "optimization_count": len(self.optimization_history),
        }

