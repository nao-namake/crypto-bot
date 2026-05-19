# GitHub Actions Workflows

CI/CD・ML 自動再学習・バックテスト・Walk-Forward 検証・GCP リソース管理・緊急停止を担う **6 ワークフロー**。

## ファイル構成

```
.github/workflows/
├── ci.yml               # CI/CD パイプライン（品質チェック・ビルド・デプロイ）
├── model-training.yml   # ML 自動再学習（週次 + repository_dispatch・55 特徴量・4 モデル）
├── backtest.yml         # バックテスト実行（手動・Markdown レポート生成）
├── walk_forward.yml     # Walk-Forward 検証（過学習検出）
├── cleanup.yml          # GCP リソースクリーンアップ（月次・コスト最適化）
├── emergency-stop.yml   # 🚨 緊急停止（iPhone ワンタップ対応）
└── README.md            # このファイル
```

## ワークフロー詳細

### ci.yml - CI/CD パイプライン

**役割**: メインの CI/CD パイプライン・品質保証・本番自動デプロイ

**実行条件**:
- `main` ブランチへのプッシュ（自動デプロイ）
- プルリクエスト作成時（品質チェック）
- 手動実行（`workflow_dispatch`）
- ML 学習完了時（`model-updated` イベント）

**実行フロー**:
1. 品質チェック（テスト + カバレッジ + コード品質）
2. GCP 環境確認（Secret Manager + Workload Identity）
3. Docker ビルド + Artifact Registry プッシュ
4. Docker 起動テスト
5. Cloud Run 本番デプロイ（MODE=live）
6. ヘルスチェック

---

### model-training.yml - ML 自動再学習

**役割**: ML モデルの自動再学習とデプロイメント・**55 特徴量・4 モデル・メタラベリング**

**実行条件**:
- 毎週日曜日 18:00 JST（スケジュール）
- 手動実行（`workflow_dispatch`・パラメータ可能）
- **repository_dispatch: types: [ml-drift-detected]**（Phase 89-γ Auto Retraining）

**パラメータ**:
- `n_trials`: Optuna 最適化試行回数（50 推奨・100 高精度・30 テスト用）
- `dry_run`: ドライラン実行フラグ（モデル保存なし）

**実行フロー**（Phase 90α 対応）:
1. 環境セットアップ（Python 3.13 + 依存関係 + `ML_TRAINING_N_JOBS=-1` で RF 並列化）
2. データ収集（365 日分・履歴 CSV）
3. ML 学習（**メタラベリング**: `--meta-label --meta-tp-ratio 0.007 --meta-sl-ratio 0.0086`）
4. 品質検証（特徴量数 55 確認）
5. 自動 commit + push
6. `model-updated` イベント送信 → ci.yml 自動デプロイ

**実行時間**: 約 7-10 分（50 trials）・タイムアウト 60 分・モデル別 30 分

---

### backtest.yml - バックテスト実行

**役割**: バックテスト実行 + Markdown レポート生成

**実行条件**: 手動実行のみ（`workflow_dispatch`）

**パラメータ**:
- `phase_name`: Phase 名（例: 90α）
- `backtest_days`: バックテスト日数（デフォルト 180）

**実行フロー**: 環境セット → 履歴 CSV 取得 → バックテスト → Markdown 生成 → Git コミット

---

### walk_forward.yml - Walk-Forward 検証

**役割**: 過学習検出のための時系列分割検証

**実行条件**: 手動実行（`workflow_dispatch`）

**実行フロー**: 履歴データを複数 window に分割 → 各 window で学習＋検証 → 全 window のメトリクス集約 → `docs/検証記録/walk_forward/` に保存

---

### cleanup.yml - GCP リソースクリーンアップ

**役割**: GCP リソースの自動削除とコスト最適化

**実行条件**:
- 手動実行（`workflow_dispatch`・推奨）
- 毎月第 1 日曜日 JST 2:00 AM（スケジュール）

**パラメータ**: `cleanup_level`（safe/moderate/aggressive）

| レベル | 内容 |
|---|---|
| safe | 古い Docker イメージ（最新 5 保持）+ Cloud Run リビジョン（最新 3 保持）|
| moderate | safe + Cloud Build 履歴（30 日以上）|
| aggressive | より積極的な大量削除（要注意）|

---

### 🚨 emergency-stop.yml - 緊急停止

**役割**: iPhone からワンタップで実行可能な緊急停止/復旧

**実行条件**: 手動実行のみ（`workflow_dispatch`）

**アクション**:
- `stop`: トラフィック 0%（即時停止・復旧簡単）
- `resume`: トラフィック 100%（復旧）
- `status`: 状態確認のみ

**使い方**: iPhone GitHub アプリ → Actions → 🚨 Emergency Stop → Run workflow

---

## 自動化フロー

```
🗓️  毎週日曜 18:00 JST
    ↓
🤖 model-training.yml 自動実行
    ├── 365 日分データ収集
    ├── ProductionEnsemble 学習（LGB 34% / XGB 34% / RF 17% / N-BEATS 15%）
    ├── 55 特徴量・メタラベリング（success/failure）品質検証
    └── Git 自動コミット → model-updated イベント送信
    ↓
🚀 ci.yml 自動トリガー
    ├── テスト + 品質チェック
    ├── Docker Build + Artifact Registry プッシュ
    └── Cloud Run 本番デプロイ（MODE=live）
    ↓
✅ 週次完全自動モデル更新完了

🗓️  毎月第 1 日曜 2:00 JST
    ↓
🧹 cleanup.yml 自動実行（safe モード）
    └── 古いリソース削除

🚨 Drift 検知時（ml.drift.consecutive_threshold 連続）
    ↓
🔄 MLHealthMonitor.trigger_retraining()
    ├── GitHub repository_dispatch (event_type=ml-drift-detected)
    └── model-training.yml 自動起動 → ci.yml 連鎖デプロイ
```

## 手動実行

```bash
gh workflow run ci.yml                                    # CI/CD パイプライン
gh workflow run model-training.yml -f n_trials=50         # ML 学習（標準）
gh workflow run model-training.yml -f n_trials=100        # 高精度学習
gh workflow run model-training.yml -f dry_run=true        # ドライラン
gh workflow run backtest.yml -f phase_name=90a -f backtest_days=180
gh workflow run walk_forward.yml                          # WF 検証
gh workflow run cleanup.yml -f cleanup_level=safe         # クリーンアップ
gh workflow run emergency-stop.yml -f action=status       # 状態確認
gh workflow run emergency-stop.yml -f action=stop         # 緊急停止
gh workflow run emergency-stop.yml -f action=resume       # 復旧

# 実行履歴
gh run list --workflow=<name>.yml --limit 5
gh run view <RUN_ID> --log
```

## 重要な設定・制約

### 実行制約
- mainブランチ実行は順次（競合回避）
- 実行時間: CI/CD 30 分・ML 学習 60 分・クリーンアップ 20 分
- Python 3.13 統一

### 環境変数（model-training.yml）
- `ML_TRAINING_N_JOBS`: -1（CI で全コア並列・RF 31 分→6.5 分）
- `ML_TRAINING_PER_MODEL_TIMEOUT`: 1800（モデル別 30 分タイムアウト）
- `ML_TRAINING_MODE`: true（cross_asset history pickle リーク防止）

### GCP 認証・権限
- Workload Identity: `projects/11445303925/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- Service Account: `github-deployer@my-crypto-bot-project.iam.gserviceaccount.com`
- Secret Manager（具体的バージョン必須・`:latest` 禁止）:
  - `bitbank-api-key:X`
  - `bitbank-api-secret:X`
  - `discord-webhook-url:X`
  - `github-repo-dispatch-token:X`（Phase 89-γ Auto Retraining）

## 更新履歴（要点）

- **Phase 90α (2026-05-17)**: model-training.yml に `--meta-label` フラグ追加（macro F1 0.347 → 0.546）+ n_jobs 環境変数化
- **Phase 89-γ (2026-05-16)**: model-training.yml に `repository_dispatch: types: [ml-drift-detected]` 追加（Auto Retraining）
- **Phase 89-β (2026-05-15)**: 55 特徴量対応 + 4 モデル化（N-BEATS 追加）
- **Phase 61.2 (2026-01-25)**: weekly_report.yml 削除（Discord 機能廃止）
- **Phase 60 (2026-01-19)**: walk_forward.yml 追加
- **Phase 52.2 (2025-12-13)**: emergency-stop.yml 追加 + cleanup.yml SHA256 削除化 + 環境変数化

---

**最終更新**: 2026年5月18日（Phase 90α: 55 特徴量・4 モデル・メタラベリング・Auto Retraining 対応）
