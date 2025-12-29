# Phase 57 開発記録

**期間**: 2025/12/29 - 進行中
**状況**: Phase 57.2 進行中

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
| 57.2 | DD 5%攻撃的設定 | 🔄 | 信頼度閾値変更・ポジション拡大 |

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

## 🚀 Phase 57.2: DD 5%攻撃的設定【進行中】

### 実施日: 2025/12/30

### 目的

DD 5%まで許容してポジションサイズを大幅拡大

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

- [ ] thresholds.yaml更新
- [ ] sizer.py修正（0.60→0.50）
- [ ] manager.py修正（0.60→0.50）
- [ ] limits.py修正（0.60→0.50）
- [ ] コミット・プッシュ
- [ ] バックテスト実行・検証

---

## 📝 学習事項

1. **レバレッジ計算の重要性**: バックテストと実運用で一致させる必要あり
2. **ML信頼度閾値の影響**: 60%閾値が厳しすぎると大半が低信頼度扱いに
3. **コードデフォルト値の問題**: 設定ファイルよりコードデフォルトが優先される場合がある
4. **MLモデル精度の限界**: 41%精度では高信頼度予測が少ない
5. **DD目標の設定**: 過度に保守的な設定は収益性を犠牲にする

---

## 📊 MLモデル性能改善の検討（将来課題）

現在のモデル精度41%は低い。改善候補:

1. **特徴量エンジニアリング**: 追加特徴量の検討
2. **ハイパーパラメータチューニング**: GridSearch/Optuna
3. **訓練データ拡充**: より長期の過去データ
4. **アンサンブル重み調整**: 現在LGB50%/XGB30%/RF20%

---

**📅 最終更新**: 2025年12月30日 - Phase 57.2進行中
