# 🚀 デプロイメント・運用統合ガイド

## 📋 概要

crypto-botのデプロイメント、運用、Cloud Run最適化に関する包括的なガイドです。Phase 16.11統合により、運用に必要な情報を一元化しています。

**統合日**: 2025年8月8日  
**統合元**: DEPLOYMENT_GUIDE.md + DEPLOYMENT_STRATEGY.md + cloud_run_optimization.md

## 🏗️ インフラ構成

### Cloud Run (現在の本番環境)
- **メリット**: サーバーレス、自動スケーリング、簡単なデプロイ
- **現在の運用**: 本番環境で稼働中
- **URL**: https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app

### Phase 14.5最適化済み設定

```yaml
# 現在の本番Cloud Run設定
service:
  name: crypto-bot-service-prod
  region: asia-northeast1  # 東京リージョン
  
  # Phase 14.5最適化: 外部API除去後の効率設定
  resources:
    cpu: "1000m"          # 1 CPU（外部API除去により削減）
    memory: "1.5Gi"       # 1.5GB（97特徴量システム最適化）
    
  # タイムアウト設定
  timeout: 3600s          # 60分（取引システム対応）
  
  # 同時実行数
  concurrency: 80         # Phase 14最適化値
  
  # スケーリング設定
  scaling:
    min_instances: 1      # 最小1インスタンス（取引継続）
    max_instances: 5      # 最大5インスタンス
```

## 🚀 推奨デプロイメント手順

### 1. 事前準備

#### APIキーの設定
```bash
# Bitbank API設定（本番運用中）
export BITBANK_API_KEY="your_api_key"
export BITBANK_API_SECRET="your_api_secret"

# Phase 14.5: 外部API設定は不要（完全除去済み）
# ❌ 以下は不要: VIX_API_KEY, POLYGON_API_KEY, FRED_API_KEY
```

#### GCP Secret Managerによるセキュア管理
```bash
# 推奨: Secret Manager使用
gcloud secrets create bitbank-api-key --data-file=-
gcloud secrets create bitbank-api-secret --data-file=-
```

### 2. 初回起動（軽量モード）

```bash
# Phase 16対応: 次世代モジュラーアーキテクチャ
export MODE=live
export EXCHANGE=bitbank
export LOG_LEVEL=INFO
```

### 3. 初期化状況確認

```bash
# ヘルスチェックで基本状態確認
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health

# 期待レスポンス
{
  "status": "healthy",
  "mode": "live",
  "margin_mode": true,
  "phase": "Phase 16 - Next Generation Architecture",
  "features": "97 Features System"
}
```

### 4. 本番デプロイ

```bash
# Phase 16.11対応デプロイ
gcloud run deploy crypto-bot-service-prod \
    --source . \
    --region=asia-northeast1 \
    --platform=managed \
    --port=8080 \
    --memory=1.5Gi \
    --cpu=1 \
    --max-instances=5 \
    --min-instances=1 \
    --concurrency=80 \
    --timeout=3600 \
    --allow-unauthenticated \
    --set-env-vars="MODE=live,EXCHANGE=bitbank,LOG_LEVEL=INFO" \
    --set-secrets="BITBANK_API_KEY=bitbank-api-key:latest,BITBANK_API_SECRET=bitbank-api-secret:latest"
```

## 📊 監視・運用

### 基本監視

```bash
# 継続的な稼働状況監視
watch -n 30 'curl -s https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health | jq .'

# ログ監視（Cloud Logging）
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"TRADE\"" --limit=10

# Phase 16.4エラー監視
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=5
```

### パフォーマンス監視

```bash
# 97特徴量システム動作確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"97\"" --limit=10

# アンサンブル学習動作確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"TradingEnsemble\"" --limit=5
```

## 🏦 取引所対応状況

### サポート取引所（Phase 16.11現在）

| 取引所 | テストネット | 現物取引 | 信用取引 | 実装状況 |
|--------|-------------|---------|---------|----------|
| **Bitbank** | ❌ | ✅ | ✅ | 本番稼働中 |
| **Bybit** | ✅ | ✅ | ✅ | 実装完了・テスト済み |
| **BitFlyer** | ❌ | ✅ | ✅ (Lightning FX) | 実装済み |
| **OKCoinJP** | ❌ | ✅ | ❌ | 実装済み |

### 現在の本番運用

**Bitbank BTC/JPY**:
- Phase 16 次世代モジュラーアーキテクチャ稼働中
- 97特徴量システム完全実装
- TradingEnsembleClassifier（LGBM + XGBoost + RandomForest）

## ⚠️ トラブルシューティング

### よくある問題と対処法

#### 1. 初期化タイムアウト
```bash
# Phase 12.2修正: INIT問題解決済み
# メインループ到達確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"INIT-9\"" --limit=3
```

#### 2. 予測エラー
```bash
# アンサンブルモデル状態確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"ensemble\"" --limit=5
```

#### 3. API制限エラー
```bash
# Bitbank API制限状況確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"rate_limit\"" --limit=3
```

## 📈 最適化設定詳細

### CPU・メモリ最適化（Phase 14.5対応）

```yaml
# 外部API除去後の効率化設定
resources:
  cpu: "1000m"     # 1 CPU（25%削減効果）
  memory: "1.5Gi"  # 1.5GB（25%削減効果）
  
# 月額コスト削減効果
cost_reduction:
  before: "¥3,640/月"
  after: "¥1,820/月"  
  savings: "50%削減達成"
```

### ネットワーク設定

```yaml
# Phase 16対応ネットワーク設定
network:
  # 外部API不要（Phase 3完全除去済み）
  egress: "private-ranges-only"  # セキュリティ向上
  
  # 必要な接続のみ
  allowed_destinations:
    - "api.bitbank.cc"        # Bitbank API
    - "public.bitbank.cc"     # Bitbank Public API
```

### 環境変数最適化

```bash
# Phase 16.11推奨環境変数
export MODE=live                    # 本番モード
export EXCHANGE=bitbank             # Bitbank使用
export LOG_LEVEL=INFO              # 適切なログレベル
export FEATURE_MODE=full           # 97特徴量フル活用

# Phase 14.5: 不要な外部API設定削除
# ❌ VIX_API_KEY, POLYGON_API_KEY, FRED_API_KEY は設定不要
```

## 🔄 継続的改善

### 定期メンテナンス

1. **週次**:
   - パフォーマンス監視・統計レビュー
   - エラーログ分析・対策実施

2. **月次**:
   - リソース使用量最適化
   - 新機能テスト・段階的導入

3. **四半期**:
   - システム大幅アップデート
   - スケールアップ・拡張計画実行

### バックアップ・復旧

```bash
# 設定バックアップ
gcloud run services describe crypto-bot-service-prod \
    --region=asia-northeast1 \
    --format="export" > backup-$(date +%Y%m%d).yaml

# 緊急時復旧
gcloud run services replace backup-YYYYMMDD.yaml \
    --region=asia-northeast1
```

---

**Phase 16.11統合完了**: デプロイメント・運用に必要な全情報を一元化し、最新のPhase 16システムに対応した実践的ガイドが完成しました。🎊