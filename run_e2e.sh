#!/usr/bin/env bash
set -euo pipefail

# ── スクリプトが置いてあるディレクトリへ移動 ──
cd "$(cd "$(dirname "$0")" && pwd)"

# 仮想環境アクティベート
source .venv/bin/activate

# -- STEP 1) 環境変数チェック or .env から読み込み --
if [ -z "${BYBIT_TESTNET_API_KEY:-}" ] || [ -z "${BYBIT_TESTNET_API_SECRET:-}" ]; then
  if [ -f .env ]; then
    echo "→ Loading .env file"
    set -a
    source .env
    set +a
  fi
fi

# 最終チェック
if [ -z "${BYBIT_TESTNET_API_KEY:-}" ] || [ -z "${BYBIT_TESTNET_API_SECRET:-}" ]; then
  echo "❌ BYBIT_TESTNET_API_KEY/SECRET not set in ENV or .env"
  exit 1
fi

echo "→ BYBIT_TESTNET_API_KEY=${BYBIT_TESTNET_API_KEY:0:4}****"
echo "→ BYBIT_TESTNET_API_SECRET=${BYBIT_TESTNET_API_SECRET:0:4}****"

# -- STEP 2) E2E テスト実行 --
pytest tests/integration -q