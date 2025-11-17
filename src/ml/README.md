# 🧠 機械学習システム

**最終更新**: 2025/11/16 (Phase 52.4-B)

## 🎯 概要

55特徴量を入力とした3モデルアンサンブル（LightGBM・XGBoost・RandomForest）によるStrategy-Aware高精度取引シグナル予測システム。

### 現状（Phase 52.4-B）

- ✅ **55特徴量固定**: 49基本特徴量+6戦略シグナル特徴量
- ✅ **3モデルアンサンブル**: LightGBM 40%・XGBoost 40%・RandomForest 20%
- ✅ **Strategy-Aware**: 実戦略信号学習・訓練/推論一貫性確保
- ✅ **本番稼働**: ensemble_full.pkl（週次自動更新）

### 開発履歴

**Phase 52.4-B（2025/11/16）**: コード整理・ドキュメント統一完了
**Phase 51.9-6D（2025/11/11）**: 3クラス分類対応（0=sell, 1=hold, 2=buy）
**Phase 50.9（2025/11/01）**: 外部API完全削除・シンプル設計回帰
**Phase 50.2（2025/10/28）**: 時間的特徴量追加（7特徴量）
**Phase 50.1（2025/10/27）**: Graceful Degradation実装
**Phase 49（2025/10/26）**: ML統合完成・バックテスト信頼性100%達成
**Phase 41.8（2025/10/17）**: Strategy-Aware ML実装・55特徴量システム確立
**Phase 40.6（2025/10/15）**: Feature Engineering拡張（15→50特徴量）

---

## 📂 ファイル構成

```
src/ml/
├── __init__.py          # ML層エクスポート（45行）
├── models.py            # 個別モデル実装（586行）
├── ensemble.py          # アンサンブルシステム（781行）
├── model_manager.py     # モデル管理・バージョニング（337行）
└── meta_learning.py     # Meta-Learning動的重み最適化（671行）

models/production/
├── ensemble_full.pkl    # 本番モデル（55特徴量・デフォルト）
└── ensemble_basic.pkl   # フォールバックモデル（49特徴量）
```

---

## 🔧 主要コンポーネント

### **models.py（586行）**

個別機械学習モデル（LightGBM・XGBoost・RandomForest）実装

#### 主要クラス

```python
class BaseMLModel(ABC):
    """機械学習モデル基底クラス"""

    def fit(self, X, y) -> 'BaseMLModel'              # 学習実行
    def predict(self, X) -> np.ndarray                # 予測実行（3クラス対応）
    def predict_proba(self, X) -> np.ndarray          # 確率予測
    def get_feature_importance(self) -> Dict          # 特徴量重要度

class LGBMModel(BaseMLModel):                         # LightGBM実装
class XGBModel(BaseMLModel):                          # XGBoost実装
class RFModel(BaseMLModel):                           # RandomForest実装
```

---

### **ensemble.py（781行）**

アンサンブルシステム・投票メカニズム・本番用モデル

#### 主要クラス

```python
class VotingSystem:
    """投票システム（ソフト・ハード・重み付け投票）"""

class EnsembleModel:
    """アンサンブル分類モデル（重み付け投票・confidence閾値）"""

    def fit(self, X, y) -> 'EnsembleModel'            # アンサンブル学習
    def predict(self, X) -> np.ndarray                # アンサンブル予測
    def predict_proba(self, X) -> np.ndarray          # 確率予測（重み付け平均）
    def evaluate(self, X, y) -> Dict                  # モデル評価

class ProductionEnsemble:
    """本番用アンサンブルモデル（週次自動学習で使用）"""
```

---

### **model_manager.py（337行）**

モデル管理・バージョニング・保存/読み込み

#### 主要メソッド

```python
class ModelManager:
    """モデルライフサイクル管理システム"""

    def save_model(model, version_name) -> str        # モデル保存
    def load_model(version_name) -> EnsembleModel     # モデル読み込み
    def get_latest_model() -> Tuple[str, EnsembleModel]  # 最新モデル取得
    async def predict(X) -> Dict                      # 予測実行
```

---

### **meta_learning.py（671行）**

Meta-Learning動的重み最適化（デフォルト無効・将来機能）

#### 主要クラス

```python
class MarketRegimeAnalyzer:
    """市場状況分析（既存特徴量活用）"""

class PerformanceTracker:
    """戦略・MLパフォーマンス履歴トラッキング"""

class MetaLearningWeightOptimizer:
    """Meta-ML動的重み最適化（シャープレシオ+30-50%向上目標）"""
```

---

## 🚀 使用例

### 基本的な使い方

```python
from src.ml import EnsembleModel, ModelManager

# 1. アンサンブルモデルの作成・学習
ensemble = EnsembleModel()
ensemble.fit(X_train, y_train)

# 2. モデル評価
metrics = ensemble.evaluate(X_test, y_test)
print(f"Accuracy: {metrics['accuracy']:.3f}")

# 3. モデル保存
manager = ModelManager()
version = manager.save_model(
    ensemble,
    version_name="ensemble_v20251116",
    description="Phase 52.4-B対応モデル",
    performance_metrics=metrics
)

# 4. 本番予測
predictions = await manager.predict(X_new)  # 55特徴量必須
print(f"Action: {predictions['action']}, Confidence: {predictions['confidence']:.3f}")
```

### 本番環境での使用

```python
from src.ml import ModelManager

# ModelManagerが自動的に最新モデルを読み込み
manager = ModelManager(base_path="models/production")

# 予測実行（フォールバック機能付き）
result = await manager.predict(features_df)  # 55特徴量DataFrame

# result = {
#     "prediction": 2,      # 0=sell, 1=hold, 2=buy
#     "confidence": 0.72,
#     "action": "buy"
# }
```

---

## 📊 55特徴量システム構成

### **49基本特徴量**

1. **基本データ（2個）**: close, volume
2. **テクニカル指標（17個）**: RSI, MACD, ATR, BB, EMA, Donchian, ADX, Stochastic, Volume
3. **異常検知（1個）**: volume_ratio
4. **ラグ特徴量（9個）**: close_lag_1/2/3/10, volume_lag_1/2/3, rsi_lag_1, macd_lag_1
5. **移動統計量（5個）**: close_ma_10/20, close_std_5/10/20
6. **交互作用特徴量（5個）**: rsi_x_atr, macd_x_volume, bb_position_x_volume_ratio, close_x_atr, volume_x_bb_position
7. **時間的特徴量（7個）**: hour, day_of_week, is_market_open_hour, is_europe_session, hour_cos, day_sin, day_cos
8. **その他（3個）**: atr_ratio, bb_position, channel_position

### **6戦略シグナル特徴量**

```python
# 戦略シグナル特徴量（strategies.yamlから動的取得）
feature_names = [
    'strategy_signal_ATRBased',              # ATRベース逆張り戦略
    'strategy_signal_DonchianChannel',        # Donchianチャネルブレイクアウト
    'strategy_signal_ADXTrendStrength',       # ADXトレンド強度戦略
    'strategy_signal_BBReversal',             # BB Reversal戦略
    'strategy_signal_StochasticReversal',     # Stochastic Reversal戦略
    'strategy_signal_MACDEMACrossover'        # MACD+EMA Crossover戦略
]

# エンコーディング方式: action_times_confidence
# buy=+confidence, hold=0, sell=-confidence
```

---

## ⚙️ 設定

### データ要件

- **特徴量数**: 55特徴量固定（49基本+6戦略シグナル）
- **順序**: feature_order.json厳守
- **最小サンプル数**: 学習時100以上・予測時1以上
- **形式**: pandas.DataFrame

### 依存関係

- **設定ファイル**:
  - `config/core/feature_order.json`: 特徴量順序定義
  - `config/core/strategies.yaml`: 戦略定義
  - `config/core/thresholds.yaml`: ML統合閾値
- **ライブラリ**: scikit-learn, lightgbm, xgboost, pandas, numpy
- **内部依存**: src.core.config, src.features, src.strategies

---

## ⚠️ 重要事項

### 設計原則

- **55特徴量固定**: feature_order.json単一真実源・全システム整合性
- **Strategy-Aware**: 実戦略信号学習・訓練/推論一貫性確保
- **Graceful Degradation**: ensemble_full.pkl → ensemble_basic.pkl → DummyModel
- **設定駆動型**: すべての設定値はget_threshold()で取得
- **品質保証**: TimeSeriesSplit・Early Stopping・SMOTE・Optuna最適化

### バージョニング

```python
# モデル命名規則
ensemble_v{YYYYMMDD_HHMMSS}  # タイムスタンプベース
# 例: ensemble_v20251116_153000

# 本番モデル
ensemble_full.pkl     # 55特徴量（デフォルト）
ensemble_basic.pkl    # 49特徴量（フォールバック）
```

### 週次自動更新

```bash
# GitHub Actions: 毎週月曜9:00 JST
python scripts/ml/create_ml_models.py --n-classes 3 --threshold 0.005 --optimize

# 出力:
# models/production/ensemble_full.pkl
# models/production/ensemble_basic.pkl
```

---

## 📈 パフォーマンス

### 期待効果

- **Accuracy**: 0.55-0.60（3クラス分類）
- **F1 Score**: 0.56-0.61
- **予測速度**: <100ms/サンプル
- **信頼度閾値**: 0.45（ML統合最小閾値）

### 最適化実績

- **Phase 41.8.5**: ML統合率10% → 100%達成
- **Phase 40.6**: ML予測精度+8-15%・ロバスト性+10-20%向上
- **Phase 39.5**: Optunaハイパーパラメータ最適化完了

---

**Phase 52.4-B完了**: コード整理・ドキュメント統一・55特徴量固定システム（49基本+6戦略シグナル）・3モデルアンサンブル・週次自動更新
