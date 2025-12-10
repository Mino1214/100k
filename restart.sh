#!/bin/bash
# 서버 재시작 스크립트

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

echo "🛑 기존 서버 종료 중..."
pkill -f 'main.py dashboard'

# 잠시 대기
sleep 2

echo "🚀 서버 재시작 중..."
./start.sh

echo "✅ 서버 재시작 완료"
echo "📋 로그 확인: tail -f logs/app.log"

