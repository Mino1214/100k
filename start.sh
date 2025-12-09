#!/bin/bash
# PM2 대신 사용할 수 있는 시작 스크립트

cd ~/100k || exit 1

# Python 경로 확인
PYTHON_CMD=$(which python3)
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ python3를 찾을 수 없습니다."
    exit 1
fi

echo "✅ Python 경로: $PYTHON_CMD"
echo "🚀 TradingView 웹훅 서버 시작..."

# 백그라운드 실행
nohup $PYTHON_CMD main.py dashboard --host 0.0.0.0 --port 5000 --webhook > logs/app.log 2>&1 &

echo "✅ 서버가 백그라운드에서 실행 중입니다."
echo "📋 로그 확인: tail -f logs/app.log"
echo "🛑 종료: pkill -f 'main.py dashboard'"

