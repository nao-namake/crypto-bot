#!/bin/bash
# Phase 13 Docker統合エントリポイント
# 607テスト・54%カバレッジ・統合最適化完了

set -e

echo "🚀 Phase 13 Docker統合エントリポイント開始"
echo "📊 環境変数確認:"
echo "  MODE: ${MODE:-paper}"
echo "  LOG_LEVEL: ${LOG_LEVEL:-INFO}"
echo "  FEATURE_MODE: ${FEATURE_MODE:-full}"
echo "  PYTHONPATH: ${PYTHONPATH:-/app}"
echo "  PORT: ${PORT:-8080}"
echo "  CI: ${CI:-false}"

# Phase 13: 基本ヘルスチェックサーバー起動（統合最適化）
echo "🌐 ヘルスチェックサーバー起動準備..."

# Phase 13: 起動時MLモデルチェック（607テスト対応・簡素化）
echo "🤖 起動時MLモデル検証実行..."
python3 -c "
import sys
sys.path.insert(0, '/app')

try:
    from src.core.orchestration.ml_adapter import MLServiceAdapter
    from src.core.logger import get_logger
    
    logger = get_logger('startup_check')
    adapter = MLServiceAdapter(logger)
    
    if adapter.is_fitted:
        model_info = adapter.get_model_info()
        print(f'✅ MLモデル初期化成功: {model_info[\"model_type\"]}')
        
        # 簡易予測テスト（12特徴量）
        import numpy as np
        test_features = np.random.random((1, 12))
        prediction = adapter.predict(test_features)
        
        print(f'✅ 予測テスト成功: prediction={prediction[0]}')
        logger.info('✅ 起動時モデル検証成功')
    else:
        print('⚠️ MLモデル未学習 - ダミーモードで継続')
        logger.warning('⚠️ ダミーモード稼働')
        
except ImportError as e:
    print(f'❌ Phase 18リファクタリング後のimportエラー: {str(e)}')
    print(f'⚠️ MLモジュール読み込み失敗 - ダミーモードで継続')
    logger.error(f'Phase 18 import修正後もエラー: {e}')
except Exception as e:
    print(f'⚠️ MLモデル検証エラー: {str(e)[:100]}...')
    print(f'⚠️ エラー詳細: {type(e).__name__}')
    print('⚠️ エラーが発生しましたが稼働を継続します')
    import traceback
    print(f'📊 スタックトレース: {traceback.format_exc()[:200]}...')
"

if [ $? -ne 0 ]; then
    echo "⚠️ MLモデル検証で問題検出 - 稼働継続（運用中修復対応）"
fi

# Phase 13簡易ヘルスチェックサーバー作成
cat > /app/health_server.py << 'EOF'
#!/usr/bin/env python3
"""
Phase 13 簡易ヘルスチェックサーバー
607テスト・54%カバレッジ・統合最適化対応
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
                # Phase 13基本ヘルスチェック
                sys.path.insert(0, '/app')
                from src.trading.executor import create_order_executor
                from src.core.config import load_config
                
                # 動的設定ファイル解決（環境に応じた最適化）
                mode = os.environ.get('MODE', 'paper')
                config_file = f'config/production/production.yaml' if mode == 'live' else 'config/core/base.yaml'
                
                config = load_config(config_file)
                executor = create_order_executor(mode=mode)
                
                health_data = {
                    "status": "healthy",
                    "phase": "13",
                    "mode": mode,
                    "timestamp": datetime.now().isoformat(),
                    "executor": "operational",
                    "config": f"loaded({config_file})"
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
        elif self.path == '/':
            # 基本動作確認エンドポイント
            basic_info = {
                "service": "crypto-bot-service-prod",
                "version": "Phase 13 完了",
                "status": "operational",
                "timestamp": datetime.now().isoformat(),
                "mode": os.environ.get('MODE', 'paper'),
                "health_endpoint": "/health"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(basic_info, indent=2).encode())
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
    
    # ライブトレードをバックグラウンドで実行
    echo "🔄 ライブトレード起動..."
    python3 main.py --mode live --config config/production/production.yaml &
    TRADING_PID=$!
    echo "✅ ライブトレード起動完了 (PID: $TRADING_PID)"
    
    # 🚨 CRITICAL FIX: 起動エラーチェック追加
    sleep 3
    if ! kill -0 $TRADING_PID 2>/dev/null; then
        echo "❌ ライブトレードプロセス起動直後に失敗"
        kill $HEALTH_PID 2>/dev/null
        exit 1
    fi
    
elif [ "$MODE" = "paper" ]; then
    echo "📝 ペーパートレード + ヘルスチェック統合モード"
    
    # ヘルスチェックサーバーをバックグラウンド起動
    echo "🌐 ヘルスチェックサーバーをバックグラウンド起動..."
    python3 /app/health_server.py &
    HEALTH_PID=$!
    echo "✅ ヘルスチェックサーバー起動完了 (PID: $HEALTH_PID)"
    
    # ヘルスチェックサーバー起動確認
    sleep 5
    
    # ペーパートレードをバックグラウンドで実行
    echo "🔄 ペーパートレード起動..."
    python3 main.py --mode paper --config config/core/base.yaml &
    TRADING_PID=$!
    echo "✅ ペーパートレード起動完了 (PID: $TRADING_PID)"
    
    # 🚨 CRITICAL FIX: 起動エラーチェック追加
    sleep 3
    if ! kill -0 $TRADING_PID 2>/dev/null; then
        echo "❌ ペーパートレードプロセス起動直後に失敗"
        kill $HEALTH_PID 2>/dev/null
        exit 1
    fi
    
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
    
    # 🚨 CRITICAL FIX: プロセス監視ループ強化（早期エラー検出）
    cycle_count=0
    while true; do
        cycle_count=$((cycle_count + 1))
        
        # ヘルスチェックサーバーの生存確認
        if ! kill -0 $HEALTH_PID 2>/dev/null; then
            echo "❌ [$(date)] ヘルスチェックサーバーが停止しました (サイクル: $cycle_count)"
            kill $TRADING_PID 2>/dev/null
            exit 1
        fi
        
        # トレーディングプロセスの生存確認
        if ! kill -0 $TRADING_PID 2>/dev/null; then
            echo "❌ [$(date)] トレーディングプロセスが停止しました (サイクル: $cycle_count)"
            kill $HEALTH_PID 2>/dev/null
            exit 1
        fi
        
        # 10秒間隔で監視（早期エラー検出優先）
        sleep 10
        
        # 定期ログ出力（1時間に1回 = 360サイクル）
        if [ $((cycle_count % 360)) -eq 0 ]; then
            echo "📊 システム稼働中 - $(date) [サイクル: $cycle_count]"
            echo "  ヘルスチェックPID: $HEALTH_PID (生存確認済み)"
            echo "  トレーディングPID: $TRADING_PID (生存確認済み)"
        fi
    done
fi