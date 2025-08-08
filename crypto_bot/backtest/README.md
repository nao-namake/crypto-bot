# backtest/ - バックテストエンジン・評価システム

## 📋 概要

**Backtesting Engine & Performance Evaluation System**  
本フォルダは crypto-bot のバックテスト機能を提供し、過去データを使用した取引戦略のシミュレーション、パフォーマンス評価、最適化を担当します。

## 🎯 主要機能

### **バックテストエンジン**
- 過去データでの取引シミュレーション実行
- ポジション管理・損益計算
- 手数料・スリッページ考慮
- 詳細な取引記録生成

### **パフォーマンス評価**
- 各種メトリクス計算（シャープレシオ、最大ドローダウン等）
- ウォークフォワード分析
- 統計的有意性検証
- レポート生成

### **最適化機能**
- パラメータ最適化
- マルチプロセス並列処理
- グリッドサーチ・ベイズ最適化対応

## 📁 ファイル構成

```
backtest/
├── __init__.py              # パッケージ初期化
├── engine.py                # バックテストエンジン本体
├── jpy_enhanced_engine.py   # JPY建て取引特化エンジン
├── metrics.py               # 評価指標計算・データ分割
├── analysis.py              # 分析・レポート生成
└── optimizer.py             # パラメータ最適化
```

## 🔍 各ファイルの役割

### **engine.py**
- `BacktestEngine`クラス - メインのバックテストエンジン
- `TradeRecord`データクラス - 取引記録管理
- ポジション管理・エントリー/エグジット実行
- 資産推移トラッキング
- CSVレポート出力

### **jpy_enhanced_engine.py**
- `JPYEnhancedBacktestEngine`クラス - JPY建て特化版
- Bitbank手数料体系対応
- 信用取引・建玉金利考慮
- 日本時間ベースの処理
- メイカー/テイカー手数料最適化

### **metrics.py**
- `split_walk_forward()` - ウォークフォワード分割
- `calculate_max_drawdown()` - 最大ドローダウン計算
- `calculate_sharpe_ratio()` - シャープレシオ計算
- `calculate_cagr()` - 年率換算リターン計算
- その他統計指標計算関数

### **analysis.py**
- バックテスト結果の詳細分析
- 期間別パフォーマンス集計
- 勝率・プロフィットファクター計算
- ビジュアライゼーション（チャート生成）

### **optimizer.py**
- `BacktestOptimizer`クラス - パラメータ最適化
- グリッドサーチ実装
- 並列処理対応
- 最適パラメータ探索

## 🚀 使用方法

### **基本的なバックテスト実行**
```python
from crypto_bot.backtest.engine import BacktestEngine

# エンジン初期化
engine = BacktestEngine(
    initial_balance=10000,
    strategy=strategy,
    risk_manager=risk_manager,
    fee_rate=0.0012
)

# バックテスト実行
results = engine.run(df)

# レポート出力
engine.save_report("results/backtest_report.csv")
```

### **JPY建て取引のバックテスト**
```python
from crypto_bot.backtest.jpy_enhanced_engine import JPYEnhancedBacktestEngine

engine = JPYEnhancedBacktestEngine(
    initial_balance=10000,
    bitbank_fee_config={
        "maker_fee": -0.0002,
        "taker_fee": 0.0012
    }
)
```

### **ウォークフォワード分析**
```python
from crypto_bot.backtest.metrics import split_walk_forward

splits = split_walk_forward(
    df=data_df,
    train_window=1500,
    test_window=250,
    step=250
)
```

## ⚠️ 課題・改善点

### **パフォーマンス最適化**
- 大規模データでの処理速度改善必要
- メモリ使用量の最適化
- ベクトル化処理の拡充

### **機能拡張**
- モンテカルロシミュレーション実装
- より高度な統計分析機能
- リアルタイムバックテスト対応

### **ファイル統合の可能性**
- `analysis.py`と`metrics.py`の機能重複
- 統合してより整理された構造に

### **ドキュメント強化**
- 各メトリクスの計算式明確化
- バックテスト設定のベストプラクティス
- よくある落とし穴の警告

## 📝 今後の展開

1. **高速化対応**
   - Numba/Cython活用
   - GPU計算対応
   - 分散処理フレームワーク統合

2. **機能拡張**
   - ポートフォリオバックテスト
   - マルチアセット対応
   - より詳細なリスク分析

3. **可視化強化**
   - インタラクティブダッシュボード
   - リアルタイムプロット
   - 3Dビジュアライゼーション

4. **検証機能強化**
   - オーバーフィッティング検出
   - 統計的有意性テスト自動化
   - ロバスト性検証