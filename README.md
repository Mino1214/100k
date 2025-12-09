# BTCUSDT 백테스트 프레임워크 v2.0

BTCUSDT 1분봉 자동매매 백테스트 프레임워크입니다. 모듈화된 OOP 구조로 확장 가능하며, 레짐 기반 전략, 고급 리스크 관리, 통계 분석을 지원합니다.

## 주요 기능

- 📊 **다양한 데이터 소스**: CSV, Binance API, Database 지원
- 📈 **확장 가능한 지표 시스템**: EMA, SMA, MACD, ATR, Bollinger Bands 등
- 🎯 **레짐 기반 전략**: Bull/Bear/Sideways 시장 상태 자동 탐지
- 💰 **고급 리스크 관리**: Fixed, Risk%, Kelly, Volatility Adjusted 포지션 사이징
- 🔄 **이벤트 기반 백테스트 엔진**: 정확한 시뮬레이션
- 📉 **통계 분석**: Sharpe, Sortino, Calmar, Monte Carlo 시뮬레이션
- 🎨 **인터랙티브 시각화**: Plotly 기반 대시보드
- 🔍 **파라미터 최적화**: Grid Search, Bayesian Optimization
- 📋 **자동 리포트 생성**: HTML/PDF 리포트

## 설치

```bash
pip install -r requirements.txt
```

또는

```bash
pip install -e .
```

## 빠른 시작

### 기본 백테스트 실행

```bash
python main.py backtest --config config/settings.yaml
```

### 특정 기간 백테스트

```bash
python main.py backtest --start 2024-01-01 --end 2024-06-30
```

### 파라미터 최적화

```bash
python main.py optimize --method bayesian --trials 100
```

### Walk-Forward 분석

```bash
python main.py walk-forward --in-sample 180 --out-sample 30
```

### 리포트 생성

```bash
python main.py report --format html --output ./reports/
```

### 대시보드 실행

```bash
python main.py dashboard --port 8050
```

## 프로젝트 구조

```
btc_backtest_framework/
├── config/          # 설정 파일
├── data/            # 데이터 로더 및 전처리
├── indicators/      # 기술적 지표
├── strategy/        # 전략 구현
├── execution/       # 실행 및 리스크 관리
├── backtest/        # 백테스트 엔진
├── analytics/       # 성능 분석
├── visualization/   # 시각화
├── optimization/    # 파라미터 최적화
├── utils/           # 유틸리티
├── tests/           # 테스트
└── notebooks/       # Jupyter 노트북
```

## 설정 파일

설정은 YAML 파일로 관리됩니다. `config/settings.yaml`을 참조하세요.

## 문서

자세한 문서는 각 모듈의 docstring을 참조하세요.

## 라이선스

MIT License

