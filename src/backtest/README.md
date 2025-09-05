# backtest - バックテストシステム

## 🎯 役割・責任

本番環境に影響を与えずに独立したバックテスト環境で戦略の性能評価・検証を提供する。Phase 19 MLOps統合により、feature_manager 12特徴量統一・ProductionEnsemble 3モデル統合・654テスト品質保証・週次自動学習システムのバックテスト検証を実現。

## 📂 ファイル構成

```
src/backtest/
├── __init__.py             # モジュール初期化・公開インターフェース定義
├── engine.py               # BacktestEngine - メインバックテスト実行エンジン（605行）
├── evaluator.py            # BacktestEvaluator - 性能評価・統計分析（535行）
├── reporter.py             # BacktestReporter - 統合レポート生成（916行）
└── README.md               # このファイル・Phase 19 MLOps統合対応
```

## 🔧 主要機能・実装

### **engine.py - バックテストエンジン**
- **独立実行環境** - 本番設定に影響しない完全分離バックテスト
- **戦略統合実行** - 4戦略（ATRBased/MochipoyAlert/MultiTimeframe/FibonacciRetracement）
- **リスク管理統合** - Kelly基準・ポジションサイジング・ドローダウン制御
- **データ品質管理** - 自動補完・異常値除去・最小データ点数チェック

### **evaluator.py - 性能評価システム**
- **基本指標** - 総取引数・勝率・総損益・リターン率・CAGR
- **リスク指標** - 最大ドローダウン・ボラティリティ・シャープレシオ・ソルティーノ比率
- **取引分析** - 平均取引時間・最大連勝/連敗・月次リターン分析
- **統計検定** - ブートストラップ・信頼区間・統計的有意性検定

### **reporter.py - 統合レポート生成**
- **多形式出力** - CSV・JSON・HTML・マークダウン・Discord通知
- **可視化レポート** - エクイティカーブ・ドローダウンチャート・取引分布
- **比較分析** - 複数戦略比較・期間別パフォーマンス・統計サマリー
- **自動保存** - logs/backtest_reports/配下に日時付きファイル保存

## 📝 使用方法・例

### **基本的なバックテスト実行**
```python
import asyncio
from datetime import datetime, timedelta
from src.backtest import BacktestEngine, BacktestEvaluator, BacktestReporter

async def run_basic_backtest():
    # 1. バックテストエンジン初期化
    engine = BacktestEngine(
        initial_balance=1000000,    # 初期残高（100万円）
        slippage_rate=0.0005,      # スリッページ0.05%
        commission_rate=0.0012     # 手数料0.12%（Bitbank）
    )
    
    # 2. バックテスト期間設定
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # 30日間
    
    # 3. バックテスト実行
    results = await engine.run_backtest(
        start_date=start_date,
        end_date=end_date,
        symbol="BTC/JPY"
    )
    
    # 4. 性能評価
    evaluator = BacktestEvaluator()
    metrics = evaluator.evaluate_performance(
        trade_records=results["trade_records"],
        equity_curve=results["equity_curve"],
        initial_balance=1000000
    )
    
    print(f"✅ バックテスト完了: 勝率{metrics.win_rate:.1%}, リターン{metrics.total_return:.2%}")
    return results

# 実行
asyncio.run(run_basic_backtest())
```

### **統合レポート生成**
```python
# レポート生成
reporter = BacktestReporter()
generated_files = await reporter.generate_full_report(
    test_name="btc_strategy_test",
    trade_records=results["trade_records"],
    performance_metrics=metrics,
    equity_curve=results["equity_curve"]
)

print(f"📁 生成ファイル: {list(generated_files.keys())}")
# ['csv', 'json', 'html'] 形式で生成
```

### **スクリプト経由実行**
```bash
# メインスクリプト実行（推奨）
python scripts/backtest/run_backtest.py

# カスタム期間・詳細ログ
python scripts/backtest/run_backtest.py --days 60 --verbose
```

## ⚠️ 注意事項・制約

### **実行環境制約**
- **Python 3.8+必須** - async/await構文・型ヒント・dataclass対応
- **メモリ要件** - 大量データ処理時2GB以上推奨（6ヶ月データ）
- **処理時間** - 30日間：30秒〜2分、180日間：2〜10分（データ量・戦略による）

### **データ制約**
- **API制限考慮** - Bitbank API制限（35秒間隔）・本番トレードとの競合回避
- **15分足制限** - 短期間データのみ取得可能・長期バックテストには4h足推奨
- **最小期間** - 7日未満は推奨しない（テクニカル指標計算不足）
- **データ品質** - 50期間未満・欠損値5%超過時は処理停止

### **モデル・設定制約**
- **ProductionEnsemble必須** - models/production/配下に3モデル（LightGBM/XGBoost/RandomForest）必要
- **12特徴量統一** - feature_manager統合・特徴量順序・型整合性必須
- **設定分離** - config/backtest/base.yamlでバックテスト専用設定使用

### **本番環境分離**
- **完全独立実行** - 本番設定（config/production/）に一切影響なし
- **データベース分離** - バックテスト結果は独立保存・本番データ影響なし
- **ログ分離** - logs/backtest_reports/配下に独立保存

## 🔗 関連ファイル・依存関係

### **設定・実行基盤**
- **`config/backtest/base.yaml`** - バックテスト専用設定・モード・戦略・リスク管理
- **`scripts/backtest/run_backtest.py`** - 実行エントリーポイント・CLI対応・結果表示
- **`src/core/config/feature_manager.py`** - 12特徴量統一管理・特徴量順序保証

### **データ・モデル基盤**
- **`src/data/data_fetcher.py`** - Bitbank API・データ取得・キャッシュ機能
- **`models/production/`** - ProductionEnsemble 3モデル（LightGBM/XGBoost/RandomForest）
- **`src/features/feature_generator.py`** - 12特徴量生成・feature_manager連携

### **戦略・取引システム**
- **`src/strategies/implementations/`** - 4戦略実装（ATRBased/MochipoyAlert/MultiTimeframe/FibonacciRetracement）
- **`src/trading/risk_manager.py`** - Kelly基準・リスク管理・ポジションサイジング
- **`src/core/orchestration/orchestrator.py`** - システム統合制御・バックテスト直接実行

### **監視・品質保証**
- **`src/monitoring/`** - Discord通知・ヘルスチェック・パフォーマンス監視
- **`scripts/testing/checks.sh`** - 654テスト実行・品質チェック（実行前推奨）
- **`tests/unit/backtest/`** - バックテスト機能単体テスト・統合テスト

### **ログ・レポート**
- **`src/core/logger.py`** - JST対応ログ・構造化出力・Discord統合
- **`logs/backtest_reports/`** - CSV・JSON・HTML・マークダウンレポート保存先