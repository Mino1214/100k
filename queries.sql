-- ============================================
-- 실시간 거래 현황 조회 쿼리
-- ============================================

-- 1. 최신 백테스트 결과 (최근 10개)
SELECT 
    session_id,
    run_date,
    symbol,
    timeframe,
    strategy_name,
    initial_capital,
    final_equity,
    total_return * 100 AS total_return_pct,
    sharpe_ratio,
    win_rate * 100 AS win_rate_pct,
    total_trades,
    max_drawdown * 100 AS max_drawdown_pct,
    profit_factor
FROM myno_backtest_results
ORDER BY run_date DESC
LIMIT 10;

-- 2. 오늘 실행된 백테스트 결과
SELECT 
    session_id,
    run_date,
    symbol,
    total_return * 100 AS total_return_pct,
    sharpe_ratio,
    win_rate * 100 AS win_rate_pct,
    total_trades
FROM myno_backtest_results
WHERE DATE(run_date) = CURDATE()
ORDER BY run_date DESC;

-- 3. 최신 거래 기록 (최근 20개)
SELECT 
    t.session_id,
    t.entry_time,
    t.exit_time,
    t.direction,
    t.entry_price,
    t.exit_price,
    t.quantity,
    t.pnl,
    t.return_pct * 100 AS return_pct,
    t.duration_bars,
    b.symbol,
    b.strategy_name
FROM myno_trade_details t
LEFT JOIN myno_backtest_results b ON t.session_id = b.session_id
ORDER BY t.entry_time DESC
LIMIT 20;

-- 4. 오늘의 거래 기록
SELECT 
    t.session_id,
    t.entry_time,
    t.exit_time,
    t.direction,
    t.entry_price,
    t.exit_price,
    t.pnl,
    t.return_pct * 100 AS return_pct,
    TIMESTAMPDIFF(MINUTE, t.entry_time, t.exit_time) AS duration_minutes
FROM myno_trade_details t
WHERE DATE(t.entry_time) = CURDATE()
ORDER BY t.entry_time DESC;

-- 5. 현재 열려있는 포지션 (exit_time이 NULL인 거래)
SELECT 
    t.session_id,
    t.entry_time,
    t.direction,
    t.entry_price,
    t.quantity,
    TIMESTAMPDIFF(MINUTE, t.entry_time, NOW()) AS duration_minutes,
    b.symbol,
    b.strategy_name
FROM myno_trade_details t
LEFT JOIN myno_backtest_results b ON t.session_id = b.session_id
WHERE t.exit_time IS NULL
ORDER BY t.entry_time DESC;

-- 6. 일별 거래 통계
SELECT 
    DATE(entry_time) AS trade_date,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN direction = 'long' THEN 1 ELSE 0 END) AS long_trades,
    SUM(CASE WHEN direction = 'short' THEN 1 ELSE 0 END) AS short_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS winning_trades,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) AS losing_trades,
    SUM(pnl) AS total_pnl,
    AVG(pnl) AS avg_pnl,
    AVG(return_pct) * 100 AS avg_return_pct
FROM myno_trade_details
WHERE exit_time IS NOT NULL
GROUP BY DATE(entry_time)
ORDER BY trade_date DESC
LIMIT 30;

-- 7. 전략별 성과 비교
SELECT 
    strategy_name,
    COUNT(DISTINCT session_id) AS session_count,
    AVG(total_return) * 100 AS avg_total_return_pct,
    AVG(sharpe_ratio) AS avg_sharpe_ratio,
    AVG(win_rate) * 100 AS avg_win_rate_pct,
    SUM(total_trades) AS total_trades,
    AVG(profit_factor) AS avg_profit_factor
FROM myno_backtest_results
GROUP BY strategy_name
ORDER BY avg_total_return_pct DESC;

-- 8. 최근 자기반성 일지
SELECT 
    session_id,
    performance_rating,
    emotional_state,
    strengths,
    weaknesses,
    lessons_learned,
    improvements,
    next_actions,
    reflection_date,
    created_at
FROM myno_reflection_logs
ORDER BY reflection_date DESC, created_at DESC
LIMIT 5;

-- 9. 최고 성과 세션 (Sharpe 비율 기준)
SELECT 
    session_id,
    run_date,
    symbol,
    strategy_name,
    total_return * 100 AS total_return_pct,
    sharpe_ratio,
    win_rate * 100 AS win_rate_pct,
    total_trades,
    profit_factor
FROM myno_backtest_results
WHERE sharpe_ratio IS NOT NULL
ORDER BY sharpe_ratio DESC
LIMIT 10;

-- 10. 최근 1시간 내 거래
SELECT 
    t.session_id,
    t.entry_time,
    t.exit_time,
    t.direction,
    t.entry_price,
    t.exit_price,
    t.pnl,
    t.return_pct * 100 AS return_pct,
    b.symbol
FROM myno_trade_details t
LEFT JOIN myno_backtest_results b ON t.session_id = b.session_id
WHERE t.entry_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
ORDER BY t.entry_time DESC;

-- 11. 실시간 포지션 현황 (포지션이 있는 경우)
SELECT 
    t.id,
    t.session_id,
    t.entry_time,
    t.direction,
    t.entry_price,
    t.quantity,
    TIMESTAMPDIFF(MINUTE, t.entry_time, NOW()) AS holding_minutes,
    b.symbol,
    b.strategy_name,
    (SELECT close FROM ETHUSDT1m ORDER BY timestamp DESC LIMIT 1) AS current_price
FROM myno_trade_details t
LEFT JOIN myno_backtest_results b ON t.session_id = b.session_id
WHERE t.exit_time IS NULL
ORDER BY t.entry_time DESC;

-- 12. 시간대별 거래 통계 (최근 24시간)
SELECT 
    DATE_FORMAT(entry_time, '%Y-%m-%d %H:00') AS hour,
    COUNT(*) AS trade_count,
    SUM(pnl) AS total_pnl,
    AVG(pnl) AS avg_pnl,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) AS losses
FROM myno_trade_details
WHERE entry_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
  AND exit_time IS NOT NULL
GROUP BY DATE_FORMAT(entry_time, '%Y-%m-%d %H:00')
ORDER BY hour DESC;

