// PM2 설정 파일 예시
// 서버 경로에 맞게 cwd를 수정하세요

module.exports = {
  apps: [
    {
      name: 'tradingview-webhook',
      script: 'python3',
      args: 'main.py dashboard --host 0.0.0.0 --port 5000 --webhook',
      cwd: '/home/mino/100k',  // 실제 프로젝트 경로로 변경하세요
      interpreter: 'python3',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
      },
      error_file: './logs/pm2-error.log',
      out_file: './logs/pm2-out.log',
      log_file: './logs/pm2-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
    },
  ],
};

