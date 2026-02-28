# Phase 66: ライブ取引再開 — 根本原因修正 + RR比改善

**期間**: 2026年2月26日-
**状態**: 進行中

| 修正 | 内容 | 状態 |
|------|------|------|
| **修正1** | HOLD信頼度ハードコード修正（ATRBased 5箇所 + BBReversal 1箇所） | ✅ 完了 |
| **修正2** | レジーム分類バグ修正（EMA slope閾値 0.01→0.003） | ✅ 完了 |
| **修正3** | ML再学習 + Recovery閾値調整 | ✅ 完了 |
| **修正4** | バックテストTP再計算バグ修正（ポジションサイズ不一致） | ✅ 完了 |
| **修正5** | RR分析機能をstandard_analysis.pyに統合 | ✅ 完了 |
| **修正6** | SL500円固定金額の実装 | ✅ 完了 |
| **修正7** | 取引数激減の根本原因診断 + Recovery閾値再調整 | ✅ 診断完了・調整済 |

---

## 背景

Phase 65.16デプロイ後、24時間（59サイクル）で**取引ゼロ**。GCPログ分析で3つの根本原因を特定。

---

## 修正1: HOLD信頼度ハードコード修正

### 問題

`SignalBuilder.create_hold_signal()` が `confidence=0.5` をハードコード。ATRBasedは最大重み(0.50)を持つ主力戦略のため、HOLD(0.5×0.50=0.250)が常にSELL(0.545×0.30=0.164)に勝ち、取引が発生しなかった。

BBReversalも同じ問題（`SignalBuilder.create_hold_signal()`をconfidenceなしで呼び出し→デフォルト0.5）。

### 対策

| ファイル | 変更 |
|---------|------|
| `src/strategies/utils/strategy_utils.py` | `create_hold_signal()`に`confidence`パラメータ追加（デフォルト0.5で後方互換） |
| `src/strategies/implementations/atr_based.py` | 5箇所の呼び出しに`confidence=self.config["hold_confidence"]`(0.20)追加 |
| `src/strategies/implementations/bb_reversal.py` | 1箇所の呼び出しに`confidence=self.config["hold_confidence"]`(0.20)追加 |

### 効果（normal_rangeでの投票計算）

| 戦略 | 重み | 信頼度(修正前) | 加重(修正前) | 信頼度(修正後) | 加重(修正後) |
|------|------|--------------|-----------|--------------|-----------|
| ATRBased | 0.50 | 0.500 | 0.250 | 0.200 | 0.100 |
| Stochastic | 0.30 | SELL 0.545 | 0.164 | SELL 0.545 | 0.164 |
| Donchian | 0.20 | 0.250 | 0.050 | 0.250 | 0.050 |

- 修正前: HOLD比率=0.300/0.464=**64.7%** → 常にHOLD
- 修正後: HOLD比率=0.150/0.314=**47.8%** → SELLが勝てる

---

## 修正2: レジーム分類バグ修正

### 問題

`_is_trending()` は `ADX > 25 AND |EMA_slope| > 0.01` の両方が必要。EMA slope = (現在EMA20 - 5本前EMA20) / 5本前EMA20 → 15分足5本=75分で1%の変動は相当大きい。結果: ADXが74でもEMA slopeが0.01未満ならtrendingにならず、デフォルトのnormal_rangeへフォールスルー。

### 対策

| ファイル | 変更 | 根拠 |
|---------|------|------|
| `config/core/thresholds.yaml` | `ema_slope_threshold: 0.01→0.003` | 75分で0.3%変動はトレンド判定として妥当。ADX>25とのAND条件でノイズ誤判定リスク低い |

### 効果

バックテストではtrending判定は1件のみ（2025年7-12月データ）。ライブ環境（2026年2月、高ボラ期）での効果を期待。

---

## バックテスト結果（修正1+2）

**期間**: 2025/07/01 - 2025/12/31（183日間）

### 前回比較

| 指標 | Phase 65.16 | Phase 66 (修正1+2) | 変化 |
|------|------------|-------------------|------|
| 総損益 | ¥+102,135 | ¥+97,236 | -4.8% |
| PF | 2.47 | 1.82 | -26% |
| 勝率 | 89.2% | 85.0% | -4.2pt |
| 最大DD | 0.94% | 0.97% | +0.03pt |
| 取引数 | — | 535件 | — |

### レジーム分布

| レジーム | 取引数 | 勝率 | 総損益 |
|---------|--------|------|--------|
| tight_range | 481件 (89.9%) | 84.4% | ¥+82,881 |
| normal_range | 53件 (9.9%) | 90.6% | ¥+13,896 |
| trending | 1件 (0.2%) | 100% | ¥+459 |

### 信頼度帯別（ML再学習の必要性を示唆）

| 信頼度帯 | 取引数 | 勝率 | 総損益 |
|---------|--------|------|--------|
| 低（<50%） | 508件 | 86.0% | ¥+100,700 |
| 中（50-65%） | 22件 | 68.2% | ¥-1,606 |
| 高（≥65%） | 5件 | 60.0% | ¥-1,858 |

→ 低信頼度が全利益、中〜高信頼度はマイナス。MLモデル19日前作成で劣化を示唆。

### 戦略別

| 戦略 | 取引数 | 勝率 | 総損益 |
|------|--------|------|--------|
| ATRBased | 363件 | 86.8% | ¥+80,493 |
| DonchianChannel | 131件 | 81.7% | ¥+9,731 |
| StochasticReversal | 40件 | 80.0% | ¥+6,554 |
| ADXTrendStrength | 1件 | 100% | ¥+459 |

---

## 修正3: ML再学習 + Recovery閾値調整

### 問題

- MLモデルは19日前（2/6）に作成。信頼度分布が劣化（高信頼度ほど負ける逆転現象）
- ML Signal Recoveryの`min_ml_confidence=0.55`だが、ライブML信頼度は最大0.450 → Recoveryが一度も発動しない

### 対策

1. 最新180日分データでモデル再学習（Optuna最適化 n-trials=50）
2. 再学習後の信頼度分布に基づきRecovery閾値を調整

| ファイル / 設定 | 変更前 | 変更後 | 根拠 |
|---------------|--------|--------|------|
| `models/production/ensemble_full.pkl` | 2/6作成（19日前） | 2/26再学習 | 最新180日分データ（11,793サンプル） |
| `models/production/ensemble_basic.pkl` | 2/6作成 | 2/26再学習 | 同上 |
| `min_ml_confidence` | 0.55 | 0.45 | 平均信頼度0.425+0.025。平均以上に自信がある時のみRecovery発動 |
| `recovery_confidence_cap` | 0.35 | 0.30 | 保守的サイズで過大エントリーを防止 |

### 再学習モデルの性能

| モデル | Accuracy | F1 Score | CV F1 Mean |
|--------|----------|----------|------------|
| LightGBM | 0.484 | 0.465 | 0.385 |
| XGBoost | 0.485 | 0.464 | 0.387 |
| RandomForest | 0.494 | 0.467 | 0.378 |

### 信頼度分布（検証時）

| 指標 | 値 |
|------|-----|
| 平均信頼度 | 0.425 |
| 最大信頼度 | 0.494 |
| 最小信頼度 | 0.384 |
| 標準偏差 | 0.017 |
| 高信頼度(>60%) | 0.0% |

→ 信頼度が0.40-0.50に集中する控えめなモデル。旧`min_ml_confidence=0.55`では最大でも届かず、Recovery発動不能だった。

---

## 修正4: バックテストTP再計算バグ修正（ポジションサイズ不一致）

### 問題

バックテストの平均TP利益が161円（目標500円の32%）しかない。根本原因はTP距離計算時のポジションサイズと実際のポジションサイズの不一致。

| 段階 | ポジションサイズ | 用途 | 平均値 |
|------|-----------------|------|--------|
| シグナル生成 | `SignalBuilder._calculate_dynamic_position_size()` | TP距離計算 | ~0.020 BTC |
| リスク評価 | `position_integrator.calculate_integrated_position_size()` | 実際の取引量 | ~0.006 BTC |

**結果**: `TP距離 = 500 / 0.020 = 25,000円` → `実利益 = 25,000 × 0.006 = 150円`（500円にならない）

### コードフロー

```
1. strategy_utils.py L687: position_size = SignalBuilder._calculate_dynamic_position_size(...)
                                               → ~0.020 BTC（残高ベース・単一ポジション想定）
2. strategy_utils.py L715: calculate_stop_loss_take_profit(position_amount=position_size)
                                               → TP = entry ± (500 / 0.020)
3. manager.py L284: position_size = position_integrator.calculate_integrated_position_size(...)
                                               → ~0.006 BTC（ML信頼度・既存ポジション考慮）
4. manager.py L302-307: take_profit = signal.take_profit  ← 0.020で計算済みTPをそのまま使用
5. executor.py L938: amount = evaluation.position_size     ← 0.006 BTC
6. executor.py L1005: "take_profit": evaluation.take_profit ← 0.020で計算されたTP（不一致！）
```

ライブモードは `tp_sl_manager.calculate_tp_sl_for_live_trade()` (L1492-1502) が実際の`position_amount`でTPを再計算しているため問題なし。**バックテストのみ**のバグ。

### 対策

`manager.py` L309以降で、リスク評価後の実際の`position_size`を使って固定金額TPを再計算。

```python
# Phase 66.4: 固定金額TP再計算（ポジションサイズ不一致修正）
if position_size > 0 and last_price > 0:
    fixed_tp_config = get_threshold("position_management.take_profit.fixed_amount", {})
    if fixed_tp_config.get("enabled", False):
        recalculated_tp = RiskManager.calculate_fixed_amount_tp(
            action=trade_side, entry_price=last_price,
            amount=position_size, fee_data=None, config=fixed_tp_config,
        )
        if recalculated_tp:
            take_profit = recalculated_tp
```

### 修正後の期待効果

| 指標 | 修正前（バグあり） | 修正後（推定） |
|------|-----------------|---------------|
| 平均TP利益 | 161円 | ~500円 |
| 実効RR比 | 0.26:1 | 0.82:1 |
| 損益分岐勝率 | 79% | 55% |

---

## 修正5: RR分析機能をstandard_analysis.pyに統合

### 目的

修正4のバグ修正効果を定量評価するため、バックテスト標準分析にRR比分析セクションを追加。

### 追加内容

`scripts/backtest/standard_analysis.py` に以下を追加:

| 分析項目 | 内容 |
|---------|------|
| 実効RR比 | TP平均利益 / SL平均損失（レジーム別） |
| TP達成率 | 各TP取引のPnL / 目標500円の分布 |
| MAE安全率 | TP取引のMAE ≥ -500円の割合（SL固定化の安全性指標） |
| What-if SL固定 | SL=300〜800円固定時のTP取引影響シミュレーション |

### 出力例

```
== RR比・TP/SL分析 ==

■ 実効リスクリワード比
  TP取引(XX件): 平均 +XXX円
  SL取引(XX件): 平均 -XXX円
  実効RR比: X.XX:1（損益分岐勝率 XX.X%）

■ レジーム別RR
  tight_range:  TP平均 +XXX円 / SL平均 -XXX円 = RR X.XX:1 (損益分岐 XX%)
  normal_range: TP平均 +XXX円 / SL平均 -XXX円 = RR X.XX:1 (損益分岐 XX%)

■ TP達成率（目標500円）
  平均: XXX円 (XX.X%)  中央値: XXX円
  50-100円: XX件  100-300円: XX件  300-500円: XX件  500円+: XX件

■ What-if: SL固定金額シミュレーション
  SL=300円: TP影響XX件/XX件(XX.X%), 推定RR X.XX:1
  SL=500円: TP影響XX件/XX件(XX.X%), 推定RR X.XX:1
```

### 分類ロジックの注意点

`exit_reason` フィールドに基づいて分類。**バックテスト終了時の強制決済**（`exit_reason`に"TP"も"SL"も含まない）はRR計算から除外。これを含めると、数千円規模の異常PnLがSL平均を歪ませる。

---

## 修正6: SL500円固定金額の実装

### 背景

既存バックテスト46取引のMAE/MFE分析結果:

| 分析 | 結果 |
|------|------|
| TP取引(32件)のMAE ≥ -500円 | **96.9%** (31/32件) → SL=500円でも影響なし |
| SL取引(8件)のMFE ≥ 300円 | **0件** → SL取引はTP圏に届かない |

**SL=500円 + TP=500円 → RR比 1:1**（修正前の0.26:1から大幅改善、損益分岐勝率50%）

### 設計

固定TP（L432-467）と対称的な構造。ポジションサイズに依存せず常に最大500円の損失に制限。

```
SL距離 = (目標最大損失 - SL決済手数料) / ポジションサイズ
SL決済手数料 = 現在価格 × ポジションサイズ × Taker手数料率(0.1%)
```

| ポジションサイズ | 現行(0.4%固定) | 固定500円 | 変化 |
|-----------------|---------------|----------|------|
| 0.006 BTC | 66,800円幅 (≈400円損失) | 83,333円幅 (=500円損失) | 広がる（余裕増） |
| 0.010 BTC | 66,800円幅 (≈668円損失) | 50,000円幅 (=500円損失) | 狭まる（損失制限） |
| 0.020 BTC | 66,800円幅 (≈1,336円損失) | 25,000円幅 (=500円損失) | 大幅に狭まる |

### 変更箇所

#### 1. 設定追加 (`config/core/thresholds.yaml`)

```yaml
  stop_loss:
    # ...既存設定...
    fixed_amount:
      enabled: true
      target_max_loss: 500       # 1取引あたりの最大損失（円）
      include_exit_fee: true
      fallback_exit_fee_rate: 0.001  # Taker 0.1%
    regime_based:
      tight_range:
        max_loss_ratio: 0.004    # フォールバック用（既存）
        fixed_amount_target: 500 # レジーム別SL金額
      # ...各レジーム同様...
```

#### 2. シグナル生成時 (`src/strategies/utils/strategy_utils.py` L430)

%ベースSL距離計算後、固定金額が有効なら上書き:

```python
# Phase 66.6: 固定金額SLモードチェック
fixed_sl_config = get_threshold("position_management.stop_loss.fixed_amount", {})
if fixed_sl_config.get("enabled", False) and position_amount > 0:
    sl_target = get_threshold(
        f"position_management.stop_loss.regime_based.{regime}.fixed_amount_target",
        fixed_sl_config.get("target_max_loss", 500),
    )
    exit_fee = current_price * position_amount * exit_fee_rate
    fixed_sl_distance = (sl_target - exit_fee) / position_amount
    stop_loss_distance = fixed_sl_distance
```

#### 3. バックテスト再計算 (`src/trading/risk/manager.py` L337)

修正4と同じブロック内で、実際のposition_sizeでSLも再計算:

```python
# Phase 66.6: 固定金額SL再計算
fixed_sl_config = get_threshold("position_management.stop_loss.fixed_amount", {})
if fixed_sl_config.get("enabled", False):
    sl_distance = (sl_target - exit_fee) / position_size
    stop_loss = last_price ± sl_distance  # buy/sellに応じて
```

#### 4. ライブリカバリ (`src/trading/execution/tp_sl_manager.py`)

`_calculate_fixed_amount_sl_for_position()` メソッド追加。リカバリ時も固定金額SLを使用。

#### 5. 設定定数 (`src/trading/execution/tp_sl_config.py`)

```python
SL_FIXED_AMOUNT_ENABLED = "position_management.stop_loss.fixed_amount.enabled"
SL_FIXED_AMOUNT_TARGET = "position_management.stop_loss.fixed_amount.target_max_loss"
SL_FIXED_AMOUNT_EXIT_FEE = "position_management.stop_loss.fixed_amount.fallback_exit_fee_rate"
```

---

## 修正7: 取引数激減の根本原因診断 + Recovery閾値再調整

### 問題

修正1+2（旧モデル）で535取引を達成したが、修正3（ML再学習・新モデル投入）後に取引数が46に激減。コード変更はなくモデルのみ変更。`strategy_weight=0.85`なのに、なぜモデル変更だけで10倍の差が出るのか？

### 診断アプローチ

新規診断スクリプト `scripts/analysis/diagnose_trade_drop.py` を作成し、全キャンドルについて以下を分析:

1. 戦略集約結果（BUY/SELL/HOLD）
2. ML予測（prediction, confidence）
3. Recovery発動条件チェック（各閾値レベルで）

### 診断結果

| 項目 | 結果 |
|------|------|
| 自然なBUY/SELL集約（戦略のみ） | 1,412件 |
| 戦略集約がHOLD | 8,588件 |
| Recovery発動（閾値0.45） | 212件 |
| Recovery発動（閾値0.35） | 583件 |
| 新モデルのクラス分布 | SELL 49.4%, BUY 25.0%, HOLD 25.6% |
| 新モデルの平均信頼度 | BUY 0.29, SELL 0.38, HOLD 0.33 |

**重要な発見**: 当初の仮説（自然な取引~46件、Recovery~490件）は部分的に不正確。自然な戦略集約では1,412件のBUY/SELL判断が出ているが、バックテスト上では**マージン維持率80%未満予測**（23,781回のリジェクション）が新規エントリーをブロックしており、実際の取引数が46件に制限されている。

### Recovery閾値再調整

修正3で`min_ml_confidence: 0.55→0.45`に調整済みだったが、新モデルの信頼度分布を踏まえてさらに引き下げ:

| 設定 | 修正3時点 | 修正7後 | 根拠 |
|------|----------|---------|------|
| `min_ml_confidence` | 0.45 | 0.35 | 新モデルの平均BUY信頼度0.29、SELL信頼度0.38付近。0.35以上=平均以上の確信 |
| `recovery_confidence_cap` | 0.30 | 0.25 | Recovery取引のサイズを保守的に抑制 |

### バックテスト結果（修正7込み）

| 指標 | 値 |
|------|-----|
| 取引数 | 46件（28完了 + 強制決済） |
| 勝率 | 80.4% |
| PF | 33.28 |
| 最大DD | 0.31% |
| 総損益 | ¥+88,974 |

Recovery発動は263回に増加したが、マージン維持率制限により取引数は変わらず。取引数の制約はRecovery閾値ではなく、ポジション管理（維持率）側にある。

### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `scripts/analysis/diagnose_trade_drop.py` | 取引数激減の根本原因診断スクリプト |

---

## バックテスト結果（修正1-3）

（GitHub Actions実行中 — 完了後に記載）

## バックテスト結果（修正4-6込み）

（実行中 — 完了後に記載）

---

## 変更ファイル一覧

### 修正1-3

| ファイル | 変更内容 |
|---------|---------|
| `src/strategies/utils/strategy_utils.py` | `create_hold_signal()`にconfidenceパラメータ追加 |
| `src/strategies/implementations/atr_based.py` | 5箇所のcreate_hold_signal()にconfidence=config値追加 |
| `src/strategies/implementations/bb_reversal.py` | 1箇所のcreate_hold_signal()にconfidence=config値追加 |
| `config/core/thresholds.yaml` | `ema_slope_threshold: 0.01→0.003` |
| `config/core/thresholds.yaml` | `ml_signal_recovery.min_ml_confidence: 0.55→0.45` |
| `config/core/thresholds.yaml` | `recovery_confidence_cap: 0.35→0.30` |
| `models/production/ensemble_full.pkl` | MLモデル再学習（Optuna n-trials=50） |
| `models/production/ensemble_basic.pkl` | MLモデル再学習（基本特徴量版） |

### 修正4-6

| ファイル | 修正 | 変更内容 |
|---------|------|---------|
| `src/trading/risk/manager.py` | 修正4,6 | 固定金額TP/SL再計算（リスク評価後のposition_sizeで再計算） |
| `src/strategies/utils/strategy_utils.py` | 修正6 | シグナル生成時の固定金額SL距離計算 |
| `config/core/thresholds.yaml` | 修正6 | `stop_loss.fixed_amount`セクション + レジーム別`fixed_amount_target` |
| `src/trading/execution/tp_sl_manager.py` | 修正6 | `_calculate_fixed_amount_sl_for_position()`追加 + リカバリSL修正 |
| `src/trading/execution/tp_sl_config.py` | 修正6 | SL固定金額設定パス定数3件追加 |
| `scripts/backtest/standard_analysis.py` | 修正5 | RR分析セクション追加（実効RR・TP達成率・MAE安全率・What-if） |

### 修正7

| ファイル | 変更内容 |
|---------|---------|
| `scripts/analysis/diagnose_trade_drop.py` | 取引数激減の根本原因診断スクリプト（新規） |
| `config/core/thresholds.yaml` | `ml_signal_recovery.min_ml_confidence: 0.45→0.35` |
| `config/core/thresholds.yaml` | `recovery_confidence_cap: 0.30→0.25` |
