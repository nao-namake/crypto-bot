# Phase 56 開発記録

**期間**: 2025/12/25 - 2025/12/27
**状況**: Phase 56.8完了

---

## 📋 Phase 56 概要

### 目的
バックテスト取引数激減問題の解決とリスク管理の最適化

### 背景
- Phase 55.12完了後、バックテストで26件/60日しか取引が発生しない
- 戦略がHOLD 94.6%を返す
- ポジションサイズが¥200,000+で制限¥10,000を大幅超過

### Phase一覧

| Phase | 内容 | 状態 | 主要成果 |
|-------|------|------|----------|
| 56.0 | バックテスト0取引問題の調査 | ✅ | 根本原因特定（Kelly支配） |
| 56.1 | ポジションサイズ修正 | ✅ | sizer.py/kelly.py修正 |
| 56.2 | 戦略閾値軽度緩和 | ✅ | BBReversal/Stochastic調整 |
| 56.3 | リスク管理問題対応 | ✅ | リスクスコア/Kelly/ポジション制限 |
| 56.4 | tight_range重み設定最適化 | ✅ | 全6戦略に適切な重み配分 |
| 56.5 | TP/SLバグ修正 | ✅ | 既存ポジションのTP/SL自動設定 |
| 56.6 | 資金アロケーション上限 | ✅ | ポジションサイズ計算用残高を10万円に制限 |
| 56.7 | HOLD率過多問題対策 | ✅ | 2票ルール導入（BUY/SELL 2票以上でHOLD無視） |
| 56.8 | DonchianChannel戦略リファクタリング | ✅ | 直列評価方式、PF 1.00→1.14 |

---

## 🔍 Phase 56.0: バックテスト0取引問題の調査【完了】

### 実施日: 2025/12/25

### 問題
バックテストで26件/60日しか取引が発生しない

### 調査結果

#### 原因1: 戦略がHOLD 94.6%を返す
- 800サンプル中759件がHOLD
- 戦略閾値が厳しすぎる

#### 原因2: ポジションサイズ超過
- 計算されるポジションサイズ: ¥200,000+
- 制限額: ¥10,000
- 全ての取引がlimits.pyで拒否

#### 根本原因: Phase 55.5の加重平均方式
```python
# Phase 55.5の加重平均
integrated_size = kelly_size * 0.50 + dynamic_size * 0.30 + risk_size * 0.20
```
- Kellyフォールバック値が0.01 BTC（約¥150,000）
- これが加重平均を支配し、常に制限超過

---

## ⚙️ Phase 56.1: ポジションサイズ修正【完了】

### 実施日: 2025/12/25

### 修正内容

#### 1. sizer.py: 信頼度別制限の事前適用（Line 110-149）

```python
# Phase 56: 信頼度別ポジション制限を事前適用（limits.pyでの拒否を防ぐ）
if current_balance and btc_price and btc_price > 0:
    if ml_confidence < 0.60:
        confidence_ratio = get_threshold(
            "position_management.max_position_ratio_per_trade.low_confidence", 0.10
        )
        confidence_category = "low"
    elif ml_confidence < 0.75:
        confidence_ratio = get_threshold(
            "position_management.max_position_ratio_per_trade.medium_confidence", 0.15
        )
        confidence_category = "medium"
    else:
        confidence_ratio = get_threshold(
            "position_management.max_position_ratio_per_trade.high_confidence", 0.25
        )
        confidence_category = "high"

    confidence_limit = current_balance * confidence_ratio / btc_price
    if integrated_size > confidence_limit:
        integrated_size = confidence_limit
```

#### 2. kelly.py: フォールバック値修正（3箇所）

```python
# Line 294, 307, 353
# 変更前
fixed_initial_size = get_threshold("trading.initial_position_size", 0.01)

# 変更後
fixed_initial_size = get_threshold("trading.initial_position_size", 0.0005)
```

### 効果
- ポジションサイズ: ¥200,000+ → ¥5,000-10,000（制限内）
- 取引実行: 0件 → 正常動作

---

## 📊 Phase 56.2: 戦略閾値軽度緩和【完了】

### 実施日: 2025/12/25

### 修正内容（thresholds.yaml）

#### BBReversal閾値緩和
```yaml
bb_reversal:
  min_confidence: 0.25 → 0.22
  hold_confidence: 0.22 → 0.20
  bb_width_threshold: 0.028 → 0.030
  rsi_overbought: 62 → 60
  rsi_oversold: 38 → 40
  bb_upper_threshold: 0.88 → 0.85
  bb_lower_threshold: 0.12 → 0.15
  adx_range_threshold: 28 → 30
```

#### StochasticReversal閾値緩和
```yaml
stochastic_reversal:
  stoch_overbought: 75 → 72
  stoch_oversold: 25 → 28
```

---

## 📈 Phase 56 バックテスト結果（36日分/60日）

### 基本統計

| 指標 | Phase 56修正前 | Phase 56修正後 | 変化 |
|------|---------------|----------------|------|
| 取引数 | 26件/60日 | 66件/36日 | - |
| 60日換算 | 26件 | **110件予測** | **+323%** |
| 1日あたり | 0.43件 | **1.83件** | **+326%** |
| PF | 不明 | **1.12** | - |
| 勝率 | 不明 | **47.0%** | - |
| 純損益 | 不明 | **+237円** | - |

### レジーム別パフォーマンス

| レジーム | 取引数 | 勝率 | PF | 純損益 | 評価 |
|----------|--------|------|-----|--------|------|
| tight_range | 61件 | 47.5% | **1.15** | +247円 | ✅ 黒字 |
| normal_range | 5件 | 40.0% | 0.95 | -10円 | ❌ 微赤字 |
| trending | 0件 | - | - | - | 取引なし |

### TP/SL分析

| 指標 | 値 |
|------|-----|
| TP決済 | 31件（+2,137円） |
| SL決済 | 35件（-1,900円） |
| 平均TP | +68.9円/件 |
| 平均SL | -54.3円/件 |
| RR比 | 1.27:1（設定1.33:1より低い） |

### DD・クールダウン

| 指標 | 値 | 制限 | 評価 |
|------|-----|------|------|
| 最大DD | 1.44% | 20% | ✅ 余裕大 |
| 最大連敗 | 5回 | 8回 | ✅ 余裕あり |
| クールダウン発動 | 1回 | - | 正常 |

---

## ⚠️ Phase 56.3: リスク管理問題への対応【進行中】

### 発見された問題

#### 問題1: リスクスコアによる取引拒否（2,196件）
- 平均リスクスコア: 27.9%
- 拒否閾値: 25%（推定）
- 影響: 戦略シグナルが出ても大量拒否

#### 問題2: Kelly基準エラー（968件）
```
Kelly計算済みポジションサイズ制限超過: 計算値=0.0349 > max_order_size=0.0300
```
- 残高増加時にKellyが大きなサイズを計算
- ログが汚染されている

#### 問題3: ポジション制限超過（98件）
```
1取引あたりの最大金額制限(low信頼度)を超過。制限: ¥9,916, 要求: ¥10,000
```
- 境界値でわずかに超過

#### 問題4: クールダウン時刻問題【修正済み】
- `limits.py._check_cooldown`で`datetime.now()`を使用
- バックテスト時にシミュレーション時刻が考慮されていなかった
- 15分クールダウンがバックテストで正しく機能しない

### 対応計画・実施状況

| 問題 | 対応 | 修正ファイル | 状態 |
|------|------|-------------|------|
| リスクスコア拒否 | 閾値確認（deny:85%/conditional:65%） | thresholds.yaml | ✅ 現設定妥当 |
| Kelly基準エラー | ログレベルERROR→DEBUG | kelly.py | ✅ |
| ポジション制限超過 | 0.5%マージン追加 | sizer.py | ✅ |
| クールダウン時刻 | current_time対応 | limits.py / executor.py / backtest_runner.py | ✅ |

### 問題4修正内容（Phase 56.3）

#### limits.py: `_check_cooldown`にcurrent_time対応
```python
async def _check_cooldown(
    self, evaluation, last_order_time, current_time=None
):
    # Phase 56.3: バックテスト時はcurrent_time使用
    now = current_time if current_time is not None else datetime.now()
    time_since_last_order = now - last_order_time
```

#### executor.py: バックテスト時刻管理
```python
# Phase 56.3: バックテスト時刻管理
self.current_time: Optional[datetime] = None

# バックテスト実行時
trade_timestamp = self.current_time if self.current_time else datetime.now()
self.last_order_time = trade_timestamp
```

#### backtest_runner.py: シミュレーション時刻設定
```python
# Phase 56.3: ExecutionServiceにシミュレーション時刻を設定
self.orchestrator.execution_service.current_time = self.current_timestamp
```

### 問題2修正内容（Phase 56.3）

#### kelly.py: ログレベルERROR→DEBUG
```python
# 変更前
self.logger.error(
    f"Kelly計算済みポジションサイズ制限超過: ..."
)

# 変更後（Phase 56.3）
self.logger.debug(
    f"Kelly計算済みポジションサイズ制限適用: ... → 制限値使用"
)
```
- 正常動作（制限適用）のためエラーレベルではなくデバッグレベルに変更

### 問題3修正内容（Phase 56.3）

#### sizer.py: 0.5%マージン追加
```python
# Phase 56.3: 0.5%マージン追加（limits.pyでの境界値超過を防ぐ）
margin_factor = 0.995  # 0.5%マージン
confidence_limit = current_balance * confidence_ratio * margin_factor / btc_price
```
- 境界値での微小超過（¥9,916 vs ¥10,000問題）を解消

---

## 🎯 Phase 56.4: tight_range重み設定最適化【完了】

### 実施日: 2025/12/26

### 問題
- CIバックテストで45取引/180日（目標: 400-500取引/180日）
- tight_rangeで3戦略（ADX, MACD, Donchian）がweight=0で完全無視
- 462件/60日のシグナルが統合結果に反映されていない

### 網羅的調査結果

#### 1. MLモデル検証 ✅ 正常
```
予測分布（300サンプル）:
- SELL: 54.7%, HOLD: 36.7%, BUY: 8.7%
- BUY/SELL合計: 63.3%（正常）
```

#### 2. 個別戦略検証 ✅ 正常
| 戦略 | 取引数/60日 | PF |
|------|-------------|-----|
| ADXTrendStrength | 120 | 1.05 |
| StochasticReversal | 181 | 1.06 |
| ATRBased | 126 | 1.11 |
| DonchianChannel | 294 | 1.00 |
| MACDEMACrossover | 48 | 1.20 |
| BBReversal | 123 | 0.99 |
| **合計** | **892** | - |

#### 3. ML統合検証 ✅ 重み0の影響なし
- `strategy_signal_*`特徴量は全6戦略から生成
- 重みは統合時のみ適用、ML入力には影響しない

#### 4. 根本原因特定 ❌ 戦略統合層
```python
# strategy_manager.py _calculate_weighted_confidence()
weight = self.strategy_weights.get(strategy_name, 1.0)
weighted_confidence = signal.confidence * weight  # weight=0 → 貢献度0!
```

### 戦略特性分析

| 戦略 | Phase | 変更内容 | 現在の区分 |
|------|-------|----------|-----------|
| **ADXTrendStrength** | 55.6 | トレンド→**レンジ逆張り**に変換 | **レンジ型** |
| StochasticReversal | 55.2 | Divergence検出強化 | レンジ型 |
| ATRBased | 54 | ATR消尽率ロジック導入 | レンジ型 |
| BBReversal | - | BB端+RSI極端値 | レンジ型 |
| DonchianChannel | - | チャネル端反転 | レンジ型 |
| MACDEMACrossover | - | MACDクロス（ADX>25条件） | **トレンド型** |

**重要**: ADXTrendStrengthはPhase 55.6でレンジ型に変換済み → weight復活が適切

### 修正内容（thresholds.yaml）

```yaml
# 修正前（3戦略がweight=0で無視）
tight_range:
  BBReversal: 0.40
  StochasticReversal: 0.35
  ATRBased: 0.25
  ADXTrendStrength: 0.0      # ← 完全無視
  MACDEMACrossover: 0.0      # ← 完全無視
  DonchianChannel: 0.0       # ← 完全無視

# 修正後（全戦略に適切な重み配分）
tight_range:
  BBReversal: 0.25           # PF 1.32（最高PF）
  StochasticReversal: 0.25   # PF 1.25（Divergence特化）
  ATRBased: 0.20             # PF 1.16（消尽率ロジック）
  ADXTrendStrength: 0.15     # PF 1.05（Phase 55.6でレンジ型に変換済み）
  DonchianChannel: 0.10      # PF 1.00（損益分岐）
  MACDEMACrossover: 0.05     # PF 1.50（トレンド型・最小限）
```

### 重み設計方針
- PFが高い戦略に高重み（BBReversal, Stochastic）
- レンジ型に変換されたADXにも適切な重み復活
- トレンド型MACDは最小限（tight_rangeではADX>25条件で自然に不発）
- 合計 = 1.0

### 期待効果
- 取引数: 45件/180日 → 400-500件/180日（目標）
- 無視されていた462件/60日のシグナルが部分的に反映

### 修正ファイル
| ファイル | 修正内容 |
|---------|---------|
| `config/core/thresholds.yaml` | tight_range重み設定更新（Line 297-304） |
| `tests/unit/services/test_dynamic_strategy_selector.py` | テスト期待値更新 |

---

## 🔧 Phase 56.5: TP/SLバグ修正【完了】

### 実施日: 2025/12/27

### 問題

ライブモードで既存ポジション（約0.0024 BTC）にTP/SL注文が設定されていない。

#### 証拠（ログ分析）
```
📊 Phase 50.4: 現在ポジション=33034円 ← ポジションあり
📊 Phase 53.6: アクティブ注文なし、復元スキップ ← TP/SL注文なし
アクティブ注文取得成功: 0件 ← 本当にTP/SL注文がない
```

### 原因分析

1. **過去に作成されたポジション**にTP/SL注文が設定されなかった
2. **Phase 53.6のポジション復元**は「アクティブ注文」ベース
3. TP/SL注文がない場合 → 復元スキップ → ポジション放置

### 調査結果（BUY/SELL同率時のHOLD変換について）

計画段階で「BUY/SELL同率時に信頼度で決定」案を検討したが、**導入すべきではない**と判断。

#### 実際のログ分析
```
コンフリクト解決: HOLD選択 (BUY=0.000, SELL=0.458, HOLD=0.542)
```

| 戦略 | シグナル | 信頼度 |
|------|---------|--------|
| ATRBased | hold | 0.500 |
| DonchianChannel | hold | 0.447 |
| ADXTrendStrength | hold | 0.464 |
| BBReversal | sell | 0.212 |
| StochasticReversal | sell | 0.556 |
| MACDEMACrossover | hold | 0.250 |

**分析結果**:
- **BUY/SELL完全同率ケースはほぼ存在しない**
- HOLDになる理由は「HOLD票が多い」（6戦略中4戦略がHOLD）
- これは市場信号が不明確な時の**適切な保守的判断**

### 修正内容

#### 1. executor.py: 3メソッド追加

```python
async def ensure_tp_sl_for_existing_positions(self):
    """
    Phase 56.5: 既存ポジションのTP/SL確保
    起動時にTP/SL注文がないポジションを検出し、自動配置する。
    """
    # Step 1: 信用建玉情報取得（/user/margin/positions）
    margin_positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")

    # Step 2: アクティブ注文取得（TP/SL存在確認用）
    active_orders = await asyncio.to_thread(...)

    # Step 3: 各ポジションのTP/SL存在確認
    for position in margin_positions:
        has_tp, has_sl = self._check_tp_sl_orders_exist(...)
        if not has_tp or not has_sl:
            await self._place_missing_tp_sl(...)

def _check_tp_sl_orders_exist(...) -> Tuple[bool, bool]:
    """既存注文からTP/SL注文の存在確認"""

async def _place_missing_tp_sl(...):
    """不足しているTP/SL注文を配置"""
```

#### 2. live_trading_runner.py: 起動時呼び出し追加

```python
# Phase 53.6: 起動時にポジションを復元
await self.orchestrator.execution_service.restore_positions_from_api()

# Phase 56.5: 既存ポジションのTP/SL確保（新規追加）
await self.orchestrator.execution_service.ensure_tp_sl_for_existing_positions()
```

### 処理フロー

```
システム起動
    ↓
Phase 53.6: restore_positions_from_api()
    ↓ アクティブ注文からポジション復元
Phase 56.5: ensure_tp_sl_for_existing_positions() ← 新規追加
    ↓ 信用建玉API取得（/user/margin/positions）
    ↓ アクティブ注文とマッチング
    ↓ TP/SLがないポジションにTP/SL配置
取引サイクル開始
```

### 修正ファイル

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/execution/executor.py` | 3メソッド新規追加（174-371行） |
| `src/core/execution/live_trading_runner.py` | 起動時呼び出し追加（120-122行） |

### 期待効果

- 全ポジションにTP/SL設定済み
- 起動時にTP/SLなしポジションを自動検出・設定
- リスク管理の正常化

---

## 💰 Phase 56.6: 資金アロケーション上限機能【完了】

### 実施日: 2025/12/27

### 背景

ライブモードでは実際の残高（33万円）がポジションサイズ計算に使用されていた。
設定値`mode_balances.live.initial_balance: 10000.0`はAPIエラー時のフォールバックのみで、
実運用時は実残高ベースで計算されていた。

#### 調査結果：意図した設計動作だが、制限機能を追加

**残高取得フロー（修正前）**:
```
[ライブモード起動]
    ↓
trading_cycle_manager.py:_fetch_trading_info()
    ↓
balance_info = data_service.client.fetch_balance()  ← bitbank APIから取得
current_balance = balance_info["JPY"]["total"]       ← 実際の残高（33万円）
    ↓
risk/sizer.py:_calculate_dynamic_position_size()
    ↓
calculated_size = (current_balance * position_ratio) / btc_price
```

### 修正内容

#### 1. thresholds.yaml: 新設定追加

```yaml
trading:
  # Phase 56.6: 資金アロケーション上限（ポジションサイズ計算に使用する残高上限）
  # null/0で無制限（実残高をそのまま使用）、正の値で上限設定
  capital_allocation_limit: 100000.0  # 10万円に制限
```

#### 2. trading_cycle_manager.py: 上限適用ロジック追加

```python
async def _fetch_trading_info(self, market_data):
    # 現在の残高取得
    balance_info = self.orchestrator.data_service.client.fetch_balance()
    actual_balance = balance_info.get("JPY", {}).get("total", 0.0)

    # Phase 56.6: 資金アロケーション上限を適用
    capital_limit = get_threshold("trading.capital_allocation_limit", None)
    if capital_limit and capital_limit > 0:
        current_balance = min(actual_balance, capital_limit)
        if actual_balance > capital_limit:
            self.logger.debug(
                f"Phase 56.6: 資金アロケーション上限適用 - "
                f"実残高: ¥{actual_balance:,.0f} → 計算用: ¥{current_balance:,.0f}"
            )
    else:
        current_balance = actual_balance
```

### 動作

```
実残高: 33万円
    ↓
資金アロケーション上限適用: min(330000, 100000) = 100000
    ↓
ポジションサイズ計算: 10万円ベース
    ↓
結果: ~0.01 BTC相当まで（以前の1/3程度に縮小）
```

### ポジションサイズ計算の影響

| 信頼度 | 比率範囲 | 33万円での計算 | 10万円での計算（修正後） |
|--------|---------|---------------|----------------------|
| 低（<60%） | 1-3% | 0.00036-0.00108 BTC | 0.00011-0.00032 BTC |
| 中（60-75%） | 3-5% | 0.00108-0.00180 BTC | 0.00032-0.00054 BTC |
| 高（>75%） | 5-10% | 0.00180-0.00360 BTC | 0.00054-0.00108 BTC |

### 修正ファイル

| ファイル | 修正内容 |
|---------|---------|
| `config/core/thresholds.yaml` | `trading.capital_allocation_limit: 100000.0` 追加 |
| `src/core/services/trading_cycle_manager.py` | 残高取得時に上限適用ロジック追加（2箇所） |

### 設定変更方法

上限を変更したい場合は `config/core/thresholds.yaml` の値を編集:
```yaml
capital_allocation_limit: 50000.0   # 5万円に変更
capital_allocation_limit: null      # 無制限（実残高使用）
capital_allocation_limit: 0         # 無制限（実残高使用）
```

---

## 🎯 Phase 56.7: HOLD率過多問題対策【進行中】

### 実施日: 2025/12/27

### 問題

バックテストでHOLD率が高すぎて取引数が少ない。

| 指標 | 現状 | 目標 |
|------|------|------|
| 取引数/60日 | 54件 | 100-200件 |
| 月間取引 | 9回/月 | 17-33回/月 |

### 調査結果

#### 1. 戦略単体検証 ✅ 問題なし

| 戦略 | 60日シグナル数 | PF |
|------|---------------|-----|
| ATRBased | 126件 | 1.11 |
| DonchianChannel | 294件 | 1.00 |
| ADXTrendStrength | 120件 | 1.05 |
| BBReversal | 123件 | 0.99 |
| StochasticReversal | 181件 | 1.06 |
| MACDEMACrossover | 48件 | 1.20 |
| **合計** | **892件** | - |

#### 2. ML予測分布 ✅ 問題なし

```
BUY: 8.7%, HOLD: 36.7%, SELL: 54.7%
→ BUY+SELL = 63.4%（正常）
```

#### 3. 根本原因 ❌ 戦略統合ロジック

**各戦略が97%の時間HOLDを出している**

| 計算 | 値 |
|------|-----|
| データポイント | 5,760件（60日×96本/日） |
| 戦略シグナル合計 | 892件 |
| 1戦略平均 | 149件/60日 |
| **非HOLD率** | **2.6%/戦略** |

#### 4. 統合時の問題

```
例:
ATRBased: hold (0.500)         ← 重み 0.20
DonchianChannel: hold (0.447)  ← 重み 0.10
ADXTrendStrength: hold (0.464) ← 重み 0.15
BBReversal: sell (0.212)       ← 重み 0.25
StochasticReversal: sell (0.556) ← 重み 0.25
MACDEMACrossover: hold (0.250) ← 重み 0.05

HOLD重み付け信頼度: 0.5×0.20 + 0.447×0.10 + 0.464×0.15 + 0.25×0.05 = 0.227
SELL重み付け信頼度: 0.212×0.25 + 0.556×0.25 = 0.192

→ HOLD > SELL → HOLDが選択される
```

**問題**: 少数のBUY/SELL票が、多数のHOLD票に負ける

### バックテスト vs ライブモード検証

| 項目 | バックテスト | ライブモード | 影響 |
|------|------------|-------------|------|
| ポジションサイズ | 固定値 | Kelly動的 | バックテスト有利 |
| 手数料 | -0.02%固定 | 変動 | バックテスト有利 |
| スリッページ | なし | あり | バックテスト有利 |
| TP/SL約定 | high/low使用 | close価格 | バックテスト有利 |
| **戦略統合** | ✅ 同じ | ✅ 同じ | **一致** |
| **ML予測** | ✅ 同じ | ✅ 同じ | **一致** |
| **クールダウン** | ✅ 同じ | ✅ 同じ | **一致** |

**結論**: 取引判断ロジックは一致。バックテストで相対比較が有効。

### 修正内容: 2票ルール導入

#### strategy_manager.py: `_resolve_signal_conflict`修正

```python
def _resolve_signal_conflict(self, signal_groups, all_signals, df) -> StrategySignal:
    buy_signals = signal_groups.get("buy", [])
    sell_signals = signal_groups.get("sell", [])
    hold_signals = signal_groups.get("hold", [])

    buy_count = len(buy_signals)
    sell_count = len(sell_signals)

    # Phase 56.7: 2票以上ルール（コンセンサス重視）
    buy_has_quorum = buy_count >= 2
    sell_has_quorum = sell_count >= 2

    # 両方2票以上 → 矛盾 → HOLD
    if buy_has_quorum and sell_has_quorum:
        return self._create_hold_signal(df, reason="Phase 56.7: BUY/SELL両方2票以上で矛盾")

    # BUY 2票以上 → BUY選択（HOLD無視）
    if buy_has_quorum:
        buy_weighted_confidence = self._calculate_weighted_confidence(buy_signals)
        best_signal = max(buy_signals, key=lambda x: x[1].confidence)[1]
        return StrategySignal(action="buy", confidence=buy_weighted_confidence, ...)

    # SELL 2票以上 → SELL選択（HOLD無視）
    if sell_has_quorum:
        sell_weighted_confidence = self._calculate_weighted_confidence(sell_signals)
        best_signal = max(sell_signals, key=lambda x: x[1].confidence)[1]
        return StrategySignal(action="sell", confidence=sell_weighted_confidence, ...)

    # BUY/SELL両方1票以下 → 従来ロジック（重み付け比較）
    # ...
```

### 設計思想

1. **コンセンサス重視**: 2戦略以上の合意でHOLD無視
2. **矛盾検出**: BUY 2票以上かつSELL 2票以上 → HOLD
3. **重み活用継続**: 2票以上ルール適用時も重み付け信頼度を計算
4. **保守的フォールバック**: 1票以下なら従来ロジック

### 修正ファイル

| ファイル | 修正内容 |
|---------|---------|
| `src/strategies/base/strategy_manager.py` | 2票ルール追加（`_resolve_signal_conflict`） |
| `config/core/thresholds.yaml` | バックテスト期間180日に変更 |
| `tests/unit/strategies/test_strategy_manager.py` | テスト期待値更新 |

### 期待効果

| 指標 | 変更前 | 期待値 |
|------|--------|--------|
| 取引数/180日 | 162件予測 | 300-600件 |
| HOLD率 | ~90% | ~70-80% |
| PF | 1.64 | 維持（重み付けで品質維持） |

### 検証状況

- GitHub Actionsで180日間バックテスト実行中
- Run ID: `20530881012`
- 結果待ち

---

## 🔧 Phase 56.8: DonchianChannel戦略リファクタリング【完了】

### 実施日: 2025/12/27

### 目的

DonchianChannel戦略をタイトレンジ向け平均回帰戦略にリファクタリング
- 現状: PF 0.85（赤字）、HOLD率高、コード550行
- 目標: PF ≥ 1.0、取引数維持、コード簡素化

### 問題分析

| 問題 | 箇所 | 影響 |
|------|------|------|
| 5段階判定が複雑 | 行234-324 | 信頼度が分散、判定曖昧 |
| 中央域広すぎ | 0.4-0.6（20%） | HOLD率30-40% |
| 出来高フィルタ無効 | volume > 1.2 | ブレイクアウト発生0件 |
| reversal_threshold未使用 | 設定0.04がコード未反映 | 技術負債 |

### 設計変更

**変更前（5段階判定）:**
```
ブレイクアウト → リバーサル → 弱シグナル → 中央域 → デフォルト
```

**変更後（直列評価方式）:**
```
ADXフィルタ（< 28）→ 極端位置（< 0.12 or > 0.88）→ RSIフィルタ → シグナル
```

### 採用設定（thresholds.yaml）

```yaml
donchian_channel:
  # 直列評価パラメータ
  adx_max_threshold: 28           # レンジ判定
  extreme_zone_threshold: 0.12    # 極端位置
  rsi_oversold: 42                # 買いRSI上限
  rsi_overbought: 58              # 売りRSI下限

  # 信頼度設定
  base_confidence: 0.40
  max_confidence: 0.60
  min_confidence: 0.30
  hold_confidence: 0.25

  # 信頼度ボーナス
  extreme_position_bonus: 0.10
  rsi_confirmation_bonus: 0.05
```

### バックテスト結果

| 期間 | 取引数 | 勝率 | PF | 損益 |
|------|--------|------|-----|------|
| 60日 | 107件 | 46.7% | **1.12** | +9,866円 |
| 180日 | 254件 | 46.9% | **1.14** | +27,999円 |

**改善効果（60日比較）:**
| 指標 | 旧 | 新 | 変化 |
|------|-----|-----|------|
| 取引数 | 294件 | 107件 | -64%（品質重視） |
| 勝率 | 43.9% | **46.7%** | **+2.8pt** |
| PF | 1.00 | **1.12** | **+12%** |
| 損益 | -171円 | **+9,866円** | **黒字化** |

### 修正ファイル

| ファイル | 修正内容 |
|---------|---------|
| `src/strategies/implementations/donchian_channel.py` | 直列評価方式に全面リファクタリング（550行→310行） |
| `config/core/thresholds.yaml` | 新パラメータ追加 |
| `tests/unit/strategies/implementations/test_donchian_channel.py` | テスト更新（24テスト全パス） |
| `config/core/donchian_backup_phase56.yaml` | バックアップ作成 |

### 学習事項

1. **直列評価の有効性**: 複雑な5段階判定より、シンプルな直列評価が保守性・性能両方で優れる
2. **RSIフィルタの重要性**: 方向確認で偽シグナル削減、PF向上に貢献
3. **取引数vs品質**: 取引数が減っても、勝率・PFが上がれば収益改善
4. **短期・長期両方で検証**: 60日と180日両方で成果を確認することで信頼性向上

---

## 📝 学習事項

1. **Kellyフォールバック値の重要性**: 0.01 BTCは¥150,000相当で、小額運用には大きすぎる
2. **加重平均方式の落とし穴**: 一つの要素が極端だと全体を支配する
3. **リスク管理のバランス**: 過度な制限は取引機会の損失につながる
4. **tight_range特化の有効性**: このレジームでPF 1.15を達成
5. **weight=0の危険性**: 戦略統合で完全無視され、取引機会を大幅に失う
6. **戦略進化の追跡**: ADXがPhase 55.6でレンジ型に変換されたことを重み設定に反映し忘れていた
7. **網羅的調査の重要性**: ML・戦略・統合層を個別検証することで根本原因を特定
8. **ポジション復元の限界**: Phase 53.6の「アクティブ注文ベース」復元では、TP/SLなしポジションを検出できない
9. **BUY/SELL同率問題の誤認**: 実際はHOLD票が多いだけで、同率問題ではなかった（調査重要）
10. **信用建玉API活用**: `/user/margin/positions`で直接ポジション情報を取得することで確実な状態把握
11. **設定値の用途明確化**: `initial_balance`はフォールバック用で、実運用は別の制限機構が必要
12. **資金アロケーション分離**: 実残高とポジションサイズ計算用残高を分離することでリスク管理を柔軟化
13. **HOLD投票の支配問題**: 各戦略が97%の時間HOLDを出すため、重み付け多数決ではHOLDが常勝
14. **2票ルールの導入**: コンセンサス（2戦略以上の合意）でHOLD無視、矛盾時はHOLD
15. **バックテストと実運用の差異**: 取引判断ロジックは一致、損益は楽観的（相対比較は有効）
16. **直列評価の有効性**: 複雑な5段階判定より、シンプルな直列評価が保守性・性能両方で優れる
17. **RSIフィルタの重要性**: 方向確認で偽シグナル削減、PF向上に貢献
18. **取引数vs品質トレードオフ**: 取引数が減っても、勝率・PFが上がれば収益改善

---

**📅 最終更新**: 2025年12月27日 - Phase 56.8完了（DonchianChannel戦略リファクタリング）
