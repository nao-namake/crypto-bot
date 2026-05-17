#!/usr/bin/env bash
# Phase 90: ローカル ML 再学習スクリプト
# - GitHub Actions の 60 分制限を回避（ローカル時間無制限）
# - RF n_jobs=-1（全コア利用）で 5-7 分に短縮
# - モデル別 30 分タイムアウト（ML_TRAINING_PER_MODEL_TIMEOUT で上書き可）
# - caffeinate でスリープ防止（macOS lid 閉じても継続実行）

set -euo pipefail

# Phase 90: macOS スリープ対策（caffeinate で自身を実行ラップ）
# v8e で「lid 閉じ → スリープ → ネットワーク I/O 停止 → データ収集 2 時間遅延」事案が発生
# CAFFEINATE_WRAPPED=1 でセルフ再起動防止
if [ "$(uname)" = "Darwin" ] && [ -z "${CAFFEINATE_WRAPPED:-}" ]; then
    echo "💤 macOS スリープ防止: caffeinate -dimsu で自身をラップ実行"
    export CAFFEINATE_WRAPPED=1
    exec caffeinate -dimsu "$0" "$@"
fi

# プロジェクトルートへ移動
cd "$(dirname "$0")/../.."
PROJECT_ROOT="$(pwd)"

# venv 確認
if [ ! -d "venv" ]; then
    echo "❌ venv が存在しません。先に python3 -m venv venv && pip install -r requirements.txt を実行"
    exit 1
fi

# Python パス
PYTHON="$PROJECT_ROOT/venv/bin/python3"

# 環境変数設定
# - ML_TRAINING_N_JOBS=-1: RF 全コア利用（ローカル限定・GCP 本番は 1 のまま維持）
# - ML_TRAINING_MODE=true: cross_asset history pickle リーク防止（P0-3）
# - ML_TRAINING_PER_MODEL_TIMEOUT=1800: 1 モデル 30 分上限（既存デフォルト）
export ML_TRAINING_N_JOBS="${ML_TRAINING_N_JOBS:--1}"
export ML_TRAINING_MODE="${ML_TRAINING_MODE:-true}"
export ML_TRAINING_PER_MODEL_TIMEOUT="${ML_TRAINING_PER_MODEL_TIMEOUT:-1800}"

# Phase 90: macOS Apple Silicon N-BEATS ハング対策
# PyTorch と sklearn/LightGBM の OpenMP/BLAS スレッド競合を回避
# CLAUDE.md 既知問題「macOS 上のテスト連続実行時 SEGFAULT」と同根
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-0}"

# Optuna 試行回数（引数指定 or デフォルト 50）
N_TRIALS="${1:-50}"

# ログディレクトリ作成
LOG_DIR="$PROJECT_ROOT/logs/ml_local"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/training_${TIMESTAMP}.log"

echo "============================================================================"
echo "📊 Phase 90: ローカル ML 再学習開始"
echo "============================================================================"
echo "  N_TRIALS:                       $N_TRIALS"
echo "  ML_TRAINING_N_JOBS:             $ML_TRAINING_N_JOBS (RF 並列度・-1=全コア)"
echo "  ML_TRAINING_MODE:               $ML_TRAINING_MODE (cross_asset リーク防止)"
echo "  ML_TRAINING_PER_MODEL_TIMEOUT:  $ML_TRAINING_PER_MODEL_TIMEOUT 秒 (1 モデル上限)"
echo "  LOG_FILE:                       $LOG_FILE"
echo "============================================================================"

# モデルバックアップ（v8 失敗時にロールバック可能）
if [ -f "models/production/ensemble_full.pkl" ]; then
    BACKUP_FILE="models/production/ensemble_full.pre_v8_${TIMESTAMP}.pkl.bak"
    echo ""
    echo "💾 既存モデルをバックアップ: $BACKUP_FILE"
    cp models/production/ensemble_full.pkl "$BACKUP_FILE"
fi
if [ -f "models/production/production_model_metadata.json" ]; then
    cp models/production/production_model_metadata.json \
       "models/production/production_model_metadata.pre_v8_${TIMESTAMP}.json.bak"
fi

START=$(date +%s)

# Step 1: データ収集
echo ""
echo "📊 Step 1: 365 日分データ収集"
echo "----------------------------------------------------------------------------"
"$PYTHON" src/backtest/scripts/collect_historical_csv.py --days 365 --symbol BTC/JPY 2>&1 | tee -a "$LOG_FILE"
ls -lh src/backtest/data/historical/ 2>&1 | tee -a "$LOG_FILE"

# Step 2: ML モデル学習
# Phase 90α (v8e): メタラベリング有効化（Phase 73-D Triple Barrier Method）
# 運用側 ml.mode=quality_filter と学習側の整合性を回復
# meta_tp/sl_ratio は tight_range の運用 TP/SL（0.7% / 0.86%）に合わせる
echo ""
echo "🤖 Step 2: ML モデル学習 (LGB/XGB/RF/N-BEATS) - メタラベリング有効"
echo "----------------------------------------------------------------------------"
"$PYTHON" scripts/ml/create_ml_models.py \
    --model full \
    --n-classes 3 \
    --threshold 0.005 \
    --use-smote \
    --optimize \
    --n-trials "$N_TRIALS" \
    --verbose \
    --meta-label \
    --meta-tp-ratio 0.007 \
    --meta-sl-ratio 0.0086 2>&1 | tee -a "$LOG_FILE"

# Step 3: HMM 学習
echo ""
echo "🧬 Step 3: HMM レジーム分類器学習"
echo "----------------------------------------------------------------------------"
"$PYTHON" scripts/ml/train_hmm_regime.py --days 365 --symbol BTC/JPY 2>&1 | tee -a "$LOG_FILE" || {
    echo "⚠️ HMM 学習失敗（fail-open 設計で本番は uniform 1/3 動作）" | tee -a "$LOG_FILE"
}

# Step 4: モデル検証
echo ""
echo "🔍 Step 4: モデル検証"
echo "----------------------------------------------------------------------------"
if [ ! -f "models/production/ensemble_full.pkl" ]; then
    echo "❌ ensemble_full.pkl 不存在" | tee -a "$LOG_FILE"
    exit 1
fi

"$PYTHON" -c "
import json
m = json.load(open('models/production/production_model_metadata.json'))
print(f'  特徴量数: {len(m.get(\"feature_names\", []))}')
print(f'  個別モデル: {m.get(\"individual_models\", [])}')
print(f'  作成日時: {m.get(\"created_at\", \"unknown\")}')
print(f'')
print(f'  === 各モデル macro F1 (真の性能) ===')
perf = m.get('performance_metrics', {})
for model_name in ['lightgbm', 'xgboost', 'random_forest', 'nbeats']:
    if model_name in perf:
        p = perf[model_name]
        print(f'  {model_name:15s}: f1={p.get(\"f1_score\", \"-\"):.4f} | cv_f1={p.get(\"cv_f1_mean\", \"-\"):.4f} ±{p.get(\"cv_f1_std\", 0):.4f}')
" 2>&1 | tee -a "$LOG_FILE"

END=$(date +%s)
ELAPSED=$((END - START))
ELAPSED_MIN=$((ELAPSED / 60))

echo ""
echo "============================================================================"
echo "✅ ローカル ML 再学習完了"
echo "============================================================================"
echo "  総所要時間:   ${ELAPSED_MIN} 分 (${ELAPSED} 秒)"
echo "  ログ:         $LOG_FILE"
echo "  ロールバック: cp $BACKUP_FILE models/production/ensemble_full.pkl"
echo ""
echo "💡 次のアクション:"
echo "  1. macro F1 を Phase 84/89-buggy と比較"
echo "  2. 改善が微小なら Phase 90α (ラベリング再設計) 着手"
echo "  3. 改善があれば git add models/ && commit && push でデプロイ"
echo "============================================================================"
