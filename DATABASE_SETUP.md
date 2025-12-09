# 데이터베이스 연결 설정

## 마리아DB 연결 정보

- **호스트**: 180.230.8.65
- **포트**: 3306 (기본값)
- **사용자**: root
- **비밀번호**: 1107
- **데이터베이스**: DEMO
- **테이블**: ETHUSDT1m

## 설정 완료

`config/settings.yaml` 파일에 다음 설정이 추가되었습니다:

```yaml
data:
  source: "database"
  symbol: "ETHUSDT"
  timeframe: "1m"
  
  database:
    connection_string: "mysql+pymysql://root:1107@180.230.8.65:3306/DEMO?charset=utf8mb4"
    table_name: "ETHUSDT1m"
    timestamp_column: "timestamp"
```

## 테이블 구조 요구사항

ETHUSDT1m 테이블은 다음 컬럼을 포함해야 합니다:

- `timestamp`: 타임스탬프 (DATETIME 또는 TIMESTAMP)
- `open`: 시가 (DECIMAL 또는 FLOAT)
- `high`: 고가 (DECIMAL 또는 FLOAT)
- `low`: 저가 (DECIMAL 또는 FLOAT)
- `close`: 종가 (DECIMAL 또는 FLOAT)
- `volume`: 거래량 (DECIMAL 또는 FLOAT)

## 사용 방법

백테스트를 실행하면 자동으로 데이터베이스에서 데이터를 로드합니다:

```bash
python main.py backtest --config config/settings.yaml
```

특정 기간의 데이터만 로드하려면:

```bash
python main.py backtest --config config/settings.yaml --start 2024-01-01 --end 2024-12-31
```

## 의존성 설치

데이터베이스 연결을 위해 pymysql이 필요합니다:

```bash
pip install pymysql
```

또는 requirements.txt를 사용:

```bash
pip install -r requirements.txt
```

