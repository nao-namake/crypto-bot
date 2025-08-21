#!/bin/bash
# Phase 7 Docker統合エントリポイント
# レガシーシステム高度制御機能継承 + 新システムシンプル化

set -e

echo "🚀 Phase 7 Docker統合エントリポイント開始"
echo "📊 環境変数確認:"
echo "  MODE: ${MODE:-paper}"
echo "  LOG_LEVEL: ${LOG_LEVEL:-INFO}"
echo "  FEATURE_MODE: ${FEATURE_MODE:-basic}"
echo "  PYTHONPATH: ${PYTHONPATH:-/app}"
echo "  PORT: ${PORT:-8080}"
echo "  CI: ${CI:-false}"

# Phase 7: 基本ヘルスチェックサーバー起動（レガシーパターン継承）
echo "🌐 ヘルスチェックサーバー起動準備..."

# Phase 7簡易ヘルスチェックサーバー作成
cat > /app/health_server.py << 'EOF'
#!/usr/bin/env python3
"""
Phase 7 簡易ヘルスチェックサーバー
レガシーパターン継承・軽量実装
"""
import json
import http.server
import socketserver
import sys
import os
from datetime import datetime

PORT = int(os.environ.get('PORT', 8080))

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            try:
                # Phase 7基本ヘルスチェック
                sys.path.insert(0, '/app')
                from src.trading.executor import create_order_executor
                from src.core.config import load_config
                
                # 簡易動作確認
                executor = create_order_executor(mode='paper')
                config = load_config('config/core/base.yaml')
                
                health_data = {
                    "status": "healthy",
                    "phase": "7",
                    "mode": os.environ.get('MODE', 'paper'),
                    "timestamp": datetime.now().isoformat(),
                    "executor": "operational",
                    "config": "loaded"
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(health_data, indent=2).encode())
                
            except Exception as e:
                error_data = {
                    "status": "unhealthy", 
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_data, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # ログを最小限に（レガシー最適化）
        pass

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
        print(f"✅ ヘルスチェックサーバー起動: ポート {PORT}")
        httpd.serve_forever()
EOF

# 実行モード別処理（レガシー高度制御継承）
if [ "$MODE" = "live" ] && [ "$CI" != "true" ]; then
    echo "🎯 本番ライブトレード + ヘルスチェック統合モード"
    
    # ヘルスチェックサーバーをバックグラウンド起動
    echo "🌐 ヘルスチェックサーバーをバックグラウンド起動..."
    python3 /app/health_server.py &
    HEALTH_PID=$!
    echo "✅ ヘルスチェックサーバー起動完了 (PID: $HEALTH_PID)"
    
    # ヘルスチェックサーバー起動確認
    sleep 5
    
    # ライブトレードをフォアグラウンドで実行
    echo "🔄 ライブトレード起動..."
    python3 main.py --mode live --config config/production/production.yaml &
    TRADING_PID=$!
    echo "✅ ライブトレード起動完了 (PID: $TRADING_PID)"
    
elif [ "$MODE" = "paper" ]; then
    echo "📝 ペーパートレード + ヘルスチェック統合モード"
    
    # ヘルスチェックサーバーをバックグラウンド起動
    echo "🌐 ヘルスチェックサーバーをバックグラウンド起動..."
    python3 /app/health_server.py &
    HEALTH_PID=$!
    echo "✅ ヘルスチェックサーバー起動完了 (PID: $HEALTH_PID)"
    
    # ヘルスチェックサーバー起動確認
    sleep 5
    
    # ペーパートレードをフォアグラウンドで実行
    echo "🔄 ペーパートレード起動..."
    python3 main.py --mode paper --config config/core/base.yaml &
    TRADING_PID=$!
    echo "✅ ペーパートレード起動完了 (PID: $TRADING_PID)"
    
else
    echo "🧪 テスト・開発モード（シンプル起動）"
    
    # 直接起動（テスト・デバッグ用）
    exec "$@"
fi

# プロセス監視とシグナルハンドリング（レガシー高度制御継承）
if [ -n "$HEALTH_PID" ] && [ -n "$TRADING_PID" ]; then
    echo "👁️  プロセス監視開始..."
    
    # シグナルハンドリング設定
    trap 'echo "🛑 シグナル受信、プロセス停止..."; kill $HEALTH_PID $TRADING_PID 2>/dev/null; exit' SIGTERM SIGINT
    
    # プロセス監視ループ（レガシーパターン継承）
    while true; do
        # ヘルスチェックサーバーの生存確認
        if ! kill -0 $HEALTH_PID 2>/dev/null; then
            echo "❌ ヘルスチェックサーバーが停止しました"
            kill $TRADING_PID 2>/dev/null
            exit 1
        fi
        
        # トレーディングプロセスの生存確認
        if ! kill -0 $TRADING_PID 2>/dev/null; then
            echo "❌ トレーディングプロセスが停止しました"
            kill $HEALTH_PID 2>/dev/null
            exit 1
        fi
        
        # 30秒間隔で監視（リソース効率化）
        sleep 30
        
        # 定期ログ出力（24時間に1回）
        if [ $(($(date +%s) % 86400)) -lt 30 ]; then
            echo "📊 Phase 7システム稼働中 - $(date)"
            echo "  ヘルスチェックPID: $HEALTH_PID"
            echo "  トレーディングPID: $TRADING_PID"
        fi
    done
fi