# Phase 67: SL 700円 + 勝率改善施策

**期間**: 2026年3月1日-
**状態**: バックテスト検証中

| 変更 | 内容 | 状態 |
|------|------|------|
| **変更1** | 固定金額SL 500円→700円（全レジーム） | ✅ 完了 |
| **変更2** | StochasticReversal重み削減 + ATRBased集中 | ✅ 完了 |
| **変更3 (67.2)** | Kelly=0時のDynamicフォールバック（ポジションサイズ復元） | ✅ 完了 |

---

## 背景

### Phase 66.8のバックテスト結果（2025/7-12月）

| 指標 | 値 |
|------|-----|
| 取引数 | 520件 |
| 勝率 | 49.0% |
| 総損益 | ¥-3,804 |
| PF | 0.97 |
| SL件数 | 265件 (51%) |
| TP件数 | 254件 (49%) |

### 根本原因分析

Phase 65（成功: +¥102,135、勝率85%）→ Phase 66.8（失敗: -¥3,804、勝率49%）の最大の差:

| 比較 | Phase 65 | Phase 66.8 | 差 |
|------|----------|-----------|-----|
| SL方式 | 0.4%（percentage-based） | 500円（fixed amount） | - |
| 実効SL金額 | ~660円 | 500円 | **160円狭い** |

SL 500円はBTC価格レベルに対して狭すぎ、正しい方向に動いた取引（95%がプラス圏経由）が
SLに引っかかっていた。

### 戦略別成績（Phase 66.8）

| 戦略 | 取引数 | 勝率 | 損益 | SL率 |
|------|--------|------|------|------|
| ATRBased | 332件 | 51.2% | **+¥3,992** | 49% |
| DonchianChannel | 148件 | 48.0% | -¥3,003 | 52% |
| **StochasticReversal** | **38件** | **34.2%** | **-¥6,006** | **66%** |

StochasticReversalは全赤字の主犯（38件で-¥6,006）。

---

## 変更1: 固定金額SL 500円→700円

### 数理的根拠

| 指標 | TP=500/SL=500 | TP=500/SL=700 |
|------|---------------|---------------|
| RR比 | 1.00 | 0.71 |
| 損益分岐勝率 | **50.0%** | **58.3%** |

勝率と期待値の関係（1取引あたり）:

| 勝率 | TP=500/SL=500 | TP=500/SL=700 |
|------|---------------|---------------|
| 55% | +¥25 | -¥40 |
| 60% | +¥50 | **+¥20** |
| 65% | +¥75 | **+¥80** |
| 70% | +¥100 | **+¥140** |
| 75% | +¥125 | **+¥200** |

勝率65%を超えるとSL=700円の方が期待値が高くなる。
Phase 65の実績（85%勝率、実効SL ~660円）から判断して十分達成可能。

### 変更箇所

**ファイル**: `config/core/thresholds.yaml`

| 設定パス | 変更前 | 変更後 |
|---------|--------|--------|
| `stop_loss.fixed_amount.target_max_loss` | 500 | **700** |
| `regime_based.tight_range.fixed_amount_target` | 500 | **700** |
| `regime_based.normal_range.fixed_amount_target` | 500 | **700** |
| `regime_based.trending.fixed_amount_target` | 500 | **700** |
| `regime_based.high_volatility.fixed_amount_target` | 500 | **700** |

---

## 変更2: StochasticReversal重み削減

### 変更箇所

**ファイル**: `config/core/thresholds.yaml`

| レジーム | 戦略 | 変更前 | 変更後 |
|---------|------|--------|--------|
| tight_range | StochasticReversal | 0.30 | **0.10** |
| tight_range | ATRBased | 0.30 | **0.45** |
| tight_range | DonchianChannel | 0.25 | **0.30** |
| tight_range | BBReversal | 0.15 | 0.15（維持） |
| normal_range | StochasticReversal | 0.30 | **0.10** |
| normal_range | ATRBased | 0.50 | **0.60** |
| normal_range | DonchianChannel | 0.20 | **0.30** |

### 根拠

- Phase 65ではATRBased（68%シェア）で85%勝率達成
- StochasticReversalを除外するだけで勝率49%→50%、損益-3,804→+2,201に改善
- 完全無効化しない理由: SL=700での改善度を確認したい

---

## 変更しないもの

| 項目 | 理由 |
|------|------|
| ML設定（信頼度閾値等） | SL変更後のML予測パフォーマンスを先に確認 |
| TP金額（500円） | Phase 61.12で最適と実証済み |
| Recovery設定 | Phase 66.8で調整済み、SL変更後に再評価 |
| DonchianChannel重み | Phase 65では70-82%勝率、SL変更で回復する可能性 |

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `config/core/thresholds.yaml` | SL 500→700円（5箇所）+ 戦略重み調整（6値） |
| `tests/unit/services/test_dynamic_strategy_selector.py` | tight_range重みテスト値更新 |
| `CLAUDE.md` | しおり更新（Phase 67）+ 固定金額SL/戦略重み記載更新 |

---

## 変更3 (Phase 67.2): Kelly=0時のDynamicフォールバック

### 根本原因

Phase 65 (+¥102,135) → Phase 67 (-¥13,319) の大幅悪化の調査で、
ポジションサイズが 0.022 BTC → 0.0066 BTC に 3.3倍縮小していることが判明。

**ポジションサイズ計算（加重平均）**:
```
integrated = kelly(0.0) × 0.5 + dynamic(0.0204) × 0.3 + risk_mgr(0.00016) × 0.2
           = 0 + 0.00612 + 0.000032
           = 0.00615 BTC  ← 実績 0.0066 と一致
```

**原因**: 固定TP/SL（500/700円）でpayoff ratio ≈ 0.71。Kelly正にはwin rate > 58.5%が必要。
現行56%ではKelly構造的に常に0 → 50%の重みが無駄に → ポジション1/3に崩壊。

### 修正内容

**ファイル**: `src/trading/risk/sizer.py`（2箇所）

Kelly ≤ min_trade_size 時にDynamic sizing単独で決定するフォールバック追加:

```python
# L109-120（動的サイジング有効時）
min_trade_size = get_threshold("production.min_order_size", 0.0001)
if kelly_size <= min_trade_size:
    integrated_size = dynamic_size  # Kelly無信号→Dynamic単独
else:
    integrated_size = (加重平均)

# L194-201（動的サイジング無効時）
if kelly_size <= min_trade_size:
    integrated_size = risk_manager_size
else:
    integrated_size = (加重平均)
```

### 修正後の期待値

| 指標 | 修正前(0.006BTC) | 修正後(0.02BTC) |
|------|------------------|----------------|
| TP距離 | 83,333円 (0.69%) | 25,000円 (0.21%) |
| SL距離 | 116,667円 (0.97%) | 35,000円 (0.29%) |
| 1トレードリスク | 700円（0.14%） | 700円（0.14%） |

---

## バックテスト結果（Phase 67.2）

（CI実行中 -- 完了後に記載）

---

## Phase 67.3: ポジションサイズ重み変更（Dynamic 100%）

**日付**: 2026年3月1日

position_integratorの重みをDynamic 100%に変更:
- kelly_weight: 0.5→0.0
- dynamic_weight: 0.3→1.0
- risk_manager_weight: 0.2→0.0

→ Kelly=0フォールバックと同等の効果を全ケースで適用。

---

## Phase 67.4: 固定ポジションサイズ + TP/SLレースコンディション修正

**日付**: 2026年3月2日

### 背景

Phase 67〜67.3でポジションサイズの動的計算を6回修正したが、ML信頼度・BTC価格・残高の
乖離により意図通りに動作しない（平均0.011 BTC、目標0.02 BTC）。

さらにライブモードで深刻な問題が発覚:
- Phase 65.2のTP/SL統合再配置でSLキャンセル→新SL配置の間にSL価格突破（レースコンディション）
- 結果: 500円TP/700円SL目標に対し、実際に2,000円超の利確/損切りが発生
- 「消失ポジション検出」が12時間以上繰り返し、新規取引もブロック

### Part A: 固定ポジションサイズテーブル導入

動的計算を廃止し、ML信頼度に応じた固定サイズに置換。

| 信頼度 | 範囲 | 固定サイズ |
|--------|------|-----------|
| low | < 50% | 0.01 BTC |
| medium | 50-65% | 0.015 BTC |
| high | >= 65% | 0.02 BTC |

**変更ファイル**:
- `config/core/thresholds.yaml`: `position_sizing` セクション追加
- `src/trading/risk/sizer.py`: `_get_fixed_position_size()` 追加、`calculate_integrated_position_size()` に固定テーブル分岐
- `src/strategies/utils/strategy_utils.py`: `_calculate_dynamic_position_size()` に固定テーブル分岐

**効果**: BTC価格・残高に依存しない安定したポジションサイズ。TP/SL距離も一定に。

### Part B: TP/SLレースコンディション修正

**問題1: SLキャンセル→再配置の間のSL不在**
- `src/trading/execution/tp_sl_manager.py`: TP→SL配置順序をSL→TPに変更
- SL価格既超過時は即成行決済（キャンセル不要）

**問題2: 消失ポジション検出の無限ループ**
- `src/trading/execution/stop_manager.py`: 1時間以上経過した消失ポジションを強制クリーンアップ

### 変更ファイル一覧

| ファイル | 変更内容 | Part |
|---------|---------|------|
| `config/core/thresholds.yaml` | 固定テーブル設定追加 | A |
| `src/trading/risk/sizer.py` | 固定テーブル参照ロジック | A |
| `src/strategies/utils/strategy_utils.py` | シグナル生成時も固定テーブル参照 | A |
| `src/trading/execution/tp_sl_manager.py` | SL→TP配置順序変更 + SL超過事前チェック | B |
| `src/trading/execution/stop_manager.py` | 消失ポジション強制クリーンアップ | B |
| テストファイル群 | 固定サイズ対応テスト更新 | Test |

---

## Phase 67.5: TP/SL損失問題の根本解決

**日付**: 2026年3月4日

### 背景

GCPログ調査（3/3〜3/4）で約3,400円の損失が発生。2つの異なる問題が原因。

#### 問題1: TP/SL未設置（filled_amount=0スキップ）

```
limit注文 → bitbank即時返却(filled_amount=0)
  → executor.py: filled_amount <= 0 → TP/SL配置スキップ
  → 5分後のサイクルでTP/SL不足検出 → Phase 65.2リカバリ
  → 間に合わない場合: SL超過 → Phase 64.12成行決済（損失拡大）
```

- 3/3 08:24 UTC: BUY 0.01 → TP/SLスキップ → -1,160円
- 3/3 09:14 UTC: BUY 0.01 → TP/SLスキップ → 成行決済
- 3/3 18:46 UTC: SELL → TP/SLスキップ → Phase 65.2でリカバリ

**原因**: `thresholds.yaml`で全注文がlimit（`high_confidence_threshold: 0.0`）→ 常に`filled_amount=0`

#### 問題2: Phase 65.2統合再配置のレースコンディション

```
Atomic Entry成功（TP+SL配置済み）
  → periodic_tp_sl_checkでカバレッジ不足判定
  → _place_missing_tp_sl() → _cancel_partial_exit_orders() で全SLキャンセル
  → Phase 67.4 SL超過チェック → awaitバグ+存在しないメソッド呼出で常に失敗
  → SL不在のまま → SL超過 → Phase 64.12成行決済
```

- 3/3 18:26 UTC: SELL Atomic Entry成功 → 18:39 SLキャンセル検出
- 3/3 20:06 UTC: BUY Atomic Entry成功 → 21:04 SLキャンセル → 21:10 成行決済

**原因**: `_place_missing_tp_sl()`がStep 0で全SLキャンセル + Phase 67.4のSL超過チェックに2つのバグ

### 修正内容（4パート）

#### Part A: limit注文の約定ポーリング

**ファイル**: `src/trading/execution/executor.py`

limit注文のSUBMITTED返却後、最大10秒（2秒×5回）fetch_orderで約定をポーリング。
約定確認できればFILLEDに更新→通常のTP/SL配置フローに進む。

#### Part B: 未約定時の次サイクル強制チェック

**ファイル**: `src/trading/execution/executor.py`

ポーリング後もfilled_amount=0の場合、`_last_tp_sl_check_time`をリセット。
次の5分サイクルでTP/SLチェックが即実行される（最悪10分→5分に短縮）。

#### Part C: Phase 67.4バグ修正

**ファイル**: `src/trading/execution/tp_sl_manager.py`

| バグ | 修正前 | 修正後 |
|------|--------|--------|
| L869 | `await bitbank_client.fetch_ticker()` | `await asyncio.to_thread(bitbank_client.fetch_ticker, symbol)` |
| L886 | `await bitbank_client.create_market_order(...)` | `await asyncio.to_thread(bitbank_client.create_order, order_type="market", ...)` |

#### Part D: Phase 65.2レースコンディション修正

**ファイル**: `src/trading/execution/tp_sl_manager.py`

`_place_missing_tp_sl()`の処理順序を変更:

```
修正前:
  Step 0: キャンセル（SL不在開始）→ 価格計算 → SL超過チェック（バグで失敗）→ SL配置

修正後:
  1. TP/SL価格計算（キャンセル前）
  2. SL超過事前チェック（既存SL有効中に実行）→ 超過なら成行決済してreturn
  3. キャンセル（SL不在期間開始）
  4. SL超過再チェック（セーフティネット）→ 超過なら成行決済してreturn
  5. SL配置 → TP配置
```

### 変更ファイル一覧

| ファイル | 変更内容 | Part |
|---------|---------|------|
| `src/trading/execution/executor.py` | 約定ポーリング追加 + 次サイクル強制チェック | A, B |
| `src/trading/execution/tp_sl_manager.py` | バグ修正 + レースコンディション修正 | C, D |
| `tests/unit/trading/execution/test_phase675.py` | 新規11テスト | Test |
| `CLAUDE.md` | しおり更新 | Doc |
