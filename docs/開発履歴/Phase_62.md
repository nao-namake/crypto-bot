# Phase 62: 戦略閾値緩和・バランス改善 📋進行中

**期間**: 2026年1月31日〜
**状態**: 📋 **進行中**
**目的**: ATRBased一強問題解消・3戦略の活用強化

---

## 背景

Phase 61完了時点で総損益¥149,195（PF 2.68）を達成したが、以下の課題が判明：

| 課題 | 詳細 | 影響 |
|------|------|------|
| ATRBased一強 | 218件/261件（83%）がATRBased | 戦略分散が機能していない |
| BBReversal機能不全 | 1件のみ・0%勝率 | 閾値が厳しすぎ |
| DonchianChannel活用不足 | 13件・69.2%勝率（良好） | 高勝率なのに取引数少ない |
| StochasticReversal普通 | 29件・51.7%勝率 | 閾値緩和で改善余地 |

### Phase 61.12 バックテスト戦略別結果

| 戦略 | 取引数 | 比率 | 勝率 | 損益 | 評価 |
|------|--------|------|------|------|------|
| ATRBased | 218件 | 83% | 61.0% | +¥118,767 | 主力 |
| **DonchianChannel** | 13件 | 5% | **69.2%** | **+¥10,608** | **良好** |
| StochasticReversal | 29件 | 11% | 51.7% | +¥3,383 | 普通 |
| BBReversal | 1件 | 0.4% | 0.0% | -¥1,194 | 問題 |

**発見**: DonchianChannelは勝率69.2%で良好 → 無効化ではなく活用強化

---

## 実装計画

| Phase | 内容 | 状態 |
|-------|------|------|
| **62.1** | 3戦略閾値一括緩和 | ✅完了 |
| **62.1-B** | さらなる閾値緩和 | ✅完了（効果なし） |
| **62.2** | 戦略条件型変更（RSIボーナス・BB主導） | ✅完了（部分成功） |
| **62.3** | BBReversal無効化（tight_range） | ✅完了 |
| **62.4** | DonchianChannel重み増加（10%→30%） | ✅完了 |
| **62.5** | HOLD診断機能実装 | ✅完了 |

### 成功基準

| 指標 | Phase 61最終 | 目標 |
|------|--------------|------|
| ATRBased比率 | 83% | 50%以下 |
| BBReversal取引数 | 1件 | 30件以上 |
| StochasticReversal取引数 | 29件 | 50件以上 |
| DonchianChannel取引数 | 13件 | 30件以上 |
| PF | 2.68 | 2.0以上維持 |
| 勝率 | 75.8% | 70%以上維持 |

---

## Phase 62.1: 3戦略閾値一括緩和 ✅完了

### 実施日: 2026年1月31日

### 実施内容

**対象ファイル**: `config/core/thresholds.yaml`

#### BBReversal

| パラメータ | Before | After |
|-----------|--------|-------|
| bb_upper_threshold | 0.85 | 0.75 |
| bb_lower_threshold | 0.15 | 0.25 |
| rsi_overbought | 62 | 58 |
| rsi_oversold | 38 | 42 |

#### StochasticReversal

| パラメータ | Before | After |
|-----------|--------|-------|
| stoch_overbought | 72 | 65 |
| stoch_oversold | 28 | 35 |

#### DonchianChannel

| パラメータ | Before | After |
|-----------|--------|-------|
| extreme_zone_threshold | 0.12 | 0.15 |
| rsi_oversold | 42 | 45 |
| rsi_overbought | 58 | 55 |

### バックテスト結果

| 指標 | Phase 61.12 | Phase 62.1 | 変化 |
|------|-------------|------------|------|
| **取引数** | 298件 | **332件** | **+11%** ✅ |
| **総損益** | ¥149,195 | **¥168,490** | **+13%** ✅ |
| **PF** | 2.68 | **2.72** | **+1.5%** ✅ |
| 勝率 | 75.8% | 74.7% | -1.1pt |
| 最大DD | ¥5,860 | ¥5,997 | +2% |

#### 戦略別変化

| 戦略 | Before | After | 変化 |
|------|--------|-------|------|
| ATRBased | 250件(84%) | 264件(79.5%) | 比率-4.5pt |
| StochasticReversal | 30件 | 44件 | **+47%** |
| DonchianChannel | 17件 | 21件 | **+24%** |
| BBReversal | 1件 | 3件 | +2件 |

**評価**: 閾値緩和成功（損益+13%・PF維持）だが、ATRBased比率79.5%で目標50%未達

---

## Phase 62.1-B: さらなる閾値緩和 ✅完了（効果なし）

### 実施日: 2026年1月31日

### 目的
Phase 62.1で改善したが目標未達のため、さらに閾値を緩和

### 実施内容

#### BBReversal（3件・33%勝率 → さらに緩和）

| パラメータ | 62.1 | 62.1-B | 変更理由 |
|-----------|------|--------|----------|
| bb_upper_threshold | 0.75 | 0.70 | さらに緩和 |
| bb_lower_threshold | 0.25 | 0.30 | さらに緩和 |
| rsi_overbought | 58 | 55 | さらに緩和 |
| rsi_oversold | 42 | 45 | さらに緩和 |

#### StochasticReversal（44件・54.5%勝率 → さらに緩和）

| パラメータ | 62.1 | 62.1-B | 変更理由 |
|-----------|------|--------|----------|
| stoch_overbought | 65 | 60 | さらに緩和 |
| stoch_oversold | 35 | 40 | さらに緩和 |

#### DonchianChannel（21件・71.4%勝率 → さらに緩和）

| パラメータ | 62.1 | 62.1-B | 変更理由 |
|-----------|------|--------|----------|
| extreme_zone_threshold | 0.15 | 0.18 | さらに緩和 |
| rsi_oversold | 45 | 48 | さらに緩和 |
| rsi_overbought | 55 | 52 | さらに緩和 |

### バックテスト結果

| 指標 | Phase 62.1 | Phase 62.1-B | 変化 |
|------|------------|--------------|------|
| **取引数** | 332件 | **344件** | **+4%** |
| **総損益** | ¥168,490 | **¥159,958** | **-5%** ❌ |
| **PF** | 2.72 | **2.51** | **-8%** ❌ |
| 勝率 | 74.7% | 73.3% | -1.4pt |
| 最大DD | ¥5,997 | ¥7,334 | +22% |

#### 戦略別変化

| 戦略 | 62.1 | 62.1-B | 変化 |
|------|------|--------|------|
| ATRBased | 264件(79.5%) | 268件(77.9%) | 比率-1.6pt |
| StochasticReversal | 44件 | 48件 | **+9%** |
| DonchianChannel | 21件 | 24件 | **+14%** |
| BBReversal | 3件 | 4件 | +1件 |

**評価**: ❌ 閾値緩和は逆効果。取引数増加したが損益-5%・PF-8%悪化。閾値緩和だけでは限界があることを確認。

**結論**: 構造的な問題（AND条件・RSIフィルタ）を解決する必要あり → Phase 62.2へ

---

## Phase 62.2: 戦略条件型変更 ✅完了（部分成功）

### 実施日: 2026年1月31日

### 背景

Phase 62.1-Bの閾値緩和だけでは限界がある。構造的な問題（AND条件・RSIフィルタ）を解決しないとATRBased一強問題（79.5%）は完全解消できない。

### 問題点と解決策

| 戦略 | 問題 | 解決策 |
|------|------|--------|
| DonchianChannel | RSIフィルタでHOLD判定 | RSIをボーナス制度に変更 |
| BBReversal | AND条件（BB+RSI）が厳しすぎ | BB位置主導に変更、RSIはボーナス |
| StochasticReversal | 弱いダイバージェンスを検出 | 最小価格変化フィルタ追加 |

### 実施内容

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

**信頼度計算**:
- RSI一致: `+rsi_confirmation_bonus`（0.05）
- RSI極端値（<30 or >70）: 追加ボーナス（0.05）
- RSI不一致: `-rsi_mismatch_penalty`（0.08）

**期待効果**: 21件 → 28-32件

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

**期待効果**: 3件 → 8-12件

#### 3. StochasticReversal: 最小価格変化フィルタ

**変更ファイル**: `src/strategies/implementations/stochastic_reversal.py`

| Before | After |
|--------|-------|
| 弱いダイバージェンスも検出 | 価格変動0.5%未満はフィルタリング |

**新パラメータ**:
```yaml
min_price_change_ratio: 0.005    # 最小価格変化（0.5%以上）
enable_min_price_filter: true    # フィルタ有効化
```

**信頼度ボーナス**:
- 価格変動が大きい（1%以上）: `+0.1`

**期待効果**: 品質向上（弱いダイバージェンス除外）

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|----------|
| `src/strategies/implementations/donchian_channel.py` | RSIボーナス制度実装 |
| `src/strategies/implementations/bb_reversal.py` | BB位置主導モード実装 |
| `src/strategies/implementations/stochastic_reversal.py` | 最小価格変化フィルタ追加 |
| `config/core/thresholds.yaml` | 新パラメータ追加 |
| `tests/unit/strategies/implementations/test_donchian_channel.py` | テスト更新 |

### 品質チェック結果

```
✅ 全テスト: 2074 passed (+802)
✅ カバレッジ: 75.58% (+12.11pt)
✅ flake8/isort/black: PASS
```

### 期待される改善

| 指標 | Phase 62.1-B | Phase 62.2目標 |
|------|-------------|----------------|
| 取引数 | 332件 | 380件以上 |
| ATRBased比率 | 79.5% | 65%以下 |
| PF | 2.72 | 2.5以上維持 |
| 勝率 | 74.7% | 72%以上維持 |

### バックテスト結果

| 指標 | 62.1-B | 62.2 | 変化 | 目標 | 達成 |
|------|--------|------|------|------|------|
| **取引数** | 344件 | **478件** | **+39%** | 380件+ | ✅ |
| **総損益** | ¥159,958 | **¥172,643** | **+8%** | - | ✅ |
| **PF** | 2.51 | **2.03** | **-19%** | 2.0+ | ✅ギリギリ |
| 勝率 | 73.3% | **68.2%** | **-5.1pt** | 72%+ | ❌ |
| 最大DD | ¥7,334 | **¥6,152** | **-16%** | - | ✅ |

#### 戦略別変化（目標達成評価）

| 戦略 | 62.1-B | 62.2 | 変化 | 目標達成 |
|------|--------|------|------|----------|
| **ATRBased** | 268件(77.9%) | **278件(58.2%)** | **-19.7pt** | ✅65%以下達成 |
| **DonchianChannel** | 24件(7.0%) | **118件(24.7%)** | **+392%** | ✅大幅増 |
| **BBReversal** | 4件(1.2%) | **44件(9.2%)** | **+1000%** | ⚠️損失発生 |
| **StochasticReversal** | 48件(13.9%) | **30件(6.3%)** | **-38%** | ❌減少 |
| ADXTrendStrength | 0件 | 8件(1.7%) | 新規 | - |

#### 戦略別損益

| 戦略 | 取引数 | 勝率 | 損益 | 評価 |
|------|--------|------|------|------|
| ATRBased | 278件 | 72.3% | **¥+120,165** | 主力 |
| DonchianChannel | 118件 | 64.4% | **¥+36,406** | ✅RSIボーナス成功 |
| StochasticReversal | 30件 | 70.0% | **¥+14,036** | 良好 |
| ADXTrendStrength | 8件 | 75.0% | **¥+4,061** | 良好 |
| **BBReversal** | 44件 | **50.0%** | **¥-2,025** | ❌問題 |

### 評価

**成功点**:
- ✅ ATRBased比率: 77.9% → 58.2%（目標65%以下達成）
- ✅ DonchianChannel: 24件 → 118件（RSIボーナス制度成功）
- ✅ 取引数: 344件 → 478件（+39%）
- ✅ 総損益: ¥159,958 → ¥172,643（+8%）
- ✅ 最大DD改善: ¥7,334 → ¥6,152（-16%）

**課題**:
- ❌ BBReversal: 50%勝率・¥-2,025損失（BB主導が裏目）
- ⚠️ 勝率低下: 73.3% → 68.2%（-5.1pt）
- ⚠️ PF低下: 2.51 → 2.03（-19%）

### 結論

構造的変更（RSIボーナス制度・BB主導モード）は**戦略分散には成功**したが、**BBReversalが損失発生**という新たな問題が判明。

**推奨対応（Phase 62.3）**:
1. BBReversal重み削減または無効化
2. または、BB主導モードの閾値調整（bb_upper_threshold引き上げ）

---

## Phase 62.3: BBReversal無効化（tight_range） ✅完了

### 実施日: 2026年1月31日

### 目的

Phase 62.2でBBReversalが損失（¥-2,025・勝率50%）を発生させたため、tight_rangeレジームでBBReversalを無効化する。

### 実施内容

**変更ファイル**: `config/core/thresholds.yaml`

```yaml
dynamic_strategy_selection:
  regime_strategy_mapping:
    tight_range:
      BBReversal: 0.0  # 無効化（0.35 → 0.0）
```

### 根拠

- Phase 62.2でBBReversalは44件・勝率50%・¥-2,025損失
- BB主導モードがtight_rangeでは機能しない
- 他の戦略は全て利益を出している

---

## Phase 62.4: DonchianChannel重み増加（10%→30%） ✅完了

### 実施日: 2026年1月31日

### 目的

BBReversal無効化分の重みをDonchianChannelに振り分け、RSIボーナス制度の効果を活用する。

### 実施内容

**変更ファイル**: `config/core/thresholds.yaml`

```yaml
dynamic_strategy_selection:
  regime_strategy_mapping:
    tight_range:
      BBReversal: 0.0       # 無効化
      DonchianChannel: 0.30  # 重み増加（0.10 → 0.30）
      StochasticReversal: 0.35
      ATRBased: 0.35
```

### 根拠

- Phase 62.2でDonchianChannelは118件・勝率64.4%・¥+36,406と良好
- RSIボーナス制度が成功している戦略に重みを移行
- ATRBasedとStochasticReversalは維持

---

## Phase 62.3-62.4 統合バックテスト結果 ✅成功

### バックテスト実行日: 2026年2月1日

### 結果サマリー

| 指標 | Phase 62.2 | Phase 62.3-62.4 | 変化 | 評価 |
|------|-----------|-----------------|------|------|
| **取引数** | 478件 | 346件 | -28% | 品質重視 |
| **総損益** | ¥172,643 | **¥177,025** | **+3%** | ✅ |
| **PF** | 2.03 | **2.75** | **+36%** | ✅大幅改善 |
| **勝率** | 68.2% | **75.7%** | **+7.5pt** | ✅回復 |
| **最大DD** | ¥6,152 | **¥4,925** | **-20%** | ✅改善 |
| SR | - | 35.15 | - | 良好 |
| 期待値 | - | ¥512/取引 | - | 良好 |

### 戦略別パフォーマンス

| 戦略 | 取引数 | 比率 | 勝率 | 損益 | 評価 |
|------|--------|------|------|------|------|
| ATRBased | 280件 | 81% | 75.4% | ¥+141,766 | 主力 |
| DonchianChannel | 25件 | 7% | 76.0% | ¥+11,045 | 良好 |
| **BBReversal** | 22件 | 6% | **72.7%** | **¥+9,506** | **改善✅** |
| StochasticReversal | 15件 | 4% | 80.0% | ¥+9,777 | 良好 |
| ADXTrendStrength | 4件 | 1% | 100% | ¥+4,931 | 良好 |

### レジーム別パフォーマンス

| レジーム | 取引数 | 勝率 | 損益 |
|---------|--------|------|------|
| tight_range | 293件 | 73.0% | ¥+139,400 |
| normal_range | 53件 | 90.6% | ¥+37,625 |

### ML×戦略一致率

| 指標 | 値 |
|------|-----|
| 一致率 | 54.6% |
| 一致時勝率 | 80.4% |
| 不一致時勝率 | 70.1% |
| ML HOLD時勝率 | 64.3% |

### 評価

**成功点**:
- ✅ BBReversal: 損失(¥-2,025) → **利益(¥+9,506)** に転換
- ✅ PF大幅改善: 2.03 → 2.75（+36%）
- ✅ 勝率回復: 68.2% → 75.7%（+7.5pt）
- ✅ 最大DD改善: ¥6,152 → ¥4,925（-20%）
- ✅ **全戦略が利益を出している**
- ✅ Phase 61水準を超える成果（¥177,025）

**トレードオフ**:
- 取引数減少: 478件 → 346件（BBReversal無効化の影響）
- ATRBased比率上昇: 58% → 81%（分散は後退）

### 結論

**品質重視の調整が成功**。取引数は減少したが、全戦略が利益を出す健全な状態に。
Phase 61最高水準（¥149,195・PF 2.68）を大きく超える成果を達成。

| 比較 | Phase 61最終 | Phase 62.3-62.4 | 改善率 |
|------|-------------|-----------------|--------|
| 総損益 | ¥149,195 | ¥177,025 | +19% |
| PF | 2.68 | 2.75 | +3% |
| 勝率 | 75.8% | 75.7% | -0.1pt |

---

## Phase 62.5: HOLD診断機能実装 ✅完了

### 実施日: 2026年2月1日

### 目的

ライブモードで「なぜHOLDなのか」「あとどれくらいでシグナルが出るか」を可視化し、システムの動作状況を把握しやすくする。

### 背景

Phase 62.2完了後、ライブモードでの取引頻度がバックテストと乖離しているように見える問題を調査。調査の結果、乖離ではなく記録方法の違い（シグナル生成数 vs 実際の約定数）であることが判明。ただし、HOLDが続く状況を診断する機能がないため、「なぜシグナルが出ないのか」を把握できない問題があった。

### 実施内容

#### 1. ATRBased戦略に診断メソッド追加

**ファイル**: `src/strategies/implementations/atr_based.py`

```python
def get_signal_proximity(self, df: pd.DataFrame) -> Dict[str, Any]:
    """シグナルまでの距離を計算"""
    # ATR消尽率、BB位置、ADXの現在値と閾値の差を計算
```

**出力例**:
```
消尽率=55%(閾値70%まで15%) | BB=45%(BUY端まで25%) | ADX=18.0✓
```

#### 2. DonchianChannel戦略に診断メソッド追加

**ファイル**: `src/strategies/implementations/donchian_channel.py`

```python
def get_signal_proximity(self, df: pd.DataFrame) -> Dict[str, Any]:
    """シグナルまでの距離を計算"""
    # チャネル位置、ADX、RSIの現在値と閾値の差を計算
```

**出力例**:
```
位置=45%(BUY端まで27%) | ADX=20.0✓ | RSI=50.0(中立)
```

#### 3. StochasticReversal戦略に診断メソッド追加

**ファイル**: `src/strategies/implementations/stochastic_reversal.py`

```python
def get_signal_proximity(self, df: pd.DataFrame) -> Dict[str, Any]:
    """シグナルまでの距離を計算"""
    # ダイバージェンス検出状態、価格変動、Stochastic、ADXを計算
```

**出力例**:
```
Div=未検出(位置差10%<20%) | 変動=0.61%✓ | Stoch=55.0(中立) | ADX=20.0✓
```

#### 4. StrategyManagerに診断ログ出力追加

**ファイル**: `src/strategies/base/strategy_manager.py`

```python
def _output_hold_diagnosis(self, df: pd.DataFrame) -> None:
    """HOLD診断情報を出力"""
    # HOLDシグナル時に各戦略のget_signal_proximity()を呼び出し
    # 診断情報をログ出力
```

**ログ出力例**:
```
=== HOLD診断 ===
[ATRBased] 消尽率=55%(閾値70%まで15%) | BB=45%(BUY端まで25%) | ADX=18.0✓
[DonchianChannel] 位置=45%(BUY端まで27%) | ADX=20.0✓ | RSI=50.0(中立)
[StochasticReversal] Div=未検出(位置差10%<20%) | 変動=0.61%✓ | Stoch=55.0(中立) | ADX=20.0✓
================
```

### 診断項目一覧

| 戦略 | 診断項目 | 説明 |
|------|---------|------|
| **ATRBased** | 消尽率 | ATR消尽率と閾値70%までの差 |
| | BB位置 | ボリンジャーバンド内位置とBUY/SELL端までの距離 |
| | ADX | レンジ相場判定（< 25でOK） |
| **DonchianChannel** | チャネル位置 | Donchianチャネル内位置と極端位置までの距離 |
| | ADX | レンジ相場判定（< 28でOK） |
| | RSI | 過買い/過売り状態 |
| **StochasticReversal** | ダイバージェンス | 検出状態と価格/Stochastic位置差 |
| | 価格変動 | 価格変動率と最小閾値0.5%までの差 |
| | Stochastic | 過買い/過売り状態 |
| | ADX | 強トレンド除外判定（< 50でOK） |

### 設計上の配慮

1. **バックテストモードでは診断出力を抑制**: パフォーマンスへの影響を最小化
2. **既存ロジックに影響なし**: 診断機能は読み取り専用で、シグナル生成には影響しない
3. **エラー耐性**: 診断エラーが発生してもシステム動作に影響しない

### 品質チェック結果

```
✅ 全テスト: 2074 passed
✅ カバレッジ: 74.77%
✅ flake8/isort/black: PASS
```

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|----------|
| `src/strategies/implementations/atr_based.py` | `get_signal_proximity()`追加 |
| `src/strategies/implementations/donchian_channel.py` | `get_signal_proximity()`追加 |
| `src/strategies/implementations/stochastic_reversal.py` | `get_signal_proximity()`追加 |
| `src/strategies/base/strategy_manager.py` | `_output_hold_diagnosis()`追加・HOLD時に診断出力 |

### 効果

- ✅ ライブモードで「なぜHOLDなのか」を即座に把握可能
- ✅ 「あとどれくらいでシグナルが出るか」を定量的に表示
- ✅ デバッグ・運用監視が容易に
- ✅ 戦略の動作状況を可視化

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `config/core/thresholds.yaml` | 戦略閾値設定（Phase 62.2パラメータ追加） |
| `src/strategies/implementations/donchian_channel.py` | RSIボーナス制度実装 + HOLD診断機能 |
| `src/strategies/implementations/bb_reversal.py` | BB位置主導モード実装 |
| `src/strategies/implementations/stochastic_reversal.py` | 最小価格変化フィルタ + HOLD診断機能 |
| `src/strategies/implementations/atr_based.py` | HOLD診断機能追加 |
| `src/strategies/base/strategy_manager.py` | HOLD診断ログ出力機能 |
| `docs/開発計画/ToDo.md` | Phase 62計画 |
| `docs/開発履歴/Phase_61.md` | Phase 61完了記録 |

---

**最終更新**: 2026年2月1日 13:25 - Phase 62.3-62.4バックテスト結果追加（¥177,025・PF 2.75達成）
