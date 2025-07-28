# Cloud Run設定最適化ガイド

## 🎯 Phase H.19: 外部API安定化のための推奨設定

このドキュメントは、crypto-botをGoogle Cloud Runで安定稼働させるための設定ガイドです。

## 📋 目次

1. [問題の概要](#問題の概要)
2. [推奨Cloud Run設定](#推奨cloud-run設定)
3. [Terraform設定例](#terraform設定例)
4. [環境変数設定](#環境変数設定)
5. [ネットワーク設定](#ネットワーク設定)
6. [モニタリング設定](#モニタリング設定)
7. [トラブルシューティング](#トラブルシューティング)

## 問題の概要

Cloud Run環境で外部APIへの接続が失敗する主な原因：

- **タイムアウト**: デフォルト設定が短すぎる
- **メモリ不足**: yfinance/pandasによる高メモリ使用
- **ネットワーク制限**: 外部APIへのアクセス制限
- **DNS解決**: 名前解決の遅延や失敗

## 推奨Cloud Run設定

### 基本設定

```yaml
# Cloud Runサービス設定
service:
  name: crypto-bot-service-prod
  region: asia-northeast1  # 東京リージョン
  
  # リソース設定
  resources:
    cpu: "2"              # 2 vCPU（外部API処理用）
    memory: "4Gi"         # 4GB（pandas/yfinance対応）
    
  # タイムアウト設定
  timeout: 300s           # 5分（外部API対応）
  
  # 同時実行数
  concurrency: 1          # 1インスタンスあたり1リクエスト
  
  # スケーリング設定
  scaling:
    min_instances: 1      # 最小1インスタンス（コールドスタート回避）
    max_instances: 5      # 最大5インスタンス
```

### 実行環境設定

```yaml
# 実行環境
execution_environment:
  service_account: crypto-bot-sa@${PROJECT_ID}.iam.gserviceaccount.com
  platform: managed
  
  # CPU割り当て
  cpu_allocation: "always"  # 常時CPU割り当て（バックグラウンド処理用）
```

## Terraform設定例

### `terraform/cloud_run.tf`

```hcl
resource "google_cloud_run_service" "crypto_bot" {
  name     = "crypto-bot-service-prod"
  location = "asia-northeast1"
  
  template {
    spec {
      # コンテナ設定
      containers {
        image = "gcr.io/${var.project_id}/crypto-bot:latest"
        
        # リソース設定
        resources {
          limits = {
            cpu    = "2000m"      # 2 CPU
            memory = "4096Mi"     # 4GB
          }
          requests = {
            cpu    = "1000m"      # 最小1 CPU
            memory = "2048Mi"     # 最小2GB
          }
        }
        
        # 環境変数
        env {
          name  = "ENVIRONMENT"
          value = "production"
        }
        
        env {
          name  = "HTTP_TIMEOUT"
          value = "30"
        }
        
        env {
          name  = "GRACEFUL_DEGRADATION"
          value = "true"
        }
      }
      
      # サービスアカウント
      service_account_name = google_service_account.crypto_bot_sa.email
      
      # タイムアウト設定
      timeout_seconds = 300
      
      # 同時実行数
      container_concurrency = 1
    }
    
    # アノテーション
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"     = "1"
        "autoscaling.knative.dev/maxScale"     = "5"
        "run.googleapis.com/cpu-throttling"    = "false"  # CPU常時割り当て
        "run.googleapis.com/startup-cpu-boost" = "true"   # 起動時CPUブースト
      }
    }
  }
  
  # トラフィック設定
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# VPCコネクタ（必要に応じて）
resource "google_vpc_access_connector" "connector" {
  name          = "crypto-bot-connector"
  region        = "asia-northeast1"
  ip_cidr_range = "10.8.0.0/28"
  network       = "default"
  
  # スループット設定
  min_throughput = 200
  max_throughput = 1000
}
```

## 環境変数設定

### 必須環境変数

```bash
# Cloud Run環境識別
K_SERVICE=crypto-bot-service-prod
K_REVISION=crypto-bot-service-prod-00001-abc

# タイムアウト設定
HTTP_TIMEOUT=30
REQUEST_TIMEOUT=30

# キャッシュ設定
CACHE_DIR=/tmp
PYRESHARK_DNS_CACHE_TTL=3600

# 品質管理
GRACEFUL_DEGRADATION=true
PARTIAL_DATA_ACCEPTANCE=true
QUALITY_IMPROVEMENT_FACTOR=1.1

# ログレベル
LOG_LEVEL=INFO
```

### 最適化環境変数

```bash
# Python最適化
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# urllib3設定
URLLIB3_DISABLE_WARNINGS=1

# DNS最適化
GODEBUG=netdns=go  # Go DNSリゾルバ使用
```

## ネットワーク設定

### ファイアウォール規則

```yaml
# 外部API許可リスト
egress_rules:
  - name: allow-yahoo-finance
    destination: "*.yahoo.com"
    ports: [443]
    
  - name: allow-alternative-me
    destination: "api.alternative.me"
    ports: [443]
    
  - name: allow-binance
    destination: "*.binance.com"
    ports: [443]
```

### VPCコネクタ設定（オプション）

VPCコネクタを使用する場合の設定：

```yaml
vpc_connector:
  name: crypto-bot-connector
  egress: ALL_TRAFFIC  # 全トラフィックをVPC経由
```

## モニタリング設定

### Cloud Monitoring設定

```yaml
# アラートポリシー
alert_policies:
  - name: external-api-failure
    condition:
      metric: cloud_run/request_count
      filter: status_code=~"5.."
      threshold: 10
      duration: 300s
    
  - name: high-latency
    condition:
      metric: cloud_run/request_latencies
      percentile: 95
      threshold: 10000  # 10秒
      duration: 300s
```

### ログ設定

```yaml
# Cloud Logging設定
logging:
  severity_filter: "INFO"
  
  # 重要なログのフィルタ
  important_logs:
    - "External API failed"
    - "Quality degraded"
    - "Circuit breaker activated"
```

## トラブルシューティング

### 診断コマンド

```bash
# 1. API診断ツールの実行
python -m crypto_bot.main diagnose-apis

# 2. Cloud Runログの確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=WARNING" --limit=50

# 3. メトリクスの確認
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --interval-end-time=now \
  --interval-start-time=-1h
```

### よくある問題と対策

#### 1. タイムアウトエラー

**症状**: "Timeout" エラーが頻発

**対策**:
- Cloud Runのタイムアウトを300秒に延長
- HTTPクライアントのタイムアウトを30秒に設定
- リトライ戦略の実装

#### 2. メモリ不足

**症状**: "Memory limit exceeded" エラー

**対策**:
- メモリを4GBに増加
- データ処理の最適化
- 不要なデータの早期解放

#### 3. DNS解決エラー

**症状**: "Name resolution failed" エラー

**対策**:
- VPCコネクタの使用
- DNSキャッシュの有効化
- Google DNSの明示的指定

#### 4. 503エラー

**症状**: "Service Unavailable" エラー

**対策**:
- 最小インスタンス数を1に設定
- CPU常時割り当てを有効化
- ヘルスチェックの実装

## 推奨デプロイ手順

1. **設定の検証**
   ```bash
   terraform plan
   ```

2. **段階的デプロイ**
   ```bash
   # 10%トラフィックでテスト
   gcloud run deploy --traffic 10
   
   # 問題なければ100%へ
   gcloud run deploy --traffic 100
   ```

3. **監視**
   ```bash
   # リアルタイムログ監視
   gcloud logging tail "resource.type=cloud_run_revision"
   
   # メトリクス確認
   gcloud monitoring dashboards list
   ```

## セキュリティ考慮事項

- サービスアカウントの最小権限原則
- シークレットはSecret Managerで管理
- VPCコネクタ使用時はファイアウォール規則を適切に設定

## パフォーマンスチューニング

### 推奨設定値

- **CPU**: 2 vCPU（外部API並列処理用）
- **メモリ**: 4GB（データ処理余裕確保）
- **同時実行数**: 1（リソース競合回避）
- **最小インスタンス**: 1（コールドスタート回避）

### 最適化のポイント

1. HTTPコネクションプーリング
2. DNSキャッシュの活用
3. リトライ戦略の実装
4. グレースフルデグレードの有効化

---

最終更新: 2025年7月27日
Phase H.19実装に基づく