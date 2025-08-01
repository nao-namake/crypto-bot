#!/bin/bash
# Docker統合エントリポイント - Phase H.28対応
# APIサーバー常時起動 + ライブトレード統合制御

set -e

echo "🚀 Phase H.28 Docker統合エントリポイント開始"
echo "📊 環境変数確認:"
echo "  MODE: ${MODE:-not_set}"
echo "  CI: ${CI:-not_set}"
echo "  API_ONLY_MODE: ${API_ONLY_MODE:-not_set}"
echo "  FEATURE_MODE: ${FEATURE_MODE:-not_set}"

echo "🌐 APIサーバー起動準備..."

# 本番環境（MODE=live）でライブトレード統合
if [ "$MODE" = "live" ] && [ "$CI" != "true" ]; then
    echo "🎯 本番ライブトレード + APIサーバー統合モード"
    
    # まずAPIサーバーをバックグラウンド起動（ヘルスチェック対応）
    echo "🌐 APIサーバーをバックグラウンド起動..."
    python -m crypto_bot.api.server &
    API_PID=$!
    echo "✅ APIサーバー起動完了 (PID: $API_PID)"
    
    # APIサーバー起動確認
    sleep 10
    
    # ライブトレードをフォアグラウンドで実行
    echo "🔄 ライブトレード起動..."
    exec python -m crypto_bot.main live-bitbank --config config/production/production.yml
    
elif [ "$CI" = "true" ] || [ "$API_ONLY_MODE" = "true" ]; then
    echo "🧪 CI/テスト環境 - API-onlyモード"
    exec python -m crypto_bot.api.server
    
else
    echo "🌐 デフォルト - APIサーバーのみ起動"
    exec python -m crypto_bot.api.server
fi