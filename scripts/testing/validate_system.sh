#!/bin/bash
# Phase 49.15: システム整合性検証スクリプト
#
# 目的: 開発・デプロイ段階でシステム稼働保証の事前チェック実行
# 検証項目: Dockerfile・特徴量・戦略・設定ファイル・環境変数・モデルメタデータ
# 使用: checks.sh、run_safe.sh、CI/CDで自動実行
#
# Phase 49.15追加機能（2025/10/26）:
# - 設定ファイル整合性チェック（YAML構文・必須フィールド・設定値妥当性）
# - 環境変数・Secret チェック（DISCORD_WEBHOOK_URL・BITBANK_API_KEY/SECRET）
# - モデルメタデータ整合性チェック（F1スコア・特徴量数・モデル年齢・訓練データサイズ）
# - すべてのチェックは動的設定読み込み方式（特徴量・戦略数の増減に自動対応）

# set -e を削除（while read ループとの互換性問題回避）

echo "🔍 Phase 49.15: システム整合性検証開始（7項目）..."
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$PROJECT_ROOT"

ERRORS=0

# ========================================
# 1. Dockerfile整合性チェック
# ========================================
echo "📦 [1/7] Dockerfile整合性チェック..."

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
echo "📊 [2/7] 特徴量数検証..."

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

# Phase 50.8: 3段階モデルシステム対応特徴量数検証
if [ -n "$FEATURE_ORDER_COUNT" ] && [ -n "$MODEL_FEATURE_COUNT" ]; then
    # feature_levelsから期待される特徴量数を取得（70, 62, 57）
    VALID_FEATURE_COUNTS=$(python3 -c "
import json
with open('config/core/feature_order.json') as f:
    data = json.load(f)
    levels = data.get('feature_levels', {})
    counts = [str(level['count']) for level in levels.values()]
    print(' '.join(counts))
" 2>&1)

    # production_model_metadata.jsonの特徴量数がいずれかのレベルに該当するか確認
    if echo "$VALID_FEATURE_COUNTS" | grep -q "\<$MODEL_FEATURE_COUNT\>"; then
        echo "  ✅ 特徴量数妥当性確認: $MODEL_FEATURE_COUNT 特徴量（Phase 50.7 Level 1-3対応）"
        if [ "$FEATURE_ORDER_COUNT" != "$MODEL_FEATURE_COUNT" ]; then
            echo "  ℹ️  INFO: Level 1定義=$FEATURE_ORDER_COUNT, 実行モデル=$MODEL_FEATURE_COUNT (正常)"
        fi
    else
        echo "  ❌ ERROR: 特徴量数不正 - $MODEL_FEATURE_COUNT は期待値 [$VALID_FEATURE_COUNTS] のいずれでもない"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""

# ========================================
# 3. 戦略整合性検証
# ========================================
echo "🎯 [3/7] 戦略整合性検証..."

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
echo "📥 [4/7] モジュールimport検証..."

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
# 5. 設定ファイル整合性チェック
# ========================================
echo "⚙️  [5/7] 設定ファイル整合性チェック..."

# YAML構文チェック - 動的にコア設定ファイルを検証
CONFIG_FILES=("config/core/unified.yaml" "config/core/thresholds.yaml" "config/core/features.yaml")

for config_file in "${CONFIG_FILES[@]}"; do
    if [ ! -f "$config_file" ]; then
        echo "  ❌ ERROR: $config_file が見つかりません"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    # YAML構文チェック
    if ! python3 -c "import yaml; yaml.safe_load(open('$config_file'))" 2>/dev/null; then
        echo "  ❌ ERROR: $config_file のYAML構文エラー"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ $config_file - 構文OK"
    fi
done

# unified.yaml 必須フィールド確認（動的検証）
UNIFIED_CHECK=$(python3 -c "
import yaml
try:
    with open('config/core/unified.yaml') as f:
        data = yaml.safe_load(f)
        required = ['mode', 'strategies', 'risk', 'execution']
        missing = [k for k in required if k not in data]
        if missing:
            print('MISSING:' + ','.join(missing))
        else:
            print('OK')
except Exception as e:
    print(f'ERROR:{e}')
" 2>&1)

if [[ "$UNIFIED_CHECK" == "MISSING:"* ]]; then
    MISSING_FIELDS=$(echo "$UNIFIED_CHECK" | cut -d':' -f2)
    echo "  ❌ ERROR: unified.yaml 必須フィールド不足: $MISSING_FIELDS"
    ERRORS=$((ERRORS + 1))
elif [[ "$UNIFIED_CHECK" == "ERROR:"* ]]; then
    echo "  ❌ ERROR: unified.yaml 読み込み失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "  ✅ unified.yaml 必須フィールド確認完了"
fi

# thresholds.yaml 設定値妥当性チェック（動的範囲検証）
THRESHOLD_CHECK=$(python3 -c "
import yaml
try:
    with open('config/core/thresholds.yaml') as f:
        data = yaml.safe_load(f)
        errors = []

        # TP/SL率チェック（動的取得）
        if 'position_management' in data:
            pm = data['position_management']
            sl_ratio = pm.get('sl_min_distance_ratio', 0)
            tp_ratio = pm.get('tp_min_profit_ratio', 0)
            if not (0.0 <= sl_ratio <= 1.0):
                errors.append(f'sl_min_distance_ratio={sl_ratio}は0.0-1.0範囲外')
            if not (0.0 <= tp_ratio <= 1.0):
                errors.append(f'tp_min_profit_ratio={tp_ratio}は0.0-1.0範囲外')

        # ML統合閾値チェック（動的取得）
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
    INVALID_VALUES=$(echo "$THRESHOLD_CHECK" | cut -d':' -f2 | tr '|' '\n')
    echo "  ❌ ERROR: thresholds.yaml 設定値妥当性エラー:"
    echo "$INVALID_VALUES" | while read line; do echo "     - $line"; done
    ERRORS=$((ERRORS + 1))
elif [[ "$THRESHOLD_CHECK" == "ERROR:"* ]]; then
    echo "  ❌ ERROR: thresholds.yaml 読み込み失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "  ✅ thresholds.yaml 設定値妥当性確認完了"
fi

echo ""

# ========================================
# 6. 環境変数・Secret チェック
# ========================================
echo "🔐 [6/7] 環境変数・Secret チェック..."

# Discord Webhook URL確認（本番環境で必須）
if [ -n "$DISCORD_WEBHOOK_URL" ]; then
    echo "  ✅ DISCORD_WEBHOOK_URL: 設定済み"
else
    echo "  ⚠️  WARNING: DISCORD_WEBHOOK_URL が未設定（ローカル環境の場合は問題なし）"
fi

# Bitbank API キー確認（ライブモード時必須）
# ローカル環境ではなくても良いため、WARNINGレベル
if [ -n "$BITBANK_API_KEY" ]; then
    echo "  ✅ BITBANK_API_KEY: 設定済み"
else
    echo "  ⚠️  WARNING: BITBANK_API_KEY が未設定（ペーパー/バックテストモードの場合は問題なし）"
fi

if [ -n "$BITBANK_API_SECRET" ]; then
    echo "  ✅ BITBANK_API_SECRET: 設定済み"
else
    echo "  ⚠️  WARNING: BITBANK_API_SECRET が未設定（ペーパー/バックテストモードの場合は問題なし）"
fi

echo ""

# ========================================
# 7. モデルメタデータ整合性チェック
# ========================================
echo "🤖 [7/7] モデルメタデータ整合性チェック..."

if [ ! -f "models/production/production_model_metadata.json" ]; then
    echo "  ❌ ERROR: production_model_metadata.json が見つかりません"
    ERRORS=$((ERRORS + 1))
else
    # メタデータ検証（動的検証）
    METADATA_CHECK=$(python3 -c "
import json
from datetime import datetime, timedelta

try:
    with open('models/production/production_model_metadata.json') as f:
        metadata = json.load(f)
        errors = []
        warnings = []

        # F1スコア妥当性チェック（動的取得・妥当範囲検証）
        if 'ensemble_performance' in metadata:
            f1_score = metadata['ensemble_performance'].get('weighted_f1', 0)
            if not (0.4 <= f1_score <= 0.8):
                warnings.append(f'F1スコア={f1_score:.3f}が通常範囲外（0.4-0.8推奨）')
            else:
                print(f'INFO:F1スコア={f1_score:.3f}')

        # Phase 50.8: 3段階モデルシステム対応特徴量数確認
        with open('config/core/feature_order.json') as ff:
            feature_config = json.load(ff)
            # Level 1-3の期待特徴量数を取得（70, 62, 57）
            valid_counts = [level['count'] for level in feature_config.get('feature_levels', {}).values()]

        actual_features = metadata['training_info'].get('feature_count', 0)
        if actual_features in valid_counts:
            print(f'INFO:特徴量数妥当={actual_features}（Phase 50.7 Level 1-3対応）')
        else:
            errors.append(f'特徴量数不正: metadata={actual_features}, 期待値={valid_counts}のいずれでもない')

        # モデル作成日チェック（動的取得・90日以内確認）
        created_at = metadata.get('created_at', '')
        if created_at:
            from datetime import timezone
            # タイムゾーン情報がない場合はUTCとして扱う
            created_str = created_at.replace('Z', '+00:00')
            created_date = datetime.fromisoformat(created_str)
            if created_date.tzinfo is None:
                created_date = created_date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_days = (now - created_date).days
            if age_days > 90:
                warnings.append(f'モデル作成から{age_days}日経過（90日以内推奨）')
            else:
                print(f'INFO:モデル作成{age_days}日前')

        # 訓練データサイズチェック（動的取得）
        if 'training_info' in metadata:
            train_size = metadata['training_info'].get('train_size', 0)
            if train_size < 10000:
                warnings.append(f'訓練データサイズ={train_size}が少ない（10,000件以上推奨）')
            else:
                print(f'INFO:訓練データ={train_size}件')

        if errors:
            print('ERROR:' + '|'.join(errors))
        elif warnings:
            print('WARNING:' + '|'.join(warnings))
        else:
            print('OK')
except Exception as e:
    print(f'ERROR:メタデータ読み込み失敗:{e}')
" 2>&1)

    # INFO行を処理（正常メッセージ）
    echo "$METADATA_CHECK" | grep "^INFO:" | cut -d':' -f2- | while read info; do
        echo "  ℹ️  $info"
    done

    # エラー・警告処理
    ERROR_LINE=$(echo "$METADATA_CHECK" | grep "^ERROR:")
    WARNING_LINE=$(echo "$METADATA_CHECK" | grep "^WARNING:")

    if [ -n "$ERROR_LINE" ]; then
        ERROR_MSGS=$(echo "$ERROR_LINE" | cut -d':' -f2 | tr '|' '\n')
        echo "  ❌ ERROR: モデルメタデータ整合性エラー:"
        echo "$ERROR_MSGS" | while read line; do echo "     - $line"; done
        ERRORS=$((ERRORS + 1))
    elif [ -n "$WARNING_LINE" ]; then
        WARNING_MSGS=$(echo "$WARNING_LINE" | cut -d':' -f2 | tr '|' '\n')
        echo "  ⚠️  WARNING: モデルメタデータ警告:"
        echo "$WARNING_MSGS" | while read line; do echo "     - $line"; done
    fi

    if [ -z "$ERROR_LINE" ] && [ -z "$WARNING_LINE" ]; then
        OK_LINE=$(echo "$METADATA_CHECK" | grep "^OK")
        if [ -n "$OK_LINE" ]; then
            echo "  ✅ モデルメタデータ整合性確認完了"
        fi
    fi
fi

# モデルファイル存在・サイズ確認（動的確認）
# Phase 50.9: 2段階モデルシステム（full/basic）
MODEL_FILES=(
    "models/production/ensemble_full.pkl"
    "models/production/ensemble_basic.pkl"
)

for model_file in "${MODEL_FILES[@]}"; do
    if [ ! -f "$model_file" ]; then
        echo "  ❌ ERROR: $model_file が見つかりません"
        ERRORS=$((ERRORS + 1))
    else
        # ファイルサイズ確認（1KB以上 - 空ファイルチェック）
        FILE_SIZE=$(stat -f%z "$model_file" 2>/dev/null || stat -c%s "$model_file" 2>/dev/null)
        if [ "$FILE_SIZE" -lt 1024 ]; then
            echo "  ❌ ERROR: $model_file のサイズが小さすぎます（${FILE_SIZE}B < 1KB）"
            ERRORS=$((ERRORS + 1))
        else
            # サイズを人間可読形式に変換
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

echo ""

# ========================================
# 結果サマリー
# ========================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo "✅ Phase 49.15: システム整合性検証完了（7項目） - エラー無し"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo "❌ Phase 49.15: システム整合性検証失敗（7項目） - $ERRORS 個のエラー"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
