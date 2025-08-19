# Models - 個別機械学習モデル

**Phase 5完了**: 3つの基本MLモデルの統一インターフェース実装完成

## 📂 ディレクトリ構造

```
models/
├── __init__.py          # モデルエクスポート統合
├── base_model.py        # 抽象基底クラス（全モデルの共通インターフェース）
├── lgbm_model.py        # LightGBMモデル実装
├── xgb_model.py         # XGBoostモデル実装
└── rf_model.py          # RandomForestモデル実装
```

## 🎯 役割と責任

### base_model.py - 抽象基底クラス
**役割**: 全MLモデルの統一インターフェース定義

**責任**:
- 共通メソッドのインターフェース定義（fit, predict, predict_proba等）
- 基本的なバリデーション処理
- モデル状態管理（is_fitted, feature_names等）
- 永続化インターフェース（save, load）

**必須実装メソッド**:
```python
@abstractmethod
def _create_model(self) -> Any
    """具体的なモデルインスタンス作成"""

@abstractmethod  
def _get_model_params(self) -> Dict[str, Any]
    """モデル固有のパラメータ取得"""
```

### lgbm_model.py - LightGBMモデル
**役割**: 高速・メモリ効率的な勾配ブースティングモデル

**特徴**:
- **用途**: メインモデル・本番環境での高速予測
- **強み**: 学習速度・メモリ効率・カテゴリ特徴量対応
- **弱み**: 過学習しやすい・小規模データでは不安定

**デフォルトパラメータ**:
```python
{
    'n_estimators': 100,
    'max_depth': 5,
    'learning_rate': 0.1,
    'objective': 'binary',
    'random_state': 42
}
```

### xgb_model.py - XGBoostモデル
**役割**: 汎用性の高い勾配ブースティングモデル

**特徴**:
- **用途**: バランス型・アンサンブルの中核
- **強み**: 安定性・豊富な調整パラメータ・並列処理
- **弱み**: LightGBMより遅い・メモリ使用量が多い

**デフォルトパラメータ**:
```python
{
    'n_estimators': 100,
    'max_depth': 5,
    'learning_rate': 0.1,
    'objective': 'binary:logistic',
    'random_state': 42
}
```

### rf_model.py - RandomForestモデル
**役割**: 解釈性と安定性重視のアンサンブルモデル

**特徴**:
- **用途**: 過学習抑制・特徴量重要度分析
- **強み**: 過学習に強い・並列処理可能・解釈しやすい
- **弱み**: 予測速度が遅い・メモリ使用量が多い

**デフォルトパラメータ**:
```python
{
    'n_estimators': 100,
    'max_depth': 10,
    'min_samples_split': 5,
    'random_state': 42
}
```

## 📜 実装ルール

### 1. 必須メソッド実装
全モデルは`BaseMLModel`を継承し、以下を実装する必要があります：

```python
class ConcreteModel(BaseMLModel):
    def _create_model(self):
        """モデルインスタンス作成"""
        return ModelClass(**self.params)
    
    def _get_model_params(self):
        """モデル固有パラメータ"""
        return {'param1': value1, ...}
    
    def get_feature_importance(self):
        """特徴量重要度取得（オプション）"""
        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_
        return None
```

### 2. エラーハンドリング
```python
# 学習前の予測を防ぐ
if not self.is_fitted:
    raise ValueError("Model not fitted. Call fit() first.")

# データ検証
if len(X) < 50:
    raise ValueError("Insufficient training data")
```

### 3. 状態管理
```python
# 学習完了後
self.is_fitted = True
self.feature_names = X.columns.tolist()
self.classes_ = np.unique(y)
```

### 4. パフォーマンス最適化
- 大規模データ: バッチ処理・メモリ効率を考慮
- 並列処理: `n_jobs=-1`で全CPUコア使用
- 早期停止: 過学習防止のための早期停止設定

## 🔧 カスタマイズガイド

### 新規モデル追加手順

1. **BaseMLModelを継承**
```python
from .base_model import BaseMLModel

class NewModel(BaseMLModel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
```

2. **必須メソッド実装**
```python
def _create_model(self):
    return YourModelClass(**self.params)

def _get_model_params(self):
    return {
        'param1': self.params.get('param1', default_value),
        # ...
    }
```

3. **__init__.pyに追加**
```python
from .new_model import NewModel
__all__ = [..., 'NewModel']
```

### パラメータ調整例

```python
# 過学習対策
lgbm_model = LGBMModel(
    n_estimators=50,      # 木の数を減らす
    max_depth=3,          # 深さを制限
    min_child_samples=20  # 葉の最小サンプル数
)

# 速度重視
xgb_model = XGBModel(
    n_estimators=50,
    tree_method='hist',   # ヒストグラムベース
    n_jobs=-1            # 全CPU使用
)
```

## 📊 性能比較ガイドライン

| モデル | 学習速度 | 予測速度 | メモリ効率 | 過学習耐性 | 解釈性 |
|--------|----------|----------|------------|------------|--------|
| LightGBM | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| XGBoost | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| RandomForest | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## ⚠️ 注意事項

### 1. メモリ管理
- 大規模データセット時は`del`で不要な変数を削除
- `gc.collect()`で明示的なガベージコレクション

### 2. 再現性確保
- 全モデルで`random_state=42`を設定
- 学習データの順序を固定

### 3. バージョン互換性
- scikit-learn: >=1.0.0
- lightgbm: >=3.0.0
- xgboost: >=1.5.0

## 🔮 拡張計画（Phase 11以降・CI/CD統合基盤活用）

### Phase 12での改善予定（GitHub Actions基盤）
1. **CatBoostモデル追加**: カテゴリ特徴量の自動処理・CI/CD品質ゲート対応
2. **パラメータ自動調整**: Optuna統合・24時間監視統合
3. **GPU対応**: CUDA環境での高速化・段階的デプロイ対応
4. **オンライン学習**: 逐次的なモデル更新・監視統合

---

**作成日**: 2025年Phase 5実装
**最終更新**: Phase 5完了（2025年8月18日）