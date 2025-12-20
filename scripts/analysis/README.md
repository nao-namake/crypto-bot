# 戦略分析スクリプト

## 概要

このディレクトリには、取引戦略の分析・評価ツールが含まれています。

## メインスクリプト

### unified_strategy_analyzer.py

統合戦略分析スクリプト。5つの旧スクリプトの機能を統合した包括的な分析ツール。

#### 基本使用法

```bash
# 60日分析（デフォルト: quickモード）
python scripts/analysis/unified_strategy_analyzer.py --days 60

# 30日分析
python scripts/analysis/unified_strategy_analyzer.py --days 30
```

#### 分析モード

| モード | 内容 | 所要時間 |
|--------|------|----------|
| `quick` | 基本メトリクス・バックテスト | 約30秒 |
| `full` | 全分析（時間帯別・連敗・相関） | 約3分 |
| `regime-only` | レジーム分類精度のみ | 約10秒 |

```bash
# quickモード（デフォルト）
python scripts/analysis/unified_strategy_analyzer.py --days 60 --mode quick

# fullモード
python scripts/analysis/unified_strategy_analyzer.py --days 60 --mode full

# レジーム分類のみ
python scripts/analysis/unified_strategy_analyzer.py --days 60 --mode regime-only
```

#### 特定戦略の分析

```bash
# ATRBasedのみ分析
python scripts/analysis/unified_strategy_analyzer.py --days 60 --strategy ATRBased

# StochasticReversalのみ分析
python scripts/analysis/unified_strategy_analyzer.py --days 60 --strategy StochasticReversal
```

#### 出力形式

```bash
# コンソール出力のみ（デフォルト）
python scripts/analysis/unified_strategy_analyzer.py --days 60

# JSON出力
python scripts/analysis/unified_strategy_analyzer.py --days 60 --export ./output --format json

# Markdown出力
python scripts/analysis/unified_strategy_analyzer.py --days 60 --export ./output --format md

# 全形式出力
python scripts/analysis/unified_strategy_analyzer.py --days 60 --export ./output --format all
```

#### 出力例

```
================================================================================
統合戦略分析レポート
================================================================================

分析日時: 2025-12-21 08:15:27
分析期間: 60日
分析モード: quick
データポイント: 5,748

----------------------------------------
レジーム分布
----------------------------------------
  tight_range:         0 (  0.0%)
  normal_range:    5,748 (100.0%)
  trending:            0 (  0.0%)
  high_volatility:     0 (  0.0%)

----------------------------------------
戦略別パフォーマンス
----------------------------------------
戦略                      取引数      勝率     PF         損益    スコア
------------------------------------------------------------
ATRBased             322   44.7%  1.03     +6,375円    50
DonchianChannel      294   44.2%  1.03     +7,855円    50
StochasticReversal   177   45.8%  1.10    +13,236円    45
MACDEMACrossover      49   49.0%  1.42    +14,629円    40
ADXTrendStrength     111   42.3%  0.92     -7,384円    35
BBReversal            93   47.3%  1.16    +11,231円    35
```

---

### strategy_theoretical_analysis.py

設定駆動型の理論分析ツール（独立維持）。
strategies.yamlの設定値に基づく理論的な分析を行います。

```bash
python scripts/analysis/strategy_theoretical_analysis.py
```

---

## アーカイブ（archive/）

統合前の旧スクリプト。参照用に保持。

| ファイル | 旧機能 |
|---------|--------|
| `comprehensive_strategy_evaluation.py` | 包括的評価（時間帯別・連敗・感度） |
| `strategy_performance_analysis.py` | 基本メトリクス・削除候補特定 |
| `extract_regime_stats.py` | ログからレジーム統計抽出 |
| `verify_regime_classification.py` | レジーム分類精度検証 |

---

## 分析指標

| 指標 | 説明 |
|------|------|
| **取引数** | 期間中の総取引回数 |
| **勝率** | 勝ちトレード / 総トレード |
| **PF** | プロフィットファクター（総利益 / 総損失） |
| **損益** | 期間中の累積損益（円） |
| **スコア** | 総合評価スコア（0-100） |
| **シャープレシオ** | リスク調整後リターン |
| **最大DD** | 最大ドローダウン |

---

## 削除候補の判定基準

- PF < 0.9
- 全レジームで勝率 < 50%
- 最大DD > 50,000円
- 取引数 < 10

---

## 注意事項

- PYTHONPATH設定が必要: `PYTHONPATH=/Users/nao/Desktop/bot python3 ...`
- データは `src/backtest/data/historical/BTC_JPY_15m.csv` から読み込み
- 分析期間はCSVデータの範囲内で指定
