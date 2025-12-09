# TradingView 웹훅 자동 거래 가이드

## 현재 상태

### ✅ 구현된 기능
1. **TradingView 웹훅 수신** - `/webhook/tradingview` 엔드포인트로 데이터 수신
2. **웹훅 데이터 파싱** - TradingView 형식을 표준 형식으로 변환
3. **LiveTrader 연동** - 웹훅 데이터를 LiveTrader에 전달

### ⚠️ 주의사항
**현재는 웹훅만 수신하고, 실제 거래를 실행하려면 LiveTrader를 별도로 실행해야 합니다.**

## 자동 거래를 위한 설정

### 방법 1: LiveTrader와 함께 실행 (권장)

#### 터미널 1: LiveTrader 실행
```bash
cd ~/100k
nohup python3 main.py live --auto-optimize --paper-trading > logs/live-trader.log 2>&1 &
```

#### 터미널 2: 웹훅 서버 실행
```bash
cd ~/100k
nohup python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook > logs/app.log 2>&1 &
```

### 방법 2: 통합 실행 (개발 중)

현재는 웹훅 서버와 LiveTrader를 별도로 실행해야 합니다. 향후 통합 버전이 추가될 예정입니다.

## 웹훅 수신 확인

### 1. 웹훅 테스트
```bash
curl -X POST http://localhost:5000/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "ETHUSDT",
    "exchange": "BINANCE",
    "timeframe": "1m",
    "timestamp": "2024-01-15T10:30:00",
    "open": 2500.0,
    "high": 2510.0,
    "low": 2490.0,
    "close": 2505.0,
    "volume": 1000.0
  }'
```

### 2. 로그 확인
```bash
# 웹훅 서버 로그
tail -f logs/app.log | grep -i webhook

# LiveTrader 로그
tail -f logs/live-trader.log
```

## TradingView Alert 설정

### Pine Script 예시
```pinescript
//@version=5
strategy("Webhook Alert", overlay=true)

// 봉 마감 감지
bar_closed = barstate.isconfirmed

// 조건 (예: 볼린저 밴드 하단 터치)
bb_lower = ta.sma(close, 20) - ta.stdev(close, 20) * 2
long_condition = bar_closed and close <= bb_lower

// Alert 메시지 생성
if long_condition
    alert_message = '{"symbol": "' + syminfo.ticker + '", "exchange": "' + syminfo.exchange + '", "timeframe": "' + timeframe.period + '", "timestamp": "' + str.tostring(time) + '", "open": ' + str.tostring(open) + ', "high": ' + str.tostring(high) + ', "low": ' + str.tostring(low) + ', "close": ' + str.tostring(close) + ', "volume": ' + str.tostring(volume) + '}'
    alert(alert_message, alert.freq_once_per_bar)
```

### Alert 설정
1. TradingView 차트에서 Alert 생성
2. **Condition**: 봉 마감 조건 선택
3. **Webhook URL**: `http://your-server-ip:5000/webhook/tradingview`
4. **Message**: 위의 JSON 형식 사용

## 작동 흐름

1. **TradingView** → 봉 마감 시 웹훅 전송
2. **웹훅 서버** → `/webhook/tradingview`에서 데이터 수신
3. **WebhookTrader** → 데이터 파싱 및 정규화
4. **LiveTrader** → 봉 데이터 처리 및 거래 로직 실행
5. **학습 시스템** → 거래 결과 분석 및 학습

## 현재 제한사항

1. **LiveTrader 별도 실행 필요**: 웹훅 서버만으로는 거래가 실행되지 않습니다
2. **연결 확인**: LiveTrader가 실행 중이어야 웹훅 데이터가 처리됩니다
3. **페이퍼 트레이딩**: `--paper-trading` 옵션으로 가상매매만 실행됩니다

## 향후 개선 사항

- 웹훅 서버와 LiveTrader 통합
- 웹훅 수신 시 자동으로 LiveTrader 시작
- 웹훅만으로도 거래 실행 가능하도록 개선

## 문제 해결

### 웹훅은 받지만 거래가 안 되는 경우
```bash
# LiveTrader가 실행 중인지 확인
ps aux | grep "main.py live"

# 실행되지 않았다면 시작
nohup python3 main.py live --auto-optimize --paper-trading > logs/live-trader.log 2>&1 &
```

### 웹훅이 수신되지 않는 경우
```bash
# 서버가 실행 중인지 확인
ps aux | grep "main.py dashboard"

# 포트 확인
lsof -i :5000

# 로그 확인
tail -f logs/app.log
```

## 요약

**현재 상태:**
- ✅ 웹훅 수신 가능
- ⚠️ 거래 실행을 위해서는 LiveTrader를 별도로 실행해야 함

**자동 거래를 원하면:**
1. LiveTrader 실행 (`main.py live`)
2. 웹훅 서버 실행 (`main.py dashboard --webhook`)
3. TradingView Alert 설정

두 프로세스가 모두 실행되어야 웹훅 → 자동 거래가 작동합니다.

