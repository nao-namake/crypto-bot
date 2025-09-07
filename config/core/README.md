# config/core/ - 攻撃的設定コア設定システム

**Phase 19+攻撃的設定完成**: 特徴量定義一元化・攻撃的戦略ロジック・Dynamic Confidence・攻撃的閾値最適化・625テスト100%品質保証により、12特徴量統一管理・月100-200取引対応・攻撃的設定統合・Cloud Run 8時間稼働実績を実現した攻撃的取引最適化基本設定システムが完成

## 🎯 役割・責任

bitbank信用取引専用・12特徴量統一管理・**攻撃的戦略ロジック**を核とした全環境（paper/live）攻撃的設定を管理します。攻撃的閾値最適化・Dynamic Confidence・月100-200取引対応・ATR不一致取引・Mochipoy1票取引による積極的取引機会創出と、攻撃的ポジションサイジング・Cloud Run安定稼働を実現します。

## 📂 ファイル構成

```
core/
├── README.md               # このファイル（Phase 19完了版）
├── base.yaml              # 基本設定（bitbank信用取引・段階的デプロイ・Phase 19対応）
├── feature_order.json     # 12特徴量統一管理（Phase 19単一真実源・feature_manager.py連携）
├── thresholds.yaml        # 攻撃的設定一元化ファイル（攻撃的閾値・Dynamic Confidence・月100-200取引対応・4戦略統一管理）
└── feature_manager.py     # 特徴量統一管理システム（Phase 19新規・12特徴量制御）
```

## 🔧 主要機能・実装

### **base.yaml - 基本設定システム（Phase 19完全対応）**

**🎯 段階的デプロイ・MLOps基盤による安全な本番移行**:
- **paper**: 安全なペーパートレード（デフォルト・無制限検証・MLOps対応）
- **live**: 実資金取引（十分な検証・MLモデル品質確認後に慎重移行）

**主要設定カテゴリ**:
```yaml
# モード設定（段階的デプロイ・Phase 19対応）
mode: paper  # デフォルト：安全なペーパートレード

# 取引所設定（bitbank信用取引専用）
exchange:
  name: bitbank
  symbol: BTC/JPY
  leverage: 2.0            # 最大2倍レバレッジ（bitbank仕様準拠）
  rate_limit_ms: 35000     # 35秒・安全マージン

# 機械学習設定（ProductionEnsemble・Phase 19統合）
ml:
  confidence_threshold: 0.65  # 65%（収益性重視・高品質シグナル）
  ensemble_enabled: true      # アンサンブルモデル使用
  models: ["lgbm", "xgb", "rf"]
  feature_count: 12           # 12特徴量統一管理（Phase 19）
  version_tracking: true      # Git情報追跡・バージョン管理

# リスク管理設定（Kelly基準・個人開発最適化）
risk:
  risk_per_trade: 0.02        # 2%（個人開発バランス）
  kelly_max_fraction: 0.25    # 25%（科学的最適化）
  max_drawdown: 0.20          # 20%制限
  consecutive_loss_limit: 5   # 連続5回損失で自動停止

# データ取得設定（マルチタイムフレーム・特徴量統一対応）
data:
  timeframes: ["15m", "4h"]   # 2軸マルチタイムフレーム分析
  since_hours: 96            # 4日間データ（bitbank安定範囲）
  feature_manager_enabled: true  # 特徴量統一管理（Phase 19）
```

### **feature_order.json - 12特徴量統一管理システム（Phase 19単一真実源）**

**Phase 19完了成果・特徴量定義一元化**:
- **大幅削減**: 97個→12特徴量（87.6%削減・効率化・統一管理）
- **単一真実源**: feature_order.json・feature_manager.py連携・整合性保証
- **カテゴリ分類**: basic(3) + technical(6) + calculations(3)
- **重要度管理**: critical/high/medium/low分類・優先度制御

**特徴量構成（Phase 19統一管理）**:
```json
{
  "total_features": 12,
  "feature_names": [
    "close", "volume", "returns_1", 
    "rsi_14", "macd", "macd_signal", "atr_14", 
    "bb_position", "ema_20", "ema_50", 
    "zscore", "volume_ratio"
  ],
  "feature_categories": {
    "basic": ["close", "volume", "returns_1"],
    "technical": ["rsi_14", "macd", "macd_signal", "atr_14", "bb_position", "ema_20", "ema_50"],
    "calculations": ["zscore", "volume_ratio"]
  },
  "phase": "Phase 19",
  "last_updated": "2025-09-04",
  "version": "19.0.0"
}
```

### **feature_manager.py - 特徴量統一管理システム（Phase 19新規確立）**

**🎯 12特徴量統一管理・整合性保証システム**:

**主要機能**:
- **特徴量統一管理**: feature_order.json読み込み・12特徴量定義制御
- **整合性検証**: 全システム特徴量定義統一・互換性保証
- **カテゴリ管理**: basic/technical/calculations分類・優先度制御
- **バージョン管理**: Phase 19対応・変更履歴・品質トレーサビリティ

**実装例**:
```python
class FeatureManager:
    def get_feature_names(self) -> List[str]:
        """12特徴量名一覧取得"""
        
    def get_feature_count(self) -> int:
        """特徴量数取得（12固定）"""
        
    def get_feature_categories(self) -> Dict[str, List[str]]:
        """カテゴリ別特徴量分類取得"""
        
    def validate_features(features: List[str]) -> bool:
        """特徴量整合性検証"""
```

### **thresholds.yaml - 攻撃的設定一元化システム（Phase 19+攻撃的設定完成・ハードコード問題解決）**

**🎯 攻撃的閾値最適化・Dynamic Confidence・月100-200取引対応・戦略設定統一化**:

**攻撃的設定変更の成果（Phase 19+攻撃的設定完成）**:
- **攻撃的閾値**: high 0.65→0.45・very_high 0.8→0.60・積極的取引機会創出
- **Dynamic Confidence**: HOLD固定0.5→市場ボラティリティ連動0.1-0.8変動・base_hold 0.3
- **月100-200取引対応**: 保守的設定排除・取引頻度最適化・機会損失防止
- **攻撃的戦略統合**: ATR不一致取引・Mochipoy1票取引・攻撃的ポジションサイジング
- **🔧 ハードコード問題解決**: 戦略内固定値完全排除・設定値一元管理・フォールバック防止統合

**8個ヘルパー関数（Phase 19拡張）**:
```python
# 基本設定値取得
get_threshold(key, default=None)           # 汎用設定値取得・特徴量統一管理対応
get_trading_config(key, default=None)      # 取引設定取得
get_ml_config(key, default=None)           # ML設定取得・MLOps統合
get_monitoring_config(key, default=None)   # 監視設定取得・Discord統合
get_position_config(key, default=None)     # ポジション設定取得
get_backtest_config(key, default=None)     # バックテスト設定取得
get_data_config(key, default=None)         # データ取得設定取得・特徴量統一管理対応
get_execution_config(key, default=None)    # 実行制御設定取得・MLOps自動化対応
```

**Phase 19+攻撃的設定カテゴリ**:
```yaml
# 攻撃的信頼度閾値（月100-200取引対応）
confidence_levels:
  very_high: 0.60      # 0.8→0.60（攻撃的）
  high: 0.45          # 0.65→0.45（攻撃的）  
  medium: 0.35        # 0.5→0.35（攻撃的）
  low: 0.25           # 新設（積極的取引）
  min_ml: 0.15        # 0.25→0.15（最低限）

# Dynamic Confidence（HOLD固定0.5問題解決）
ml:
  dynamic_confidence:
    base_hold: 0.3           # 0.5→0.3（攻撃的）
    error_fallback: 0.2      # エラー時フォールバック
    neutral_default: 0.35    # 中性時デフォルト

# 4戦略統一管理（Phase 19+循環インポート解決版・ハードコード問題解決完了）
strategies:
  atr_based:
    normal_volatility_strength: 0.3  # 通常ボラティリティ時強度（攻撃的）
    hold_confidence: 0.3             # HOLD決定時信頼度（旧：ハードコード0.5）
  fibonacci_retracement:
    no_signal_confidence: 0.3        # 反転シグナルなし時信頼度（攻撃的）
    no_level_confidence: 0.3         # フィボレベル接近なし時信頼度（旧：ハードコード0.0）
  mochipoy_alert:
    hold_confidence: 0.3             # HOLD信頼度（攻撃的）
  multi_timeframe:
    hold_confidence: 0.3             # HOLD信頼度（攻撃的）

# 特徴量統一管理（Phase 19新規）
features:
  feature_manager_enabled: true    # feature_manager.py有効化
  strict_validation: true          # 厳格な特徴量整合性チェック
  feature_order_path: "config/core/feature_order.json"  # 単一真実源

# 取引関連動的設定・Phase 19対応
trading:
  default_balance_jpy: 10000.0      # 初期残高（1万円・個人開発）
  bid_spread_ratio: 0.999           # 0.1%スプレッド
  
# 実行間隔制御・MLOps自動化対応
execution:
  paper_mode_interval_seconds: 60   # ペーパートレード間隔
  live_mode_interval_seconds: 180   # ライブトレード間隔（収益性重視）
  ml_training_interval_hours: 168   # 週次自動学習（7日=168時間）
```

## 📝 使用方法・例

### **Phase 19特徴量統一管理システム**
```python
# Phase 19新機能：特徴量統一管理
from src.core.config.feature_manager import FeatureManager
from src.core.config import load_config, get_threshold, get_ml_config

# 特徴量統一管理システム初期化
fm = FeatureManager()

# 12特徴量統一管理
feature_names = fm.get_feature_names()          # 12特徴量名一覧
feature_count = fm.get_feature_count()          # 12（固定）
categories = fm.get_feature_categories()        # カテゴリ別分類

# 特徴量整合性検証
features_valid = fm.validate_features(some_features)  # True/False

# 設定との統合確認
expected_count = get_ml_config('expected_feature_count', 12)  # 12
assert feature_count == expected_count, "特徴量数不整合"
```

### **Phase 19設定アクセスシステム**
```python
from src.core.config import load_config, get_threshold, get_ml_config, get_trading_config

# Phase 19対応設定読み込み
config = load_config('config/core/base.yaml')

# 基本設定値取得
mode = config.mode  # paper/live
confidence = config.ml.confidence_threshold  # 0.65
leverage = config.exchange.leverage  # 2.0（bitbank仕様）

# Phase 19新システム: 特徴量統一管理対応
feature_count = get_ml_config('expected_feature_count', 12)  # 12
version_tracking = get_ml_config('version_tracking_enabled', True)  # True
auto_archive = get_ml_config('auto_archive_enabled', True)  # True

# 特徴量管理設定
feature_manager_enabled = get_threshold('features.feature_manager_enabled', True)
strict_validation = get_threshold('features.strict_validation', True)
feature_order_path = get_threshold('features.feature_order_path')
```

### **MLOps基盤・バージョン管理統合（Phase 19新機能）**
```python
# MLOps基盤設定確認
ml_training_interval = get_execution_config('ml_training_interval_hours', 168)  # 週次学習

# バージョン管理・Git情報追跡
version_tracking = get_ml_config('version_tracking_enabled', True)
if version_tracking:
    # Git情報追跡・メタデータ管理
    git_info = get_git_info()  # commit hash, branch, timestamp
    
# 自動アーカイブ設定
auto_archive = get_ml_config('auto_archive_enabled', True)
if auto_archive:
    # models/archive/自動バージョン管理
    archive_old_models()
```

### **段階的デプロイの実例（Phase 19対応）**
```bash
# 1. デフォルト（paper・安全・特徴量統一管理対応）
python3 main.py --config config/core/base.yaml

# 2. 本番移行（十分な検証・MLモデル品質確認後）
export MODE=live
python3 main.py --config config/core/base.yaml

# 3. MLOps機能確認（Phase 19新機能）
python3 -c "
from src.core.config.feature_manager import FeatureManager
fm = FeatureManager()
print(f'特徴量数: {fm.get_feature_count()}')
print(f'Phase 19対応: {fm.get_feature_names()}')
"
```

### **8個ヘルパー関数の実用例（Phase 19拡張対応）**
```python
from src.core.config import (
    get_threshold, get_ml_config, get_trading_config, 
    get_monitoring_config, get_position_config, 
    get_backtest_config, get_data_config, get_execution_config
)

# 1. ML設定の動的取得（Phase 19 MLOps対応）
confidence_threshold = get_ml_config('confidence_threshold', 0.65)
feature_count = get_ml_config('expected_feature_count', 12)  # 12特徴量統一
version_tracking = get_ml_config('version_tracking_enabled', True)

# 2. 特徴量統一管理設定（Phase 19新規）
feature_manager_enabled = get_threshold('features.feature_manager_enabled', True)
strict_validation = get_threshold('features.strict_validation', True)

# 3. MLOps自動化設定（Phase 19新機能）
ml_training_interval = get_execution_config('ml_training_interval_hours', 168)
auto_archive = get_ml_config('auto_archive_enabled', True)

# 4. 取引設定の動的取得
initial_balance = get_trading_config('default_balance_jpy', 10000.0)
bid_spread = get_trading_config('bid_spread_ratio', 0.999)

# 5. 監視設定の動的取得・Discord統合
discord_timeout = get_monitoring_config('discord.timeout_seconds', 30)
retry_count = get_monitoring_config('discord.max_retries', 3)

# 6. 品質保証設定（Phase 19企業級）
emergency_stop = get_threshold("ml.emergency_stop_on_dummy", True)
if emergency_stop and model_type == "DummyModel":
    logger.critical("🚨 ダミーモデル検出により緊急停止")
    sys.exit(1)

# 7. ハードコード問題解決システム（戦略設定統一管理）
# 戦略内での設定値取得（フォールバック防止）
from ...core.config.threshold_manager import get_threshold

# ATRBased戦略のHOLD信頼度設定
hold_confidence = get_threshold("strategies.atr_based.hold_confidence", 0.3)

# FibonacciRetracement戦略の設定
no_level_confidence = get_threshold("strategies.fibonacci_retracement.no_level_confidence", 0.3)
no_signal_confidence = get_threshold("strategies.fibonacci_retracement.no_signal_confidence", 0.3)

# 戦略設定統一管理により、ハードコード値完全排除・フォールバック防止実現
```

## ⚠️ 注意事項・制約

### **段階的デプロイの重要性（Phase 19対応）**
- **デフォルト安全設計**: base.yamlは`mode: paper`で安全・特徴量統一管理対応
- **本番移行慎重**: paperでの十分な実績・MLモデル品質確認後にlive移行
- **1万円スタート**: 個人開発リアルな初期資金設定
- **段階的拡大**: 1万円→成功時10万円→最終目標50万円
- **MLOps品質確認**: ProductionEnsemble・12特徴量・Git情報追跡確認必須

### **12特徴量統一管理制約（Phase 19新規）**
- **12特徴量固定**: feature_order.json・feature_manager.py・単一真実源
- **整合性必須**: 全システム12特徴量統一・互換性保証・厳格検証
- **順序重要**: 特徴量の順序変更は予測性能に影響・バージョン管理必須
- **カテゴリ分類**: basic/technical/calculations各カテゴリバランス

### **MLOps基盤制約（Phase 19新規）**
- **バージョン管理**: Git情報追跡・自動アーカイブ・メタデータ管理必須
- **週次自動学習**: model-training.yml・GitHub Actions・品質検証統合
- **品質保証**: ProductionEnsemble・12特徴量・整合性100%必須
- **アーカイブ管理**: models/archive/・ディスク容量監視・履歴保持

### **Phase 19+攻撃的設定品質保証制約**
- **625テスト100%成功**: 攻撃的戦略ロジック・特徴量統一管理・MLOps品質保証維持必須
- **58.64%カバレッジ**: 企業級品質保証基準・攻撃的設定対応・継続監視必須
- **型安全性**: MyPy統合・段階的型エラー解消・特徴量型安全性

## 🔗 関連ファイル・依存関係

### **Phase 19新規統合システム**

**特徴量統一管理連携**:
- **`src/core/config/feature_manager.py`**: 特徴量統一管理システム・12特徴量制御
- **`config/core/feature_order.json`**: 12特徴量定義・単一真実源・Phase 19
- **`src/features/feature_generator.py`**: 特徴量生成・feature_manager連携
- **`tests/unit/core/config/`**: feature_manager.pyテスト・品質保証

**MLOps基盤連携**:
- **`scripts/ml/create_ml_models.py`**: Git情報追跡・自動アーカイブ・バージョン管理
- **`.github/workflows/model-training.yml`**: 週次自動学習・GitHub Actions
- **`models/`**: ProductionEnsemble・メタデータ・アーカイブ管理
- **`tests/unit/ml/`**: ML品質テスト・ProductionEnsemble検証

### **重要な外部依存（Phase 19完全統合）**
- **`src/core/config.py`**: 設定読み込みシステム・3層優先度・特徴量統一管理対応
- **`src/core/orchestration/orchestrator.py`**: 統合システム制御・MLOps統合
- **`main.py`**: エントリーポイント・コマンドライン引数・Phase 19対応
- **`.github/workflows/ci.yml`**: CI/CD・654テスト・特徴量整合性検証

### **環境別設定ファイル（Phase 19対応）**
- **`config/production/production.yaml`**: 本番環境設定・MLOps統合
- **bitbank信用取引設定**: 2倍レバレッジ・BTC/JPY専用・特徴量統一管理対応
- **GCP統合**: Secret Manager・Workload Identity・GitHub Actions統合

### **Phase 19品質保証システム統合**
- **654テスト**: 特徴量統一管理・MLOps品質保証・統合テスト強化
- **59.24%カバレッジ**: 企業級品質保証基準・継続監視・特徴量カバー
- **MyPy統合**: 型安全性・段階的型エラー解消・特徴量型安全性
- **CI/CD品質ゲート**: 自動品質チェック・特徴量整合性・MLOps品質検証

## 📊 Phase 19成果・継続運用体制

### **特徴量定義一元化完成実績**
```
🎯 12特徴量統一: feature_order.json・feature_manager.py・単一真実源確立
✅ 整合性保証: 全システム特徴量定義統一・互換性100%・厳格検証
⚡ 保守性向上: ハードコード完全排除・設定一元化・メンテナンス効率化
🤖 自動検証: 特徴量整合性チェック・CI/CD統合・回帰防止
📊 カテゴリ管理: basic/technical/calculations・優先度制御・バランス保持
```

### **MLOps基盤確立実績**
```
🚀 バージョン管理: Git情報追跡・自動アーカイブ・メタデータ管理完成
📅 週次自動学習: model-training.yml・GitHub Actions・品質検証統合
🔄 品質保証: ProductionEnsemble・12特徴量・整合性100%継続
📁 アーカイブ管理: models/archive/・履歴保持・品質トレーサビリティ
⚡ CI/CD統合: 自動品質ゲート・特徴量検証・MLOps統合完了
```

### **品質保証継続体制（Phase 19企業級）**
```
🎯 654テスト100%: 特徴量統一管理・MLOps・品質保証完備
📊 59.24%カバレッジ: 企業級水準・継続監視・品質劣化防止
🔧 30秒高速実行: CI/CD最適化・開発効率化・品質チェック統合
🤖 自動化完成: 特徴量整合性・MLOps・品質検証・運用効率化
🚀 企業級品質: 回帰防止・継続改善・安定運用・保守性向上
```

---

**🎯 Phase 19+攻撃的設定完成・設定統合基盤確立**: 特徴量定義一元化・攻撃的戦略ロジック・Dynamic Confidence・攻撃的閾値最適化・625テスト100%品質保証により、12特徴量統一管理・月100-200取引対応・攻撃的設定統合・Cloud Run 8時間稼働実績を実現した攻撃的取引最適化基本設定システムが完全稼働**

## 🚀 Phase 19+攻撃的設定完了記録・攻撃的設定統合基盤達成

**完了日時**: 2025年9月6日（Phase 19+攻撃的設定完成・Cloud Run 8時間稼働実績）  
**Phase 19+攻撃的設定達成**: 
- ✅ **攻撃的閾値最適化完成** (high 0.65→0.45・very_high 0.8→0.60・積極的取引機会創出)
- ✅ **Dynamic Confidence実装** (HOLD固定0.5→市場ボラティリティ連動0.1-0.8・base_hold 0.3)
- ✅ **攻撃的戦略統合** (ATR不一致取引・Mochipoy1票取引・攻撃的ポジションサイジング)
- ✅ **品質保証体制継続** (625テスト100%・58.64%カバレッジ・攻撃的設定対応)
- ✅ **月100-200取引対応** (保守的設定排除・取引頻度最適化・機会損失防止)

**攻撃的運用体制**:
- 🎯 **攻撃的設定統合**: thresholds.yaml攻撃的閾値・Dynamic Confidence・月100-200取引対応
- 🤖 **攻撃的戦略実行**: ATR不一致取引・Mochipoy1票取引・積極的シグナル捕捉
- 📊 **品質保証継続**: 625テスト・58.64%カバレッジ・攻撃的ロジック対応・回帰防止
- 🔧 **攻撃的運用継続**: Cloud Run 8時間稼働実績・シンプルヘルスチェック・安定攻撃的取引継続