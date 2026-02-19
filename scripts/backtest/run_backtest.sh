#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# バックテスト実行スクリプト - Phase 61
#
# 機能:
#   - CSVデータ収集（Bitbank APIから履歴データ取得）
#   - 明確な期間指定（コマンドライン優先、未指定時は設定ファイル参照）
#   - Markdownレポート自動生成
#
# 使い方:
#   # コマンドライン指定（優先）
#   bash scripts/backtest/run_backtest.sh --days 10           # 直近10日間
#   bash scripts/backtest/run_backtest.sh --days 30           # 直近30日間
#   bash scripts/backtest/run_backtest.sh --start 2025-07-01 --end 2025-12-31  # 固定期間
#
#   # 設定ファイル参照（コマンドライン未指定時）
#   bash scripts/backtest/run_backtest.sh                     # thresholds.yaml参照
#
#   # その他オプション
#   bash scripts/backtest/run_backtest.sh --skip-collect      # 既存CSV使用
#   bash scripts/backtest/run_backtest.sh --prefix phase59    # カスタムログ名
#
# 期間指定の優先順位:
#   1. --start/--end（固定期間・最優先）
#   2. --days（ローリングウィンドウ）
#   3. thresholds.yaml（デフォルト）
# =============================================================================

# ログ保存ディレクトリ
LOG_DIR="logs/backtest"
mkdir -p "$LOG_DIR"

# デフォルト値
DAYS=""
START_DATE=""
END_DATE=""
PREFIX="backtest"
SKIP_COLLECT=false
PERIOD_SPECIFIED=false

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            PERIOD_SPECIFIED=true
            shift 2
            ;;
        --start)
            START_DATE="$2"
            PERIOD_SPECIFIED=true
            shift 2
            ;;
        --end)
            END_DATE="$2"
            PERIOD_SPECIFIED=true
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
            echo "期間指定オプション（優先順位順）:"
            echo "  --start DATE     開始日（YYYY-MM-DD形式）"
            echo "  --end DATE       終了日（YYYY-MM-DD形式）"
            echo "  --days N         直近N日間（ローリングウィンドウ）"
            echo ""
            echo "その他オプション:"
            echo "  --prefix NAME    ログファイル名の接頭辞（デフォルト: backtest）"
            echo "  --skip-collect   CSVデータ収集をスキップ（既存データを使用）"
            echo "  --help, -h       このヘルプを表示"
            echo ""
            echo "例:"
            echo "  bash scripts/backtest/run_backtest.sh --days 10              # 直近10日間"
            echo "  bash scripts/backtest/run_backtest.sh --days 180             # 直近180日間"
            echo "  bash scripts/backtest/run_backtest.sh --start 2025-07-01 --end 2025-12-31"
            echo "  bash scripts/backtest/run_backtest.sh                        # 設定ファイル参照"
            exit 0
            ;;
        *)
            echo "⚠️ 不明なオプション: $1"
            echo "ヘルプ: bash scripts/backtest/run_backtest.sh --help"
            exit 1
            ;;
    esac
done

# 期間決定ロジック
if [ -n "$START_DATE" ] && [ -n "$END_DATE" ]; then
    # --start/--end 指定: 固定期間モード
    MODE="fixed"
    PERIOD_DESC="${START_DATE} ~ ${END_DATE}"
elif [ -n "$DAYS" ]; then
    # --days 指定: ローリングウィンドウモード
    MODE="rolling"
    PERIOD_DESC="直近${DAYS}日間"
else
    # 未指定: 設定ファイルから読み込み
    MODE=$(python3 -c "
import yaml
with open('config/core/thresholds.yaml') as f:
    config = yaml.safe_load(f)
if config.get('execution', {}).get('backtest_use_fixed_dates', False):
    print('fixed')
else:
    print('rolling')
")
    if [ "$MODE" = "fixed" ]; then
        START_DATE=$(python3 -c "
import yaml
with open('config/core/thresholds.yaml') as f:
    config = yaml.safe_load(f)
print(config.get('execution', {}).get('backtest_start_date', '2025-07-01'))
")
        END_DATE=$(python3 -c "
import yaml
with open('config/core/thresholds.yaml') as f:
    config = yaml.safe_load(f)
print(config.get('execution', {}).get('backtest_end_date', '2025-12-31'))
")
        PERIOD_DESC="${START_DATE} ~ ${END_DATE}（設定ファイル）"
    else
        DAYS=$(python3 -c "
import yaml
with open('config/core/thresholds.yaml') as f:
    config = yaml.safe_load(f)
print(config.get('execution', {}).get('backtest_period_days', 180))
")
        PERIOD_DESC="直近${DAYS}日間（設定ファイル）"
    fi
fi

# タイムスタンプ生成（JST）
TIMESTAMP=$(TZ=Asia/Tokyo date +"%Y%m%d_%H%M%S")

# ログファイル名
LOG_FILE="${LOG_DIR}/${PREFIX}_${TIMESTAMP}.log"

# 実行時間計測開始
SECONDS=0

echo "🚀 バックテスト実行開始（Phase 61）"
echo "📅 期間: ${PERIOD_DESC}"
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
    if [ "$MODE" = "fixed" ]; then
        echo "📥 Step 1: CSVデータ収集開始（${START_DATE} ~ ${END_DATE}）..."
        python3 src/backtest/scripts/collect_historical_csv.py --start-date "$START_DATE" --end-date "$END_DATE"
    else
        echo "📥 Step 1: CSVデータ収集開始（直近${DAYS}日間）..."
        python3 src/backtest/scripts/collect_historical_csv.py --days "$DAYS"
    fi

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

# Step 2: 設定ファイル更新
echo "⚙️ Step 2: バックテスト期間設定..."
cp "$CONFIG_FILE" "$CONFIG_BACKUP"

if [ "$MODE" = "fixed" ]; then
    # 固定期間モードに設定
    python3 -c "
import yaml

with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

if 'execution' not in config:
    config['execution'] = {}

config['execution']['backtest_use_fixed_dates'] = True
config['execution']['backtest_start_date'] = '$START_DATE'
config['execution']['backtest_end_date'] = '$END_DATE'

with open('$CONFIG_FILE', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
"
    echo "✅ 固定期間モード設定: ${START_DATE} ~ ${END_DATE}"
else
    # ローリングウィンドウモードに設定
    python3 -c "
import yaml

with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

if 'execution' not in config:
    config['execution'] = {}

config['execution']['backtest_use_fixed_dates'] = False
config['execution']['backtest_period_days'] = $DAYS

with open('$CONFIG_FILE', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
"
    echo "✅ ローリングウィンドウモード設定: 直近${DAYS}日間"
fi
echo ""

# Step 3: バックテスト実行
echo "🔄 Step 3: バックテスト実行中..."
python3 main.py --mode backtest 2>&1 | tee "${LOG_FILE}"
BACKTEST_EXIT_CODE=${PIPESTATUS[0]}
echo ""

# Step 4: 設定ファイル復元
echo "🔧 Step 4: 設定ファイル復元..."
if [ -f "$CONFIG_BACKUP" ]; then
    mv "$CONFIG_BACKUP" "$CONFIG_FILE"
    echo "✅ 設定ファイル復元完了"
fi
trap - EXIT  # trapを解除
echo ""

# バックテスト失敗時は終了
if [ $BACKTEST_EXIT_CODE -ne 0 ]; then
    echo "❌ バックテスト実行失敗（終了コード: $BACKTEST_EXIT_CODE）"
    exit $BACKTEST_EXIT_CODE
fi

# Step 5: Markdownレポート生成
echo "📝 Step 5: Markdownレポート生成..."
LATEST_JSON=$(ls -t logs/backtest/backtest_*.json 2>/dev/null | head -1)
if [ -n "$LATEST_JSON" ]; then
    python3 scripts/backtest/generate_markdown_report.py "$LATEST_JSON"
    LATEST_MD=$(ls -t docs/検証記録/backtest_*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_MD" ]; then
        echo "✅ Markdownレポート生成完了: $LATEST_MD"
    fi
else
    echo "⚠️ JSONレポートが見つかりません（Markdownレポート生成スキップ）"
fi

# Step 6: ローカル結果を検証記録に保存
echo ""
echo "📁 Step 6: ローカル結果を検証記録に保存..."
if [ -n "$LATEST_JSON" ]; then
    REPORT_DATE=$(TZ=Asia/Tokyo date +"%Y%m%d")
    LOCAL_JSON="docs/検証記録/local_backtest_${REPORT_DATE}.json"
    cp "$LATEST_JSON" "$LOCAL_JSON"
    echo "✅ ローカル結果保存: $LOCAL_JSON"
    echo "   → 分析: python3 scripts/backtest/standard_analysis.py --local"
else
    echo "⚠️ JSONファイルが見つかりません（保存スキップ）"
fi

# 実行時間計算
ELAPSED=$SECONDS
MINUTES=$((ELAPSED / 60))
SECS=$((ELAPSED % 60))

echo ""
echo "================================================="
echo "✅ バックテスト実行完了"
echo "📁 ログファイル: ${LOG_FILE}"
echo "📊 期間: ${PERIOD_DESC}"
if [ -n "${LATEST_MD:-}" ]; then
    echo "📝 レポート: ${LATEST_MD}"
fi
echo "⏱️ 実行時間: ${MINUTES}分${SECS}秒"
echo ""
