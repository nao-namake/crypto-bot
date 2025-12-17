# Phase 54 開発記録

**期間**: 2025/12/16-18
**状況**: ✅ **Phase 54.8完了**（ML HOLDバイアス問題解決・HOLD率96%→45%）

---

## 📋 Phase 54 概要

### 目的
ML予測と戦略の最適化による性能回復（PF 1.25 → 1.34+）

### 背景
- Phase 53.13完了後、PF 1.25・勝率 47.9%
- ベースライン（Phase 52.1）: PF 1.34・勝率 51.4%
- 課題: PF -0.09、勝率 -3.5%の性能低下

### Phase一覧

| Phase | 内容 | 状態 |
|-------|------|------|
| **54.0** | ML予測分析（コード変更なし） | ✅ 完了 |
| **54.1** | 戦略別性能分析（コード変更なし） | ✅ 完了 |
| **54.2** | 戦略エントリー基準厳格化 | ✅ 完了 |
| **54.3-A** | BBReversal閾値緩和実験 | ✅ 完了（却下） |
| **54.3-B** | ATRBased・DonchianChannel PF改善 | ✅ 完了（部分成功） |
| **54.4** | ATRBasedコード改善・最終検証 | ✅ **完了（PF 1.95達成）** |
| **54.5** | 条件緩和・取引数回復 | ✅ **完了（131件/180日）** |
| **54.6** | ポジションサイズ最適化・取引数回復 | ✅ **完了** |
| **54.7** | Kelly基準改修・ML設定緩和 | ✅ **完了（HOLD 96%問題発見）** |
| **54.8** | ML HOLDバイアス問題解決 | ✅ **完了（HOLD 45%達成）** |

---

## 🔍 Phase 54.0: ML予測分析【完了】

### 実施日
2025年12月16日

### 目的
ML予測の分布・精度を可視化し、問題点を特定

### 実施内容

バックテストログからML予測の分析を実施

### 結果

| 指標 | 値 | 評価 |
|------|-----|------|
| BUY/SELL比率 | 51.8% / 48.2% | 均等・健全 |
| レジーム分布 | tight_range 93.3% / normal_range 6.7% | tight_range支配 |
| 勝率 | 47.9% | 目標51%に-3.1pt |

### 成果物
- `docs/検証記録/Phase_54.0_ML分析_20251216.md`

---

## 📊 Phase 54.1: 戦略別性能分析【完了】

### 実施日
2025年12月16日

### 目的
各戦略の個別性能を測定し、弱点を特定

### 実施内容

1. スクリプト修正（60日分15m足対応）
2. 60日分データで戦略評価実行（5,748行）
3. 戦略別性能レポート作成

### 結果（変更前）

| 戦略 | 取引数 | 勝率 | PF | 評価 |
|------|--------|------|-----|------|
| ATRBased | 322 | 62.4% | 0.86 | **問題: RR比0.52:1** |
| DonchianChannel | 426 | 60.8% | 0.91 | **問題: RR比0.59:1** |
| ADXTrendStrength | 179 | 33.5% | 1.04 | 中立 |
| BBReversal | 14 | 42.9% | **1.92** | **最高性能** |
| StochasticReversal | 9 | 11.1% | 0.02 | **致命的** |
| MACDEMACrossover | 24 | 33.3% | 1.50 | 良好 |

### 主要発見

1. **主力戦略（ATRBased, DonchianChannel）がPF<1.0**
   - 勝率は高い（58-62%）がRR比が悪い（0.52-0.59:1）
   - 平均負けが平均勝ちの約2倍

2. **BBReversalが最高性能（PF 1.92）**
   - 取引数14件と少ないが高品質
   - 重み0.35は過小評価

3. **StochasticReversalは即時削除が必要（PF 0.02）**

### 成果物
- `docs/検証記録/Phase_54.1_戦略別分析_20251216.md`
- `scripts/analysis/strategy_performance_analysis.py`（60日分対応修正）

---

## ⚙️ Phase 54.2: 戦略エントリー基準厳格化【完了】

### 実施日
2025年12月16日

### 目的
tight_range戦略のエントリー基準を厳格化し、低質取引を削減

### 実施内容

#### 1. tight_range重み配分変更

```yaml
regime_strategy_mapping:
  tight_range:
    ATRBased: 0.45 → 0.30
    BBReversal: 0.35 → 0.50
    DonchianChannel: 0.10 → 0.20
    StochasticReversal: 0.10 → 0.00  # 無効化
```

#### 2. ATRBased閾値厳格化

```yaml
atr_based:
  bb_overbought: 0.7 → 0.85
  bb_oversold: 0.3 → 0.15
  rsi_overbought: 65 → 70
  rsi_oversold: 35 → 30
  min_confidence: 0.25 → 0.35
  weak_signal_enabled: false  # 新規追加
```

#### 3. DonchianChannel閾値厳格化

```yaml
donchian_channel:
  min_confidence: 0.25 → 0.35
  weak_signal_enabled: false  # 新規追加
```

#### 4. コード変更

- `atr_based.py`: weak_signal_enabled設定に対応
- `donchian_channel.py`: weak_signal_enabled設定に対応
- `test_atr_based.py`: 新閾値に合わせたテスト更新

### 結果

| 戦略 | 変更前取引数 | 変更後取引数 | 変更前PF | 変更後PF | 評価 |
|------|------------|------------|----------|----------|------|
| ATRBased | 322 | 205 (-36%) | 0.86 | **0.96** | PF改善+0.10 |
| DonchianChannel | 426 | 185 (-57%) | 0.91 | 0.89 | 微低下 |
| BBReversal | 14 | 14 | 1.92 | 1.92 | 維持 |
| 合計 | 771 | 390 | - | - | 300件以上維持 |

### 成果
- ATRBased: PF 0.86→0.96（+11.6%改善）
- 低質取引削減: 771件→390件（-49.4%）

### 成果物
- `config/core/thresholds.yaml`（設定変更）
- `docs/検証記録/Phase_54.2_変更前設定_backup.md`

---

## 🔬 Phase 54.3-A: BBReversal閾値緩和実験【完了・却下】

### 実施日
2025年12月16日

### 目的
BBReversal（PF 1.92）の取引数を増やし、最高PF戦略の寄与を最大化

### 仮説
BBReversalのBB閾値0.95/0.05が厳しすぎて機会損失している

### 実験内容

#### 実験1: 積極的緩和

```yaml
bb_reversal:
  bb_upper_threshold: 0.95 → 0.85
  bb_lower_threshold: 0.05 → 0.15
  rsi_overbought: 70 → 65
  rsi_oversold: 30 → 35
```

#### 実験2: 控えめ緩和

```yaml
bb_reversal:
  bb_upper_threshold: 0.95 → 0.90
  bb_lower_threshold: 0.05 → 0.10
  # RSI維持
```

### 結果

| 設定 | 取引数 | PF | 評価 |
|------|--------|-----|------|
| **オリジナル** (BB 0.95/0.05) | 14 | **1.92** | 最高品質 |
| 積極的緩和 (BB 0.85/0.15) | 27 | 1.12 | **PF -42%低下** |
| 控えめ緩和 (BB 0.90/0.10) | 17 | 1.12 | **PF -42%低下** |

### 結論

**BBReversal閾値の緩和は却下**

- 取引数増加に寄与するが、PF低下が大きすぎて逆効果
- BBReversalは厳格な閾値でこそ高PFを発揮
- オリジナル設定（BB 0.95/0.05）を維持

### 学習事項
「取引品質を犠牲にして取引数を増やすアプローチは採用しない」

---

## 🔧 Phase 54.3-B: ATRBased・DonchianChannel PF改善【完了・部分成功】

### 実施日
2025年12月16日

### 目的
ATRBased（PF 0.96）とDonchianChannel（PF 0.89）のPFを1.0+に改善

### 実施内容

#### ATRBasedの変更（試行→却下）

```yaml
atr_based:
  bb_overbought: 0.85 → 0.90  # 厳格化
  bb_oversold: 0.15 → 0.10    # 厳格化
  rsi_overbought: 70 → 75     # 厳格化
  rsi_oversold: 30 → 25       # 厳格化
  min_confidence: 0.35 → 0.40 # 厳格化
```

#### DonchianChannelの変更（採用）

```yaml
donchian_channel:
  min_confidence: 0.35 → 0.40       # 厳格化
  reversal_threshold: 0.05 → 0.03   # リバーサル厳格化
```

### 結果

| 戦略 | 変更前PF | 変更後PF | 評価 |
|------|----------|----------|------|
| **DonchianChannel** | 0.89 | **1.08** | **目標達成 +21%** |
| ATRBased | 0.96 | 0.89 | **逆効果 -7%** |

### 最終設定

- **DonchianChannel**: Phase 54.3-B設定を維持（PF 1.08達成）
- **ATRBased**: Phase 54.2設定に戻す（過剰厳格化が逆効果）

### 成果
- DonchianChannel: PF 0.89→1.08（+21%改善）、PF 1.0+達成

---

## 🚀 Phase 54.4: ATRBasedコード改善【完了・大成功】

### 実施日
2025年12月16日

### 目的
ATRBased（PF 0.96）のPFを1.0+に改善（根本原因対処）

### 問題分析

ATRBased（PF 0.96）とBBReversal（PF 1.92）の比較分析により根本原因を特定：

| 項目 | ATRBased（問題） | BBReversal（成功） |
|------|------------------|-------------------|
| **BB閾値** | 0.85 / 0.15（緩い） | 0.95 / 0.05（厳格） |
| **シグナル条件** | BB **または** RSI | BB **かつ** RSI |
| **ADXフィルタ** | **なし** | < 20（レンジのみ） |
| **RR比** | 0.67:1 | 2.56:1 |

**根本原因**: ATRBasedは条件が緩いため：
1. トレンド相場でも逆張りシグナル発生 → 負けトレードが大きい
2. 極端でないBB位置でもシグナル発生 → 勝ちトレードが小さい

### 実施内容

#### 1. シグナル条件厳格化（BBReversal同様）

```python
# 変更前: BB または RSI でシグナル生成
elif bb_signal != 0:  # BBシグナルのみ → シグナル生成
elif rsi_signal != 0:  # RSIシグナルのみ → シグナル生成

# 変更後: BB かつ RSI 一致のみ
if bb_signal != 0 and rsi_signal != 0 and bb_signal == rsi_signal:
    # シグナル生成
else:
    # HOLD
```

#### 2. ADXフィルタ追加

```python
# analyzeメソッドに追加
if current_adx > adx_filter_threshold:  # デフォルト: 25
    return HOLD  # トレンド相場では逆張り回避
```

#### 3. 設定追加

```yaml
strategies:
  atr_based:
    require_both_signals: true  # BB+RSI両方必須
    adx_filter_threshold: 25    # ADX > 25 でHOLD
```

### コード変更

- `src/strategies/implementations/atr_based.py`:
  - `analyze`: ADXフィルタ追加
  - `_make_decision`: require_both_signals対応
  - `get_required_features`: adx_14追加

- `config/core/thresholds.yaml`:
  - tight_range重み戻し（ATR 0.30, BBR 0.50）
  - ATRBased新設定追加

### 検証結果（120日分析）

| 指標 | 変更前 | 変更後 | 変化 |
|------|--------|--------|------|
| **PF** | 0.96 | **1.83** | **+90.6%** ✅ |
| **取引数** | 205 | 38 | -81.5% |
| **勝率** | 59% | 55.3% | -3.7pt |
| **平均勝ち** | 1,336円 | **3,423円** | +156% |
| **平均負け** | 1,996円 | 2,315円 | +16% |
| **RR比** | 0.67:1 | **1.48:1** | +121% |
| **総損益** | -6,030円 | **+32,533円** | 黒字転換 |

### 成果

- **ATRBased PF 0.96 → 1.83**（目標1.05の174%達成）
- RR比大幅改善: 0.67:1 → 1.48:1
- 総損益黒字転換: -6,030円 → +32,533円

### 関連コミット

| コミット | 内容 |
|---------|------|
| `d6463b3b` | feat: Phase 54.4 ATRBased PF改善（0.96→1.83） |

### 180日バックテスト結果 ✅ 完了

**実行日時**: 2025/12/16 09:45 JST
**Run ID**: 20259416064

| 指標 | 結果 | 目標 | 評価 |
|------|------|------|------|
| **PF** | **1.95** | ≥1.35 | ✅ **大幅達成（+44%）** |
| **勝率** | **58.97%** | ≥50% | ✅ **達成（+9pt）** |
| **取引数** | 78件 | - | 適正 |
| **最大DD** | **0.05%** | ≤0.5% | ✅ **達成** |
| **RR比** | 1.30:1 | - | 良好 |
| **総損益** | +297円 | - | 黒字 |

**レジーム別パフォーマンス**:

| レジーム | 取引数 | 勝率 | 総損益 |
|---------|--------|------|--------|
| tight_range | 69件 | 57.97% | +236円 |
| normal_range | 9件 | 66.67% | +61円 |

### Phase 54.4 成果サマリー

**ATRBased改善の効果**:
- `require_both_signals: true`（BB+RSI両方必須）
- `adx_filter_threshold: 25`（トレンド回避）

**結果**: 全体PF **1.95**（Phase 53.13の1.25から**+56%改善**）

---

## 📈 Phase 54 現在の戦略別PF（Phase 54.4後）

| 戦略 | PF | 評価 |
|------|-----|------|
| BBReversal | **1.92** | 最高 |
| **ATRBased** | **1.83** | **Phase 54.4達成** ✅ |
| MACDEMACrossover | **1.50** | 良好 |
| DonchianChannel | **1.08** | Phase 54.3-B達成 |
| ADXTrendStrength | **1.04** | 良好 |
| StochasticReversal | 0.02 | 無効化済み |

**tight_range戦略（ATRBased + BBReversal + DonchianChannel）全てPF 1.0+達成**

---

## 🔗 関連コミット

| コミット | 内容 |
|---------|------|
| `021a4423` | docs: Phase 54.0 ML予測分析完了 |
| `35a02ab5` | feat: Phase 54.2-54.3-B 戦略エントリー基準最適化 |
| `d6463b3b` | feat: Phase 54.4 ATRBased PF改善（0.96→1.83） |

---

## 📝 Phase 54.4 総括【完了】

### 目標達成状況

| 指標 | 目標 | 結果 | 達成率 |
|------|------|------|--------|
| PF | ≥1.35 | **1.95** | **144%** ✅ |
| 勝率 | ≥50% | **58.97%** | **118%** ✅ |
| 最大DD | ≤0.5% | **0.05%** | **達成** ✅ |

### Phase 54.4 成果

1. **ATRBased PF 0.96 → 1.83**（+90.6%）
2. **全体PF 1.25 → 1.95**（+56%）
3. **tight_range主要戦略すべてPF 1.0+達成**
   - ATRBased: 1.83
   - BBReversal: 1.92
   - DonchianChannel: 1.08

### 本番稼働継続判断

**継続推奨** - Phase 53.13比で大幅な性能改善達成

---

## ✅ Phase 54.5: 条件緩和・取引数回復【完了】

### 実施日
2025年12月16-17日

### 背景・問題

Phase 54.4でPF 1.95・勝率58.97%を達成したが、重大な問題を発見：

| 指標 | Phase 54.4 | 問題点 |
|------|------------|--------|
| **取引数** | 78件/180日 | 少なすぎる |
| **総損益** | +297円 | **0.3%/180日（論外レベル）** |
| **ポジションサイズ** | 0.0001 BTC固定 | 最小取引単位のみ |

**根本原因**:
1. `require_both_signals: true`（BB+RSI両方必須）が厳しすぎる
2. 全取引が0.0001 BTC（最小取引単位）で実行

### 実施内容

#### 1. ATRBased条件緩和

```yaml
strategies:
  atr_based:
    require_both_signals: false  # true → false（単独シグナル許可）
    adx_filter_threshold: 25     # 25維持（ADXフィルタは厳格のまま）
```

#### 2. ADXフィルタ緩和検証（却下）

| ADXフィルタ | 取引数 | PF | 総損益 | 判定 |
|------------|--------|-----|--------|------|
| 25（require: true） | 38件 | 1.83 | +32,533円 | - |
| 30（require: false） | 92件 | 0.98 | -1,357円 | ❌ |
| 35（require: false） | 122件 | 0.72 | -35,077円 | ❌ |
| **25（require: false）** | **63件** | **1.95** | **+46,572円** | ✅ **採用** |

**結論**: ADXフィルタ緩和は逆効果（トレンド相場での逆張りで損失拡大）

#### 3. StochasticReversal改善（効果限定的）

```yaml
stochastic_reversal:
  stoch_overbought: 90  # 80 → 90
  stoch_oversold: 10    # 20 → 10
  bb_width_threshold: 0.02  # 新規
  require_crossover: false  # 新規
```

結果: PF 0.02 → 0.03（改善するも依然低い、重み0維持）

### 180日バックテスト結果

**Run ID**: 20265756678

| 指標 | Phase 54.4 | Phase 54.5 | 変化 |
|------|------------|------------|------|
| **取引数** | 78件 | **131件** | **+68%** ✅ |
| **勝率** | 58.97% | **58.02%** | -1pt |
| **総損益** | +297円 | **+478円** | **+61%** ✅ |
| **PF** | 1.95 | **1.91** | -2% |
| **最大DD** | 0.05% | **0.07%** | +0.02pt |

### ポジションサイズ問題の発見

バックテストログ分析により、全取引が**0.0001 BTC（最小取引単位）**で実行されていることを確認：

```
✅ 注文実行成功 - 数量: 0.0001 BTC, 価格: ¥16,559,221
✅ 注文実行成功 - 数量: 0.0001 BTC, 価格: ¥16,461,382
```

**原因**:
1. Kelly履歴不足 → 最小単位使用（kelly.py:268-288）
2. 保守的設計（3方式の最小値採用）
3. max_position_ratio: 3%でもBTC高値で0.0001875 BTC

**影響**: 131取引で+478円 = **平均3.65円/取引**（著しく低い）

### 関連コミット

| コミット | 内容 |
|---------|------|
| `60a5877d` | fix: Phase 54.5 条件緩和（取引数回復） |

### Phase 54.5 成果

1. **取引数**: 78件 → 131件（+68%）
2. **総損益**: +297円 → +478円（+61%）
3. **PF・勝率・DD**: 良好維持
4. **問題発見**: ポジションサイズが最小単位固定

---

## ✅ Phase 54.6: ポジションサイズ最適化・取引数回復【完了】

### 実施日
2025年12月17日

### 目的
1. ポジションサイズを最適化し、総損益を大幅改善
2. 取引数をさらに回復し、レンジボットとしての効率向上

### 背景

Phase 54.5で発見した問題:
- 全取引が0.0001 BTC（最小取引単位）
- 100,000円資金に対して1.6%のポジション
- PF 1.91でも総損益が極小

### Kelly基準による理論最適値

```
Kelly % = (勝率 × 勝敗比率 - 敗率) / 勝敗比率
       = (0.58 × 1.3 - 0.42) / 1.3
       = 25.7%
```

### 実施内容

#### 1. ポジションサイズ設定変更（thresholds.yaml）

```yaml
risk:
  kelly_criterion:
    max_position_ratio: 0.10    # 3% → 10%
  position_sizing:
    max_position_ratio: 0.10    # 5% → 10%
  dynamic_position_sizing:
    low_confidence:
      min_ratio: 0.03    # 1% → 3%
      max_ratio: 0.05    # 3% → 5%
    medium_confidence:
      min_ratio: 0.05    # 3% → 5%
      max_ratio: 0.08    # 5% → 8%
    high_confidence:
      min_ratio: 0.08    # 5% → 8%
      max_ratio: 0.10    # 10%維持
```

#### 2. 最大注文サイズ変更（unified.yaml）

```yaml
production:
  max_order_size: 0.001   # 0.0005 → 0.001（10万円×10%対応）
```

#### 3. 戦略条件緩和（thresholds.yaml）

```yaml
strategies:
  atr_based:
    adx_filter_threshold: 30     # 25 → 30
    min_confidence: 0.32         # 0.35 → 0.32

  donchian_channel:
    min_confidence: 0.35         # 0.40 → 0.35
    reversal_threshold: 0.04     # 0.03 → 0.04
```

#### 4. weight配分調整（thresholds.yaml）

```yaml
dynamic_strategy_selection:
  regime_strategy_mapping:
    tight_range:
      ATRBased: 0.35           # 0.30 → 0.35
      BBReversal: 0.40         # 0.50 → 0.40
      DonchianChannel: 0.25    # 0.20 → 0.25
```

### 60日分析結果（ローカル検証）

| 戦略 | 取引数 | 勝率 | PF | 評価 |
|------|--------|------|-----|------|
| ATRBased | 95件 | 52.6% | 0.84 | 個別PF<1（ML統合で改善見込み） |
| DonchianChannel | 179件 | 59.8% | 0.89 | 個別PF<1（ML統合で改善見込み） |
| BBReversal | 14件 | 42.9% | **1.92** | 最高性能 |
| ADXTrendStrength | 175件 | 34.9% | 1.06 | 中立 |
| MACDEMACrossover | 24件 | 33.3% | 1.50 | 良好 |
| **合計** | **487件** | - | - | **8.1件/日** |

### 取引数とPFのトレードオフに関する考察

| 設定 | ATRBased PF | 取引数 | 総損益見込み |
|------|-------------|--------|-------------|
| 厳格（Phase 54.4） | 1.83 | 78件/180日 | +297円（低い） |
| バランス（Phase 54.6） | 1.15-1.30見込み | 200-300件見込み | **+5,000円見込み** |

**結論**: PFを1.15-1.30程度に抑えつつ、取引数を増やして**総利益を最大化**する方針を採用

### 期待効果

| 設定 | 現在 | 10%設定後 | 改善 |
|------|------|----------|------|
| ポジションサイズ | 0.0001 BTC | ~0.0006 BTC | **6倍** |
| 1取引あたり | ~1,600円 | ~10,000円 | **6倍** |
| 取引数/180日 | 131件 | 200-300件見込み | +50-130% |
| 総損益/180日 | +478円 | **+5,000-10,000円見込み** | **10-20倍** |

### テスト結果

- **全テスト**: 1,203件成功（100%）
- **カバレッジ**: 65.42%
- **品質チェック**: flake8/isort/black全てPASS

### 追加修正: DataService注入（フォールバックATR問題修正）

#### 発見した問題

GCP本番環境診断中に、フォールバックATRが過去24時間で12回使用（約12%）されていることを確認。

**ATR取得の3段階フロー**:

| Level | 方法 | 状況 |
|-------|------|------|
| Level 1 | `evaluation.market_conditions`から取得 | 88%成功 |
| Level 2 | `DataService`経由で取得 | ❌ **未接続（常にスキップ）** |
| Level 3 | フォールバック（500,000円） | 12%発生 |

**根本原因**: `ExecutionService`に`data_service`が注入されておらず、Level 2が無効化状態

#### 修正内容

**1. executor.py: data_service初期化追加**

```python
# 関連サービスの初期化（後で注入される）
self.order_strategy = None
self.stop_manager = None
self.position_limits = None
self.balance_monitor = None
self.position_tracker = None
self.data_service = None  # Phase 54.6: ATR取得Level 2用（追加）
```

**2. executor.py: inject_services更新**

```python
def inject_services(
    self,
    order_strategy=None,
    stop_manager=None,
    position_limits=None,
    balance_monitor=None,
    position_tracker=None,
    data_service=None,  # Phase 54.6追加
) -> None:
    # ...
    if data_service:
        self.data_service = data_service
```

**3. orchestrator.py: data_service注入追加**

```python
execution_service.inject_services(
    position_limits=position_limits,
    balance_monitor=balance_monitor,
    order_strategy=order_strategy,
    stop_manager=stop_manager,
    position_tracker=position_tracker,
    data_service=data_service,  # Phase 54.6: ATR取得Level 2用
)
```

#### 期待効果

| 指標 | 修正前 | 修正後見込み |
|------|--------|-------------|
| フォールバック率 | 12% | **<2%** |
| ATR取得成功率 | 88% | **>98%** |
| TP/SL精度 | やや保守的 | 最適化 |

#### 影響範囲

- **BUY/SELL/HOLD判断**: 影響なし（ATRは判断後のTP/SL計算のみに使用）
- **TP/SL計算**: 精度向上（フォールバック500,000円ではなく実ATR使用）

### 関連コミット

| コミット | 内容 |
|---------|------|
| `0b86ab13` | Phase 54.6: 取引数回復 + ポジションサイズ10% |
| `d23ce458` | fix: Phase 54.6 DataService注入（フォールバックATR修正） |

### 180日バックテスト結果 ✅ 完了

**実行日時**: 2025/12/17 08:34 JST
**Run ID**: 20282969800

| 指標 | Phase 54.5 | Phase 54.6 | 変化 |
|------|------------|------------|------|
| **取引数** | 131件 | **200件** | **+53%** ✅ |
| **勝率** | 58.02% | **57.00%** | -1pt |
| **PF** | 1.91 | **1.81** | -5% |
| **総損益** | +478円 | **+679円** | **+42%** ✅ |
| **最大DD** | 0.07% | **0.08%** | 微増 |

**レジーム別パフォーマンス**:

| レジーム | 取引数 | 勝率 | 総損益 |
|---------|--------|------|--------|
| tight_range | 190件 | 55.26% | +546円 |
| normal_range | 10件 | 90.00% | +132円 |

**Phase 54.6 成果**:
1. 取引数: 131件 → 200件（+53%）
2. 総損益: +478円 → +679円（+42%）
3. PF/勝率: 高品質維持（PF 1.81、勝率57%）

---

## ✅ Phase 54.7: Kelly基準改修・ML設定緩和【完了】

### 実施日
2025年12月17-18日

### 目的
1. バックテストでKelly履歴が蓄積されない問題を修正
2. ML設定緩和により取引数を増加

### 問題分析

#### Kelly基準の問題

| モード | Kelly履歴記録 | ポジションサイズ |
|--------|--------------|----------------|
| **ライブ** | ✓ 記録される | 動的計算（Kelly基準） |
| **バックテスト** | ✗ **記録されない** | 固定0.0001 BTC |

**根本原因**: バックテスト決済処理で`DrawdownManager`のみに記録、Kelly履歴に未記録

### 実施内容

#### 1. Kelly履歴蓄積修正（backtest_runner.py）

**修正箇所1**: `_check_tp_sl_triggers()` メソッド（Line 820-828付近）

```python
# 追加：Kelly履歴に記録
if hasattr(self.orchestrator, 'risk_manager') and self.orchestrator.risk_manager:
    self.orchestrator.risk_manager.record_trade_result(
        profit_loss=pnl,
        strategy_name=strategy_name,
        confidence=0.5  # デフォルト信頼度
    )
```

**修正箇所2**: `_force_close_remaining_positions()` メソッド（Line 891付近）
- バックテスト終了時の強制決済でも同様にKelly記録追加

#### 2. ML設定緩和（thresholds.yaml）

```yaml
ml_integration:
  hold_conversion_threshold: 0.25   # 0.30 → 0.25

  regime_ml_integration:
    tight_range:
      min_ml_confidence: 0.45       # 0.50 → 0.45
      disagreement_penalty: 0.95    # 0.92 → 0.95
    normal_range:
      disagreement_penalty: 0.95    # 0.90 → 0.95
```

#### 3. ML再学習（閾値0.005・SMOTE・n_trials 50）

55特徴量・3クラス分類でモデル再訓練:

| モデル | Test F1 | CV F1 |
|--------|---------|-------|
| LightGBM | 0.906 | 0.896±0.048 |
| XGBoost | 0.917 | 0.899±0.049 |
| RandomForest | 0.916 | 0.904±0.045 |

### 問題発見: ML HOLD比率96%

モデル性能検証で重大な問題を発見：

| 予測クラス | 比率 | 評価 |
|-----------|------|------|
| HOLD | **96%** | ❌ 異常 |
| BUY | 2% | - |
| SELL | 2% | - |

**ユーザー判定**: HOLD率90%以上は失敗（戦略判断の意味をなさない）

**根本原因**: 閾値0.005では訓練データのHOLD比率が92-94%
→ SMOTEでも元データ偏りすぎで効果不十分

### Phase 54.7 成果

1. ✅ Kelly履歴蓄積修正完了（backtest_runner.py）
2. ✅ ML設定緩和適用（thresholds.yaml）
3. ✅ ML再学習完了（高F1スコア達成）
4. ❌ **問題発見**: HOLD比率96%（Phase 54.8で解決予定）

---

## ✅ Phase 54.8: ML HOLDバイアス問題解決【完了】

### 実施日
2025年12月18日

### 目的
MLが常にHOLDを返す問題を根本解決（目標: HOLD ≤ 60%）

### 問題

| 項目 | 改修前 | 目標 |
|------|--------|------|
| **HOLD予測率** | 96% | ≤ 60% |
| **BUY予測率** | 2% | 15-35% |
| **SELL予測率** | 2% | 15-35% |

### 根本原因分析

#### 1. SMOTEバグ発見（重大）

```python
# scripts/ml/create_ml_models.py Line 887 & 957
if self.use_smote and self.n_classes == 2:  # ← 2クラスのみ！
```

**影響**: `--n-classes 3 --use-smote` でもSMOTEは一切適用されなかった

#### 2. 閾値とHOLD率の関係

| 閾値 | 訓練データHOLD比率 | 予測HOLD率 | 評価 |
|------|-------------------|-----------|------|
| ±0.5% (0.005) | 92-94% | 96% | ❌ 失敗 |
| ±0.3% (0.003) | 77% | 93.7% | ❌ FAIL |
| ±0.1% (0.001) | 44.6% | 68.0% | ⚠️ 目標未達 |
| ±0.08% (0.0008) | 37.1% | 71.3% | ⚠️ 目標未達 |
| **±0.05% (0.0005)** | **25.9%** | **55.0%** | **✅ 目標達成** |

### 解決策

#### Step 1: SMOTE 3クラス対応修正 ✅ 完了

```python
# 変更前
if self.use_smote and self.n_classes == 2:

# 変更後
if self.use_smote:  # 全クラス数で適用
```

#### Step 2: 検証スクリプト改修 ✅ 完了

`validate_ml_prediction_distribution.py` を実データ検証に変更:
- ランダム特徴量ではなく実CSV + FeatureGenerator使用
- より実運用に近い検証

#### Step 3: 最適閾値決定（総合分析）✅ 完了

**Phase 54.6バックテスト結果を考慮**:
- PF 1.81、勝率 57%、取引数 200件
- 95%がtight_range（レンジ相場）
- 戦略重み 75%、ML重み 25%（MLは補完役）

**閾値選定根拠**:

| threshold | 予測HOLD | SELL | BUY | CV F1 | 取引機会 |
|-----------|----------|------|-----|-------|----------|
| 0.001 | 68.0% | 21.3% | 10.7% | 0.39 | 32.0% |
| 0.0008 | 71.3% | 12.7% | 16.0% | 0.33 | 28.7% |
| **0.0005** | **55.0%** | **28.7%** | **16.3%** | **0.32** | **45.0%** |

**決定: threshold 0.0005 採用**

採用理由:
1. **HOLD 55% < 60%**: ユーザー要件達成
2. **取引機会最大化**: 45%がBUY/SELL（他は28-32%）
3. **戦略との整合性**: SELL優勢（1.76:1）がレンジ逆張りに適合
4. **リスク軽減**: 戦略75%重みがMLミスをカバー

#### Step 4: ML再学習（最終版）✅ 完了

```bash
python scripts/ml/create_ml_models.py \
  --n-classes 3 \
  --threshold 0.0005 \
  --use-smote \
  --optimize \
  --n-trials 30
```

**訓練データクラス分布**（閾値0.0005）:
- SELL 36.8%, HOLD 25.9%, BUY 37.2%（バランス良好）

**SMOTE適用**: 4885 → 5556サンプル（33.3%均等化）

**fullモデル（55特徴量）学習結果**:

| モデル | Test F1 | CV F1 |
|--------|---------|-------|
| LightGBM | 0.422 | 0.345±0.052 |
| XGBoost | 0.423 | 0.321±0.064 |
| RandomForest | 0.446 | 0.304±0.071 |

※ F1低下は正常（閾値縮小で分類難度上昇）、戦略75%重みでカバー

### 最終検証結果

```
>>> MLモデル予測分布検証（Phase 54.8 - 実データ版）
  実データ読み込み完了: 300行
  特徴量生成完了: 300行 x 59列
  実データでの予測分布テスト...
     SELL (class 0): 86回 (28.7%)
     HOLD (class 1): 165回 (55.0%)
     BUY  (class 2): 49回 (16.3%)
     最大クラス比率: 55.0%
  [OK] モデルのクラスバランスは良好です（最大クラス: 55.0% < 80%）
>>> MLモデル予測分布検証完了
```

### 結果

| 項目 | 閾値0.005 | 閾値0.0005 | 変化 |
|------|-----------|-----------|------|
| **HOLD率** | 96% | **55%** | **-41pt** ✅ |
| **BUY率** | 2% | **16.3%** | +14.3pt |
| **SELL率** | 2% | **28.7%** | +26.7pt |
| **最大クラス比率** | 96% | **55%** | **-41pt** ✅ |

### 品質チェック結果

| チェック | 結果 |
|---------|------|
| flake8 | ✅ PASS |
| isort | ✅ PASS |
| black | ✅ PASS |
| pytest | ✅ PASS（1,191テスト・65.42%カバレッジ） |

### 修正対象ファイル

| ファイル | 変更内容 | 状態 |
|---------|---------|------|
| `scripts/ml/create_ml_models.py` | SMOTE 3クラス対応修正 | ✅ 完了 |
| `scripts/testing/validate_ml_prediction_distribution.py` | 実データ検証に改修 | ✅ 完了 |
| `models/production/ensemble_full.pkl` | 閾値0.0005で再学習 | ✅ 完了 |
| `models/production/ensemble_basic.pkl` | 閾値0.0005で再学習 | ✅ 完了 |
| `models/production/production_model_metadata.json` | メタデータ更新 | ✅ 完了 |

### Phase 54.8 成果

1. ✅ **SMOTEバグ修正**: 3クラス分類でもSMOTE適用可能に
2. ✅ **HOLD比率改善**: 96% → 55%（-41pt、目標60%以下達成）
3. ✅ **取引機会最大化**: BUY/SELL合計45%（最多）
4. ✅ **検証スクリプト改修**: 実データ検証で実運用精度向上
5. ✅ **閾値最適化**: 0.0005がレンジ逆張り戦略に最適と判定
6. ✅ **バックテストML分析機能**: レポートにML分析セクション追加

### バックテストML分析機能（Phase 54.8追加）

バックテスト結果にML性能分析を追加:

**分析項目**:
- **予測分布**: SELL/HOLD/BUY件数・比率（HOLD≤60%チェック）
- **信頼度統計**: 平均信頼度・高信頼度比率
- **ML vs 戦略一致率**: 一致率・勝率比較

**出力例**:
```
================================================================================
📊 ML Analysis (Phase 54.8)
================================================================================
Prediction Distribution:
  SELL: 5,432 (31.4%)
  HOLD: 8,234 (47.6%)  ← Target ≤60% [PASS]
  BUY:  3,605 (20.8%)

Confidence Statistics:
  Average: 0.542 | High (>60%): 23.4%

ML vs Strategy Agreement:
  Agreement Rate: 58.5% (412/697 trades)
  Agreement Win Rate: 48.1% | Disagreement Win Rate: 47.7%
================================================================================
```

**修正ファイル**:
- `src/backtest/reporter.py`: MLAnalyzerクラス追加・TradeTracker拡張
- `src/core/execution/backtest_runner.py`: ML情報記録

---

**📅 最終更新**: 2025年12月18日 - **Phase 54.8完了**（ML HOLDバイアス問題解決・バックテストML分析機能追加）
