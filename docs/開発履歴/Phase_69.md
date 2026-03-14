# Phase 69: SL超過修正 + 逆張りショート対策

**期間**: 2026年3月14日
**状態**: ✅ 完了・デプロイ待ち

| 変更 | 内容 | 状態 |
|------|------|------|
| **修正1** | SL計算からentry_fee除去（バグ修正） | ✅ 完了 |
| **修正2** | normal_rangeにトレンド型戦略の重みを付与（設定変更） | ✅ 完了 |
| **修正3** | EMAトレンド方向フィルタ追加（逆張りペナルティ） | ✅ 完了 |

---

## 背景

48時間ライブ分析で2つの重大問題を発見:

### 問題1: SL超過（目標500円→実損914円、83%超過）

SL計算で`entry_fee`を二重計上し、SL距離が0.09%と極端に狭い → タイムアウト → 成行決済 → スリッページで大損。

**GCPログ証拠**:
```
固定金額SL適用 - 目標最大損失=500円, エントリー手数料=172円, 決済手数料=172円, SL距離=10403円(0.09%)
ポジション決済完了: buy 0.020000 BTC (理由: SLタイムアウト) 損失:-914円
```

**原因**: `gross_loss = sl_target - exit_fee - entry_fee` — entry_feeはエントリー時に支払済み（サンクコスト）。SL予算から引くとSL距離が極端に狭くなる。

### 問題2: 逆張りショート連発

上昇トレンド中にSELLポジションばかり。レジーム判定がnormal_range/tight_rangeとなり、レンジ型戦略（ATR 60%+Donchian 30%）がSELLシグナルを出す。トレンド型戦略は重み0%で完全無効化されていた。

**GCPログ証拠**:
```
動的戦略選択: レジーム=normal_range, 戦略重み={ATRBased: 0.60, DonchianChannel: 0.30, ...ADXTrendStrength: 0.00, MACDEMACrossover: 0.00}
TP価格=11462034円 (sell)  ← SELL（ショート）ばかり
```

---

## 修正1: SL計算からentry_fee除去（バグ修正）

### 修正前後の比較（0.015 BTC @ 11,477,296円）

| | 修正前 | 修正後 |
|---|--------|--------|
| gross_loss | 500-172-172=**156円** | 500-172=**328円** |
| SL距離 | 10,400円(**0.09%**) | 21,867円(**0.19%**) |

SL距離が約2倍に改善。タイムアウトによる成行決済リスクが大幅に低下。

### 変更ファイル

#### `src/strategies/utils/strategy_utils.py`

```python
# Before:
entry_fee_rate = fixed_sl_config.get("fallback_entry_fee_rate", 0.001)
entry_fee = current_price * position_amount * entry_fee_rate
gross_loss = sl_target - exit_fee - entry_fee

# After:
# Phase 69: entry_feeはサンクコスト（エントリー時に支払済み）
gross_loss = sl_target - exit_fee
```

#### `src/trading/execution/tp_sl_manager.py`

```python
# Before:
entry_fee_rate = get_threshold(TPSLConfig.SL_FIXED_AMOUNT_ENTRY_FEE, 0.001)
entry_fee = avg_price * amount * entry_fee_rate
gross_needed = target - entry_fee - exit_fee

# After:
# Phase 69: entry_feeはサンクコスト → SL予算から除外
gross_needed = target - exit_fee
```

#### `config/core/thresholds.yaml`

```yaml
# Before:
include_entry_fee: true

# After:
include_entry_fee: false
```

---

## 修正2: normal_rangeにトレンド型戦略の重みを付与

上昇初期はADX < 25のためtrending判定されず、normal_rangeに分類。normal_rangeではトレンド型戦略が完全に無効化されていた問題を解決。

### `config/core/thresholds.yaml` — normal_range戦略重み

```yaml
# Before:
normal_range:
  ATRBased: 0.60
  StochasticReversal: 0.10
  DonchianChannel: 0.30
  BBReversal: 0.0
  ADXTrendStrength: 0.0
  MACDEMACrossover: 0.0

# After:
normal_range:
  ATRBased: 0.45
  StochasticReversal: 0.10
  DonchianChannel: 0.20
  BBReversal: 0.0
  ADXTrendStrength: 0.15
  MACDEMACrossover: 0.10
```

トレンド型戦略に合計25%の重みを付与。レンジ型は100%→75%に削減。

---

## 修正3: EMAトレンド方向フィルタ追加

レンジレジーム判定時でも、明確なトレンド方向と逆のシグナルにペナルティを適用。

### `config/core/thresholds.yaml` — フィルタ設定

```yaml
dynamic_strategy_selection:
  trend_filter:
    enabled: true
    ema_slope_threshold: 0.003  # 0.3%（trending判定0.7%より低い→早期検出）
    counter_trend_penalty: 0.5  # 逆トレンド信頼度50%に削減
```

### `src/strategies/base/strategy_manager.py` — `_apply_trend_filter()`

`_combine_signals()`内でシグナル統合前にフィルタを適用:

- EMA傾き > 0.3%（上昇）の時にSELLシグナルの信頼度を50%に削減
- EMA傾き < -0.3%（下降）の時にBUYシグナルの信頼度を50%に削減
- EMA傾きが閾値未満の場合はペナルティなし（フラット市場では無干渉）

---

## 変更ファイル一覧

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `config/core/thresholds.yaml` | include_entry_fee: false + normal_range重み変更 + trend_filter設定追加 |
| 2 | `src/strategies/utils/strategy_utils.py` | SL計算からentry_fee除去 |
| 3 | `src/trading/execution/tp_sl_manager.py` | SL計算からentry_fee除去 |
| 4 | `src/strategies/base/strategy_manager.py` | `_apply_trend_filter()`メソッド追加 |
| 5 | `tests/unit/strategies/utils/test_risk_manager.py` | SLテスト期待値更新（entry_fee除外） |
| 6 | `tests/unit/trading/execution/test_tp_sl_manager.py` | `TestPhase69FixedAmountSLNoEntryFee`に更新 |
| 7 | `tests/unit/services/test_dynamic_strategy_selector.py` | normal_range重みテスト更新 |
| 8 | `tests/unit/strategies/test_strategy_manager.py` | `TestPhase69TrendFilter`テスト4件追加 |
| 9 | `CLAUDE.md` | Phase 69しおり更新 + SL計算式更新 |

---

## テスト結果

```
2014 passed, 1 skipped, 75.25% coverage
flake8/black/isort: all PASS
```

### 新規・更新テスト

- `TestConfidenceBasedTPSL::test_low_confidence_tp_sl_400` — SL期待値更新（entry_fee除外）
- `TestConfidenceBasedTPSL::test_high_confidence_tp_sl_500` — SL期待値更新
- `TestConfidenceBasedTPSL::test_confidence_none_fallback` — SL期待値更新
- `TestConfidenceBasedTPSL::test_confidence_based_disabled` — SL期待値更新
- `TestPhase69FixedAmountSLNoEntryFee::test_sl_excludes_entry_fee` — exit_feeのみ考慮
- `TestPhase69FixedAmountSLNoEntryFee::test_sl_short_position` — ショートSL計算
- `TestPhase69FixedAmountSLNoEntryFee::test_sl_gross_needed_floor` — フォールバック
- `TestPhase69TrendFilter::test_uptrend_penalizes_sell` — 上昇中SELL信頼度削減
- `TestPhase69TrendFilter::test_downtrend_penalizes_buy` — 下降中BUY信頼度削減
- `TestPhase69TrendFilter::test_flat_market_no_penalty` — フラット市場ペナルティなし
- `TestPhase69TrendFilter::test_filter_disabled` — フィルタ無効時ペナルティなし

---

## 設計判断

### entry_feeをSL予算から除外する理由

entry_feeはエントリー注文が約定した時点で既に支払われた**サンクコスト**。SLの目的は「このポジションからの追加損失を制限する」ことであり、エントリー時の手数料はSL発動の有無に関係なく発生する固定費用。SL予算から差し引くとSL距離が極端に狭くなり、タイムアウト→成行決済→スリッページの連鎖で目標を大幅に超過する損失が発生する。

### TP計算ではentry_feeを引き続き考慮する理由

TP計算の目的は「純利益として500円を確保する」こと。純利益 = 含み益 - entry_fee - exit_fee なので、entry_feeを含めないとTP到達時の純利益が目標に達しない。TPとSLでentry_feeの扱いが異なるのは、目的の違い（純利益保証 vs 追加損失制限）に起因する。

### normal_rangeにトレンド型25%を付与した理由

上昇初期はADX < 25のためtrending判定されず、normal_rangeに分類される。従来のnormal_rangeではトレンド型戦略が0%で完全無効化されていたため、上昇トレンドを全く捉えられなかった。25%の重みを付与することで、normal_rangeでもトレンド方向のシグナルが少し反映される。

### EMAフィルタの閾値を0.3%にした理由

trending判定のEMA傾き閾値は0.7%（`market_regime.trending.ema_slope_threshold: 0.003`の2期間計算で実効~0.6-0.7%）。フィルタ閾値を0.3%に設定することで、trending判定より早くトレンド方向を検出し、逆張りシグナルを抑制する。
