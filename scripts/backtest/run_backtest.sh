#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# バックテスト実行スクリプト - Phase 52.4
#
# 用途:
#   - バックテストを実行し、ログを src/backtest/logs/ に保存
#   - タイムスタンプ付きログファイル名で整理
#
# 使い方:
#   bash scripts/backtest/run_backtest.sh [ログ名接頭辞]
#
# 例:
#   bash scripts/backtest/run_backtest.sh           # デフォルト: backtest_YYYYMMDD_HHMMSS.log
#   bash scripts/backtest/run_backtest.sh phase52.4 # カスタム: phase52.4_YYYYMMDD_HHMMSS.log
# =============================================================================

# ログ保存ディレクトリ
LOG_DIR="src/backtest/logs"

# ログファイル名接頭辞（引数指定可能）
PREFIX="${1:-backtest}"

# タイムスタンプ生成（JST）
TIMESTAMP=$(TZ=Asia/Tokyo date +"%Y%m%d_%H%M%S")

# ログファイル名
LOG_FILE="${LOG_DIR}/${PREFIX}_${TIMESTAMP}.log"

echo "🚀 バックテスト実行開始"
echo "📂 ログ保存先: ${LOG_FILE}"
echo "================================================="
echo ""

# ロックファイル削除（残留対策・ユーザー非依存）
rm -f /tmp/crypto_bot_*.lock

# バックテスト実行（ログ保存）
python3 main.py --mode backtest 2>&1 | tee "${LOG_FILE}"

echo ""
echo "================================================="
echo "✅ バックテスト実行完了"
echo "📁 ログファイル: ${LOG_FILE}"
echo ""
