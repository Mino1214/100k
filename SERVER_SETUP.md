# 서버 설정 가이드

## 1. 의존성 설치

### Python 패키지 설치
```bash
cd ~/100k

# pip3가 없으면 설치
sudo apt update
sudo apt install python3-pip -y

# 의존성 설치
pip3 install -r requirements.txt

# 또는 사용자 디렉토리에 설치 (sudo 권한 없이)
pip3 install --user -r requirements.txt
```

### 가상환경 사용 (권장)
```bash
cd ~/100k

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

## 2. 실행

### 가상환경 사용 시
```bash
cd ~/100k
source venv/bin/activate
nohup python main.py dashboard --host 0.0.0.0 --port 5000 --webhook > logs/app.log 2>&1 &
```

### 가상환경 없이
```bash
cd ~/100k
nohup python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook > logs/app.log 2>&1 &
```

## 3. PM2 사용 시 (가상환경)

`ecosystem.config.js` 수정:
```javascript
{
  name: 'tradingview-webhook',
  script: 'main.py',
  args: 'dashboard --host 0.0.0.0 --port 5000 --webhook',
  cwd: process.env.HOME + '/100k',
  interpreter: process.env.HOME + '/100k/venv/bin/python',  // 가상환경 Python
  // ...
}
```

## 4. 문제 해결

### pandas가 설치되지 않는 경우
```bash
# pip 업그레이드
pip3 install --upgrade pip

# 개별 설치
pip3 install pandas numpy
```

### 권한 문제
```bash
# 사용자 디렉토리에 설치
pip3 install --user -r requirements.txt

# 또는 sudo 사용 (권장하지 않음)
sudo pip3 install -r requirements.txt
```

### Python 버전 확인
```bash
python3 --version
# Python 3.8 이상 필요
```

## 5. 빠른 설치 스크립트

```bash
#!/bin/bash
cd ~/100k

echo "의존성 설치 중..."
pip3 install --user -r requirements.txt

echo "설치 완료!"
echo "이제 실행하세요:"
echo "  nohup python3 main.py dashboard --host 0.0.0.0 --port 5000 --webhook > logs/app.log 2>&1 &"
```

