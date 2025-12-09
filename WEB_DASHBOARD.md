# 웹 대시보드 사용 가이드

## 개요

백테스트 진행 상황을 실시간으로 모니터링할 수 있는 웹 대시보드입니다.

## 기능

- ✅ 실시간 백테스트 진행 상황 모니터링
- ✅ 진행률 및 예상 남은 시간 표시
- ✅ 최신 백테스트 결과 조회
- ✅ 자기반성 일지 확인
- ✅ 거래 상세 기록 조회
- ✅ 자동 갱신 (2초마다 상태, 10초마다 결과)

## 실행 방법

### 1. 웹 대시보드만 실행

```bash
python3 main.py dashboard --port 5000 --host 0.0.0.0
```

### 2. 백테스트와 함께 실행

터미널 1: 웹 대시보드 실행
```bash
python3 main.py dashboard --port 5000 --host 0.0.0.0
```

터미널 2: 백테스트 실행
```bash
python3 main.py backtest --config config/settings.yaml
```

## 접속 방법

### 로컬 접속
```
http://localhost:5000
```

### 서버 접속 (같은 네트워크)
```
http://서버IP:5000
```

### 서버 접속 (외부)
```
http://서버공인IP:5000
```

## API 엔드포인트

### 상태 조회
```
GET /api/status
```

### 최신 결과 조회
```
GET /api/results/latest
```

### 특정 세션 결과 조회
```
GET /api/results/{session_id}
```

### 최신 자기반성 일지
```
GET /api/reflection/latest
```

### 특정 세션 자기반성 일지
```
GET /api/reflection/{session_id}
```

### 특정 세션 거래 기록
```
GET /api/trades/{session_id}
```

### 헬스 체크
```
GET /api/health
```

## 서버 배포

### 프로덕션 환경 (Gunicorn 사용)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web.server:app
```

### systemd 서비스로 등록 (선택사항)

`/etc/systemd/system/backtest-dashboard.service` 파일 생성:

```ini
[Unit]
Description=Backtest Web Dashboard
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/forfunonly
ExecStart=/usr/bin/python3 /path/to/forfunonly/main.py dashboard --port 5000 --host 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

서비스 시작:
```bash
sudo systemctl start backtest-dashboard
sudo systemctl enable backtest-dashboard
```

## 보안 고려사항

프로덕션 환경에서는 다음을 고려하세요:

1. **방화벽 설정**: 필요한 포트만 열기
2. **HTTPS 사용**: nginx + Let's Encrypt
3. **인증 추가**: Flask-Login 등 사용
4. **Rate Limiting**: Flask-Limiter 사용

## 문제 해결

### 포트가 이미 사용 중인 경우
```bash
# 다른 포트 사용
python3 main.py dashboard --port 5001
```

### 외부에서 접속이 안 되는 경우
1. 방화벽 확인: `sudo ufw allow 5000`
2. 서버 방화벽 확인
3. `--host 0.0.0.0` 옵션 사용 확인

