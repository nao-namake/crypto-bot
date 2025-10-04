#!/bin/bash
# ML信頼度分析スクリプト (Phase 33.2)
# GCP Cloud Runログから ML信頼度の統計情報を抽出

echo "📊 ML信頼度分析開始"
echo "===================="
echo ""

# 分析期間設定（デフォルト: 過去24時間）
START_TIME=${1:-$(python3 -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))")}
echo "📅 分析期間: $START_TIME 以降"
echo ""

# ML信頼度ログ取得
echo "🔍 ML信頼度データ取得中..."
ML_CONFIDENCE_LOGS=$(gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"動的ポジションサイズ\" AND timestamp>=\"$START_TIME\"" --limit=1000 --format="value(textPayload)" 2>/dev/null)

if [ -z "$ML_CONFIDENCE_LOGS" ]; then
    echo "❌ ML信頼度ログが見つかりませんでした"
    exit 1
fi

# 信頼度を抽出してファイルに保存
echo "$ML_CONFIDENCE_LOGS" | grep -oE "信頼度\([0-9.]+%" | grep -oE "[0-9.]+" > /tmp/ml_confidence_values.txt

# 統計計算
TOTAL_COUNT=$(wc -l < /tmp/ml_confidence_values.txt)
if [ "$TOTAL_COUNT" -eq 0 ]; then
    echo "❌ 信頼度データが抽出できませんでした"
    exit 1
fi

echo ""
echo "📈 ML信頼度統計"
echo "===================="
echo "サンプル数: ${TOTAL_COUNT}件"
echo ""

# 平均値計算
AVERAGE=$(awk '{ sum += $1; count++ } END { if (count > 0) print sum / count; else print 0 }' /tmp/ml_confidence_values.txt)
echo "平均値: ${AVERAGE}%"

# 最小値・最大値
MIN=$(sort -n /tmp/ml_confidence_values.txt | head -1)
MAX=$(sort -n /tmp/ml_confidence_values.txt | tail -1)
echo "最小値: ${MIN}%"
echo "最大値: ${MAX}%"

# 中央値計算
MEDIAN_LINE=$(echo "($TOTAL_COUNT + 1) / 2" | bc)
MEDIAN=$(sort -n /tmp/ml_confidence_values.txt | sed -n "${MEDIAN_LINE}p")
echo "中央値: ${MEDIAN}%"

echo ""
echo "📊 信頼度レベル別分布"
echo "===================="

# 低信頼度 (< 60%)
LOW_COUNT=$(awk '$1 < 60' /tmp/ml_confidence_values.txt | wc -l)
LOW_PERCENT=$(echo "scale=2; $LOW_COUNT * 100 / $TOTAL_COUNT" | bc)
echo "低信頼度 (<60%): ${LOW_COUNT}件 (${LOW_PERCENT}%)"

# 中信頼度 (60-75%)
MEDIUM_COUNT=$(awk '$1 >= 60 && $1 < 75' /tmp/ml_confidence_values.txt | wc -l)
MEDIUM_PERCENT=$(echo "scale=2; $MEDIUM_COUNT * 100 / $TOTAL_COUNT" | bc)
echo "中信頼度 (60-75%): ${MEDIUM_COUNT}件 (${MEDIUM_PERCENT}%)"

# 高信頼度 (>= 75%)
HIGH_COUNT=$(awk '$1 >= 75' /tmp/ml_confidence_values.txt | wc -l)
HIGH_PERCENT=$(echo "scale=2; $HIGH_COUNT * 100 / $TOTAL_COUNT" | bc)
echo "高信頼度 (≥75%): ${HIGH_COUNT}件 (${HIGH_PERCENT}%)"

echo ""
echo "⚡ スマート注文機能への影響"
echo "===================="
echo "指値注文使用可能: ${HIGH_COUNT}件 (高信頼度≥75%)"
echo "成行注文強制: $((TOTAL_COUNT - HIGH_COUNT))件 (信頼度<75%)"
LIMIT_ORDER_RATIO=$(echo "scale=2; $HIGH_COUNT * 100 / $TOTAL_COUNT" | bc)
echo "指値注文使用率: ${LIMIT_ORDER_RATIO}%"

echo ""
echo "💡 推奨事項"
echo "===================="

if [ "$(echo "$LIMIT_ORDER_RATIO < 10" | bc)" -eq 1 ]; then
    echo "⚠️ 指値注文使用率が非常に低い（${LIMIT_ORDER_RATIO}%）"
    echo "推奨: ML予測モデルの再学習を検討"
    echo "または: スマート注文高信頼度閾値を75% → 65%に引き下げ検討"
elif [ "$(echo "$LIMIT_ORDER_RATIO < 30" | bc)" -eq 1 ]; then
    echo "⚠️ 指値注文使用率が低い（${LIMIT_ORDER_RATIO}%）"
    echo "推奨: ML予測精度の向上を検討"
else
    echo "✅ 指値注文使用率は良好（${LIMIT_ORDER_RATIO}%）"
fi

# 一時ファイル削除
rm -f /tmp/ml_confidence_values.txt

echo ""
echo "✅ 分析完了"
