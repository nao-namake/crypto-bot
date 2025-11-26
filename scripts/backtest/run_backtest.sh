#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# バックテスト実行スクリプト - Phase 55.2
#
# 用途:
#   - オプションでデータ自動収集機能追加（CSVヘッダー問題解消）
#   - バックテストを実行し、ログを src/backtest/logs/ に保存
#   - タイムスタンプ付きログファイル名で整理
#   - リアルタイム進捗表示機能（--progress オプション）
#
# 使い方:
#   bash scripts/backtest/run_backtest.sh [オプション] [ログ名接頭辞]
#
# オプション:
#   --days <日数>        指定期間のデータを自動収集してからバックテスト実行
#   --collect-only       データ収集のみ実行（バックテスト省略）
#   --progress           リアルタイム進捗表示（30秒間隔）
#
# 例:
#   bash scripts/backtest/run_backtest.sh                           # デフォルト（データ収集なし）
#   bash scripts/backtest/run_backtest.sh phase54                   # カスタムログ名
#   bash scripts/backtest/run_backtest.sh --days 7                  # 7日間データ自動収集 → バックテスト
#   bash scripts/backtest/run_backtest.sh --days 30 phase54_30days # 30日間 + カスタムログ名
#   bash scripts/backtest/run_backtest.sh --days 180 --collect-only # データ収集のみ
#   bash scripts/backtest/run_backtest.sh --days 30 --progress      # 進捗表示付き
# =============================================================================

# デフォルト値
PREFIX="backtest"
DAYS=""
COLLECT_ONLY=false
SHOW_PROGRESS=false

# 引数解析
while [[ $# -gt 0 ]]; do
  case $1 in
    --days)
      DAYS="$2"
      shift 2
      ;;
    --collect-only)
      COLLECT_ONLY=true
      shift
      ;;
    --progress)
      SHOW_PROGRESS=true
      shift
      ;;
    *)
      # オプション以外は接頭辞として扱う
      PREFIX="$1"
      shift
      ;;
  esac
done

# ログ保存ディレクトリ
LOG_DIR="src/backtest/logs"

# タイムスタンプ生成（JST）
TIMESTAMP=$(TZ=Asia/Tokyo date +"%Y%m%d_%H%M%S")

# ログファイル名
LOG_FILE="${LOG_DIR}/${PREFIX}_${TIMESTAMP}.log"

echo "🚀 バックテスト実行スクリプト開始"
echo "================================================="

# データ収集（--days指定時）
if [[ -n "$DAYS" ]]; then
  echo ""
  echo "📊 データ収集開始: ${DAYS}日間"
  echo "📂 収集先: src/backtest/data/historical/"
  echo ""

  # collect_historical_csv.py実行
  if python3 src/backtest/scripts/collect_historical_csv.py --days "$DAYS"; then
    echo ""
    echo "✅ データ収集完了"
  else
    echo ""
    echo "❌ データ収集失敗: collect_historical_csv.py実行エラー"
    exit 1
  fi
fi

# データ収集のみの場合はここで終了
if [[ "$COLLECT_ONLY" == true ]]; then
  echo ""
  echo "================================================="
  echo "✅ データ収集完了（--collect-onlyモード）"
  echo "📁 データ保存先: src/backtest/data/historical/"
  echo ""
  exit 0
fi

# バックテスト実行
echo ""
echo "🎯 バックテスト実行開始"
echo "📂 ログ保存先: ${LOG_FILE}"
echo "================================================="
echo ""

# ロックファイル削除（残留対策・ユーザー非依存）
rm -f /tmp/crypto_bot_*.lock

# 進捗監視関数
show_progress() {
  local log_file="$1"
  local interval=30  # 30秒間隔

  while true; do
    sleep "$interval"

    # プロセスが終了していたら監視終了
    if ! ps -p "$BACKTEST_PID" > /dev/null 2>&1; then
      break
    fi

    # ログファイルから最新の進捗を取得
    if [[ -f "$log_file" ]]; then
      local progress_line
      progress_line=$(grep "バックテスト進行中:" "$log_file" 2>/dev/null | tail -1)
      if [[ -n "$progress_line" ]]; then
        # 進捗情報を抽出して表示
        local progress
        progress=$(echo "$progress_line" | grep -oE '[0-9]+\.[0-9]+%' | head -1)
        local current
        current=$(echo "$progress_line" | grep -oE '\([0-9]+/[0-9]+\)' | head -1)
        local remaining
        remaining=$(echo "$progress_line" | grep -oE '残り時間: [0-9]+時間[0-9]+分' | head -1)

        echo ""
        echo "📊 進捗: ${progress:-N/A} ${current:-} ${remaining:-}"
      fi
    fi
  done
}

# バックテスト実行
if [[ "$SHOW_PROGRESS" == true ]]; then
  echo "📈 進捗表示モード: 30秒間隔で進捗を表示します"
  echo ""

  # バックグラウンドで実行してPIDを取得（--days指定時は環境変数で渡す）
  if [[ -n "$DAYS" ]]; then
    BACKTEST_DAYS="$DAYS" python3 main.py --mode backtest > "${LOG_FILE}" 2>&1 &
  else
    python3 main.py --mode backtest > "${LOG_FILE}" 2>&1 &
  fi
  BACKTEST_PID=$!

  # 進捗監視をバックグラウンドで開始
  show_progress "${LOG_FILE}" &
  PROGRESS_PID=$!

  # バックテスト完了を待機
  wait "$BACKTEST_PID"
  BACKTEST_EXIT_CODE=$?

  # 進捗監視を終了
  kill "$PROGRESS_PID" 2>/dev/null || true

  # 最終ログ表示
  echo ""
  echo "📝 最終ログ（直近50行）:"
  tail -50 "${LOG_FILE}"

  if [[ "$BACKTEST_EXIT_CODE" -ne 0 ]]; then
    echo ""
    echo "❌ バックテストがエラーで終了しました（終了コード: $BACKTEST_EXIT_CODE）"
    exit "$BACKTEST_EXIT_CODE"
  fi
else
  # 従来モード（リアルタイム出力）（--days指定時は環境変数で渡す）
  if [[ -n "$DAYS" ]]; then
    BACKTEST_DAYS="$DAYS" python3 main.py --mode backtest 2>&1 | tee "${LOG_FILE}"
  else
    python3 main.py --mode backtest 2>&1 | tee "${LOG_FILE}"
  fi
fi

echo ""
echo "================================================="
echo "✅ バックテスト実行完了"
echo "📁 ログファイル: ${LOG_FILE}"

# 結果サマリー表示
if [[ -f "${LOG_FILE}" ]]; then
  echo ""
  echo "📊 結果サマリー:"
  BUY_COUNT=$(grep -c "サイド: BUY" "${LOG_FILE}" 2>/dev/null || echo "0")
  SELL_COUNT=$(grep -c "サイド: SELL" "${LOG_FILE}" 2>/dev/null || echo "0")
  TP_COUNT=$(grep -c "TP決済損益" "${LOG_FILE}" 2>/dev/null || echo "0")
  SL_COUNT=$(grep -c "SL決済損益" "${LOG_FILE}" 2>/dev/null || echo "0")

  echo "  📈 BUY注文: ${BUY_COUNT}回"
  echo "  📉 SELL注文: ${SELL_COUNT}回"
  echo "  ✅ TP決済: ${TP_COUNT}回"
  echo "  ❌ SL決済: ${SL_COUNT}回"
  echo "  📊 合計取引: $((BUY_COUNT + SELL_COUNT))回"

  # 最終残高を表示
  FINAL_BALANCE=$(grep "残高:" "${LOG_FILE}" 2>/dev/null | tail -1 | grep -oE '¥[0-9,]+' | tail -1)
  if [[ -n "$FINAL_BALANCE" ]]; then
    echo "  💰 最終残高: ${FINAL_BALANCE}"
  fi
fi

echo ""
