# Ensemble - アンサンブル統合システム

**Phase 11完了・CI/CD統合・24時間監視・段階的デプロイ対応**: ソフト投票と重み付け投票によるモデル統合システム完成・GitHub Actions統合

## 📂 ディレクトリ構造

```
ensemble/
├── __init__.py          # アンサンブルエクスポート統合
├── ensemble_model.py    # メインアンサンブルクラス
└── voting.py           # 投票システム実装
```

## 🎯 役割と責任

### ensemble_model.py - アンサンブル統合クラス（Phase 11・CI/CD統合）
**役割**: 複数MLモデルの統合管理と予測統合・GitHub Actions対応

**主要機能**:
- 3モデル（LightGBM, XGBoost, RandomForest）の統合・24時間監視対応
- ソフト投票による確率ベース統合・段階的デプロイ対応
- 信頼度閾値による低信頼度予測の除外・CI/CD品質ゲート対応
- 重み付け投票による性能最適化・監視統合
- モデルパフォーマンスの個別追跡・GitHub Actions統合

**コア実装**:
```python
class EnsembleModel:
    def __init__(self, models=None, weights=None, confidence_threshold=0.35):
        """
        Args:
            models: カスタムモデル辞書（デフォルト: 3モデル自動作成）
            weights: モデル重み（デフォルト: 均等重み）
            confidence_threshold: 信頼度閾値（デフォルト: 0.35）
        """
```

**重要メソッド**:
- `fit()`: 全モデルの並列学習
- `predict()`: アンサンブル予測（信頼度閾値適用）
- `predict_proba()`: 確率予測
- `evaluate()`: 包括的評価メトリクス
- `get_feature_importance()`: 統合特徴量重要度

### voting.py - 投票システム（Phase 11・CI/CD統合）
**役割**: 複数モデルの予測を統合する投票メカニズム・GitHub Actions対応

**投票方式**:
```python
class VotingMethod(Enum):
    SOFT = "soft"          # 確率ベース（デフォルト）
    HARD = "hard"          # クラスベース多数決
    WEIGHTED = "weighted"  # 重み付け投票
```

**主要機能**:
- **ソフト投票**: 各モデルの確率を平均化・24時間監視対応
- **ハード投票**: 多数決による決定・段階的デプロイ対応
- **重み付け**: モデル性能に応じた重み適用・CI/CD品質ゲート対応
- **投票統計**: 全会一致率・ペア一致率等の分析・監視統合
- **不一致分析**: モデル間の予測相違パターン分析・GitHub Actions統合

**統計分析機能**:
```python
def get_voting_statistics(predictions):
    """
    Returns:
        - unanimity_rate: 全モデル一致率
        - avg_majority_confidence: 平均多数派信頼度
        - pairwise_agreement: ペア別一致率
    """

def analyze_disagreement(predictions, confidence_threshold):
    """
    Returns:
        - disagreement_indices: 不一致サンプルインデックス
        - low_confidence_indices: 低信頼度サンプル
    """
```

## 📜 実装ルール（Phase 11・CI/CD統合・24時間監視・段階的デプロイ対応）

### 1. アンサンブル構成ルール（GitHub Actions対応）

**デフォルト3モデル構成**:
```python
# 自動的に3モデル作成
ensemble = EnsembleModel()  # LightGBM, XGBoost, RandomForest

# カスタムモデル指定
custom_models = {
    'lgbm': LGBMModel(n_estimators=200),
    'xgb': XGBModel(max_depth=3),
    'rf': RFModel(n_estimators=50)
}
ensemble = EnsembleModel(models=custom_models)
```

### 2. 重み管理ルール（24時間監視対応）

**重み正規化**:
```python
# 入力重みは自動的に正規化（合計1.0）
weights = {'lgbm': 2, 'xgb': 3, 'rf': 1}
# 内部で {'lgbm': 0.33, 'xgb': 0.5, 'rf': 0.17} に変換
```

**動的重み更新**:
```python
# パフォーマンスに基づく重み調整
voting_system.update_weights(new_weights)
```

### 3. 信頼度管理ルール（段階的デプロイ対応）

**信頼度閾値の適用**:
```python
# 予測確率の最大値が閾値未満の場合
if max(probabilities) < confidence_threshold:
    return -1  # 取引しない（低信頼度）
else:
    return predicted_class  # 0 or 1
```

**閾値調整ガイドライン**:
- **0.2-0.3**: 積極的（高カバレッジ・低精度）
- **0.35**: デフォルト（バランス型）
- **0.4-0.5**: 保守的（低カバレッジ・高精度）
- **0.6+**: 超保守的（非常に高い確信度のみ）

### 4. エラーハンドリング（CI/CD品質ゲート対応）

**必須チェック**:
```python
# 学習前チェック
if len(X) < 50:
    raise ValueError("Insufficient training data")

# 予測前チェック  
if not self.is_fitted:
    raise ValueError("Model not fitted")

# 投票時の形状チェック
if not all(pred.shape == predictions[0].shape for pred in predictions):
    raise ValueError("All predictions must have same shape")
```

## 🔧 使用パターン（Phase 11・CI/CD統合・24時間監視・段階的デプロイ対応）

### 1. 基本的なアンサンブル（GitHub Actions対応）
```python
# シンプルな均等重みアンサンブル
ensemble = EnsembleModel()
ensemble.fit(X_train, y_train)
predictions = ensemble.predict(X_test)
```

### 2. カスタム重み付けアンサンブル（24時間監視対応）
```python
# 性能ベースの重み設定
weights = {'lgbm': 0.5, 'xgb': 0.3, 'rf': 0.2}
ensemble = EnsembleModel(weights=weights, confidence_threshold=0.4)
```

### 3. 投票システムの直接使用（段階的デプロイ対応）
```python
voting = VotingSystem(method=VotingMethod.SOFT)
final_pred, confidence = voting.vote(
    individual_predictions,
    individual_probabilities
)
```

### 4. 詳細分析モード（CI/CD品質ゲート対応）
```python
# 個別モデルパフォーマンス追跡
ensemble.fit(X_train, y_train)
for model_name, performance in ensemble.model_performance.items():
    print(f"{model_name}: {performance['train_score']:.3f}")

# 投票統計取得
stats = voting_system.get_voting_statistics(predictions)
print(f"全会一致率: {stats['unanimity_rate']:.2%}")
```

## 📊 パフォーマンス最適化（Phase 11・CI/CD統合・24時間監視・段階的デプロイ対応）

### 1. 重み最適化戦略（GitHub Actions対応）

**バックテストベース**:
```python
# 各モデルの個別性能を測定
performances = {}
for name, model in models.items():
    score = model.evaluate(X_val, y_val)['f1_score']
    performances[name] = score

# 性能比例の重み設定
total_score = sum(performances.values())
weights = {name: score/total_score for name, score in performances.items()}
```

### 2. 信頼度閾値最適化（24時間監視対応）

```python
# 閾値スキャン
thresholds = np.arange(0.2, 0.7, 0.05)
results = []

for threshold in thresholds:
    ensemble.confidence_threshold = threshold
    metrics = ensemble.evaluate(X_val, y_val)
    results.append({
        'threshold': threshold,
        'coverage': metrics['confidence_coverage'],
        'accuracy': metrics['confidence_accuracy']
    })

# 最適閾値選択（F1スコア最大化等）
```

### 3. メモリ効率化（段階的デプロイ対応）

```python
# 不要なモデルの削除
del ensemble.models['underperforming_model']

# ガベージコレクション
import gc
gc.collect()
```

## ⚠️ 注意事項（Phase 11・CI/CD統合・監視統合）

### 1. 計算コスト（GitHub Actions対応）
- 3モデル学習により学習時間は3倍
- 予測時も3モデル実行のオーバーヘッド
- メモリ使用量も3倍

### 2. 過学習リスク（24時間監視対応）
- 個別モデルが全て過学習すると改善なし
- 交差検証による適切な評価が必要

### 3. モデル相関（段階的デプロイ対応）
- 似たモデルばかりでは多様性なし
- 異なる特性のモデル組み合わせが重要

## 🎯 ベストプラクティス（Phase 11・CI/CD統合・24時間監視・段階的デプロイ対応）

### 1. モデル選択（GitHub Actions対応）
```python
# 多様性を確保する組み合わせ
models = {
    'lgbm': LGBMModel(),      # ブースティング系
    'rf': RFModel(),          # バギング系
    'xgb': XGBModel()         # 異なるブースティング実装
}
```

### 2. 評価戦略（24時間監視対応）
```python
# 時系列分割での評価
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)

for train_idx, val_idx in tscv.split(X):
    ensemble.fit(X[train_idx], y[train_idx])
    score = ensemble.evaluate(X[val_idx], y[val_idx])
```

### 3. 本番運用（段階的デプロイ対応）
```python
# 本番設定例
production_ensemble = EnsembleModel(
    weights={'lgbm': 0.5, 'xgb': 0.3, 'rf': 0.2},
    confidence_threshold=0.4  # 保守的設定
)

# 定期的な再学習
if performance_degradation_detected():
    production_ensemble.fit(recent_data)
```

## 🔮 拡張計画（Phase 11基盤活用・CI/CD統合）

### Phase 12での改善予定（GitHub Actions基盤）
1. **スタッキング実装**: メタ学習器による高度な統合・CI/CD品質ゲート対応
2. **動的重み調整**: オンラインでの重み最適化・24時間監視統合
3. **モデル自動選択**: 性能基準での動的モデル追加/削除・段階的デプロイ対応
4. **並列化強化**: 分散学習・予測の実装・監視統合

---

**作成日**: 2025年Phase 5実装
**最終更新**: Phase 11完了（2025年8月18日）・CI/CD統合・24時間監視・段階的デプロイ対応・GitHub Actions統合