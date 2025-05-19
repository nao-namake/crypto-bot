#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 \"your commit message\""
  exit 1
fi

MSG="$1"
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# 必要なファイルをまとめてステージ
git add \
  scripts/run_e2e.sh \
  scripts/checks.sh \
  .github/workflows/ci.yml \
  crypto_bot/execution/bybit_client.py \
  tests/integration/bybit/test_bybit_e2e.py \
  tests/integration/main/test_main_e2e.py

git commit -m "${MSG}"

# リモート最新を rebase してプッシュ
git pull --rebase origin "${BRANCH}"
git push origin "${BRANCH}"

echo "→ committed and pushed to ${BRANCH}"
