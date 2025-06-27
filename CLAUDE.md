# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 開発コマンド

### テストと品質チェック
- `bash scripts/checks.sh` - 全品質チェックを実行（flake8, isort, black, カバレッジ70%のpytest）
- `pytest tests/unit` - ユニットテストのみ実行
- `pytest tests/integration` - 統合テスト実行（APIキーが必要）
- `bash scripts/run_e2e.sh` - Bybit TestnetでE2Eテスト実行

### 48時間本番稼働監視 🚀
- `./scripts/monitor_48h_deployment.sh` - 48時間連続監視（5分間隔）
- `./scripts/monitor_48h_deployment.sh --once` - ワンタイムヘルスチェック
- `./scripts/troubleshoot_deployment.sh` - 自動エラー診断・ログ解析
- `./scripts/verify_wif_hardening.sh` - Workload Identity Federation セキュリティ検証

### モデル学習と最適化
- `python -m crypto_bot.main optimize-and-train --config config/default.yml` - Optuna最適化付きフルMLパイプライン
- `python -m crypto_bot.main train --config config/default.yml` - 基本モデル学習
- `python -m crypto_bot.main optimize-ml --config config/default.yml` - ハイパーパラメータ最適化のみ

### バックテストと分析
- `python -m crypto_bot.main backtest --config config/default.yml` - ウォークフォワードバックテスト
- `python -m crypto_bot.main optimize-backtest --config config/default.yml` - パラメータ最適化
- `bash scripts/run_pipeline.sh` - 完全分析パイプライン（最適化→キャリブレーション→バックテスト→可視化）

### 本番取引所テスト
- `bash scripts/run_production_tests.sh -c bybit` - API互換性チェック（Bybit）
- `bash scripts/run_production_tests.sh bitbank` - 基本機能テスト（残高・データ取得）
- `bash scripts/run_production_tests.sh -s bitflyer` - 実注文テスト（最小額、要注意）
- `bash scripts/run_production_tests.sh -a -c` - 全取引所互換性チェック

### 監視・アラート
- `python scripts/check_monitoring_status.py` - 監視システム全体の動作確認
- `python scripts/test_alert_policies.py` - アラートポリシーのE2Eテスト
- `bq query --use_legacy_sql=false < scripts/bigquery_log_queries.sql` - ログ分析クエリ実行

### ライブトレード（ペーパー）
- `python -m crypto_bot.main live-paper --config config/default.yml` - Testnetペーパートレード
- `streamlit run crypto_bot/monitor.py` - ローカル監視ダッシュボード

### オンライン学習コマンド
- `python -m crypto_bot.main online-train --config config/default.yml --model-type river_linear` - オンライン学習開始
- `python -m crypto_bot.main drift-monitor --config config/default.yml --duration 3600` - データドリフト監視
- `python -m crypto_bot.main retrain-schedule --config config/default.yml --model-id my_model --start` - 自動再トレーニング開始
- `python -m crypto_bot.main online-status --export status/online.json` - オンライン学習ステータス確認

### Dockerコマンド
- `bash scripts/build_docker.sh` - Dockerイメージビルド
- `bash scripts/run_docker.sh <command>` - Dockerコンテナ内で任意のコマンド実行

### Kubernetesコマンド
- `helm lint k8s/helm/crypto-bot` - Helmチャートの検証
- `helm install crypto-bot k8s/helm/crypto-bot --namespace crypto-bot-dev --values k8s/helm/crypto-bot/values-dev.yaml` - 開発環境デプロイ
- `kubectl get pods -n crypto-bot-dev` - Pod状態確認
- `kubectl logs -f deployment/crypto-bot -n crypto-bot-dev` - ログ確認
- `kubectl port-forward svc/crypto-bot 8080:80 -n crypto-bot-dev` - ローカルアクセス
- `gh workflow run "Kubernetes Deploy" --field environment=dev --field platform=gke` - GitHub Actions手動デプロイ

### CI/CDとデプロイメント
#### 環境別自動デプロイ
- **Development**: `develop`ブランチ → dev環境（paper mode）自動デプロイ
- **Production**: `main`ブランチ → prod環境（live mode）自動デプロイ
- **HA Production**: `v*.*.*`タグ → ha-prod環境（multi-region）自動デプロイ

#### ビルド最適化
- GitHub Actions Cacheとレジストリキャッシュでビルド時間短縮
- 最新Actions（auth@v2.1.3, setup-gcloud@v2.1.0）使用
- マルチステージDockerfileでキャッシュ効率向上

#### セキュリティ機能
- 最小権限デプロイサービスアカウント（ServiceAccountAdmin削除済み）
- Workload Identity Federation（OIDC認証）
- リポジトリ制限付きプロバイダー設定

## アーキテクチャ概要

### コアコンポーネント
- **crypto_bot/main.py** - 学習、バックテスト、ライブトレードのCLIエントリポイント
- **crypto_bot/strategy/** - トレード戦略（MLStrategyがメイン）
- **crypto_bot/execution/** - 取引所クライアント（Bybit, Bitbank, Bitflyer, OKCoinJP）
- **crypto_bot/backtest/** - ウォークフォワード検証付きバックテストエンジン
- **crypto_bot/ml/** - 機械学習パイプライン（LightGBM/XGBoost/RandomForest）
- **crypto_bot/data/** - マーケットデータ取得と前処理
- **crypto_bot/risk/** - 動的ポジションサイジング付きリスク管理
- **crypto_bot/online_learning/** - インクリメンタル学習（River/scikit-learn）
- **crypto_bot/drift_detection/** - データドリフト検知（ADWIN/DDM/統計的検定）

### データフロー
1. CCXT経由で取引所からデータ取得（デフォルト：Bybit Testnet）
2. pandas-taでテクニカル指標計算
3. preprocessor.pyでML特徴量エンジニアリング
4. Optunaハイパーパラメータ最適化でモデル学習
5. ウォークフォワードバックテストで戦略パフォーマンス検証
6. Testnet上で監視付きライブトレード実行

### オンライン学習フロー
1. ライブデータストリームから新しいサンプルを受信
2. インクリメンタルモデル（River/scikit-learn）でpartial_fit実行
3. データドリフト検知アルゴリズム（ADWIN/DDM/統計的検定）で異常監視
4. 性能監視システムでモデル精度を継続追跡
5. 設定可能なトリガー（性能劣化/ドリフト検知/スケジュール）で自動再トレーニング
6. アラート・ログ出力で運用監視サポート

### 設定
- **config/default.yml** - メイン設定ファイル
- **.env** - APIキーとシークレット（.env.exampleをテンプレートとして使用）
- **pyproject.toml** - 依存関係付きPythonパッケージ設定

### 主要機能
- **ウォークフォワード検証** - 訓練/テスト分割による現実的なバックテスト
- **マルチ取引所対応** - ファクトリーパターンによるプラガブル取引所クライアント
- **MLパイプライン** - 自動特徴量エンジニアリング、学習、キャリブレーション
- **リスク管理** - ボラティリティベースの動的ポジションサイジング
- **監視** - Cloud Monitoring統合とStreamlitダッシュボード
- **CI/CD** - GitHub ActionsとTerraformによるCloud Run/Kubernetesデプロイ
- **Kubernetes対応** - GKE/EKS完全対応、Helm Chart、HPA/PDB
- **コードレビュー** - Issue/PRテンプレート、自動品質チェック、ブランチ保護

### テスト戦略
- ユニットテストは個別コンポーネントをカバー
- 統合テストは取引所API連携を検証
- E2EテストはTestnet上で完全なトレードワークフローを実行  
- カバレッジ要件：最低70%

### テクニカル指標
config/default.ymlの`ml.extra_features`で設定可能：
- RSI、MACD、RCI（モメンタム用）
- Volume Z-score（出来高分析用）
- 時間特徴（曜日、時間）
- カスタム指標（crypto_bot/indicator/calculator.py）

### 開発ワークフロー

#### 環境別ブランチ戦略（最新）
**開発フロー**:
1. **feature/XXXブランチ作成**: `git checkout -b feature/your-feature`
2. **コード変更**: 機能実装・バグ修正
3. **品質チェック**: `bash scripts/checks.sh`でflake8/black/isort/pytest
4. **E2Eテスト**: `bash scripts/run_e2e.sh`でTestnet検証
5. **developブランチへPR**: 開発環境での自動テスト
6. **自動デプロイ**: develop → dev環境（paper mode）自動デプロイ
7. **統合テスト**: dev環境での動作確認
8. **mainブランチへPR**: 本番デプロイ準備
9. **本番デプロイ**: main → prod環境（live mode）自動デプロイ

**リリースフロー**:
1. **リリースタグ作成**: `git tag v1.0.0 && git push origin v1.0.0`
2. **HA環境自動デプロイ**: タグ → ha-prod環境（multi-region）
3. **ヘルスチェック**: 全リージョンでの動作確認
4. **監視確認**: ダッシュボードでメトリクス監視

#### ブランチ運用ルール
- **main**: 本番環境（live mode）- 直接pushは禁止、PR必須
- **develop**: 開発環境（paper mode）- featureブランチからのPR受け入れ
- **feature/XXX**: 機能ブランチ - developへのPR作成
- **hotfix/XXX**: 緊急修正 - mainへの直接PR可能

#### セキュリティチェックポイント
- サービスアカウント権限は最小権限を維持
- Secretsの適切な管理
- Workload Identity Federationの正常動作確認
- .dockerignoreによる機密情報除外確認
10. **自動デプロイ**: mainブランチプッシュでCI経由Cloud Runデプロイ

#### Kubernetes デプロイ（新方式）
1-9. **上記1-9と同じ**
10. **K8sデプロイ**: k8s-deploy.ymlワークフローでGKE/EKSデプロイ
11. **スケーリング確認**: HPA/PDBによる自動スケーリング検証
12. **監視**: Prometheus/Cloud Monitoringでメトリクス監視

### コードレビューとIssue管理
- **.github/ISSUE_TEMPLATE/**: バグ報告・機能要求・改善提案用テンプレート
- **.github/PULL_REQUEST_TEMPLATE/**: 包括的なPRチェックリスト
- **.github/workflows/code-review.yml**: 自動品質チェック・セキュリティスキャン
- **docs/github-branch-protection.md**: ブランチ保護設定手順書

### Kubernetesリソース
- **k8s/manifests/**: 基本Kubernetesマニフェスト（Deployment, Service, ConfigMap等）
- **k8s/helm/crypto-bot/**: 包括的Helmチャート（環境別values含む）
- **infra/modules/gke/**: GKE Terraformモジュール
- **infra/modules/eks/**: EKS Terraformモジュール
- **infra/envs/k8s-gke/**: GKE環境設定
- **infra/envs/k8s-eks/**: EKS環境設定
- **.github/workflows/k8s-deploy.yml**: Kubernetes自動デプロイワークフロー
- **docs/kubernetes-migration-guide.md**: Cloud RunからKubernetes移行ガイド

## 📋 開発履歴とマイルストーン

### 🎉 **2025年6月26日**: CI/CDパイプライン完全構築成功

#### ✅ **技術的成果**
**「ローカルで通ればCIも通る」原則の実証**
- Docker build最適化によるローカル・CI環境一致性確保
- Terraform Infrastructure as Codeによる再現可能なデプロイ
- Workload Identity Federationによる安全な認証基盤

#### 🏗️ **実装したインフラ構成**
```
GitHub Repository
├── GitHub Actions (CI/CD Pipeline)
│   ├── Docker Build & Test
│   ├── Terraform Validation
│   └── Multi-Environment Deploy
├── Workload Identity Federation
│   ├── OIDC Provider (Repository-Restricted)
│   ├── Identity Pool (github-pool)
│   └── Service Account Binding
└── Google Cloud Platform
    ├── Cloud Run Services
    │   ├── crypto-bot-service-prod (LIVE)
    │   └── crypto-bot-dev (PAPER)
    ├── Artifact Registry (Docker Images)
    ├── Cloud Monitoring (Metrics & Alerts)
    ├── BigQuery (Log Analytics)
    ├── Cloud Storage (Terraform State)
    └── IAM (Minimal Privilege SA)
```

#### 🔧 **解決した主要な技術課題**

**1. Docker Build タイムアウト問題**
```dockerfile
# 修正前: 重複ビルドによるタイムアウト
RUN pip wheel --no-cache-dir --no-deps -w /app/wheels .
RUN pip wheel --no-cache-dir --no-deps -w /app/wheels .  # 重複

# 修正後: 効率的な単一ステージビルド
RUN pip wheel --no-cache-dir --no-deps -w /app/wheels .
RUN pip install --no-cache-dir --find-links /app/wheels /app/wheels/*.whl
```

**2. Workload Identity Federation 移行**
```yaml
# 修正前: サービスアカウントキー認証（期限切れ）
- uses: google-github-actions/auth@v1
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}

# 修正後: WIF OIDC認証（キーレス）
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
    service_account: ${{ secrets.GCP_DEPLOYER_SA }}
```

**3. Terraform State共有問題**
```hcl
# 修正前: ローカルstate (CI/CDで共有不可)
terraform {
  # No remote backend
}

# 修正後: GCS Remote Backend
terraform {
  backend "gcs" {
    bucket = "my-crypto-bot-terraform-state"
    prefix = "prod"  # 環境別prefix
  }
}
```

**4. 最小権限IAM設計**
```bash
# デプロイサービスアカウントの最小権限セット
ROLES=(
  "roles/run.admin"                    # Cloud Run管理
  "roles/artifactregistry.admin"       # コンテナレジストリ
  "roles/monitoring.admin"             # メトリクス・アラート
  "roles/secretmanager.admin"          # シークレット管理
  "roles/storage.objectAdmin"          # Terraformステート
  "roles/bigquery.admin"               # ログ分析
  "roles/logging.admin"                # ログ収集
  "roles/iam.workloadIdentityPoolAdmin" # WIF管理
)
```

#### 🚀 **現在の稼働状況**
- **本番サービス**: `crypto-bot-service-prod` - **RUNNING** ✅
- **開発サービス**: `crypto-bot-dev` - **RUNNING** ✅  
- **本番URL**: https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health
- **モード**: Paper mode（24時間安定性テスト実行中）
- **開始時刻**: 2025-06-26 21:00 JST
- **監視**: Cloud Monitoring + BigQuery Logging 稼働中

#### 📊 **次期マイルストーン**
1. ✅ **Terraform CI/CD構築**: 完了
2. 🔄 **Paper mode 24時間テスト**: 実行中（2025-06-26 21:00〜）
3. ⏭️ **Live mode短時間テスト**: Paper mode成功後実施
4. ⏭️ **Live mode 24時間本格運用**: 最終段階
5. ⏭️ **戦略最適化**: 運用データ分析・アルゴリズム改善

#### 🔍 **運用監視コマンド**
```bash
# デプロイメント状態確認
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health

# ログ確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-prod" --limit=50

# メトリクス確認  
gcloud monitoring metrics list --filter="metric.type:custom.googleapis.com/crypto_bot/*"

# Terraform状態確認
cd infra/envs/prod && terraform show
```

#### 💡 **学んだベストプラクティス**
1. **ローカル優先開発**: `ローカルで通ればCIも通る`を実証
2. **Infrastructure as Code**: Terraformによる完全な環境再現
3. **セキュリティファースト**: WIF + 最小権限SAによるゼロトラスト
4. **モニタリング充実**: Cloud Monitoring + BigQuery統合監視
5. **段階的デプロイ**: dev(paper) → prod(paper) → prod(live)の慎重なプロモーション

### 📝 **技術詳細アーカイブ**

#### Dockerfile最適化詳細
```dockerfile
# マルチステージビルドによる効率化
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps -w /app/wheels -r requirements.txt
COPY . .
RUN pip wheel --no-cache-dir --no-deps -w /app/wheels .

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/wheels /app/wheels/
RUN pip install --no-cache-dir --find-links /app/wheels /app/wheels/*.whl
COPY . .
CMD ["uvicorn", "crypto_bot.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### WIF Provider設定詳細
```bash
# リポジトリ制限付きOIDCプロバイダー
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition='attribute.repository == "nao-namake/crypto-bot"'
```

#### BigQuery Logging設定
```hcl
# ログシンク + ビュー作成（現在は一時的に無効化）
resource "google_logging_project_sink" "crypto_bot_bq_sink" {
  name = "${var.service_name}_bq_sink"
  filter = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${var.service_name}"
  EOT
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${data.google_bigquery_dataset.crypto_bot_logs.dataset_id}"
}
```

この技術基盤により、**安定した本番環境での暗号資産取引ボット運用**が実現可能になりました。