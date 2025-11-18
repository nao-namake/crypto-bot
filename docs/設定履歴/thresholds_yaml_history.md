# thresholds.yaml 設定状態記録

**最終更新**: 2025-11-18

---

## このファイルの目的

`config/core/thresholds.yaml`の現在の設定状態を記録し、設定の意味・構造・使われ方を文書化する。

---

## 現在の設定状態

### ML統合設定 (ml.strategy_integration)

**基本統合ロジック**:
- `ml_weight`: 0.35（ML予測の重み35%）
- `strategy_weight`: 0.7（戦略シグナルの重み70%）
- `min_ml_confidence`: 0.45（ML統合最小信頼度45%）
- `high_confidence_threshold`: 0.60（高信頼度閾値60%）

**3段階統合ロジック**:
1. **信頼度 < 0.45**: 戦略シグナルのみ使用
2. **信頼度 0.45-0.60**: 加重平均（戦略70% + ML30%）
3. **信頼度 ≥ 0.60**: ボーナス/ペナルティ適用

**戦略信号エンコーディング**:
- `signal_encoding`: "action_times_confidence"
- buy = +confidence, hold = 0, sell = -confidence

### レジーム別ML統合設定 (ml.regime_ml_integration)

**レジーム別ML重み調整**:

| レジーム | ML重み | 説明 |
|---------|--------|------|
| `tight_range` | 0.2 | 横ばい・低ボラ - 戦略重視（実績99.4%）|
| `normal_range` | 0.3 | 通常レンジ - バランス型 |
| `trending` | 0.4 | トレンド相場 - ML重視 |
| `デフォルト` | 0.3 | 未分類時のフォールバック |

**有効化設定**: `enabled: true`（レジーム別ML統合有効）

### TP/SL基本設定 (position_management)

**基本TP/SL**（normal_range用）:
- `tp_rate`: 0.01（利確1.0%）
- `sl_rate`: 0.007（損切0.7%）
- **RR比**: 1.0 / 0.7 = **1.43:1**

**適応型ATR SL調整**:
- 低ボラティリティ: `2.5 × ATR`
- 通常ボラティリティ: `2.0 × ATR`
- 高ボラティリティ: `1.5 × ATR`

### レジーム別TP/SL設定 (position_management.regime_based)

**tight_range（横ばい・低ボラ）**:
- `tp_rate`: 0.006（利確0.6%）
- `sl_rate`: 0.008（損切0.8%）
- **RR比**: 0.6 / 0.8 = **0.75:1**
- **戦略**: 頻繁利確・勝率重視

**normal_range（通常レンジ）**:
- `tp_rate`: 0.01（利確1.0%）
- `sl_rate`: 0.007（損切0.7%）
- **RR比**: 1.0 / 0.7 = **1.43:1**
- **戦略**: バランス型

**trending（トレンド相場）**:
- `tp_rate`: 0.02（利確2.0%）
- `sl_rate`: 0.02（損切2.0%）
- **RR比**: 2.0 / 2.0 = **1.0:1**
- **戦略**: トレンドフォロー・大きな値幅狙い

**有効化設定**: `use_regime_based: true`（レジーム別TP/SL有効）

### 証拠金維持率設定 (margin.thresholds)

**証拠金維持率閾値**:
- `warning`: 120.0%（警告レベル）
- `critical`: 80.0%（緊急レベル・bitbank最低維持率遵守）
- `safe`: 150.0%（安全レベル）

**追加設定**:
- `force_close_below_critical`: true（critical未満で強制決済）

### バックテスト設定 (backtest)

**初期設定**:
- `initial_jpy_balance`: 100000（初期残高10万円）
- `initial_btc_balance`: 0（BTC初期保有なし）
- `use_realistic_fees`: true（リアル手数料適用）
- `use_realistic_slippage`: true（リアルスリッページ適用）

**手数料設定**:
- `maker_fee`: -0.0002（Maker手数料 -0.02%・リベート）
- `taker_fee`: 0.0012（Taker手数料 0.12%）

**スリッページ設定**:
- `slippage_bps`: 5（5bps = 0.05%）

### 戦略パラメータ設定

**各戦略のパラメータはthresholds.yamlに定義**:

| 戦略 | 主要パラメータ例 |
|------|----------------|
| ATRBased | atr_period, atr_multiplier, rsi_period |
| DonchianChannel | donchian_period, breakout_threshold |
| ADXTrendStrength | adx_period, adx_threshold, di_threshold |
| BBReversal | bb_period, bb_std, rsi_oversold/overbought |
| StochasticReversal | k_period, d_period, oversold/overbought |
| MACDEMACrossover | macd_fast/slow/signal, ema_period |

**設定場所**: `config/core/thresholds.yaml` の各戦略セクション

### Optuna最適化結果 (optuna_optimized)

**3階層構造**（Phase 52.4-A構造改善）:

```yaml
optuna_optimized:
  risk_management:
    kelly:
      # Kelly基準設定
    position_limits:
      # ポジション制限設定

  strategy_parameters:
    # 各戦略の最適化パラメータ

  ml_integration:
    # ML統合最適化設定

  ml_hyperparameters:
    lightgbm:
      # LightGBMハイパーパラメータ
    xgboost:
      # XGBoostハイパーパラメータ
    random_forest:
      # RandomForestハイパーパラメータ
```

**最適化対象**: リスク管理・戦略パラメータ・ML統合・MLハイパーパラメータ

---

## 使用箇所

| 項目 | 使用箇所 |
|------|---------|
| ML統合設定 | `src/core/orchestration/ml_adapter.py` (MLAdapter) |
| レジーム別ML統合 | `src/core/orchestration/ml_adapter.py` (get_regime_ml_weight) |
| TP/SL設定 | `src/trading/execution/executor.py` (calculate_tp_sl) |
| レジーム別TP/SL | `src/trading/execution/tp_sl_calculator.py` |
| 証拠金維持率 | `src/trading/balance/monitor.py` (MarginMonitor) |
| バックテスト設定 | `src/backtest/backtest_runner.py` |
| 戦略パラメータ | `src/strategies/implementations/*.py` |
| Optuna結果 | `scripts/optimization/run_phase40_optimization.py` |

---

## 設定値の意味

### ML統合重み調整の考え方

**戦略重視 vs ML重視のバランス**:
- 戦略重視（ml_weight 0.2-0.3）: tight_range・実績重視
- バランス型（ml_weight 0.3）: normal_range・標準設定
- ML重視（ml_weight 0.4）: trending・トレンド判定強化

**信頼度閾値**:
- `min_ml_confidence` 0.45: ML統合率100%達成（Phase 41.8.5最適化）
- `high_confidence_threshold` 0.60: ボーナス/ペナルティ適用ライン

### レジーム別TP/SLの考え方

**tight_range（TP 0.6% / SL 0.8%）**:
- 頻繁利確・勝率重視
- 横ばい相場で小さな利益を積み重ねる

**normal_range（TP 1.0% / SL 0.7%）**:
- RR比1.43:1・バランス型
- Phase 51.6最終調整後の基本設定

**trending（TP 2.0% / SL 2.0%）**:
- トレンドフォロー・大きな値幅狙い
- RR比1:1だがトレンド継続時の大幅利益期待

### 証拠金維持率閾値

**critical 80.0%の意味**:
- bitbank最低証拠金維持率（80%）を確実に遵守
- Phase 49.18で100.0% → 80.0%に変更
- 80%未満で強制決済（force_close_below_critical: true）

---

## 設定変更時の注意点

1. **ML統合設定変更**: バックテストで効果検証必須
2. **TP/SL変更**: RR比・勝率への影響を慎重評価
3. **レジーム別設定変更**: 各レジームの特性理解が重要
4. **証拠金維持率変更**: bitbank規約遵守（80%以上）
5. **Optuna最適化結果**: 統計的有意性確認後に適用

---

## 参照

- **動的閾値設定ファイル**: `config/core/thresholds.yaml`
- **統一設定**: `config/core/unified.yaml`
- **戦略設定**: `config/core/strategies.yaml`
- **Optuna最適化**: `scripts/optimization/run_phase40_optimization.py`
- **開発履歴**: `docs/開発履歴/`

---

**最終更新**: 2025-11-18
