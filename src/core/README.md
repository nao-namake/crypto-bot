# core/ - MLOps統合基盤システム

**Phase 19 MLOps統合版・根本修正完了**: feature_manager 12特徴量統合・ProductionEnsemble 3モデル統合・ML信頼度修正・Discord Webhookローカル設定化・654テスト品質保証・週次自動学習・Cloud Run 24時間稼働統合で、MLOps完全統合した企業級品質保証システムの核心基盤を実現

## 🎯 役割・責任

システム全体の基盤層を担当し、設定管理・ログシステム・統合制御・実行管理・レポート生成・サービス層を統合提供。Phase 19 MLOps統合により、feature_manager 12特徴量統一管理・ProductionEnsemble 3モデル統合・週次自動学習・Cloud Run 24時間稼働・Discord 3階層監視システムを統合し、堅牢で保守可能なMLOps基盤を提供します。

## 📂 ファイル構成

```
src/core/
├── __init__.py                 # 統合エクスポート設定（105行）
├── logger.py                   # 統合ログシステム（415行・JST対応・Discord統合）
├── market_data.py              # 市場データ構造（422行・統一データクラス）
├── exceptions.py               # カスタム例外システム（310行・階層化エラー処理）
├── protocols.py                # サービスプロトコル（60行・型安全性）
│
├── config/                     # 設定管理システム（Phase 17階層化完了）
│   ├── __init__.py             # 統合設定エクスポート（415行）
│   ├── config_classes.py       # 設定クラス定義（97行）
│   ├── feature_manager.py      # feature_manager 12特徴量統一管理★MLOps統合KEY
│   └── threshold_manager.py    # 閾値管理システム（211行）
│
├── orchestration/              # MLOps統合制御システム（Phase 19統合完成）
│   ├── __init__.py             # 統合制御エクスポート
│   ├── orchestrator.py         # システム統合制御（534行・Discord Webhookローカル設定）
│   ├── ml_adapter.py           # MLサービス統合（660行・feature_manager連携）
│   ├── ml_loader.py            # MLOpsモデル読み込み（ProductionEnsemble優先）
│   └── ml_fallback.py          # フォールバック機能専門（38行）
│
├── execution/                  # 実行モード管理（Phase 14-B分離完成）
│   ├── __init__.py             # 実行モード統合エクスポート
│   ├── base_runner.py          # 基底実行クラス（191行）
│   ├── paper_trading_runner.py # ペーパートレード（216行）
│   └── live_trading_runner.py  # ライブトレード（293行）
│
├── reporting/                  # レポート生成システム（Phase 14-B分離完成）
│   ├── __init__.py             # レポートシステムエクスポート
│   ├── base_reporter.py        # 基底レポーター（192行）
│   └── paper_trading_reporter.py # ペーパートレードレポート（322行）
│
└── services/                   # サービス層システム（Phase 19強化完成）
    ├── __init__.py             # サービス層統合エクスポート
    ├── health_checker.py       # ヘルスチェック（171行）
    ├── system_recovery.py      # システム復旧（215行）
    ├── trading_cycle_manager.py # 取引サイクル管理（358行・ML信頼度修正★重要）
    └── trading_logger.py       # 取引ログサービス（253行）
```

**統合成果（Phase 19完了）**:
- **MLOps統合**: feature_manager 12特徴量統一管理・ProductionEnsemble 3モデル統合・週次自動学習
- **根本修正**: ML信頼度固定値0.5問題解消・Discord Webhookローカル設定化・401エラー処理強化
- **品質保証**: 654テスト100%・59.24%カバレッジ・企業級品質管理・継続的品質改善

## 🔧 主要機能・実装

### **feature_manager統合（Phase 19 MLOps統合KEY）**

**12特徴量統一管理**:
```python
# src/core/config/feature_manager.py実装（Phase 19統合）
from src.core.config.feature_manager import FeatureManager

fm = FeatureManager()
print(f"特徴量数: {fm.get_feature_count()}")        # 12（統一管理）
print(f"特徴量一覧: {fm.get_feature_names()}")      # 12特徴量統一定義

# 整合性検証（Phase 19品質保証）
features = ["close", "volume", "returns_1", "rsi_14", "macd", 
           "macd_signal", "atr_14", "bb_position", "ema_20", 
           "ema_50", "zscore", "volume_ratio"]
assert fm.validate_features(features), "特徴量整合性エラー"
```

**ProductionEnsemble連携**:
```python
# feature_manager + ProductionEnsemble統合
from src.core.orchestration import MLServiceAdapter

ml_service = MLServiceAdapter(logger, enable_production_ensemble=True)
features_df = ml_service.generate_features_unified()  # 12特徴量統一DataFrame
predictions = ml_service.predict_ensemble(features_df)  # 3モデル統合予測
```

### **ML信頼度修正（Phase 19根本修正完了）**

**修正前（問題）**:
```python
# src/core/services/trading_cycle_manager.py（固定値0.5の問題）
"confidence": get_threshold("ml.default_confidence", 0.5)  # 常に0.5
```

**修正後（真のML予測）**:
```python
# 実際のMLモデル出力を使用（Phase 19修正）
ml_predictions_array = self.orchestrator.ml_service.predict(main_features_for_ml)
ml_probabilities = self.orchestrator.ml_service.predict_proba(main_features_for_ml)

if len(ml_predictions_array) > 0 and len(ml_probabilities) > 0:
    prediction = int(ml_predictions_array[-1])
    # 最大確率を信頼度として使用（実際MLモデルの出力）
    confidence = float(np.max(ml_probabilities[-1]))
    
logger.info(f"ML予測完了: prediction={prediction}, confidence={confidence:.3f}")
```

### **Discord Webhookローカル設定（Phase 19実装）**

**orchestrator.pyローカル優先読み込み**:
```python
# src/core/orchestration/orchestrator.py実装（Phase 19）
from pathlib import Path

webhook_path = Path("config/secrets/discord_webhook.txt")
if webhook_path.exists():
    try:
        webhook_url = webhook_path.read_text().strip()
        logger.info(f"📁 Discord Webhook URLをローカルファイルから読み込み（{len(webhook_url)}文字）")
    except Exception as e:
        logger.error(f"⚠️ ローカルファイル読み込み失敗: {e}")
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        logger.info(f"🌐 環境変数からフォールバック")
else:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    logger.info(f"🌐 Discord Webhook URLを環境変数から読み込み")
```

### **統合ログシステム（Phase 19強化）**

**JST対応・Discord統合・構造化ログ**:
```python
# src/core/logger.py実装
from src.core.logger import setup_logging

logger = setup_logging("crypto_bot")

# 基本ログ
logger.info("システム起動完了")

# 構造化ログ（Phase 19 MLOps統合）
logger.info("feature_manager 12特徴量生成完了", extra_data={
    'features_count': 12,
    'model': 'ProductionEnsemble',
    'confidence': 0.734
})

# Discord通知付きログ
logger.error("ProductionEnsemble読み込み失敗", discord_notify=True)
```

### **統合制御システム（Phase 19 orchestration強化）**

**TradingOrchestrator統合制御**:
```python
# src/core/orchestration/orchestrator.py使用例
from src.core import create_trading_orchestrator

# Phase 19 MLOps統合orchestrator作成
orchestrator = await create_trading_orchestrator(config, logger)

# システム全体統合実行
await orchestrator.initialize()           # システム初期化・feature_manager統合
await orchestrator.run_trading_cycle()   # 取引サイクル・ProductionEnsemble統合
await orchestrator.cleanup()             # リソース解放・ログ出力
```

## 📝 使用方法・例

### **基本的な使用方法（Phase 19更新版）**

**システム初期化**:
```python
from src.core import load_config, setup_logging, create_trading_orchestrator

# 設定読み込み・ログ初期化
config = load_config('config/core/base.yaml', cmdline_mode='paper')
logger = setup_logging("crypto_bot")

# MLOps統合orchestrator作成（Phase 19）
orchestrator = await create_trading_orchestrator(config, logger)
```

**feature_manager統合使用**:
```python
from src.core.config.feature_manager import FeatureManager

# feature_manager初期化・12特徴量統一管理
fm = FeatureManager()
feature_count = fm.get_feature_count()        # 12
feature_names = fm.get_feature_names()        # 統一特徴量リスト

# 特徴量生成・ProductionEnsemble連携
features_df = orchestrator.ml_service.generate_features_unified()
```

**設定管理使用**:
```python
from src.core import get_threshold, get_monitoring_config, get_ml_config

# 基本的な閾値取得
confidence = get_threshold("ml.default_confidence", 0.5)
balance = get_threshold("trading.initial_balance_jpy", 10000.0)

# MLOps統合設定取得（Phase 19）
emergency_stop = get_ml_config("emergency_stop_on_dummy", True)
max_failures = get_ml_config("max_model_failures", 3)

# Discord設定取得
discord_timeout = get_monitoring_config("discord.timeout", 10)
```

### **エラーハンドリング（Phase 19強化）**

**カスタム例外使用**:
```python
from src.core.exceptions import MLModelError, ExchangeAPIError

try:
    # ProductionEnsemble読み込み
    predictions = orchestrator.ml_service.predict_ensemble(features_df)
except MLModelError as e:
    logger.error(f"MLモデルエラー: {e}", discord_notify=True)
except ExchangeAPIError as e:
    logger.error(f"取引所APIエラー: {e}", discord_notify=True)
```

## ⚠️ 注意事項・制約

### **Phase 19重要変更点**

**ML信頼度修正注意事項**:
- **固定値問題解消**: `confidence=0.5`固定から実際のMLモデル出力に変更
- **予測精度向上**: ProductionEnsembleの実際の予測確率を反映
- **ダミーモデル回避**: 真のML予測により取引精度向上
- **デバッグ強化**: 予測値と信頼度の詳細ログ出力

**Discord Webhook設定注意事項**:
- **ローカル優先**: `config/secrets/discord_webhook.txt` > 環境変数 > GCP
- **機密保護**: `.gitignore`設定・Git漏洩防止
- **エラー処理**: 401エラー専用処理・自動無効化
- **フォールバック**: 従来のGCP Secret Manager併用可能

### **MLOps統合制約**

**feature_manager制約**:
- **12特徴量固定**: config/core/feature_order.json単一真実源
- **DataFrame統一**: 全システムでDataFrame形式統一
- **整合性必須**: 特徴量名・順序・型の厳密な一致

**ProductionEnsemble制約**:
- **3モデル必須**: LightGBM・XGBoost・RandomForest全て必要
- **重み付け固定**: 40%・40%・20%の重み付け投票
- **Git情報必須**: モデルファイルにGit情報埋め込み

### **品質保証制約（Phase 19強化）**

**654テスト制約**:
- **100%成功必須**: 全テスト通過・回帰防止
- **59.24%カバレッジ維持**: 新機能でのカバレッジ向上必須
- **MLOps統合テスト**: feature_manager・ProductionEnsemble統合テスト

## 🔗 関連ファイル・依存関係

### **重要な外部依存（Phase 19統合）**

**config/設定ファイル連携**:
- **`config/core/feature_order.json`**: feature_manager 12特徴量統一定義★MLOps統合KEY
- **`config/core/base.yaml`**: システム基本設定・モード設定
- **`config/core/thresholds.yaml`**: 動的閾値設定・160個ハードコード値統合
- **`config/secrets/discord_webhook.txt`**: Discord Webhookローカル設定

**MLOps統合連携**:
- **`src/features/feature_generator.py`**: feature_manager統合FeatureGenerator・12特徴量生成
- **`src/ml/`**: ProductionEnsemble 3モデル統合・週次自動学習
- **`src/strategies/`**: feature_manager連携戦略・ProductionEnsemble統合判定
- **`src/monitoring/discord_notifier.py`**: Discord 3階層監視・401エラー処理強化

### **CI/CD・品質保証連携**

**GitHub Actions連携**:
- **`.github/workflows/ci.yml`**: 654テスト・品質チェック・デプロイ
- **`.github/workflows/model-training.yml`**: 週次自動学習・ProductionEnsemble更新
- **`scripts/testing/checks.sh`**: 品質チェック・カバレッジ確認

**GCP統合連携**:
- **Cloud Run**: 24時間稼働・スケーラブル実行・Discord監視
- **Secret Manager**: フォールバック設定・従来方式継続サポート
- **Cloud Logging**: システムログ・エラー監視・Discord通知連携

### **テスト・品質管理連携**

**テストシステム連携**:
- **`tests/unit/core/`**: core層単体テスト・100%合格必須
- **`tests/integration/`**: MLOps統合テスト・feature_manager + ProductionEnsemble
- **`coverage-reports/`**: 59.24%カバレッジレポート・品質可視化

---

**🎯 Phase 19 MLOps統合・根本修正完了**: feature_manager 12特徴量統一管理・ProductionEnsemble 3モデル統合・ML信頼度修正・Discord Webhookローカル設定化・654テスト品質保証・週次自動学習・Cloud Run 24時間稼働統合により、MLOps完全統合した企業級品質保証システムの核心基盤を実現**

**重要**: Phase 19根本修正により、ML予測の精度・Discord通知の安定性・設定管理の柔軟性が大幅向上。core/基盤システムは、feature_manager統合・ProductionEnsemble統合・真のML予測・ローカル設定優先・強化エラー処理により、ペーパートレードから本番運用まで一貫した高品質MLOps基盤を実現しています。