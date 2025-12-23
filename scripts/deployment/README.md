# scripts/deployment/ - デプロイメント管理（Phase 55.9更新）

**最終更新**: 2025年12月23日

## 役割

本番環境（GCP Cloud Run）へのデプロイメント基盤を提供します。

## ファイル構成

```
scripts/deployment/
├── README.md              # このファイル
└── docker-entrypoint.sh   # Docker ENTRYPOINT（Cloud Run起動）
```

## docker-entrypoint.sh

Docker コンテナの起動制御とプロセス管理を担当。

**主要機能**:
| 機能 | 説明 |
|------|------|
| デュアルプロセス | ヘルスチェックサーバー + 取引システム並行実行 |
| MLモデル検証 | 起動時55特徴量モデル動作確認 |
| ヘルスチェックAPI | `/health` エンドポイント（ポート8080） |
| プロセス監視 | 異常終了検知・自動復旧 |
| Cloud Run最適化 | メモリ効率・起動時間短縮 |

**Dockerfile での使用**:
```dockerfile
COPY scripts/deployment/docker-entrypoint.sh /app/
ENTRYPOINT ["/app/docker-entrypoint.sh"]
```

## 使用方法

### 日常運用

```bash
# 品質チェック（デプロイ前必須）
bash scripts/testing/checks.sh

# 本番環境確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# ヘルスチェック
curl https://[SERVICE_URL]/health
```

### ローカルテスト

```bash
# Dockerビルド・実行
docker build -t crypto-bot .
docker run --env-file .env crypto-bot

# ヘルスチェック確認
curl http://localhost:8080/health
```

## デプロイフロー

```
GitHub push → ci.yml → Docker build → gcloud run deploy → Cloud Run
```

デプロイは `.github/workflows/ci.yml` で自動実行。手動デプロイスクリプトは不要。

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `Dockerfile` | コンテナイメージ定義 |
| `.github/workflows/ci.yml` | CI/CDパイプライン |
| `main.py` | アプリケーションエントリーポイント |
