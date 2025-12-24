# Phase 56 開発記録

**期間**: 2025/12/25
**状況**: Phase 56進行中

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
| 56.3 | リスク管理問題対応 | 🔄 | リスクスコア/Kelly/ポジション制限 |

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

## 📝 学習事項

1. **Kellyフォールバック値の重要性**: 0.01 BTCは¥150,000相当で、小額運用には大きすぎる
2. **加重平均方式の落とし穴**: 一つの要素が極端だと全体を支配する
3. **リスク管理のバランス**: 過度な制限は取引機会の損失につながる
4. **tight_range特化の有効性**: このレジームでPF 1.15を達成

---

**📅 最終更新**: 2025年12月25日
