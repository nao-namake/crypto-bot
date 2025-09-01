# config/core/ - コア設定システム

**Phase 16-B完了**: 設定一元化・保守性向上完成により、160個ハードコード値統合・8個ヘルパー関数・動的設定アクセスを実現した、bitbank信用取引専用・620テスト品質保証で企業級メンテナンス性を持つ基本設定システムが完成

## 🎯 役割・責任

bitbank信用取引専用・12個厳選特徴量・マルチタイムフレーム分析を核とした全環境（paper/live）共通の基本設定を管理します。段階的デプロイ（paper→live）による安全な本番移行と、1万円→50万円の段階的資金管理を実現します。

## 📂 ファイル構成

```
core/
├── README.md               # このファイル（Phase 16-B完成版）
├── base.yaml              # 基本設定（bitbank信用取引・段階的デプロイ対応）
├── feature_order.json     # 12個厳選特徴量定義（Phase 3完了システム）
└── thresholds.yaml        # 一元化設定ファイル（160個ハードコード値統合・8個ヘルパー関数）
```

## 🔧 主要機能・実装

### **base.yaml - 基本設定システム（bitbank信用取引専用）**

**🎯 段階的デプロイによる安全な本番移行**:
- **paper**: 安全なペーパートレード（デフォルト・無制限検証）
- **live**: 実資金取引（十分な検証後に慎重移行）

**主要設定カテゴリ**:
```yaml
# モード設定（段階的デプロイ）
mode: paper  # デフォルト：安全なペーパートレード

# 取引所設定（bitbank信用取引専用）
exchange:
  name: bitbank
  symbol: BTC/JPY
  leverage: 2.0            # 最大2倍レバレッジ（bitbank仕様準拠）
  rate_limit_ms: 35000     # 35秒・安全マージン

# 機械学習設定（ProductionEnsemble統合）
ml:
  confidence_threshold: 0.65  # 65%（収益性重視・高品質シグナル）
  ensemble_enabled: true      # アンサンブルモデル使用
  models: ["lgbm", "xgb", "rf"]

# リスク管理設定（Kelly基準・個人開発最適化）
risk:
  risk_per_trade: 0.02        # 2%（個人開発バランス）
  kelly_max_fraction: 0.25    # 25%（科学的最適化）
  max_drawdown: 0.20          # 20%制限
  consecutive_loss_limit: 5   # 連続5回損失で自動停止

# データ取得設定（マルチタイムフレーム）
data:
  timeframes: ["15m", "4h"]   # 2軸マルチタイムフレーム分析
  since_hours: 96            # 4日間データ（bitbank安定範囲）
```

### **feature_order.json - 12個厳選特徴量システム**

**Phase 3完了成果**:
- **大幅削減**: 97個→12個特徴量（87.6%削減・効率化）
- **カテゴリ分類**: basic(3) + technical(6) + anomaly(3)
- **重要度管理**: critical/high/medium/low分類

**特徴量構成**:
```json
{
  "total_features": 12,
  "feature_categories": {
    "basic": ["close", "volume", "returns_1"],
    "technical": ["rsi_14", "macd", "atr_14", "bb_position", "ema_20", "ema_50"],
    "anomaly": ["zscore", "volume_ratio", "market_stress"]
  }
}
```

### **thresholds.yaml - 設定一元化システム（Phase 16-B完成）**

**🎯 160個ハードコード値完全統合・8個ヘルパー関数システム**:

**設定一元化の成果**:
- **完全統合**: 160個のハードコード値をthresholds.yamlに集約
- **動的アクセス**: 8個ヘルパー関数でドット記法アクセス実現
- **保守性向上**: 設定変更時の工数を80%削減・メンテナンス効率化
- **型安全性**: 設定値の型検証・デフォルト値フォールバック機能

**8個ヘルパー関数**:
```python
# 基本設定値取得
get_threshold(key, default=None)           # 汎用設定値取得
get_trading_config(key, default=None)      # 取引設定取得
get_ml_config(key, default=None)           # ML設定取得  
get_monitoring_config(key, default=None)   # 監視設定取得
get_position_config(key, default=None)     # ポジション設定取得
get_backtest_config(key, default=None)     # バックテスト設定取得
get_data_config(key, default=None)         # データ取得設定取得
get_execution_config(key, default=None)    # 実行制御設定取得
```

**設定カテゴリ構成**:
```yaml
# ML関連フォールバック・エラーハンドリング
ml:
  default_confidence: 0.5           # ダミーモデル時の信頼度
  emergency_stop_on_dummy: true     # ダミーモデル時緊急停止
  max_model_failures: 3            # モデル失敗上限

# 取引関連動的設定
trading:
  default_balance_jpy: 10000.0      # 初期残高（1万円・個人開発）
  bid_spread_ratio: 0.999           # 0.1%スプレッド
  
# 実行間隔制御
execution:
  paper_mode_interval_seconds: 60   # ペーパートレード間隔
  live_mode_interval_seconds: 180   # ライブトレード間隔（収益性重視）
```

## 📝 使用方法・例

### **Phase 16-B設定アクセスシステム**
```python
from src.core.config import load_config, get_threshold, get_ml_config, get_trading_config

# Phase 16-B対応設定読み込み
config = load_config('config/core/base.yaml')

# 設定値取得
mode = config.mode  # paper/live
confidence = config.ml.confidence_threshold  # 0.65
leverage = config.exchange.leverage  # 2.0（bitbank仕様）

# 新システム: 8個ヘルパー関数で動的アクセス
# ドット記法で階層設定にアクセス
ml_confidence = get_ml_config('default_confidence', 0.5)  # 0.5
initial_balance = get_trading_config('default_balance_jpy', 10000.0)  # 10000.0
btc_fallback = get_threshold('data.btc_fallback_price_jpy', 16000000.0)  # 16000000.0
```

### **段階的デプロイの実例**
```bash
# 1. デフォルト（paper・安全）
python3 main.py --config config/core/base.yaml

# 2. 本番移行（十分な検証後）
export MODE=live
python3 main.py --config config/core/base.yaml

# 3. コマンドライン指定
python3 main.py --config config/core/base.yaml --mode live
```

### **8個ヘルパー関数の実用例**
```python
from src.core.config import (
    get_threshold, get_ml_config, get_trading_config, 
    get_monitoring_config, get_position_config, 
    get_backtest_config, get_data_config, get_execution_config
)

# 1. ML設定の動的取得
confidence_threshold = get_ml_config('confidence_threshold', 0.65)
emergency_stop = get_ml_config('emergency_stop_on_dummy', True)

# 2. 取引設定の動的取得
initial_balance = get_trading_config('default_balance_jpy', 10000.0)
bid_spread = get_trading_config('bid_spread_ratio', 0.999)

# 3. 監視設定の動的取得
discord_timeout = get_monitoring_config('discord.timeout_seconds', 30)
retry_count = get_monitoring_config('discord.max_retries', 3)

# 4. ポジション管理設定
max_position_size = get_position_config('max_size_jpy', 100000.0)
min_profit_margin = get_position_config('min_profit_margin', 0.001)

# 5. バックテスト設定
backtest_period = get_backtest_config('period_days', 365)
commission_rate = get_backtest_config('commission_rate', 0.0012)

# 6. データ取得設定
max_retries = get_data_config('max_retries', 5)
timeout_seconds = get_data_config('timeout_seconds', 30)

# 7. 実行制御設定
max_workers = get_execution_config('max_concurrent_workers', 4)
batch_size = get_execution_config('batch_processing_size', 100)

# 8. 汎用設定（ドット記法）
btc_price = get_threshold('data.btc_fallback_price_jpy', 16000000.0)
feature_count = get_threshold('ml.expected_feature_count', 12)
confidence = get_threshold("ml.default_confidence", 0.5)
interval = get_threshold("execution.paper_mode_interval_seconds", 60)
balance = get_threshold("trading.default_balance_jpy", 10000.0)

# フォールバック制御
emergency_stop = get_threshold("ml.emergency_stop_on_dummy", True)
if emergency_stop and model_type == "DummyModel":
    logger.critical("🚨 ダミーモデル検出により緊急停止")
    sys.exit(1)
```

## ⚠️ 注意事項・制約

### **段階的デプロイの重要性**
- **デフォルト安全設計**: base.yamlは`mode: paper`で安全
- **本番移行慎重**: paperでの十分な実績確認後にlive移行
- **1万円スタート**: 個人開発リアルな初期資金設定
- **段階的拡大**: 1万円→成功時10万円→最終目標50万円

### **bitbank信用取引制約**
- **2倍レバレッジ上限**: bitbank仕様準拠・安全性重視
- **BTC/JPY専用**: 信用取引対応通貨ペア
- **API制限**: 35秒間隔・リトライ5回で信頼性確保

### **12個厳選特徴量システム制約**
- **12個固定**: feature_order.jsonで定義された厳選特徴量使用
- **順序重要**: 特徴量の順序変更は予測性能に影響
- **カテゴリ分類**: basic/technical/anomaly各カテゴリバランス

### **Phase 16-B品質保証制約**
- **620テスト100%合格**: 設定一元化品質保証維持必須
- **50%+カバレッジ**: 目標を上回る品質保証基準遵守
- **型安全性**: MyPy統合・段階的型エラー解消

## 🔗 関連ファイル・依存関係

### **重要な外部依存**
- **`src/core/config.py`**: 設定読み込みシステム・3層優先度実装
- **`src/core/orchestrator.py`**: 統合システム制御・設定適用
- **`main.py`**: エントリーポイント・コマンドライン引数解析
- **`.github/workflows/ci.yml`**: CI/CD・620テスト・設定検証・品質ゲート

### **環境別設定ファイル**
- **`config/production/production.yaml`**: 本番環境設定（Phase 16-B対応）
- **bitbank信用取引設定**: 2倍レバレッジ・BTC/JPY専用
- **GCP統合**: Secret Manager・Workload Identity

### **Phase 16-B品質保証システム統合**
- **620テスト**: 設定一元化品質保証・統合テスト強化対応
- **50%+カバレッジ**: 目標を上回る企業級品質保証基準
- **MyPy統合**: 型安全性・段階的型エラー解消
- **CI/CD品質ゲート**: 自動品質チェック・デプロイ制御

---

**重要**: このディレクトリはPhase 16-B完了により、bitbank信用取引専用・160個ハードコード値統合・8個ヘルパー関数による動的設定管理・段階的デプロイ（paper→live）・個人開発最適化（1万円→50万円）・620テスト品質保証を実現した設定一元化基盤システムです。thresholds.yaml変更時は十分な検証を実施してください。