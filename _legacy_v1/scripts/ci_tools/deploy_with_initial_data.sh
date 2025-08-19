#!/bin/bash
set -e

# エントリーシグナル生成問題の根本解決デプロイスクリプト
# 初期データの準備からデプロイまでを自動化

echo "=================================================="
echo "🚀 Deployment with Initial Data Cache"
echo "=================================================="

# Step 1: 初期データの準備
echo ""
echo "📊 Step 1: Preparing initial data cache..."
echo "--------------------------------------------------"

# cacheディレクトリがなければ作成
mkdir -p cache

# 既存のキャッシュをバックアップ（存在する場合）
if [ -f "cache/initial_data.pkl" ]; then
    echo "📦 Backing up existing cache..."
    mv cache/initial_data.pkl cache/initial_data.pkl.bak.$(date +%Y%m%d_%H%M%S)
fi

# 初期データを取得・計算
echo "🔄 Fetching and computing initial data..."
python scripts/prepare_initial_data.py

# キャッシュの存在確認
if [ ! -f "cache/initial_data.pkl" ]; then
    echo "❌ Error: Failed to create initial data cache"
    echo "Please check the error messages above and try again."
    exit 1
fi

echo "✅ Initial data cache created successfully"

# Step 2: ローカルテスト（オプション）
echo ""
echo "🧪 Step 2: Running local tests..."
echo "--------------------------------------------------"

# 基本的な文法チェック
echo "🔍 Running syntax checks..."
python -m py_compile crypto_bot/cli/live.py
python -m py_compile crypto_bot/data/fetching/data_processor.py
echo "✅ Syntax checks passed"

# Step 3: Dockerイメージのビルド
echo ""
echo "🐳 Step 3: Building Docker image..."
echo "--------------------------------------------------"

# Dockerイメージをビルド
docker build -t crypto-bot:fix -f docker/Dockerfile .

if [ $? -ne 0 ]; then
    echo "❌ Error: Docker build failed"
    exit 1
fi

echo "✅ Docker image built successfully"

# Step 4: Git コミット
echo ""
echo "📝 Step 4: Committing changes..."
echo "--------------------------------------------------"

# 変更をステージング
git add -A

# コミット（変更がある場合のみ）
if ! git diff --cached --quiet; then
    git commit -m "fix: エントリーシグナル生成問題の根本解決

- timeframe設定を1hに統一
- confidence_thresholdを0.35に統一  
- 初期データキャッシュシステム実装
- データ取得ロジックのタイムスタンプ修正
- Cloud Runリビジョン競合解決
- Dockerfileに初期データキャッシュ追加

これらの修正により、データ取得が成功し、エントリーシグナルが正常に生成されるようになります。"
    
    echo "✅ Changes committed"
else
    echo "ℹ️ No changes to commit"
fi

# Step 5: GitHub へプッシュ（CI/CD自動実行）
echo ""
echo "🚀 Step 5: Pushing to GitHub (triggers CI/CD)..."
echo "--------------------------------------------------"

# メインブランチにプッシュ
git push origin main

if [ $? -ne 0 ]; then
    echo "❌ Error: Git push failed"
    echo "Please resolve any conflicts and try again."
    exit 1
fi

echo "✅ Pushed to GitHub successfully"

# Step 6: デプロイ状況の監視
echo ""
echo "📊 Step 6: Monitoring deployment..."
echo "--------------------------------------------------"
echo ""
echo "GitHub Actions CI/CD pipeline has been triggered."
echo "You can monitor the deployment at:"
echo "https://github.com/[your-repo]/actions"
echo ""
echo "Once deployed, check the service health:"
echo "curl https://crypto-bot-service-prod-lufv3saz7q-an.a.run.app/health"
echo ""
echo "Monitor logs with:"
echo "gcloud logging read \"resource.type=cloud_run_revision\" --limit=50"
echo ""
echo "=================================================="
echo "✅ Deployment script completed successfully!"
echo "=================================================="