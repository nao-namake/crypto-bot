# scripts/ - ユーティリティスクリプト・分析ツール

## 📋 概要

**Utility Scripts & Analysis Tools**  
本フォルダは crypto-bot のスタンドアロンスクリプトを管理し、バックテスト結果の可視化、ウォークフォワード分析などの補助ツールを提供します。

## 🎯 主要機能

### **結果可視化**
- エクイティカーブ描画
- 累積損益グラフ
- パフォーマンス可視化
- matplotlib統合

### **ウォークフォワード分析**
- 時系列データの分割検証
- スライディングウィンドウ
- Out-of-sample検証
- 過学習検出

## 📁 ファイル構成

```
scripts/
├── __init__.py         # パッケージ初期化
├── plot_equity.py      # エクイティカーブ描画
└── walk_forward.py     # ウォークフォワード分析
```

## 🔍 各ファイルの役割

### **plot_equity.py**
- バックテスト結果CSVからグラフ生成
- エクイティカーブ（資産推移）可視化
- コマンドライン引数対応
- 複数グラフタイプ対応
- PNG/PDF出力サポート

### **walk_forward.py**
- ウォークフォワードテスト実行
- 学習期間→テスト期間の繰り返し検証
- MLStrategy等の時系列検証
- 結果CSV出力
- パフォーマンス安定性評価

## 🚀 使用方法

### **エクイティカーブ描画**
```bash
# 基本的な使用方法
python scripts/plot_equity.py -c ./results/backtest_results.csv --equity

# 出力ファイル指定
python scripts/plot_equity.py \
    -c ./results/backtest_results.csv \
    -o ./results/equity_curve.png \
    --title "BTC/JPY Strategy Performance"

# 複数メトリクス表示
python scripts/plot_equity.py \
    -c ./results/backtest_results.csv \
    --equity --drawdown --trades
```

### **ウォークフォワード分析**
```bash
# 基本実行
python scripts/walk_forward.py \
    -c ./config/ml_strategy.yml \
    -o ./results/walk_forward_metrics.csv

# カスタムウィンドウ設定
python scripts/walk_forward.py \
    -c ./config/ml_strategy.yml \
    --train-window 1500 \
    --test-window 250 \
    --step 250

# 並列実行
python scripts/walk_forward.py \
    -c ./config/ml_strategy.yml \
    --parallel \
    --workers 4
```

## ⚠️ 課題・改善点

### **ファイル数不足**
- 分析ツールに対してスクリプト数が少ない
- より多様な分析スクリプトが必要
- 統計分析ツールの追加

### **機能拡張余地**
- インタラクティブグラフ
- リアルタイム更新グラフ
- 複数戦略比較ツール
- レポート自動生成

### **統合不足**
- Jupyter Notebook統合
- Webダッシュボード連携
- CI/CD統合
- 自動実行スケジューラー

### **ドキュメント**
- 各スクリプトの詳細な使用例
- パラメータ説明の充実
- 出力形式の仕様書

## 📝 今後の展開

1. **分析スクリプト拡充**
   ```
   scripts/
   ├── visualization/      # 可視化ツール群
   │   ├── plot_equity.py
   │   ├── plot_trades.py
   │   └── plot_features.py
   ├── analysis/          # 分析ツール群
   │   ├── walk_forward.py
   │   ├── monte_carlo.py
   │   └── sensitivity.py
   ├── optimization/      # 最適化ツール群
   │   ├── grid_search.py
   │   └── bayesian_opt.py
   └── reporting/         # レポート生成
       ├── daily_report.py
       └── monthly_summary.py
   ```

2. **高度な分析機能**
   - モンテカルロシミュレーション
   - 感度分析
   - 相関分析
   - リスク分析

3. **自動化・統合**
   - スケジュール実行
   - パイプライン統合
   - 通知システム連携
   - クラウドストレージ連携

4. **インタラクティブ化**
   - Dash/Streamlitアプリ
   - リアルタイムダッシュボード
   - パラメータ調整UI
   - 結果探索ツール