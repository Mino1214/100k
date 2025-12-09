"""웹 서버 모듈"""

from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
import threading
import time
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
CORS(app)  # CORS 활성화 (필요시)

# API 블루프린트는 나중에 등록 (순환 import 방지)
from .api import api_bp
app.register_blueprint(api_bp, url_prefix="/api")


@app.route("/")
def index():
    """메인 대시보드 페이지"""
    html_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>백테스트 실시간 모니터링</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .status-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running {
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        .status-stopped {
            background: #f44336;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .reflection-section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .reflection-item {
            margin: 15px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        .reflection-item h4 {
            color: #667eea;
            margin-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #667eea;
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .auto-refresh {
            float: right;
            margin-top: -40px;
        }
        .refresh-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4CAF50;
            margin-right: 5px;
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 백테스트 실시간 모니터링</h1>
            <div class="auto-refresh">
                <span class="refresh-indicator"></span>
                <span>자동 갱신 활성화</span>
            </div>
        </div>

        <!-- 상태 카드 -->
        <div class="status-card">
            <h2>
                <span class="status-indicator" id="statusIndicator"></span>
                <span id="statusText">대기 중</span>
            </h2>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar" style="width: 0%">
                    <span id="progressText">0%</span>
                </div>
            </div>
            <div id="statusMessage" style="margin-top: 10px; color: #666;"></div>
            <div id="timeInfo" style="margin-top: 10px; color: #666;"></div>
        </div>

        <!-- 통계 그리드 -->
        <div class="stats-grid" id="statsGrid">
            <div class="stat-box">
                <div class="stat-label">현재 바</div>
                <div class="stat-value" id="currentBar">0</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">전체 바</div>
                <div class="stat-value" id="totalBars">0</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">진행률</div>
                <div class="stat-value" id="progressPercent">0%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">예상 남은 시간</div>
                <div class="stat-value" id="eta">-</div>
            </div>
        </div>

        <!-- 차트 컨테이너 -->
        <div class="chart-container">
            <h2>실시간 진행 차트</h2>
            <div id="progressChart" style="height: 300px;"></div>
        </div>

        <!-- 최신 결과 테이블 -->
        <div class="status-card">
            <h2>최신 백테스트 결과</h2>
            <div id="resultsTable"></div>
        </div>

        <!-- 자기반성 일지 -->
        <div class="reflection-section">
            <h2>최신 자기반성 일지</h2>
            <div id="reflectionContent"></div>
        </div>
    </div>

    <script>
        let progressData = {
            x: [],
            y: []
        };

        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // 상태 업데이트
                    const indicator = document.getElementById('statusIndicator');
                    const statusText = document.getElementById('statusText');
                    const progressBar = document.getElementById('progressBar');
                    const progressText = document.getElementById('progressText');
                    const statusMessage = document.getElementById('statusMessage');
                    const timeInfo = document.getElementById('timeInfo');

                    if (data.running) {
                        indicator.className = 'status-indicator status-running';
                        statusText.textContent = '실행 중';
                    } else {
                        indicator.className = 'status-indicator status-stopped';
                        statusText.textContent = '대기 중';
                    }

                    const progress = data.progress || 0;
                    progressBar.style.width = progress + '%';
                    progressText.textContent = progress.toFixed(1) + '%';
                    
                    document.getElementById('currentBar').textContent = data.current_bar || 0;
                    document.getElementById('totalBars').textContent = data.total_bars || 0;
                    document.getElementById('progressPercent').textContent = progress.toFixed(1) + '%';
                    document.getElementById('eta').textContent = data.estimated_time_remaining || '-';

                    statusMessage.textContent = data.message || '';
                    
                    if (data.start_time) {
                        const elapsed = Math.floor((new Date() - new Date(data.start_time)) / 1000);
                        const minutes = Math.floor(elapsed / 60);
                        const seconds = elapsed % 60;
                        timeInfo.textContent = `경과 시간: ${minutes}분 ${seconds}초`;
                    }

                    // 진행 차트 업데이트
                    if (data.current_bar > 0) {
                        progressData.x.push(new Date());
                        progressData.y.push(progress);
                        
                        if (progressData.x.length > 100) {
                            progressData.x.shift();
                            progressData.y.shift();
                        }

                        Plotly.newPlot('progressChart', [{
                            x: progressData.x,
                            y: progressData.y,
                            type: 'scatter',
                            mode: 'lines',
                            name: '진행률',
                            line: { color: '#667eea', width: 2 }
                        }], {
                            title: '백테스트 진행률',
                            xaxis: { title: '시간' },
                            yaxis: { title: '진행률 (%)', range: [0, 100] },
                            margin: { l: 50, r: 50, t: 50, b: 50 }
                        });
                    }
                })
                .catch(error => console.error('Status update error:', error));
        }

        function updateResults() {
            fetch('/api/results/latest')
                .then(response => response.json())
                .then(data => {
                    if (data && data.length > 0) {
                        const latest = data[0];
                        const table = `
                            <table>
                                <thead>
                                    <tr>
                                        <th>세션 ID</th>
                                        <th>실행 일시</th>
                                        <th>심볼</th>
                                        <th>총 수익률</th>
                                        <th>Sharpe 비율</th>
                                        <th>승률</th>
                                        <th>총 거래 수</th>
                                        <th>성과 평가</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.slice(0, 10).map(result => `
                                        <tr>
                                            <td>${result.session_id}</td>
                                            <td>${new Date(result.run_date).toLocaleString('ko-KR')}</td>
                                            <td>${result.symbol}</td>
                                            <td style="color: ${result.total_return >= 0 ? 'green' : 'red'}">
                                                ${(result.total_return * 100).toFixed(2)}%
                                            </td>
                                            <td>${result.sharpe_ratio ? result.sharpe_ratio.toFixed(2) : '-'}</td>
                                            <td>${(result.win_rate * 100).toFixed(1)}%</td>
                                            <td>${result.total_trades}</td>
                                            <td>
                                                <a href="/api/reflection/${result.session_id}" target="_blank">
                                                    보기
                                                </a>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `;
                        document.getElementById('resultsTable').innerHTML = table;
                    }
                })
                .catch(error => console.error('Results update error:', error));
        }

        function updateReflection() {
            fetch('/api/reflection/latest')
                .then(response => response.json())
                .then(data => {
                    if (data) {
                        const content = `
                            <div class="reflection-item">
                                <h4>성과 평가: ${data.performance_rating}/10</h4>
                                <p><strong>감정 상태:</strong> ${data.emotional_state}</p>
                            </div>
                            <div class="reflection-item">
                                <h4>강점</h4>
                                <p>${data.strengths || '-'}</p>
                            </div>
                            <div class="reflection-item">
                                <h4>약점</h4>
                                <p>${data.weaknesses || '-'}</p>
                            </div>
                            <div class="reflection-item">
                                <h4>배운 점</h4>
                                <p>${data.lessons_learned || '-'}</p>
                            </div>
                            <div class="reflection-item">
                                <h4>개선 사항</h4>
                                <p>${data.improvements || '-'}</p>
                            </div>
                            <div class="reflection-item">
                                <h4>다음 행동 계획</h4>
                                <p>${data.next_actions || '-'}</p>
                            </div>
                            <div class="reflection-item">
                                <h4>메모</h4>
                                <p style="white-space: pre-wrap;">${data.notes || '-'}</p>
                            </div>
                        `;
                        document.getElementById('reflectionContent').innerHTML = content;
                    }
                })
                .catch(error => console.error('Reflection update error:', error));
        }

        // 초기 로드
        updateStatus();
        updateResults();
        updateReflection();

        // 자동 갱신 (2초마다)
        setInterval(() => {
            updateStatus();
        }, 2000);

        // 결과 및 일지 갱신 (10초마다)
        setInterval(() => {
            updateResults();
            updateReflection();
        }, 10000);
    </script>
</body>
</html>
    """
    return render_template_string(html_template)


def create_app():
    """Flask 앱 생성"""
    return app


def run_server(host="0.0.0.0", port=5000, debug=False):
    """웹 서버 실행"""
    logger.info(f"웹 서버 시작: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)

