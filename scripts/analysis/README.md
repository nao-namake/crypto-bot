# Analysis Scripts

**Phase 52.4** - システム評価用分析ユーティリティ

## 📋 概要

このフォルダには、システムの戦略パフォーマンスとレジーム分類精度を評価するための分析スクリプトが含まれています。

**設定管理**: 分析パラメータは`config/core/thresholds.yaml`の`analysis`セクションに定義されています。

---

## 📊 strategy_performance_analysis.py

### 目的
戦略個別パフォーマンスの総合分析・バックテスト評価

### 機能
- 単一戦略のパフォーマンス分析（勝率・損益率・シャープレシオ・最大DD）
- レジーム別パフォーマンス分析（tight_range/normal_range/trending別）
- 戦略間相関分析（相関係数マトリクス）
- アンサンブル貢献度測定（除外時の性能変化）
- レポート生成・JSON出力

### 使用例
```bash
# 基本実行
python scripts/analysis/strategy_performance_analysis.py

# カスタムデータファイル指定
python scripts/analysis/strategy_performance_analysis.py --data-file path/to/data.csv
```

### 出力
- Sharpe比（年率換算）
- 勝率・プロフィットファクター
- 最大ドローダウン
- レジーム別パフォーマンス
- 戦略間相関行列
- アンサンブル貢献度

### 設定
`config/core/thresholds.yaml`:
```yaml
analysis:
  strategy_performance:
    default_data_path: "src/backtest/data/historical/BTC_JPY_4h.csv"
    sharpe_ratio:
      risk_free_rate: 0.0
      annualization_factor: 365
    backtest:
      min_data_rows: 100
      warmup_rows: 50
      fixed_position_size: 0.01
      min_regime_data: 50
    deletion_criteria:
      win_rate_threshold: 0.5
      correlation_threshold: 0.7
      contribution_threshold: 0.0
```

### ユースケース
- 新戦略候補の評価
- レジーム別戦略パフォーマンス比較
- 冗長戦略の特定（高相関・低貢献度）
- アンサンブル最適化の判断材料

---

## 🎯 verify_regime_classification.py

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
- 目標達成確認（✅/⚠️）
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

## 🔧 開発・保守

### 依存関係
- `src/strategies/strategy_loader.py`: 動的戦略読み込み
- `src/core/services/market_regime_classifier.py`: レジーム分類
- `src/features/feature_generator.py`: 特徴量生成
- `src/backtest/reporter.py`: TradeTracker

### テスト
```bash
# strategy_performance_analysis.pyのテスト
pytest tests/unit/analysis/test_strategy_performance_analysis.py

# verify_regime_classification.pyのテスト
# （テストファイル未作成 - 今後追加推奨）
```

### 設定変更時の注意
- `thresholds.yaml`の`analysis`セクション変更時は、対応するスクリプトの動作確認を推奨
- デフォルトパス変更時は、データファイルの存在確認必須
- 閾値変更時は、バックテスト結果への影響を確認

---

## 📝 履歴

- **Phase 52.4** (2025-11-15):
  - コード整理（extract_regime_stats.py, strategy_theoretical_analysis.py削除）
  - ハードコード撲滅（thresholds.yaml参照に変更）
  - README.md追加

- **Phase 51.7**: strategy_performance_analysis.pyを動的戦略ロードに対応

- **Phase 51.2**: verify_regime_classification.py追加

---

**最終更新**: 2025-11-15 (Phase 52.4)
