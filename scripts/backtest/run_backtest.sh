#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# バックテスト実行スクリプト - Phase 57.11改修
#
# 機能:
#   - CSVデータ収集（Bitbank APIから履歴データ取得）
#   - 日数指定オプション（設定ファイル変更不要）
#   - Markdownレポート自動生成
#
# 使い方:
#   bash scripts/backtest/run_backtest.sh                    # 180日・CSV収集あり
#   bash scripts/backtest/run_backtest.sh --days 30          # 30日・CSV収集あり
#   bash scripts/backtest/run_backtest.sh --days 60 --skip-collect  # 60日・既存CSV使用
#   bash scripts/backtest/run_backtest.sh --prefix phase57   # カスタムログ名
# =============================================================================

# ログ保存ディレクトリ
LOG_DIR="src/backtest/logs"
mkdir -p "$LOG_DIR"

# デフォルト値
DAYS=180
PREFIX="backtest"
SKIP_COLLECT=false

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --prefix)
            PREFIX="$2"
            shift 2
            ;;
        --skip-collect)
            SKIP_COLLECT=true
            shift
            ;;
        --help|-h)
            echo "使い方: bash scripts/backtest/run_backtest.sh [オプション]"
            echo ""
            echo "オプション:"
            echo "  --days N         バックテスト日数（デフォルト: 180）"
            echo "  --prefix NAME    ログファイル名の接頭辞（デフォルト: backtest）"
            echo "  --skip-collect   CSVデータ収集をスキップ（既存データを使用）"
            echo "  --help, -h       このヘルプを表示"
            echo ""
            echo "例:"
            echo "  bash scripts/backtest/run_backtest.sh --days 30"
            echo "  bash scripts/backtest/run_backtest.sh --days 60 --skip-collect"
            exit 0
            ;;
        *)
            # 旧互換: 最初の引数はプレフィックス
            PREFIX="$1"
            shift
            ;;
    esac
done

# タイムスタンプ生成（JST）
TIMESTAMP=$(TZ=Asia/Tokyo date +"%Y%m%d_%H%M%S")

# ログファイル名
LOG_FILE="${LOG_DIR}/${PREFIX}_${TIMESTAMP}.log"

# 実行時間計測開始
SECONDS=0

echo "🚀 バックテスト実行開始（Phase 57.11）"
echo "📅 バックテスト期間: ${DAYS}日間"
echo "📂 ログ保存先: ${LOG_FILE}"
echo "================================================="
echo ""

# ロックファイル削除（残留対策）
rm -f /tmp/crypto_bot_nao.lock

# 設定ファイル復元用のtrap設定
CONFIG_FILE="config/core/thresholds.yaml"
CONFIG_BACKUP="${CONFIG_FILE}.bak"
cleanup() {
    if [ -f "$CONFIG_BACKUP" ]; then
        mv "$CONFIG_BACKUP" "$CONFIG_FILE"
        echo "⚠️ 設定ファイル復元完了"
    fi
}
trap cleanup EXIT

# Step 1: CSVデータ収集
if [ "$SKIP_COLLECT" = false ]; then
    echo "📥 Step 1: CSVデータ収集開始（${DAYS}日間）..."
    python3 src/backtest/scripts/collect_historical_csv.py --days "$DAYS"

    # データ収集確認
    if [ -f "src/backtest/data/historical/BTC_JPY_15m.csv" ]; then
        CSV_LINES=$(wc -l < src/backtest/data/historical/BTC_JPY_15m.csv)
        echo "✅ 15分足データ収集完了: ${CSV_LINES}行"
    else
        echo "❌ 15分足データ収集失敗"
        exit 1
    fi
    echo ""
else
    echo "⏭️ Step 1: CSVデータ収集スキップ（--skip-collect指定）"
    echo ""
fi

# Step 2: 設定ファイルの日数を一時変更
echo "⚙️ Step 2: バックテスト期間設定（${DAYS}日間）..."
cp "$CONFIG_FILE" "$CONFIG_BACKUP"
sed -i.tmp "s/backtest_period_days:.*/backtest_period_days: ${DAYS}  # Phase 57.11: スクリプト指定/" "$CONFIG_FILE"
rm -f "${CONFIG_FILE}.tmp"
echo "✅ 設定ファイル更新完了"
echo ""

# Step 3: バックテスト実行
echo "🔄 Step 3: バックテスト実行中..."
python3 main.py --mode backtest 2>&1 | tee "${LOG_FILE}"
BACKTEST_EXIT_CODE=${PIPESTATUS[0]}
echo ""

# Step 4: 設定ファイル復元
echo "🔧 Step 4: 設定ファイル復元..."
mv "$CONFIG_BACKUP" "$CONFIG_FILE"
trap - EXIT  # trapを解除
echo "✅ 設定ファイル復元完了"
echo ""

# バックテスト失敗時は終了
if [ $BACKTEST_EXIT_CODE -ne 0 ]; then
    echo "❌ バックテスト実行失敗（終了コード: $BACKTEST_EXIT_CODE）"
    exit $BACKTEST_EXIT_CODE
fi

# Step 5: Markdownレポート生成
echo "📝 Step 5: Markdownレポート生成..."
LATEST_JSON=$(ls -t src/backtest/logs/backtest_*.json 2>/dev/null | head -1)
if [ -n "$LATEST_JSON" ]; then
    python3 scripts/backtest/generate_markdown_report.py "$LATEST_JSON"
    LATEST_MD=$(ls -t docs/検証記録/backtest_*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_MD" ]; then
        echo "✅ Markdownレポート生成完了: $LATEST_MD"
    fi
else
    echo "⚠️ JSONレポートが見つかりません（Markdownレポート生成スキップ）"
fi

# 実行時間計算
ELAPSED=$SECONDS
MINUTES=$((ELAPSED / 60))
SECS=$((ELAPSED % 60))

echo ""
echo "================================================="
echo "✅ バックテスト実行完了"
echo "📁 ログファイル: ${LOG_FILE}"
echo "📊 バックテスト期間: ${DAYS}日間"
if [ -n "${LATEST_MD:-}" ]; then
    echo "📝 レポート: ${LATEST_MD}"
fi
echo "⏱️ 実行時間: ${MINUTES}分${SECS}秒"
echo ""
