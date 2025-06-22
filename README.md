# Crypto-Bot - 汎用暗号資産トレーディングボット

## 概要

暗号資産の自動売買ボットです。バックテスト、パラメータ最適化、ウォークフォワード検証、機械学習モデル、Testnet/Live発注までをワンストップで実行できます。

## 主な機能

- **データ取得**: CCXT経由（デフォルト: Bybit Testnet）
- **バックテスト**: スリッページ・手数料・ATRストップ・損益集計
- **最適化**: テクニカル指標スイープ/Optuna ハイパーパラメータ探索、MLモデル再学習
- **ウォークフォワード**: CAGR・Sharpeを可視化
- **リスク管理**: 動的ポジションサイジング（dynamic_position_sizing）
- **機械学習**: LightGBM/RandomForest/XGBoost、追加特徴量（volume_zscore等）
- **パイプライン**: run_pipeline.shで一連処理を自動化
- **CI/CD**: GitHub Actions（lint/unit/integration、カバレッジ70%以上）+ 環境別自動デプロイ
- **セキュリティ**: 最小権限サービスアカウント、Workload Identity Federation、最新Actionsバージョン
- **コードレビュー**: Issue/PRテンプレート、自動品質チェック、ブランチ保護
- **マルチ取引所対応**: Bybit, Bitbank, Bitflyer, OKCoinJP（本番API互換性確認済み）
- **監視機能**: GCP Cloud Monitoring + Streamlit ダッシュボード
- **インフラ**: Terraform + GCP Cloud Run + Workload Identity Federation
- **Kubernetes対応**: GKE/EKS完全対応、Helm Chart、自動スケーリング
- **高可用性**: マルチリージョンデプロイ + Global Load Balancer + 自動フェイルオーバー
- **オンライン学習**: River/scikit-learn対応インクリメンタル学習、データドリフト検知、自動再トレーニング
- **ビルド最適化**: Dockerマルチレイヤーキャッシュ、GitHub Actions Cacheによる高速ビルド

## 動作要件

- Python 3.11 〜 3.12
- Bybit Testnet API Key と Secret
- 動作確認環境: Linux/macOS/WSL2
- GCPプロジェクト（Cloud Monitoring有効化）とMetric Writer権限付きサービスアカウント
- Kubernetes環境（オプション）: GKE または EKS クラスター

## セットアップ

### 1. リポジトリを取得
```bash
git clone https://github.com/nao-namake/crypto-bot.git
cd crypto-bot
```

### 2. 仮想環境を作成
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. パッケージをインストール
```bash
pip install -e .
pip install -r requirements-dev.txt
```

### 4. GCP認証キーを設定
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### 5. APIキーを設定
```bash
cp .env.example .env
# .env を開いて BYBIT_TESTNET_API_KEY と SECRET を記入
```

## 基本コマンド

### バックテスト
```bash
python -m crypto_bot.main backtest --config config/default.yml
```

### 最適化付きバックテスト
```bash
python -m crypto_bot.main optimize-backtest --config config/default.yml
```

### 機械学習モデル学習
```bash
python -m crypto_bot.main train --config config/default.yml
```

### 学習 + Optuna最適化
```bash
python -m crypto_bot.main optimize-and-train --config config/default.yml
```

### Testnet統合テスト
```bash
# Bybit Testnet E2Eテスト
bash scripts/run_e2e.sh

# 本番取引所テスト（要APIキー）
bash scripts/run_production_tests.sh -c bitbank  # API互換性のみ
bash scripts/run_production_tests.sh bitbank     # 基本機能テスト
bash scripts/run_production_tests.sh -s bitbank  # 実注文テスト（要注意）
```

### コード整形とテスト
```bash
bash scripts/checks.sh
```

### ローカル監視UI
```bash
streamlit run crypto_bot/monitor.py
```

### 高可用性（HA）管理

#### クラスター状態確認
```bash
curl https://your-load-balancer-ip/health/cluster
```

#### 手動フェイルオーバー
```bash
curl -X POST https://your-load-balancer-ip/health/failover
```

#### HA監視ダッシュボード
```bash
# Terraform出力からダッシュボードURLを取得
terraform -chdir=infra/envs/ha-prod output dashboard_url
```

### マルチ戦略管理

#### 利用可能な戦略一覧
```bash
python -m crypto_bot.main list-strategies
```

#### 戦略詳細情報
```bash
python -m crypto_bot.main strategy-info simple_ma
```

#### 設定検証
```bash
python -m crypto_bot.main validate-config --config config/multi_strategy.yml
```

### オンライン学習

#### オンライン学習の開始
```bash
python -m crypto_bot.main online-train --config config/default.yml --model-type river_linear
```

#### データドリフト監視
```bash
python -m crypto_bot.main drift-monitor --config config/default.yml --duration 3600 --log-file logs/drift.log
```

#### 自動再トレーニングスケジューラー
```bash
python -m crypto_bot.main retrain-schedule --config config/default.yml --model-id my_model --start
```

#### オンライン学習ステータス確認
```bash
python -m crypto_bot.main online-status --export status/online_learning.json
```

## パイプライン自動実行

### 1. 最適モデルを作成
```bash
python -m crypto_bot.main optimize-and-train --config config/default.yml
```

### 2. パイプライン実行（ログを保存）
```bash
caffeinate ./scripts/run_pipeline.sh 2>&1 | tee results/pipeline_log/pipeline_$(date +%Y%m%d_%H%M%S).log
```

## Docker での実行

### 1. Dockerイメージのビルド
```bash
bash scripts/build_docker.sh
```

### 2. .envファイルの準備
```bash
cp .env.example .env
# .env を開いて必要な項目を記入
```

### 3. Dockerコンテナでコマンドを実行
```bash
# バックテスト
bash scripts/run_docker.sh backtest --config config/default.yml

# モデル最適化
bash scripts/run_docker.sh optimize-and-train --config config/default.yml

# 統合テスト
bash scripts/run_docker.sh e2e-test
```

## GCP インフラストラクチャ

### Terraform セットアップ

#### 1. Terraformをインストール
```bash
# macOS
brew install terraform

# Linux
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform
```

#### 2. GCPプロジェクトの設定
```bash
# プロジェクトを作成
gcloud projects create crypto-bot-project-id

# プロジェクトを設定
gcloud config set project crypto-bot-project-id

# 必要なAPIを有効化
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

#### 3. Terraform初期化
```bash
cd infra/envs/dev
terraform init
```

#### 4. インフラプランの確認
```bash
terraform plan
```

#### 5. インフラの適用
```bash
terraform apply
```

### 環境別デプロイ

#### 開発環境（dev）
```bash
cd infra/envs/dev
terraform workspace select dev || terraform workspace new dev
terraform apply
```

#### ペーパートレード環境（paper）
```bash
cd infra/envs/paper
terraform workspace select paper || terraform workspace new paper
terraform apply
```

#### 本番環境（prod）
```bash
cd infra/envs/prod
terraform workspace select prod || terraform workspace new prod
terraform apply
```

#### 高可用性本番環境（ha-prod）
```bash
cd infra/envs/ha-prod
terraform init
terraform apply
```

このHA環境では以下の機能が有効になります：
- **マルチリージョンデプロイ**: asia-northeast1（プライマリ）+ us-central1（セカンダリ）
- **Global Load Balancer**: 自動的にトラフィックを健全なリージョンにルーティング
- **リーダー選出**: プライマリリージョンがリーダーとして動作し、セカンダリは待機
- **自動フェイルオーバー**: プライマリリージョン障害時にセカンダリが自動的に引き継ぎ
- **クラスター監視**: 全リージョンの健全性を一元監視

### GCP サービスアカウント設定

```bash
# サービスアカウントを作成
gcloud iam service-accounts create crypto-bot-sa \
    --description="Crypto Bot Service Account" \
    --display-name="Crypto Bot SA"

# 必要な権限を付与
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:crypto-bot-sa@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.metricWriter"

# キーファイルを作成
gcloud iam service-accounts keys create crypto-bot-key.json \
    --iam-account=crypto-bot-sa@PROJECT_ID.iam.gserviceaccount.com
```

### Cloud Monitoring セットアップ

```bash
# カスタム指標を確認
gcloud monitoring metrics list --filter="metric.type:custom.googleapis.com/crypto_bot/*"

# アラートポリシーを作成（例: PnL監視）
gcloud alpha monitoring policies create --policy-from-file=monitoring/alert-policy.yaml
```

## コードレビュー・Issue管理

### GitHub Issue テンプレート

リポジトリでは以下のIssueテンプレートが利用できます：

- **バグ報告**: 詳細な再現手順とトリアージ情報を収集
- **機能要求**: 新機能の提案用構造化テンプレート
- **改善提案**: 既存機能の改善提案用テンプレート

### Pull Request プロセス

1. **ブランチ作成**: `git checkout -b feature/your-feature`
2. **PR作成**: 包括的なPRテンプレートを使用
3. **自動チェック**: コード品質、セキュリティ、複雑度分析
4. **コードレビュー**: 必須承認設定での品質管理
5. **マージ**: 保護ルールによる安全なマージ

### ブランチ保護設定

詳細は [`docs/github-branch-protection.md`](docs/github-branch-protection.md) を参照してください。

主要な保護機能：
- mainブランチへの直接プッシュ禁止
- Pull Requestでのコードレビュー必須
- 自動テスト合格の必須化
- コード品質チェックの強制

## GitHub Actions CI/CD

### 環境別自動デプロイ戦略

本プロジェクトでは、ブランチベースの環境別デプロイメント戦略を採用しています：

| 環境 | ブランチ | モード | デプロイ条件 |
|------|----------|--------|--------------|
| **Development** | `develop` | paper | develop pushまたはPR |
| **Production** | `main` | live | main pushのみ |
| **HA Production** | tags | live | `v*.*.*` タグpushのみ |

### 1. GitHub Secrets設定
```bash
# GitHub CLIを使用（最新版推奨）
gh secret set BYBIT_TESTNET_API_KEY --body "your-api-key"
gh secret set BYBIT_TESTNET_API_SECRET --body "your-api-secret"
gh secret set CODECOV_TOKEN --body "your-codecov-token"
gh secret set CR_PAT --body "your-container-registry-token"
gh secret set GCP_PROJECT_ID --body "your-gcp-project-id"
gh secret set GCP_PROJECT_NUMBER --body "your-gcp-project-number"
gh secret set GCP_WIF_PROVIDER --body "projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
gh secret set GCP_DEPLOYER_SA --body "github-deployer@PROJECT_ID.iam.gserviceaccount.com"
gh secret set ALERT_EMAIL --body "your-alert-email@example.com"
```

### 2. セキュリティ強化済みWorkload Identity Federation設定
```bash
# GitHub OIDCプロバイダーを作成（リポジトリ制限付き）
gcloud iam workload-identity-pools create "github-pool" \
    --location="global" \
    --description="GitHub Actions pool"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition='attribute.repository == "nao-namake/crypto-bot"'
```

### 3. 最小権限デプロイサービスアカウント設定
```bash
# デプロイ用サービスアカウントを作成
gcloud iam service-accounts create github-deployer \
    --description="GitHub Actions deployer (minimal privileges)" \
    --display-name="GitHub Deployer"

# 最小権限セットを付与（セキュリティ強化済み）
DEPLOYER_SA="github-deployer@PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:$DEPLOYER_SA" --role="roles/run.admin"
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:$DEPLOYER_SA" --role="roles/artifactregistry.admin"
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:$DEPLOYER_SA" --role="roles/monitoring.admin"
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:$DEPLOYER_SA" --role="roles/serviceusage.serviceUsageAdmin"
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:$DEPLOYER_SA" --role="roles/secretmanager.admin"
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:$DEPLOYER_SA" --role="roles/storage.objectAdmin"

# Workload Identity のバインディング
gcloud iam service-accounts add-iam-policy-binding \
    --role roles/iam.workloadIdentityUser \
    --member "principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/nao-namake/crypto-bot" \
    $DEPLOYER_SA
```

### 4. 高速ビルド・最適化機能

**Dockerビルドキャッシュ**:
- GitHub Actions Cache + レジストリキャッシュの併用
- マルチステージビルド最適化
- .dockerignoreによる不要ファイル除外

**CI/CD最適化**:
- 最新GitHub Actionsバージョン使用
- 並列テスト実行
- 環境別条件分岐による効率的デプロイ

## 監視とアラート

### 1. カスタム指標Push
```bash
# monitor.pyが status.json を読み取り、PnL等をCloud Monitoringへ送信
python crypto_bot/monitor.py
```

### 2. Cloud Monitoringダッシュボード
- custom.googleapis.com/crypto_bot/* シリーズをウィジェットへ追加
- PnL=折れ線、取引回数=スコアカード、position_flag=ゲージが推奨

### 3. アラートポリシー
- PnL が -5,000円未満で1時間持続 → Bot停止検討
- 取引レイテンシ > 3s が15分継続 → 高レイテンシ通知

## Kubernetes デプロイメント

### 前提条件

- kubectl がインストール済み
- Helm 3.x がインストール済み
- Kubernetesクラスター（GKE または EKS）への接続設定済み

### GKE クラスターのセットアップ

#### 1. Terraformでクラスター作成
```bash
cd infra/envs/k8s-gke
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集してプロジェクトID等を設定

terraform init
terraform plan
terraform apply
```

#### 2. kubectl接続設定
```bash
gcloud container clusters get-credentials crypto-bot-dev \
  --zone=asia-northeast1 \
  --project=your-project-id
```

### EKS クラスターのセットアップ

#### 1. Terraformでクラスター作成
```bash
cd infra/envs/k8s-eks
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集してAWS設定

terraform init
terraform plan
terraform apply
```

#### 2. kubectl接続設定
```bash
aws eks update-kubeconfig \
  --region us-west-2 \
  --name crypto-bot-dev
```

### Helmデプロイメント

#### 1. 開発環境へのデプロイ
```bash
# Helmチャートの検証
helm lint k8s/helm/crypto-bot

# 開発環境デプロイ
helm install crypto-bot k8s/helm/crypto-bot \
  --namespace crypto-bot-dev \
  --create-namespace \
  --values k8s/helm/crypto-bot/values-dev.yaml \
  --set image.tag=latest
```

#### 2. 本番環境へのデプロイ
```bash
# 本番環境デプロイ
helm install crypto-bot k8s/helm/crypto-bot \
  --namespace crypto-bot-prod \
  --create-namespace \
  --values k8s/helm/crypto-bot/values-prod.yaml \
  --set image.tag=v1.0.0
```

#### 3. 設定の更新
```bash
# Helm values の更新
helm upgrade crypto-bot k8s/helm/crypto-bot \
  --namespace crypto-bot-dev \
  --values k8s/helm/crypto-bot/values-dev.yaml \
  --set config.mode=paper
```

### マニフェストベースデプロイ（代替方法）

```bash
# 基本リソースの適用
kubectl apply -f k8s/manifests/namespace.yaml
kubectl apply -f k8s/manifests/configmap.yaml
kubectl apply -f k8s/manifests/secret.yaml
kubectl apply -f k8s/manifests/serviceaccount.yaml

# アプリケーションのデプロイ
kubectl apply -f k8s/manifests/deployment.yaml
kubectl apply -f k8s/manifests/service.yaml
kubectl apply -f k8s/manifests/hpa.yaml
kubectl apply -f k8s/manifests/pdb.yaml

# 外部アクセス用（オプション）
kubectl apply -f k8s/manifests/ingress.yaml
```

### GitHub Actions 自動デプロイ

#### 1. 必要なシークレット設定
```bash
# GKE用
gh secret set GCP_WIF_PROVIDER --body "projects/123/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
gh secret set GCP_CRYPTO_BOT_SA --body "crypto-bot-gke@project-id.iam.gserviceaccount.com"

# EKS用
gh secret set AWS_DEPLOY_ROLE_ARN --body "arn:aws:iam::123456789012:role/crypto-bot-deploy-role"
gh secret set AWS_CRYPTO_BOT_ROLE_ARN --body "arn:aws:iam::123456789012:role/crypto-bot-eks-role"
```

#### 2. 手動デプロイ実行
```bash
# GKE開発環境へのデプロイ
gh workflow run "Kubernetes Deploy" \
  --field environment=dev \
  --field platform=gke

# EKS本番環境へのデプロイ  
gh workflow run "Kubernetes Deploy" \
  --field environment=prod \
  --field platform=eks
```

### 動作確認

#### 1. Pod状態確認
```bash
kubectl get pods -n crypto-bot-dev
kubectl logs -f deployment/crypto-bot -n crypto-bot-dev
```

#### 2. サービス確認
```bash
kubectl get svc -n crypto-bot-dev
kubectl port-forward svc/crypto-bot 8080:80 -n crypto-bot-dev
```

#### 3. ヘルスチェック
```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/metrics
```

#### 4. スケーリング確認
```bash
kubectl get hpa -n crypto-bot-dev
kubectl scale deployment crypto-bot --replicas=3 -n crypto-bot-dev
```

### Kubernetes移行ガイド

Cloud RunからKubernetesへの詳細な移行手順については、[`docs/kubernetes-migration-guide.md`](docs/kubernetes-migration-guide.md) を参照してください。

## 設定ファイル（config/default.yml）

主な設定項目：
- `data`: 取得取引所・シンボル・期間など
- `strategy`: 戦略設定（単一またはマルチ戦略）
- `risk`: ベースリスク、dynamic_position_sizing設定
- `walk_forward`: 訓練窓・テスト窓・スライド幅
- `ml`: 追加特徴量、Optuna設定、モデルパラメータ

### 戦略設定の種類

#### 単一戦略の場合
```yaml
strategy:
  type: single
  name: ml
  params:
    model_path: model/calibrated_model.pkl
    threshold: 0.1
```

#### マルチ戦略の場合
```yaml
strategy:
  type: multi
  combination_mode: weighted_average  # weighted_average, majority_vote, unanimous, first_match
  strategies:
    - name: ml
      weight: 0.6
      params:
        model_path: model/calibrated_model.pkl
        threshold: 0.1
    - name: simple_ma
      weight: 0.3
      params:
        short_period: 20
        long_period: 50
    - name: bollinger_bands
      weight: 0.1
      params:
        period: 20
        std_dev: 2.0
```

## プロジェクト構成

```
crypto-bot/
├── .github/               # GitHub テンプレート・ワークフロー
│   ├── ISSUE_TEMPLATE/   # Issue テンプレート (バグ報告、機能要求等)
│   ├── PULL_REQUEST_TEMPLATE/ # PR テンプレート
│   └── workflows/        # CI/CD ワークフロー (ci.yml, code-review.yml, k8s-deploy.yml)
├── config/               # 設定ファイル (YAML)
├── crypto_bot/
│   ├── data/            # データ取得・ストリーム
│   ├── backtest/        # バックテストエンジン
│   ├── execution/       # 取引所クライアント
│   ├── strategy/        # 戦略 (MLStrategy等)
│   ├── ml/              # 前処理・モデル・最適化
│   ├── risk/            # リスク管理
│   └── utils/           # ユーティリティ
├── docs/                # プロジェクトドキュメント
│   ├── github-branch-protection.md # ブランチ保護設定手順書
│   └── kubernetes-migration-guide.md # Kubernetes移行ガイド
├── k8s/                 # Kubernetes設定
│   ├── manifests/       # 基本マニフェスト (Deployment, Service等)
│   └── helm/crypto-bot/ # Helm Chart (環境別values含む)
├── scripts/             # run_pipeline.sh, checks.sh等
├── tests/               # unit/integration テスト
├── tools/               # 分析・可視化ツール
├── infra/               # Terraform設定
│   ├── modules/         # 再利用可能モジュール (gke, eks, crypto_bot_app等)
│   └── envs/            # 環境別設定 (dev, prod, k8s-gke, k8s-eks)
└── requirements*.txt    # 依存関係
```

## Bot運用・拡張手順

### 1. テクニカル指標の追加・削除
```bash
# 1. crypto_bot/indicator/calculator.py に指標関数を追加
# 2. crypto_bot/ml/preprocessor.py の extra_features に追加
# 3. config/default.yml の ml:extra_features リストに追加
# 4. コード整形とテスト
bash scripts/checks.sh
# 5. パイプライン再実行
./scripts/run_pipeline.sh
```

### 2. 機械学習以外の戦略への切り替え
```bash
# 1. crypto_bot/strategy/ に新しい戦略クラスを作成
# 2. config/default.yml の strategy:name を変更
# 3. 動作確認
python -m crypto_bot.main backtest --config config/default.yml
```

### 3. 取引所の切り替え
```bash
# 1. API互換性チェック
bash scripts/run_production_tests.sh -c 取引所名

# 2. 環境変数の設定（.envファイルまたはexport）
export BITBANK_API_KEY="your_api_key"
export BITBANK_API_SECRET="your_api_secret"

# 3. config/default.yml の data:exchange を変更
# 4. 基本機能テスト
bash scripts/run_production_tests.sh 取引所名

# 5. 動作確認
python -m crypto_bot.main backtest --config config/default.yml
```

## 可視化ツール

- `tools/plot_performance.py`: エクイティカーブ・ドローダウン
- `tools/plot_walk_forward.py`: CAGR と Sharpe の推移グラフ
- `tools/sweep_thresholds.py`: 閾値スイープ分析

## FAQ

**Q: マルチ取引所の実運用はどうすれば？**
A: 雛形テスト・.env.exampleでAPI管理、実運用は本当に使うときのみ

**Q: テストは全取引所で必須？**
A: テストネットのない取引所は雛形まででOK。API仕様変更時のみ実装

**Q: 複数取引所の併用・拡張方法は？**
A: 1) API互換性チェック 2) 環境変数設定 3) config編集 4) 本番テスト実行 5) 段階的運用開始。詳細は [本番取引所運用ガイド](docs/production-exchange-guide.md) を参照

## ライセンス

本プロジェクトはMIT Licenseで公開されています。