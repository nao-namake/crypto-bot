# config/core/ - システム基本設定

## 🎯 役割・責任

システム全体で使用する基本設定を管理します。取引所接続、機械学習、戦略、リスク管理などの核となる設定ファイル群を提供し、全システムで一貫した動作を保証します。

## 📂 ファイル構成

```
core/
├── unified.yaml         # 統一設定ファイル（全環境対応）
├── feature_order.json   # 特徴量定義
├── thresholds.yaml      # 動的閾値設定  
└── README.md            # このファイル
```

## 📋 各ファイルの役割

### **unified.yaml**
システムの基本動作を定義する統一設定ファイルです。全環境（paper/live/backtest）をサポートし、3層優先度（CLI > 環境変数 > YAML）でモード切り替えが可能です。

**主要設定項目**:
- `mode`: 動作モード（paper/live）
- `exchange`: 取引所設定（bitbank信用取引専用）
- `ml`: 機械学習設定（アンサンブルモデル、信頼度閾値）
- `risk`: リスク管理設定（Kelly基準、損切り設定）
- `data`: データ取得設定（タイムフレーム、取得期間）
- `features`: 特徴量管理設定
- `strategies`: 戦略設定
- `logging`: ログ設定
- `production`: 本番運用設定
- `monitoring`: 監視システム設定
- `security`: セキュリティ設定

### **feature_order.json**  
機械学習で使用する特徴量の定義と順序を管理するファイルです。

**主要内容**:
- `total_features`: 特徴量総数（12個）
- `feature_categories`: カテゴリ別特徴量分類
  - `basic`: 基本価格・出来高情報（3個）
  - `momentum`: モメンタム指標（3個） 
  - `volatility`: ボラティリティ指標（2個）
  - `trend`: トレンド指標（2個）
  - `volume`: 出来高指標（1個）
  - `anomaly`: 異常検知指標（1個）
- `feature_definitions`: 各特徴量の詳細定義
- `validation`: チェックサム、検証ステータス

### **thresholds.yaml**
動的な閾値設定を一元管理するファイルです。

**主要設定項目**:
- `confidence_levels`: 信頼度レベル別閾値
- `ml.dynamic_confidence`: 動的信頼度設定
- `strategies`: 各戦略の設定値
- `features`: 特徴量管理設定
- `trading`: 取引関連設定
- `execution`: 実行制御設定
- 8個のヘルパー関数用設定値

## 📝 使用方法・例

### **基本設定の読み込み**
```python
from src.core.config import load_config, get_threshold, get_ml_config, get_trading_config

# unified.yaml設定読み込み
config = load_config('config/core/unified.yaml')

# 基本設定値取得
mode = config.mode  # paper/live
confidence = config.ml.confidence_threshold  # 0.65
leverage = config.exchange.leverage  # 1.0
```

### **特徴量管理**
```python
from src.core.config.feature_manager import FeatureManager

# 特徴量管理システム初期化
fm = FeatureManager()

# 特徴量情報取得
feature_names = fm.get_feature_names()          # 12特徴量名一覧
feature_count = fm.get_feature_count()          # 12
categories = fm.get_feature_categories()        # カテゴリ別分類

# 整合性検証
features_valid = fm.validate_features(some_features)  # True/False
```

### **動的設定値取得**
```python
from src.core.config import (
    get_threshold, get_ml_config, get_trading_config, 
    get_monitoring_config, get_position_config, 
    get_backtest_config, get_data_config, get_execution_config
)

# 各種設定値取得
confidence_threshold = get_ml_config('confidence_threshold', 0.65)
initial_balance = get_trading_config('default_balance_jpy', 10000.0)
discord_timeout = get_monitoring_config('discord.timeout_seconds', 30)
hold_confidence = get_threshold("strategies.atr_based.hold_confidence", 0.3)
```

## ⚠️ 注意事項・制約

### **設定ファイル編集時の注意**
- **unified.yaml**: デフォルトは`mode: paper`（安全）。本番移行は慎重に実施
- **feature_order.json**: 特徴量の順序変更は予測性能に影響するため慎重に変更
- **thresholds.yaml**: 閾値変更は取引頻度・リスクに大きく影響

### **設定整合性の重要性**
- 全ファイル間での設定値の整合性を保つ
- 特徴量定義は`feature_order.json`が単一真実源
- 動的設定値は`thresholds.yaml`で一元管理

## 🔗 関連ファイル・依存関係

### **設定管理システム連携**
- `src/core/config.py`: 設定読み込みシステム
- `src/core/config/feature_manager.py`: 特徴量管理システム
- `src/core/config/threshold_manager.py`: 閾値管理システム

### **参照元システム**
- `src/core/orchestration/orchestrator.py`: システム統合制御
- `src/features/feature_generator.py`: 特徴量生成
- `src/strategies/`: 各取引戦略
- `main.py`: エントリーポイント

### **環境別設定**
- `config/core/unified.yaml`: 統一設定ファイル（全環境対応）
- `config/backtest/`: バックテスト専用設定
