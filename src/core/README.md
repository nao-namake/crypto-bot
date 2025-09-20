# src/core/ - コアシステム基盤 (Phase 22最適化完了)

## 🎯 役割・責任

AI自動取引システムのコアシステム基盤層。設定管理、ログシステム、統合制御、実行モード管理、レポート生成、サービスコンポーネントを提供。システム統合、MLモデル管理、取引実行制御、運用監視を担当し、全システムの基盤として機能します。

**Phase 22最適化**: 未使用コード削除（423行）・構造最適化・保守性向上を実現し、企業級コード品質を確立。

## 📂 ディレクトリ構成

```
src/core/
├── __init__.py                    # コアモジュールエクスポート (Phase 22最適化)
├── logger.py                      # JST対応ログシステム・Discord統合
├── exceptions.py                  # カスタム例外階層 (Phase 22スリム化)
│
├── config/                        # 設定管理システム
│   ├── __init__.py                # 設定ローダー・階層化設定管理
│   ├── config_classes.py          # 設定dataclass定義
│   ├── feature_manager.py         # 特徴量統一管理
│   └── threshold_manager.py       # 閾値・動的設定管理
│
├── orchestration/                 # システム統合制御
│   ├── __init__.py                # 統合制御エクスポート
│   ├── orchestrator.py            # メインシステム統合制御
│   ├── protocols.py               # サービスプロトコル定義 (Phase 22移動)
│   ├── ml_adapter.py              # MLサービス統合
│   ├── ml_loader.py               # MLモデル読み込み
│   └── ml_fallback.py             # MLフォールバック機能
│
├── execution/                     # 実行モード管理
│   ├── __init__.py                # 実行モードエクスポート
│   ├── base_runner.py             # 基底実行ランナー
│   ├── paper_trading_runner.py    # ペーパートレード実行
│   └── live_trading_runner.py     # ライブトレード実行
│
├── reporting/                     # レポート生成
│   ├── __init__.py                # レポートエクスポート
│   ├── base_reporter.py           # 基底レポート機能
│   └── paper_trading_reporter.py  # ペーパートレードレポート
│
└── services/                      # システムサービス
    ├── __init__.py                # サービス層エクスポート
    ├── health_checker.py          # システムヘルス監視
    ├── system_recovery.py         # システム復旧
    ├── trading_cycle_manager.py   # 取引サイクル管理
    └── trading_logger.py          # 取引ログサービス
```

## 🔧 主要コンポーネント

### **設定管理システム (config/)**

**目的**: YAML設定ファイルによる集約的設定システム・15特徴量統一管理

**主要ファイル**:
- `__init__.py`: 3層優先度（CLI > 環境変数 > YAML）の設定ローダー
- `config_classes.py`: 5つのdataclass定義（ExchangeConfig、MLConfig、RiskConfig、DataConfig、LoggingConfig）
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

### **レポート生成 (reporting/)**

**目的**: ペーパートレードレポート生成（バックテストレポートはsrc/backtest/で処理）

**主要ファイル**:
- `base_reporter.py`: マークダウン・Discord対応の基底レポート機能
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
構造化出力・Discord webhook統合付きJSTタイムゾーンログシステム

**機能**:
- JSTタイムゾーン対応
- extra_data付き構造化ログ
- Discord通知統合
- 複数ログレベル・フォーマット

### **exceptions.py (Phase 22スリム化完了)**
エラーハンドリング用階層化カスタム例外システム

**機能** (最適化後):
- 実際に使用される例外のみ保持
- 削除: NotificationError, APITimeoutError, APIAuthenticationError等（10クラス）
- 保持: 取引固有例外、MLモデル例外、取引所API例外、システム復旧例外
- エラー重要度マッピング最適化

**Phase 22最適化内容**:
- **削除済み**: `market_data.py` (423行完全未使用コード)
- **移動済み**: `protocols.py` → `orchestration/protocols.py` (組織改善)
- **スリム化済み**: `exceptions.py` 未使用例外クラス削除（10クラス削除）

## 🚀 使用例

### **基本システム初期化**
```python
from src.core import load_config, setup_logging, create_trading_orchestrator

# 設定・ログ初期化
config = load_config('config/core/unified.yaml', cmdline_mode='paper')
logger = setup_logging("crypto_bot")

# オーケストレーター作成
orchestrator = await create_trading_orchestrator(config, logger)

# システム実行
if await orchestrator.initialize():
    await orchestrator.run()
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

### **エラーハンドリング (Phase 22最適化)**
```python
from src.core.exceptions import ModelLoadError, ModelPredictionError, ExchangeAPIError

try:
    predictions = ml_service.predict(features)
except ModelLoadError as e:
    logger.error(f"MLモデル読み込みエラー: {e}", discord_notify=True)
except ModelPredictionError as e:
    logger.error(f"ML予測エラー: {e}", discord_notify=True)  
except ExchangeAPIError as e:
    logger.error(f"取引所APIエラー: {e}", discord_notify=True)
```

### **プロトコル使用 (Phase 22移動後)**
```python
from src.core.orchestration.protocols import MLServiceProtocol, RiskServiceProtocol

# 型安全なサービス注入
def create_orchestrator(ml_service: MLServiceProtocol, risk_service: RiskServiceProtocol):
    return TradingOrchestrator(ml_service, risk_service)
```

## ⚠️ 重要事項 (Phase 22最適化)

### **2025/09/20修正: Silent Failure問題解決**
- **orchestrator.py**: execution_service設定修正（RiskManager → ExecutionService）
- **trading_cycle_manager.py**: AttributeErrorの詳細ログ追加・エラー可視性向上
- **ExecutionService統合**: 実際の取引実行機能を実装・BitbankClient.create_order呼び出し
- **システム復旧**: 0取引/24時間問題を根本解決・取引実行確保

### **Phase 22最適化成果**
- **コード削減**: 423行の完全未使用コード削除（market_data.py）
- **構造改善**: protocols.pyをorchestration/に移動・責任明確化
- **例外最適化**: 10個の未使用例外クラス削除・保守性向上
- **Phase統一**: 全ファイルのPhase番号をPhase 22に統一
- **品質向上**: 625テスト通過維持・58.64%カバレッジ保持

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
- **Discord統合**: 通知用webhook設定

### **テスト**
すべてのコアコンポーネントは以下でテストカバレッジを維持：
- `tests/unit/core/` の単体テスト
- サービス相互作用の統合テスト
- 設定検証テスト

---

**コア基盤 (Phase 22最適化完了)**: AI自動取引システムが異なるモードと環境で確実に動作するための設定、統合制御、実行、レポート、サービスを可能にする基盤層。15特徴量統一管理・5戦略統合・MLモデル統合により、包括的なシステム基盤を提供。

**Phase 22成果**: 未使用コード削除・構造最適化・保守性向上により企業級コード品質を実現。423行削除・10例外クラス最適化・プロトコル再配置完了。