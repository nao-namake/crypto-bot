# src/core/orchestration - 統合制御システム 📋 Phase 52.4

Application Service Layerとして、システム全体の統合制御・ML統合・高レベルフロー制御を提供。
6コンポーネントによる堅牢なシステム統合基盤。

---

## 📂 ファイル構成

### 主要ファイル

- **`orchestrator.py`** (574行・46%): 統合取引システム制御・TradingOrchestrator
- **`ml_loader.py`** (324行): MLモデル読み込み管理・3段階Graceful Degradation
- **`ml_adapter.py`** (192行): ML予測統合インターフェース・ProductionEnsemble統一
- **`protocols.py`** (73行): サービスプロトコル定義・依存性注入基盤
- **`ml_fallback.py`** (58行): DummyModelフォールバック・最終安全装置
- **`__init__.py`** (19行): モジュールエクスポート

**総行数**: 1,240行

---

## 🏗️ アーキテクチャ

### Application Service Layer設計

orchestration層は**Application Service Layer**として設計され、高レベルフロー制御のみを担当します。

```
┌─────────────────────────────────────────────────────────┐
│           Application Service Layer                     │
│           (orchestration層)                             │
├─────────────────────────────────────────────────────────┤
│  TradingOrchestrator                                    │
│  ├─ データ取得 (DataService)                            │
│  ├─ 特徴量生成 (FeatureGenerator)                       │
│  ├─ 戦略実行 (StrategyManager)                          │
│  ├─ ML予測 (MLServiceAdapter)                           │
│  ├─ リスク評価 (IntegratedRiskManager)                  │
│  └─ 取引判断 (ExecutionService)                         │
└─────────────────────────────────────────────────────────┘
         ↓  依存性注入（Protocol型ヒント）
┌─────────────────────────────────────────────────────────┐
│              各サービス層（具体的実装）                  │
│  data・features・strategies・ml・trading                │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 コンポーネント詳細

### 1. TradingOrchestrator（orchestrator.py）

**責任**: システム全体の統合制御・高レベルフロー制御

**主要機能**:
- **データフロー統合**: データ取得→特徴量生成→戦略実行→ML予測→リスク評価→取引判断
- **依存性注入**: Protocol型ヒントによる各サービス層注入
- **モード別実行制御**: backtest/paper/liveモード対応
- **エラーハンドリング階層化**: DataFetchError・ModelPredictionError・TradingError等
- **バックテスト最適化**: ログレベル動的変更・Discord無効化

**設計原則**:
- Application Service Pattern（高レベルフロー制御のみ）
- 依存性注入（テスト容易性確保）
- 責任分離（具体的実装は各層に委譲）

**使用例**:
```python
from src.core.orchestration import create_trading_orchestrator

# TradingOrchestrator作成（依存性注入）
orchestrator = await create_trading_orchestrator(
    mode="paper",  # backtest/paper/live
    config=config,
    logger=logger
)

# 取引サイクル実行
await orchestrator.run_trading_cycle()
```

---

### 2. MLServiceAdapter（ml_adapter.py）

**責任**: ML予測統合インターフェース・ProductionEnsemble統一

**主要機能**:
- **ProductionEnsemble統一インターフェース**: 3モデルアンサンブル予測（LightGBM・XGBoost・RandomForest）
- **3段階Graceful Degradation**: ensemble_full → ensemble_basic → DummyModel
- **特徴量数自動判定**: ensure_correct_model()による動的モデル切り替え
- **予測信頼度自動計算**: 確率分布ベース信頼度算出
- **3クラス分類対応**: buy/hold/sell

**Graceful Degradationフロー**:
```
1. ensemble_full.pkl読み込み試行
   ↓（失敗）
2. ensemble_basic.pkl読み込み試行
   ↓（失敗）
3. DummyModel使用（hold固定）
```

**使用例**:
```python
from src.core.orchestration import MLServiceAdapter

# MLアダプター初期化
ml_adapter = MLServiceAdapter(logger=logger)

# 予測実行
predictions = ml_adapter.predict(features_df)  # np.ndarray
```

---

### 3. MLModelLoader（ml_loader.py）

**責任**: MLモデル読み込み管理・個別モデル再構築

**主要機能**:
- **ProductionEnsemble読み込み**: ensemble_full.pkl/ensemble_basic.pkl
- **個別モデル再構築**: LightGBM・XGBoost・RandomForestの動的再構築
- **環境判定**: GCP Cloud Run / ローカル環境自動判定
- **特徴量数自動判定**: feature_order.json設定駆動型
- **pickle.UnpicklingError対応**: モデルクラス再定義

**モデル読み込み優先順位**:
```yaml
# config/core/thresholds.yaml
ml:
  model_paths:
    base_path: /app  # GCP Cloud Run
    local_path: .    # ローカル環境
```

**3段階Graceful Degradation**:
| Level | モデルファイル | 特徴量数 | 説明 |
|-------|--------------|---------|------|
| 1 | ensemble_full.pkl | 全特徴量 | デフォルト（戦略信号含む） |
| 2 | ensemble_basic.pkl | 基本特徴量 | フォールバック（戦略信号なし） |
| 3 | DummyModel | 任意 | 最終フォールバック（hold固定） |

---

### 4. DummyModel（ml_fallback.py）

**責任**: 最終フォールバック・システム継続動作保証

**主要機能**:
- **hold固定予測**: 全予測でhold（信頼度0.5）を返却
- **3クラス分類対応**: buy/hold/sell（hold=1, buy/sell=0）
- **is_fitted=True固定**: 常に利用可能状態
- **特徴量数任意対応**: 任意の特徴量数で動作

**設計思想**:
- MLモデル読み込み失敗時でもシステム継続動作保証
- 安全第一（hold固定でポジションを取らない）
- ゼロダウンタイム実現

**使用例**:
```python
from src.core.orchestration.ml_fallback import DummyModel

dummy = DummyModel()
predictions = dummy.predict(X)  # 全てhold（クラス1）
```

---

### 5. Protocols（protocols.py）

**責任**: サービスプロトコル定義・依存性注入基盤

**主要機能**:
- **6サービスプロトコル定義**:
  - `DataServiceProtocol`: データ層インターフェース
  - `FeatureServiceProtocol`: 特徴量層インターフェース
  - `StrategyServiceProtocol`: 戦略層インターフェース
  - `MLServiceProtocol`: ML層インターフェース
  - `ExecutionServiceProtocol`: 実行層インターフェース
  - `RiskServiceProtocol`: リスク管理層インターフェース
- **Protocol型ヒントシステム**: typing.Protocol基盤・型安全性確保
- **循環インポート回避**: TYPE_CHECKING条件分岐

**使用例**:
```python
from src.core.orchestration.protocols import DataServiceProtocol

class MyDataService:
    async def fetch_multi_timeframe(self, symbol: str, limit: int):
        # 実装...
        pass

# TradingOrchestratorへ注入
orchestrator = TradingOrchestrator(
    data_service=my_data_service,  # Protocol準拠確認
    # ...
)
```

---

## 📊 データフロー

### 取引サイクル完全フロー

```
1. データ取得（DataService）
   ↓ multi_timeframe_data
2. 特徴量生成（FeatureGenerator）
   ↓ features_df
3. 戦略実行（StrategyManager）
   ↓ strategy_signal
4. ML予測（MLServiceAdapter）
   ↓ ml_prediction + confidence
5. リスク評価（IntegratedRiskManager）
   ↓ position_size + risk_metrics
6. 取引判断（ExecutionService）
   ↓ ExecutionResult
7. 結果返却
```

### ML予測詳細フロー

```
MLServiceAdapter.predict(features_df)
  ↓
ensure_correct_model(features_df)  # 特徴量数判定
  ↓
ProductionEnsemble.predict_proba(features_df)
  ├─ LightGBM (40%)
  ├─ XGBoost (40%)
  └─ RandomForest (20%)
  ↓（アンサンブル）
weighted_probabilities
  ↓（信頼度計算）
final_prediction + confidence
```

---

## ⚙️ 設定ファイル連携

### config/core/thresholds.yaml

**ML設定**:
```yaml
ml:
  default_confidence: 0.5
  dummy_confidence: 0.5
  model_paths:
    base_path: /app
    local_path: .
    training_path: models/training
```

**バックテスト設定**:
```yaml
backtest:
  log_level: WARNING
  discord_enabled: false
```

### config/core/feature_order.json

**特徴量レベル定義**:
```json
{
  "feature_levels": {
    "full": {
      "count": 60,
      "model_file": "ensemble_full.pkl"
    },
    "basic": {
      "count": 57,
      "model_file": "ensemble_basic.pkl"
    }
  }
}
```

---

## 🚀 使用方法

### TradingOrchestrator作成

```python
from src.core.orchestration import create_trading_orchestrator

# orchestrator作成（依存性注入）
orchestrator = await create_trading_orchestrator(
    mode="paper",
    config=config,
    logger=logger
)

# 各サービス層アクセス
data_service = orchestrator.data_service
strategy_manager = orchestrator.strategy_manager
execution_service = orchestrator.execution_service
```

### 取引サイクル実行

```python
# 取引サイクル実行
result = await orchestrator.run_trading_cycle()

# 結果確認
if result.action != "hold":
    print(f"取引実行: {result.action}")
    print(f"サイズ: {result.size}")
    print(f"信頼度: {result.confidence}")
```

### ML予測のみ実行

```python
from src.core.orchestration import MLServiceAdapter

ml_adapter = MLServiceAdapter(logger=logger)

# 予測実行
predictions = ml_adapter.predict(features_df)
confidence = ml_adapter.calculate_confidence(features_df)
```

---

## 🔧 設計原則

### Application Service Pattern

**原則**: 高レベルフロー制御のみを担当

**❌ 避けるべき（Anti-Pattern）**:
```python
class TradingOrchestrator:
    def calculate_rsi(self, data):
        # ビジネスロジックを直接実装（NG）
        pass
```

**✅ 推奨**:
```python
class TradingOrchestrator:
    def run_trading_cycle(self):
        # FeatureGeneratorに委譲
        features = self.feature_generator.generate_features(data)
```

### 依存性注入

**原則**: Protocol型ヒントによる型安全な注入

```python
class TradingOrchestrator:
    def __init__(
        self,
        data_service: DataServiceProtocol,  # Protocol型ヒント
        strategy_manager: StrategyServiceProtocol,
        execution_service: ExecutionServiceProtocol,
        # ...
    ):
        self.data_service = data_service
        # ...
```

### エラーハンドリング階層化

**原則**: 適切なレベルでの例外処理

```python
try:
    data = await self.data_service.fetch_multi_timeframe(...)
except DataFetchError as e:
    self.logger.error(f"データ取得失敗: {e}")
    return ExecutionResult(action="hold")
```

---

## 🧪 テスト戦略

### モック戦略

Protocol型ヒントにより、各サービス層のモック作成が容易:

```python
class MockDataService:
    async def fetch_multi_timeframe(self, symbol, limit):
        # テストデータ返却
        return test_data

# TradingOrchestratorテスト
orchestrator = TradingOrchestrator(
    data_service=MockDataService(),  # モック注入
    # ...
)
```

### 統合テスト

```bash
# orchestration層統合テスト
pytest tests/unit/core/orchestration/

# カバレッジ確認
pytest tests/unit/core/orchestration/ --cov=src/core/orchestration
```

---

## 🔍 トラブルシューティング

### ML予測エラー

**症状**: ModelPredictionError発生

**原因確認**:
```python
# モデルファイル存在確認
ls models/production/ensemble_full.pkl
ls models/production/ensemble_basic.pkl

# ログ確認
grep "MLモデル読み込み" logs/trading.log
```

**解決策**:
1. モデルファイル再作成: `python scripts/ml/create_ml_models.py`
2. DummyModelフォールバック確認: ログに"DummyModel使用"が表示されるか確認

### 依存性注入エラー

**症状**: AttributeError: 'NoneType' object has no attribute ...

**原因**: サービス層の注入忘れ

**解決策**:
```python
# create_trading_orchestrator()使用（推奨）
orchestrator = await create_trading_orchestrator(mode="paper", ...)

# または手動注入時は全サービス層を確実に注入
```

### バックテストログ過剰

**症状**: バックテスト時にログが大量出力

**原因**: ログレベル設定ミス

**解決策**:
```yaml
# config/core/thresholds.yaml
backtest:
  log_level: WARNING  # INFO → WARNING に変更
  discord_enabled: false
```

---

## 📊 Phase履歴（抜粋）

- **Phase 52.4**: コード品質改善・Phase参照統一・README.md作成
- **Phase 51.5-B**: 動的戦略管理基盤実装
- **Phase 50.9**: 外部API削除・シンプル設計回帰・2段階Graceful Degradation
- **Phase 49**: Application Service Pattern確立・依存性注入基盤・エラーハンドリング階層化
- **Phase 35**: バックテスト最適化実装（ログレベル動的変更・Discord無効化）
- **Phase 28-29**: Application Service Pattern基盤確立・責任分離・Protocol型ヒント

---

## 🔗 関連ファイル

### 依存サービス層

- `src/data/`: DataService実装
- `src/features/`: FeatureGenerator実装
- `src/strategies/`: StrategyManager実装
- `src/ml/`: ProductionEnsemble実装
- `src/trading/`: ExecutionService・IntegratedRiskManager実装

### 実行モード層

- `src/core/execution/`: BacktestRunner・PaperTradingRunner・LiveTradingRunner

### 設定管理

- `src/core/config/`: Config・ConfigManager・get_threshold()

---

**🎯 Phase 52.4完了**: Phase参照統一・README.md作成により、orchestration層の理解促進・保守性向上が実現されています。
