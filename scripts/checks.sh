#!/usr/bin/env bash
set -euo pipefail

# Coverage の最低ライン
COV_FAIL_UNDER=75

# --fix オプションで isort/black を自動適用
FIX_MODE=false
if [[ "${1:-}" == "--fix" ]]; then
  FIX_MODE=true
fi

echo ">>> flake8"
flake8 .

if $FIX_MODE; then
  echo ">>> isort (applying fixes)"
  isort .
  echo ">>> black (applying fixes)"
  black .
else
  echo ">>> isort (check only)"
  isort --check-only .
  echo ">>> black (check only)"
  black --check .
fi

echo ">>> pytest (with coverage)"
pytest \
  --maxfail=1 \
  --disable-warnings \
  -q \
  --cov=crypto_bot \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-fail-under="${COV_FAIL_UNDER}"

echo
echo "✅ all checks passed! Coverage report: ./htmlcov/index.html"
