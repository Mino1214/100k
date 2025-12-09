"""메인 실행 파일"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.loader import DataLoader
from strategy.strategy_registry import StrategyRegistry
from backtest.engine import BacktestEngine
from backtest.walk_forward import WalkForwardAnalyzer
from analytics.metrics import calculate_metrics
from analytics.report_generator import ReportGenerator
from analytics.db_logger import DatabaseLogger
from analytics.reflection_prompt import ReflectionGenerator
from optimization.grid_search import GridSearchOptimizer
from optimization.bayesian_opt import BayesianOptimizer
from optimization.reflection_optimizer import ReflectionOptimizer
from optimization.continuous_optimizer import ContinuousOptimizer
from trading.live_trader import LiveTrader
from visualization.interactive_dash import create_dashboard
from utils.helpers import load_yaml
from utils.logger import setup_logger, get_logger
from datetime import datetime
from backtest.engine import set_status_updater
from web.status import update_backtest_status
from web.server import run_server as run_web_server
import threading
import time

logger = get_logger(__name__)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="BTCUSDT 백테스트 프레임워크")
    subparsers = parser.add_subparsers(dest="command", help="명령어")
    
    # 백테스트 명령어
    backtest_parser = subparsers.add_parser("backtest", help="백테스트 실행")
    backtest_parser.add_argument("--config", type=str, default="config/settings.yaml", help="설정 파일 경로")
    backtest_parser.add_argument("--start", type=str, help="시작 날짜 (YYYY-MM-DD)")
    backtest_parser.add_argument("--end", type=str, help="종료 날짜 (YYYY-MM-DD)")
    
    # 최적화 명령어
    optimize_parser = subparsers.add_parser("optimize", help="파라미터 최적화")
    optimize_parser.add_argument("--config", type=str, default="config/settings.yaml", help="설정 파일 경로")
    optimize_parser.add_argument("--method", type=str, default="grid_search", choices=["grid_search", "bayesian", "reflection", "continuous"], help="최적화 방법")
    optimize_parser.add_argument("--iterations", type=int, default=5, help="반복 횟수 (Reflection/Continuous)")
    optimize_parser.add_argument("--trials", type=int, default=100, help="시도 횟수 (Bayesian)")
    optimize_parser.add_argument("--start", type=str, help="시작 날짜 (YYYY-MM-DD HH:MM) - Continuous 모드 필수")
    optimize_parser.add_argument("--end", type=str, help="종료 날짜 (YYYY-MM-DD HH:MM) - Continuous 모드 필수")
    optimize_parser.add_argument("--target-win-rate", type=float, default=0.5, help="목표 승률 (Continuous, 기본 0.5)")
    optimize_parser.add_argument("--target-return", type=float, default=0.0, help="목표 수익률 (Continuous, 기본 0.0)")
    optimize_parser.add_argument("--step-size", type=int, default=5, help="파라미터 조정 단위 (Continuous, 기본 5)")
    optimize_parser.add_argument("--base-ema", type=str, help="기준 EMA 값 (예: '20,40,80' 또는 '50,100,200')")
    optimize_parser.add_argument("--variation-range", type=int, default=20, help="기준값에서 ±변동 범위 (Continuous, 기본 20)")
    
    # Walk-Forward 명령어
    wf_parser = subparsers.add_parser("walk-forward", help="Walk-Forward 분석")
    wf_parser.add_argument("--config", type=str, default="config/settings.yaml", help="설정 파일 경로")
    wf_parser.add_argument("--in-sample", type=int, default=180, help="In-sample 기간 (일)")
    wf_parser.add_argument("--out-sample", type=int, default=30, help="Out-of-sample 기간 (일)")
    
    # 리포트 명령어
    report_parser = subparsers.add_parser("report", help="리포트 생성")
    report_parser.add_argument("--config", type=str, default="config/settings.yaml", help="설정 파일 경로")
    report_parser.add_argument("--format", type=str, nargs="+", default=["console", "html"], help="리포트 형식")
    report_parser.add_argument("--output", type=str, default="./reports/", help="출력 디렉토리")
    
    # 대시보드 명령어
    dashboard_parser = subparsers.add_parser("dashboard", help="대시보드 실행")
    dashboard_parser.add_argument("--config", type=str, default="config/settings.yaml", help="설정 파일 경로")
    dashboard_parser.add_argument("--port", type=int, default=5000, help="포트 번호")
    dashboard_parser.add_argument("--host", type=str, default="0.0.0.0", help="호스트 주소")
    dashboard_parser.add_argument("--webhook", action="store_true", help="TradingView 웹훅 활성화")
    
    # 실시간 거래 명령어
    live_parser = subparsers.add_parser("live", help="실시간 거래 시작")
    live_parser.add_argument("--config", type=str, default="config/settings.yaml", help="설정 파일 경로")
    live_parser.add_argument("--auto-optimize", action="store_true", help="자동 최적화 활성화")
    live_parser.add_argument("--paper-trading", action="store_true", default=True, help="페이퍼 트레이딩 모드")
    live_parser.add_argument("--optimization-window", type=int, default=30, help="최적화 윈도우 (일)")
    live_parser.add_argument("--reoptimize-frequency", type=str, default="daily", choices=["daily", "weekly", "on_bar_close"], help="재최적화 빈도")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 로거 설정
    setup_logger(log_level="INFO", log_file="./logs/backtest.log")
    
    # 설정 로드
    config = load_yaml(args.config)
    
    # 명령어 실행
    if args.command == "backtest":
        run_backtest(config, args.start, args.end)
    elif args.command == "optimize":
        # base_ema 파싱
        base_ema = None
        if args.base_ema:
            try:
                base_ema = [int(x.strip()) for x in args.base_ema.split(",")]
                if len(base_ema) != 3:
                    logger.error("base-ema는 3개의 값을 쉼표로 구분하여 입력하세요 (예: 20,40,80)")
                    base_ema = None
            except ValueError:
                logger.error("base-ema 형식이 잘못되었습니다. 예: 20,40,80")
                base_ema = None
        
        run_optimize(
            config, 
            args.method, 
            args.trials, 
            args.iterations,
            args.start,
            args.end,
            args.target_win_rate,
            args.target_return,
            args.step_size,
            base_ema,
            args.variation_range,
        )
    elif args.command == "walk-forward":
        run_walk_forward(config, args.in_sample, args.out_sample)
    elif args.command == "report":
        run_report(config, args.format, args.output)
    elif args.command == "dashboard":
        run_dashboard(config, args.port, args.host, enable_webhook=args.webhook)
    elif args.command == "live":
        run_live_trading(
            config,
            args.auto_optimize,
            args.paper_trading,
            args.optimization_window,
            args.reoptimize_frequency,
        )


def run_backtest(config: dict, start_date: str = None, end_date: str = None):
    """백테스트 실행"""
    logger.info("백테스트 시작")
    
    # 데이터 로드
    data_config = config.get("data", {})
    data_loader = DataLoader(data_config)
    
    # 샘플 데이터 생성 (CSV 파일이 없는 경우)
    try:
        df = data_loader.load(start_date=start_date, end_date=end_date)
    except FileNotFoundError:
        logger.warning("데이터 파일을 찾을 수 없습니다. 샘플 데이터를 생성합니다.")
        df = data_loader.generate_sample_data(
            start_date=start_date or "2024-01-01",
            end_date=end_date or "2024-12-31",
        )
    
    # 전략 생성
    strategy_config = config.get("strategy", {})
    strategy_name = strategy_config.get("name", "EMA_BB_TurtleTrailing")
    strategy = StrategyRegistry.get_strategy(strategy_name, config)
    
    # 백테스트 실행
    backtest_config = config.get("backtest", {})
    engine = BacktestEngine(strategy, backtest_config)
    result = engine.run(df)
    
    # 성능 지표 계산
    metrics = calculate_metrics(
        result["trades"],
        result["equity_curve"],
        engine.initial_capital,
    )
    
    # metrics에 final_equity 추가 (DB 저장용)
    metrics.final_equity = result["final_equity"]
    
    # 리포트 생성
    analytics_config = config.get("analytics", {})
    report_config = analytics_config.get("report", {})
    report_generator = ReportGenerator(report_config)
    report_generator.generate(metrics, result["trades"], result["equity_curve"])
    
    # 데이터베이스에 결과 저장
    db_config = data_config.get("database", {})
    if db_config.get("connection_string"):
        try:
            # 세션 ID 생성 (날짜 + 시간 + 심볼)
            session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{data_config.get('symbol', 'UNKNOWN')}"
            
            # 데이터베이스 로거 초기화
            db_logger = DatabaseLogger(
                connection_string=db_config.get("connection_string"),
                project_prefix="myno"
            )
            
            # 백테스트 결과 저장
            db_logger.save_backtest_result(
                session_id=session_id,
                metrics=metrics,
                config=config,
                start_date=start_date,
                end_date=end_date,
            )
            
            # 거래 상세 기록 저장
            if not result["trades"].empty:
                db_logger.save_trades(session_id, result["trades"])
            
            # 자기반성 일지 생성 및 저장
            reflection_gen = ReflectionGenerator()
            reflection = reflection_gen.generate_reflection(metrics, session_id, config)
            
            db_logger.save_reflection(
                session_id=session_id,
                performance_rating=reflection["performance_rating"],
                strengths=reflection["strengths"],
                weaknesses=reflection["weaknesses"],
                lessons_learned=reflection["lessons_learned"],
                improvements=reflection["improvements"],
                next_actions=reflection["next_actions"],
                emotional_state=reflection["emotional_state"],
                notes=reflection["notes"],
            )
            
            logger.info(f"데이터베이스 저장 완료: session_id={session_id}")
            logger.info(f"성과 평가: {reflection['performance_rating']}/10")
            
        except Exception as e:
            logger.error(f"데이터베이스 저장 실패: {e}")
    
    logger.info("백테스트 완료")


def run_optimize(
    config: dict, 
    method: str, 
    n_trials: int, 
    max_iterations: int = 5,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    target_win_rate: float = 0.5,
    target_return: float = 0.0,
    step_size: int = 5,
    base_ema: Optional[List[int]] = None,
    variation_range: int = 20,
):
    """파라미터 최적화 실행"""
    logger.info(f"파라미터 최적화 시작: {method}")
    
    # 데이터 로드 (한 번만)
    data_config = config.get("data", {})
    data_loader = DataLoader(data_config)
    df = data_loader.load()
    
    if df.empty:
        logger.error("데이터를 로드할 수 없습니다.")
        return
    
    logger.info(f"데이터 로드 완료: {len(df)}행")
    
    # 최적화 설정
    optimization_config = config.get("optimization", {})
    optimization_config["n_trials"] = n_trials
    objective_config = optimization_config.get("objective", {})
    primary_objective = objective_config.get("primary", "sharpe_ratio")
    constraints = objective_config.get("constraints", {})
    
    # 백테스트 설정
    backtest_config = config.get("backtest", {})
    
    def objective_func(params: dict) -> float:
        """목적 함수: 파라미터에 대해 백테스트 실행하고 점수 반환"""
        try:
            # 전략 설정 복사 및 파라미터 업데이트
            strategy_config = config.get("strategy", {}).copy()
            indicators_config = config.get("indicators", {}).copy()
            
            # EMA 파라미터 업데이트
            if "ema_fast" in params:
                indicators_config["ema"] = indicators_config.get("ema", {})
                indicators_config["ema"]["periods"] = [
                    params.get("ema_fast", 20),
                    params.get("ema_mid", 40),
                    params.get("ema_slow", 80),
                ]
            
            # BB 파라미터 업데이트
            if "bb_period" in params:
                indicators_config["bollinger"] = indicators_config.get("bollinger", {})
                indicators_config["bollinger"]["period"] = params["bb_period"]
            
            # ATR multiplier 업데이트
            if "atr_multiplier" in params:
                strategy_config["exit"] = strategy_config.get("exit", {})
                strategy_config["exit"]["stop_loss"] = strategy_config["exit"].get("stop_loss", {})
                strategy_config["exit"]["stop_loss"]["atr_multiplier"] = params["atr_multiplier"]
            
            # 전략 생성
            strategy = StrategyRegistry.create_strategy(
                strategy_config.get("name", "EMA_BB_TurtleTrailing"),
                {**strategy_config, "indicators": indicators_config, "regime": config.get("regime", {})}
            )
            
            # 백테스트 엔진 생성 및 실행
            engine = BacktestEngine(strategy, backtest_config)
            result = engine.run(df)
            
            # 성능 지표 계산
            if result["trades"].empty:
                logger.warning(f"파라미터 {params}: 거래 없음")
                return -999.0  # 매우 낮은 점수
            
            metrics = calculate_metrics(
                result["trades"],
                result["equity_curve"],
                backtest_config.get("engine", {}).get("initial_capital", 100000),
            )
            
            # 제약 조건 확인
            if constraints.get("min_trades", 0) > 0:
                if metrics.total_trades < constraints["min_trades"]:
                    logger.debug(f"파라미터 {params}: 거래 수 부족 ({metrics.total_trades})")
                    return -999.0
            
            if constraints.get("max_drawdown", 1.0) < 1.0:
                if metrics.max_drawdown > constraints["max_drawdown"]:
                    logger.debug(f"파라미터 {params}: 드로다운 초과 ({metrics.max_drawdown:.2%})")
                    return -999.0
            
            # 목적 함수 값 반환
            if primary_objective == "sharpe_ratio":
                score = metrics.sharpe_ratio if metrics.sharpe_ratio is not None else -999.0
            elif primary_objective == "profit_factor":
                score = metrics.profit_factor if metrics.profit_factor is not None else -999.0
            elif primary_objective == "total_return":
                score = metrics.total_return if metrics.total_return is not None else -999.0
            elif primary_objective == "calmar_ratio":
                score = metrics.calmar_ratio if metrics.calmar_ratio is not None else -999.0
            else:
                score = metrics.sharpe_ratio if metrics.sharpe_ratio is not None else -999.0
            
            logger.info(f"파라미터 {params}: {primary_objective}={score:.4f}, 거래={metrics.total_trades}, 수익률={metrics.total_return:.2%}")
            return score
            
        except Exception as e:
            logger.error(f"파라미터 평가 실패 {params}: {e}")
            return -999.0
    
    if method == "reflection":
        # Reflection 기반 자동 최적화
        db_config = config.get("data", {}).get("database", {})
        db_logger = None
        if db_config.get("connection_string"):
            db_logger = DatabaseLogger(
                connection_string=db_config.get("connection_string"),
                project_prefix="myno"
            )
        
        reflection_optimizer = ReflectionOptimizer(config, db_logger)
        
        # 초기 백테스트 실행
        logger.info("초기 백테스트 실행 중...")
        strategy_config = config.get("strategy", {})
        strategy_name = strategy_config.get("name", "EMA_BB_TurtleTrailing")
        strategy = StrategyRegistry.get_strategy(strategy_name, config)
        engine = BacktestEngine(strategy, backtest_config)
        result = engine.run(df)
        metrics = calculate_metrics(
            result["trades"],
            result["equity_curve"],
            engine.initial_capital,
        )
        
        # Reflection 기반 최적화 (반복적으로 개선)
        session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_reflection_opt"
        
        for iteration in range(max_iterations):
            logger.info(f"\n{'='*60}")
            logger.info(f"Reflection 최적화 반복 {iteration + 1}/{max_iterations}")
            logger.info(f"{'='*60}")
            
            # Reflection 생성 및 파라미터 조정
            opt_result = reflection_optimizer.optimize_from_reflection(
                metrics, session_id, config, max_iterations=1  # 한 번씩 반복
            )
            
            # 조정된 설정으로 재실행
            optimized_config = opt_result["best_config"]
            strategy = StrategyRegistry.get_strategy(strategy_name, optimized_config)
            engine = BacktestEngine(strategy, backtest_config)
            result = engine.run(df)
            metrics = calculate_metrics(
                result["trades"],
                result["equity_curve"],
                engine.initial_capital,
            )
            
            logger.info(f"반복 {iteration + 1} 결과: Sharpe={metrics.sharpe_ratio:.2f}, 수익률={metrics.total_return:.2%}")
            
            # 성과가 충분히 좋으면 조기 종료
            if metrics.sharpe_ratio > 2.0 and metrics.total_return > 0.1:
                logger.info("목표 성과 달성! 조기 종료")
                break
        
        logger.info("=" * 60)
        logger.info("Reflection 기반 최적화 완료!")
        logger.info(reflection_optimizer.get_optimization_summary())
        logger.info("=" * 60)
        
        # 최적화된 설정으로 최종 백테스트 재실행
        logger.info("최적화된 설정으로 최종 백테스트 재실행 중...")
        run_backtest(optimized_config, None, None)
        return  # Reflection 모드 종료
        
    elif method == "continuous":
        # 연속 최적화 모드
        if not start_date or not end_date:
            logger.error("연속 최적화 모드에서는 --start와 --end 인자가 필요합니다.")
            logger.info("예: --start '2024-01-01 12:30' --end '2024-01-31 13:30'")
            return
        
        db_config = config.get("data", {}).get("database", {})
        db_logger = None
        if db_config.get("connection_string"):
            db_logger = DatabaseLogger(
                connection_string=db_config.get("connection_string"),
                project_prefix="myno"
            )
        
        continuous_optimizer = ContinuousOptimizer(
            config,
            db_logger,
            target_win_rate=target_win_rate,
            target_return=target_return,
            base_ema=base_ema,
            variation_range=variation_range,
            step_size=step_size,
        )
        
        logger.info("연속 최적화 모드 시작")
        logger.info(f"기간: {start_date} ~ {end_date}")
        logger.info(f"목표: 승률 {target_win_rate:.1%} 이상 또는 수익률 {target_return:.1%} 이상")
        
        # 데이터 로드
        data_config = config.get("data", {})
        data_loader = DataLoader(data_config)
        df = data_loader.load(start_date=start_date, end_date=end_date)
        
        if df.empty:
            logger.error("데이터를 로드할 수 없습니다.")
            return
        
        logger.info(f"데이터 로드 완료: {len(df)}행")
        
        # 연속 최적화 루프
        backtest_config = config.get("backtest", {})
        strategy_config = config.get("strategy", {})
        strategy_name = strategy_config.get("name", "EMA_BB_TurtleTrailing")
        
        total_combinations = len(continuous_optimizer.param_combinations)
        max_iterations = min(max_iterations, total_combinations)  # 조합 수만큼만
        
        for iteration in range(max_iterations):
            logger.info(f"\n{'='*60}")
            logger.info(f"조합 {iteration + 1}/{max_iterations} (전체 {total_combinations}개 중)")
            
            # 다음 파라미터 조합 가져오기
            opt_result = continuous_optimizer.optimize_continuously(
                start_date, end_date, max_iterations=1, step_size=step_size
            )
            
            if opt_result["best_params"] is None:
                logger.info("모든 조합 테스트 완료")
                break
            
            current_params = opt_result["best_params"]
            logger.info(f"현재 테스트 파라미터:")
            logger.info(f"  Fast EMA: {current_params['ema_fast']}")
            logger.info(f"  Mid EMA: {current_params['ema_mid']}")
            logger.info(f"  Slow EMA: {current_params['ema_slow']}")
            logger.info(f"  ATR Multiplier: {current_params['atr_multiplier']:.2f}")
            
            # 파라미터를 설정에 적용
            optimized_config = continuous_optimizer.apply_params_to_config(config, current_params)
            
            # 백테스트 실행
            strategy = StrategyRegistry.get_strategy(strategy_name, optimized_config)
            engine = BacktestEngine(strategy, backtest_config)
            result = engine.run(df)
            
            if result["trades"].empty:
                logger.warning("거래가 없습니다. 다음 조합으로 진행...")
                continue
            
            # 성능 지표 계산
            metrics = calculate_metrics(
                result["trades"],
                result["equity_curve"],
                engine.initial_capital,
            )
            
            logger.info(f"결과: 승률={metrics.win_rate:.2%}, 수익률={metrics.total_return:.2%}, Sharpe={metrics.sharpe_ratio:.2f}")
            
            # 목표 달성 확인 및 스냅샷 저장
            session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_continuous_{iteration+1}"
            snapshot_saved = continuous_optimizer.check_and_save_snapshot(
                metrics, current_params, start_date, end_date, session_id
            )
            
            if snapshot_saved:
                # 목표 달성 시 DB에 결과 저장
                if db_logger:
                    try:
                        metrics.final_equity = result["final_equity"]
                        db_logger.save_backtest_result(
                            session_id=session_id,
                            metrics=metrics,
                            config=optimized_config,
                            start_date=start_date,
                            end_date=end_date,
                        )
                        if not result["trades"].empty:
                            db_logger.save_trades(session_id, result["trades"])
                    except Exception as e:
                        logger.error(f"DB 저장 실패: {e}")
            
            # 짧은 대기 (과부하 방지)
            time.sleep(0.1)
        
        # 최종 요약
        logger.info("=" * 60)
        logger.info("연속 최적화 완료!")
        logger.info(continuous_optimizer.get_snapshots_summary())
        logger.info("=" * 60)
        return  # Continuous 모드 종료
        
    elif method == "grid_search":
        optimizer = GridSearchOptimizer(optimization_config)
    elif method == "bayesian":
        optimizer = BayesianOptimizer(optimization_config)
    else:
        raise ValueError(f"알 수 없는 최적화 방법: {method}")
    
    result = optimizer.optimize(objective_func)
    
    logger.info("=" * 60)
    logger.info("최적화 완료!")
    logger.info(f"최적 파라미터: {result['best_params']}")
    logger.info(f"최적 점수 ({primary_objective}): {result['best_score']:.4f}")
    logger.info("=" * 60)
    
    # 최적 파라미터로 백테스트 재실행
    logger.info("최적 파라미터로 백테스트 재실행 중...")
    run_backtest(config, None, None)  # 전체 기간으로 재실행


def run_walk_forward(config: dict, in_sample_days: int, out_sample_days: int):
    """Walk-Forward 분석 실행"""
    logger.info("Walk-Forward 분석 시작")
    
    # 데이터 로드
    data_config = config.get("data", {})
    data_loader = DataLoader(data_config)
    
    try:
        df = data_loader.load()
    except FileNotFoundError:
        logger.warning("데이터 파일을 찾을 수 없습니다. 샘플 데이터를 생성합니다.")
        df = data_loader.generate_sample_data()
    
    # 전략 생성
    strategy_config = config.get("strategy", {})
    strategy_name = strategy_config.get("name", "EMA_BB_TurtleTrailing")
    strategy = StrategyRegistry.get_strategy(strategy_name, config)
    
    # Walk-Forward 분석
    backtest_config = config.get("backtest", {})
    period_config = backtest_config.get("period", {})
    walk_forward_config = period_config.get("walk_forward", {})
    walk_forward_config["in_sample_days"] = in_sample_days
    walk_forward_config["out_of_sample_days"] = out_sample_days
    
    analyzer = WalkForwardAnalyzer(backtest_config)
    result = analyzer.analyze(strategy, df, backtest_config)
    
    logger.info("Walk-Forward 분석 완료")


def run_report(config: dict, formats: list, output_dir: str):
    """리포트 생성"""
    logger.info("리포트 생성 시작")
    # 리포트 생성 로직 (백테스트 결과가 필요한 경우)
    logger.info("리포트 생성 완료")


def run_dashboard(
    config: dict,
    port: int,
    host: str = "0.0.0.0",
    enable_webhook: bool = False,
    live_trader: Optional[Any] = None,
):
    """대시보드 실행"""
    from web.server import create_app, set_webhook_trader
    from trading.webhook_trader import WebhookTrader
    
    app = create_app()
    
    # 웹훅 거래자 설정 (활성화된 경우)
    if enable_webhook:
        webhook_trader = WebhookTrader(config, live_trader=live_trader)
        set_webhook_trader(webhook_trader)
        logger.info("=" * 60)
        logger.info("TradingView 웹훅 활성화됨")
        logger.info(f"웹훅 URL: http://{host}:{port}/webhook/tradingview")
        if live_trader:
            logger.info("✅ LiveTrader와 연결됨 - 웹훅 수신 시 자동 거래 실행")
        else:
            logger.warning("⚠️  LiveTrader가 없습니다")
            logger.warning("   웹훅은 수신하지만 거래는 제한적으로 실행됩니다")
            logger.warning("   완전한 자동 거래를 원하면 LiveTrader를 별도로 실행하세요:")
            logger.warning("   python3 main.py live --auto-optimize --paper-trading")
        logger.info("=" * 60)
    
    logger.info(f"웹 대시보드 시작: http://{host}:{port}")
    if enable_webhook:
        logger.info("웹훅 엔드포인트: http://{host}:{port}/webhook/tradingview")
    run_web_server(host=host, port=port, debug=False)


def run_live_trading(
    config: dict,
    auto_optimize: bool = True,
    paper_trading: bool = True,
    optimization_window: int = 30,
    reoptimize_frequency: str = "daily",
):
    """실시간 거래 실행"""
    logger.info("=" * 60)
    logger.info("실시간 거래 모드 시작")
    logger.info("=" * 60)
    
    # 데이터베이스 로거
    db_config = config.get("data", {}).get("database", {})
    db_logger = None
    if db_config.get("connection_string"):
        db_logger = DatabaseLogger(
            connection_string=db_config.get("connection_string"),
            project_prefix="myno"
        )
    
    # 실시간 거래자 생성
    live_trader = LiveTrader(
        config,
        db_logger,
        optimization_window_days=optimization_window,
        reoptimize_frequency=reoptimize_frequency,
    )
    
    # 거래 시작
    try:
        live_trader.start_trading(
            auto_optimize=auto_optimize,
            paper_trading=paper_trading,
        )
    except KeyboardInterrupt:
        logger.info("거래 중지 요청됨")
        live_trader.stop()
    except Exception as e:
        logger.error(f"거래 실행 중 에러: {e}")
        live_trader.stop()
        raise


if __name__ == "__main__":
    main()

