# scripts/backtest/ - バックテスト実行スクリプト

## 🎯 役割・責任

システムの取引戦略とモデルの性能を、本番環境に影響を与えずに検証するためのバックテストスクリプトを管理します。過去の市場データを使用して取引システムの動作確認、性能評価、収益性分析を実行し、戦略改善とリスク管理に必要な詳細な分析データを提供します。

## 📂 ファイル構成

```
scripts/backtest/
├── README.md            # このファイル
└── run_backtest.py      # メインバックテスト実行スクリプト
```

## 📋 主要ファイル・フォルダの役割

### **run_backtest.py**
バックテスト実行のメインエントリーポイントスクリプトです。
- **コマンドライン引数処理**: 期間、シンボル、初期残高、設定ファイル指定
- **バックテストエンジン初期化**: BacktestEngine生成と設定読み込み
- **非同期実行**: asyncio.runによる並行処理での高効率実行
- **詳細結果表示**: 取引統計、資産統計、パフォーマンス評価の表示
- **エラーハンドリング**: 例外処理と適切な終了コード管理
- **設定分離**: config/backtest/設定による本番環境からの完全分離
- 約7.8KBの実装ファイル

### **主要機能と特徴**
- **独立実行環境**: 本番設定に影響しないバックテスト専用設定
- **柔軟な期間指定**: デフォルト30日から任意期間での検証
- **複数シンボル対応**: BTC/JPY、ETH/JPYなど異なる通貨ペアでの検証
- **詳細統計出力**: 勝率、収益率、最大ドローダウン、リスク指標
- **パフォーマンス分析**: 取引あたりの平均利益、シャープレシオ計算
- **ログ統合**: JST時刻での構造化ログ出力

## 📝 使用方法・例

### **基本的なバックテスト実行**
```bash
# デフォルト設定での実行（30日間・BTC/JPY・100万円）
python3 scripts/backtest/run_backtest.py

# 期間指定での実行（60日間）
python3 scripts/backtest/run_backtest.py --days 60

# 詳細ログ表示での実行
python3 scripts/backtest/run_backtest.py --verbose
```

### **カスタム設定での実行**
```bash
# カスタム設定ファイルを使用
python3 scripts/backtest/run_backtest.py --config config/backtest/custom.yaml

# 異なるシンボル・初期残高での実行
python3 scripts/backtest/run_backtest.py --symbol ETH/JPY --initial-balance 500000

# 複数オプションの組み合わせ
python3 scripts/backtest/run_backtest.py \
  --days 90 \
  --verbose \
  --initial-balance 2000000 \
  --symbol BTC/JPY
```

### **長期分析とカスタム設定例**
```bash
# 3ヶ月間の詳細分析
python3 scripts/backtest/run_backtest.py \
  --days 90 \
  --initial-balance 1000000 \
  --config config/backtest/extended.yaml \
  --verbose

# 複数期間での比較分析用スクリプト
for days in 30 60 90; do
  echo "=== $days 日間バックテスト ==="
  python3 scripts/backtest/run_backtest.py --days $days
done
```

### **結果出力の例**
```
🚀 Crypto-Bot バックテスト実行開始
📁 設定ファイル: config/backtest/base.yaml
📅 バックテスト期間: 30日間
💱 対象シンボル: BTC/JPY
💰 初期残高: ¥1,000,000

============================================================
🎯 バックテスト結果サマリー
============================================================
📈 トレード統計:
   総取引数: 15回
   勝率: 60.0%
   総損益: ¥+45,000

💰 資産統計:
   初期残高: ¥1,000,000
   最終残高: ¥1,045,000
   リターン: +4.50%
   最大ドローダウン: 2.30%

📊 パフォーマンス評価:
   平均利益/取引: ¥+3,000
   総合評価: 🥈 良好
```

### **Python APIでの直接実行**
```python
import asyncio
from src.backtest.engine import BacktestEngine
from src.core.config import load_config

# バックテスト設定の読み込み
config = load_config(cmdline_mode="backtest")

# バックテストエンジンの初期化
engine = BacktestEngine(
    initial_balance=1000000,
    commission_rate=0.0012,
    slippage_rate=0.0005
)

# 非同期でのバックテスト実行
async def run_custom_backtest():
    results = await engine.run_backtest(
        symbol="BTC/JPY",
        days=30,
        verbose=True
    )
    return results

# 実行と結果取得
results = asyncio.run(run_custom_backtest())
print(f"総利益: {results['total_profit']}")
print(f"勝率: {results['win_rate']:.1%}")
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python 3.8以上**: async/await構文と型ヒント対応必須
- **依存関係**: srcモジュール群とconfig設定ファイル完全インストール
- **メモリ要件**: 大量データ処理時は2GB以上のメモリ推奨
- **実行場所**: プロジェクトルートディレクトリからの実行必須

### **データ取得制約**
- **API制限**: Bitbank API制限（35秒間隔）の自動考慮
- **データ粒度**: 15分足データでの制約による精度限界
- **最小期間**: 7日未満のテストは推奨しない（データ不足）
- **履歴制限**: 過去データの取得可能期間による制約

### **設定とモデル要件**
- **設定ファイル**: config/backtest/base.yamlの存在必須
- **モデルファイル**: models/production/配下のProductionEnsemble必須
- **戦略実装**: src/strategies/implementations/での戦略定義必須
- **環境分離**: 本番設定への影響完全回避の保証

### **パフォーマンス制約**
- **実行時間**: 30日間で約30秒〜2分（データ量・戦略複雑度による）
- **メモリ使用**: 100MB〜500MB（期間・データ量による）
- **ディスク使用**: 一時ファイルで10MB〜50MB（ログ・キャッシュ）
- **CPU使用**: シングルスレッド実行による計算リソース制限

## 🔗 関連ファイル・依存関係

### **核心バックテストシステム**
- `src/backtest/engine.py`: BacktestEngineメイン実装・処理ロジック
- `config/backtest/base.yaml`: バックテスト専用設定・パラメータ
- `src/core/config.py`: 設定読み込み機能・環境分離

### **データ・特徴量システム**
- `src/data/data_fetcher.py`: Bitbank APIデータ取得・キャッシュ
- `src/features/feature_manager.py`: 特徴量生成・管理システム
- `models/production/`: ProductionEnsembleモデル・予測エンジン

### **取引戦略・リスク管理**
- `src/strategies/implementations/`: 取引戦略実装（ATRBased、MochipoyAlertなど）
- `src/trading/risk_manager.py`: Kelly基準・リスク管理・ポジションサイジング
- `src/trading/order_manager.py`: 注文管理・取引実行シミュレーション

### **ログ・レポートシステム**
- `src/core/logger.py`: ログ設定・JST対応・構造化出力
- `logs/backtest_reports/`: バックテスト結果レポート保存先
- `src/backtest/reporter.py`: バックテスト結果分析・レポート生成

### **品質保証・テスト**
- `tests/unit/test_backtest.py`: バックテスト機能単体テスト
- `scripts/testing/checks.sh`: システム品質チェック（実行前推奨）
- `tests/integration/`: バックテストシステム統合テスト

### **設定ファイル**
- `config/backtest/`: バックテスト専用設定ディレクトリ
- `config/core/`: システム基本設定・特徴量定義
- `config/secrets/`: API認証情報・セキュア設定