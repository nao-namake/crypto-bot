#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ファイル名: scripts/run_e2e.sh
# 説明:
# エンドツーエンド（E2E）テストを自動実行するスクリプトです。
# - プロジェクトルートに移動し、.venvがあれば仮想環境を有効化
# - .envファイルからAPIキー等の環境変数を読み込み
# - BYBIT_TESTNET_API_KEY/SECRETの存在チェック（未設定ならエラーで停止）
# - tests/integration ディレクトリ配下のテスト（pytest）を実行
#
# 【用途】
#   - Bybit Testnet APIキーを使った本番同等の動作検証
#   - 環境構築やAPI設定確認の自動化
#   - CI/CDやローカルでの総合テスト
#
# 【使い方例】（プロジェクトルートで実行）
#   bash scripts/run_e2e.sh
#   ./scripts/run_e2e.sh
# =============================================================================

# スクリプト自身のあるディレクトリへ移動
cd "$(cd "$(dirname "$0")" && pwd)/.."

# 仮想環境アクティベート (.venv がルート直下にある想定)
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

# — STEP 1) 環境変数読み込み —
if [ -f .env ] && { [ -z "${BYBIT_TESTNET_API_KEY:-}" ] || [ -z "${BYBIT_TESTNET_API_SECRET:-}" ]; }; then
  echo "→ Loading .env"
  set -a
  source .env
  set +a
fi

# 最終チェック
if [ -z "${BYBIT_TESTNET_API_KEY:-}" ] || [ -z "${BYBIT_TESTNET_API_SECRET:-}" ]; then
  echo "❌ BYBIT_TESTNET_API_KEY/SECRET not set"
  exit 1
fi

echo "→ BYBIT_TESTNET_API_KEY=${BYBIT_TESTNET_API_KEY:0:4}****"
echo "→ BYBIT_TESTNET_API_SECRET=${BYBIT_TESTNET_API_SECRET:0:4}****"

# — STEP 2) E2E テスト実行 —
# tests/integration 以下を再帰的に拾う
pytest tests/integration -q