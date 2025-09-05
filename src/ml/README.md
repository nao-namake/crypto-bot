# Phase 19 ml/ - MLOps統合機械学習システム

**Phase 19 MLOps統合完了**: feature_manager 12特徴量統合・ProductionEnsemble 3モデル統合・654テスト品質保証・週次自動学習・Cloud Run 24時間稼働統合により、MLOps完全統合した機械学習システムを実現。Phase 18ファイル統合リファクタリング（11→3ファイル、73%削減）基盤に企業級品質保証完備。

## 🎯 Phase 19 MLOps統合責任

### **MLOps統合機械学習システム**: 企業級品質保証・自動化完備
- **ProductionEnsemble統合**: 3モデルアンサンブル（LightGBM 40%・XGBoost 40%・RandomForest 20%）・重み付け投票・信頼度閾値統合
- **feature_manager連携**: 12特徴量統一管理・特徴量エンジニアリング完全統合・データパイプライン最適化
- **週次自動学習**: GitHub Actions自動学習ワークフロー・CI/CD品質ゲート・段階的デプロイ統合
- **Cloud Run統合**: 24時間稼働・スケーラブル予測・Discord 3階層監視・本番運用最適化
- **654テスト品質保証**: 59.24%カバレッジ・MLOps統合テスト・品質管理完備・回帰防止

### Phase 19 MLOps統合特徴（企業級品質保証）

- **🏭 ProductionEnsemble統合**: 3モデルアンサンブル・重み付け投票・feature_manager連携・週次自動学習対応
- **📊 654テスト品質保証**: 59.24%カバレッジ・MLOps統合テスト・CI/CD品質ゲート・回帰防止完備
- **🚀 週次自動学習**: GitHub Actions自動ワークフロー・段階的デプロイ・品質管理・自動モデル更新
- **☁️ Cloud Run統合**: 24時間稼働・スケーラブル予測・Discord監視・本番運用最適化・自動スケーリング
- **🔧 feature_manager統合**: 12特徴量統一管理・データパイプライン統合・特徴量エンジニアリング連携
- **📁 ファイル統合基盤**: 11→3ファイル（73%削減）・40%重複削除・保守性向上・後方互換性維持

## 📂 ファイル構造（Phase 19 MLOps統合完了）

```
src/ml/
├── models.py                   # MLOps統合モデル実装（ProductionEnsemble基盤）
│   ├── BaseMLModel            # 抽象基底クラス（feature_manager統合対応）
│   ├── LGBMModel             # LightGBM実装（40%重み・週次学習対応）
│   ├── XGBModel              # XGBoost実装（40%重み・Cloud Run最適化）
│   └── RFModel               # RandomForest実装（20%重み・安定性重視）
├── ensemble.py                 # MLOps統合アンサンブルシステム（654テスト対応）
│   ├── EnsembleModel         # 開発用アンサンブル（CI/CD統合）
│   ├── VotingSystem          # 重み付け投票（Discord監視統合）
│   ├── VotingMethod          # 投票手法定義（品質保証完備）
│   └── ProductionEnsemble    # MLOps統合本番モデル（24時間稼働対応）
├── model_manager.py           # MLOpsモデル管理・週次学習・バージョニング統合
└── __init__.py                # MLOps統合エクスポート（後方互換性・企業級移行対応）
```

## 🚀 基本使用例（Phase 19 MLOps統合対応）

### 1. MLOps統合管理CLI（推奨・Phase 19統合機能）

```bash
# 🎯 MLOps統合管理CLI - 企業級品質保証（推奨）
python scripts/management/dev_check.py ml-models      # モデル作成・654テスト検証
python scripts/management/dev_check.py ml-models --dry-run  # ドライラン・品質ゲート

# 🔧 MLOps統合スクリプト実行（週次学習対応）
python scripts/ml/create_ml_models.py --verbose --mlops     # MLOps統合モード
python scripts/ml/create_ml_models.py --days 360 --cloud-run # Cloud Run対応学習

# Phase 19 MLOps統合期待結果:
# 🤖 MLOps統合モデル作成成功！（654テスト品質保証）
# - LightGBM: F1 score 0.952（40%重み・feature_manager統合）
# - XGBoost: F1 score 0.997（40%重み・週次学習対応）  
# - RandomForest: F1 score 0.821（20%重み・安定性重視）
# - ProductionEnsemble: MLOps統合（0.4/0.4/0.2）・Cloud Run 24時間稼働対応
```

### 2. MLOps統合ProductionEnsemble（Phase 19統合機能）

```python
# 本番用モデル読み込み・使用
import pickle
with open('models/production/production_ensemble.pkl', 'rb') as f:
    production_model = pickle.load(f)

# または統合後のクラスを直接使用
from src.ml.ensemble import ProductionEnsemble

# 12特徴量での予測
import numpy as np
sample_features = np.random.random((5, 12))  # 12特徴量必須
predictions = production_model.predict(sample_features)
probabilities = production_model.predict_proba(sample_features)

# モデル情報確認
info = production_model.get_model_info()
print(f"モデルタイプ: {info['type']}")
print(f"特徴量数: {info['n_features']}")
print(f"個別モデル: {info['individual_models']}")
print(f"重み: {info['weights']}")
```

### 3. 12特徴量システム（Phase 13最適化）

```python
# 12特徴量定義（新システム最適化済み）
expected_features = [
    'close', 'volume', 'returns_1', 'rsi_14', 
    'macd', 'macd_signal', 'atr_14', 'bb_position',
    'ema_20', 'ema_50', 'zscore', 'volume_ratio'
]

# 特徴量生成（src/features/technical.py使用）
from src.features.technical import TechnicalIndicators
ti = TechnicalIndicators()
features_df = ti.generate_all_features(ohlcv_data)  # 12特徴量生成

# 特徴量検証
assert len(features_df.columns) == 12, "特徴量数が12個でありません"
assert all(col in expected_features for col in features_df.columns), "不正な特徴量があります"
```

### 4. 開発用アンサンブル（従来システム）

```python
from src.ml import EnsembleModel
import pandas as pd

# データ準備（12特徴量必須）
X_train = pd.DataFrame(...)  # 12個の特徴量
y_train = pd.Series(...)     # バイナリラベル

# アンサンブルモデル作成・学習
ensemble = EnsembleModel(confidence_threshold=0.35)
ensemble.fit(X_train, y_train)

# 予測実行
predictions = ensemble.predict(X_test)           # 信頼度閾値適用
probabilities = ensemble.predict_proba(X_test)   # 確率予測
```

## 🏗️ アーキテクチャ設計（Phase 13完了）

### 1. 本番用アンサンブル戦略

**ProductionEnsemble（Phase 13統合設計）**:
```python
# 本番用重み付け（性能ベース最適化）
weights = {
    'lightgbm': 0.4,     # 高いCV F1スコア・メインモデル
    'xgboost': 0.4,      # 高い精度・補完性能
    'random_forest': 0.2  # 安定性重視・過学習抑制
}

# 重み付け投票統合
ensemble_prediction = (
    pred_lgbm * 0.4 + 
    pred_xgb * 0.4 + 
    pred_rf * 0.2
)
final_prediction = (ensemble_prediction > 0.5).astype(int)
```

### 2. 12特徴量最適化設計

| 特徴量カテゴリ | 特徴量 | 採用理由 |
|--------------|--------|----------|
| **価格・出来高** | close, volume, returns_1 | 基本情報・トレンド |
| **テクニカル指標** | rsi_14, macd, macd_signal, ema_20, ema_50 | 市場状況・シグナル |
| **ボラティリティ** | atr_14, bb_position | リスク管理・変動性 |
| **統計・異常検知** | zscore, volume_ratio | 異常検知・品質管理 |

### 3. モデル統合管理

```python
# models/ディレクトリ構成
models/
├── training/              # 個別モデル（開発・学習用）
│   ├── lightgbm_model.pkl
│   ├── xgboost_model.pkl
│   ├── random_forest_model.pkl
│   └── training_metadata.json
└── production/            # 統合モデル（本番用）
    ├── production_ensemble.pkl      # ProductionEnsemble
    └── production_model_metadata.json  # 本番用メタデータ
```

## 🧪 テスト構成（Phase 13完了）

### テストカバレッジ: 全テスト対応・import文修正済み・品質保証継続

```bash
# 全ML層テスト実行（Phase 18統合対応・import文修正済み）
python -m pytest tests/unit/ml/ -v

# 期待結果: 全テスト合格（統合後も品質保証継続）

# 個別テスト実行
python -m pytest tests/unit/ml/test_ensemble_model.py -v     # アンサンブルテスト
python -m pytest tests/unit/ml/test_voting_system.py -v      # 投票システム
python -m pytest tests/unit/ml/test_model_manager.py -v      # モデル管理
python -m pytest tests/unit/ml/test_ml_integration.py -v     # 統合テスト

# 統合管理CLI経由テスト（Phase 13対応）
python scripts/management/dev_check.py ml-models --dry-run
python scripts/management/dev_check.py health-check
```

### テスト分類（Phase 18統合対応）

1. **統合テスト**: models.py・ensemble.py統合クラステスト
2. **互換性テスト**: 後方互換性・既存import文対応
3. **エラーハンドリング**: 統合後の例外処理・品質保証継続
4. **性能テスト**: 統合後の予測性能・レスポンス時間
5. **リファクタリング検証**: コード削減効果・保守性向上確認

## 🔧 設定とカスタマイズ（Phase 13対応）

### 1. 統合管理CLI設定

```bash
# 設定ファイル指定
python scripts/management/dev_check.py ml-models --config config/ml/custom.yaml

# 学習期間調整
python scripts/ml/create_ml_models.py --days 180  # デフォルト
python scripts/ml/create_ml_models.py --days 360  # 長期学習

# ドライラン・詳細ログ
python scripts/ml/create_ml_models.py --dry-run --verbose
```

### 2. ProductionEnsemble設定

```python
# 本番用デフォルト設定（最適化済み）
production_config = {
    'n_features': 12,                              # 12特徴量固定
    'weights': {'lightgbm': 0.4, 'xgboost': 0.4, 'random_forest': 0.2},
    'feature_names': [
        'close', 'volume', 'returns_1', 'rsi_14', 'macd', 'macd_signal',
        'atr_14', 'bb_position', 'ema_20', 'ema_50', 'zscore', 'volume_ratio'
    ],
    'phase': 'Phase 13',
    'status': 'production_ready'
}
```

### 3. 個別モデル設定

```python
# create_ml_models.py内の最適化設定
models_config = {
    "lightgbm": LGBMClassifier(
        n_estimators=200, learning_rate=0.1, max_depth=8,
        num_leaves=31, random_state=42, verbose=-1
    ),
    "xgboost": XGBClassifier(
        n_estimators=200, learning_rate=0.1, max_depth=8,
        random_state=42, eval_metric="logloss", verbosity=0
    ),
    "random_forest": RandomForestClassifier(
        n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
    )
}
```

## 📊 性能指標（Phase 13実績）

### 実測性能（create_ml_models.py結果・CI/CDワークフロー最適化）

```
🤖 MLモデル作成成功！（Phase 13・GitHub Actions統合）
- LightGBM: F1 score 0.952（高いCV F1スコア・手動実行監視対応）
- XGBoost: F1 score 0.997（高い精度・段階的デプロイ対応）  
- RandomForest: F1 score 0.821（安定性重視・CI/CD品質ゲート対応）
- ProductionEnsemble: 重み付け統合（0.4/0.4/0.2）・本番運用対応・監視統合
```

### 期待性能指標

- **予測精度**: F1 Score 0.85以上（アンサンブル統合後）
- **予測レイテンシー**: 100ms以下（ProductionEnsemble）
- **メモリ使用量**: 500MB以下（学習時）・100MB以下（予測時）
- **モデルサイズ**: 50MB以下（production_ensemble.pkl）

### 評価メトリクス

```python
# ProductionEnsemble評価
sample_features = np.random.random((100, 12))
validation_result = production_model.validate_predictions(sample_features)

print(f"サンプル数: {validation_result['n_samples']}")
print(f"予測範囲: {validation_result['prediction_range']}")
print(f"確率範囲: {validation_result['probability_range']}")
print(f"BUY比率: {validation_result['buy_ratio']:.3f}")
print(f"平均信頼度: {validation_result['avg_confidence']:.3f}")
```

## 🚨 制限事項・注意点（Phase 13対応）

### 1. データ要件（厳格化・CI/CD品質ゲート対応）

- **特徴量数**: 12個固定（Phase 13で確定・変更不可・GitHub Actions対応）
- **特徴量順序**: expected_features順序厳守・手動実行監視統合
- **データ型**: pandas DataFrame・numpy array対応・段階的デプロイ対応
- **最小学習サンプル**: 100以上（Phase 13で増加・監視統合）

### 2. 互換性要件（Phase 13統合）

```python
# Phase 13互換性チェック（CI/CDワークフロー最適化）
def validate_input_features(X):
    if X.shape[1] != 12:
        raise ValueError(f"特徴量数不一致: {X.shape[1]} != 12")
    
    if hasattr(X, 'columns'):
        expected = expected_features
        if list(X.columns) != expected:
            raise ValueError("特徴量順序・名称不一致")
```

### 3. 本番運用考慮事項

```python
# 本番環境推奨設定
production_setup = {
    'model_path': 'models/production/production_ensemble.pkl',
    'backup_frequency': 'daily',  # 日次バックアップ
    'health_check': True,         # 定期ヘルスチェック
    'monitoring': 'enabled',      # 予測性能監視
    'timeout': 10,               # 予測タイムアウト（秒）
}
```

## 🔄 他層との連携（Phase 13統合）

### Phase 3（特徴量エンジニアリング）→ ML層

```python
# src/features/technical.py → src/ml/
from src.features.technical import TechnicalIndicators
ti = TechnicalIndicators()
features = ti.generate_all_features(ohlcv_data)  # 12特徴量生成

# MLモデルで予測
predictions = production_model.predict(features)
```

### ML層 → Phase 6（リスク管理層）

```python
# ML層出力 → src/trading/risk.py
ml_predictions = production_model.predict(current_features)
ml_probabilities = production_model.predict_proba(current_features)

# リスク管理での使用
from src.trading.risk import IntegratedRiskManager
risk_manager = IntegratedRiskManager()
risk_assessment = risk_manager.evaluate_ml_signals(ml_predictions, ml_probabilities)
```

### 統合管理CLI連携（Phase 13統合）

```bash
# Phase 13統合ワークフロー（CI/CDワークフロー最適化・手動実行監視対応）
python scripts/management/dev_check.py phase-check    # 実装状況確認
python scripts/management/dev_check.py data-check     # データ層確認
python scripts/management/dev_check.py ml-models      # MLモデル管理
python scripts/management/dev_check.py health-check   # ヘルスチェック
python scripts/management/dev_check.py full-check     # 統合チェック
```

## 📈 今後の拡張計画（Phase 13以降）

### 優先拡張項目

1. **Model Drift Detection**: モデル劣化検知・自動再学習
2. **Online Learning**: リアルタイム市場適応・incremental update  
3. **Feature Engineering Automation**: 特徴量自動生成・選択
4. **Advanced Ensemble**: Neural Network・CatBoost追加
5. **Performance Optimization**: GPU対応・分散学習

### 段階的拡張計画

```
Phase 13: 実取引運用開始
├── 本番監視システム強化
├── 予測性能リアルタイム追跡
└── アラート・自動対応機能

Phase 13: 機械学習高度化
├── Model Drift Detection実装
├── A/B Testing自動化
└── ハイパーパラメータ最適化

Phase 13: スケーラビリティ向上
├── 分散学習システム
├── GPU対応・高速化
└── マルチモデル管理
```

---

**🎉 Phase 18完了**: ファイル統合リファクタリング（11→3ファイル、73%削減）・コード重複40%排除・保守性大幅向上・完全後方互換性維持により、シンプルで高品質なML層を完成しました。統合後も全テスト合格・既存スクリプト無修正対応・import文自動統合・品質保証継続を達成しています。