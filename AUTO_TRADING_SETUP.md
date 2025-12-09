# 자동 거래 설정 가이드

## 🚀 빠른 시작 (권장)

웹훅 서버만 실행하면 LiveTrader가 자동으로 시작되어 완전한 자동 거래가 가능합니다!

```bash
cd ~/100k
nohup python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook --auto-live-trader > logs/app.log 2>&1 &
```

이 명령어 하나로:
- ✅ 웹훅 서버 시작
- ✅ LiveTrader 자동 시작
- ✅ TradingView 웹훅 수신
- ✅ 자동 거래 실행 (가상매매)
- ✅ 학습 시스템 작동

## 명령어 옵션

### 기본 웹훅 서버 (LiveTrader 없음)
```bash
python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook
```
- 웹훅만 수신 (거래는 제한적)

### 웹훅 + LiveTrader 자동 시작 (권장)
```bash
python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook --auto-live-trader
```
- 웹훅 수신 + 자동 거래 실행

## 작동 방식

1. **웹훅 서버 시작** → Flask 서버 실행
2. **LiveTrader 자동 생성** → 백그라운드 스레드에서 시작
3. **웹훅 수신** → TradingView에서 봉 마감 데이터 전송
4. **자동 거래** → LiveTrader가 웹훅 데이터를 받아서 거래 실행

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

## 로그 확인

```bash
# 실시간 로그
tail -f logs/app.log

# 웹훅 수신 확인
tail -f logs/app.log | grep -i webhook

# 거래 실행 확인
tail -f logs/app.log | grep -i "거래\|trade\|진입\|청산"
```

## 프로세스 확인

```bash
# 실행 중인 프로세스 확인
ps aux | grep "main.py dashboard"

# 포트 확인
lsof -i :5000
```

## 문제 해결

### LiveTrader가 시작되지 않는 경우
```bash
# 로그 확인
tail -n 100 logs/app.log | grep -i "live\|trader\|error"

# 수동으로 LiveTrader 실행 테스트
python3 main.py live --auto-optimize --paper-trading
```

### 웹훅이 수신되지 않는 경우
```bash
# 서버가 실행 중인지 확인
ps aux | grep "main.py dashboard"

# 웹훅 테스트
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

## 요약

**한 줄로 시작:**
```bash
python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook --auto-live-trader
```

이제 TradingView Alert만 설정하면 자동으로 거래가 실행됩니다! 🎉

