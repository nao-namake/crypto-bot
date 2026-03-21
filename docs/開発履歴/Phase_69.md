# Phase 69: SL超過修正 + 逆張りショート対策 + 孤児SL修正 + SLタイムアウト延長 + レジーム閾値調整 + SL監査・ML再学習 + SL成行化・同方向制限

**期間**: 2026年3月14日-21日
**状態**: ✅ 完了

| 変更 | 内容 | 状態 |
|------|------|------|
| **修正1** | SL計算からentry_fee除去（バグ修正） | ✅ 完了 |
| **修正2** | normal_rangeにトレンド型戦略の重みを付与（設定変更） | ✅ 完了 |
| **修正3** | EMAトレンド方向フィルタ追加（逆張りペナルティ） | ✅ 完了 |
| **Phase 69.2** | 孤児TP/SL注文修正（複数VP決済時の兄弟VP一括クリーンアップ） | ✅ 完了 |
| **Phase 69.3** | SLタイムアウト延長（300→900秒） | ✅ 完了 |
| **Phase 69.4** | ML信頼度固定問題調査（モデル再学習が必要） | 🔍 調査完了 |
| **Phase 69.5** | レジーム閾値調整（tight_range偏重修正） | ✅ 完了 |
| **Phase 69.6** | MLコード修正（lookahead=1復元・Cal廃止）+ SL監査バグ修正 + ML再学習 | ✅ 完了 |
| **Phase 69.8** | SL注文を成行化（stop_limit→stop） + 同方向ポジション制限（1個上限） | ✅ 完了 |

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

---

## Phase 69.2: 孤児TP/SL注文修正（2026年3月16日）

### 問題

複数回エントリーで複数VP（仮想ポジション）が存在する場合、1つのVP決済時に他のVPのTP/SL注文がbitbank上に孤児として残留する。

**発生メカニズム**:
1. 3回のsellエントリー → 3 VP × 3 SL注文（各VPに`sl_order_id`）
2. VP1のSLタイムアウト → `_execute_position_exit`でVP1のSLのみキャンセル
3. VP2, VP3のSL注文がbitbank上に孤児として残留

**根本原因**: `_execute_position_exit`（line 1112-1113）が`position.get("sl_order_id")`で1つのVPのIDしか取得しない。

### 修正内容

`_execute_position_exit`に`virtual_positions`パラメータを追加。決済成功後、同サイドの全VPのTP/SL注文を`_cleanup_sibling_vp_orders()`で一括キャンセル。

### 変更ファイル

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `src/trading/execution/stop_manager.py` | `_cleanup_sibling_vp_orders()`追加、`_execute_position_exit`/`_evaluate_position_exit`/`_check_stop_limit_timeout`にvirtual_positions伝搬、`detect_auto_executed_orders`にも兄弟クリーンアップ追加 |
| 2 | `tests/unit/trading/execution/test_stop_manager.py` | `TestPhase692SiblingVPCleanup`テスト5件追加 |

### テスト

```
2019 passed, 1 skipped, 75.22% coverage
flake8/black/isort: all PASS
```

- `test_sibling_vp_sl_cancelled_on_exit` — 兄弟VPのSL/TPがキャンセルされる
- `test_sibling_cleanup_skips_opposite_side` — 反対サイドのVPは対象外
- `test_sibling_cleanup_clears_order_ids` — クリーンアップ後、IDがクリアされる
- `test_no_sibling_cleanup_without_virtual_positions` — 後方互換性テスト
- `test_sibling_cleanup_error_does_not_block` — エラー時も決済は成功

---

## Phase 69.3: SLタイムアウト延長（2026年3月19日）

### 問題

stop_limit注文がINACTIVE状態のまま300秒（5分）タイムアウト → 成行フォールバック → スリッページで目標SL大幅超過。

| 取引 | タイムアウト経過 | 目標SL | 実損 | 超過率 |
|------|---------------|--------|------|--------|
| 3/15 19:31 | 4484秒 | 500円 | 853円 | 71% |
| 3/16 08:07 | — | 500円 | 887円 | 77% |
| 3/16 13:53 | 461秒 | 500円 | 819円 | 64% |
| 3/17 19:10 | 449秒 | 500円 | 682円 | 36% |

### 修正内容

`stop_limit_timeout`を300秒→**900秒**（15分）に延長。Bot実行間隔（5分）の3回分を確保し、stop_limit指値の約定確率を向上。

### 変更ファイル

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `config/core/thresholds.yaml` | `stop_limit_timeout: 300` → `900` |

---

## Phase 69.4: ML信頼度固定問題調査（2026年3月19日）

### 問題

ML信頼度が0.437-0.440でほぼ固定。MLが入力変化に対して無反応。

### 調査結果

- **根本原因**: モデル精度46-47%（ランダム水準）、全予測がHOLDで信頼度~0.4545固定
- LightGBM: 46.9%, XGBoost: 46.1%, RandomForest: 47.4%
- HOLDクラスが支配的（予測の100%がHOLD）
- 信頼度 = max(P(SELL)=0.24, **P(HOLD)=0.4545**, P(BUY)=0.30)

### 結論

コード修正では解決不可。**モデル再学習**が必要。

---

## Phase 69.5: レジーム閾値調整（2026年3月19日）

### 問題

レジーム分類がほぼ常にtight_range（推定90%+） → normal_range/trending用のPhase 69修正（トレンド型戦略重み・EMAフィルタ）が機能しない。

### 原因

| レジーム | 判定条件 | 問題 |
|---------|---------|------|
| tight_range | BB幅<3%, 価格変動<2% | 閾値が広すぎ（通常相場が全てマッチ） |
| trending | ADX>25, EMA傾き>0.3% | EMA傾き閾値が厳しすぎ（実現は月1-2回） |
| normal_range | BB幅<5%, ADX<20 | tight_rangeで先に引っかかり機能しない |

### 修正内容

| パラメータ | 修正前 | 修正後 |
|-----------|--------|--------|
| tight_range BB幅 | 3.0% | **2.0%** |
| tight_range 価格変動 | 2.0% | **1.2%** |
| trending ADX | 25 | **22** |
| trending EMA傾き | 0.3% | **0.1%** |
| normal_range ADX | 20 | **22** |
| trend_filter EMA傾き | 0.3% | **0.1%** |

### バックテスト結果（レジーム分布改善）

| レジーム | 修正前(推定) | 修正後 |
|---------|------------|--------|
| tight_range | ~90% | **60%** (5,171) |
| trending | ~0% | **30%** (2,608) |
| normal_range | ~5% | **10%** (856) |
| high_volatility | <1% | <1% (8) |

### 追加修正: バックテストSeriesエラー

`backtest_runner.py`で`features_df.iloc[i]`（Series）を`classify()`に渡していたバグを修正。`iloc[start:i+1]`（DataFrame、直近50行スライス）に変更し、BB幅・価格変動率の正しい計算を保証。

### 変更ファイル

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `config/core/thresholds.yaml` | レジーム閾値6箇所更新 + trend_filter EMA閾値整合 |
| 2 | `src/core/services/market_regime_classifier.py` | デフォルト値・docstring更新 |
| 3 | `src/core/execution/backtest_runner.py` | Seriesエラー修正（iloc[i]→iloc[start:i+1]） |
| 4 | `tests/unit/services/test_market_regime_classifier.py` | テスト閾値・アサーション値更新 |

### テスト結果

```
2019 passed, 1 skipped, 75.22% coverage
flake8/black/isort: all PASS
```

---

## Phase 69.6: MLコード修正 + SL監査バグ修正 + ML再学習（2026年3月20日）

### MLコード修正内容

Phase 69.4で判明したML信頼度固定問題への対応として、学習コードを修正しML再学習を実施。

| 修正 | 内容 |
|------|------|
| lookahead復元 | lookahead=4→**1**に戻す（Phase 69.4で4に変更していたが、1が正しい設定） |
| Calibration廃止 | CalibratedClassifierCVを削除（3クラス分類で信頼度を歪めていた） |
| RF下限維持 | RandomForest `n_estimators`下限100を維持 |

### SLシステム監査バグ修正

SLシステム全体監査により発見された2件のP0バグを修正。

#### バグ1: position_restorer.pyのsl_placed_at復元が古いフィールドを参照

Phase 69.6で`sl_placed_at`フィールドを永続化に追加したが、position_restorerの復元側が`saved_at`のみを参照していた。

```python
# Before（バグ）
sl_placed_at = sl_state.get("saved_at")

# After（修正）
sl_placed_at = sl_state.get("sl_placed_at") or sl_state.get("saved_at")
```

通常は`saved_at`≒`sl_placed_at`だが、SL再配置時にはタイミングが乖離する可能性があった。

#### バグ2: SL再配置後のsl_order_id取得が永続化ファイル読み戻しに依存

`_replace_sl_order()`がreturn Noneだったため、SL再配置成功後にsl_persistence.load()で読み戻していた。
`_replace_sl_order()`の例外時に永続化保存がスキップされると古いデータを返すリスクがあった。

```python
# Before（リスクあり）
await self._replace_sl_order(position, stop_loss, bitbank_client)
sl_state = self.sl_persistence.load()
position["sl_order_id"] = sl_state[entry_side].get("sl_order_id")

# After（安全）
new_sl_order_id = await self._replace_sl_order(position, stop_loss, bitbank_client)
if new_sl_order_id:
    position["sl_order_id"] = new_sl_order_id
```

### SL監査ファイル変更

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `src/trading/execution/position_restorer.py` L219 | `sl_placed_at`フィールド優先復元 |
| 2 | `src/trading/execution/stop_manager.py` L1563-1621 | `_replace_sl_order()`に`Optional[str]`戻り値追加 |
| 3 | `src/trading/execution/stop_manager.py` L1012-1024 | 永続化読み戻しから直接参照に変更 |

### ML再学習結果

#### Full モデル（55特徴量）

| モデル | Test F1 | CV F1 | 信頼度mean | 信頼度std | 信頼度range |
|--------|---------|-------|-----------|----------|------------|
| LightGBM | 0.449 | 0.417±0.015 | 0.422 | 0.080 | [0.334, 0.691] |
| XGBoost | 0.440 | 0.406±0.017 | 0.466 | 0.100 | [0.334, 0.877] |
| RandomForest | 0.456 | 0.414±0.025 | 0.429 | 0.056 | [0.334, 0.646] |

#### Basic モデル（49特徴量）

| モデル | Test F1 | CV F1 | 信頼度mean | 信頼度std | 信頼度range |
|--------|---------|-------|-----------|----------|------------|
| LightGBM | 0.452 | 0.427±0.018 | 0.452 | 0.105 | [0.335, 0.834] |
| XGBoost | 0.449 | 0.408±0.022 | 0.529 | 0.125 | [0.336, 0.982] |
| RandomForest | 0.454 | 0.420±0.018 | 0.434 | 0.067 | [0.335, 0.671] |

#### Phase 69.4との比較（信頼度固定問題の改善）

| 指標 | Phase 69.4（問題） | Phase 69.6（修正後） |
|------|-------------------|---------------------|
| 信頼度分布 | mean=0.4545, std≈0 | mean=0.452, **std=0.105** |
| 信頼度range | [0.437, 0.440]（ほぼ固定） | [0.335, 0.834]（**正常分散**） |
| 予測多様性 | 100% HOLD | BUY/HOLD/SELL分散 |

Calibration廃止とlookahead=1復元により、信頼度の分散が正常化。入力変化に対してモデルが適切に反応するようになった。

### PnL計算修正（Phase 69.7）

standard_analysis.pyの損益計算がDBベースだったため、SLタイムアウト決済が漏れて+1,000円と誤表示されていた問題を修正。

**原因**: DBにはGCPログ由来のTP決済のみ記録（SLタイムアウト決済は`sync_exit_records`のログパターンに未対応）。

**修正**: bitbank APIの`profit_loss`フィールドを直接使用（最も信頼できるソース）。

```python
# Phase 69.7: bitbank APIから直接PnL取得
trades = client.exchange.fetch_my_trades("BTC/JPY", limit=100)
for t in trades:
    info = t.get("info", {})
    pnl = float(info.get("profit_loss", 0))      # 決済時のみ非ゼロ
    fee = float(info.get("fee_occurred_amount_quote", 0))  # 実発生手数料
```

| 指標 | 修正前（DB） | 修正後（bitbank API） |
|------|------------|-------------------|
| 総損益 | +1,000円 | **-2,796円** |
| 決済件数 | TP:2件のみ | TP:3 SL:5 計8件 |
| 勝率 | 33.3% | 37.5% |
| 手数料合計 | 不明 | 1,544円 |

**手数料フィールドの発見**:
- `fee_amount_quote`: ccxtが読む値（決済時にエントリー手数料が移転されるため不正確）
- `fee_occurred_amount_quote`: **実発生タイミングの手数料**（正確）
- 合計は一致するが、個別取引レベルでは配分が異なる

### 変更ファイル

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `src/trading/execution/position_restorer.py` | sl_placed_atフィールド優先復元 |
| 2 | `src/trading/execution/stop_manager.py` | _replace_sl_order()戻り値追加 + 永続化読み戻し回避 |
| 3 | `scripts/live/standard_analysis.py` | bitbank API PnL取得（_fetch_pnl_from_bitbank_api追加） |

### テスト結果

```
181 passed（SL関連テスト）
全テスト通過確認済み
```

---

## Phase 69.8: SL成行化 + 同方向ポジション制限（2026年3月21日）

### 背景

72時間の実績で**-5,805円**。根本問題:

1. **SL損失が目標500円を平均71%超過**（平均-856円）→ stop_limitの約定失敗→成行フォールバック時のスリッページ
2. **同方向に複数エントリー**して合算SLが倍増（0.02BTC以上のSL 6件、追加損失2,177円）
3. 勝率37.5%に対し必要勝率65.1%（RR比1:1.87のため）

### 修正1: SL注文をstop_limit → stop（成行）に変更

**根拠**:
- 現行のstop_limitは0.8%のslippage_bufferを設定 → SL発動時に実質0.8%の余分な損失余地
- さらにタイムアウト（900秒）後の成行フォールバックでさらにスリッページ
- 成行SLなら即時約定。手数料0.1%（Taker）は発生するが、現行のスリッページ平均356円（超過分）より遥かに安い
- BTC/JPYは流動性が高く、成行SLのスリッページは軽微

**変更内容**: 設定変更のみ（コード変更不要）

```yaml
# config/core/thresholds.yaml
stop_loss:
  order_type: stop  # 旧: stop_limit
```

既存コードの`tp_sl_manager.py`と`stop_manager.py`は`order_type`設定で分岐済み。`stop`の場合はlimit_price計算をスキップする。

**期待効果**:
- SL平均損失: -856円 → -500〜-550円に改善（手数料0.1%のみ追加）
- タイムアウトフォールバック: 不要になる（即時約定）
- 月間損失削減: 約3,000〜4,000円

### 修正2: 同方向の重複エントリーを制限

**方針**: 同方向1ポジション上限をデフォルト設定。反対方向（ヘッジ）は許可。

**問題の実例**:
- buy × 2ポジション → 両方SL発動 → 損失1,000円（本来500円）
- 0.02BTC以上のSL 6件で追加損失2,177円

**変更内容**:

```yaml
# config/core/thresholds.yaml
position_management:
  max_same_direction_positions: 1  # 新設定
```

`PositionLimits._check_same_direction_positions()`メソッドを追加:
- `virtual_positions`内の同じ`side`のポジション数をカウント
- 上限超過時は`{"allowed": False, "reason": "同方向ポジション制限"}`を返す
- `check_limits()`フローの最大ポジション数チェック直後に実行（追加フィルタ）
- 設定値0で制限無効化可能

### 変更ファイル

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `config/core/thresholds.yaml` | `order_type: stop` + `max_same_direction_positions: 1` |
| 2 | `src/trading/position/limits.py` | `_check_same_direction_positions()`追加 + `check_limits()`に組み込み |
| 3 | `tests/unit/trading/position/test_limits.py` | 同方向制限テスト7件追加 |
| 4 | `CLAUDE.md` | Phase 69.8しおり更新 + SL注文タイプ更新 |

### テスト結果

```
2050 passed, 1 skipped, 75.41% coverage
flake8/black/isort: all PASS
```

### 新規テスト（7件）

- `test_same_direction_blocked` — 同方向ポジションが上限に達している場合ブロック
- `test_opposite_direction_allowed` — 反対方向のポジションは制限しない
- `test_no_existing_positions_allowed` — 既存ポジションなしの場合は許可
- `test_limit_disabled_when_zero` — 設定値0で制限無効
- `test_limit_two_allows_second` — 上限2の場合、1件目は許可
- `test_no_side_info_skips` — side情報がない場合はスキップ
- `test_mixed_positions_counts_correctly` — buy/sell混在でも正しくカウント

### 設計判断

#### SLを成行にする理由

| 比較項目 | stop_limit（旧） | stop（新） |
|---------|----------------|-----------|
| 約定確実性 | gap throughリスクあり | **100%**（即時約定） |
| 価格制御 | slippage_buffer 0.8%以内 | なし（市場価格） |
| タイムアウト対応 | 900秒→成行フォールバック | **不要** |
| 実績SL損失 | 平均-856円（71%超過） | 推定-500〜550円 |
| 手数料 | 0.1%（Taker） | 0.1%（Taker） |

BTC/JPYは24時間取引で流動性が高く、成行SLのスリッページは通常1-2ティック（数百円/BTC）程度。stop_limitの約定失敗リスクと比較して、成行の方が損失の予測可能性が遥かに高い。

#### 同方向制限を完全禁止ではなく設定で制御する理由

将来的に勝率が改善した場合、同方向2ポジション（ピラミッディング）が有効になる可能性がある。`max_same_direction_positions`を設定で管理することで、将来の戦略変更に柔軟に対応できる。現時点では各エントリーが独立したTP/SLを持つ設計のため、同方向2ポジションが同時にSLに引っかかると損失が倍増するリスクがある。
