#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────────────────
# 1) テスト用ディレクトリを作成
# ────────────────────────────────────────────────────────
UNIT_BASE="tests/unit"
for d in data backtest execution strategy risk ml main scripts; do
  mkdir -p "${UNIT_BASE}/${d}"
done

INT_BASE="tests/integration"
for d in bybit main; do
  mkdir -p "${INT_BASE}/${d}"
done

# ────────────────────────────────────────────────────────
# 2) ユニットテストの振り分け
# ────────────────────────────────────────────────────────
# (元ファイルが tests/unit 以下にある想定)
mv tests/unit/test_fetcher*.py      "${UNIT_BASE}/data/"         2>/dev/null || true
mv tests/unit/test_streamer.py      "${UNIT_BASE}/data/"         2>/dev/null || true

mv tests/unit/test_backtest_engine.py  "${UNIT_BASE}/backtest/"  2>/dev/null || true
mv tests/unit/test_metrics.py          "${UNIT_BASE}/backtest/"  2>/dev/null || true
mv tests/unit/test_entry_exit.py       "${UNIT_BASE}/backtest/"  2>/dev/null || true
mv tests/unit/test_optimizer*.py       "${UNIT_BASE}/backtest/"  2>/dev/null || true

mv tests/unit/test_execution_engine*.py "${UNIT_BASE}/execution/" 2>/dev/null || true

mv tests/unit/test_strategy*.py       "${UNIT_BASE}/strategy/"    2>/dev/null || true

mv tests/unit/test_manager.py         "${UNIT_BASE}/risk/"        2>/dev/null || true

mv tests/unit/test_preprocessor.py    "${UNIT_BASE}/ml/"          2>/dev/null || true
mv tests/unit/test_target.py          "${UNIT_BASE}/ml/"          2>/dev/null || true
mv tests/unit/test_model*.py          "${UNIT_BASE}/ml/"          2>/dev/null || true
mv tests/unit/test_ml_optimizer.py    "${UNIT_BASE}/ml/"          2>/dev/null || true

mv tests/unit/test_main_train.py      "${UNIT_BASE}/main/"        2>/dev/null || true

mv tests/unit/test_walkforward.py     "${UNIT_BASE}/scripts/"     2>/dev/null || true

# ────────────────────────────────────────────────────────
# 3) 統合テストの振り分け
# ────────────────────────────────────────────────────────
# bybit の E2E（もともと tests/integration 直下）
mv tests/integration/test_bybit_e2e.py "${INT_BASE}/bybit/"     2>/dev/null || true

# main の E2E（もともと tests/ 直下）
if [ -f tests/test_main_e2e.py ]; then
  mv tests/test_main_e2e.py            "${INT_BASE}/main/"   \
    && echo "Moved tests/test_main_e2e.py → ${INT_BASE}/main/"
else
  echo "→ tests/test_main_e2e.py が見つかりませんでした。"
fi

echo "✅ テストフォルダの整理が完了しました。"
