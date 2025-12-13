# GitHub Actions Workflows

## 🎯 役割

このディレクトリには、AI自動取引システムのCI/CD、ML自動再学習、緊急停止、リソース管理、レポート自動送信を実現する6つのワークフローが含まれています。

## 📂 ファイル構成

```
.github/workflows/
├── ci.yml               # CI/CDパイプライン（品質チェック・ビルド・デプロイ）
├── model-training.yml   # ML自動再学習（週次・55特徴量Strategy-Aware ML）
├── backtest.yml         # バックテスト実行（手動・Markdownレポート生成）
├── cleanup.yml          # GCPリソースクリーンアップ（月次・コスト最適化）
├── weekly_report.yml    # 週間レポート自動送信（Phase 48実装）
├── emergency-stop.yml   # 🚨 緊急停止（iPhoneワンタップ対応）
└── README.md            # このファイル
```

## 🔧 ワークフロー詳細

### **ci.yml - CI/CDパイプライン**

**役割**: メインのCI/CDパイプライン・品質保証・本番自動デプロイ

**実行条件**:
- `main` ブランチへのプッシュ（自動デプロイ）
- プルリクエスト作成時（品質チェック）
- 手動実行（`workflow_dispatch`）
- ML学習完了時（`model-updated`イベント）

**実行フロー**:
1. **品質チェック**: テスト実行・カバレッジ・コード品質確認
2. **GCP環境確認**: Secret Manager・Workload Identity・必要リソース確認
3. **Dockerビルド**: イメージ構築とArtifact Registryプッシュ
4. **Docker起動テスト**: モジュールimport検証
5. **本番デプロイ**: Cloud Runサービスデプロイ（MODE=live）
6. **ヘルスチェック**: デプロイ成功確認

---

### **model-training.yml - ML自動再学習**

**役割**: MLモデルの週次自動再学習とデプロイメント・55特徴量Strategy-Aware ML

**実行条件**:
- 毎週日曜日 18:00 JST（スケジュール実行）
- 手動実行（`workflow_dispatch`・パラメータ設定可能）

**パラメータ**:
- `n_trials`: Optuna最適化試行回数（50推奨・100高精度・30テスト用）
- `dry_run`: ドライラン実行フラグ（モデル保存なし）

**実行フロー**:
1. **環境セットアップ**: Python3.13・依存関係インストール
2. **データ収集**: 180日分の履歴データ取得
3. **ML学習実行**:
   ```bash
   --n-classes 3 --threshold 0.005 --optimize --n-trials 50 --verbose
   ```
4. **品質検証**: MIN_FEATURE_COUNT（50）以上確認
5. **バージョン管理**: 自動コミット・プッシュ
6. **デプロイトリガー**: `model-updated`イベント送信 → ci.yml自動実行

**実行時間**: 約4-8分（50-100 trials）・タイムアウト30分

---

### **backtest.yml - バックテスト実行**

**役割**: バックテスト実行とMarkdownレポート生成

**実行条件**:
- 手動実行のみ（`workflow_dispatch`）

**パラメータ**:
- `phase_name`: Phase名（例: 52.1）
- `backtest_days`: バックテスト日数（デフォルト: 180）

**実行フロー**:
1. **環境セットアップ**: Python3.13・依存関係インストール
2. **履歴データ収集**: 15分足・4時間足データ取得
3. **バックテスト実行**: main.py --mode backtest
4. **Markdownレポート生成**: docs/バックテスト記録/に保存
5. **Git自動コミット**: レポートをリポジトリにプッシュ

---

### **cleanup.yml - GCPリソースクリーンアップ**

**役割**: GCPリソースの自動削除とコスト最適化（月30%削減）

**実行条件**:
- 手動実行（`workflow_dispatch`・推奨）
- 毎月第1日曜日 JST 2:00 AM（スケジュール実行）

**パラメータ**:
- `cleanup_level`: クリーンアップレベル（safe/moderate/aggressive）

**クリーンアップレベル**:
- **Safe**: 古いDockerイメージ（最新5個保持）・Cloud Runリビジョン（最新3個保持）
- **Moderate**: Safe + Cloud Build履歴（30日以上）
- **Aggressive**: より積極的な大量削除（要注意）

**Phase 52.2改善**:
- SHA256ダイジェストベース削除（より確実）
- 環境変数によるマジックナンバー排除

---

### **weekly_report.yml - 週間レポート自動送信**

**役割**: 週間取引統計レポート（損益曲線グラフ付き）のDiscord自動送信

**実行条件**:
- 毎週月曜日 9:00 JST（スケジュール実行）
- 手動実行（`workflow_dispatch`）

**レポート内容**:
- 週間損益統計（勝率・取引回数・最大利益/損失）
- 損益曲線グラフ（matplotlib生成）
- Discord自動送信

**Phase 52.2改善**:
- Cloud Storage統合（gs://crypto-bot-trade-data/tax/trade_history.db）
- 環境変数化（BUCKET_NAME, DB_PATH）

---

### **🚨 emergency-stop.yml - 緊急停止**

**役割**: iPhoneからワンタップで実行可能な緊急停止/復旧

**実行条件**:
- 手動実行のみ（`workflow_dispatch`）

**アクション**:
- **stop**: トラフィック0%に設定（即時停止・リソース保持で復旧簡単）
- **resume**: トラフィック100%に設定（復旧）
- **status**: 現在の状態確認のみ

**使い方**:
1. iPhoneのGitHubアプリを開く
2. Actions → 🚨 Emergency Stop → Run workflow
3. アクションを選択して実行

---

## 📝 使用方法

### **完全自動化フロー**

```
🗓️  毎週日曜18:00 JST
    ↓
🤖 model-training.yml 自動実行
    ├── 180日分データ収集
    ├── ProductionEnsemble学習（LightGBM・XGBoost・RandomForest）
    ├── 55特徴量品質検証（MIN_FEATURE_COUNT: 50）
    └── Git自動コミット・model-updatedイベント送信
    ↓
🚀 ci.yml 自動トリガー
    ├── テスト・品質チェック
    ├── Docker Build・Artifact Registry プッシュ
    └── Cloud Run本番デプロイ（MODE=live）
    ↓
✅ 週次完全自動モデル更新完了

🗓️  毎週月曜9:00 JST
    ↓
📊 weekly_report.yml 自動実行
    └── 週間レポート（損益統計・グラフ）Discord送信

🗓️  毎月第1日曜2:00 JST
    ↓
🧹 cleanup.yml 自動実行（safeモード）
    └── 古いリソース削除・コスト30%削減
```

### **手動実行方法**

```bash
# GitHub CLI使用
gh workflow run ci.yml                                    # CI/CDパイプライン
gh workflow run model-training.yml                        # MLモデル学習（50 trials）
gh workflow run backtest.yml -f phase_name=52.2           # バックテスト実行
gh workflow run cleanup.yml -f cleanup_level=safe         # リソースクリーンアップ
gh workflow run weekly_report.yml                         # 週間レポート即座送信
gh workflow run emergency-stop.yml -f action=status       # 状態確認

# パラメータ付き実行
gh workflow run model-training.yml -f n_trials=100        # 高精度学習（100 trials）
gh workflow run model-training.yml -f dry_run=true        # ドライラン（モデル保存なし）
gh workflow run cleanup.yml -f cleanup_level=moderate     # 中程度クリーンアップ
gh workflow run emergency-stop.yml -f action=stop         # 緊急停止
gh workflow run emergency-stop.yml -f action=resume       # 復旧
```

### **実行状況確認**

```bash
# 実行履歴確認
gh run list --workflow=ci.yml --limit 5
gh run list --workflow=model-training.yml --limit 5
gh run list --workflow=backtest.yml --limit 5
gh run list --workflow=cleanup.yml --limit 5

# 詳細ログ確認
gh run view [RUN_ID] --log

# 最新実行確認
gh run list --limit 1
```

---

## ⚠️ 重要な設定・制約

### **実行制約**
- **同時実行制限**: mainブランチでは順次実行（競合回避）
- **実行時間制限**: CI/CD 30分・ML学習 30分・クリーンアップ 20分・週間レポート 15分
- **Python版**: 3.13（全ワークフロー統一）
- **実行制限**: mainブランチでの実行に制限（安全性確保）

### **環境変数（Phase 52.2追加）**
- **MIN_FEATURE_COUNT**: 50（model-training.yml）
- **IMAGE_RETENTION_COUNT**: 5（cleanup.yml）
- **REVISION_RETENTION_COUNT**: 3（cleanup.yml）
- **BUCKET_NAME**: crypto-bot-trade-data（weekly_report.yml）

### **GCP認証・権限**
- **Workload Identity**: `projects/11445303925/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- **Service Account**: `github-deployer@my-crypto-bot-project.iam.gserviceaccount.com`
- **Secret Manager**: 具体的バージョン必須
  - `bitbank-api-key:3`
  - `bitbank-api-secret:3`
  - `discord-webhook-url:6`

---

## 🔧 更新履歴

### **2025-12-13: Phase 52.2整理**

**更新内容**:
- 全ワークフローのPhase参照更新
- emergency-stop.yml追加（緊急停止/復旧）
- 環境変数によるマジックナンバー排除
- cleanup.yml: SHA256ダイジェストベース削除
- model-training.yml: データ収集ステップ追加
- weekly_report.yml: Cloud Storage統合
- 55特徴量システム対応

---

**Phase 52.2完了**: 55特徴量Strategy-Aware ML・Python 3.13統一・緊急停止機能追加により、堅牢なCI/CD基盤が整備されています。
