#!/usr/bin/env bash
# =============================================================================
# ファイル名: scripts/run_pipeline.sh
# 説明:
#  - モデルの最適化（Optuna）、再学習
#  - モデルキャリブレーション
#  - 閾値スイープ（Pythonスクリプトで実行）
#  - 最良閾値のconfig反映
#  - 再キャリブレーション＆再バックテスト
#  - ウォークフォワード検証
#  - 最終レポート生成
# =============================================================================
set -euo pipefail

CONFIG="config/default.yml"
RESULT_DIR="results"
SWEEP_CSV="${RESULT_DIR}/threshold_sweep.csv"
WF_METRICS="${RESULT_DIR}/walk_forward_metrics.csv"
REPORT_DIR="${RESULT_DIR}/walk_forward_report"

BEST_MODEL="model/best_model.pkl"
CALIB_MODEL="model/calibrated_model.pkl"

echo "=== 0. ディレクトリ準備 ==="
mkdir -p "${RESULT_DIR}" "${REPORT_DIR}" "$(dirname "${BEST_MODEL}")"

echo "=== 0-A. optimize-and-train で再学習 ==="
python -m crypto_bot.main optimize-and-train \
  --config "${CONFIG}" \
  --model-out "${BEST_MODEL}" \
  --trials-out "${RESULT_DIR}/optuna_trials.csv"

echo "=== 0-B. モデルキャリブレーション ==="
python tools/calibrate_model.py \
  --model  "${BEST_MODEL}" \
  --output "${CALIB_MODEL}" \
  --config "${CONFIG}"

echo "=== 1. 閾値スイープ（Pythonスクリプト呼び出し） ==="
python tools/sweep_thresholds.py

if [[ ! -f "${SWEEP_CSV}" ]]; then
  echo "Error: Sweep結果ファイルが見つかりません: ${SWEEP_CSV}"
  exit 1
fi

# 最高利益の閾値を抽出（mean_total_profitが空でない最大のもの）
BEST_THRESH=$(awk -F',' 'NR>1 && $2 != "" && $2+0==$2 {if($2>max) {max=$2; th=$1}} END{print th}' "${SWEEP_CSV}")

if [[ -z "${BEST_THRESH}" ]]; then
  echo "Error: 閾値スイープで有効な閾値が見つかりませんでした。trade_logが空か、バックテスト失敗です。"
  echo "config/データ/モデルの整合性や、バックテストの成立可否を再確認してください。"
  exit 1
fi

echo "[OK] 最高利益の閾値 = ${BEST_THRESH}"

echo "=== 2. config に閾値を反映 (threshold=${BEST_THRESH}) ==="
if command -v yq > /dev/null 2>&1; then
  TMP_CFG="${CONFIG}.tmp$$"
  yq e ".strategy.params.threshold = ${BEST_THRESH}" "${CONFIG}" > "${TMP_CFG}"
  mv "${TMP_CFG}" "${CONFIG}"
else
  python3 -c "
import yaml
with open('${CONFIG}') as f:
    data = yaml.safe_load(f)
data['strategy']['params']['threshold'] = float('${BEST_THRESH}')
with open('${CONFIG}', 'w') as f:
    yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
"
fi

echo "=== 3. キャリブレーション（閾値反映後のモデル） ==="
python tools/calibrate_model.py \
  --model  "${BEST_MODEL}" \
  --output "${CALIB_MODEL}" \
  --config "${CONFIG}"

echo "=== 4. 再バックテスト ==="
python -m crypto_bot.main backtest \
  --config "${CONFIG}" \
  --stats-output "${RESULT_DIR}/backtest_recalib.csv"

echo "=== 5. ウォークフォワード ==="
python -m crypto_bot.scripts.walk_forward \
  --config "${CONFIG}" \
  --output "${WF_METRICS}"

echo "=== 6. 可視化 ==="
python tools/plot_walk_forward.py \
  --input  "${WF_METRICS}" \
  --output "${REPORT_DIR}"

echo "=== 完了: 生成物 ==="
echo "  * ${SWEEP_CSV}"
echo "  * ${CALIB_MODEL}"
echo "  * ${RESULT_DIR}/backtest_recalib.csv"
echo "  * ${WF_METRICS}"
echo "  * ${REPORT_DIR}/*.png"