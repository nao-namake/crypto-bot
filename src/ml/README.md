# src/ml/ - 機械学習システム

## 🎯 役割・責任

AI自動取引システムの機械学習層。15特徴量を入力として、3つの機械学習モデル（LightGBM、XGBoost、RandomForest）によるアンサンブル予測を提供。買い/売り/ホールドの取引シグナルを高精度で生成。

## 📂 ファイル構成

```
src/ml/
├── __init__.py          # ML層エクスポート（43行）
├── models.py            # 個別モデル実装（540行）
├── ensemble.py          # アンサンブルシステム（687行）
└── model_manager.py     # モデル管理・バージョニング（297行）
```

## 🔧 主要コンポーネント

### **models.py（540行）**

**目的**: 個別機械学習モデルの実装・統合基底クラス

**主要クラス**:
```python
class BaseMLModel(ABC):
    def __init__(self, model_name: str, **kwargs)     # 基底初期化
    def fit(self, X, y) -> 'BaseMLModel'              # 学習実行
    def predict(self, X) -> np.ndarray                # 予測実行
    def predict_proba(self, X) -> np.ndarray          # 確率予測
    def get_feature_importance(self) -> Dict          # 特徴量重要度
    
class LGBMModel(BaseMLModel):                         # LightGBM実装
class XGBModel(BaseMLModel):                          # XGBoost実装
class RFModel(BaseMLModel):                           # RandomForest実装
```

**使用例**:
```python
from src.ml.models import LGBMModel, XGBModel, RFModel

# 個別モデル作成・学習
lgbm_model = LGBMModel(n_estimators=200, max_depth=8)
lgbm_model.fit(X_train, y_train)

# 予測実行
predictions = lgbm_model.predict(X_test)
probabilities = lgbm_model.predict_proba(X_test)

# 特徴量重要度
importance = lgbm_model.get_feature_importance()
```

### **ensemble.py（687行）**

**目的**: 複数モデルによるアンサンブル予測システム

**主要クラス**:
```python
class EnsembleModel:
    def __init__(self, confidence_threshold=0.35)     # アンサンブル初期化
    def fit(self, X, y) -> 'EnsembleModel'            # 全モデル学習
    def predict(self, X) -> np.ndarray                # アンサンブル予測
    def predict_proba(self, X) -> np.ndarray          # アンサンブル確率
    def get_individual_predictions(self) -> Dict      # 個別予測取得
    
class ProductionEnsemble:                             # 本番用アンサンブル
    def predict(self, features) -> np.ndarray         # 重み付け投票
    def predict_proba(self, features) -> np.ndarray   # 重み付け確率
    def get_model_info(self) -> Dict                  # モデル情報

class VotingSystem:                                   # 投票システム
class VotingMethod(Enum):                             # 投票手法定義
    MAJORITY = "majority"                             # 多数決
    WEIGHTED = "weighted"                             # 重み付け
    CONSENSUS = "consensus"                           # 合意制
```

**使用例**:
```python
from src.ml.ensemble import EnsembleModel

# アンサンブルモデル作成・学習
ensemble = EnsembleModel(confidence_threshold=0.35)
ensemble.fit(X_train, y_train)

# アンサンブル予測
predictions = ensemble.predict(X_test)
probabilities = ensemble.predict_proba(X_test)

# 個別モデル予測確認
individual = ensemble.get_individual_predictions(X_test)
print("LightGBM:", individual['lightgbm'])
print("XGBoost:", individual['xgboost'])
print("RandomForest:", individual['random_forest'])
```

### **model_manager.py（297行）**

**目的**: モデルのバージョニング・保存・読み込み管理

**主要クラス**:
```python
class ModelManager:
    def __init__(self, base_dir="models")             # 管理初期化
    def save_model(self, model, description) -> str   # モデル保存
    def load_model(self, model_id) -> Any             # モデル読み込み
    def list_models(self) -> List[Dict]               # モデル一覧
    def get_model_info(self, model_id) -> Dict        # モデル情報
    def delete_model(self, model_id) -> bool          # モデル削除
    def create_backup(self) -> str                    # バックアップ作成
```

**使用例**:
```python
from src.ml.model_manager import ModelManager

manager = ModelManager()

# モデル保存
model_id = manager.save_model(
    ensemble, 
    description="15特徴量アンサンブルモデル v1.0"
)

# モデル読み込み
loaded_model = manager.load_model(model_id)

# モデル一覧表示
models = manager.list_models()
for model in models:
    print(f"ID: {model['id']}, 作成日: {model['created_at']}")
```

## 🚀 使用方法

### **基本的なアンサンブル学習**
```python
from src.ml import EnsembleModel
import pandas as pd

# 15特徴量データ準備
X_train = pd.DataFrame({
    'close': [...], 'volume': [...], 'returns_1': [...],
    'rsi_14': [...], 'macd': [...], 'macd_signal': [...],
    'atr_14': [...], 'bb_position': [...], 
    'ema_20': [...], 'ema_50': [...],
    'zscore': [...], 'volume_ratio': [...]
})
y_train = pd.Series([0, 1, 0, 1, ...])  # バイナリラベル

# アンサンブル学習
ensemble = EnsembleModel(confidence_threshold=0.35)
ensemble.fit(X_train, y_train)

# 予測実行
predictions = ensemble.predict(X_test)
probabilities = ensemble.predict_proba(X_test)
```

### **本番用ProductionEnsemble**
```python
# models/production/から本番モデル読み込み
import pickle
with open('models/production/production_ensemble.pkl', 'rb') as f:
    production_model = pickle.load(f)

# 本番予測実行
sample_features = np.random.random((5, 15))  # 15特徴量必須
predictions = production_model.predict(sample_features)
probabilities = production_model.predict_proba(sample_features)

# モデル情報確認
info = production_model.get_model_info()
print(f"モデル重み: {info['weights']}")
print(f"特徴量数: {info['n_features']}")
```

### **モデル管理ワークフロー**
```python
from src.ml import EnsembleModel, ModelManager

# 1. モデル学習
ensemble = EnsembleModel()
ensemble.fit(X_train, y_train)

# 2. モデル保存
manager = ModelManager()
model_id = manager.save_model(ensemble, "週次学習モデル v2.1")

# 3. 性能評価
loaded_model = manager.load_model(model_id)
accuracy = loaded_model.score(X_test, y_test)
print(f"テスト精度: {accuracy:.3f}")

# 4. バックアップ作成
backup_path = manager.create_backup()
print(f"バックアップ保存: {backup_path}")
```

## 📊 アンサンブル構成

### **3モデル統合システム**

**重み付け設定**（ProductionEnsemble）:
```python
weights = {
    'lightgbm': 0.4,     # 40% - 高いCV F1スコア
    'xgboost': 0.4,      # 40% - 高い精度・補完性能
    'random_forest': 0.2  # 20% - 安定性重視・過学習抑制
}
```

**投票方式**:
- **重み付け投票**: 性能ベースの重み付け平均
- **多数決投票**: 3モデルの多数決
- **合意制投票**: 全モデル一致時のみ取引

### **15特徴量対応**

**必須特徴量**（順序固定）:
```python
expected_features = [
    'close', 'volume',                        # 基本データ（2個）
    'rsi_14', 'macd',                         # モメンタム（2個）
    'atr_14', 'bb_position',                  # ボラティリティ（2個）
    'ema_20', 'ema_50',                       # トレンド（2個）
    'volume_ratio',                           # 出来高（1個）
    'donchian_high_20', 'donchian_low_20', 'channel_position',  # ブレイクアウト（3個）
    'adx_14', 'plus_di_14', 'minus_di_14'     # 市場レジーム（3個）
]
```

## 🔧 設定・カスタマイズ

### **個別モデルパラメータ**
```python
# カスタムパラメータでモデル作成
lgbm_model = LGBMModel(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=10,
    num_leaves=31
)

xgb_model = XGBModel(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=10,
    eval_metric="logloss"
)
```

### **アンサンブル設定**
```python
# 信頼度閾値調整
ensemble = EnsembleModel(
    confidence_threshold=0.4,  # より慎重な予測
    voting_method=VotingMethod.WEIGHTED
)
```

## ⚠️ 重要事項

### **データ要件**
- **特徴量数**: 15個固定（変更不可）
- **特徴量順序**: expected_features順序厳守
- **データ型**: pandas DataFrame または numpy array
- **最小学習サンプル**: 100以上推奨

### **パフォーマンス特性**
- **予測レイテンシー**: 100ms以下（ProductionEnsemble）
- **メモリ使用量**: 学習時500MB以下、予測時100MB以下
- **モデルサイズ**: production_ensemble.pkl 50MB以下

### **制限事項**
- 特徴量数・順序の変更は互換性破綻の原因
- 学習データの品質がアンサンブル性能に直結
- GPUサポートは現在未対応（CPU最適化済み）

### **依存関係**
- **外部ライブラリ**: scikit-learn、lightgbm、xgboost、joblib
- **内部依存**: src.core.logger、src.core.exceptions
- **特徴量**: src.features（15特徴量生成）

---

**機械学習システム**: 15特徴量を入力とした3モデルアンサンブルにより、高精度な取引シグナル予測を提供する統合機械学習システム。