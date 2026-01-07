# Phase 57 開発記録

**期間**: 2025/12/29 - 2026/01/07
**状況**: ✅ Phase 57完了

---

## 📋 Phase 57 概要

### 目的

年利10%達成に向けたリスク設定の最適化とポジションサイズの拡大

### 背景

- Phase 56完了後、PF 1.17達成だがDD 0.79%と過度に保守的
- 50万円証拠金で年間¥7,000程度では開発コスト対効果に見合わない
- 年利10%（年間¥50,000）を目標に設定

### Phase一覧

| Phase | 内容 | 状態 | 主要成果 |
|-------|------|------|----------|
| 57.0 | 年利10%計画策定 | ✅ | リスク設定調査・計画作成 |
| 57.1 | レバレッジ・Kelly・ポジション緩和 | ✅ | 4倍→2倍修正、各種制限緩和 |
| 57.2 | DD 5%攻撃的設定 | ✅ | 信頼度閾値50%、ポジション2倍 |
| 57.3 | ライブモード診断・修正 | ✅ | リスクスコア正規化バグ修正 |
| 57.4 | API遅延対策 | ✅ | API閾値緩和（3秒→10秒） |
| 57.5 | DD 10%許容・年利5%目標 | ✅ | ポジション10倍拡大 |
| 57.6 | リスク最大化・年利10%目標 | ✅ | ボトルネック解消・Kelly重視 |
| 57.7 | 設定ファイル体系整理・レポート計算修正 | ✅ | unified.yaml統合・レポートバグ修正 |
| 57.10 | バックテストDDタイムスタンプバグ修正 | ✅ | IntegratedRiskManagerのDD時刻処理修正 |
| 57.11 | ローカルバックテスト機能強化 | ✅ | CSV収集・日数指定・日毎損益分析 |
| 57.12 | バックテストデータ拡充・分析レポート強化 | ✅ | 個別戦略名記録・ML予測記録 |
| 57.13 | 固定期間バックテスト・標準分析スクリプト | ✅ | 固定期間・84項目分析・CI/ローカル連携 |
| 57.14 | ライブモード標準分析スクリプト | ✅ | 35固定指標・bitbank API/GCPログ連携 |

---

## 🔍 Phase 57.0: 年利10%計画策定【完了】

### 実施日: 2025/12/29

### 調査結果

| 指標 | 値 | 評価 |
|------|-----|------|
| 証拠金 | ¥100,000（設定） | 少額 |
| 年利 | 1.4% | 非常に低い |
| DD | 0.79% | 過度に保守的 |
| max_drawdown設定 | 20% | 余裕大 |

### 発見した制約

1. **レバレッジ計算バグ**: コードで4倍計算、bitbankは2倍まで
2. **Kelly基準が厳しい**: max_position_ratio 10%、safety_factor 0.7
3. **ポジションサイズ制限**: 多層制限で極小化

### 計画

- 証拠金: 10万円 → 50万円
- 年利目標: 10%（年間¥50,000）
- 想定DD: 2-5%

---

## ⚙️ Phase 57.1: レバレッジ・Kelly・ポジション緩和【完了】

### 実施日: 2025/12/29

### 修正内容

#### 1. レバレッジ計算バグ修正

| ファイル | 変更 |
|---------|------|
| `src/trading/execution/executor.py:956-958` | `/ 4` → `/ 2` |
| `src/core/execution/backtest_runner.py:831, 992` | `/ 4` → `/ 2` |

#### 2. Kelly基準緩和（thresholds.yaml）

```yaml
kelly_criterion:
  max_position_ratio: 0.25    # 10% → 25%
  safety_factor: 0.8          # 0.7 → 0.8
initial_position_size: 0.002   # 0.0005 → 0.002
```

#### 3. ポジションサイズ制限緩和

```yaml
max_position_ratio_per_trade:
  low_confidence: 0.15    # 10% → 15%
  medium_confidence: 0.25  # 15% → 25%
  high_confidence: 0.40    # 25% → 40%
max_capital_usage: 0.5     # 0.3 → 0.5
```

#### 4. 証拠金設定更新（unified.yaml）

```yaml
mode_balances:
  paper/live/backtest:
    initial_balance: 500000.0  # 10万 → 50万
```

### 発見された問題

ATR戦略のコードデフォルト値がPhase 56.10の実験設定のまま残っていた。
- `bb_as_main_condition: True` → `False`に修正

### バックテスト結果（12/29）

| 指標 | Phase 56 | Phase 57.1 | 変化 |
|------|----------|------------|------|
| 取引数/180日 | 70件 | 90件 | +29% |
| 勝率 | 51.4% | 45.6% | -5.8pt |
| PF | 1.35 | 1.17 | -0.18 |
| 総損益 | ¥+706 | ¥+754 | +7% |
| 最大DD | 0.4% | 0.79% | +0.39pt |
| 平均勝ち | ¥+75 | ¥+124 | +65% |
| 平均負け | ¥-75 | ¥-88 | +17% |

**分析**:
- ポジションサイズは増加（平均勝ち+65%）
- 勝率が低下（ATR戦略のコード設定問題）
- DD 0.79%は目標5%に遠い

---

## 🚀 Phase 57.2: DD 5%攻撃的設定【完了】

### 実施日: 2025/12/30

### 目的

DD 5%まで許容してポジションサイズを大幅拡大

### MLモデルの実態

| 指標 | 値 | 問題点 |
|------|-----|--------|
| 平均信頼度 | 51.8% | 60%閾値を下回る |
| 高信頼度(>60%) | 23% | 77%が低信頼度扱い |
| モデル精度 | 41% | ランダム33%よりわずかに良い程度 |

### 修正内容

#### 1. 信頼度閾値変更（60%→50%）

| ファイル | 箇所 |
|---------|------|
| `src/trading/risk/sizer.py` | 116, 223, 252行 |
| `src/trading/risk/manager.py` | 781行 |
| `src/trading/position/limits.py` | 340行 |

#### 2. ポジションサイズ制限のさらなる緩和

```yaml
max_position_ratio_per_trade:
  low_confidence: 0.25     # 0.15 → 0.25
  medium_confidence: 0.35   # 0.25 → 0.35
  high_confidence: 0.50     # 0.40 → 0.50
```

#### 3. Kelly基準のさらなる緩和

```yaml
kelly_criterion:
  max_position_ratio: 0.35    # 0.25 → 0.35
  safety_factor: 0.9          # 0.8 → 0.9
initial_position_size: 0.005   # 0.002 → 0.005
```

#### 4. max_order_size制限の緩和

```yaml
production:
  max_order_size: 0.05        # 0.03 → 0.05
```

### DD 5%達成の計算

| 項目 | 現状 | 変更後（6倍） | 目標 |
|------|------|--------------|------|
| 平均損失 | ¥88 | ¥528 | - |
| 最大DD | 0.79% | ~4.7% | 5% |
| 年利 | 1.5% | ~9% | 10% |

### 期待効果

| 指標 | Phase 57.1 | Phase 57.2予測 | 目標 |
|------|------------|----------------|------|
| DD | 0.79% | ~5% | 5% |
| 平均勝ち | ¥124 | ~¥620 | - |
| 平均負け | ¥88 | ~¥440 | - |
| 年利 | 1.5% | ~9% | 10% |

---

## 🔧 Phase 57.3: ライブモード診断・修正【完了】

### 実施日: 2025/12/30

### 問題

Phase 56.8デプロイ後、ライブモードで取引が発生しない。全ての取引が`リスクスコア=100.0%`で拒否。

### 根本原因

リスクスコア計算のバグ: `drawdown_risk`と`consecutive_risk`が1.0でキャップされていなかった

```python
# 修正前
drawdown_risk = drawdown_ratio / 0.20          # キャップなし

# 修正後（Phase 57.3）
drawdown_risk = min(1.0, drawdown_ratio / 0.20)
consecutive_risk = min(1.0, consecutive_losses / 5.0)
```

### 修正ファイル

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/risk/manager.py` | リスクコンポーネントのmin(1.0, ...)正規化追加 |
| `src/core/services/trading_logger.py` | RiskDecision Enum対応（.value使用） |

### 追加診断ログ

高リスクスコア（≥85%）時に詳細ログを出力するよう追加:
```
🔍 リスクスコア詳細: total=0.850, ml_risk=0.607×0.3=0.182,
anomaly=0.500×0.25=0.125, drawdown=0.000×0.25=0.000,
consecutive=0.000×0.1=0.000, volatility=0.400×0.1=0.040
```

### 期待効果

- リスクスコアが適切な範囲（0-100%）に正規化
- denial_reasonsが空でも正確なリスクスコアを計算
- ログで判定結果が正しく表示される

---

## ⚡ Phase 57.4: API遅延対策【完了】

### 実施日: 2025/12/30

### 問題

GCPログで5000-7500msのAPI遅延が継続的に発生し、critical anomaly（閾値3000ms）として検出。

### 修正内容（unified.yaml）

```yaml
anomaly_detector:
  api_latency_warning: 5.0    # 1秒 → 5秒
  api_latency_critical: 10.0  # 3秒 → 10秒
```

### 変更前後の動作比較

| API応答時間 | 変更前 | 変更後 |
|------------|--------|--------|
| 1-3秒 | 正常 | 正常 |
| 3-5秒 | critical → 拒否 | 正常 |
| 5-10秒 | critical → 拒否 | warning（取引可能） |
| 10秒以上 | critical → 拒否 | critical → 拒否 |

### リスク評価

| 項目 | 影響 |
|------|------|
| 利点 | 5-7秒のAPI応答で取引が拒否されなくなる |
| リスク | API障害時の検出が10秒に遅延 |
| 緩和策 | 10秒でも十分に異常検出可能（通常は<1秒） |

---

## 💰 Phase 57.5: DD 10%許容・年利5%目標【完了】

### 実施日: 2025/12/30

### 目標

| 指標 | 現在 | 目標 |
|------|------|------|
| DD上限 | 0.91% | ≤10% |
| 年利 | 0.5% | 5% |
| ポジション倍率 | 1x | 10x |

### 修正内容

#### 1. バグ修正: reporter.py設定キー

```python
# 修正前
initial_capital = get_threshold("backtest.initial_balance", 100000.0)

# 修正後
initial_capital = get_threshold("mode_balances.backtest.initial_balance", 500000.0)
```

#### 2. ポジションサイズ10倍拡大（thresholds.yaml）

```yaml
production:
  max_order_size: 0.20        # 0.05 → 0.20
kelly_criterion:
  max_position_ratio: 1.00    # 0.35 → 1.00
  safety_factor: 1.0          # 0.9 → 1.0
initial_position_size: 0.02   # 0.005 → 0.02

# 信頼度別最大比率
max_position_ratio_per_trade:
  low_confidence: 0.80      # 0.25 → 0.80
  medium_confidence: 0.90   # 0.35 → 0.90
  high_confidence: 1.00     # 0.50 → 1.00

# 動的ポジションサイジング
dynamic_position_sizing:
  low_confidence:
    min_ratio: 0.50         # 0.10 → 0.50
    max_ratio: 0.80         # 0.20 → 0.80
  medium_confidence:
    min_ratio: 0.60         # 0.15 → 0.60
    max_ratio: 0.90         # 0.25 → 0.90
  high_confidence:
    min_ratio: 0.70         # 0.20 → 0.70
    max_ratio: 1.00         # 0.35 → 1.00
```

### 期待効果

| 指標 | 現在 | 10倍後予測 | 目標 |
|------|------|-----------|------|
| DD | 0.91% | ~9% | ≤10% ✅ |
| 半年利益 | ¥1,264 | ~¥12,600 | ¥12,500 ✅ |
| 年利 | 0.5% | ~5% | 5% ✅ |

### リスク管理

| リスク | 対策 |
|--------|------|
| DD 10%超過 | max_drawdown 20%でハード制限 |
| 連続損失 | consecutive_loss_limit 8回 |
| 大損失 | max_order_size 0.20 BTC制限 |

---

## 🚀 Phase 57.6: リスク最大化・年利10%目標【完了】

### 実施日: 2025/12/31

### ボトルネック分析

| ボトルネック | 原因 | 影響 |
|-------------|------|------|
| capital_allocation_limit | 10万円制限 | 50万円の20%しか使えない |
| ML信頼度別制限の二重適用 | sizer.py + limits.py | 重複制限 |
| 加重平均による希薄化 | Kelly 50%重み | Kelly効果が半減 |

### 修正内容

```yaml
trading:
  capital_allocation_limit: 500000.0  # 10万→50万
  initial_position_size: 0.04         # 0.02→0.04
production:
  max_order_size: 0.40                # 0.20→0.40
position_integrator:
  kelly_weight: 0.7                   # 50%→70%
  dynamic_weight: 0.2                 # 30%→20%
  risk_manager_weight: 0.1            # 20%→10%
```

### バックテストモード残高参照バグ修正

**問題**: `trading_cycle_manager.py`がバックテストモードでもAPIを呼び出し

**修正**: `ExecutionService.virtual_balance`を参照するよう変更（`trading_cycle_manager.py:480-493`）

```python
# Phase 57.6: バックテストモードではExecutionServiceのvirtual_balanceを使用
execution_service = getattr(self.orchestrator, "execution_service", None)
if execution_service and execution_service.mode == "backtest":
    actual_balance = execution_service.virtual_balance
else:
    balance_info = self.orchestrator.data_service.client.fetch_balance()
    actual_balance = balance_info.get("JPY", {}).get("total", 0.0)
```

### 期待効果

| 指標 | Phase 57.5 | Phase 57.6予測 | 目標 |
|------|-----------|---------------|------|
| 半年利益 | ¥3,623 | ¥36,000 | ¥25,000 ✅ |
| DD | 0.56% | ~5.6% | ≤10% ✅ |
| 年利 | 1.4% | ~14% | 10% ✅ |

---

## 🔧 Phase 57.7: 設定ファイル体系整理・レポート計算修正【完了】

### 実施日: 2026/01/01

### Part 1: 設定ファイル体系整理

#### 問題

`mode_balances`は`unified.yaml`に定義されているが、コードは`get_threshold()`（thresholds.yamlのみ参照）で読み込もうとしていた。

#### 解決策

`threshold_manager.py`を拡張して`unified.yaml`もフォールバック参照:

```python
def load_thresholds() -> Dict[str, Any]:
    # thresholds.yaml読み込み
    thresholds_data = yaml.safe_load(thresholds_path) or {}
    # Phase 57.7: unified.yamlをフォールバックとしてマージ
    unified_data = yaml.safe_load(unified_path) or {}
    thresholds_data = _deep_merge(unified_data, thresholds_data)
```

### Part 2: バックテストレポート計算バグ修正

| # | 問題 | 修正内容 |
|---|------|---------|
| 1 | バックテスト期間が0日間 | ISO文字列をdatetimeに変換 |
| 2 | PFが0.0（損失0時） | `float("inf")`を返すよう修正 |
| 3 | リカバリーファクターが0.0（DD=0時） | `float("inf")`を返すよう修正 |
| 4 | ソルティノレシオが0.0（負リターンなし時） | `float("inf")`を返すよう修正 |
| 5 | カルマーレシオが0.0（DD=0時） | `float("inf")`を返すよう修正 |
| 6 | ペイオフレシオが0.0（損失0時） | `float("inf")`を返すよう修正 |
| 7 | レジーム別制限ハードコード | `get_threshold()`から動的読み込み |

### 修正例（PF計算）

```python
# 修正前
profit_factor = (total_profit / abs(total_loss)) if total_loss != 0 else 0.0

# 修正後（Phase 57.7）
if total_loss == 0:
    profit_factor = float("inf") if total_profit > 0 else 0.0
else:
    profit_factor = total_profit / abs(total_loss)
```

### ∞表示対応

Markdownレポートで`float("inf")`を適切に表示するヘルパー関数を追加:

```python
def format_metric(value: float, decimals: int = 2) -> str:
    """Phase 57.7: 指標値のフォーマット（∞対応）"""
    import math
    if value is None:
        return "N/A"
    if math.isinf(value):
        return "∞" if value > 0 else "-∞"
    return f"{value:.{decimals}f}"
```

### 修正ファイル

| ファイル | 修正内容 |
|---------|---------|
| `src/core/config/threshold_manager.py` | unified.yamlフォールバック追加 |
| `src/backtest/reporter.py` | 期間計算・PF・RF等修正 |
| `scripts/backtest/generate_markdown_report.py` | ∞表示対応・動的設定読み込み |

---

## Phase 57.8-57.9: スキップ

Phase 57.8と57.9は、Phase 57.7のコミットメッセージ番号の誤りによりスキップされた。

---

## 🐛 Phase 57.10: バックテストDDタイムスタンプバグ修正【完了】

### 実施日: 2026/01/02

### 問題

同一設定でバックテストを実行しても、取引数が激減（58件→5件）

### 根本原因

**IntegratedRiskManagerのDrawdownManagerがバックテストタイムスタンプを使用していなかった**

| インスタンス | タイムスタンプ処理 |
|------------|-----------------|
| backtest_runner | ✅ シミュレート時刻使用 |
| IntegratedRiskManager | ❌ `datetime.now()`（実時刻）使用 |

損失発生時に`datetime.now()`でクールダウン設定 → 実時刻が進まないため6時間のクールダウンが永続化

### バグの影響フロー

1. 損失発生 → `record_trade_result()`が`datetime.now()`（実時刻: 2026-01-02 14:00）でクールダウン設定
2. クールダウン終了時刻 = 2026-01-02 20:00（6時間後）
3. 次の取引チェック → `check_trading_allowed()`も`datetime.now()`を使用
4. バックテスト実行中（数分間）は実時刻が進まない
5. **6時間のクールダウンが解除されず、残り全ての取引がブロック**

### 修正内容

| ファイル | 行 | 修正内容 |
|---------|-----|---------|
| `src/trading/risk/manager.py` | 199-200 | `check_trading_allowed(reference_timestamp)` |
| `src/trading/risk/manager.py` | 449-452 | `record_trade_result(..., current_time=timestamp)` |
| `src/trading/risk/manager.py` | 119 | デフォルト連敗制限: 5→8 |

### 追加調査結果

他のコンポーネントに同様のバグがないか調査:

| コンポーネント | 状態 | 備考 |
|--------------|------|------|
| Kelly基準 | ✅ | `reference_timestamp`を正しく使用 |
| `update_balance` | ✅ | 時刻処理不要（残高更新のみ） |
| Anomaly検出 | ✅ | バックテストへの影響軽微 |
| backtest_runner | ✅ | シミュレート時刻を正しく使用 |

### 期待効果

- バックテスト取引数: 5件 → 58件程度に回復
- DrawdownManagerがシミュレート時刻で正しく動作

---

## 📝 Phase 57.11: ローカルバックテスト機能強化【完了】

### 実施日: 2026/01/04

### 実装内容

#### Part 1: TP/SL改修

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/execution/stop_manager.py` | TP/SL order_id null check追加 |
| `src/trading/execution/executor.py` | エントリーロールバックリトライ追加（3回） |

**TP/SL order_id null check例**:
```python
order_id = tp_order.get("id")
if not order_id:
    raise Exception(
        f"TP注文配置失敗（order_idが空）: API応答={tp_order}, "
        f"サイド={side}, 数量={amount:.6f} BTC, TP価格={take_profit_price:.0f}円"
    )
```

**ロールバックリトライ例**:
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        await asyncio.to_thread(self.bitbank_client.cancel_order, entry_order_id, symbol)
        self.logger.error(f"🚨 エントリー注文ロールバック成功 - ID: {entry_order_id}")
        break
    except Exception as e:
        if attempt < max_retries - 1:
            wait_time = 2**attempt  # 1秒, 2秒
            await asyncio.sleep(wait_time)
        else:
            self.logger.critical(f"❌ CRITICAL: 手動介入必要 - 全{max_retries}回失敗")
```

#### Part 2: レポート改修

`scripts/backtest/generate_markdown_report.py`に以下を追加:
- 信頼度帯別統計
- ポジションサイズ統計
- 戦略×レジーム クロス集計
- **日毎損益分析**（ASCII損益曲線・月別パフォーマンス）

#### Part 3: run_backtest.sh改修

| 機能 | 実装 |
|------|------|
| CSVデータ収集 | ✅ |
| 日数指定 | `--days N` |
| Markdownレポート生成 | ✅ |
| 設定ファイル自動復元 | trap処理 |

使い方:
```bash
bash scripts/backtest/run_backtest.sh --days 60 --skip-collect
```

---

## 📊 Phase 57.12: バックテストデータ拡充・分析レポート強化【完了】

### 実施日: 2026/01/04

### 問題

- 戦略名が記録されない（全取引が`"strategy": "unknown"`）
- ML予測が記録されない

### 根本原因

1. TradeEvaluation dataclassにstrategy_nameフィールドがない
2. StrategyManagerが自身の名前をハードコード（"StrategyManager"）

### 修正内容

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/core/types.py` | TradeEvaluationに`strategy_name`フィールド追加 |
| `src/trading/risk/manager.py` | TradeEvaluation構築時にstrategy_name渡す |
| `src/strategies/base/strategy_manager.py` | 個別戦略名記録（4箇所）+ contributing_strategies追加 |
| `scripts/backtest/generate_markdown_report.py` | 戦略別・ML別・一致率統計セクション追加 |

### 追加分析機能

- 戦略別統計（取引数・勝率・平均損益・総損益）
- ML予測別統計（BUY/HOLD/SELLごと）
- ML×戦略一致率分析

### 出力例（戦略別）

```markdown
## 戦略別パフォーマンス（Phase 57.12追加）

| 戦略 | 取引数 | 勝率 | 平均損益/取引 | 総損益 |
|------|--------|------|-------------|--------|
| StochasticReversal | 1件 | 100.0% | ¥+381 | ¥+381 |
| DonchianChannel | 3件 | 33.3% | ¥+70 | ¥+211 |
| ATRBased | 15件 | 40.0% | ¥-35 | ¥-528 |
```

### 出力例（ML×戦略一致率）

```markdown
## ML×戦略一致率分析（Phase 57.12追加）

| 区分 | 取引数 | 勝率 | 総損益 |
|------|--------|------|--------|
| **一致**（戦略=ML） | 2件 | 100.0% | ¥+241 |
| 不一致（戦略≠ML） | 20件 | 30.0% | ¥-715 |
| └ ML HOLD時 | 17件 | 23.5% | ¥-926 |

**一致率**: 9.1% (2/22件)
**評価**: 一致時の勝率が70.0pt高い → ML予測を重視すべき
```

---

## 📊 Phase 57.13: 固定期間バックテスト・標準分析スクリプト【完了】

### 実施日: 2026/01/06

### 解決した問題

1. ローリングウィンドウ方式により毎日結果が変わる
2. 毎回異なる観点で分析するため比較が困難
3. CI/ローカル間の連携不足

### Part 1: 固定期間バックテスト

**thresholds.yaml設定追加**:
```yaml
execution:
  backtest_use_fixed_dates: true
  backtest_start_date: "2025-07-01"
  backtest_end_date: "2025-12-31"
```

**backtest_runner.py修正**: `_setup_backtest_period()`で固定期間モード対応

### Part 2: 標準分析スクリプト

**新規作成**: `scripts/backtest/standard_analysis.py`

84項目の固定指標:
| カテゴリ | 項目数 |
|---------|--------|
| 基本指標 | 10 |
| 戦略別 | 36 |
| ML予測別 | 12 |
| ML×戦略一致率 | 4 |
| レジーム別 | 8 |
| 時系列 | 6 |
| 改善示唆 | 8 |

使い方:
```bash
python3 scripts/backtest/standard_analysis.py --from-ci --phase 57.13
python3 scripts/backtest/standard_analysis.py --local --phase 57.13
```

### Part 3: CI/ローカル連携

**backtest.yml修正**:
- Step 7.5追加: バックテスト結果をartifactとして保存（90日保存）
- artifact内容: `src/backtest/logs/backtest_*.json`, `backtest_run.log`

**run_backtest.sh修正**:
```bash
# Step 6: ローカル結果を検証記録に保存
REPORT_DATE=$(TZ=Asia/Tokyo date +"%Y%m%d")
LOCAL_JSON="docs/検証記録/local_backtest_${REPORT_DATE}.json"
cp "$LATEST_JSON" "$LOCAL_JSON"
echo "📁 ローカル結果保存: $LOCAL_JSON"
```

### 期待される成果

1. **再現性**: 同一コードで同一結果が保証される
2. **比較容易性**: 履歴CSVで変更前後を即座に比較
3. **改善指針**: 自動生成される改善提案で次のアクションが明確
4. **ブレ排除**: 分析項目固定で「今回だけ見た指標」がなくなる
5. **CI/ローカル統一**: 同じ分析スクリプトでどちらも分析可能

---

## 📊 Phase 57 最終結果分析

### 固定期間バックテスト結果（2025/07/01〜2025/12/31）

| 指標 | 値 | 評価 |
|------|-----|------|
| 総取引数 | 501件 | 約2.74件/日 |
| 勝率 | 44.7% | 標準的 |
| 総損益 | **¥+23,073** | **基準値として設定** |
| PF | 1.18 | 良好 |
| SR | 4.78 | 優秀 |
| 最大DD | ¥15,638 (2.93%) | 低リスク |
| 期待値 | ¥+46/取引 | 安定 |

### 戦略別パフォーマンス

| 戦略 | 取引数 | 勝率 | 損益 | 評価 |
|------|--------|------|------|------|
| ATRBased | 274 (54.7%) | 45.3% | ¥+21,205 | ◎ 主力 |
| StochasticReversal | 59 (11.8%) | 54.2% | ¥+6,909 | ◎ 最高勝率 |
| ADXTrendStrength | 68 (13.6%) | 44.1% | ¥+3,969 | ○ 安定 |
| DonchianChannel | 88 (17.6%) | 42.0% | ¥-3,560 | △ 要検討 |
| BBReversal | 12 (2.4%) | 8.3% | ¥-5,451 | ✗ 問題あり |

### ML予測別パフォーマンス

| ML予測 | 取引数 | 勝率 | 損益 |
|--------|--------|------|------|
| BUY | 152 | 43.4% | ¥+5,710 |
| HOLD | 87 | **55.2%** | **¥+15,255** |
| SELL | 262 | 42.0% | ¥+2,108 |

**重要発見**: ML HOLD時の勝率55.2%が全体44.7%を大幅に上回る

### 信頼度帯別パフォーマンス

| 信頼度帯 | 勝率 | 評価 |
|---------|------|------|
| 低（<50%） | 43.8% | 標準 |
| 高（≥65%） | **36.4%** | **低い** |

**問題**: 高信頼度帯の勝率が低信頼度帯より低い逆転現象

### レジーム別パフォーマンス

| レジーム | 取引数 | 勝率 | 損益 |
|----------|--------|------|------|
| tight_range | 442 | 45.2% | ¥+20,977 |
| normal_range | 59 | 40.7% | ¥+2,096 |
| trending | 0 | - | - |
| high_volatility | 0 | - | - |

**発見**: tight_rangeが全体の88%を占め、利益の91%を生成

### 時系列指標

| 指標 | 値 |
|------|-----|
| 利益日数 | 46日 |
| 損失日数 | 43日 |
| 最良日 | ¥+5,557 |
| 最悪日 | ¥-3,546 |
| 最大連勝 | 9回 |
| 最大連敗 | 13回 |

### 2票ルール評価

Phase 56.7で導入された「2票ルール」を分析した結果:

#### 2票ルールのロジック

```
BUY 2票以上 かつ SELL 1票以下 → BUY選択（HOLD無視）
SELL 2票以上 かつ BUY 1票以下 → SELL選択（HOLD無視）
BUY/SELL両方2票以上 → HOLD（矛盾）
BUY/SELL両方1票以下 → 従来ロジック（重み付け比較）
```

#### 従来方式との比較

| 観点 | 従来方式 | 2票ルール |
|------|---------|----------|
| 設計思想 | 「確信がなければ待つ」 | 「コンセンサスがあれば行動」 |
| リスク | 機会損失 | 低品質取引の混入 |
| HOLD問題 | HOLD支配で取引激減 | HOLDを無視して解決 |

#### 結論

**2票ルールを維持すべき**（条件付き）

理由:
1. シャープレシオ4.78は非常に優秀
2. 最大DD 2.93%は低リスク
3. 総損益¥+23,073は黒字を維持
4. HOLD支配問題を解決している

**発見された問題**:
- BBReversal: 勝率8.3%で¥-5,451の損失 → **無効化推奨**
- DonchianChannel: ¥-3,560の赤字 → **重み削減検討**
- 高信頼度帯の勝率(36.4%)が低信頼度帯(43.8%)より低い → **フィルター見直し**

#### 推奨アクション（Phase 58へ）

| 優先度 | アクション | 期待効果 |
|--------|-----------|---------|
| 高 | BBReversal無効化 | +¥5,451 |
| 中 | DonchianChannel重み削減 | +¥1,000〜3,000 |
| 低 | 信頼度フィルター見直し | 勝率改善 |

---

## 📊 Phase 57.14: ライブモード標準分析スクリプト【完了】

### 実施日: 2026/01/07

### 目的

バックテストの`standard_analysis.py`と同様に、ライブモードでも固定指標で分析できるスクリプトを作成。
毎回の診断で評価方法がブレないようにする。

### 実装内容

#### 35固定指標

| カテゴリ | 指標数 | 主要項目 |
|---------|--------|----------|
| アカウント状態 | 5 | 証拠金維持率、利用可能残高、未実現損益 |
| ポジション状態 | 5 | オープンポジション、未約定注文、ロスカット価格 |
| 取引履歴分析 | 12 | 勝率、損益、戦略別統計、TP/SL発動数 |
| システム健全性 | 6 | API応答時間、エラー数、Container再起動 |
| TP/SL適切性 | 4 | TP/SL距離%、設置状態 |
| 稼働率 | 3 | 稼働時間率（90%目標）、ダウンタイム |

#### データ取得方法

| データ | 取得方法 |
|--------|---------|
| アカウント状態 | `BitbankClient.fetch_margin_status()` |
| ポジション | `BitbankClient.fetch_positions()` |
| アクティブ注文 | `BitbankClient.fetch_active_orders()` |
| 取引履歴 | `tax/trade_history.db` SQLite |
| GCPログ | `gcloud logging read` subprocess |
| サービス状態 | `gcloud run services describe` |

### 作成ファイル

| ファイル | 内容 |
|---------|------|
| `scripts/live/standard_analysis.py` | メインスクリプト（741行） |
| `scripts/live/__init__.py` | パッケージ初期化 |
| `CLAUDE.md` | 使用方法追記 |

### 使用方法

```bash
# 基本実行（24時間分析）
python3 scripts/live/standard_analysis.py

# 期間指定（48時間）
python3 scripts/live/standard_analysis.py --hours 48

# 出力先指定
python3 scripts/live/standard_analysis.py --output results/live/
```

### 出力形式

- **JSON**: `results/live/live_analysis_YYYYMMDD_HHMMSS.json`
- **Markdown**: `results/live/live_analysis_YYYYMMDD_HHMMSS.md`
- **CSV履歴**: `results/live/live_analysis_history.csv`

---

## 📝 学習事項

### リスク管理

1. **レバレッジ計算の重要性**: バックテストと実運用で一致させる必要あり
2. **リスクコンポーネント正規化**: min(1.0, ...)でキャップしないと予期しない高スコアが発生
3. **DD目標の設定**: 過度に保守的な設定は収益性を犠牲にする

### ML・信頼度

4. **ML信頼度閾値の影響**: 60%閾値が厳しすぎると大半が低信頼度扱いに
5. **MLモデル精度の限界**: 41%精度では高信頼度予測が少ない

### 設定管理

6. **設定ファイル役割の分離**: features.yaml / unified.yaml / thresholds.yaml を明確に分離
7. **設定読み込みの優先順位**: get_threshold()でunified.yamlをフォールバック参照

### バックテスト

8. **時刻処理の重要性**: 複数コンポーネントがDrawdownManagerを持つ場合、全てにシミュレート時刻を渡す
9. **デフォルト値の統一**: 同じ設定項目のデフォルト値は全ファイルで統一する
10. **固定期間の重要性**: ローリングウィンドウでは比較困難、固定期間で再現性確保

### API・GCP

11. **API閾値の適正化**: 実測値に基づいた閾値設定が必要
12. **Enum値のログ出力**: `.value`属性を使用して文字列値を取得

### 戦略分析

13. **BBReversal問題**: 勝率8.3%は統計的に異常 → 無効化検討
14. **ATRBased優位性**: 全利益の92%を生成する主力戦略
15. **レジーム集中**: tight_rangeが全体の88%、利益の91%を占める

### ML活用

16. **ML HOLD予測の価値**: HOLD時勝率55.2%は全体より高い
17. **信頼度フィルターの逆転**: 高信頼度帯の勝率が低信頼度帯より低い

---

## 📁 修正ファイル一覧（主要）

### 設定ファイル

| ファイル | 主な変更 |
|---------|---------|
| `config/core/thresholds.yaml` | Kelly緩和・ポジション制限・固定期間設定 |
| `config/core/unified.yaml` | 証拠金50万円・API閾値緩和 |

### リスク管理

| ファイル | 主な変更 |
|---------|---------|
| `src/trading/risk/manager.py` | リスクスコア正規化・タイムスタンプ修正 |
| `src/trading/risk/sizer.py` | 信頼度閾値60%→50% |
| `src/trading/position/limits.py` | 信頼度閾値60%→50% |

### バックテスト

| ファイル | 主な変更 |
|---------|---------|
| `src/core/execution/backtest_runner.py` | レバレッジ修正・固定期間対応 |
| `src/backtest/reporter.py` | 設定キー修正・計算バグ修正 |
| `scripts/backtest/standard_analysis.py` | **新規** - 標準分析スクリプト |
| `scripts/backtest/run_backtest.sh` | CSV収集・日数指定・レポート生成 |
| `scripts/backtest/generate_markdown_report.py` | 分析機能追加 |
| `scripts/live/standard_analysis.py` | **新規** - ライブモード標準分析スクリプト |
| `scripts/live/__init__.py` | **新規** - パッケージ初期化 |

### 取引実行

| ファイル | 主な変更 |
|---------|---------|
| `src/trading/execution/executor.py` | レバレッジ修正・ロールバックリトライ |
| `src/trading/execution/stop_manager.py` | order_id null check |

### その他

| ファイル | 主な変更 |
|---------|---------|
| `src/core/config/threshold_manager.py` | unified.yamlフォールバック |
| `src/core/services/trading_cycle_manager.py` | バックテスト残高参照修正 |
| `src/core/services/trading_logger.py` | RiskDecision Enum対応 |
| `src/strategies/base/strategy_manager.py` | 個別戦略名記録 |
| `src/trading/core/types.py` | TradeEvaluationにstrategy_name追加 |

### CI/CD

| ファイル | 主な変更 |
|---------|---------|
| `.github/workflows/backtest.yml` | 固定期間対応・artifact保存追加 |

---

## 📊 Phase 57 全体評価

### 目標達成状況

| 目標 | 設定値 | 結果 | 達成 |
|------|--------|------|------|
| 年利 | 10% | 約9.2%（半年¥23,073×2） | △ |
| 最大DD | ≤10% | 2.93% | ✅ |
| PF | ≥1.15 | 1.18 | ✅ |
| SR | - | 4.78 | ✅ |

### 成果サマリー

**Phase 57.0-57.6**: リスク設定最適化
- レバレッジ計算バグ修正（4倍→2倍）
- ポジションサイズ10倍拡大
- Kelly基準緩和・capital_allocation_limit修正

**Phase 57.7**: 設定管理改善
- unified.yamlフォールバック実装
- レポート計算バグ7件修正

**Phase 57.10**: バックテスト安定化
- DrawdownManagerタイムスタンプバグ修正
- デフォルト値統一

**Phase 57.11-57.12**: 分析機能強化
- TP/SL安定性改善
- 戦略別・ML別分析追加
- 個別戦略名記録対応

**Phase 57.13**: 再現性確保
- 固定期間バックテスト実装
- 標準分析スクリプト作成
- CI/ローカル連携強化

**Phase 57.14**: ライブモード分析標準化
- 35固定指標の標準分析スクリプト作成
- bitbank API/GCPログ連携
- JSON/Markdown/CSV出力対応

### 次フェーズへの引き継ぎ（Phase 58）

1. **BBReversal無効化**: 勝率8.3%・¥-5,451 → 期待効果+¥5,451
2. **DonchianChannel重み削減**: ¥-3,560 → 期待効果+¥1,000〜3,000
3. **信頼度フィルター見直し**: 高信頼度帯の逆転現象解消

**Phase 58目標**: 総損益 ≥¥+28,000（+21%）、PF ≥1.25

---

**📅 最終更新**: 2026年1月7日 - Phase 57.14完了（ライブモード標準分析スクリプト）
