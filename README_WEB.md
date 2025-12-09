# 웹 대시보드 빠른 시작

## 실행 방법

### 1. 웹 대시보드 실행

```bash
python3 main.py dashboard --port 5000 --host 0.0.0.0
```

### 2. 브라우저에서 접속

- 로컬: http://localhost:5000
- 서버: http://서버IP:5000

## 주요 기능

1. **실시간 진행 상황**
   - 진행률 바
   - 현재 바 / 전체 바
   - 예상 남은 시간
   - 실시간 진행 차트

2. **최신 결과 조회**
   - 최근 20개 백테스트 결과
   - 세션별 상세 정보

3. **자기반성 일지**
   - 최신 일지 자동 표시
   - 성과 평가, 강점, 약점 등

## 서버 배포

### Gunicorn 사용 (권장)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web.server:app
```

### 백그라운드 실행

```bash
nohup python3 main.py dashboard --port 5000 --host 0.0.0.0 > dashboard.log 2>&1 &
```

## API 사용 예시

```bash
# 상태 조회
curl http://localhost:5000/api/status

# 최신 결과
curl http://localhost:5000/api/results/latest

# 특정 세션 결과
curl http://localhost:5000/api/results/20241209_181000_ETHUSDT
```

