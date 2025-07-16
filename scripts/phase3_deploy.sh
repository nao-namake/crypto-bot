#!/bin/bash
# Phase 3.1: 段階的デプロイメント実行スクリプト

set -e

echo "🚀 Phase 3.1: 段階的デプロイメント・包括的テスト実行開始"
echo "================================================================"

# Phase 3.1a: ローカル品質チェック
echo "🔍 Phase 3.1a: ローカル品質チェック"
echo "================================"

# Python構文チェック
echo "📝 Python構文チェック..."
python3 -m py_compile crypto_bot/init_enhanced.py
python3 -m py_compile crypto_bot/main.py
echo "✅ Python構文チェック完了"

# blackフォーマットチェック
echo "🎨 blackフォーマットチェック..."
python3 -m black crypto_bot/init_enhanced.py
echo "✅ blackフォーマット完了"

# isortチェック
echo "📚 isortチェック..."
python3 -m isort crypto_bot/init_enhanced.py
echo "✅ isort完了"

# flake8チェック
echo "🔍 flake8チェック..."
python3 -m flake8 crypto_bot/init_enhanced.py --max-line-length=100
echo "✅ flake8チェック完了"

# Phase 3.1b: 基本テスト実行
echo ""
echo "🧪 Phase 3.1b: 基本テスト実行"
echo "============================="

# インポートテスト
echo "📦 インポートテスト..."
python3 -c "from crypto_bot.init_enhanced import enhanced_init_sequence; print('✅ init_enhanced.py import successful')"

# yfinance依存関係テスト
echo "📊 yfinance依存関係テスト..."
python3 -c "import yfinance; print('✅ yfinance available')"

# Phase 3.1c: AMD64イメージビルド
echo ""
echo "🏗️ Phase 3.1c: AMD64イメージビルド"
echo "================================"

# Docker buildx設定確認
echo "🔧 Docker buildx設定確認..."
docker buildx ls

# AMD64イメージビルド
BUILD_TAG="phase3-complete-$(date +%s)"
echo "🏗️ AMD64イメージビルド (tag: $BUILD_TAG)..."
docker buildx build --platform linux/amd64 -t gcr.io/crypto-bot-prod/$BUILD_TAG --load .

# イメージ検証
echo "🔍 イメージ検証..."
docker run --rm gcr.io/crypto-bot-prod/$BUILD_TAG python3 -c "from crypto_bot.init_enhanced import enhanced_init_sequence; print('✅ Image verification successful')"

# Phase 3.1d: 開発環境デプロイ
echo ""
echo "🚀 Phase 3.1d: 開発環境デプロイ"
echo "==============================="

# 開発環境デプロイ
echo "📤 開発環境デプロイ..."
gcloud run deploy crypto-bot-service-dev \
  --image gcr.io/crypto-bot-prod/$BUILD_TAG \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated

# 開発環境ヘルスチェック
echo "🏥 開発環境ヘルスチェック..."
sleep 30
curl -f https://crypto-bot-service-dev-11445303925.asia-northeast1.run.app/health
echo "✅ 開発環境ヘルスチェック完了"

# Phase 3.1e: 本番環境デプロイ
echo ""
echo "🌟 Phase 3.1e: 本番環境デプロイ"
echo "==============================="

# 本番環境デプロイ
echo "📤 本番環境デプロイ..."
gcloud run deploy crypto-bot-service-prod \
  --image gcr.io/crypto-bot-prod/$BUILD_TAG \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated

# 本番環境ヘルスチェック
echo "🏥 本番環境ヘルスチェック..."
sleep 30
curl -f https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health
echo "✅ 本番環境ヘルスチェック完了"

# Phase 3.1f: 包括的テスト実行
echo ""
echo "🔬 Phase 3.1f: 包括的テスト実行"
echo "==============================="

# API機能テスト
echo "🌐 API機能テスト..."
echo "- ヘルスチェックAPI"
curl -f https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health

echo "- 詳細ヘルスチェックAPI"
curl -f https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health/detailed

echo "- パフォーマンスメトリクスAPI"
curl -f https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health/performance

echo "- Prometheusメトリクス"
curl -f https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/metrics

# ログ検証
echo "📋 ログ検証..."
gcloud logging read "resource.labels.service_name=crypto-bot-service-prod" --limit=10

echo ""
echo "🎉 Phase 3.1: 段階的デプロイメント・包括的テスト実行が完了しました!"
echo "================================================================"
echo ""
echo "📊 デプロイメント完了サマリー:"
echo "- ローカル品質チェック: ✅ 完了"
echo "- 基本テスト: ✅ 完了"
echo "- AMD64イメージビルド: ✅ 完了"
echo "- 開発環境デプロイ: ✅ 完了"
echo "- 本番環境デプロイ: ✅ 完了"
echo "- 包括的テスト: ✅ 完了"
echo ""
echo "🔗 本番環境URL: https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health"
echo "🏗️ 使用したイメージ: gcr.io/crypto-bot-prod/$BUILD_TAG"