# TradingView 웹훅 설정 가이드

## 개요

TradingView의 Alert 기능을 사용하여 봉 마감 시 웹훅으로 데이터를 전송하고, 이를 받아서 자동으로 거래를 실행할 수 있습니다.

## API 엔드포인트

### 웹훅 수신
- **URL**: `http://your-server:port/webhook/tradingview`
- **Method**: `POST`
- **Content-Type**: `application/json`

### 테스트
- **URL**: `http://your-server:port/webhook/tradingview/test`
- **Method**: `GET` or `POST`

## TradingView Alert 설정

### 1. Pine Script 예시

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
    alert_message = '{"symbol": "' + syminfo.ticker + '", "exchange": "' + syminfo.exchange + '", "timeframe": "' + timeframe.period + '", "timestamp": "' + str.tostring(time) + '", "open": ' + str.tostring(open) + ', "high": ' + str.tostring(high) + ', "low": ' + str.tostring(low) + ', "close": ' + str.tostring(close) + ', "volume": ' + str.tostring(volume) + ', "action": "buy"}'
    alert(alert_message, alert.freq_once_per_bar)
```

### 2. Alert 설정

1. TradingView 차트에서 Alert 생성
2. **Condition**: 원하는 조건 선택 (예: 봉 마감)
3. **Webhook URL**: `http://your-server:port/webhook/tradingview`
4. **Message**: JSON 형식으로 데이터 전송

### 3. Alert 메시지 형식

#### 상세 형식 (권장)
```json
{
    "symbol": "{{ticker}}",
    "exchange": "{{exchange}}",
    "timeframe": "{{interval}}",
    "timestamp": "{{time}}",
    "open": {{open}},
    "high": {{high}},
    "low": {{low}},
    "close": {{close}},
    "volume": {{volume}},
    "action": "{{strategy.order.action}}",
    "strategy_name": "{{strategy.name}}"
}
```

#### 간단한 형식
```json
{
    "ticker": "{{ticker}}",
    "price": {{close}},
    "time": "{{time}}",
    "volume": {{volume}}
}
```

## 서버 실행

### 기본 실행
```bash
python main.py dashboard --host 0.0.0.0 --port 5000
```

### 웹훅 활성화
```bash
python main.py dashboard --host 0.0.0.0 --port 5000 --webhook
```

### 실시간 거래와 함께 실행
```bash
# 터미널 1: 실시간 거래자 실행
python main.py live --auto-optimize --paper-trading

# 터미널 2: 웹훅 활성화된 대시보드 실행
python main.py dashboard --host 0.0.0.0 --port 5000 --webhook
```

## 웹훅 데이터 처리 흐름

1. **TradingView Alert** → 봉 마감 시 웹훅 전송
2. **웹훅 엔드포인트** (`/webhook/tradingview`) → 데이터 수신
3. **데이터 파싱** → TradingView 형식을 표준 형식으로 변환
4. **WebhookTrader** → 봉 데이터 처리
5. **LiveTrader** → 실시간 거래 로직 실행
6. **거래 실행** → 자동으로 진입/청산 결정

## 보안

### 웹훅 시크릿 검증 (선택적)

요청 헤더에 `X-Webhook-Secret`을 포함하여 검증할 수 있습니다:

```python
# TradingView Alert에서
headers = {
    "X-Webhook-Secret": "your-secret-key"
}
```

## 테스트

### curl로 테스트
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

### 테스트 엔드포인트
```bash
curl http://localhost:5000/webhook/tradingview/test
```

## 로그 확인

웹훅 수신 및 처리 로그는 다음에서 확인할 수 있습니다:

```bash
tail -f logs/backtest.log
```

## 문제 해결

### 웹훅이 수신되지 않는 경우
1. 서버가 외부에서 접근 가능한지 확인
2. 방화벽 설정 확인
3. TradingView Alert의 Webhook URL 확인
4. 로그에서 에러 메시지 확인

### 데이터 파싱 실패
1. Alert 메시지 형식 확인
2. JSON 형식이 올바른지 확인
3. 필수 필드 (symbol, close 등) 포함 여부 확인

## 예시: 완전한 Pine Script

```pinescript
//@version=5
strategy("Webhook Trading Bot", overlay=true, initial_capital=100000)

// 지표
ema_fast = ta.ema(close, 20)
ema_slow = ta.ema(close, 50)
bb_upper = ta.sma(close, 20) + ta.stdev(close, 20) * 2
bb_lower = ta.sma(close, 20) - ta.stdev(close, 20) * 2

// 조건
long_condition = barstate.isconfirmed and close <= bb_lower and ema_fast > ema_slow
short_condition = barstate.isconfirmed and close >= bb_upper and ema_fast < ema_slow

// 웹훅 전송
if long_condition
    alert_json = '{"symbol": "' + syminfo.ticker + '", "exchange": "' + syminfo.exchange + '", "timeframe": "' + timeframe.period + '", "timestamp": "' + str.tostring(time) + '", "open": ' + str.tostring(open) + ', "high": ' + str.tostring(high) + ', "low": ' + str.tostring(low) + ', "close": ' + str.tostring(close) + ', "volume": ' + str.tostring(volume) + ', "action": "buy"}'
    alert(alert_json, alert.freq_once_per_bar)

if short_condition
    alert_json = '{"symbol": "' + syminfo.ticker + '", "exchange": "' + syminfo.exchange + '", "timeframe": "' + timeframe.period + '", "timestamp": "' + str.tostring(time) + '", "open": ' + str.tostring(open) + ', "high": ' + str.tostring(high) + ', "low": ' + str.tostring(low) + ', "close": ' + str.tostring(close) + ', "volume": ' + str.tostring(volume) + ', "action": "sell"}'
    alert(alert_json, alert.freq_once_per_bar)
```

## 참고사항

- TradingView Alert는 봉 마감 시 한 번만 실행됩니다
- 웹훅은 POST 요청으로 전송됩니다
- 서버는 24/7 실행되어야 합니다
- 네트워크 지연을 고려하여 설정하세요

