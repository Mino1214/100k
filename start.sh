#!/bin/bash
# PM2 대신 사용할 수 있는 시작 스크립트

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

# Python 경로 확인
PYTHON_CMD=$(which python3)
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ python3를 찾을 수 없습니다."
    exit 1
fi

echo "✅ Python 경로: $PYTHON_CMD"
echo "✅ 프로젝트 경로: $SCRIPT_DIR"
echo "🚀 TradingView 웹훅 서버 시작 (자동 가상매매 활성화)..."

# 백그라운드 실행 (--webhook과 --auto-live-trader 옵션 추가)
nohup $PYTHON_CMD main.py dashboard --host 0.0.0.0 --port 5000 --webhook --auto-live-trader > logs/app.log 2>&1 &

echo "✅ 서버가 백그라운드에서 실행 중입니다."
echo "✅ 자동 가상매매 모드 활성화됨"
echo "📋 로그 확인: tail -f logs/app.log"
echo "🛑 종료: pkill -f 'main.py dashboard'"

