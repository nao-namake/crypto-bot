# core/ - 基盤システム

**Phase 12完了**: システム全体を支える核心的な基盤機能を提供するディレクトリです。環境変数・YAML統合・構造化ログ・Discord通知・階層化例外処理・統合システム制御・CI/CDワークフロー最適化・手動実行監視を実装しています（399テスト基盤・GitHub Actions対応）。

## 📁 ファイル構成

```
core/
├── config.py      # 設定管理システム ✅ Phase 12 CI/CDワークフロー最適化
├── logger.py      # ログシステム ✅ 手動実行監視対応
├── exceptions.py  # カスタム例外 ✅ GitHub Actions対応
└── orchestrator.py # 統合システム制御 ✅ 段階的デプロイ対応
```

## 🔧 各モジュール詳細

### config.py - 設定管理システム

**目的**: 環境変数とYAMLファイルの統合設定管理

**主要クラス**:
- `ExchangeConfig`: 取引所接続設定
- `MLConfig`: 機械学習設定
- `RiskConfig`: リスク管理設定
- `DataConfig`: データ取得設定
- `LoggingConfig`: ログ設定
- `Config`: 統合設定クラス

**使用例**:
```python
from src.core.config import Config

# YAML設定ファイル読み込み
config = Config.load_from_file('config/base.yaml')

# 設定検証
if config.validate():
    print("設定OK")

# 設定値取得
confidence_threshold = config.ml.confidence_threshold
leverage = config.risk.kelly_max_fraction
```

**特徴**:
- 環境変数による機密情報管理
- YAML による構造化設定
- 設定値の自動検証
- 420行から最小限に削減

### logger.py - ログシステム

**目的**: 構造化ログ出力とDiscord通知の統合

**主要機能**:
- 構造化ログ出力（JSON形式）
- レベル別ログフィルタリング
- Discord通知統合（3階層）
- ファイルローテーション

**使用例**:
```python
from src.core.logger import get_logger

logger = get_logger()

# 基本ログ
logger.info("取引開始")

# 構造化ログ
logger.info(
    "取引実行",
    extra_data={
        'symbol': 'BTC/JPY',
        'side': 'buy',
        'amount': 0.001
    }
)

# エラーログ（Discord通知）
logger.error("API接続失敗", error=e)
```

**Discord通知レベル**:
- **Critical**: 取引停止、重大エラー
- **Warning**: API遅延、異常値検知
- **Info**: 日次サマリー、システム状態

### exceptions.py - カスタム例外

**目的**: 統一されたエラーハンドリングとコンテキスト情報の提供

**主要例外クラス**:
- `ExchangeAPIError`: 取引所API関連エラー
- `DataFetchError`: データ取得エラー
- `ConfigurationError`: 設定関連エラー
- `TradingError`: 取引実行エラー
- `RiskManagementError`: リスク管理エラー

**使用例**:
```python
from src.core.exceptions import DataFetchError

try:
    data = fetch_market_data()
except Exception as e:
    raise DataFetchError(
        "市場データ取得に失敗",
        context={
            'symbol': 'BTC/JPY',
            'timeframe': '1h',
            'retry_count': 3
        }
    ) from e
```

**特徴**:
- コンテキスト情報付きエラー
- 階層的例外構造
- ログシステム連携
- デバッグ情報の自動収集

### orchestrator.py - 統合システム制御 🆕

**目的**: Application Service Layer として Phase 1-6の高レベル統合制御

**主要クラス**:
- `TradingOrchestrator`: 統合取引システム制御
- `DataServiceProtocol`: データ層インターフェース  
- `FeatureServiceProtocol`: 特徴量生成インターフェース
- `StrategyServiceProtocol`: 戦略評価インターフェース
- `MLServiceProtocol`: ML予測インターフェース
- `RiskServiceProtocol`: リスク管理インターフェース

**使用例**:
```python
from src.core.orchestrator import create_trading_orchestrator

# ファクトリー関数による簡単作成
orchestrator = await create_trading_orchestrator(config, logger)

# 初期化確認
if await orchestrator.initialize():
    # 実行
    await orchestrator.run("paper")
```

**設計原則**:
- **Application Service Pattern**: 高レベルフロー制御のみ
- **依存性注入**: 完全にモック可能な設計
- **責任分離**: 具体的実装は各Phase層に委譲
- **Protocol使用**: 型安全性とテスト容易性確保

**メリット**:
1. **テスト容易性**: 各サービスを独立してモック可能
2. **保守性**: main.pyを変更せずに機能拡張可能  
3. **可読性**: システム全体のフローが明確
4. **拡張性**: 新モードやPhaseの追加が容易

**ファクトリー関数**:
- `create_trading_orchestrator()`: 依存性組み立て自動化
- main.pyからの利用を簡潔化
- 各Phase層の初期化詳細を隠蔽

## 🎯 設計方針

### レイヤー分離の徹底 🆕
- **main.py**: エントリーポイント特化（90行以内）
- **orchestrator.py**: Application Service Layer（統合制御）
- **各Phase層**: Domain Logic（具体的ビジネスロジック）

### 責任分離原則 🆕
- **main.py責任**: 引数解析・基本設定・エラーハンドリング
- **orchestrator責任**: システム統合・フロー制御・サービス協調
- **Phase層責任**: 専門的処理・データ変換・具体的計算

### テスト容易性優先 🆕
- Protocol（インターフェース）による依存性注入
- 各層が独立してテスト可能
- モック・スタブによる隔離テスト
- main.pyはテスト不要レベルまで薄く設計

### シンプルさ優先
- 複雑な機能は排除
- 個人開発に特化した設計
- 保守性を重視

### 堅牢性確保
- 適切なエラーハンドリング
- 設定値の検証機能
- 失敗時の安全な動作

### 統合性
- 全システムで共通の基盤
- 一貫したログ出力
- 統一されたエラー処理

## 🔧 開発ガイドライン

### main.py開発ルール 🆕
- **90行以内を厳守**: エントリーポイント特化を維持
- **ビジネスロジック禁止**: 具体的処理はorchestratorに委譲
- **変更最小化**: 新機能追加時もmain.pyは変更しない
- **テスト不要設計**: シンプルすぎてテストが不要なレベル

### orchestrator開発ルール 🆕
- **高レベル制御のみ**: 具体的実装は各Phase層に委譲
- **Protocol使用**: インターフェースによる疎結合設計
- **ファクトリー活用**: create_trading_orchestrator()で依存性組み立て
- **テスト容易性**: 各サービスをモック可能な設計

### Phase 7以降開発時 🆕
- **main.py不変**: 新機能追加時もmain.pyは変更しない
- **orchestrator経由**: 新サービスはProtocolを実装してorchestratorに注入
- **ファクトリー更新**: create_trading_orchestrator()に新サービス追加

### 設定追加時
1. 適切なConfigクラスに新フィールド追加
2. validate()メソッドに検証ロジック追加
3. get_summary()で機密情報除外

### ログ出力時
- 構造化ログを活用
- 機密情報（APIキー等）は除外
- レベルを適切に設定

### 例外処理時
- 適切なカスタム例外を使用
- コンテキスト情報を含める
- ログ出力と連携

## 📊 依存関係

**外部ライブラリ**:
- `pyyaml`: YAML設定ファイル読み込み
- `dataclasses`: 設定データクラス

**内部依存**:
- なし（基盤システムのため）
- orchestrator.pyは各Phase層に依存（ファクトリー関数内のみ）

## 🧪 テスト状況

### Phase 2手動テスト（100%合格）
```bash
# 基盤システム動作確認（設定システムテスト含む）
python tests/manual/test_phase2_components.py

# 個別コンポーネント確認
python -c "from src.core.config import Config; print('✅ Config OK')"
python -c "from src.core.logger import get_logger; print('✅ Logger OK')"
python -c "from src.core.exceptions import ConfigurationError; print('✅ Exceptions OK')"
```

### Phase 12テスト環境（CI/CDワークフロー最適化）
```bash
# 手動テスト（100%合格）
python tests/manual/test_phase2_components.py

# 399テスト実行基盤（Phase 12完了・GitHub Actions統合）
python -m pytest tests/unit/strategies/ tests/unit/ml/ tests/unit/backtest/ tests/unit/trading/ -v

# 統合管理CLI経由確認（推奨・Phase 12対応）
python scripts/management/dev_check.py health-check
python scripts/management/dev_check.py validate --mode light

# 基盤システム動作確認
python -c "from src.core.orchestrator import create_trading_orchestrator; print('✅ Orchestrator OK')"
```

## 🏆 Phase 12達成成果

- **✅ 設定管理**: 420行→最小限削減・環境変数統合・検証機能・Phase 12品質保証・CI/CDワークフロー最適化
- **✅ ログシステム**: JSON構造化・Discord 3階層通知・日次ローテーション・399テスト対応・手動実行監視統合
- **✅ 例外処理**: 階層化カスタム例外・コンテキスト情報・ログ連携・包括的エラーハンドリング・GitHub Actions対応
- **✅ 統合制御**: orchestrator.py実装・Application Service Layer・399テスト基盤構築・段階的デプロイ対応
- **✅ 品質保証**: Phase 12完了・399テスト・68.13%合格・包括的システム基盤・CI/CDワークフロー最適化・手動実行監視

---

**Phase 12完了**: *信頼性とシンプルさ・品質保証・CI/CDワークフロー最適化・手動実行監視を両立した統合基盤システム実装完了*