# Nginx 설정 가이드 - TradingView 웹훅

## 개요

TradingView 웹훅을 외부에서 받으려면 nginx를 리버스 프록시로 설정하는 것이 좋습니다. 이를 통해:
- 외부에서 접근 가능한 URL 제공
- SSL/TLS 보안 적용
- 로드 밸런싱 및 성능 최적화
- 로깅 및 모니터링

## 설치

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install nginx
```

### CentOS/RHEL
```bash
sudo yum install nginx
# 또는
sudo dnf install nginx
```

## 설정 방법

### 1. 설정 파일 생성

```bash
sudo nano /etc/nginx/sites-available/tradingview-webhook
```

또는

```bash
sudo nano /etc/nginx/conf.d/tradingview-webhook.conf
```

### 2. 설정 내용 복사

`nginx.conf.example` 파일의 내용을 복사하거나, 아래 설정을 사용:

```nginx
server {
    listen 80;
    server_name your-server-ip-or-domain.com;  # 서버 IP 또는 도메인
    
    # 로그 설정
    access_log /var/log/nginx/tradingview_webhook_access.log;
    error_log /var/log/nginx/tradingview_webhook_error.log;
    
    # 클라이언트 최대 바디 크기
    client_max_body_size 1M;
    
    # 타임아웃 설정
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # TradingView 웹훅 엔드포인트
    location /webhook/tradingview {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS 헤더
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "POST, GET, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization";
        
        # OPTIONS 요청 처리
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "POST, GET, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization";
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
    }
    
    # 대시보드 및 API
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API 엔드포인트
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. 심볼릭 링크 생성 (sites-available 사용 시)

```bash
sudo ln -s /etc/nginx/sites-available/tradingview-webhook /etc/nginx/sites-enabled/
```

### 4. 설정 테스트

```bash
sudo nginx -t
```

### 5. Nginx 재시작

```bash
sudo systemctl restart nginx
# 또는
sudo service nginx restart
```

## HTTPS 설정 (권장)

### Let's Encrypt 사용

```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo certbot renew --dry-run
```

### 수동 SSL 설정

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # 웹훅 설정 (위와 동일)
    location /webhook/tradingview {
        proxy_pass http://127.0.0.1:5000;
        # ... (위와 동일)
    }
}

# HTTP to HTTPS 리다이렉트
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## 방화벽 설정

### UFW (Ubuntu)
```bash
sudo ufw allow 'Nginx Full'
# 또는
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### firewalld (CentOS/RHEL)
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## TradingView Alert 설정

nginx 설정 후 TradingView Alert의 Webhook URL을 다음과 같이 설정:

### HTTP 사용 시
```
http://your-server-ip-or-domain/webhook/tradingview
```

### HTTPS 사용 시 (권장)
```
https://your-domain.com/webhook/tradingview
```

## 테스트

### 1. Nginx 설정 테스트
```bash
curl http://your-server-ip/webhook/tradingview/test
```

### 2. 웹훅 테스트
```bash
curl -X POST http://your-server-ip/webhook/tradingview \
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

## 보안 강화

### 1. IP 화이트리스트 (선택적)

TradingView의 IP만 허용하려면:

```nginx
location /webhook/tradingview {
    # TradingView IP 범위 (실제 IP 확인 필요)
    allow 52.84.0.0/15;
    allow 52.85.0.0/15;
    deny all;
    
    proxy_pass http://127.0.0.1:5000;
    # ... (나머지 설정)
}
```

### 2. 웹훅 시크릿 검증

nginx에서 기본 인증 추가:

```nginx
location /webhook/tradingview {
    auth_basic "TradingView Webhook";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    proxy_pass http://127.0.0.1:5000;
    # ... (나머지 설정)
}
```

비밀번호 파일 생성:
```bash
sudo htpasswd -c /etc/nginx/.htpasswd username
```

### 3. Rate Limiting

```nginx
# http 블록에 추가
limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=10r/m;

server {
    # ...
    location /webhook/tradingview {
        limit_req zone=webhook_limit burst=5;
        proxy_pass http://127.0.0.1:5000;
        # ... (나머지 설정)
    }
}
```

## 로그 확인

```bash
# 접근 로그
sudo tail -f /var/log/nginx/tradingview_webhook_access.log

# 에러 로그
sudo tail -f /var/log/nginx/tradingview_webhook_error.log

# Nginx 에러 로그
sudo tail -f /var/log/nginx/error.log
```

## 문제 해결

### 502 Bad Gateway
- Flask 앱이 실행 중인지 확인: `ps aux | grep python`
- 포트 확인: `netstat -tlnp | grep 5000`
- Flask 앱 로그 확인

### 504 Gateway Timeout
- `proxy_read_timeout` 값 증가
- Flask 앱 성능 확인

### Connection Refused
- 방화벽 설정 확인
- Flask 앱이 `0.0.0.0`에서 리스닝하는지 확인

## 자동 시작 설정

### systemd 서비스 (Flask 앱)

`/etc/systemd/system/tradingview-webhook.service`:

```ini
[Unit]
Description=TradingView Webhook Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/forfunonly
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python /path/to/forfunonly/main.py dashboard --host 0.0.0.0 --port 5000 --webhook
Restart=always

[Install]
WantedBy=multi-user.target
```

서비스 활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tradingview-webhook
sudo systemctl start tradingview-webhook
```

## 모니터링

### Nginx 상태 확인
```bash
sudo systemctl status nginx
```

### Flask 앱 상태 확인
```bash
sudo systemctl status tradingview-webhook
```

### 로그 모니터링
```bash
# 실시간 로그 모니터링
sudo tail -f /var/log/nginx/tradingview_webhook_access.log
```

## 참고사항

- nginx를 사용하지 않아도 직접 포트를 열어서 사용할 수 있지만, 보안상 권장하지 않습니다
- HTTPS 사용을 강력히 권장합니다
- 서버 IP가 변경되면 TradingView Alert 설정도 업데이트해야 합니다
- 도메인을 사용하면 IP 변경 시에도 유연하게 대응할 수 있습니다

