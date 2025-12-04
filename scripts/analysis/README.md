# Analysis Scripts

**Phase 60.3** - システム評価用分析ユーティリティ

## 概要

このフォルダには、システムの戦略パフォーマンスとレジーム分類精度を評価するための分析スクリプトが含まれています。

**設定管理**: 分析パラメータは`config/core/thresholds.yaml`の`analysis`セクションに定義されています。

## クイックスタート

```bash
# 推奨: 包括的戦略評価（全6戦略を一括評価）
python scripts/analysis/comprehensive_strategy_evaluation.py --days 30

# 特定の戦略のみ評価
python scripts/analysis/comprehensive_strategy_evaluation.py --days 30 --strategy ATRBased

# 結果をファイル出力
python scripts/analysis/comprehensive_strategy_evaluation.py --days 30 --export ./output
```

---

## スクリプト一覧（4ファイル）

| スクリプト | 用途 | 推奨度 |
|-----------|------|--------|
| `comprehensive_strategy_evaluation.py` | 全戦略の包括的評価（統合版） | 推奨 |
| `advanced_trade_analysis.py` | 時間帯・曜日分析・可視化 | 補完 |
| `strategy_hold_analysis.py` | ADX分布・閾値シミュレーション | 専門 |
| `verify_regime_classification.py` | レジーム分類精度検証 | ユーティリティ |

---

## comprehensive_strategy_evaluation.py（推奨）

### 目的
全6戦略を単体で詳細評価し、改善ポイントを特定する包括的分析ツール。
既存の分析スクリプト機能を統合した統一インターフェース。

### 機能
- 戦略単体バックテスト（勝率・PF・シャープレシオ・最大DD）
- シグナル分布分析（BUY/SELL/HOLD率・HOLD理由）
- ADX/RSI/Stochastic条件達成率
- 市場条件分析（ADX分布）
- 総合スコア算出（0-100点）
- 改善提案の自動生成
- **[Phase 60.3]** レジーム別パフォーマンス分析
- **[Phase 60.3]** 戦略間相関分析
- **[Phase 60.3]** アンサンブル貢献度測定（Leave-One-Out法）

### 使用例
```bash
# 30日分のデータで全戦略を評価
python scripts/analysis/comprehensive_strategy_evaluation.py --days 30

# 特定の戦略のみ評価
python scripts/analysis/comprehensive_strategy_evaluation.py --days 30 --strategy StochasticReversal

# 結果をファイル出力
python scripts/analysis/comprehensive_strategy_evaluation.py --days 30 --export ./output
```

### 出力例
```
戦略別サマリー
--------------------------------------------------------------------------------
戦略名                    |     勝率 |    PF |   取引数 |   HOLD率 |   スコア
--------------------------------------------------------------------------------
DonchianChannel           |  41.5% |  1.86 |     118 |   26.4% |    80.1
ADXTrendStrength          |  37.1% |  2.72 |      35 |    2.4% |    73.5
MACDEMACrossover          |  60.0% |  3.44 |       5 |   88.8% |    70.1
ATRBased                  |  51.5% |  0.49 |      33 |   39.2% |    68.1
BBReversal                |  53.8% |  0.54 |      26 |   72.0% |    59.5
StochasticReversal        |  18.2% |  0.12 |      11 |   86.4% |    33.8

レジーム別パフォーマンス:
  tight_range: 勝率 48.1%, 12取引
  normal_range: 勝率 55.2%, 28取引
  trending: 勝率 58.7%, 8取引

戦略間相関:
  ATRBased vs DonchianChannel: 0.32
  ATRBased vs ADXTrendStrength: 0.18
  ...

アンサンブル貢献度: +8.5%
```

### ユースケース
- 戦略パラメータ調整後の効果検証
- HOLD率が高い戦略の原因特定
- 新戦略追加前の既存戦略評価
- Phase間の性能比較
- 冗長戦略の特定（高相関・低貢献度）
- レジーム別の戦略適性評価

---

## advanced_trade_analysis.py

### 目的
時間帯・曜日別の取引パターン分析とmatplotlib可視化

### 機能
- 時間帯別パフォーマンス分析
- 曜日別パフォーマンス分析
- 取引分布可視化（matplotlib）
- エクイティカーブ生成

### 使用例
```bash
python scripts/analysis/advanced_trade_analysis.py --days 30
python scripts/analysis/advanced_trade_analysis.py --days 30 --export ./output
```

---

## strategy_hold_analysis.py

### 目的
ADX値の分布分析・閾値変更シミュレーション・条件達成率計算

### 機能
- ADX値の分布統計
- 閾値変更時のシミュレーション
- 条件達成率の計算
- HOLD理由の詳細分類

### 使用例
```bash
python scripts/analysis/strategy_hold_analysis.py --days 30
python scripts/analysis/strategy_hold_analysis.py --days 30 --export
```

---

## verify_regime_classification.py

### 目的
MarketRegimeClassifierの分類精度検証・システムヘルスチェック

### 機能
- 履歴データ全体のレジーム分類
- レジーム分布統計の算出
- 目標範囲との比較（自動判定）
- ランダムサンプル表示（手動検証）

### 使用例
```bash
# 全データで検証
python scripts/analysis/verify_regime_classification.py

# 行数制限（テスト用）
python scripts/analysis/verify_regime_classification.py --limit-rows 1000
```

### 出力
- レジーム分布統計（tight_range/normal_range/trending/high_volatility）
- 目標達成確認
- ランダムサンプル詳細（価格・ATR・ADX・EMA等）

### 設定
`config/core/thresholds.yaml`:
```yaml
analysis:
  regime_verification:
    default_data_path: "src/backtest/data/historical/BTC_JPY_4h.csv"
    sample_size: 50
    target_ranges:
      range_market: {min: 70, max: 80}
      trending_market: {min: 15, max: 20}
      high_volatility: {min: 5, max: 10}
```

### ユースケース
- レジーム分類器のヘルスチェック
- レジーム閾値調整の効果検証
- 市場環境変化の検出
- レジーム分類ドリフトの監視

---

## 開発・保守

### 依存関係
- `src/strategies/strategy_loader.py`: 動的戦略読み込み
- `src/core/services/market_regime_classifier.py`: レジーム分類
- `src/features/feature_generator.py`: 特徴量生成
- `src/backtest/reporter.py`: TradeTracker

### 設定変更時の注意
- `thresholds.yaml`の`analysis`セクション変更時は、対応するスクリプトの動作確認を推奨
- デフォルトパス変更時は、データファイルの存在確認必須
- 閾値変更時は、バックテスト結果への影響を確認

---

## 履歴

- **Phase 60.3** (2025-12-04):
  - スクリプト整理（6 -> 4ファイル）
  - `strategy_signal_analyzer.py` 削除（機能重複）
  - `strategy_performance_analysis.py` 削除（機能統合）
  - `comprehensive_strategy_evaluation.py` にレジーム別・相関・貢献度分析を統合

- **Phase 59.4** (2025-12-03):
  - `comprehensive_strategy_evaluation.py` 追加（包括的戦略評価統合版）
  - `strategy_hold_analysis.py` 追加（ADX分布・閾値シミュレーション）

- **Phase 55.7** (2025-11-21):
  - `strategy_signal_analyzer.py` 追加（シグナル分布分析）

- **Phase 52.4** (2025-11-15):
  - コード整理（extract_regime_stats.py, strategy_theoretical_analysis.py削除）
  - ハードコード撲滅（thresholds.yaml参照に変更）
  - README.md追加

- **Phase 51.7**: strategy_performance_analysis.pyを動的戦略ロードに対応

- **Phase 51.2**: verify_regime_classification.py追加

---

**最終更新**: 2025-12-04 (Phase 60.3)
