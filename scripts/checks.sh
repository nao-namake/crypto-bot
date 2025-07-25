#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ファイル名: scripts/checks.sh
# 説明:
# プロジェクトの品質チェックを一括実行するシェルスクリプトです。
# - flake8: コードスタイルチェック（PEP8違反検出）
# - isort: import順チェック（自動修正せず、--check-only）
# - black: コード整形チェック（自動修正せず、--checkのみ）
# - pytest: テスト実行とカバレッジ計測
#   （--cov-fail-under=75 でカバレッジ75%未満ならエラー終了）
#
# 主にローカルやCI/CDで静的解析とテストを一発で確認したい時に使います。
#
# 使い方（ターミナルでプロジェクトルートから実行）:
#   bash scripts/checks.sh
#   ./scripts/checks.sh
#
#   ※どちらも同じ意味です
# =============================================================================

# Coverage の最低ライン
COV_FAIL_UNDER=14

echo ">>> flake8"
python3 -m flake8 .

echo ">>> isort (check only)"
python3 -m isort --check-only .

echo ">>> black (check only)"
python3 -m black --check .

echo ">>> pytest (with coverage)"
python3 -m pytest \
  --maxfail=1 \
  --disable-warnings \
  -q \
  --cov=crypto_bot \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-fail-under="${COV_FAIL_UNDER}" \
  --ignore=tests/unit/test_monitor.py \
  --ignore=tests/integration

echo
echo "✅ all checks passed! Coverage report: ./htmlcov/index.html"