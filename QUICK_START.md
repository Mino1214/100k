# 빠른 시작 가이드

## 서버에서 실행하기

### 1. GitHub에서 코드 받기
```bash
cd ~/100k
git pull origin main
```

### 2. PM2로 실행 (권장)

#### PM2 설정 파일 생성
```bash
# ecosystem.config.js 파일이 없으면 생성
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'tradingview-webhook',
    script: 'python3',
    args: 'main.py dashboard --host 0.0.0.0 --port 5000 --webhook',
    cwd: process.env.HOME + '/100k',
    interpreter: 'python3',
    instances: 1,
    exec_mode: 'fork',
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PYTHONUNBUFFERED: '1',
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_file: './logs/pm2-combined.log',
    time: true,
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 4000,
  }],
};
EOF
```

#### PM2로 시작
```bash
pm2 start ecosystem.config.js --only tradingview-webhook
```

#### 상태 확인
```bash
pm2 status
pm2 logs tradingview-webhook
```

### 3. 직접 실행 (PM2 없이)

```bash
cd ~/100k
python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook
```

### 4. 백그라운드 실행 (PM2 없이)

```bash
cd ~/100k
nohup python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook > logs/app.log 2>&1 &
```

## TradingView 웹훅 URL

서버가 실행되면 다음 URL로 웹훅을 설정하세요:

```
http://your-server-ip:5000/webhook/tradingview
```

또는 nginx를 사용하는 경우:

```
http://your-server-ip/webhook/tradingview
```

## 테스트

```bash
# 웹훅 테스트
curl http://localhost:5000/webhook/tradingview/test

# 실제 웹훅 테스트
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

## 문제 해결

### 포트가 이미 사용 중인 경우
```bash
# 포트 확인
lsof -i :5000

# 프로세스 종료
kill -9 <PID>
```

### PM2가 실행되지 않는 경우
```bash
# 로그 확인
pm2 logs tradingview-webhook --lines 100

# 수동 실행해서 에러 확인
python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook
```

### 의존성 설치
```bash
pip3 install -r requirements.txt
```

