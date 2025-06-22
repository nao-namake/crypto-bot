-- =============================================================================
-- BigQuery ログ分析クエリ集
-- Cloud Logging Sink により BigQuery に保存されたログを分析するためのクエリ
-- =============================================================================

-- ▼ 基本的なエラーログ抽出 ▼
-- 最新の ERROR レベル以上のログを取得
SELECT 
  timestamp,
  severity,
  textPayload,
  resource.labels.service_name,
  resource.labels.revision_name
FROM `my-crypto-bot-project.crypto_bot_logs.run_googleapis_com_stderr_*`
WHERE severity >= 'ERROR'
  AND DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY timestamp DESC
LIMIT 20;

-- ▼ 時系列エラー分析 ▼
-- 日別・時間別のエラー発生状況
SELECT 
  DATE(timestamp) as date,
  EXTRACT(HOUR FROM timestamp) as hour,
  severity,
  COUNT(*) as error_count
FROM `my-crypto-bot-project.crypto_bot_logs.run_googleapis_com_stderr_*`
WHERE severity >= 'WARNING'
  AND DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY date, hour, severity
ORDER BY date DESC, hour DESC;

-- ▼ アプリケーション起動・停止ログ ▼
-- Cloud Run のライフサイクルイベント
SELECT 
  timestamp,
  textPayload,
  resource.labels.revision_name
FROM `my-crypto-bot-project.crypto_bot_logs.run_googleapis_com_varlog_system_*`
WHERE textPayload LIKE '%Starting%' 
   OR textPayload LIKE '%Stopping%'
   OR textPayload LIKE '%Ready%'
ORDER BY timestamp DESC
LIMIT 50;

-- ▼ リクエストログ分析 ▼
-- HTTP リクエストの成功・失敗状況
SELECT 
  timestamp,
  httpRequest.requestMethod as method,
  httpRequest.requestUrl as url,
  httpRequest.status as status_code,
  httpRequest.responseSize as response_size,
  httpRequest.latency as latency
FROM `my-crypto-bot-project.crypto_bot_logs.run_googleapis_com_requests_*`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND httpRequest.status >= 400
ORDER BY timestamp DESC
LIMIT 100;

-- ▼ レイテンシ分析 ▼
-- P50, P95, P99 レイテンシの日別統計
WITH latency_stats AS (
  SELECT 
    DATE(timestamp) as date,
    EXTRACT(EPOCH FROM CAST(httpRequest.latency AS INTERVAL)) as latency_seconds
  FROM `my-crypto-bot-project.crypto_bot_logs.run_googleapis_com_requests_*`
  WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    AND httpRequest.latency IS NOT NULL
)
SELECT 
  date,
  COUNT(*) as request_count,
  ROUND(APPROX_QUANTILES(latency_seconds, 100)[OFFSET(50)], 3) as p50_latency,
  ROUND(APPROX_QUANTILES(latency_seconds, 100)[OFFSET(95)], 3) as p95_latency,
  ROUND(APPROX_QUANTILES(latency_seconds, 100)[OFFSET(99)], 3) as p99_latency,
  ROUND(AVG(latency_seconds), 3) as avg_latency
FROM latency_stats
GROUP BY date
ORDER BY date DESC;

-- ▼ 特定のエラーパターン検索 ▼
-- よくあるエラーを検索
SELECT 
  timestamp,
  severity,
  textPayload,
  CASE 
    WHEN textPayload LIKE '%ConnectionError%' THEN 'Connection Issue'
    WHEN textPayload LIKE '%timeout%' THEN 'Timeout'
    WHEN textPayload LIKE '%authentication%' THEN 'Auth Error'
    WHEN textPayload LIKE '%rate limit%' THEN 'Rate Limit'
    WHEN textPayload LIKE '%insufficient%' THEN 'Insufficient Balance'
    ELSE 'Other Error'
  END as error_category
FROM `my-crypto-bot-project.crypto_bot_logs.run_googleapis_com_stderr_*`
WHERE severity >= 'ERROR'
  AND DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND (
    textPayload LIKE '%ConnectionError%' OR
    textPayload LIKE '%timeout%' OR
    textPayload LIKE '%authentication%' OR
    textPayload LIKE '%rate limit%' OR
    textPayload LIKE '%insufficient%'
  )
ORDER BY timestamp DESC;

-- ▼ 長時間実行クエリ検知 ▼
-- 異常に長いレスポンス時間のリクエスト
SELECT 
  timestamp,
  httpRequest.requestMethod,
  httpRequest.requestUrl,
  httpRequest.status,
  httpRequest.latency,
  EXTRACT(EPOCH FROM CAST(httpRequest.latency AS INTERVAL)) as latency_seconds
FROM `my-crypto-bot-project.crypto_bot_logs.run_googleapis_com_requests_*`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND EXTRACT(EPOCH FROM CAST(httpRequest.latency AS INTERVAL)) > 5.0  -- 5秒以上
ORDER BY latency_seconds DESC
LIMIT 20;

-- ▼ ヘルスチェック除外したリクエスト分析 ▼
-- ヘルスチェックを除いた実際のアプリケーションリクエスト
SELECT 
  DATE(timestamp) as date,
  httpRequest.status,
  COUNT(*) as request_count,
  AVG(EXTRACT(EPOCH FROM CAST(httpRequest.latency AS INTERVAL))) as avg_latency
FROM `my-crypto-bot-project.crypto_bot_logs.run_googleapis_com_requests_*`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND httpRequest.requestUrl NOT LIKE '%/healthz%'
  AND httpRequest.requestUrl NOT LIKE '%/health%'
GROUP BY date, httpRequest.status
ORDER BY date DESC, httpRequest.status;

-- ▼ 監査ログ確認 ▼ 
-- 重要な設定変更やアクセス
SELECT 
  timestamp,
  protoPayload.methodName,
  protoPayload.authenticationInfo.principalEmail,
  protoPayload.resourceName,
  severity
FROM `my-crypto-bot-project.crypto_bot_logs.cloudaudit_googleapis_com_activity_*`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND protoPayload.resourceName LIKE '%crypto-bot%'
ORDER BY timestamp DESC
LIMIT 50;