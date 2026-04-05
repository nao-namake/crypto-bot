#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ファイル名: scripts/testing/checks.sh
# 説明: Phase 61 品質チェック統合スクリプト
#
# Phase 61.2で validate_system.sh を統合し、12項目チェックに最適化
#
# チェック項目:
#   [1] ディレクトリ構造確認
#   [2] Dockerfile整合性
#   [3] 特徴量数検証（55/49）
#   [4] 戦略整合性（6戦略）
#   [5] 設定ファイル整合性（YAML構文・必須フィールド）
#   [6] モデルファイル・メタデータ
#   [7] ML検証（validate_ml_models.py --quick）
#   [8] flake8
#   [9] isort
#   [10] black
#   [11] pytest
#   [12] 結果サマリー
#
# 使い方（プロジェクトルートから実行）:
#   bash scripts/testing/checks.sh
# =============================================================================

# スクリプト開始時刻記録
START_TIME=$(date +%s)

echo "🚀 品質チェック開始 (Phase 61)"
echo "============================================="

# カバレッジ最低ライン
COV_FAIL_UNDER=74

# プロジェクトルート設定
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$PROJECT_ROOT"

# エラーカウンター
ERRORS=0

# ========================================
# [1/12] ディレクトリ構造確認
# ========================================
echo ""
echo "📂 [1/12] ディレクトリ構造確認..."

if [[ ! -d "src" ]]; then
    echo "❌ エラー: src/ディレクトリが見つかりません"
    echo "プロジェクトルートから実行してください"
    exit 1
fi

echo "  ✅ src/ディレクトリ確認完了"

# ========================================
# [2/12] Dockerfile整合性チェック
# ========================================
echo ""
echo "📦 [2/12] Dockerfile整合性チェック..."

# 必須ディレクトリリスト
REQUIRED_DIRS=("src" "config" "models" "tax")

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "  ❌ ERROR: ディレクトリ '$dir' が存在しません"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    if ! grep -q "COPY $dir/" Dockerfile; then
        echo "  ❌ ERROR: Dockerfile に 'COPY $dir/' が見つかりません"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ $dir/ - OK"
    fi
done

# ========================================
# [3/12] 特徴量数検証
# ========================================
echo ""
echo "📊 [3/12] 特徴量数検証..."

FEATURE_ORDER_COUNT=""
MODEL_FEATURE_COUNT=""

# feature_order.json の特徴量数取得
if [ ! -f "config/core/feature_order.json" ]; then
    echo "  ❌ ERROR: config/core/feature_order.json が見つかりません"
    ERRORS=$((ERRORS + 1))
else
    FEATURE_ORDER_COUNT=$(python3 -c "
import json
with open('config/core/feature_order.json') as f:
    data = json.load(f)
    print(data['total_features'])
" 2>&1)

    if [ $? -ne 0 ]; then
        echo "  ❌ ERROR: feature_order.json の読み込みに失敗"
        ERRORS=$((ERRORS + 1))
    else
        echo "  📋 feature_order.json: $FEATURE_ORDER_COUNT 特徴量"
    fi
fi

# production_model_metadata.json の特徴量数取得
if [ ! -f "models/production/production_model_metadata.json" ]; then
    echo "  ❌ ERROR: models/production/production_model_metadata.json が見つかりません"
    ERRORS=$((ERRORS + 1))
else
    MODEL_FEATURE_COUNT=$(python3 -c "
import json
with open('models/production/production_model_metadata.json') as f:
    data = json.load(f)
    print(data['training_info']['feature_count'])
" 2>&1)

    if [ $? -ne 0 ]; then
        echo "  ❌ ERROR: production_model_metadata.json の読み込みに失敗"
        ERRORS=$((ERRORS + 1))
    else
        echo "  🤖 production_model_metadata.json: $MODEL_FEATURE_COUNT 特徴量"
    fi
fi

# 特徴量数妥当性確認
if [ -n "$FEATURE_ORDER_COUNT" ] && [ -n "$MODEL_FEATURE_COUNT" ]; then
    VALID_FEATURE_COUNTS=$(python3 -c "
import json
with open('config/core/feature_order.json') as f:
    data = json.load(f)
    levels = data.get('feature_levels', {})
    counts = [str(level['count']) for level in levels.values()]
    print(' '.join(counts))
" 2>&1)

    if echo "$VALID_FEATURE_COUNTS" | grep -q "\<$MODEL_FEATURE_COUNT\>"; then
        echo "  ✅ 特徴量数妥当性確認: $MODEL_FEATURE_COUNT 特徴量"
    else
        echo "  ❌ ERROR: 特徴量数不正 - $MODEL_FEATURE_COUNT は期待値 [$VALID_FEATURE_COUNTS] のいずれでもない"
        ERRORS=$((ERRORS + 1))
    fi
fi

# ========================================
# [4/12] 戦略整合性検証
# ========================================
echo ""
echo "🎯 [4/12] 戦略整合性検証..."

# thresholds.yaml から戦略リスト取得
STRATEGIES_YAML_STRATEGIES=$(python3 -c "
import yaml
with open('config/core/thresholds.yaml') as f:
    data = yaml.safe_load(f)
    strategies = data.get('strategies', {})
    print(' '.join(sorted(strategies.keys())))
" 2>&1)

if [ $? -ne 0 ]; then
    echo "  ❌ ERROR: config/core/thresholds.yaml の戦略読み込みに失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "  📋 thresholds.yaml 戦略: $STRATEGIES_YAML_STRATEGIES"
fi

# feature_order.json の strategy_signal 特徴量取得
FEATURE_STRATEGIES=$(python3 -c "
import json
with open('config/core/feature_order.json') as f:
    data = json.load(f)
    signals = data['feature_categories']['strategy_signals']['features']
    strategies = [s.replace('strategy_signal_', '') for s in signals]
    print(' '.join(sorted(strategies)))
" 2>&1)

if [ $? -ne 0 ]; then
    echo "  ❌ ERROR: feature_order.json の strategy_signals 読み込みに失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "  📊 feature_order.json 戦略信号: $FEATURE_STRATEGIES"
fi

# 戦略数一致確認
if [ -n "$STRATEGIES_YAML_STRATEGIES" ] && [ -n "$FEATURE_STRATEGIES" ]; then
    STRATEGIES_COUNT=$(echo $STRATEGIES_YAML_STRATEGIES | wc -w | tr -d ' ')
    FEATURE_COUNT=$(echo $FEATURE_STRATEGIES | wc -w | tr -d ' ')

    if [ "$STRATEGIES_COUNT" != "$FEATURE_COUNT" ]; then
        echo "  ⚠️  WARNING: 戦略数不一致 - thresholds.yaml:$STRATEGIES_COUNT vs feature_order.json:$FEATURE_COUNT"
    else
        echo "  ✅ 戦略数一致: $STRATEGIES_COUNT 戦略"
    fi
fi

# ========================================
# [5/12] 設定ファイル整合性チェック
# ========================================
echo ""
echo "⚙️  [5/12] 設定ファイル整合性チェック..."

# YAML構文チェック（thresholds.yaml単一ファイル体系）
CONFIG_FILE="config/core/thresholds.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "  ❌ ERROR: $CONFIG_FILE が見つかりません"
    ERRORS=$((ERRORS + 1))
else
    if ! python3 -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null; then
        echo "  ❌ ERROR: $CONFIG_FILE のYAML構文エラー"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ $CONFIG_FILE - 構文OK"
    fi
fi

# thresholds.yaml 必須フィールド確認（環境設定+パラメータ）
REQUIRED_CHECK=$(python3 -c "
import yaml
try:
    with open('config/core/thresholds.yaml') as f:
        data = yaml.safe_load(f)
        required = ['mode', 'exchange', 'data', 'strategies', 'ml', 'risk']
        missing = [k for k in required if k not in data]
        if missing:
            print('MISSING:' + ','.join(missing))
        else:
            print('OK')
except Exception as e:
    print(f'ERROR:{e}')
" 2>&1)

if [[ "$REQUIRED_CHECK" == "MISSING:"* ]]; then
    MISSING_FIELDS=$(echo "$REQUIRED_CHECK" | cut -d':' -f2)
    echo "  ❌ ERROR: thresholds.yaml 必須フィールド不足: $MISSING_FIELDS"
    ERRORS=$((ERRORS + 1))
elif [[ "$REQUIRED_CHECK" == "ERROR:"* ]]; then
    echo "  ❌ ERROR: thresholds.yaml 読み込み失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "  ✅ thresholds.yaml 必須フィールド確認完了"
fi

# thresholds.yaml 設定値妥当性チェック
THRESHOLD_CHECK=$(python3 -c "
import yaml
try:
    with open('config/core/thresholds.yaml') as f:
        data = yaml.safe_load(f)
        errors = []

        if 'position_management' in data:
            pm = data['position_management']
            sl_ratio = pm.get('sl_min_distance_ratio', 0)
            tp_ratio = pm.get('tp_min_profit_ratio', 0)
            if not (0.0 <= sl_ratio <= 1.0):
                errors.append(f'sl_min_distance_ratio={sl_ratio}は0.0-1.0範囲外')
            if not (0.0 <= tp_ratio <= 1.0):
                errors.append(f'tp_min_profit_ratio={tp_ratio}は0.0-1.0範囲外')

        if 'ml_integration' in data:
            ml = data['ml_integration']
            min_conf = ml.get('min_ml_confidence', 0)
            high_conf = ml.get('high_confidence_threshold', 0)
            if not (0.0 <= min_conf <= 1.0):
                errors.append(f'min_ml_confidence={min_conf}は0.0-1.0範囲外')
            if not (0.0 <= high_conf <= 1.0):
                errors.append(f'high_confidence_threshold={high_conf}は0.0-1.0範囲外')

        if errors:
            print('INVALID:' + '|'.join(errors))
        else:
            print('OK')
except Exception as e:
    print(f'ERROR:{e}')
" 2>&1)

if [[ "$THRESHOLD_CHECK" == "INVALID:"* ]]; then
    echo "  ❌ ERROR: thresholds.yaml 設定値妥当性エラー"
    ERRORS=$((ERRORS + 1))
elif [[ "$THRESHOLD_CHECK" == "ERROR:"* ]]; then
    echo "  ❌ ERROR: thresholds.yaml 読み込み失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "  ✅ thresholds.yaml 設定値妥当性確認完了"
fi

# ========================================
# [6/12] モデルファイル・メタデータ
# ========================================
echo ""
echo "🤖 [6/12] モデルファイル・メタデータチェック..."

# モデルファイル存在・サイズ確認
MODEL_FILES=(
    "models/production/ensemble_full.pkl"
    "models/production/ensemble_basic.pkl"
)

for model_file in "${MODEL_FILES[@]}"; do
    if [ ! -f "$model_file" ]; then
        echo "  ❌ ERROR: $model_file が見つかりません"
        ERRORS=$((ERRORS + 1))
    else
        FILE_SIZE=$(stat -f%z "$model_file" 2>/dev/null || stat -c%s "$model_file" 2>/dev/null)
        if [ "$FILE_SIZE" -lt 1024 ]; then
            echo "  ❌ ERROR: $model_file のサイズが小さすぎます（${FILE_SIZE}B < 1KB）"
            ERRORS=$((ERRORS + 1))
        else
            if [ "$FILE_SIZE" -ge 1048576 ]; then
                SIZE_MB=$(echo "scale=1; $FILE_SIZE / 1048576" | bc)
                echo "  ✅ $model_file - ${SIZE_MB}MB"
            else
                SIZE_KB=$(echo "scale=1; $FILE_SIZE / 1024" | bc)
                echo "  ✅ $model_file - ${SIZE_KB}KB"
            fi
        fi
    fi
done

# メタデータ検証
if [ -f "models/production/production_model_metadata.json" ]; then
    METADATA_CHECK=$(python3 -c "
import json
from datetime import datetime, timezone

try:
    with open('models/production/production_model_metadata.json') as f:
        metadata = json.load(f)
        info = []

        if 'ensemble_performance' in metadata:
            f1_score = metadata['ensemble_performance'].get('weighted_f1', 0)
            info.append(f'F1={f1_score:.3f}')

        if 'training_info' in metadata:
            train_size = metadata['training_info'].get('train_size', 0)
            info.append(f'訓練データ={train_size}件')

        created_at = metadata.get('created_at', '')
        if created_at:
            created_str = created_at.replace('Z', '+00:00')
            created_date = datetime.fromisoformat(created_str)
            if created_date.tzinfo is None:
                created_date = created_date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_days = (now - created_date).days
            info.append(f'作成{age_days}日前')

        print(' / '.join(info))
except Exception as e:
    print(f'ERROR:{e}')
" 2>&1)

    if [[ "$METADATA_CHECK" == "ERROR:"* ]]; then
        echo "  ❌ ERROR: メタデータ読み込み失敗"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ℹ️  $METADATA_CHECK"
    fi
fi

# 整合性チェックでエラーがあれば早期終了
if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "❌ システム整合性検証失敗: $ERRORS 個のエラー"
    echo "上記のエラーを修正してから再実行してください"
    exit 1
fi

echo ""
echo "✅ システム整合性検証完了（6項目）"

# ========================================
# [7/12] ML検証（--quick）
# ========================================
echo ""
echo "🤖 [7/12] ML検証（37特徴量）..."

if [[ -f "scripts/testing/validate_ml_models.py" ]]; then
    python3 scripts/testing/validate_ml_models.py --quick || {
        echo "❌ エラー: ML検証失敗"
        echo "モデル再訓練が必要: python3 scripts/ml/create_ml_models.py"
        exit 1
    }
else
    echo "⚠️  警告: validate_ml_models.py が見つかりません"
fi

# ========================================
# [8/12] flake8
# ========================================
echo ""
echo "🎨 [8/12] flake8: コードスタイルチェック..."

python3 -m flake8 src/ tests/ scripts/ \
    --max-line-length=100 \
    --ignore=E203,W503,E402,F401,F841,F541,F811 \
    --exclude=_legacy_v1 || {
    echo "❌ flake8チェック失敗"
    exit 1
}

echo "✅ flake8チェック完了"

# ========================================
# [9/12] isort
# ========================================
echo ""
echo "📥 [9/12] isort: import順序チェック..."

python3 -m isort --check-only --diff src/ tests/ scripts/ \
    --skip=_legacy_v1 || {
    echo "❌ isortチェック失敗"
    echo "修正するには: python3 -m isort src/ tests/ scripts/"
    exit 1
}

echo "✅ isortチェック完了"

# ========================================
# [10/12] black
# ========================================
echo ""
echo "⚫ [10/12] black: コード整形チェック..."

python3 -m black --check --diff src/ tests/ scripts/ \
    --exclude="_legacy_v1" || {
    echo "❌ blackチェック失敗"
    echo "修正するには: python3 -m black src/ tests/ scripts/"
    exit 1
}

echo "✅ blackチェック完了"

# ========================================
# [11/12] pytest
# ========================================
echo ""
echo "🧪 [11/12] pytest: 全テスト実行..."

python3 -m pytest \
  tests/ \
  --maxfail=3 \
  --disable-warnings \
  -v \
  --cov=src \
  --cov-report=term-missing \
  --cov-report=html:.cache/coverage/htmlcov \
  --cov-fail-under="${COV_FAIL_UNDER}" \
  --tb=short || {
    echo "❌ テスト実行失敗"
    exit 1
}

echo "✅ 全テスト実行完了"

# ========================================
# [12/12] 結果サマリー
# ========================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "🎉 品質チェック完了！ (Phase 61)"
echo "============================================="
echo "📊 チェック結果:"
echo "  - システム整合性: ✅ PASS (6項目)"
echo "  - ML検証: ✅ PASS (37特徴量)"
echo "  - flake8: ✅ PASS"
echo "  - isort: ✅ PASS"
echo "  - black: ✅ PASS"
echo "  - pytest: ✅ PASS (${COV_FAIL_UNDER}%+カバレッジ)"
echo "  - 実行時間: ${DURATION}秒"
echo ""
echo "📁 カバレッジレポート: .cache/coverage/htmlcov/index.html"
