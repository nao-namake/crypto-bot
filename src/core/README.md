# core/ - 基盤システム

**Phase 13完了**: システム全体を支える核心的な基盤機能を提供するディレクトリです。環境変数・YAML統合・構造化ログ・Discord通知・階層化例外処理・統合システム制御・Config型不一致修正・to_dict()メソッド追加・本番モード設定最適化・API設定重複エラー完全修正を実装しています（全テスト対応・GitHub Actions統合・Cloud Run本番運用対応）。

**最新修正（2025年8月23日）**: 
- ✅ **orchestrator.py クラス名不整合修正**: MochiPoyAlertStrategy→MochipoyAlertStrategyに修正・Cloud Runコンテナクラッシュ解消
- ✅ **config.py API設定重複エラー完全修正**: ExchangeConfig YAML/環境変数競合解決・api_key重複問題解決
- ✅ **統合設定システム強化**: dataclass全フィールド対応・MLConfig/RiskConfig/DataConfig/LoggingConfig拡張完了
- ✅ **環境変数優先設計**: YAMLファイルapi_key/api_secret除外処理・セキュリティ強化・本番運用対応
- ✅ **型安全性確保**: Optional型活用・デフォルト値統一・__post_init__メソッド活用・設定検証強化

## 📁 ファイル構成

```
core/
├── config.py      # 設定管理システム ✅ Phase 13 CI/CDワークフロー最適化
├── logger.py      # ログシステム ✅ 手動実行監視対応
├── exceptions.py  # カスタム例外 ✅ GitHub Actions対応
├── orchestrator.py # 統合システム制御 ✅ 段階的デプロイ対応
└── ml_adapter.py  # MLサービス統合 ✅ 根本問題解決対応
```

## 🔧 各モジュール詳細

### config.py - 設定管理システム（モード設定一元化完了）

**目的**: 環境変数とYAMLファイルの統合設定管理、モード設定一元化

**🎯 モード設定3層優先順位**:
1. **コマンドライン引数**（最優先）: `--mode live`
2. **環境変数**（中優先）: `MODE=live`  
3. **YAMLファイル**（デフォルト）: `mode: paper`

**主要クラス**:
- `ExchangeConfig`: 取引所接続設定
- `MLConfig`: 機械学習設定
- `RiskConfig`: リスク管理設定
- `DataConfig`: データ取得設定
- `LoggingConfig`: ログ設定
- `Config`: 統合設定クラス（モード設定一元化対応）

**モード設定一元化の使用例**:
```python
from src.core.config import Config

# 基本使用法（3層優先順位自動適用）
config = Config.load_from_file('config/base.yaml', cmdline_mode='live')

# モード確認
print(f"実行モード: {config.mode}")  # live/paper/backtest

# 設定検証（ライブモード時はAPI認証必須）
if config.validate():
    print("設定OK")

# 設定値取得
confidence_threshold = config.ml.confidence_threshold
leverage = config.risk.kelly_max_fraction
```

**モード設定ルール**:
- ✅ **システム全体で単一のモード設定**
- ✅ **環境変数とコードの大文字小文字統一**（環境変数=`MODE`、コード=`mode`）
- ✅ **設定不整合によるミストレード防止**
- ✅ **テスト時のモック対応**

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

### ml_adapter.py - MLサービス統合アダプター 🆕

**目的**: MLモデル未学習エラーの根本的解決とサービス統合

**主要クラス**:
- `MLServiceAdapter`: ML予測サービス統合アダプター
- `DummyModel`: 最終フォールバック用安全モデル  

**優先順位付きモデル読み込み**:
1. **ProductionEnsemble**（最優先）: `models/production/production_ensemble.pkl`
2. **個別モデル再構築**（代替）: `models/training/` から自動再構築
3. **ダミーモデル**（最終安全網）: 常にholdシグナル（信頼度0.5）

**使用例**:
```python
from src.core.ml_adapter import MLServiceAdapter

# 自動モデル読み込み（優先順位適用）
ml_service = MLServiceAdapter(logger)

# 統一インターフェース
predictions = ml_service.predict(features_df, use_confidence=True)

# モデル情報確認
print(ml_service.get_model_info())  
# {'model_type': 'ProductionEnsemble', 'is_fitted': True}
```

**根本問題解決機能**:
- **完全停止防止**: 全モデル読み込み失敗でもダミーモデルで継続稼働
- **自動復旧**: 個別モデルからの自動再構築機能  
- **統一インターフェース**: ProductionEnsemble・EnsembleModelの差異を吸収
- **エラー記録**: 詳細なログ出力で問題特定を支援

**設計原則**:
- **フォールバック階層**: 3段階の安全ネット構造
- **統合インターフェース**: 既存コードへの影響最小化
- **自動復旧機能**: 運用中の手動介入不要
- **透明性確保**: モデル状態の可視化

**メリット**:
1. **システム継続稼働**: MLモデルエラーでの完全停止を防止
2. **運用負荷軽減**: 自動復旧により手動対応を削減
3. **開発効率向上**: 統一インターフェースで開発・テスト簡素化
4. **信頼性向上**: 複数の安全ネットによる堅牢な動作保証

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

### Phase 13テスト環境（CI/CDワークフロー最適化）
```bash
# 手動テスト（100%合格）
python tests/manual/test_phase2_components.py

# 399テスト実行基盤（Phase 13完了・GitHub Actions統合）
python -m pytest tests/unit/strategies/ tests/unit/ml/ tests/unit/backtest/ tests/unit/trading/ -v

# 統合管理CLI経由確認（推奨・Phase 13対応）
python scripts/management/dev_check.py health-check
python scripts/management/dev_check.py validate --mode light

# 基盤システム動作確認
python -c "from src.core.orchestrator import create_trading_orchestrator; print('✅ Orchestrator OK')"
```

## 🏆 Phase 13達成成果

- **✅ 設定管理**: 420行→最小限削減・環境変数統合・検証機能・Phase 13品質保証・CI/CDワークフロー最適化
- **✅ ログシステム**: JSON構造化・Discord 3階層通知・日次ローテーション・399テスト対応・手動実行監視統合
- **✅ 例外処理**: 階層化カスタム例外・コンテキスト情報・ログ連携・包括的エラーハンドリング・GitHub Actions対応
- **✅ 統合制御**: orchestrator.py実装・Application Service Layer・399テスト基盤構築・段階的デプロイ対応
- **✅ 品質保証**: Phase 13完了・399テスト・68.13%合格・包括的システム基盤・CI/CDワークフロー最適化・手動実行監視

---

**Phase 13完了**: *信頼性とシンプルさ・品質保証・CI/CDワークフロー最適化・手動実行監視を両立した統合基盤システム実装完了*