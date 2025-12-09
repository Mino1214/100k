// PM2 설정 파일
module.exports = {
  apps: [
    {
      name: 'tradingview-webhook',
      script: 'main.py',
      args: 'dashboard --host 0.0.0.0 --port 5000 --webhook',
      cwd: process.env.HOME + '/100k',  // ~/100k 경로 자동 설정
      interpreter: '/usr/bin/python3',  // Python 전체 경로
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
    // 실시간 거래자 (선택적)
    {
      name: 'live-trader',
      script: 'main.py',
      args: 'live --auto-optimize --paper-trading',
      cwd: process.env.HOME + '/100k',
      interpreter: '/usr/bin/python3',  // Python 전체 경로
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
      },
      error_file: './logs/pm2-live-error.log',
      out_file: './logs/pm2-live-out.log',
      log_file: './logs/pm2-live-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
    },
  ],
};

