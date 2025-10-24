#!/bin/bash
# Phase 49.14-1: システム整合性検証スクリプト
#
# 目的: 開発段階でDockerfile・特徴量・戦略の不整合を検出
# 使用: checks.sh、run_safe.sh、CI/CDで自動実行

set -e

echo "🔍 Phase 49.14: システム整合性検証開始..."
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$PROJECT_ROOT"

ERRORS=0

# ========================================
# 1. Dockerfile整合性チェック
# ========================================
echo "📦 [1/4] Dockerfile整合性チェック..."

# 必須ディレクトリリスト（Phase 49.13で追加されたtax/を含む）
REQUIRED_DIRS=("src" "config" "models" "tax" "tests/manual")

for dir in "${REQUIRED_DIRS[@]}"; do
    # ディレクトリの存在確認
    if [ ! -d "$dir" ]; then
        echo "  ❌ ERROR: ディレクトリ '$dir' が存在しません"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    # Dockerfileに COPY 命令が存在するか確認
    if ! grep -q "COPY $dir/" Dockerfile; then
        echo "  ❌ ERROR: Dockerfile に 'COPY $dir/' が見つかりません"
        echo "     → Phase 49.13問題の再発（40時間停止の原因）"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ $dir/ - OK"
    fi
done

# 逆チェック: Dockerfileに記載されているが存在しないディレクトリ
COPIED_DIRS=$(grep -oE 'COPY [a-zA-Z_/]+/ ' Dockerfile | awk '{print $2}' | sed 's|/$||')
for dir in $COPIED_DIRS; do
    if [ ! -d "$dir" ]; then
        echo "  ⚠️  WARNING: Dockerfile に記載されているが存在しないディレクトリ: $dir"
    fi
done

echo ""

# ========================================
# 2. 特徴量数検証
# ========================================
echo "📊 [2/4] 特徴量数検証..."

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

# 特徴量数一致確認
if [ -n "$FEATURE_ORDER_COUNT" ] && [ -n "$MODEL_FEATURE_COUNT" ]; then
    if [ "$FEATURE_ORDER_COUNT" != "$MODEL_FEATURE_COUNT" ]; then
        echo "  ❌ ERROR: 特徴量数不一致 - $FEATURE_ORDER_COUNT != $MODEL_FEATURE_COUNT"
        echo "     → Phase 49.13エラー '特徴量数不一致: 15 != 55' の再発"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ 特徴量数一致: $FEATURE_ORDER_COUNT 特徴量"
    fi
fi

echo ""

# ========================================
# 3. 戦略整合性検証
# ========================================
echo "🎯 [3/4] 戦略整合性検証..."

# unified.yaml の戦略リスト取得
UNIFIED_STRATEGIES=$(python3 -c "
import yaml
with open('config/core/unified.yaml') as f:
    data = yaml.safe_load(f)
    strategies = data.get('strategies', {})
    print(' '.join(sorted(strategies.keys())))
" 2>&1)

if [ $? -ne 0 ]; then
    echo "  ❌ ERROR: unified.yaml の読み込みに失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "  📋 unified.yaml 戦略: $UNIFIED_STRATEGIES"
fi

# feature_order.json の strategy_signal 特徴量取得
FEATURE_STRATEGIES=$(python3 -c "
import json
with open('config/core/feature_order.json') as f:
    data = json.load(f)
    signals = data['feature_categories']['strategy_signals']['features']
    # 'strategy_signal_' プレフィックスを削除
    strategies = [s.replace('strategy_signal_', '') for s in signals]
    print(' '.join(sorted(strategies)))
" 2>&1)

if [ $? -ne 0 ]; then
    echo "  ❌ ERROR: feature_order.json の strategy_signals 読み込みに失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "  📊 feature_order.json 戦略信号: $FEATURE_STRATEGIES"
fi

# src/strategies/implementations/ の実装ファイル取得
IMPL_STRATEGIES=""
if [ -d "src/strategies/implementations" ]; then
    # .py ファイルから __init__.py を除外し、ファイル名を取得
    IMPL_FILES=$(ls src/strategies/implementations/*.py 2>/dev/null | grep -v "__init__" | xargs -n1 basename | sed 's/.py$//' | sort)
    IMPL_STRATEGIES=$(echo $IMPL_FILES | tr '\n' ' ')
    echo "  💻 implementations/ ファイル: $IMPL_STRATEGIES"
else
    echo "  ❌ ERROR: src/strategies/implementations/ が見つかりません"
    ERRORS=$((ERRORS + 1))
fi

# 戦略整合性確認（簡易版 - 数の一致確認）
if [ -n "$UNIFIED_STRATEGIES" ] && [ -n "$FEATURE_STRATEGIES" ]; then
    UNIFIED_COUNT=$(echo $UNIFIED_STRATEGIES | wc -w | tr -d ' ')
    FEATURE_COUNT=$(echo $FEATURE_STRATEGIES | wc -w | tr -d ' ')

    if [ "$UNIFIED_COUNT" != "$FEATURE_COUNT" ]; then
        echo "  ⚠️  WARNING: 戦略数不一致 - unified.yaml:$UNIFIED_COUNT vs feature_order.json:$FEATURE_COUNT"
        echo "     → 新規戦略追加時は両方のファイルを更新してください"
    else
        echo "  ✅ 戦略数一致: $UNIFIED_COUNT 戦略"
    fi
fi

echo ""

# ========================================
# 4. モジュールimport検証（軽量版）
# ========================================
echo "📥 [4/4] モジュールimport検証..."

# PYTHONPATH設定
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:$PYTHONPATH"

# 重要モジュールのimportテスト
CRITICAL_IMPORTS=(
    "from src.core.orchestration.orchestrator import TradingOrchestrator"
    "from src.trading.execution.executor import ExecutionService"
    "from tax.trade_history_recorder import TradeHistoryRecorder"
    "from src.strategies.base.strategy_manager import StrategyManager"
)

for import_stmt in "${CRITICAL_IMPORTS[@]}"; do
    MODULE_NAME=$(echo "$import_stmt" | awk '{print $2}' | cut -d'.' -f1-3)

    if python3 -c "$import_stmt" 2>/dev/null; then
        echo "  ✅ $MODULE_NAME - OK"
    else
        echo "  ❌ ERROR: $import_stmt が失敗しました"
        echo "     → Phase 49.13エラー 'No module named ...' の可能性"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# ========================================
# 結果サマリー
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo "✅ Phase 49.14: システム整合性検証完了 - エラー無し"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo "❌ Phase 49.14: システム整合性検証失敗 - $ERRORS 個のエラー"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
