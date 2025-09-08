# src/backtest/ - バックテストシステム

## 🎯 役割・責任

取引戦略の検証・性能評価を担当するバックテストシステムです。本番環境に影響を与えることなく、過去のデータを使用して戦略の有効性、リスク特性、収益性を包括的に分析します。機械学習モデル、取引戦略、リスク管理システムの統合検証により、実運用前の品質保証を提供します。

## 📂 ファイル構成

```
src/backtest/
├── README.md               # このファイル
├── __init__.py             # モジュール初期化・公開インターフェース
├── engine.py               # BacktestEngine - メインバックテスト実行エンジン
├── evaluator.py            # BacktestEvaluator - 性能評価・統計分析
└── reporter.py             # BacktestReporter - レポート生成・可視化
```

## 📋 主要ファイル・フォルダの役割

### **engine.py**
バックテストの核心となる実行エンジンです。
- **TradeRecord dataclass**: 取引記録管理・統計分析・レポート生成用
- **BacktestEngine**: メインバックテスト実行・戦略統合・リスク管理
- **戦略統合**: 4戦略（ATR・フィボナッチ・もちぽよアラート・マルチタイムフレーム）
- **リスク管理統合**: Kelly基準・ポジションサイジング・ドローダウン制御
- **データ品質管理**: 欠損値処理・異常値除去・最小データ点数チェック
- **仮想取引実行**: スリッページ・手数料・タイムラグを考慮した現実的なシミュレーション
- 約33.7KBの実装ファイル

### **evaluator.py**
バックテスト結果の包括的な性能評価を担当します。
- **PerformanceMetrics dataclass**: 性能指標データ構造・統計結果管理
- **BacktestEvaluator**: 性能評価・統計分析・リスク指標計算
- **基本指標**: 総取引数・勝率・総損益・リターン率・CAGR・平均利益
- **リスク指標**: 最大ドローダウン・ボラティリティ・シャープレシオ・ソルティーノ比率
- **取引分析**: 平均取引時間・最大連勝連敗・月次リターン・取引分布
- **統計検定**: ブートストラップ・信頼区間・統計的有意性・ロバストネス検証
- 約18.8KBの実装ファイル

### **reporter.py**
バックテスト結果の多形式レポート生成を担当します。
- **BacktestReporter**: 統合レポート生成・可視化・通知システム
- **多形式出力**: CSV・JSON・HTML・マークダウン・Discord通知対応
- **可視化レポート**: エクイティカーブ・ドローダウンチャート・取引分布グラフ
- **比較分析**: 複数戦略比較・期間別パフォーマンス・ベンチマーク比較
- **自動保存**: logs/backtest_reports/配下への日時付きファイル保存
- **Discord統合**: 結果サマリー通知・重要指標アラート・レポートURL配信
- 約36.7KBの実装ファイル

### **__init__.py**
モジュールの公開インターフェースと統合管理を定義します。
- **公開クラス**: BacktestEngine・TradeRecord・BacktestEvaluator・BacktestReporter
- **BacktestDataLoader統合**: data_pipeline.pyからの統合版データローダー
- **バージョン管理**: Phase 18対応・統合システム・重複削除完了
- **依存関係管理**: 循環インポート回避・遅延インポート・インターフェース統一

## 📝 使用方法・例

### **基本的なバックテスト実行**
```python
import asyncio
from datetime import datetime, timedelta
from src.backtest import BacktestEngine, BacktestEvaluator, BacktestReporter

async def run_backtest_example():
    # バックテストエンジン初期化
    engine = BacktestEngine(
        initial_balance=1000000,      # 初期残高（100万円）
        slippage_rate=0.0005,        # スリッページ0.05%
        commission_rate=0.0012       # 手数料0.12%
    )
    
    # バックテスト期間設定
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # バックテスト実行
    results = await engine.run_backtest(
        start_date=start_date,
        end_date=end_date,
        symbol="BTC/JPY"
    )
    
    # 性能評価
    evaluator = BacktestEvaluator()
    metrics = evaluator.evaluate_performance(
        trade_records=results["trade_records"],
        equity_curve=results["equity_curve"],
        initial_balance=1000000
    )
    
    print(f"勝率: {metrics.win_rate:.1%}")
    print(f"リターン: {metrics.total_return:.2%}")
    print(f"最大ドローダウン: {metrics.max_drawdown:.2%}")
    
    return results, metrics

# 実行
results, metrics = asyncio.run(run_backtest_example())
```

### **包括的レポート生成**
```python
# レポート生成
reporter = BacktestReporter()
generated_files = await reporter.generate_full_report(
    test_name="btc_strategy_30days",
    trade_records=results["trade_records"],
    performance_metrics=metrics,
    equity_curve=results["equity_curve"]
)

print("生成されたファイル:")
for format_type, file_path in generated_files.items():
    print(f"  {format_type}: {file_path}")

# Discord通知送信
await reporter.send_discord_summary(
    test_name="btc_strategy_30days",
    metrics=metrics,
    trade_count=len(results["trade_records"])
)
```

### **スクリプト経由実行**
```bash
# メインスクリプト実行（推奨）
python scripts/backtest/run_backtest.py

# カスタム期間・詳細ログ
python scripts/backtest/run_backtest.py --days 60 --verbose

# 特定設定・初期残高指定
python scripts/backtest/run_backtest.py --days 90 --initial-balance 2000000
```

### **性能分析・比較**
```python
# 複数期間での比較分析
periods = [30, 60, 90]
results_comparison = {}

for days in periods:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    results = await engine.run_backtest(start_date, end_date, "BTC/JPY")
    metrics = evaluator.evaluate_performance(
        results["trade_records"], 
        results["equity_curve"], 
        1000000
    )
    
    results_comparison[f"{days}days"] = {
        "win_rate": metrics.win_rate,
        "total_return": metrics.total_return,
        "max_drawdown": metrics.max_drawdown,
        "sharpe_ratio": metrics.sharpe_ratio
    }

# 比較結果表示
for period, metrics in results_comparison.items():
    print(f"{period}: 勝率{metrics['win_rate']:.1%}, "
          f"リターン{metrics['total_return']:.2%}")
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.8以上・async/await対応・型ヒント・dataclass必須
- **メモリ要件**: 大量データ処理時2GB以上推奨・長期バックテスト（6ヶ月）対応
- **処理時間**: 30日間30秒-2分・180日間2-10分（データ量・戦略複雑度による）
- **実行場所**: プロジェクトルートディレクトリからの実行必須・相対パス依存

### **データ品質・制約**
- **API制限**: Bitbank API制限（35秒間隔）考慮・本番取引との競合回避
- **データ粒度**: 15分足制限・長期バックテストには4h足推奨
- **最小期間**: 7日未満非推奨（テクニカル指標計算不足・統計的信頼性不足）
- **データ品質**: 50期間未満・欠損値5%超過時は処理停止・品質保証

### **モデル・設定要件**
- **機械学習統合**: ProductionEnsemble必須・models/production/配下の3モデル
- **特徴量統合**: feature_manager 12特徴量・特徴量順序・型整合性必須
- **設定分離**: config/backtest/専用設定・本番設定への影響完全回避
- **戦略統合**: 4戦略実装必須・戦略間競合解決・信頼度管理

### **本番環境分離制約**
- **完全独立**: 本番設定（config/production/）への影響一切なし
- **データベース分離**: バックテスト結果独立保存・本番データ非影響
- **ログ分離**: logs/backtest_reports/配下独立保存・本番ログ非混入
- **リソース分離**: メモリ・CPU・ネットワーク使用量の本番システム非影響

## 🔗 関連ファイル・依存関係

### **データ・特徴量システム**
- `src/data/data_pipeline.py`: BacktestDataLoader・市場データ取得・キャッシュ
- `src/features/feature_generator.py`: 12特徴量生成・feature_manager連携
- `src/core/config/feature_manager.py`: 特徴量統一管理・順序保証・型安全

### **戦略・取引システム**
- `src/strategies/implementations/`: 4戦略実装（ATR・フィボナッチ・もちぽよ・MTF）
- `src/strategies/base/strategy_manager.py`: 戦略管理・競合解決・統合制御
- `src/trading/risk_manager.py`: Kelly基準・リスク管理・ポジションサイジング

### **機械学習・モデル**
- `models/production/`: ProductionEnsemble・3モデル統合・予測エンジン
- `src/ml/ensemble.py`: モデル統合・予測実行・信頼度評価
- `src/ml/model_manager.py`: モデル管理・バージョン・メタデータ

### **設定・実行基盤**
- `config/backtest/`: バックテスト専用設定・戦略・リスク・モデル設定
- `scripts/backtest/run_backtest.py`: 実行エントリーポイント・CLI・結果表示
- `src/core/orchestration/orchestrator.py`: システム統合制御・バックテスト実行

### **監視・品質保証**
- `src/monitoring/discord_notifier.py`: Discord通知・レポート配信・アラート
- `tests/unit/backtest/test_engine.py`: バックテスト単体テスト・品質保証
- `scripts/testing/checks.sh`: 品質チェック・テスト実行（実行前推奨）

### **ログ・レポート**
- `src/core/logger.py`: JST対応ログ・構造化出力・エラー追跡
- `logs/backtest_reports/`: CSV・JSON・HTML・マークダウンレポート保存
- 外部ライブラリ: pandas・numpy・matplotlib・統計分析・可視化