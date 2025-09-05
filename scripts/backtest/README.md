# backtest - バックテスト実行スクリプト群

## 🎯 役割・責任

バックテスト実行のためのスクリプト群を管理し、本番環境に影響を与えずに独立したバックテスト環境でシステムの動作確認・性能評価を提供する。Phase 19 MLOps統合対応により、feature_manager 12特徴量・ProductionEnsemble・週次自動学習システムのバックテスト検証を実現。

## 📂 ファイル構成

```
scripts/backtest/
└── run_backtest.py             # メインバックテスト実行スクリプト（CLI対応・結果表示）
```

## 🔧 主要機能・実装

### **run_backtest.py - バックテスト実行エントリーポイント**

#### **コマンドライン引数処理**
- **--config** - バックテスト設定ファイル指定（デフォルト: config/backtest/base.yaml）
- **--days** - バックテスト期間（日数）（デフォルト: 30日）
- **--symbol** - 取引対象シンボル（デフォルト: BTC/JPY）
- **--initial-balance** - 初期残高（円）（デフォルト: 1,000,000円）
- **--verbose** - 詳細ログ表示フラグ

#### **バックテストエンジン初期化**
- **BacktestEngine生成** - 手数料・スリッページ・最大ポジション比率設定
- **設定読み込み** - cmdline_mode="backtest"でバックテスト専用設定適用
- **ログ初期化** - setup_logging("backtest")・JST対応・構造化出力

#### **実行・結果処理**
- **非同期実行** - asyncio.run()でバックテスト並行処理
- **詳細結果表示** - 取引統計・資産統計・パフォーマンス評価・取引履歴
- **エラーハンドリング** - 例外キャッチ・詳細トレースバック・適切な終了コード

## 📝 使用方法・例

### **基本実行**
```bash
# デフォルト設定（30日間・BTC/JPY・100万円）
python scripts/backtest/run_backtest.py

# 期間指定（60日間）
python scripts/backtest/run_backtest.py --days 60

# 詳細ログ表示
python scripts/backtest/run_backtest.py --verbose
```

### **カスタム設定実行**
```bash
# カスタム設定ファイル使用
python scripts/backtest/run_backtest.py --config config/backtest/custom.yaml

# 異なるシンボル・初期残高
python scripts/backtest/run_backtest.py --symbol ETH/JPY --initial-balance 500000

# 複数オプション組み合わせ
python scripts/backtest/run_backtest.py --days 90 --verbose --initial-balance 2000000
```

### **結果出力例**
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

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python 3.8+** - async/await構文・型ヒント対応
- **依存関係** - src/モジュール・config設定ファイル必須
- **メモリ使用量** - 大量データ処理時は2GB以上推奨

### **データ制約**
- **API制限** - Bitbank API制限（35秒間隔）考慮
- **15分足制限** - 短期間データのみ取得可能
- **最小期間** - 7日未満は推奨しない（データ不足）

### **設定制約**
- **設定ファイル必須** - config/backtest/base.yaml が存在必要
- **モデル要件** - models/production/配下にProductionEnsemble必要
- **本番分離** - 本番設定への影響なし保証

### **パフォーマンス制約**
- **実行時間** - 30日間で約30秒〜2分（データ量・戦略複雑度による）
- **メモリ使用量** - 100MB〜500MB（期間・データ量による）
- **ディスク使用量** - 一時的に10MB〜50MB（ログ・キャッシュ）

## 🔗 関連ファイル・依存関係

### **核心依存関係**
- **`src/backtest/engine.py`** - BacktestEngine実装・メイン処理ロジック
- **`config/backtest/base.yaml`** - バックテスト専用設定・実行パラメータ
- **`src/core/config.py`** - load_config()・設定読み込み機能

### **バックテスト基盤**
- **`src/core/logger.py`** - setup_logging()・JST対応ログ
- **`src/features/feature_generator.py`** - 12特徴量生成・feature_manager統合
- **`models/production/`** - ProductionEnsemble 3モデル（LightGBM/XGBoost/RandomForest）

### **戦略・取引システム**
- **`src/strategies/implementations/`** - 4戦略実装（ATRBased/MochipoyAlert等）
- **`src/trading/risk_manager.py`** - Kelly基準・リスク管理・ポジションサイジング
- **`src/data/data_fetcher.py`** - Bitbank API・データ取得・キャッシュ

### **品質保証**
- **`scripts/testing/checks.sh`** - 654テスト実行・品質チェック（実行前推奨）
- **`tests/unit/test_backtest.py`** - バックテスト機能単体テスト