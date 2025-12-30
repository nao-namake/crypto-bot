# Phase 57 開発記録

**期間**: 2025/12/29 - 2025/12/30
**状況**: Phase 57.6 リスク最大化・年利10%目標

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

---

## 🔍 Phase 57.0: 年利10%計画策定【完了】

### 実施日: 2025/12/29

### 調査結果

#### 現状分析

| 指標 | 値 | 評価 |
|------|-----|------|
| 証拠金 | ¥100,000（設定） | 少額 |
| 年利 | 1.4% | 非常に低い |
| DD | 0.79% | 過度に保守的 |
| max_drawdown設定 | 20% | 余裕大 |

#### 制約の発見

1. **レバレッジ計算バグ**: コードで4倍計算、bitbankは2倍まで
2. **Kelly基準が厳しい**: max_position_ratio 10%、safety_factor 0.7
3. **ポジションサイズ制限**: 多層制限で極小化

### 計画策定

- 証拠金: 10万円 → 50万円（設定変更）
- 年利目標: 10%（年間¥50,000）
- 想定DD: 2-5%

---

## ⚙️ Phase 57.1: レバレッジ・Kelly・ポジション緩和【完了】

### 実施日: 2025/12/29

### 修正内容

#### 1. レバレッジ計算バグ修正

| ファイル | 行 | 変更 |
|---------|-----|------|
| `src/trading/execution/executor.py` | 956-958 | `/ 4` → `/ 2` |
| `src/core/execution/backtest_runner.py` | 831, 992 | `/ 4` → `/ 2` |

```python
# Phase 57: 必要証拠金計算（bitbank信用取引は2倍レバレッジ）
order_total = price * amount  # 注文総額
required_margin = order_total / 2  # 必要証拠金（50%）
```

#### 2. Kelly基準緩和（thresholds.yaml）

```yaml
kelly_criterion:
  max_position_ratio: 0.25    # 10% → 25%
  safety_factor: 0.8          # 0.7 → 0.8

initial_position_size: 0.002   # 0.0005 → 0.002（4倍）
```

#### 3. ポジションサイズ制限緩和（thresholds.yaml）

```yaml
max_position_ratio_per_trade:
  low_confidence: 0.15    # 10% → 15%
  medium_confidence: 0.25  # 15% → 25%
  high_confidence: 0.40    # 25% → 40%

dynamic_position_sizing:
  low_confidence:
    min_ratio: 0.05    # 3% → 5%
    max_ratio: 0.10    # 5% → 10%
  medium_confidence:
    min_ratio: 0.08    # 5% → 8%
    max_ratio: 0.15    # 8% → 15%
  high_confidence:
    min_ratio: 0.12    # 8% → 12%
    max_ratio: 0.20    # 10% → 20%

max_capital_usage: 0.5     # 0.3 → 0.5
```

#### 4. 証拠金設定更新（unified.yaml）

```yaml
mode_balances:
  paper:
    initial_balance: 500000.0     # 10万 → 50万
  live:
    initial_balance: 500000.0     # 10万 → 50万
  backtest:
    initial_balance: 500000.0     # 10万 → 50万
```

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
- しかし勝率が低下（ATR戦略のコード設定問題）
- DD 0.79%は目標5%に遠い

### 発見された問題

#### ATR戦略コードのデフォルト値問題

atr_based.pyのコードデフォルト値がPhase 56.10の実験設定のまま残っていた。

```python
# 問題のあったデフォルト値（Phase 56.10）
"bb_as_main_condition": True  # PF 0.78の原因

# 修正後（Phase 55.4設定）
"bb_as_main_condition": False  # PF 1.16の設定
```

修正内容:
- `src/strategies/implementations/atr_based.py`: デフォルト値をPhase 55.4に復元
- `config/core/thresholds.yaml`: ATR設定をPhase 55.4に復元

---

## 🚀 Phase 57.2: DD 5%攻撃的設定【実装完了】

### 実施日: 2025/12/30

### 目的

DD 5%まで許容してポジションサイズを大幅拡大（年利10%達成）

### 調査結果

#### MLモデルの実態

```
ML検証スクリプト実行結果:

🎯 信頼度統計:
   平均: 0.518
   最小: 0.349
   最大: 0.717
   高信頼度(>60%): 23.0%

📊 個別モデル性能:
   LightGBM:     Accuracy 41.5%, F1 0.412
   XGBoost:      Accuracy 41.9%, F1 0.419
   RandomForest: Accuracy 41.3%, F1 0.400
```

| 指標 | 値 | 問題点 |
|------|-----|--------|
| 平均信頼度 | **51.8%** | 60%閾値を下回る |
| 高信頼度(>60%) | **23%** | 77%が低信頼度扱い |
| モデル精度 | **41%** | ランダム33%よりわずかに良い程度 |

**問題**: 77%の取引が「低信頼度」（<60%）に分類され、ポジションサイズが制限される

### 変更計画

#### 1. 信頼度閾値を60%→50%に変更

**理由**: 平均信頼度51.8%なので、50%閾値なら約半数が「中信頼度」に分類

**変更ファイル**:

| ファイル | 行 | 変更 |
|---------|-----|------|
| `src/trading/risk/sizer.py` | 116, 223, 252 | `0.60` → `0.50` |
| `src/trading/risk/manager.py` | 781 | `0.60` → `0.50` |
| `src/trading/position/limits.py` | 340 | `0.60` → `0.50` |

#### 2. ポジションサイズ制限のさらなる緩和

```yaml
# thresholds.yaml
max_position_ratio_per_trade:
  low_confidence: 0.25     # 0.15 → 0.25
  medium_confidence: 0.35   # 0.25 → 0.35
  high_confidence: 0.50     # 0.40 → 0.50

dynamic_position_sizing:
  low_confidence:
    min_ratio: 0.10        # 0.05 → 0.10（2倍）
    max_ratio: 0.20        # 0.10 → 0.20（2倍）
  medium_confidence:
    min_ratio: 0.15        # 0.08 → 0.15
    max_ratio: 0.25        # 0.15 → 0.25
  high_confidence:
    min_ratio: 0.20        # 0.12 → 0.20
    max_ratio: 0.35        # 0.20 → 0.35
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

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `config/core/thresholds.yaml` | ポジションサイズ・Kelly緩和 |
| `src/trading/risk/sizer.py` | 信頼度閾値60%→50% |
| `src/trading/risk/manager.py` | 信頼度閾値60%→50% |
| `src/trading/position/limits.py` | 信頼度閾値60%→50% |

### 実装状況

- [x] thresholds.yaml更新（Kelly緩和・ポジション制限拡大）
- [x] sizer.py修正（0.60→0.50、3箇所）
- [x] manager.py修正（0.60→0.50、1箇所）
- [x] limits.py修正（0.60→0.50、1箇所）
- [x] atr_based.py修正（Phase 55.4設定復元）
- [x] thresholds.yaml ATR設定復元
- [x] コミット・プッシュ（744a0dc1）
- [ ] バックテスト結果検証（Run ID: 20583684251）

### コミット情報

```
commit 744a0dc1
Author: Claude Code
Date: 2025/12/30

fix: Phase 57.2 DD 5%攻撃的設定

- 信頼度閾値60%→50%に変更（5ファイル）
- Kelly max_position_ratio: 25%→35%
- Kelly safety_factor: 0.8→0.9
- initial_position_size: 0.002→0.005
- max_order_size: 0.03→0.05
- ポジション制限約2倍に拡大
- ATR戦略Phase 55.4設定復元
```

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

Phase 56.8デプロイ後、ライブモードで取引が発生しない。全ての取引が`リスクスコア=100.0%`で拒否されている。

### 調査結果

#### GCPログ分析

```
取引拒否: リスクスコア=100.0%, 理由=
取引拒否: リスクスコア=100.0%, 理由=重大なAPI遅延: 5600ms
```

- 全ての取引がrisk_score=1.0で拒否
- 「理由」が空のケースが多い（denial_reasonsが空）
- API遅延警告（3000ms超過）が時々発生

#### 根本原因

1. **リスクスコア計算のバグ**: `drawdown_risk`と`consecutive_risk`が1.0でキャップされていなかった

```python
# 問題のあったコード
drawdown_risk = drawdown_ratio / 0.20          # キャップなし
consecutive_risk = consecutive_losses / 5.0   # キャップなし

# 修正後（Phase 57.3）
drawdown_risk = min(1.0, drawdown_ratio / 0.20)
consecutive_risk = min(1.0, consecutive_losses / 5.0)
```

2. **ログ表示バグ**: RiskDecision列挙型が正しく処理されず「❓ 不明」と表示

```python
# 問題: str(RiskDecision.DENIED) → "RiskDecision.DENIED"
# 修正: decision_raw.value → "denied"
```

### 修正内容

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/risk/manager.py` | リスクコンポーネントのmin(1.0, ...)正規化追加 |
| `src/trading/risk/manager.py` | リスクスコア詳細ログ追加（診断用） |
| `src/core/services/trading_logger.py` | RiskDecision Enum対応（.value使用） |

### 追加診断ログ

高リスクスコア（≥85%）時に詳細ログを出力：

```
🔍 リスクスコア詳細: total=0.850, ml_risk=0.607×0.3=0.182,
anomaly=0.500×0.25=0.125, drawdown=0.000×0.25=0.000,
consecutive=0.000×0.1=0.000, volatility=0.400×0.1=0.040
```

### 期待効果

- リスクスコアが適切な範囲（0-100%）に正規化
- denial_reasonsが空でも正確なリスクスコアを計算
- ログで判定結果が正しく表示される（🟢 取引承認 / 🔴 取引拒否）

---

## ⚡ Phase 57.4: API遅延対策【完了】

### 実施日: 2025/12/30

### 問題

GCPログで5000-7500msのAPI遅延が継続的に発生し、critical anomaly（閾値3000ms）として検出されていた。

```
取引拒否: リスクスコア=100.0%, 理由=重大なAPI遅延: 5600ms
取引拒否: リスクスコア=100.0%, 理由=重大なAPI遅延: 6600ms
```

### 調査結果

#### API遅延パターン

| 項目 | 値 |
|------|-----|
| 遅延範囲 | 5000-7500ms |
| 発生頻度 | 継続的 |
| 閾値（warning） | 1秒 |
| 閾値（critical） | 3秒 |

#### 遅延の原因

| 原因 | 可能性 | 備考 |
|------|--------|------|
| bitbank API応答 | 中〜高 | 外部要因、制御不可 |
| Cloud Run cold start | 中 | コンテナ起動時の初期遅延 |
| ccxt rate limiting | 低 | 1秒制限で5秒遅延は説明不可 |
| ネットワーク遅延 | 低 | 両方とも東京リージョン |

### 修正内容

#### unified.yaml の変更

```yaml
# Before
anomaly_detector:
  api_latency_warning: 1.0    # 1秒
  api_latency_critical: 3.0   # 3秒

# After (Phase 57.4)
anomaly_detector:
  api_latency_warning: 5.0    # 5秒（実測5-7秒に対応）
  api_latency_critical: 10.0  # 10秒（過剰拒否防止）
```

### システムへの影響

#### 変更前後の動作比較

| API応答時間 | 変更前 | 変更後 |
|------------|--------|--------|
| 1-3秒 | 正常 | 正常 |
| 3-5秒 | critical → 拒否 | 正常 |
| 5-10秒 | critical → 拒否 | warning（取引可能） |
| 10秒以上 | critical → 拒否 | critical → 拒否 |

#### リスク評価

| 項目 | 影響 |
|------|------|
| **利点** | 5-7秒のAPI応答で取引が拒否されなくなる |
| **リスク** | API障害時の検出が10秒に遅延 |
| **緩和策** | 10秒でも十分に異常検出可能（通常は<1秒） |

### 補足

Phase 57.3の修正（リスクコンポーネントの正規化）により、API遅延があってもrisk_scoreが100%まで上がることはなくなる。両方の修正を併用することで安定した運用が可能。

---

## 💰 Phase 57.5: DD 10%許容・年利5%目標【完了】

### 実施日: 2025/12/30

### 背景

Phase 57.2バックテスト結果:
- DD 0.91%、利益 ¥1,264（半年）
- 50万円で半年¥1,264は年利0.5%
- 目標: 年利5%（半年で¥12,500）

### 目標設定

| 指標 | 現在 | 目標 |
|------|------|------|
| DD上限 | 0.91% | **≤10%** |
| 年利 | 0.5% | **5%** |
| 半年利益 | ¥1,264 | **¥12,500** |
| ポジション倍率 | 1x | **10x** |

### 修正内容

#### 1. バグ修正: reporter.py設定キー

バックテストレポートが¥100,000で計算されていた問題を修正。

```python
# Before (src/backtest/reporter.py:350)
initial_capital = get_threshold("backtest.initial_balance", 100000.0)

# After (Phase 57.5)
initial_capital = get_threshold("mode_balances.backtest.initial_balance", 500000.0)
```

#### 2. ポジションサイズ10倍拡大（thresholds.yaml）

```yaml
# production
max_order_size: 0.20        # 0.05 → 0.20（4倍）

# Kelly基準
kelly_criterion:
  max_position_ratio: 1.00  # 0.35 → 1.00（2.9倍）
  safety_factor: 1.0        # 0.9 → 1.0（安全係数撤廃）

# 初期ポジション
initial_position_size: 0.02  # 0.005 → 0.02（4倍）

# 信頼度別最大比率
max_position_ratio_per_trade:
  low_confidence: 0.80      # 0.25 → 0.80（3.2倍）
  medium_confidence: 0.90   # 0.35 → 0.90（2.6倍）
  high_confidence: 1.00     # 0.50 → 1.00（2倍）

# 動的ポジションサイジング
dynamic_position_sizing:
  low_confidence:
    min_ratio: 0.50         # 0.10 → 0.50（5倍）
    max_ratio: 0.80         # 0.20 → 0.80（4倍）
  medium_confidence:
    min_ratio: 0.60         # 0.15 → 0.60（4倍）
    max_ratio: 0.90         # 0.25 → 0.90（3.6倍）
  high_confidence:
    min_ratio: 0.70         # 0.20 → 0.70（3.5倍）
    max_ratio: 1.00         # 0.35 → 1.00（2.9倍）
```

### 期待効果

| 指標 | 現在 | 10倍後予測 | 目標 |
|------|------|-----------|------|
| DD | 0.91% | ~9% | ≤10% ✅ |
| 半年利益 | ¥1,264 | ~¥12,600 | ¥12,500 ✅ |
| 年利 | 0.5% | ~5% | 5% ✅ |
| 平均勝ち | ¥211 | ~¥2,100 | - |
| 平均負け | ¥156 | ~¥1,560 | - |

### リスク管理

| リスク | 対策 |
|--------|------|
| DD 10%超過 | max_drawdown 20%でハード制限 |
| 連続損失 | consecutive_loss_limit 8回 |
| 大損失 | max_order_size 0.20 BTC制限 |

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `src/backtest/reporter.py` | 設定キー修正（mode_balances.backtest.initial_balance） |
| `config/core/thresholds.yaml` | ポジション設定10倍拡大 |

---

## 🚀 Phase 57.6: リスク最大化・年利10%目標【完了】

### 実施日: 2025/12/31

### 背景

Phase 57.5バックテスト結果:
- DD 0.56%、利益 ¥3,623（半年）
- 10倍設定でも利益は3倍にしか増えなかった
- DD余裕が17.8倍（0.56% vs 目標10%）

### ボトルネック分析

徹底調査により3つの主要ボトルネックを特定:

| ボトルネック | 原因 | 影響 |
|-------------|------|------|
| capital_allocation_limit | 10万円制限 | 50万円の20%しか使えない |
| ML信頼度別制限の二重適用 | sizer.py + limits.py | 重複制限 |
| 加重平均による希薄化 | Kelly 50%重み | Kelly効果が半減 |

### 修正内容

```yaml
# thresholds.yaml
trading:
  capital_allocation_limit: 500000.0  # 10万→50万（5倍）

trading:
  initial_position_size: 0.04  # 0.02→0.04（2倍）

production:
  max_order_size: 0.40  # 0.20→0.40（2倍）

position_integrator:
  kelly_weight: 0.7      # 50%→70%
  dynamic_weight: 0.2    # 30%→20%
  risk_manager_weight: 0.1  # 20%→10%
```

### 期待効果

| 指標 | Phase 57.5 | Phase 57.6予測 | 目標 |
|------|-----------|---------------|------|
| 半年利益 | ¥3,623 | ¥36,000 | ¥25,000 ✅ |
| DD | 0.56% | ~5.6% | ≤10% ✅ |
| 年利 | 1.4% | ~14% | 10% ✅ |

### リスク管理

| リスク | 対策 |
|--------|------|
| DD 10%超過 | max_drawdown 20%でハード制限 |
| 連続損失 | consecutive_loss_limit 8回 |
| 大損失 | max_order_size 0.40 BTC制限 |
| 証拠金維持率 | 80%維持必須 |

---

## 📝 学習事項

1. **レバレッジ計算の重要性**: バックテストと実運用で一致させる必要あり
2. **ML信頼度閾値の影響**: 60%閾値が厳しすぎると大半が低信頼度扱いに
3. **コードデフォルト値の問題**: 設定ファイルよりコードデフォルトが優先される場合がある
4. **MLモデル精度の限界**: 41%精度では高信頼度予測が少ない
5. **DD目標の設定**: 過度に保守的な設定は収益性を犠牲にする
6. **リスクコンポーネント正規化の重要性**: min(1.0, ...)でキャップしないと予期しない高スコアが発生
7. **Enum値のログ出力**: `.value`属性を使用して文字列値を取得する必要がある
8. **API閾値の適正化**: 実測値に基づいた閾値設定が必要（過度に厳しい閾値は正常なトレードを拒否する）

---

## 📊 MLモデル性能改善の検討（将来課題）

現在のモデル精度41%は低い。改善候補:

1. **特徴量エンジニアリング**: 追加特徴量の検討
2. **ハイパーパラメータチューニング**: GridSearch/Optuna
3. **訓練データ拡充**: より長期の過去データ
4. **アンサンブル重み調整**: 現在LGB50%/XGB30%/RF20%

---

**📅 最終更新**: 2025年12月31日 - Phase 57.6 リスク最大化・年利10%目標完了
