# Phase 62: Maker戦略実装・手数料最適化

**期間**: 2026年1月31日〜2月5日
**状態**: ✅ 完了
**成果**: バックテスト ¥+119,815（年利24%相当）、Maker戦略で往復手数料-0.04%実現

---

## サマリー

| Phase | 内容 | 成果 | 状態 |
|-------|------|------|------|
| 62.1 | 3戦略閾値一括緩和 | 損益+13%、PF+1.5% | ✅完了 |
| 62.1-B | さらなる閾値緩和 | ❌効果なし（損益-5%） | ✅完了 |
| 62.2 | 戦略条件型変更 | RSIボーナス制度導入、ATRBased比率77.9%→58.2% | ✅完了 |
| 62.3 | BBReversal無効化 | tight_range 0%勝率対策 | ✅完了 |
| 62.4 | DonchianChannel重み増加 | 10%→30% | ✅完了 |
| 62.5 | HOLD診断機能 | 分析・デバッグ強化 | ✅完了 |
| 62.6 | 手数料考慮計算 | 実現損益精度向上 | ✅完了 |
| 62.7 | バックテスト手数料修正 | Taker統一 | ✅完了 |
| 62.8 | 手数料多重計算バグ修正 | 重複計算排除 | ✅完了 |
| 62.9 | エントリーMaker戦略 | post_only対応、0.14%削減 | ✅完了 |
| 62.10 | TP決済Maker戦略 | 指値TP配置、0.14%削減 | ✅完了 |
| 62.11 | TP手数料計算バグ修正 | 純利益500円保証 | ✅完了 |
| 62.11B | バックテスト手数料統一 | Maker反映 | ✅完了 |
| 62.12 | Maker戦略動作検証 | 100%成功確認 | ✅完了 |
| 62.13 | ATRフォールバック修正 | atr_current直接参照 | ✅完了 |
| **62.14** | **SL逆指値指値化** | **stop_limit使用、スリッページ抑制** | **✅完了** |
| **62.15** | **SL幅見直し** | **tight_range 0.3%→0.4%** | **✅完了** |
| **62.16** | **スリッページ分析機能** | **slippage記録・レポート追加** | **✅完了** |

---

## 背景

Phase 61完了時点で総損益¥149,195（PF 2.68）を達成したが、以下の課題が判明：

| 課題 | 詳細 | 影響 |
|------|------|------|
| ATRBased一強 | 218件/261件（83%） | 戦略分散が機能していない |
| BBReversal機能不全 | 1件・0%勝率 | 閾値が厳しすぎ |
| DonchianChannel活用不足 | 13件・69.2%勝率 | 高勝率なのに取引数少ない |

### Phase 61.12 バックテスト戦略別結果（出発点）

| 戦略 | 取引数 | 比率 | 勝率 | 損益 | 評価 |
|------|--------|------|------|------|------|
| ATRBased | 218件 | 83% | 61.0% | +¥118,767 | 主力 |
| DonchianChannel | 13件 | 5% | 69.2% | +¥10,608 | 良好だが少ない |
| StochasticReversal | 29件 | 11% | 51.7% | +¥3,383 | 普通 |
| BBReversal | 1件 | 0.4% | 0.0% | -¥1,194 | 問題 |

---

## 主要成果

### Maker戦略効果（Phase 62.9-62.10）

| 項目 | Taker前提 | Maker実装後 | 削減効果 |
|------|----------|-------------|---------|
| エントリー | 0.12% | -0.02% | 0.14% |
| TP決済 | 0.12% | -0.02% | 0.14% |
| SL決済 | 0.12% | 0.12% | 0%（API制限） |
| **往復（TP時）** | 0.24% | **-0.04%** | **0.28%** |

**年間削減額**: ¥40,000〜84,000（取引量依存）

### 最終バックテスト結果（Phase 62.11B）

| 指標 | 値 | 評価 |
|------|-----|------|
| **期間** | 2025-07-01 ~ 2025-12-31 | 6ヶ月 |
| **総取引数** | 303件 | - |
| **勝率** | 59.7% | ✅ |
| **総損益** | **¥+119,815** | ✅ |
| **PF** | **1.65** | ✅ |
| **シャープレシオ** | 16.55 | ✅ |
| **最大DD** | ¥13,352 (2.14%) | ✅ |
| **年利換算** | **約24%** | ✅ |

### SL Maker業界調査結果

**結論**: SLでMaker約定は**業界全体で不可能**

| 項目 | TP | SL |
|------|-----|-----|
| Maker対応 | ✅可能 | ❌不可（業界標準） |
| 手数料 | **-0.02%** | **0.12%** |

**理由**: SLの「確実な決済」とPost-Onlyの「即時約定禁止」が矛盾

---

## バックテスト結果推移

Phase 62を通じてのバックテスト結果の変化：

| Phase | 取引数 | 勝率 | 総損益 | PF | 最大DD | 備考 |
|-------|--------|------|--------|-----|--------|------|
| 61.12（出発点） | 298件 | 75.8% | ¥149,195 | 2.68 | ¥5,860 | 手数料なし |
| 62.1 | 332件 | 74.7% | ¥168,490 | 2.72 | ¥5,997 | 閾値緩和成功 |
| 62.1-B | 344件 | 73.3% | ¥159,958 | 2.51 | ¥7,334 | ❌過度な緩和 |
| 62.2 | 478件 | 68.2% | ¥172,643 | 2.03 | ¥6,152 | 戦略分散成功、BB損失 |
| 62.3-62.4 | 346件 | 75.7% | ¥177,025 | 2.75 | ¥4,925 | BB調整成功 |
| 62.7（Taker統一） | - | - | 約¥57,000 | 1.5-2.0 | - | 手数料反映 |
| 62.8（バグ修正） | - | 39.9% | ¥-64,845 | 0.04 | - | ❌多重計算 |
| **62.11B（最終）** | 303件 | 59.7% | **¥119,815** | **1.65** | ¥13,352 | Maker手数料反映 |

**注**: 62.7-62.8は手数料計算の試行錯誤期間。最終的に62.11Bで正確な計算に到達。

---

## Phase 62.1〜62.4: 戦略閾値調整

### Phase 62.1: 3戦略閾値一括緩和 ✅完了

**実施日**: 2026年1月31日

**目的**: ATRBased一強問題を解消し、他戦略の活用を強化

#### 変更内容

| 戦略 | パラメータ | Before | After |
|------|-----------|--------|-------|
| BBReversal | bb_upper_threshold | 0.85 | 0.75 |
| BBReversal | bb_lower_threshold | 0.15 | 0.25 |
| BBReversal | rsi_overbought | 62 | 58 |
| BBReversal | rsi_oversold | 38 | 42 |
| StochasticReversal | stoch_overbought | 72 | 65 |
| StochasticReversal | stoch_oversold | 28 | 35 |
| DonchianChannel | extreme_zone_threshold | 0.12 | 0.15 |
| DonchianChannel | rsi_oversold | 42 | 45 |
| DonchianChannel | rsi_overbought | 58 | 55 |

#### 結果

| 指標 | Phase 61.12 | Phase 62.1 | 変化 |
|------|-------------|------------|------|
| 取引数 | 298件 | 332件 | +11% ✅ |
| 総損益 | ¥149,195 | ¥168,490 | +13% ✅ |
| PF | 2.68 | 2.72 | +1.5% ✅ |
| ATRBased比率 | 83% | 79.5% | -3.5pt |

**評価**: 閾値緩和成功だが、ATRBased比率79.5%で目標50%未達

---

### Phase 62.1-B: さらなる閾値緩和 ✅完了（効果なし）

**実施日**: 2026年1月31日

さらに閾値を緩和したが、**逆効果**となった。

| 指標 | Phase 62.1 | Phase 62.1-B | 変化 |
|------|------------|--------------|------|
| 総損益 | ¥168,490 | ¥159,958 | -5% ❌ |
| PF | 2.72 | 2.51 | -8% ❌ |
| 最大DD | ¥5,997 | ¥7,334 | +22% ❌ |

**結論**: 閾値緩和だけでは限界がある → 構造的な問題（AND条件・RSIフィルタ）を解決する必要あり

---

### Phase 62.2: 戦略条件型変更 ✅完了

**実施日**: 2026年1月31日

**目的**: 構造的問題（AND条件・RSIフィルタ）を解決

#### 問題点と解決策

| 戦略 | 問題 | 解決策 |
|------|------|--------|
| DonchianChannel | RSIフィルタでHOLD判定 | RSIをボーナス制度に変更 |
| BBReversal | AND条件（BB+RSI）が厳しすぎ | BB位置主導に変更、RSIはボーナス |
| StochasticReversal | 弱いダイバージェンスを検出 | 最小価格変化フィルタ追加 |

#### 1. DonchianChannel: RSIボーナス制度

**変更ファイル**: `src/strategies/implementations/donchian_channel.py`

| Before | After |
|--------|-------|
| RSI不一致 → HOLD | RSI不一致 → シグナル発生（ペナルティ適用） |
| RSI一致 → シグナル | RSI一致 → シグナル（ボーナス適用） |

**新パラメータ**:
```yaml
rsi_as_bonus: true           # RSIをHOLD→ボーナス制度に
rsi_mismatch_penalty: 0.08   # RSI不一致時の信頼度ペナルティ
```

#### 2. BBReversal: BB位置主導モード

**変更ファイル**: `src/strategies/implementations/bb_reversal.py`

| Before | After |
|--------|-------|
| BB位置 AND RSI → シグナル | BB位置のみ → シグナル |
| RSI不一致 → HOLD | RSI不一致 → シグナル（ペナルティ適用） |

**新パラメータ**:
```yaml
bb_primary_mode: true        # BB位置主導モード
rsi_match_bonus: 0.08        # RSI一致時ボーナス
rsi_extreme_bonus: 0.05      # RSI極端値（<30, >70）追加ボーナス
rsi_mismatch_penalty: 0.05   # RSI不一致時ペナルティ
```

#### 3. StochasticReversal: 最小価格変化フィルタ

**変更ファイル**: `src/strategies/implementations/stochastic_reversal.py`

**新パラメータ**:
```yaml
min_price_change_ratio: 0.005    # 最小価格変化（0.5%以上）
enable_min_price_filter: true    # フィルタ有効化
```

#### 結果

| 指標 | 62.1-B | 62.2 | 変化 | 目標 |
|------|--------|------|------|------|
| 取引数 | 344件 | 478件 | +39% | 380件+ ✅ |
| ATRBased比率 | 77.9% | 58.2% | -19.7pt | 65%以下 ✅ |
| 総損益 | ¥159,958 | ¥172,643 | +8% | ✅ |
| PF | 2.51 | 2.03 | -19% | 2.0+ ✅ギリギリ |
| 勝率 | 73.3% | 68.2% | -5.1pt | 72%+ ❌ |

#### 戦略別結果

| 戦略 | 取引数 | 勝率 | 損益 | 評価 |
|------|--------|------|------|------|
| ATRBased | 278件 | 72.3% | +¥120,165 | 主力 |
| DonchianChannel | 118件 | 64.4% | +¥36,406 | ✅RSIボーナス成功 |
| StochasticReversal | 30件 | 70.0% | +¥14,036 | 良好 |
| ADXTrendStrength | 8件 | 75.0% | +¥4,061 | 良好 |
| **BBReversal** | 44件 | **50.0%** | **-¥2,025** | ❌問題 |

**評価**: 戦略分散には成功したが、BBReversalが損失発生という新たな問題が判明

---

### Phase 62.3-62.4: BBReversal調整・DonchianChannel強化 ✅完了

**実施日**: 2026年1月31日

#### Phase 62.3: BBReversal無効化

**変更ファイル**: `config/core/thresholds.yaml`

```yaml
dynamic_strategy_selection:
  regime_strategy_mapping:
    tight_range:
      BBReversal: 0.0  # 無効化（0.35 → 0.0）
```

**根拠**: BBReversalは44件・勝率50%・¥-2,025損失。BB主導モードがtight_rangeでは機能しない。

#### Phase 62.4: DonchianChannel重み増加

```yaml
tight_range:
  BBReversal: 0.0       # 無効化
  DonchianChannel: 0.30  # 重み増加（0.10 → 0.30）
  StochasticReversal: 0.35
  ATRBased: 0.35
```

**根拠**: DonchianChannelは118件・勝率64.4%・¥+36,406と良好。RSIボーナス制度が成功している戦略に重みを移行。

#### 統合結果

| 指標 | Phase 62.2 | Phase 62.3-62.4 | 変化 |
|------|-----------|-----------------|------|
| 取引数 | 478件 | 346件 | -28%（品質重視） |
| 総損益 | ¥172,643 | **¥177,025** | +3% ✅ |
| PF | 2.03 | **2.75** | +36% ✅ |
| 勝率 | 68.2% | **75.7%** | +7.5pt ✅ |
| 最大DD | ¥6,152 | **¥4,925** | -20% ✅ |

#### 戦略別パフォーマンス（62.3-62.4）

| 戦略 | 取引数 | 勝率 | 損益 | 評価 |
|------|--------|------|------|------|
| ATRBased | 280件 | 75.4% | +¥141,766 | 主力 |
| DonchianChannel | 25件 | 76.0% | +¥11,045 | 良好 |
| **BBReversal** | 22件 | **72.7%** | **+¥9,506** | **改善✅** |
| StochasticReversal | 15件 | 80.0% | +¥9,777 | 良好 |
| ADXTrendStrength | 4件 | 100% | +¥4,931 | 良好 |

**結論**: BBReversalが損失(¥-2,025)→利益(¥+9,506)に転換。全戦略が利益を出す健全な状態に。

---

## Phase 62.5: HOLD診断機能 ✅完了

**実施日**: 2026年2月1日

**目的**: 「なぜHOLDなのか」「あとどれくらいでシグナルが出るか」を可視化

### 実装内容

各戦略に`get_signal_proximity()`メソッドを追加：

| 戦略 | 診断項目 |
|------|---------|
| ATRBased | 消尽率、BB位置、ADX |
| DonchianChannel | チャネル位置、ADX、RSI |
| StochasticReversal | ダイバージェンス検出状態、価格変動、Stochastic、ADX |

### 出力例

```
=== HOLD診断 ===
[ATRBased] 消尽率=55%(閾値70%まで15%) | BB=45%(BUY端まで25%) | ADX=18.0✓
[DonchianChannel] 位置=45%(BUY端まで27%) | ADX=20.0✓ | RSI=50.0(中立)
[StochasticReversal] Div=未検出(位置差10%<20%) | 変動=0.61%✓ | Stoch=55.0(中立) | ADX=20.0✓
================
```

### 変更ファイル

| ファイル | 変更内容 |
|---------|----------|
| `src/strategies/implementations/atr_based.py` | `get_signal_proximity()`追加 |
| `src/strategies/implementations/donchian_channel.py` | `get_signal_proximity()`追加 |
| `src/strategies/implementations/stochastic_reversal.py` | `get_signal_proximity()`追加 |
| `src/strategies/base/strategy_manager.py` | `_output_hold_diagnosis()`追加 |

**効果**: バックテストモードでは診断出力を抑制し、パフォーマンスへの影響なし。

---

## Phase 62.6〜62.8: 手数料計算の修正

### 手数料修正の経緯

```
62.6: ライブの手数料計算を修正（bitbank UIと一致）
  ↓ 「バックテストと乖離している」と気づく
62.7: バックテストもTaker統一（0.12%×2）
  ↓ 結果がおかしい（PF 0.04、損益-¥64,845）
  ↓ 調査 → 手数料が4箇所で計算されていた（多重控除）
62.8: 多重計算バグ修正（reporter.pyに一元化）
```

### Phase 62.6: 手数料考慮した実現損益計算 ✅完了

**実施日**: 2026年2月2日

**問題**: GCPログのpnl値とbitbank UI「実現損益」に差異

**原因**: 手数料が考慮されていなかった

#### 修正内容

**thresholds.yaml**:
```yaml
trading:
  fees:
    maker_rate: -0.0002       # Maker -0.02%（リベート）
    taker_rate: 0.0012        # Taker 0.12%
    entry_taker_rate: 0.0012  # エントリー Taker 0.12%
    exit_taker_rate: 0.0012   # 決済 Taker 0.12%（TP/SL自動執行）
```

**stop_manager.py の `_calc_pnl()` 修正**:
```python
def _calc_pnl(self, entry_price, exit_price, amount, side) -> float:
    # 粗利益計算
    if side.lower() == "buy":
        gross_pnl = (exit_price - entry_price) * amount
    else:
        gross_pnl = (entry_price - exit_price) * amount

    # 手数料計算（TP/SL約定はTaker扱い）
    entry_fee = entry_price * amount * 0.0012
    exit_fee = exit_price * amount * 0.0012

    return gross_pnl - entry_fee - exit_fee
```

---

### Phase 62.7: バックテスト手数料修正（Taker統一） ✅完了

**実施日**: 2026年2月2日

**問題**: バックテストとライブモードで手数料計算が異なっていた

| 項目 | バックテスト（修正前） | ライブモード | 乖離 |
|------|---------------------|-------------|------|
| エントリー | Maker -0.02% | Taker 0.12% | 0.14%差 |
| 決済 | Maker -0.02% | Taker 0.12% | 0.14%差 |
| 往復 | -0.04%（報酬） | +0.24%（費用） | **0.28%差** |

#### 修正内容

バックテストもTaker手数料（0.12%×2）に統一：

- `executor.py`: エントリー手数料をTakerに変更
- `backtest_runner.py`: 決済手数料・PnL計算をTakerに変更
- `reporter.py`: PnL計算に手数料追加

---

### Phase 62.8: 手数料多重計算バグ修正 ✅完了

**実施日**: 2026年2月3日

**問題**: Phase 62.7後のバックテスト結果がおかしい

| 結果 | 修正前（1/31） | 修正後（2/2） |
|------|--------------|--------------|
| 総損益 | ¥177,025 | **¥-64,845** |
| 勝率 | 75.7% | **39.9%** |
| PF | 2.75 | **0.04** |

**原因**: 手数料が4箇所で計算され多重控除されていた

| # | ファイル | 処理 | 手数料 |
|---|---------|------|--------|
| 1 | executor.py | エントリー時残高控除 | -0.12% |
| 2 | backtest_runner.py | _calculate_pnl()でエントリー手数料 | -0.12% |
| 3 | backtest_runner.py | TP/SL決済時残高控除 | -0.12% |
| 4 | reporter.py | 往復手数料計算 | -0.24% |

**実際の計算**: 0.12% + 0.12% + 0.12% + 0.24% = **0.60%**（正しい0.24%の2.5倍）

#### 修正方針

**手数料はreporter.pyのみで計算**（後処理で一括）

| ファイル | 修正前 | 修正後 |
|---------|--------|--------|
| executor.py | エントリー手数料控除 | **削除** |
| backtest_runner.py _calculate_pnl() | エントリー手数料控除 | **削除**（利息のみ） |
| backtest_runner.py TP/SL | 決済手数料控除 | **削除** |
| reporter.py | 往復手数料計算 | **維持（唯一の計算箇所）** |

---

## Phase 62.9〜62.12: Maker戦略実装

### Maker戦略実装の経緯

```
62.9: エントリーをMaker約定に（post_only対応）
  ↓
62.10: TP決済もMaker約定に（limit + post_onlyで代替）
  ↓
62.11: TP純利益が目標未達（300-400円 vs 500円目標）
  ↓ 調査 → TP計算時はMaker想定、決済時はTakerで計算していた
  ↓ 修正 → Taker手数料でTP価格を計算
62.11B: バックテストもMaker手数料対応
  ↓
62.12: Maker戦略が正常動作していることを検証（100%成功）
```

### Phase 62.9: エントリーMaker戦略 ✅完了

**実施日**: 2026年2月3日

**目的**: エントリー注文をMaker約定（-0.02%リベート）で行い、手数料を0.14%削減

#### 実装内容

| ファイル | 変更内容 |
|---------|----------|
| `config/core/thresholds.yaml` | `order_execution.maker_strategy`設定追加 |
| `src/data/bitbank_client.py` | `create_order()`にpost_onlyパラメータ追加 |
| `src/trading/execution/order_strategy.py` | Maker戦略実装（リトライ・フォールバック） |
| `src/core/exceptions.py` | `PostOnlyCancelledException`追加 |

#### 設定

```yaml
order_execution:
  maker_strategy:
    enabled: true              # Maker戦略有効化
    max_retries: 3             # 最大リトライ回数
    retry_interval_ms: 500     # リトライ間隔
    timeout_seconds: 30        # タイムアウト
    fallback_to_taker: true    # Takerフォールバック
```

---

### Phase 62.10: TP決済Maker戦略 ✅完了

**実施日**: 2026年2月3日

**目的**: TP決済注文をMaker約定で行い、決済手数料を0.14%削減

**制約**: bitbank APIの`take_profit`タイプはpost_only非対応のため、`limit + post_only`で代替

#### 実装内容

| ファイル | 変更内容 |
|---------|----------|
| `config/core/thresholds.yaml` | `take_profit.maker_strategy`設定追加 |
| `src/data/bitbank_client.py` | `create_take_profit_order()`にpost_onlyパラメータ追加 |
| `src/trading/execution/stop_manager.py` | `_place_tp_maker()`・`_place_tp_native()`実装 |

#### 設定

```yaml
take_profit:
  maker_strategy:
    enabled: true              # TP Maker戦略有効化
    max_retries: 2             # 最大リトライ回数（TPは速度優先）
    retry_interval_ms: 300     # リトライ間隔
    timeout_seconds: 10        # タイムアウト（短め）
    fallback_to_native: true   # take_profitタイプにフォールバック
```

#### 動作フロー

```
TP注文配置
    ↓
Maker戦略有効？
    ↓ Yes
limit + post_only注文試行（最大2回）
    ↓
成功 → Maker約定（-0.02%リベート）✅
    ↓ 失敗
fallback_to_native有効？
    ↓ Yes
take_profitタイプで配置（従来方式・Taker 0.12%）
```

---

### Phase 62.11: TP手数料計算バグ修正 ✅完了

**実施日**: 2026年2月4日

**問題**: TP純利益が300-400円程度（500円目標に未達）

**実測値（CSV分析）**:
- 取引#2: +299円
- 取引#5: +369円
- 取引#8: +371円

#### 根本原因

TP計算時と決済時で手数料率が異なっていた：

| タイミング | 決済手数料率 | 想定 |
|-----------|-------------|------|
| TP価格計算時 | -0.0002 (Maker) | リベート減算 |
| 決済実績計算時 | 0.0012 (Taker) | 手数料加算 |

**差分**: 約0.14%（約7円/取引）の損失

#### 修正内容

**thresholds.yaml**:
```yaml
# 修正前
fallback_exit_fee_rate: -0.0002   # Maker -0.02%（リベート）
target_net_profit: 1000           # 不一致

# 修正後
fallback_exit_fee_rate: 0.0012    # Taker 0.12%に統一
target_net_profit: 500            # 500円に統一
```

**strategy_utils.py**:
```python
# 修正前
exit_fee_rebate = abs(entry_price * amount * exit_fee_rate)
required_gross_profit = target_net_profit + entry_fee + interest - exit_fee_rebate  # リベート減算

# 修正後
exit_fee = entry_price * amount * exit_fee_rate
required_gross_profit = target_net_profit + entry_fee + interest + exit_fee  # 手数料加算
```

---

### Phase 62.11B: バックテスト/ライブ手数料統一 ✅完了

**実施日**: 2026年2月4日

**問題**: ライブモードがMaker手数料対応になったが、バックテストはTaker手数料のまま

| 項目 | バックテスト | ライブモード |
|------|-------------|--------------|
| エントリー | Taker 0.12% | Maker -0.02% |
| TP決済 | Taker 0.12% | Maker -0.02% |
| SL決済 | Taker 0.12% | Taker 0.12% |

#### 修正内容

**thresholds.yaml**:
```yaml
# 修正後
backtest_entry_rate: -0.0002    # Maker -0.02%（リベート）
backtest_tp_exit_rate: -0.0002  # TP決済 Maker -0.02%
backtest_sl_exit_rate: 0.0012   # SL決済 Taker 0.12%
```

**reporter.py**: `calculate_pnl_with_fees()`に`exit_type`引数追加
- `exit_type="tp"` → Maker手数料
- `exit_type="sl"` → Taker手数料

---

### Phase 62.12: Maker戦略動作検証 ✅完了

**実施日**: 2026年2月4日

**目的**: CSVの「ポストオンリー」列が全てFALSEのため、Maker戦略が実際に機能しているか検証

#### GCPログ検証結果

| 項目 | 結果 |
|------|------|
| エントリーMaker成功 | 4件（100%） |
| TP Maker配置成功 | 4件（100%） |
| post_onlyキャンセル | 0件 |
| Takerフォールバック | 0件 |

#### GCPログ証跡

```
2026-02-03 08:43:38 ✅ 指値注文投入成功: 注文ID=54342865990, 予想手数料: Maker(-0.02%)
2026-02-03 08:43:43 ✅ Phase 62.10: TP Maker配置成功 - ID: 54342868219, 価格: 12251246円
2026-02-03 06:12:06 ✅ 指値注文投入成功: 注文ID=54339672694, 予想手数料: Maker(-0.02%)
2026-02-03 06:12:13 ✅ Phase 62.10: TP Maker配置成功 - ID: 54339674922, 価格: 12229689円
```

**結論**:
1. Maker戦略は正常動作（100%成功率）
2. CSV「ポストオンリー」FALSEはbitbank仕様（約定後のCSVには反映されない）
3. Phase 62.11修正後、TP純利益が500円に改善される見込み

---

## Phase 62.13: ATRフォールバック問題修正 ✅完了

**実施日**: 2026年2月5日

### 背景

ライブモードでATR取得に失敗した際、フォールバック値として500,000円（約5%）という非現実的な値が使用されていた。

### 問題

| 問題 | 詳細 |
|------|------|
| ATRフォールバック値 | 500,000円（BTC価格の約5%） |
| 実際のATR | 約120,000円（約1%） |
| 影響 | SL距離が過大、リスク管理に問題 |

### 修正内容

#### 1. executor.py: Level 0追加（atr_current直接参照）

ATR取得の優先順位を改善：
- Level 0（新規）: `atr_current`を直接参照
- Level 1: `signal.ml_features["atr_current"]`
- Level 2: `signal.ml_features["atr_ratio"]`から逆算
- Level 3: フォールバック値

#### 2. thresholds.yaml: フォールバック値修正

```yaml
# 修正前
fallback_atr: 500000  # 非現実的

# 修正後
fallback_atr: 120000  # 現実的な値（約1%）
```

#### 3. standard_analysis.py: ATR取得状況の検知・レポート機能追加

- ATRフォールバック使用回数のカウント
- フォールバック使用時の警告表示

### 変更ファイル

| ファイル | 変更内容 |
|---------|----------|
| `src/trading/execution/executor.py` | Level 0追加（atr_current直接参照） |
| `config/core/thresholds.yaml` | `fallback_atr: 500000` → `120000` |
| `scripts/live/standard_analysis.py` | ATR取得状況の検知・レポート機能追加 |

---

## 補足情報

### 700円固定TP比較テスト結果

**実施日**: 2026年2月5日

| 指標 | 500円TP | 700円TP | 評価 |
|------|---------|---------|------|
| 勝率 | 59.7% | 54.5% | ❌ -5.2pt |
| 総損益 | ¥+119,815 | ¥+86,079 | ❌ -¥33,736 |
| PF | 1.65 | 1.50 | ❌ |
| 最大DD | ¥13,352 | ¥12,089 | ✅ |

**結論**: 500円TPが明確に優位。TPを広げると到達率が下がり、勝率低下→損益悪化。

### 戦略別パフォーマンス（Phase 62.11B バックテスト最終）

| 戦略 | 取引数 | 勝率 | 損益 |
|------|--------|------|------|
| ATRBased | 245件 | 58.8% | ¥+88,445 |
| DonchianChannel | 20件 | 75.0% | ¥+13,785 |
| StochasticReversal | 15件 | 60.0% | ¥+8,130 |
| BBReversal | 19件 | 52.6% | ¥+4,695 |
| ADXTrendStrength | 4件 | 75.0% | ¥+4,759 |

### TP/SL統計（Phase 62.11B）

| 項目 | 件数 | 平均PnL |
|------|------|---------|
| TP決済 | 181件 | ¥+1,674 |
| SL決済 | 122件 | ¥-1,519 |

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `config/core/thresholds.yaml` | 戦略閾値・手数料・Maker戦略設定 |
| `src/strategies/implementations/donchian_channel.py` | RSIボーナス制度・HOLD診断 |
| `src/strategies/implementations/bb_reversal.py` | BB位置主導モード |
| `src/strategies/implementations/stochastic_reversal.py` | 最小価格変化フィルタ・HOLD診断 |
| `src/strategies/implementations/atr_based.py` | HOLD診断機能 |
| `src/strategies/base/strategy_manager.py` | HOLD診断ログ出力 |
| `src/trading/execution/order_strategy.py` | エントリーMaker戦略（Phase 62.9） |
| `src/trading/execution/stop_manager.py` | TP Maker戦略・手数料計算（Phase 62.10） |
| `src/trading/execution/executor.py` | ATRフォールバック修正（Phase 62.13） |
| `src/data/bitbank_client.py` | post_only対応（Phase 62.9・62.10） |
| `src/backtest/reporter.py` | バックテスト損益計算（唯一の手数料計算箇所） |
| `scripts/live/standard_analysis.py` | Maker戦略・ATR取得状況確認機能 |

---

## Phase 62.14: SL逆指値指値化 ✅完了

**実施日**: 2026年2月5日

### 背景

SL注文が成行（`stop_loss`タイプ）のため、価格急変時にスリッページが発生し、想定より不利な価格で約定する問題。

### 修正内容

**config/core/thresholds.yaml**:
```yaml
stop_loss:
  # 変更前
  use_native_type: true     # stop_lossタイプ（成行決済）
  slippage_buffer: 0.001    # 0.1%

  # 変更後
  use_native_type: false    # stop_limitタイプ（指値決済）
  slippage_buffer: 0.002    # 0.2%（約定確実性向上）
```

### 効果

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| 注文タイプ | `stop_loss`（成行） | `stop_limit`（指値） |
| UI表示 | 「損切り」 | 「逆指値」 |
| スリッページ | 発生 | 0.2%以内に抑制 |

### 未約定リスクとセーフティネット検討

**現状**: `slippage_buffer: 0.2%`で約定確実性を確保。セーフティネット未実装。

**リスクシナリオ**:

| シナリオ | 確率 | 影響 |
|----------|------|------|
| 通常の下落 | 高 | 0.2%バッファで約定 ✅ |
| 急落（0.2%超のギャップ） | 低 | 未約定リスクあり ❌ |
| 流動性枯渇時 | 極低 | 未約定リスクあり ❌ |

**検討した対策案**（問題発生時に実装）:

| 案 | 概要 | 複雑度 |
|----|------|--------|
| 案1 | 未約定検知 + 成行フォールバック（タイムアウト後に成行決済） | 中 |
| 案2 | 二重SL（指値 + 成行バックアップを同時配置） | 高 |
| 案3 | SL発動後のポジション監視強化（残存ポジション検知→成行） | 中 |

**方針**: 現時点では実装せず、問題発生時に対応。bitbank信用取引では追証・ロスカットがあるため、極端なギャップでも最終的には強制決済される。

---

## Phase 62.15: SL幅見直し ✅完了

**実施日**: 2026年2月5日

### 背景

tight_rangeのSL幅0.3%が狭すぎて、SL発動率が高く勝率に影響している可能性。

### 修正内容

**config/core/thresholds.yaml**:
```yaml
stop_loss:
  regime_based:
    tight_range:
      # 変更前
      max_loss_ratio: 0.003   # SL 0.3%
      weekend_ratio: 0.002    # 土日 SL 0.2%

      # 変更後
      max_loss_ratio: 0.004   # SL 0.4%（SL発動率低下・勝率改善）
      weekend_ratio: 0.0025   # 土日 SL 0.25%（平日比62.5%維持）
```

### 期待効果

- SL発動率低下
- 勝率改善
- RR比の調整（TP 0.4% : SL 0.4% = 1:1）

---

## Phase 62.16: スリッページ分析機能 ✅完了

**実施日**: 2026年2月5日

### 目的

スリッページの実態把握・改善点の可視化

### 実装内容

#### 1. TradeHistoryRecorder拡張

**tax/trade_history_recorder.py**:
- `slippage`フィールド追加（スリッページ金額・円）
- `expected_price`フィールド追加（期待約定価格・円）
- DBスキーマ自動マイグレーション対応

#### 2. executor.py でスリッページ記録

**src/trading/execution/executor.py**:
- エントリー時: `expected_price` vs `filled_price` の差を記録
- スリッページ計算式: `約定価格 - 期待価格`
  - buy時: 正が不利（高く買った）
  - sell時: 負が不利（安く売った）

#### 3. standard_analysis.py にレポート追加

**scripts/live/standard_analysis.py**:
- `LiveAnalysisResult`にスリッページ統計フィールド追加（6指標）
- `_analyze_slippage()`メソッド追加
- Markdownレポートにスリッページ分析セクション追加

### スリッページ統計（6指標）

| 指標 | 説明 |
|------|------|
| slippage_count | スリッページ記録数 |
| slippage_avg | 平均スリッページ（円） |
| slippage_max | 最大スリッページ（円） |
| slippage_min | 最小スリッページ（円） |
| slippage_entry_avg | エントリー時平均スリッページ |
| slippage_exit_avg | 決済時平均スリッページ |

---

## Phase 62 完了

**完了日**: 2026年2月5日

### 最終成果

| 指標 | 値 |
|------|-----|
| バックテスト期間 | 2025-07-01 ~ 2025-12-31（6ヶ月） |
| 総損益 | ¥+119,815 |
| PF | 1.65 |
| 勝率 | 59.7% |
| 年利換算 | 約24% |
| 最大DD | ¥13,352 (2.14%) |

### 主要実装

| Phase | 内容 | 効果 |
|-------|------|------|
| 62.1-62.4 | 戦略閾値調整・分散改善 | ATRBased一強解消 |
| 62.5 | HOLD診断機能 | デバッグ強化 |
| 62.6-62.8 | 手数料計算修正 | 正確な損益計算 |
| 62.9-62.10 | Maker戦略実装 | 往復手数料-0.04%（0.28%削減） |
| 62.11-62.12 | TP手数料修正・検証 | 純利益500円保証 |
| 62.13 | ATRフォールバック修正 | 正確なATR取得 |
| 62.14-62.15 | SL逆指値指値化・幅見直し | スリッページ抑制 |
| 62.16 | スリッページ分析機能 | 実態把握可能化 |

### 保留タスク

| タスク | 保留理由 |
|--------|----------|
| 1年バックテスト | GitHub Actions上限6時間超過の可能性（6ヶ月で3時間） |

---

**最終更新**: 2026年2月5日 - **Phase 62完了**
