# src/core/ - コアシステム基盤

## 🎯 役割・責任

AI自動取引システムのコアシステム基盤層。設定管理、ログシステム、統合制御、実行モード管理、レポート生成、サービスコンポーネントを提供。システム統合、MLモデル管理、取引実行制御、運用監視を担当。

## 📂 ディレクトリ構成

```
src/core/
├── __init__.py                    # コアモジュールエクスポート（105行）
├── logger.py                      # JST対応ログシステム・Discord統合（415行）
├── market_data.py                 # マーケットデータ構造（422行）
├── exceptions.py                  # カスタム例外階層（310行）
├── protocols.py                   # サービスプロトコル定義（60行）
│
├── config/                        # 設定管理システム
│   ├── __init__.py                # 設定ローダー（412行）
│   ├── config_classes.py          # 設定dataclass定義（5クラス）
│   ├── feature_manager.py         # 12特徴量統一管理
│   └── threshold_manager.py       # 閾値・動的設定管理（211行）
│
├── orchestration/                 # システム統合制御
│   ├── __init__.py                # 統合制御エクスポート
│   ├── orchestrator.py            # メインシステム統合制御（365行）
│   ├── ml_adapter.py              # MLサービス統合（393行）
│   ├── ml_loader.py               # MLモデル読み込み（171行）
│   └── ml_fallback.py             # MLフォールバック機能（38行）
│
├── execution/                     # 実行モード管理
│   ├── __init__.py                # 実行モードエクスポート
│   ├── base_runner.py             # 基底実行ランナー（191行）
│   ├── paper_trading_runner.py    # ペーパートレード実行（216行）
│   └── live_trading_runner.py     # ライブトレード実行（293行）
│
├── reporting/                     # レポート生成
│   ├── __init__.py                # レポートエクスポート
│   ├── base_reporter.py           # 基底レポート機能（192行）
│   └── paper_trading_reporter.py  # ペーパートレードレポート（322行）
│
└── services/                      # システムサービス
    ├── __init__.py                # サービス層エクスポート
    ├── health_checker.py          # システムヘルス監視（171行）
    ├── system_recovery.py         # システム復旧（215行）
    ├── trading_cycle_manager.py   # 取引サイクル管理（358行）
    └── trading_logger.py          # 取引ログサービス（253行）
```

## 🔧 主要コンポーネント

### **設定管理システム (config/)**

**目的**: YAML設定ファイルによる集約的設定システム

**主要ファイル**:
- `__init__.py`（412行）: 3層優先度（CLI > 環境変数 > YAML）の設定ローダー
- `config_classes.py`: 5つのdataclass定義（ExchangeConfig、MLConfig、RiskConfig、DataConfig、LoggingConfig）
- `feature_manager.py`: ML統合のための12特徴量統一管理
- `threshold_manager.py`（211行）: 動的閾値・パラメータ管理

**使用方法**:
```python
from src.core.config import load_config, get_threshold

config = load_config('config/core/unified.yaml', cmdline_mode='paper')
confidence = get_threshold('ml.default_confidence', 0.5)
```

### **システム統合制御 (orchestration/)**

**目的**: 高レベルシステム統合制御・MLサービス統合

**主要ファイル**:
- `orchestrator.py`（365行）: 実行モード制御を含むメインシステム統合制御
- `ml_adapter.py`（393行）: エラーハンドリング付き統一MLサービスインターフェース
- `ml_loader.py`（171行）: 優先度ベースMLモデル読み込み（ProductionEnsemble > 個別 > ダミー）
- `ml_fallback.py`（38行）: エラー復旧用フォールバックダミーモデル

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
- `base_runner.py`（191行）: 共通実行機能を持つ基底クラス
- `paper_trading_runner.py`（216行）: セッション追跡付きペーパートレードモード実行
- `live_trading_runner.py`（293行）: 検証機能付きライブトレードモード実行

**使用方法**:
```python
from src.core.execution import PaperTradingRunner, LiveTradingRunner

paper_runner = PaperTradingRunner(orchestrator_ref, logger)
success = await paper_runner.run()
```

### **レポート生成 (reporting/)**

**目的**: ペーパートレードレポート生成（バックテストレポートはsrc/backtest/で処理）

**主要ファイル**:
- `base_reporter.py`（192行）: マークダウン・Discord対応の基底レポート機能
- `paper_trading_reporter.py`（322行）: ペーパートレードセッションレポート・統計

**使用方法**:
```python
from src.core.reporting import PaperTradingReporter

reporter = PaperTradingReporter(logger)
report_path = await reporter.generate_session_report(session_stats)
```

### **システムサービス (services/)**

**目的**: システム監視、ヘルスチェック、運用サービス

**主要ファイル**:
- `health_checker.py`（171行）: 包括的システムヘルス監視
- `system_recovery.py`（215行）: エラー復旧・システム再起動機能
- `trading_cycle_manager.py`（358行）: 取引サイクル実行・ログ記録
- `trading_logger.py`（253行）: 専門取引ログサービス

**使用方法**:
```python
from src.core.services import HealthChecker, TradingCycleManager

health_checker = HealthChecker(config, logger)
is_healthy = await health_checker.check_system_health()

cycle_manager = TradingCycleManager(orchestrator_ref, logger)
result = await cycle_manager.execute_trading_cycle()
```

## 📝 コア基盤ファイル

### **logger.py（415行）**
構造化出力・Discord webhook統合付きJSTタイムゾーンログシステム

**機能**:
- JSTタイムゾーン対応
- extra_data付き構造化ログ
- Discord通知統合
- 複数ログレベル・フォーマット

### **market_data.py（422行）**
取引オペレーション用統一マーケットデータ構造・dataclass

**機能**:
- マーケットデータdataclass
- 価格・出来高構造
- OHLCV データ処理

### **exceptions.py（310行）**
エラーハンドリング用階層化カスタム例外システム

**機能**:
- 取引固有例外
- MLモデル例外
- 取引所API例外
- システム復旧例外

### **protocols.py（60行）**
型安全性・サービスインターフェース用プロトコル定義

**機能**:
- サービスプロトコル定義
- 依存性注入の型安全性
- インターフェース契約

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
from src.core.exceptions import MLModelError, ExchangeAPIError

try:
    predictions = ml_service.predict(features)
except MLModelError as e:
    logger.error(f"MLモデルエラー: {e}", discord_notify=True)
except ExchangeAPIError as e:
    logger.error(f"取引所APIエラー: {e}", discord_notify=True)
```

## ⚠️ 重要事項

### **設計原則**
- **単一責任原則**: 各モジュールは明確で焦点の絞られた目的を持つ
- **依存性注入**: サービスはインスタンス化ではなく注入される
- **設定外部化**: ハードコード値なし、すべて設定可能
- **エラー復旧**: 段階的劣化・自動復旧機能

### **依存関係**
- **外部設定**: `config/core/unified.yaml`、`config/core/thresholds.yaml`
- **特徴量管理**: `config/core/feature_order.json`
- **MLモデル**: `models/production/` ディレクトリ
- **Discord統合**: 通知用webhook設定

### **テスト**
すべてのコアコンポーネントは以下でテストカバレッジを維持：
- `tests/unit/core/` の単体テスト
- サービス相互作用の統合テスト
- 設定検証テスト

---

**コア基盤**: AI自動取引システムが異なるモードと環境で確実に動作するための設定、統合制御、実行、レポート、サービスを可能にする基盤層を提供。