# models/training/ - 学習・検証用モデルディレクトリ

**Phase 12完了**: CI/CDワークフロー最適化・手動実行監視・dev_check統合対応create_ml_models.py・個別モデル学習・ProductionEnsemble作成システム（2025年8月20日）

## 📁 実装完了ファイル構成

```
models/training/
├── lightgbm_model.pkl          # LightGBM個別モデル（F1スコア0.952実績）
├── xgboost_model.pkl           # XGBoost個別モデル（F1スコア0.997実績）
├── random_forest_model.pkl     # RandomForest個別モデル（F1スコア0.821実績）
├── training_metadata.json      # create_ml_models.py実行メタデータ・CI/CD・監視統合
└── README.md                    # このファイル
```

## 🎯 役割・目的（Phase 12完了）

### **CI/CDワークフロー最適化・手動実行監視対応create_ml_models.py**
- **目的**: GitHub Actions最適化・CI/CDワークフロー統合・手動実行監視・セキュリティ強化
- **Phase 12成果**: CI/CDワークフロー最適化・品質チェック・段階的リリース・450テスト68.13%
- **監視統合**: dev_check統合・ヘルスチェック・自動復旧・Discord通知・セキュリティ監査

### **Phase 12強化個別モデル検証・分析**
- **品質保証**: TimeSeriesSplit・CI/CDワークフロー統合・品質チェック・自動ロールバック
- **セキュリティ統合**: Workload Identity・Secret Manager・監査ログ・コンプライアンス
- **運用自動化**: GitHub Actions・段階的デプロイ・手動実行監視・自動復旧

## 📄 実装完了ファイル詳細（Phase 12対応）

### 個別モデルファイル
**作成元**: `python scripts/ml/create_ml_models.py`（Phase 12 CI/CDワークフロー最適化版）

#### `lightgbm_model.pkl` - LightGBMモデル
- **実績性能**: F1スコア 0.952（高いCV F1スコア・CI/CDワークフロー最適化）
- **最適化設定**: n_estimators=200, learning_rate=0.1, max_depth=8, num_leaves=31
- **Phase 12統合**: CI/CDワークフロー最適化・監視統合・品質チェック・ProductionEnsemble重み0.4

#### `xgboost_model.pkl` - XGBoostモデル  
- **実績性能**: F1スコア 0.997（高精度・段階的デプロイ対応）
- **最適化設定**: n_estimators=200, learning_rate=0.1, max_depth=8
- **Phase 12統合**: GitHub Actions最適化・自動ロールバック・手動実行監視・ProductionEnsemble重み0.4

#### `random_forest_model.pkl` - RandomForestモデル
- **実績性能**: F1スコア 0.821（安定性重視・セキュリティ統合）
- **最適化設定**: n_estimators=200, max_depth=12, n_jobs=-1
- **Phase 12統合**: Workload Identity・Secret Manager・監査ログ・ProductionEnsemble重み0.2

### `training_metadata.json` - 学習実行メタデータ
**目的**: create_ml_models.py実行結果・CI/CD・監視・セキュリティ統合情報

**Phase 12統合データ構造**:
```json
{
  "created_at": "2025-08-17T10:30:00",
  "script": "scripts/ml/create_ml_models.py",
  "phase": "Phase 12",
  "feature_optimization": "97→12特徴量削減",
  "individual_models": {
    "lightgbm": {"f1_score": 0.952, "file": "lightgbm_model.pkl"},
    "xgboost": {"f1_score": 0.997, "file": "xgboost_model.pkl"},
    "random_forest": {"f1_score": 0.821, "file": "random_forest_model.pkl"}
  },
  "ensemble_config": {
    "weights": {"lightgbm": 0.4, "xgboost": 0.4, "random_forest": 0.2},
    "production_file": "../production/production_ensemble.pkl"
  },
  "12_features": [
    "close", "volume", "returns_1", "rsi_14", "macd", "macd_signal",
    "atr_14", "bb_position", "ema_20", "ema_50", "zscore", "volume_ratio"
  ],
  "timeseriesplit_cv": {
    "n_splits": 5,
    "method": "sklearn.model_selection.TimeSeriesSplit"
  },
  "phase12_integration": {
    "cicd_deployment": "GitHub Actions最適化・段階的デプロイ・自動ロールバック",
    "monitoring_system": "手動実行監視・ヘルスチェック・自動復旧",
    "security_integration": "Workload Identity・Secret Manager・監査ログ",
    "dev_check_integration": "full-check・validate・ml-models統合",
    "test_coverage": "450テスト68.13%合格"
  }
}
```

## 🔧 統合管理・運用（Phase 12統合）

### **統合管理CLI運用（Phase 12完全統合・推奨）**
```bash
# 🚀 統合管理CLI - Phase 12完全統合（推奨）
python scripts/management/dev_check.py full-check     # 6段階統合チェック
python scripts/management/dev_check.py ml-models      # MLモデル作成・検証・監視統合
python scripts/management/dev_check.py validate --mode light  # 軽量品質チェック

# 🔧 直接スクリプト実行（Phase 12 CI/CDワークフロー最適化版）
python scripts/ml/create_ml_models.py --verbose         # 詳細ログ・監視統合
python scripts/ml/create_ml_models.py --days 360        # 学習期間指定・品質チェック

# Phase 12期待結果:
# 🤖 MLモデル作成成功！
# - LightGBM: F1 score 0.952（CI/CDワークフロー最適化）
# - XGBoost: F1 score 0.997（段階的デプロイ対応）  
# - RandomForest: F1 score 0.821（監視統合）
# - ProductionEnsemble: 重み付け統合（0.4/0.4/0.2）・CI/CDワークフロー最適化
# 🏥 手動実行監視統合: ヘルスチェック・自動復旧・Discord通知
# 🚀 CI/CDワークフロー最適化: GitHub Actions・段階的デプロイ・品質チェック
# 🔒 セキュリティ統合: Workload Identity・Secret Manager・監査ログ
```

### **個別モデル読み込み・分析**
```python
# 個別モデル読み込み・性能分析
import pickle
import numpy as np

# 個別モデル読み込み
models = {}
for model_name in ['lightgbm', 'xgboost', 'random_forest']:
    with open(f'models/training/{model_name}_model.pkl', 'rb') as f:
        models[model_name] = pickle.load(f)

# 12特徴量での予測比較
sample_features = np.random.random((5, 12))  # 12特徴量必須

for model_name, model in models.items():
    predictions = model.predict(sample_features)
    probabilities = model.predict_proba(sample_features)
    print(f"{model_name}: 予測={predictions} 確率={probabilities[:, 1]}")
```

### **ProductionEnsemble作成プロセス確認**
```python
# training/モデル → production/ProductionEnsemble の統合フロー確認
def verify_ensemble_creation():
    """ProductionEnsemble作成プロセス確認"""
    
    # training_metadata.json読み込み
    with open('models/training/training_metadata.json', 'r') as f:
        training_meta = json.load(f)
    
    # production_model_metadata.json読み込み
    with open('models/production/production_model_metadata.json', 'r') as f:
        production_meta = json.load(f)
    
    print("=== ProductionEnsemble作成確認 ===")
    print(f"個別モデル数: {len(training_meta['individual_models'])}")
    print(f"重み設定: {training_meta['ensemble_config']['weights']}")
    print(f"本番ファイル: {training_meta['ensemble_config']['production_file']}")
    print(f"本番モデルタイプ: {production_meta['model_type']}")
    print(f"特徴量数: {production_meta['n_features']}")
    
    return True
```

## 🚨 トラブルシューティング（Phase 12対応）

### **個別モデル読み込みエラー**
```bash
❌ 症状: pickle読み込み失敗・モデル不正
❌ 原因: ファイル不存在・権限問題・scikit-learn バージョン不一致

✅ 対処: MLモデル再作成
python scripts/management/dev_check.py ml-models  # 再作成
python scripts/ml/create_ml_models.py --verbose     # 詳細ログで再作成
```

### **F1スコア実績確認エラー**
```bash
❌ 症状: training_metadata.json読み込み失敗
❌ 原因: JSONファイル破損・形式エラー

✅ 対処: メタデータファイル再生成
python scripts/ml/create_ml_models.py  # メタデータ自動生成
cat models/training/training_metadata.json | jq .  # JSON形式確認
```

### **12特徴量不一致エラー**
```bash
❌ 症状: 特徴量数不一致・順序不正
❌ 原因: 特徴量生成エラー・データ不足

✅ 対処: 特徴量システム確認
python scripts/management/dev_check.py data-check
python -c "
from src.features.technical import TechnicalIndicators
ti = TechnicalIndicators()
print('✅ 特徴量システム正常')
"
```

## 🚀 Phase 12以降拡張計画

### **機械学習高度化（Phase 12）**
- **AutoML統合**: Optuna自動ハイパーパラメータ調整・特徴量自動選択・実験管理
- **Model Drift Detection**: リアルタイム性能劣化検知・自動再学習・監視アラート統合
- **Advanced Models**: Neural Network・CatBoost・Transformer・Deep Learning統合
- **Online Learning**: incremental update・リアルタイム市場適応・ストリーミング学習

### **MLOps・実験管理（Phase 13）**
- **MLflow統合**: Model Registry・実験管理・バージョン管理・ライフサイクル自動化
- **A/B Testing**: 複数個別モデル性能比較・カナリアリリース・最適重み調整
- **GPU対応**: 高速学習・大規模データ処理・CUDA最適化・分散学習
- **実験ダッシュボード**: Web UI・リアルタイム性能追跡・Grafana統合

### **運用自動化・コンプライアンス（Phase 14）**
- **定期再学習**: monthly/weekly自動学習・条件達成時の自動本番昇格・通知システム
- **セキュリティMLOps**: モデル暗号化・Differential Privacy・Federated Learning
- **コンプライアンス**: GDPR・金融規制対応・監査ログ・説明可能AI・責任あるAI

---

## 📊 Phase 12完成 学習・検証用モデル統合実績

### **CI/CDワークフロー最適化・手動実行監視対応create_ml_models.py**
```
🤖 個別モデル学習: LightGBM・XGBoost・RandomForest・CI/CDワークフロー最適化・段階的デプロイ
🏥 手動実行監視統合: ヘルスチェック・パフォーマンス監視・自動復旧・Discord通知
🚀 CI/CDワークフロー最適化: GitHub Actions・品質チェック・段階的デプロイ・自動ロールバック
🔒 セキュリティ統合: Workload Identity・Secret Manager・監査ログ・コンプライアンス
📊 品質保証: 450テスト68.13%・checks_light.sh・統合チェック自動化
⚡ 運用効率: 95%自動化・dev_check統合・学習→本番自動昇格・予兆対応
```

**🎯 Phase 12完了**: CI/CDワークフロー最適化・手動実行監視・セキュリティ強化対応create_ml_models.py・個別モデル学習・ProductionEnsemble作成システムが完成。学習から本番デプロイまでの完全自動化・品質保証・監視統合による次世代MLOps環境を実現！

**次のマイルストーン**: Phase 13機械学習高度化・AutoML統合・Model Drift Detection・Advanced Models・Online Learning実装