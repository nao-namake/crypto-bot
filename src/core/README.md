# src/core/ - コアシステム基盤

## 📂 ディレクトリ構成

```
src/core/                          # 31 Pythonファイル（8,078行）+ 4 README
├── __init__.py                    # モジュールマーカー
├── logger.py                      # JST対応ログシステム・構造化出力
├── exceptions.py                  # カスタム例外階層（9種類派生クラス + PostOnlyCancelledException）
│
├── config/                        # 設定管理システム（5ファイル）
│   ├── __init__.py                # 設定ローダー・3層設定体系
│   ├── config_classes.py          # 5設定dataclass定義
│   ├── feature_manager.py         # 37特徴量統一管理（Phase 77）
│   ├── runtime_flags.py           # ランタイムフラグ（Phase 35）
│   └── threshold_manager.py       # 閾値・動的設定管理・実行時オーバーライド（Phase 40.1）
│
├── orchestration/                 # システム統合制御（6ファイル）
│   ├── __init__.py                # 統合制御エクスポート
│   ├── orchestrator.py            # Application Service Layer（575行）
│   ├── protocols.py               # 5サービスプロトコル定義
│   ├── ml_adapter.py              # ProductionEnsemble統一インターフェース
│   ├── ml_loader.py               # MLモデル読み込み・個別モデル再構築
│   └── ml_fallback.py             # DummyModel安全装置（hold信頼度0.5）
│
├── execution/                     # 実行モード管理（5ファイル）
│   ├── __init__.py                # 実行モードエクスポート
│   ├── base_runner.py             # 基底実行ランナー（ABC型安全設計）
│   ├── paper_trading_runner.py    # ペーパートレード実行
│   ├── live_trading_runner.py     # ライブトレード実行
│   └── backtest_runner.py         # バックテスト実行（Phase 49完全改修・信頼性100%達成）
│
├── reporting/                     # レポート生成（2ファイル + README）
│   ├── __init__.py                # レポートエクスポート
│   ├── base_reporter.py           # 基底レポート機能
│   ├── paper_trading_reporter.py  # ペーパートレードレポート
│   └── README.md                  # レポート生成システム詳細
│
└── services/                      # システムサービス（6ファイル + README）
    ├── __init__.py                # サービス層エクスポート
    ├── trading_cycle_manager.py   # 取引サイクル管理（1,033行・Phase 49完了・最重要ファイル）
    ├── graceful_shutdown_manager.py # Graceful shutdown管理（30秒タイムアウト）
    ├── health_checker.py          # システムヘルスチェック
    ├── system_recovery.py         # システム復旧（MLサービス復旧・最大3回試行）
    ├── trading_logger.py          # 取引ログサービス
    └── README.md                  # システムサービス層詳細
```

## 🔧 主要コンポーネント

### **設定管理システム (config/)**

**目的**: YAML設定ファイルによる集約的設定システム・15特徴量統一管理

**主要ファイル**:
- `__init__.py`: 3層優先度（CLI > 環境変数 > YAML）の設定ローダー
- `config_classes.py`: 7つのdataclass定義（ExchangeConfig、MLConfig、RiskConfig、DataConfig、LoggingConfig、**MarginConfig、OrderExecutionConfig（Phase 26追加）**）
- `feature_manager.py`: 15特徴量統一管理・feature_order.json連携・システム統合
- `threshold_manager.py`: 動的閾値・パラメータ管理

**使用方法**:
```python
from src.core.config import load_config, get_threshold

config = load_config('config/core/unified.yaml', cmdline_mode='paper')
confidence = get_threshold('ml.default_confidence', 0.5)
```

### **システム統合制御 (orchestration/)**

**目的**: 高レベルシステム統合制御・MLサービス統合・取引サイクル管理

**主要ファイル**:
- `orchestrator.py`: 実行モード制御を含むメインシステム統合制御・取引サイクル実行（2025/09/20修正: execution_service統合）
- `protocols.py`: サービスプロトコル定義（Phase 22で移動・組織改善）
- `ml_adapter.py`: エラーハンドリング付き統一MLサービスインターフェース
- `ml_loader.py`: 優先度ベースMLモデル読み込み（ProductionEnsemble > 個別 > ダミー）
- `ml_fallback.py`: エラー復旧用フォールバックダミーモデル

**使用方法**:
```python
from src.core.orchestration import create_trading_orchestrator

orchestrator = await create_trading_orchestrator(config, logger)
await orchestrator.initialize()
await orchestrator.run()
```

### **実行モード管理 (execution/)**

**目的**: 異なる取引モードのストラテジーパターン実装

**主要ファイル**:
- `base_runner.py`: 共通実行機能を持つ基底クラス
- `paper_trading_runner.py`: セッション追跡付きペーパートレードモード実行
- `live_trading_runner.py`: 検証機能付きライブトレードモード実行

**使用方法**:
```python
from src.core.execution import PaperTradingRunner, LiveTradingRunner

paper_runner = PaperTradingRunner(orchestrator_ref, logger)
success = await paper_runner.run()
```

# Graceful Shutdown機能はservices/graceful_shutdown_manager.pyに統合済み（Phase 29最適化）

### **レポート生成 (reporting/)**

**目的**: ペーパートレードレポート生成（バックテストレポートはsrc/backtest/で処理）

**主要ファイル**:
- `base_reporter.py`: 基底レポート機能
- `paper_trading_reporter.py`: ペーパートレードセッションレポート・統計

**使用方法**:
```python
from src.core.reporting import PaperTradingReporter

reporter = PaperTradingReporter(logger)
report_path = await reporter.generate_session_report(session_stats)
```

### **システムサービス (services/)**

**目的**: システム監視、ヘルスチェック、運用サービス

**主要ファイル**:
- `health_checker.py`: 包括的システムヘルス監視
- `system_recovery.py`: エラー復旧・システム再起動機能
- `trading_cycle_manager.py`: 取引サイクル実行・ログ記録（2025/09/20修正: エラーハンドリング強化）
- `trading_logger.py`: 専門取引ログサービス
- `graceful_shutdown_manager.py`: システム終了管理（Phase 29統合）

**使用方法**:
```python
from src.core.services import HealthChecker, TradingCycleManager

health_checker = HealthChecker(config, logger)
is_healthy = await health_checker.check_system_health()

cycle_manager = TradingCycleManager(orchestrator_ref, logger)
result = await cycle_manager.execute_trading_cycle()
```

## 📝 コア基盤ファイル (Phase 22最適化)

### **logger.py**
JSTタイムゾーン対応の構造化ログシステム

**機能**:
- JSTタイムゾーン対応
- extra_data付き構造化ログ
- JSON/カラー出力フォーマット
- 複数ログレベル

### **exceptions.py**
エラーハンドリング用階層化カスタム例外システム

**保持クラス**: CryptoBotError(基底)、DataFetchError、ExchangeAPIError、TradingError、RiskManagementError、DataProcessingError、ModelLoadError、ModelPredictionError、FileIOError、HealthCheckError、StrategyError、PostOnlyCancelledException

## 🚀 使用例

### **基本システム初期化**
```python
from src.core.config import load_config
from src.core.logger import setup_logging
from src.core.orchestration import create_trading_orchestrator

# 設定・ログ初期化
config = load_config('config/core/unified.yaml', cmdline_mode='paper')
logger = setup_logging("crypto_bot")

# オーケストレーター作成
orchestrator = await create_trading_orchestrator(config, logger)

# システム実行
if await orchestrator.initialize():
    await orchestrator.run()
```

### **Graceful Shutdown管理（main.py軽量化対応）**
```python
from src.core.services import GracefulShutdownManager

# main.py での使用例
async def main():
    # 基本設定
    config = load_config('config/core/unified.yaml', cmdline_mode='paper')
    logger = setup_logging("crypto_bot")

    # オーケストレーター初期化
    orchestrator = await create_trading_orchestrator(config, logger)
    await orchestrator.initialize()

    # GracefulShutdownManager初期化（main.py軽量化）
    shutdown_manager = GracefulShutdownManager(logger)
    shutdown_manager.initialize(orchestrator)

    # メイン処理とshutdown監視を並行実行
    # SIGINT/SIGTERM受信時の適切な終了処理を自動化
    main_task = asyncio.create_task(orchestrator.run())
    await shutdown_manager.shutdown_with_main_task(main_task)
```

### **特徴量管理**
```python
from src.core.config.feature_manager import FeatureManager

# 15特徴量統一管理システム
fm = FeatureManager()
feature_names = fm.get_feature_names()          # 15特徴量名一覧
feature_count = fm.get_feature_count()          # 15
categories = fm.get_feature_categories()        # 7カテゴリ分類

# カテゴリ別取得
basic_features = fm.get_category_features('basic')      # ['close', 'volume']
breakout_features = fm.get_category_features('breakout') # ['donchian_high_20', 'donchian_low_20', 'channel_position']

# 整合性検証
features_valid = fm.validate_features(some_features)  # True/False
```

### **設定管理**
```python
from src.core.config import get_threshold, get_ml_config

# 基本閾値アクセス
confidence = get_threshold('ml.default_confidence', 0.5)
balance = get_threshold('trading.initial_balance_jpy', 10000.0)

# ML設定
emergency_stop = get_ml_config('emergency_stop_on_dummy', True)
```

### **エラーハンドリング**
```python
from src.core.exceptions import ModelLoadError, ModelPredictionError, ExchangeAPIError

try:
    predictions = ml_service.predict(features)
except ModelLoadError as e:
    logger.error(f"MLモデル読み込みエラー: {e}")
except ModelPredictionError as e:
    logger.error(f"ML予測エラー: {e}")
except ExchangeAPIError as e:
    logger.error(f"取引所APIエラー: {e}")
```

### **プロトコル使用 (Phase 22移動後)**
```python
from src.core.orchestration.protocols import MLServiceProtocol, RiskServiceProtocol

# 型安全なサービス注入
def create_orchestrator(ml_service: MLServiceProtocol, risk_service: RiskServiceProtocol):
    return TradingOrchestrator(ml_service, risk_service)
```

## ⚠️ 重要事項 (Phase 22最適化)

### **2025/09/24 Phase 23追加: モード別初期残高一元管理**
- **orchestrator.py**: mode_balances対応・大文字小文字統一（config.mode.lower()）
- **_get_actual_balance()**: unified.yamlのmode_balancesから残高取得・ペーパーモードAPI呼び出し回避
- **設定一元化**: 将来の残高変更（10万円・50万円）も設定ファイル1箇所修正で完結
### **2025/09/20修正: Silent Failure問題解決**
- **orchestrator.py**: execution_service設定修正（RiskManager → ExecutionService）
- **trading_cycle_manager.py**: AttributeErrorの詳細ログ追加・エラー可視性向上
- **ExecutionService統合**: 実際の取引実行機能を実装・BitbankClient.create_order呼び出し
- **システム復旧**: 0取引/24時間問題を根本解決・取引実行確保

### **2025/09/28 Phase 29: システム統合最適化**
- **services/graceful_shutdown_manager.py統合**: shutdownフォルダ廃止・サービス層統合でアーキテクチャ簡素化
- **32ファイル全更新**: 全コアコンポーネントのPhase 29マーカー統一

### **Phase 29最適化成果**
- **32ファイル全更新**: 全コアコンポーネントのPhase 29マーカー統一完了
- **アーキテクチャ最適化**: shutdown統合でシステム構造最適化
- **デプロイ前準備**: コードクリーンアップ・横断的機能配置最適化完了
- **企業級品質**: 639テスト100%成功・64.74%カバレッジ維持・品質ゲート通過

### **設計原則**
- **単一責任原則**: 各モジュールは明確で焦点の絞られた目的を持つ
- **依存性注入**: サービスはインスタンス化ではなく注入される
- **設定外部化**: ハードコード値なし、すべて設定可能
- **エラー復旧**: 段階的劣化・自動復旧機能

### **15特徴量統合システム**
- **統一管理**: feature_order.json（15特徴量）が全システムの単一真実源
- **7カテゴリ分類**: basic(2)・momentum(2)・volatility(2)・trend(2)・volume(1)・breakout(3)・regime(3)
- **整合性保証**: 特徴量順序・型・カテゴリの一貫性確保
- **システム連携**: 特徴量生成・戦略・ML・バックテストの完全統合

### **依存関係**
- **外部設定**: `config/core/unified.yaml`、`config/core/thresholds.yaml`
- **特徴量管理**: `config/core/feature_order.json`（15特徴量統一定義）
- **MLモデル**: `models/production/` ディレクトリ


### **テスト**
すべてのコアコンポーネントは以下でテストカバレッジを維持：
- `tests/unit/core/` の単体テスト
- サービス相互作用の統合テスト
- 設定検証テスト

---

**コア基盤**: 設定、統合制御、実行、レポート、サービスを提供する基盤層。