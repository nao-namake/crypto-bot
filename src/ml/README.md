# src/ml/ - 機械学習システム

**Phase 49完了**: 55特徴量を入力とした3モデルアンサンブル（LightGBM・XGBoost・RandomForest）によるStrategy-Aware高精度取引シグナル予測システム。50→55特徴量拡張（5戦略信号追加）・実戦略信号学習・訓練/推論一貫性確保・実データ学習・閾値最適化・TimeSeriesSplit・Early Stopping・SMOTE・Optunaハイパーパラメータ最適化・Meta-Learning動的重み最適化完了。

## 📂 ファイル構成

```
src/ml/
├── __init__.py          # ML層エクスポート（43行・Phase 49完了）
├── models.py            # 個別モデル実装（574行・Phase 49完了）
├── ensemble.py          # アンサンブルシステム（775行・Phase 49完了）
├── model_manager.py     # モデル管理・バージョニング（335行・Phase 49完了）
└── meta_learning.py     # Meta-Learning動的重み最適化（669行・Phase 49完了）
```

## 🔧 主要コンポーネント

### **models.py（574行・Phase 49完了）**

**目的**: 個別機械学習モデル（LightGBM・XGBoost・RandomForest）実装

**主要クラス**:
```python
class BaseMLModel(ABC):                               # 基底クラス
    def fit(self, X, y) -> 'BaseMLModel'              # 学習実行
    def predict(self, X) -> np.ndarray                # 予測実行
    def predict_proba(self, X) -> np.ndarray          # 確率予測
    def get_feature_importance(self) -> Dict          # 特徴量重要度

class LGBMModel(BaseMLModel):                         # LightGBM実装
class XGBModel(BaseMLModel):                          # XGBoost実装
class RFModel(BaseMLModel):                           # RandomForest実装
```

### **ensemble.py（775行・Phase 49完了）**

**目的**: 3モデルアンサンブル予測システム・重み付け投票・本番ProductionEnsemble

**主要クラス**:
```python
class EnsembleModel:
    def __init__(self, confidence_threshold=0.35)     # アンサンブル初期化
    def fit(self, X, y) -> 'EnsembleModel'            # 全モデル学習
    def predict(self, X) -> np.ndarray                # アンサンブル予測
    def predict_proba(self, X) -> np.ndarray          # アンサンブル確率

class ProductionEnsemble:                             # 本番用アンサンブル
    def predict(self, features) -> np.ndarray         # 重み付け投票
    def predict_proba(self, features) -> np.ndarray   # 重み付け確率

class VotingSystem:                                   # 投票システム
class VotingMethod(Enum):                             # 投票手法定義
    MAJORITY = "majority"  # WEIGHTED = "weighted"  # CONSENSUS = "consensus"
```

### **model_manager.py（335行・Phase 49完了）**

**目的**: モデルのバージョニング・保存・読み込み管理

**主要クラス**:
```python
class ModelManager:
    def save_model(self, model, description) -> str   # モデル保存
    def load_model(self, model_id) -> Any             # モデル読み込み
    def list_models(self) -> List[Dict]               # モデル一覧
    def create_backup(self) -> str                    # バックアップ作成
```

### **meta_learning.py（669行・Phase 49完了）**

**目的**: Meta-Learning動的重み最適化・市場状況適応型戦略選択

**主要クラス**:
```python
class MarketRegimeAnalyzer:                      # 市場状況分析
    def analyze(self, df) -> Dict[str, float]   # 10-15市場特徴量抽出
    def _calculate_bb_width(self, df) -> float   # BB幅計算
    def _calculate_volatility_ratio(self, df) -> float  # ボラティリティ比率
    def _calculate_ema_spread(self, df) -> float # EMAスプレッド

class PerformanceTracker:                        # パフォーマンス追跡
    def record_performance(self, strategy, result)  # 戦略実績記録
    def get_recent_performance(self, period) -> Dict  # 最近のパフォーマンス取得
    def get_strategy_statistics(self, strategy) -> Dict  # 戦略統計取得

class MetaLearningWeightOptimizer:               # 動的重み最適化
    def optimize_weights(self, market_data, performance) -> Dict  # 市場状況ベース重み計算
    def _calculate_weights(self, features) -> Dict  # 重み計算エンジン
    def get_current_weights(self) -> Dict        # 現在の重み取得
```

**Phase 45実装**:
- **市場状況適応**: MarketRegimeAnalyzerによる10-15特徴量抽出（volatility_atr_14、trend_ema_spread、range_detection等）
- **動的重み最適化**: 市場状況に応じた戦略・ML重みの自動調整
- **シャープレシオ+30-50%向上目標**: パフォーマンストラッキングによる継続的改善
- **ハードコード完全排除**: 全設定値をthresholds.yamlから取得（`get_threshold()`パターン完全適用）
- **フォールバック機能**: Meta-ML失敗時は固定重み使用（Graceful Degradation）
- **段階的有効化**: デフォルト無効（`enabled: false`）・本番検証後に有効化可能
- **JSON永続化**: 履歴データ保存・再起動時復元機能

**使用例**:
```python
from src.ml.meta_learning import MetaLearningWeightOptimizer

# Meta-Learning初期化（thresholds.yamlから設定取得）
optimizer = MetaLearningWeightOptimizer()

# 市場データ・パフォーマンスデータから最適重みを計算
optimal_weights = optimizer.optimize_weights(market_data, performance_history)
# 結果例: {"ATRBased": 0.3, "MochipoyAlert": 0.25, "MultiTimeframe": 0.2, ...}
```

**注意**: 内部実装のため`__init__.py`に含まれていません。`trading_cycle_manager.py`から条件付きimportで使用されます。

## 🚀 使用例

```python
# 基本的なアンサンブル学習
from src.ml import EnsembleModel

# 55特徴量データ準備（Phase 41.8拡張完了・必須順序）
ensemble = EnsembleModel(confidence_threshold=0.35)
ensemble.fit(X_train, y_train)

# アンサンブル予測
predictions = ensemble.predict(X_test)
probabilities = ensemble.predict_proba(X_test)

# 本番用ProductionEnsemble使用
import pickle
with open('models/production/production_ensemble.pkl', 'rb') as f:
    production_model = pickle.load(f)

predictions = production_model.predict(sample_features)  # 55特徴量必須（Phase 41.8拡張完了）
```

## 📊 アンサンブル構成

### **3モデル統合システム**（Phase 49完了）

**Phase 49完了: Strategy-Aware ML実装**:
- **50→55特徴量拡張**: 5戦略信号特徴量追加（ATRBased・MochipoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength）
- **実戦略信号学習**: 訓練時に実際の戦略を実行して実戦略信号を生成・0-fill問題解決
- **訓練/推論一貫性**: 訓練データと推論データの特徴量構造を完全統一
- **Look-ahead bias防止**: `df.iloc[: i + 1]`による過去データのみ使用・未来データリーク防止
- **信号エンコーディング**: `action × confidence`方式・buy=+1.0、hold=0.0、sell=-1.0
- **F1スコア**: 0.56-0.61（XGBoost 0.593, RandomForest 0.614, LightGBM 0.489）

**Phase 40.6完了: 50特徴量拡張システム実装**:
- **Phase 40.6**: 15→50特徴量拡張・ML予測精度+8-15%・ロバスト性+10-20%向上
  - ラグ特徴量（10個）：過去の価格・出来高情報
  - 移動統計量（12個）：短期/長期トレンド・ボラティリティ
  - 交互作用特徴量（6個）：指標間の相関関係
  - 時間ベース特徴量（7個）：時刻・曜日周期性

**Phase 39学習システム実装**:
- **Phase 39.1**: 実データ学習（CSV読み込み・過去180日分15分足データ・17,271件）
- **Phase 39.2**: 閾値最適化（0.3% → 0.5%）・3クラス分類（BUY/HOLD/SELL）
- **Phase 39.3**: TimeSeriesSplit n_splits=5・Early Stopping rounds=20・Train/Val/Test 70/15/15
- **Phase 39.4**: SMOTE oversampling・class_weight='balanced'・クラス不均衡対応
- **Phase 39.5**: Optunaハイパーパラメータ最適化（TPESampler・3モデル自動最適化）

**重み付け設定**（ProductionEnsemble）:
```python
weights = {
    'lightgbm': 0.4,        # 40% - 高いCV F1スコア
    'xgboost': 0.4,         # 40% - 高い精度・補完性能
    'random_forest': 0.2    # 20% - 安定性重視・過学習抑制
}
```

### **55特徴量対応**（Phase 49完了）

**必須特徴量**（順序固定・55個）:
```python
expected_features = [
    # 基本特徴量（15個・従来システム）
    'close', 'volume',                                          # 基本データ（2個）
    'rsi_14', 'macd',                                          # モメンタム（2個）
    'atr_14', 'bb_position',                                   # ボラティリティ（2個）
    'ema_20', 'ema_50',                                        # トレンド（2個）
    'volume_ratio',                                            # 出来高（1個）
    'donchian_high_20', 'donchian_low_20', 'channel_position', # ブレイクアウト（3個）
    'adx_14', 'plus_di_14', 'minus_di_14',                     # 市場レジーム（3個）

    # Phase 40.6拡張特徴量（35個）
    'close_lag_1', 'close_lag_2', 'close_lag_3', 'close_lag_4', 'close_lag_5',  # ラグ特徴量（10個）
    'volume_lag_1', 'volume_lag_2', 'volume_lag_3', 'volume_lag_4', 'volume_lag_5',
    'close_rolling_mean_5', 'close_rolling_std_5', 'close_rolling_max_5', 'close_rolling_min_5',  # 移動統計量（12個）
    'close_rolling_mean_20', 'close_rolling_std_20', 'close_rolling_max_20', 'close_rolling_min_20',
    'volume_rolling_mean_5', 'volume_rolling_std_5', 'volume_rolling_mean_20', 'volume_rolling_std_20',
    'rsi_atr', 'macd_volume', 'ema_spread', 'bb_width', 'volatility_trend', 'momentum_volume',  # 交互作用（6個）
    'hour', 'day_of_week', 'day_of_month', 'is_weekend', 'hour_sin', 'hour_cos', 'day_sin',  # 時間（7個）

    # Phase 41.8戦略信号特徴量（5個）
    'strategy_signal_ATRBased',           # ATRBased戦略信号（action × confidence）
    'strategy_signal_MochipoyAlert',      # MochipoyAlert戦略信号
    'strategy_signal_MultiTimeframe',     # MultiTimeframe戦略信号
    'strategy_signal_DonchianChannel',    # DonchianChannel戦略信号
    'strategy_signal_ADXTrendStrength'    # ADXTrendStrength戦略信号
]
```

## 🔧 設定

**環境変数**: 不要（設定ファイルから自動取得）
**データ要件**: 55特徴量固定（Phase 49完了）・順序厳守・最小学習サンプル100以上
**本番モデル**: models/production/production_ensemble.pkl（50MB以下）

## ⚠️ 重要事項

### **特性・制約**
- **55特徴量統一**: 15→50→55特徴量拡張完了（Phase 49: 5戦略信号追加）・特徴量数・順序変更は互換性破綻の原因
- **Strategy-Aware ML**: 訓練時/推論時一貫性確保・実戦略信号学習・Look-ahead bias防止
- **3モデルアンサンブル**: LightGBM・XGBoost・RandomForest重み付け統合
- **Meta-Learning**: 市場状況適応型重み最適化（Phase 45実装・デフォルト無効）
- **本番運用**: ProductionEnsemble・予測レイテンシー100ms以下
- **メモリ効率**: 学習時500MB以下・予測時100MB以下
- **Phase 49完了**: 55特徴量Strategy-Aware ML・訓練/推論一貫性確保・実戦略信号学習・Meta-Learning動的最適化
- **品質保証**: 1,065テスト100%成功・66.72%カバレッジ達成
- **依存**: scikit-learn・lightgbm・xgboost・imbalanced-learn・optuna・joblib・src.core.*・src.strategies.*

---

**機械学習システム（Phase 49完了）**: 55特徴量Strategy-Aware 3モデルアンサンブル（15→50→55拡張）による高精度取引シグナル予測・実戦略信号学習・訓練/推論一貫性確保・Look-ahead bias防止・実データ学習・閾値最適化・TimeSeriesSplit・Early Stopping・SMOTE・Optunaハイパーパラメータ最適化・Meta-Learning動的重み最適化（Phase 45実装）・重み付け投票・本番ProductionEnsemble統合システム。