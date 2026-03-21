# Phase 70: 期待値改善（日次損失上限・RR比改善・シグナル一貫性・ML閾値引き上げ）

**期間**: 2026年3月21日
**状態**: ✅ 完了

| 変更 | 内容 | 状態 |
|------|------|------|
| **A1** | 日次/週次損失上限の実装（DrawdownManager + IntegratedRiskManager） | ✅ 完了 |
| **A2** | TP/SL RR比改善（TP 750円 / SL 500円 = RR 1.5:1） | ✅ 完了 |
| **A3** | シグナル一貫性チェック（2回連続同方向でエントリー許可） | ✅ 完了 |
| **A4** | ML信頼度閾値引き上げ（tight_range 0.40, normal 0.38, trending 0.40） | ✅ 完了 |

---

## 背景

72時間実績: -5,805円、勝率37.5%。
**根本問題**: 勝率37.5% × RR比1:1 = 期待値マイナス（-125円/取引）。

---

## A1: 日次/週次損失上限の実装

### 問題
`thresholds.yaml`に`daily_loss_limit: 0.05`と`weekly_loss_limit: 0.1`が定義されているが、リスク管理コードに組み込まれていない。

### 変更内容

**`src/trading/risk/drawdown.py`**:
- `get_daily_pnl()` / `get_weekly_pnl()`: 日次/週次PnL計算
- `check_daily_loss_limit()`: 初期残高×制限比率で損失上限チェック
- `get_position_size_multiplier()`: 連敗段階的サイズ縮小
  - 5回: 50%, 6回: 40%, 7回: 25%, 8回以上: 0%

**`src/trading/risk/manager.py`**:
- `evaluate_trade_opportunity()`に日次損失チェック追加（ステップ1.5）
- 連敗時ポジションサイズ縮小（ステップ6の後）

### 期待効果
- 大損日を自動停止で防ぎ、月間DD抑制
- 連敗5回でサイズ半減→損失拡大を段階的に制御

---

## A2: TP/SL RR比改善

### 問題
TP 500円 / SL 500円 = RR比1:1 → 勝率37.5%では期待値 = -125円/取引。

### 変更内容

**`config/core/thresholds.yaml`**:
- `take_profit.fixed_amount.target_net_profit`: 500 → 750
- `take_profit.fixed_amount.confidence_based.low`: 400 → 600
- `take_profit.fixed_amount.confidence_based.high`: 500 → 750
- `take_profit.regime_based.*.fixed_amount_target`: 500 → 750（全レジーム）
- SL設定は変更なし（500円維持）

### 数値
- RR比: 750/500 = **1.5:1**
- 損益分岐勝率: 500/(750+500) = **40%**
- 勝率37.5%での期待値: 0.375×750 - 0.625×500 = **-31円/取引**（改善前-125円から75%改善）
- 勝率40%で期待値: 0.4×750 - 0.6×500 = **0円**（損益分岐）
- 勝率45%で期待値: 0.45×750 - 0.55×500 = **+62.5円/取引**（黒字化）

---

## A3: シグナル一貫性チェック

### 問題
5分間隔で毎回独立にシグナル生成→即実行。前回と矛盾するシグナルでもエントリーする。

### 変更内容

**`src/core/services/trading_cycle_manager.py`**:
- `_signal_history`: 過去5回のシグナル方向バッファ
- `_apply_signal_consistency_check()`: 直近2回連続同方向でのみエントリー許可
- リスク評価後、取引実行前に挿入

### 期待効果
- ノイズシグナル40-50%削減
- 勝率+3-5%

---

## A4: ML信頼度閾値引き上げ

### 問題
`min_ml_confidence: 0.33`（tight_range）→ 信頼度33%=ほぼランダムでもエントリー。

### 変更内容

**`config/core/thresholds.yaml`**（`ml.regime_ml_integration`セクション）:
- `tight_range.min_ml_confidence`: 0.33 → **0.40**
- `normal_range.min_ml_confidence`: 0.30 → **0.38**
- `trending.min_ml_confidence`: 0.35 → **0.40**

### 期待効果
- 低品質エントリー削減
- 勝率+2-3%（取引回数は5-10%減少）
