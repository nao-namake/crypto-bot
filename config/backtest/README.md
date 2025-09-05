# backtest - バックテスト専用設定管理

## 🎯 役割・責任

バックテスト専用の設定ファイル群を管理し、本番環境に影響を与えずにバックテスト実行環境を提供する。Phase 19 MLOps統合対応により、feature_manager 12特徴量統一・ProductionEnsemble連携・週次自動学習に対応したバックテスト環境を構築。

## 📂 ファイル構成

```
config/backtest/
├── base.yaml                   # メイン設定（取引所・ML・戦略・監視設定統合）
├── feature_order.json          # 12特徴量統一定義（Phase 19 MLOps統合版）
└── thresholds.yaml             # 動的閾値・パラメータ管理（運用時調整可能）
```

## 🔧 主要機能・実装

### **base.yaml - バックテスト基本設定**
- **mode: backtest** - バックテスト専用モード設定
- **exchange設定** - bitbank信用取引・1倍レバレッジ・API制限35秒
- **ML設定** - confidence_threshold: 0.65・ProductionEnsemble有効
- **戦略設定** - 4戦略統合（ATRBased/MochipoyAlert/MultiTimeframe/FibonacciRetracement）
- **リスク管理** - Kelly基準・1%リスク・20%最大DD・ATR損切り

### **feature_order.json - 12特徴量統一管理**
- **Phase 19 MLOps統合** - feature_manager統一特徴量定義
- **6カテゴリ分類** - basic/momentum/volatility/trend/volume/anomaly
- **97→12特徴量厳選** - importance_based_selection・87.6%削減
- **ProductionEnsemble連携** - 3モデル統合対応・型安全性保証

### **thresholds.yaml - 動的閾値管理**
- **ML閾値** - confidence階層・フォールバック設定・予測失敗対応
- **取引閾値** - Kelly基準・ポジションサイジング・リスク管理
- **監視閾値** - ヘルスチェック・エラー検知・Discord通知設定
- **API閾値** - タイムアウト・リトライ・レート制限管理

## 📝 使用方法・例

### **バックテスト設定読み込み**
```python
from src.core.config import load_config

# バックテスト専用設定で初期化
config = load_config("config/backtest/base.yaml", cmdline_mode="backtest")
print(f"モード: {config.mode}")  # backtest

# 特徴量定義確認
feature_manager = FeatureManager()
features = feature_manager.get_feature_order()
print(f"特徴量数: {len(features)}")  # 12
```

### **バックテスト実行**
```bash
# デフォルト30日間バックテスト
python scripts/backtest/run_backtest.py

# カスタム期間・詳細ログ
python scripts/backtest/run_backtest.py --days 60 --verbose

# カスタム設定ファイル
python scripts/backtest/run_backtest.py --config config/backtest/base.yaml
```

### **閾値動的取得**
```python
from src.core.config import get_threshold

# ML信頼度閾値
confidence = get_threshold("ml.default_confidence", 0.5)

# 取引実行間隔
interval = get_threshold("execution.paper_mode_interval_seconds", 60)

# リスク管理閾値
max_dd = get_threshold("position_management.drawdown.max_ratio", 0.20)
```

## ⚠️ 注意事項・制約

### **本番環境分離**
- **独立実行** - 本番設定（config/production/）に一切影響なし
- **データベース分離** - バックテスト結果は独立保存
- **API制限考慮** - 35秒間隔・本番トレードとの競合回避

### **データ制約**
- **15分足制限** - Bitbank API制限により短期間データのみ取得可能
- **最小データ量** - 50期間未満は処理停止
- **欠損値処理** - 5%まで許容・超過時はエラー

### **MLモデル制約**
- **ProductionEnsemble必須** - models/production/配下に3モデル必要
- **フォールバック対応** - モデル未発見時はダミー予測（停止推奨）
- **特徴量整合性** - 12特徴量完全一致が必須

## 🔗 関連ファイル・依存関係

### **核心依存関係**
- **`src/core/config/feature_manager.py`** - 12特徴量統一管理・特徴量順序保証
- **`models/production/`** - ProductionEnsemble 3モデル（LightGBM/XGBoost/RandomForest）
- **`src/backtest/engine.py`** - BacktestEngine実装・この設定を参照

### **実行スクリプト**
- **`scripts/backtest/run_backtest.py`** - バックテスト実行エントリーポイント
- **`scripts/testing/checks.sh`** - 品質チェック・バックテスト前実行推奨

### **監視・ログ**
- **`src/monitoring/`** - Discord通知・ヘルスチェック設定参照
- **`src/core/logger.py`** - JST対応ログ・構造化出力設定

### **戦略・取引**
- **`src/strategies/implementations/`** - 4戦略実装（設定参照）
- **`src/trading/risk_manager.py`** - Kelly基準・リスク管理設定適用