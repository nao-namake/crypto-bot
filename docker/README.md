# Docker Directory

このディレクトリは、crypto-bot プロジェクトのDocker関連ファイルを統合管理するためのフォルダです。

**📊 Phase 12.5 Docker統合完了**: 全Docker関連ファイル統合・Environment Parity強化・CI/CD最適化・プロジェクト整理完成

## 📁 ディレクトリ構造

### 🐳 **Docker コアファイル**
- **`Dockerfile`**: 本番用軽量コンテナ定義・Phase 18 cache/ディレクトリ対応
- **`docker-entrypoint.sh`**: Phase H.28統合エントリポイント・ライブトレード+APIサーバー統合制御
- **注**: `.dockerignore`はプロジェクトルートに移動（Phase 18修正）

### 🛠️ **Docker 運用スクリプト**
- **`build_docker.sh`**: Dockerイメージビルド自動化・crypto-bot:latest生成
- **`run_docker.sh`**: Dockerコンテナ実行ラッパー・.env環境変数対応・汎用実行
- **`test_docker_local.sh`**: ローカルDocker環境テスト・ビルド検証・ヘルスチェック

## 🎯 **Phase 12.5 Environment Parity & Dependency Management System統合**

### **統一Docker環境管理の実現**
```
Local Development:
├── docker/Dockerfile (開発・テスト用ビルド)
├── requirements/base.txt (本番最小依存関係)
└── docker-entrypoint.sh (統合制御)

CI/CD Environment:
├── .github/workflows/ci.yml (Dockerビルド・テスト自動化)
├── Artifact Registry推送 (asia-northeast1-docker.pkg.dev)
└── Production環境検証 (import テスト・ヘルスチェック)

Production Environment:
├── GCP Cloud Run (本番稼働環境)
├── docker-entrypoint.sh (ライブトレード+APIサーバー統合)
└── 24時間安定稼働 (プロセス監視・シグナルハンドリング)
```

### **🆕 Docker環境統一効果**
- **Environment Parity完全達成**: Local ≈ CI ≈ Production環境統一・依存関係一貫性100%保証
- **Container Import Failed解決**: .dockerignore最適化・軽量ビルドコンテキスト・GCP Cloud Run安定デプロイ
- **CI/CD最適化**: Docker操作集約・ビルド時間短縮・自動テスト強化・品質保証統合

## 🚀 **使用方法**

### **基本Docker操作**
```bash
# プロジェクトルートから実行（重要）
cd /Users/nao/Desktop/bot

# Dockerイメージビルド
bash docker/build_docker.sh
# 実行: docker build -f docker/Dockerfile -t crypto-bot:latest .

# Dockerコンテナでコマンド実行
bash docker/run_docker.sh backtest --config config/production/production.yml

# ローカルDocker環境テスト
bash docker/test_docker_local.sh
```

### **CI/CD統合デプロイ**
```bash
# 本番デプロイ（GitHub Actions自動実行）
git push origin main
# → Docker build → Artifact Registry → GCP Cloud Run

# 手動本番デプロイ
gcloud run deploy crypto-bot-service-prod \
    --source . \
    --dockerfile docker/Dockerfile \
    --region=asia-northeast1
```

### **Production環境確認**
```bash
# 本番稼働確認
curl https://crypto-bot-service-prod-lufv3saz7q-an.a.run.app/health
# 期待: {"status":"healthy","mode":"live","margin_mode":true}

# ライブトレード+APIサーバー統合動作確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"Phase H.28\"" --limit=3
```

## 🔧 **技術仕様**

### **Dockerfile設計（Phase 12.5対応）**
```dockerfile
# 軽量Python 3.11ベース
FROM python:3.11-slim-bullseye

# Phase 12.5: 本番最小依存関係（単一真実源）
COPY requirements/base.txt /app/requirements.txt

# アプリケーション最小限コピー
COPY crypto_bot/ /app/crypto_bot/
COPY config/production/ /app/config/production/
COPY models/production/ /app/models/production/
COPY docker/docker-entrypoint.sh /app/

# Phase H.28統合エントリポイント
CMD ["/app/docker-entrypoint.sh"]
```

### **docker-entrypoint.sh統合制御**
```bash
# 本番環境（MODE=live）
if [ "$MODE" = "live" ] && [ "$CI" != "true" ]; then
    # APIサーバーバックグラウンド起動
    python -m crypto_bot.api.server &
    # ライブトレードフォアグラウンド実行
    python -m crypto_bot.main live-bitbank --config config/production/production.yml &
    # プロセス監視・シグナルハンドリング
fi

# CI/テスト環境
elif [ "$CI" = "true" ] || [ "$API_ONLY_MODE" = "true" ]; then
    # API-onlyモード
    exec python -m crypto_bot.api.server
fi
```

### **.dockerignore超軽量化設計**
```
# 開発・テスト完全除外
tests/
scripts/
docs/
*.md

# 本番以外設定除外
config/validation/
config/development/
!config/production/

# 軽量ビルドコンテキスト実現
archive/
data/
results/
```

## 🎯 **Phase 12.5包括的実装効果**

### **Environment Parity完全達成**
- **統一依存関係管理**: requirements/base.txt単一真実源・手動管理脱却
- **Local ≈ CI ≈ Production**: 100%環境統一・デプロイ品質向上・問題早期発見

### **Docker最適化・CI/CD強化**
- **Container Import Failed解決**: 超軽量ビルドコンテキスト・GCP Cloud Run安定デプロイ
- **ビルド効率向上**: Docker操作集約・処理時間短縮・Artifact Registry最適化
- **自動テスト強化**: 本番Docker環境検証・import テスト・ヘルスチェック自動化

### **プロジェクト整理・保守性向上**
- **Docker関連ファイル統合**: 6ファイル集約・論理的グループ化・管理効率向上
- **設定変更影響範囲明確化**: Docker関連変更の局所化・メンテナンス効率向上
- **Phase 12.5アーカイブ統合延長**: 整理方針一貫性・プロジェクト全体最適化

## ⚠️ **重要な運用指針**

### **パス指定の重要性**
```bash
# ✅ 正しい実行方法（プロジェクトルートから）
cd /Users/nao/Desktop/bot
docker build -f docker/Dockerfile -t crypto-bot:latest .

# ❌ 間違った実行方法
cd /Users/nao/Desktop/bot/docker
docker build -t crypto-bot:latest .  # ビルドコンテキストエラー
```

### **CI/CD自動調整済み**
- **.github/workflows/ci.yml**: 自動的に`docker/Dockerfile`パス使用
- **GCP Cloud Run**: `--dockerfile docker/Dockerfile`指定でデプロイ
- **依存関係検証**: Phase 12.5環境パリティ検証自動実行

## 📋 **更新履歴**

- **2025-08-09**: Phase 18 CI/CD修正・cache/ディレクトリ対応
  - CI環境でのcache/ディレクトリ自動作成対応
  - .dockerignoreプロジェクトルート移動（docker/から移動）
  - Dockerfile改善：cache/ディレクトリ適切な処理
  - CI/CDワークフロー更新：Docker build前のキャッシュ準備

- **2025-08-06**: Docker統合ディレクトリ構築・Phase 12.5完全対応
  - 全Docker関連ファイル統合（6ファイル）・README.md新設
  - Environment Parity強化・CI/CD最適化・プロジェクト整理完成
  - Local ≈ CI ≈ Production統一環境実現・Container Import Failed解決継承

---

このディレクトリは、crypto-botプロジェクトのDocker環境統一管理と Phase 12.5 Environment Parity & Dependency Management System の中核を担う重要なコンポーネントです。