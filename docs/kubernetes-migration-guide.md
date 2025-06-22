# Kubernetes移行ガイド - Cloud RunからKubernetesへ

このドキュメントでは、crypto-botをCloud RunからKubernetes（GKE/EKS）に移行する手順を説明します。

## 📋 概要

### なぜKubernetesに移行するのか

**メリット:**
- **より細かいリソース制御**: CPU/メモリ制限の柔軟な調整
- **高度なスケーリング**: HPA/VPAによる自動スケーリング
- **マルチクラウド対応**: GKE/EKS両対応
- **オーケストレーション機能**: CronJob、StatefulSet等の利用
- **エコシステム**: Prometheus、Grafana等の豊富な監視ツール

**デメリット:**
- **複雑性の増加**: Kubernetesの学習コストとメンテナンス負荷
- **運用コスト**: クラスター管理の追加作業
- **起動時間**: Cloud Runより若干遅い起動時間

### 移行戦略

1. **段階的移行**: dev → staging → prod の順番で移行
2. **並行運用**: 一定期間Cloud RunとKubernetesを並行運用
3. **ロールバック計画**: 問題発生時のCloud Run復旧手順

## 🏗️ アーキテクチャ比較

### 現在（Cloud Run）
```
GitHub Actions → Container Registry → Cloud Run Service
                                   ↓
                            Cloud Monitoring
```

### 移行後（Kubernetes）
```
GitHub Actions → Container Registry → Kubernetes Cluster
                                   ↓
                               Pod + Service + Ingress
                                   ↓
                            Prometheus/Cloud Monitoring
```

## 🚀 移行手順

### Phase 1: 環境準備

#### 1.1 GKEクラスター作成

```bash
# Terraformでクラスター作成
cd infra/envs/k8s-gke
terraform init
terraform plan
terraform apply

# kubectl設定
gcloud container clusters get-credentials crypto-bot-dev \
  --zone=asia-northeast1 \
  --project=your-project-id
```

#### 1.2 EKSクラスター作成（AWS使用の場合）

```bash
# Terraformでクラスター作成
cd infra/envs/k8s-eks
terraform init
terraform plan
terraform apply

# kubectl設定
aws eks update-kubeconfig \
  --region us-west-2 \
  --name crypto-bot-dev
```

### Phase 2: 設定とシークレットの移行

#### 2.1 Kubernetesシークレット作成

**GKEの場合:**
```bash
# Google Secret Managerから取得
kubectl create secret generic crypto-bot-secrets \
  --from-literal=bybit-testnet-api-key="$(gcloud secrets versions access latest --secret="bybit_testnet_api_key")" \
  --from-literal=bybit-testnet-api-secret="$(gcloud secrets versions access latest --secret="bybit_testnet_api_secret")" \
  --namespace=crypto-bot-dev
```

**EKSの場合:**
```bash
# AWS Secrets Managerから取得
kubectl create secret generic crypto-bot-secrets \
  --from-literal=bybit-testnet-api-key="$(aws secretsmanager get-secret-value --secret-id crypto-bot/bybit-testnet-api-key --query SecretString --output text)" \
  --from-literal=bybit-testnet-api-secret="$(aws secretsmanager get-secret-value --secret-id crypto-bot/bybit-testnet-api-secret --query SecretString --output text)" \
  --namespace=crypto-bot-dev
```

#### 2.2 設定の確認

```bash
# ConfigMapの内容確認
kubectl get configmap crypto-bot-config -n crypto-bot-dev -o yaml

# Secretの確認（値は表示されない）
kubectl get secret crypto-bot-secrets -n crypto-bot-dev -o yaml
```

### Phase 3: アプリケーションデプロイ

#### 3.1 Helmを使用したデプロイ

```bash
# Helm chartの検証
helm lint k8s/helm/crypto-bot

# 開発環境へのデプロイ
helm install crypto-bot k8s/helm/crypto-bot \
  --namespace crypto-bot-dev \
  --values k8s/helm/crypto-bot/values-dev.yaml \
  --set image.tag=latest

# デプロイ状況の確認
kubectl get pods -n crypto-bot-dev
kubectl logs -f deployment/crypto-bot -n crypto-bot-dev
```

#### 3.2 マニフェストを使用したデプロイ（代替方法）

```bash
# ネームスペース作成
kubectl apply -f k8s/manifests/namespace.yaml

# ConfigMapとSecret作成
kubectl apply -f k8s/manifests/configmap.yaml
kubectl apply -f k8s/manifests/secret.yaml

# ServiceAccountとRBAC
kubectl apply -f k8s/manifests/serviceaccount.yaml

# アプリケーションデプロイ
kubectl apply -f k8s/manifests/deployment.yaml
kubectl apply -f k8s/manifests/service.yaml

# オートスケーリング設定
kubectl apply -f k8s/manifests/hpa.yaml
kubectl apply -f k8s/manifests/pdb.yaml

# Ingress設定（外部アクセス用）
kubectl apply -f k8s/manifests/ingress.yaml
```

### Phase 4: 動作確認

#### 4.1 基本動作確認

```bash
# Pod状態確認
kubectl get pods -n crypto-bot-dev
kubectl describe pod -l app=crypto-bot -n crypto-bot-dev

# サービス確認
kubectl get svc -n crypto-bot-dev
kubectl port-forward svc/crypto-bot-service 8080:80 -n crypto-bot-dev

# ログ確認
kubectl logs -f deployment/crypto-bot -n crypto-bot-dev
```

#### 4.2 ヘルスチェック

```bash
# ヘルスエンドポイントテスト
curl http://localhost:8080/healthz
curl http://localhost:8080/ready

# メトリクス確認
curl http://localhost:8080/metrics
```

#### 4.3 スケーリングテスト

```bash
# 手動スケーリング
kubectl scale deployment crypto-bot --replicas=3 -n crypto-bot-dev

# HPAの確認
kubectl get hpa -n crypto-bot-dev

# 負荷テスト（オプション）
kubectl run -i --tty load-test --image=busybox --rm --restart=Never -- /bin/sh
# コンテナ内で: while true; do wget -q -O- http://crypto-bot-service.crypto-bot-dev.svc.cluster.local/healthz; done
```

### Phase 5: 監視設定

#### 5.1 Prometheus監視（オプション）

```bash
# Prometheus Operatorインストール
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# ServiceMonitor作成
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crypto-bot
  namespace: crypto-bot-dev
spec:
  selector:
    matchLabels:
      app: crypto-bot
  endpoints:
  - port: metrics
    path: /metrics
EOF
```

#### 5.2 ログ集約

**GKEの場合:**
```bash
# Cloud Loggingは自動で設定済み
kubectl logs deployment/crypto-bot -n crypto-bot-dev --tail=100
```

**EKSの場合:**
```bash
# Fluent Bitを使用したログ転送設定
helm repo add aws https://aws.github.io/eks-charts
helm install aws-for-fluent-bit aws/aws-for-fluent-bit \
  --namespace kube-system \
  --set cloudWatchLogs.region=us-west-2
```

### Phase 6: CI/CDの移行

#### 6.1 GitHub Actions設定

```bash
# 必要なシークレットを設定
gh secret set GCP_WIF_PROVIDER --body "projects/123/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
gh secret set GCP_CRYPTO_BOT_SA --body "crypto-bot-gke@project-id.iam.gserviceaccount.com"

# または EKS用
gh secret set AWS_DEPLOY_ROLE_ARN --body "arn:aws:iam::123456789012:role/crypto-bot-deploy-role"
gh secret set AWS_CRYPTO_BOT_ROLE_ARN --body "arn:aws:iam::123456789012:role/crypto-bot-eks-role"
```

#### 6.2 ワークフロー実行

```bash
# 手動デプロイ
gh workflow run "Kubernetes Deploy" \
  --field environment=dev \
  --field platform=gke
```

## 🔄 ロールバック計画

### Cloud Runへの緊急復旧

1. **Cloud Runサービス復活**
```bash
cd infra/envs/dev
terraform apply -target=google_cloud_run_service.service
```

2. **DNS切り替え**
```bash
# Ingressを無効化
kubectl patch ingress crypto-bot -n crypto-bot-dev \
  -p '{"spec":{"rules":[]}}'
```

3. **トラフィック検証**
```bash
curl https://your-cloud-run-url.run.app/healthz
```

### Kubernetesロールバック

```bash
# Helmリリースのロールバック
helm rollback crypto-bot -n crypto-bot-dev

# または直接的なイメージ変更
kubectl set image deployment/crypto-bot \
  crypto-bot=ghcr.io/nao-namake/crypto-bot:previous-tag \
  -n crypto-bot-dev
```

## 📊 パフォーマンス比較

### メトリクス監視項目

| 項目 | Cloud Run | Kubernetes | 備考 |
|------|-----------|------------|------|
| 起動時間 | ~2秒 | ~5-10秒 | Pod起動時間含む |
| メモリ使用量 | 512MB | 256-512MB | より細かい制御可能 |
| CPU使用量 | 1vCPU | 0.2-1vCPU | リクエストベース |
| スケーリング | ゼロスケール | 最小1Pod | HPAで調整可能 |
| コールドスタート | あり | なし（最小レプリカ維持） | レスポンス安定 |

### コスト比較

**Cloud Run（月額概算）:**
- 実行時間: 100時間 × $0.00002400 = $2.40
- メモリ: 512MB × 100時間 × $0.0000025 = $0.13
- リクエスト: 100万リクエスト × $0.0000004 = $0.40
- **合計: ~$3/月**

**GKE（月額概算）:**
- ノード: e2-standard-2 × 2台 × $50 = $100
- ディスク: 50GB × 2台 × $5 = $10
- 外部IP: $3
- **合計: ~$113/月**

**EKS（月額概算）:**
- コントロールプレーン: $73
- ノード: m5.large × 2台 × $70 = $140
- **合計: ~$213/月**

## ❗ 注意事項とベストプラクティス

### セキュリティ

1. **RBAC設定**
```bash
# 最小権限の原則
kubectl auth can-i get pods --as=system:serviceaccount:crypto-bot-dev:crypto-bot
```

2. **ネットワークポリシー**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: crypto-bot-netpol
spec:
  podSelector:
    matchLabels:
      app: crypto-bot
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
```

3. **シークレット管理**
```bash
# External Secrets Operatorの使用を推奨
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

### パフォーマンス最適化

1. **リソース設定**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "512Mi"
    cpu: "1000m"
```

2. **ヘルスチェック調整**
```yaml
livenessProbe:
  initialDelaySeconds: 60
  periodSeconds: 30
readinessProbe:
  initialDelaySeconds: 30
  periodSeconds: 10
```

3. **アフィニティ設定**
```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values: ["crypto-bot"]
        topologyKey: kubernetes.io/hostname
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. Pod起動失敗
```bash
# イベント確認
kubectl describe pod <pod-name> -n crypto-bot-dev

# よくある原因:
# - イメージプル失敗
# - シークレット不足
# - リソース不足
```

#### 2. シークレットアクセス失敗
```bash
# シークレット確認
kubectl get secret crypto-bot-secrets -n crypto-bot-dev -o yaml

# WorkloadIdentity確認（GKE）
kubectl annotate serviceaccount crypto-bot \
  iam.gke.io/gcp-service-account=crypto-bot-gke@project-id.iam.gserviceaccount.com \
  -n crypto-bot-dev
```

#### 3. ネットワーク接続問題
```bash
# DNS確認
kubectl run -i --tty --rm debug --image=busybox --restart=Never -- nslookup crypto-bot-service.crypto-bot-dev.svc.cluster.local

# 外部接続確認
kubectl exec -it deployment/crypto-bot -n crypto-bot-dev -- curl https://api.bybit.com/v2/public/time
```

#### 4. HPA動作しない
```bash
# Metrics Server確認
kubectl get deployment metrics-server -n kube-system

# メトリクス確認
kubectl top pods -n crypto-bot-dev
kubectl get hpa -n crypto-bot-dev
```

### デバッグコマンド集

```bash
# 包括的な状態確認
kubectl get all -n crypto-bot-dev

# ログ取得
kubectl logs -f deployment/crypto-bot -n crypto-bot-dev --tail=100

# イベント確認
kubectl get events -n crypto-bot-dev --sort-by='.lastTimestamp'

# リソース使用量確認
kubectl top pods -n crypto-bot-dev
kubectl top nodes

# エンドポイント確認
kubectl get endpoints -n crypto-bot-dev

# Ingress確認
kubectl describe ingress -n crypto-bot-dev
```

## 📚 参考資料

- [Kubernetes公式ドキュメント](https://kubernetes.io/docs/)
- [GKE公式ドキュメント](https://cloud.google.com/kubernetes-engine/docs)
- [EKS公式ドキュメント](https://docs.aws.amazon.com/eks/)
- [Helm公式ドキュメント](https://helm.sh/docs/)
- [kubectl チートシート](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

---

この移行ガイドを参考に、段階的かつ安全にKubernetesへの移行を進めてください。問題が発生した場合は、すぐにロールバック計画を実行し、安定運用を最優先してください。