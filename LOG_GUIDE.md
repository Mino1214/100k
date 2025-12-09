# 로그 확인 가이드

## 실시간 로그 보기

### 1. 기본 로그 파일
```bash
# 실시간 로그 보기 (tail -f)
tail -f logs/app.log

# 마지막 100줄 보기
tail -n 100 logs/app.log

# 마지막 50줄 보기
tail -n 50 logs/app.log
```

### 2. 에러만 보기
```bash
# 에러 로그만 필터링
tail -f logs/app.log | grep -i error

# 또는
grep -i error logs/app.log
```

### 3. 특정 키워드 검색
```bash
# "웹훅" 관련 로그만 보기
tail -f logs/app.log | grep -i webhook

# "에러" 관련 로그만 보기
tail -f logs/app.log | grep -i error
```

## 프로세스 확인

### 실행 중인지 확인
```bash
# 프로세스 확인
ps aux | grep "main.py dashboard"

# 또는
pgrep -f "main.py dashboard"
```

### 포트 확인
```bash
# 5000번 포트 사용 확인
lsof -i :5000

# 또는
netstat -tlnp | grep 5000
```

## 로그 파일 위치

- **애플리케이션 로그**: `logs/app.log`
- **백테스트 로그**: `logs/backtest.log`
- **PM2 로그** (PM2 사용 시):
  - `logs/pm2-out.log`
  - `logs/pm2-error.log`
  - `logs/pm2-combined.log`

## 로그 레벨별 확인

### INFO 레벨 이상
```bash
tail -f logs/app.log | grep -E "(INFO|WARNING|ERROR)"
```

### ERROR만
```bash
tail -f logs/app.log | grep ERROR
```

## 로그 정리

### 로그 파일 크기 확인
```bash
du -h logs/app.log
```

### 로그 파일 비우기 (주의!)
```bash
# 로그 파일 내용 삭제 (파일은 유지)
> logs/app.log
```

## 실시간 모니터링

### 여러 로그 동시 보기
```bash
# 여러 로그 파일 동시 모니터링
tail -f logs/app.log logs/backtest.log
```

### 로그 + 시스템 리소스
```bash
# 로그와 함께 CPU/메모리 확인
watch -n 1 'tail -n 20 logs/app.log && echo "---" && ps aux | grep python3'
```

## 웹훅 테스트 시 로그 확인

웹훅이 들어오는지 확인:
```bash
tail -f logs/app.log | grep -i "webhook\|tradingview"
```

## 문제 해결

### 로그가 안 보이는 경우
```bash
# 로그 파일이 있는지 확인
ls -lh logs/

# 로그 디렉토리 생성
mkdir -p logs

# 권한 확인
ls -la logs/app.log
```

### 프로세스가 죽었는지 확인
```bash
# 프로세스 확인
ps aux | grep python3

# 프로세스가 없으면 다시 시작
cd ~/100k
nohup python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook > logs/app.log 2>&1 &
```

## 유용한 명령어 모음

```bash
# 실시간 로그 + 프로세스 상태
watch -n 2 'echo "=== 로그 (마지막 10줄) ===" && tail -n 10 logs/app.log && echo "" && echo "=== 프로세스 ===" && ps aux | grep "main.py" | grep -v grep'

# 로그에서 웹훅 수신 확인
grep "웹훅 수신" logs/app.log

# 최근 에러 확인
grep -i error logs/app.log | tail -20
```

