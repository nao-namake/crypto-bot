# Optuna最適化システム - 使い方ガイド

**最終更新**: 2025年12月4日 - Phase 60.3スクリプト整理完了

---

## 概要

Optunaを使用したベイズ最適化により、トレーディングシステムのパラメータを包括的に最適化します。

**対応最適化タイプ**:
- `hybrid`: 全パラメータ3段階最適化（リスク + ML統合 + 戦略）← **推奨**
- `risk`: リスク管理パラメータのみ
- `ml_integration`: ML統合パラメータのみ
- `strategy`: 戦略パラメータのみ（6戦略対応）

---

## ディレクトリ構成

```
scripts/optimization/
├── README.md                           # このファイル
├── run_github_optimization.py          # エントリーポイント（GitHub Actions対応）
├── save_as_preset.py                   # 最適化結果をプリセットとして保存
├── hybrid_optimizer.py                 # 3段階ハイブリッド最適化パイプライン
├── backtest_integration.py             # バックテスト統合・実行
├── optuna_utils.py                     # 共通ユーティリティ
├── optimize_risk_management.py         # リスク管理パラメータ最適化
├── optimize_ml_integration.py          # ML統合パラメータ最適化
├── optimize_ml_hyperparameters.py      # MLハイパーパラメータ最適化
└── optimize_strategy_parameters_v2.py  # 戦略パラメータ最適化（6戦略対応）

config/optimization/results/
├── latest_optimization.json            # 最新の最適化結果
├── phase57_6_strategy_parameters_v2.json  # 戦略パラメータ結果
└── ...
```

---

## 基本的な使い方

### 1. GitHub Actionsで実行（推奨）

GitHub Actions > "Optuna Parameter Optimization" > "Run workflow" から実行

```
パラメータ:
- optimization_type: hybrid / risk / ml_integration / strategy
- n_trials: 30 / 50 / 100
- backtest_days: 30 / 90 / 180
```

**実行時間目安（hybrid, 50試行, 90日）**: 約3.5-4時間

### 2. ローカルで実行

```bash
# 全パラメータ最適化（推奨）
python3 scripts/optimization/run_github_optimization.py \
  --type hybrid \
  --n-trials 50 \
  --backtest-days 90 \
  --verbose

# 戦略パラメータのみ最適化
python3 scripts/optimization/run_github_optimization.py \
  --type strategy \
  --n-trials 30 \
  --backtest-days 30

# 特定の戦略のみ最適化（Phase 60.3）
python3 scripts/optimization/run_github_optimization.py \
  --type strategy \
  --strategy ATRBased \
  --n-trials 30
```

### 3. 結果をプリセットとして保存

```bash
python3 scripts/optimization/save_as_preset.py \
  --source config/optimization/results/latest_optimization.json \
  --preset-name "optuna_20251204" \
  --update-active
```

---

## 3段階ハイブリッド最適化

### Stage 1: シミュレーション（高速探索）
- 試行数: 750
- 所要時間: 約10分
- 目的: 粗い探索で候補を絞り込み

### Stage 2: 軽量バックテスト（中間検証）
- 対象: Stage 1上位候補
- データ: 7日×100%
- 所要時間: 1試行あたり約4分

### Stage 3: フルバックテスト（最終検証）
- 対象: Stage 2上位候補
- データ: 90日×100%
- 所要時間: 1試行あたり約52分

---

## 対応戦略（Phase 60.3）

| 戦略名 | タイプ | 最適化パラメータ |
|--------|--------|------------------|
| ATRBased | レンジ | atr_period, atr_multiplier, rsi_overbought/oversold |
| DonchianChannel | レンジ | period, breakout_threshold |
| ADXTrendStrength | トレンド | adx_period, adx_threshold, trend_strength_threshold |
| BBReversal | レンジ | bb_period, bb_std, bb_width_threshold, rsi_buy/sell_threshold |
| StochasticReversal | トレンド | stoch_period, stoch_overbought/oversold |
| MACDEMACrossover | トレンド | macd_fast/slow/signal, ema_period |

---

## 高度な機能（Phase 60.3）

### Walk-Forward検証

```bash
python3 scripts/optimization/run_github_optimization.py \
  --type hybrid \
  --walk-forward \
  --backtest-days 180
```

- 訓練期間: 120日
- テスト期間: 60日
- ステップ: 30日

### 過学習検出

訓練期間とテスト期間のスコア乖離が20%以上で警告表示。

---

## 結果ファイル

```
config/optimization/results/latest_optimization.json
```

```json
{
  "phase": "hybrid",
  "created_at": "2025-12-04T12:00:00",
  "best_params": {
    "risk.kelly_fraction": 0.15,
    "ml_integration.ml_weight": 0.4,
    ...
  },
  "best_value": 1.25
}
```

---

## トラブルシューティング

### Q: 最適化が途中で停止する

```bash
# タイムアウト延長（環境変数）
OPTUNA_TIMEOUT_SECONDS=21600 python3 scripts/optimization/run_github_optimization.py ...
```

### Q: バックテストデータがない

```bash
# データ収集
python3 src/backtest/scripts/collect_historical_csv.py --days 90

# データ確認
wc -l src/backtest/data/historical/BTC_JPY_*.csv
```

### Q: 結果ファイルが見つからない

```bash
ls -la config/optimization/results/
```

---

## 関連ドキュメント

- `docs/運用ガイド/戦略選定ガイド.md` - 戦略最適化の詳細
- `docs/開発履歴/Phase_60.md` - Phase 60.3分析機能強化
- `docs/開発履歴/Phase_57.md` - Phase 57.6-57.7 Optunaワークフロー
- `config/core/thresholds.yaml` - 最適化対象パラメータ

---

**最終更新**: 2025年12月4日 - Phase 60.3スクリプト整理（13→9ファイル）
