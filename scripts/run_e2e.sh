#!/usr/bin/env bash
set -euo pipefail

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
