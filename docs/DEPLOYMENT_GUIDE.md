# 🚀 デプロイメント・運用ガイド

## 📋 概要

このドキュメントは、crypto-botのデプロイメント、運用、GitHub管理に関する包括的なガイドです。

## 🏗️ インフラ構成

### Cloud Run (推奨)
- **メリット**: サーバーレス、自動スケーリング、簡単なデプロイ
- **現在の運用**: 本番環境で稼働中
- **URL**: https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app

### Kubernetes移行 (オプション)
**メリット:**
- より細かいリソース制御
- 高度なスケーリング (HPA/VPA)
- マルチクラウド対応 (GKE/EKS)
- 豊富な監視ツール (Prometheus、Grafana)

**デメリット:**
- 複雑性の増加
- 運用コストの増加
- 学習コストの増加

## 🏦 本番取引所運用

### サポート取引所

| 取引所 | テストネット | 現物取引 | 先物取引 | 実装状況 |
|--------|-------------|---------|---------|----------|
| **Bybit** | ✅ | ✅ | ✅ | 完全実装 |
| **Bitbank** | ❌ | ✅ | ❌ | 本番実装済み |
| **BitFlyer** | ❌ | ✅ | ✅ (Lightning FX) | 本番実装済み |
| **OKCoinJP** | ❌ | ✅ | ❌ | 本番実装済み |

### 事前準備

#### 1. APIキーの取得
各取引所でAPIキーを取得し、適切な権限を設定してください。

#### 2. 環境変数設定
```bash
# Bitbank
export BITBANK_API_KEY="your_api_key"
export BITBANK_API_SECRET="your_api_secret"

# Bybit
export BYBIT_API_KEY="your_api_key"
export BYBIT_API_SECRET="your_api_secret"
```

#### 3. 段階的テスト手順
1. **Bybit Testnet**: リスクなしでシステム検証
2. **最小額テスト**: 1万円程度での実証
3. **本格運用**: 50万円規模での運用開始

## 📊 GitHub管理・品質保証

### ブランチ保護ルール

#### 自動設定項目
- mainブランチへの直接プッシュ禁止
- Pull Requestでのコードレビュー必須
- 自動テストの合格必須
- コード品質チェック強制

#### 設定手順
1. GitHub リポジトリの Settings → Branches
2. "Add rule" をクリック
3. Branch name pattern: `main`
4. 以下のオプションを有効化：
   - Require a pull request before merging
   - Require status checks to pass before merging
   - Require branches to be up to date before merging
   - Include administrators

### Pull Requestテンプレート
包括的なPRテンプレートを`.github/PULL_REQUEST_TEMPLATE/default.md`に配置済み。

## 🔧 運用監視

### ヘルスチェック
```bash
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health
```

### ログ監視
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-prod" --limit=20
```

### パフォーマンス監視
- Cloud Monitoring統合
- BigQuery ログ分析
- 自動アラート設定

## 🎯 101特徴量システム

### 現在の構成
- **VIX統合**: 恐怖指数による市場環境判定
- **DXY統合**: ドル指数・マクロ経済環境分析
- **Fear&Greed統合**: 市場心理分析
- **Funding Rate統合**: 資金フロー分析
- **テクニカル指標**: 30+ の高度な指標

### 品質保証
- **テストカバレッジ**: 52% (556テスト成功)
- **CI/CD**: 完全自動化
- **コード品質**: flake8/black/isort完全準拠

---

**🤖 Generated with [Claude Code](https://claude.ai/code)**