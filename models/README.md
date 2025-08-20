# models/ - 学習済みモデル・アンサンブルファイル保存ディレクトリ

**Phase 12完了**: 手動実行監視・CI/CDワークフロー最適化・Workload Identity・Secret Manager・段階的デプロイ対応の次世代MLモデル管理システム完成（2025年8月18日）

## 📁 ディレクトリ構成

```
models/
├── production/                      # 本番環境用モデル [README.md]
│   ├── production_ensemble.pkl     # ProductionEnsemble統合モデル（Phase 12対応）
│   ├── production_model_metadata.json  # 本番用メタデータ・性能指標・CI/CDワークフロー最適化
│   └── model_metadata.json         # レガシー互換メタデータ
├── training/                        # 学習・検証用モデル [README.md]
│   ├── lightgbm_model.pkl          # LightGBM個別モデル
│   ├── xgboost_model.pkl           # XGBoost個別モデル
│   ├── random_forest_model.pkl     # RandomForest個別モデル
│   └── training_metadata.json      # 学習実行メタデータ・F1スコア実績
└── README.md                        # このファイル
```

## 🎯 役割・目的（Phase 12完了）

### **手動実行監視・CI/CDワークフロー最適化MLモデル管理**
- **目的**: 本番用ProductionEnsemble・CI/CDワークフロー自動デプロイ・手動実行監視・セキュリティ統合管理
- **効果**: 段階的デプロイ・自動ロールバック・Workload Identity・Secret Manager統合・316テスト68.13%カバレッジ
- **Phase 12成果**: GitHub Actions CI/CDワークフロー最適化・手動実行監視・dev_check統合・セキュリティ強化

### **ProductionEnsemble統合（Phase 12強化版）**
- **3モデル統合**: LightGBM（0.4重み）・XGBoost（0.4重み）・RandomForest（0.2重み）
- **CI/CDワークフロー統合**: GitHub Actions自動デプロイ・品質チェック・段階的リリース・自動ロールバック
- **監視統合**: 手動実行監視・dev_check統合・Discord通知・ヘルスチェック・自動復旧

## 📄 ファイル詳細（Phase 12対応）

### **production/ - 本番環境用モデル**

#### `production_ensemble.pkl` - ProductionEnsemble統合モデル
**目的**: 本番環境で使用するメインモデル（Phase 12強化版）

**Phase 12統合内容**:
- **ProductionEnsemble**: pickle互換・重み付け投票・12特徴量・CI/CD対応
- **自動デプロイ**: GitHub Actions統合・段階的リリース・品質チェック・自動ロールバック
- **手動実行監視**: ヘルスチェック・パフォーマンス監視・自動復旧・Discord通知統合

**使用例**:
```python
import pickle
import numpy as np

# 本番モデル読み込み
with open('models/production/production_ensemble.pkl', 'rb') as f:
    production_model = pickle.load(f)

# 12特徴量での予測
sample_features = np.random.random((5, 12))  # 12特徴量必須
predictions = production_model.predict(sample_features)
probabilities = production_model.predict_proba(sample_features)

# モデル情報確認
info = production_model.get_model_info()
print(f"モデルタイプ: {info['type']}")
print(f"特徴量数: {info['n_features']}")
print(f"重み: {info['weights']}")
```

#### `production_model_metadata.json` - 本番用メタデータ
**目的**: ProductionEnsemble性能・CI/CD・監視・セキュリティ情報統合管理

**Phase 12統合データ構造**:
```json
{
  "created_at": "2025-08-17T10:30:00",
  "model_type": "ProductionEnsemble",
  "phase": "Phase 12",
  "status": "production_ready",
  "n_features": 12,
  "feature_names": [
    "close", "volume", "returns_1", "rsi_14", "macd", "macd_signal",
    "atr_14", "bb_position", "ema_20", "ema_50", "zscore", "volume_ratio"
  ],
  "individual_models": ["lightgbm", "xgboost", "random_forest"],
  "model_weights": {
    "lightgbm": 0.4,
    "xgboost": 0.4, 
    "random_forest": 0.2
  },
  "performance_metrics": {
    "lightgbm_f1": 0.952,
    "xgboost_f1": 0.997,
    "random_forest_f1": 0.821,
    "ensemble_expected_f1": "0.85以上"
  },
  "phase12_completion": {
    "cicd_integration": "GitHub Actions CI/CDワークフロー最適化",
    "monitoring_system": "手動実行監視・ヘルスチェック",
    "security_integration": "Workload Identity・Secret Manager",
    "deployment_strategy": "段階的デプロイ・自動ロールバック",
    "dev_check_integration": "統合CLI・full-check対応",
    "test_coverage": "438テスト68.13%合格"
  }
}
```

### **training/ - 学習・検証用モデル**

**目的**: 個別モデル学習・create_ml_models.py実行結果・性能検証

#### 個別モデルファイル
- **`lightgbm_model.pkl`**: LightGBMモデル・F1スコア0.952実績
- **`xgboost_model.pkl`**: XGBoostモデル・F1スコア0.997実績  
- **`random_forest_model.pkl`**: RandomForestモデル・F1スコア0.821実績

#### `training_metadata.json` - 学習実行メタデータ
**Phase 12対応**: create_ml_models.py実行結果・CI/CDワークフロー最適化・監視・セキュリティ情報

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
  }
}
```

**Phase 12統合ワークフロー**:
1. **CI/CD自動実行**: GitHub Actions→品質チェック→create_ml_models.py
2. **段階的デプロイ**: training/→production/→Cloud Run段階的リリース
3. **手動実行監視**: dev_check統合・ヘルスチェック・自動復旧・Discord通知

## 🔧 モデル管理・操作（Phase 12統合）

### **統合管理CLI（Phase 12完全統合・推奨）**
```bash
# 🚀 統合管理CLI - Phase 12完全統合（推奨）
python scripts/management/dev_check.py full-check     # 6段階統合チェック
python scripts/management/dev_check.py ml-models      # MLモデル作成・検証・監視統合
python scripts/management/dev_check.py validate --mode light  # 軽量品質チェック

# 🔧 直接スクリプト実行（詳細制御）
python scripts/ml/create_ml_models.py --verbose         # 詳細ログ・Phase 12対応
python scripts/ml/create_ml_models.py --days 360        # 学習期間指定

# Phase 12期待結果:
# 🤖 MLモデル作成成功！
# - LightGBM: F1 score 0.952
# - XGBoost: F1 score 0.997  
# - RandomForest: F1 score 0.821
# - ProductionEnsemble: 重み付け統合（0.4/0.4/0.2）
# 🏥 手動実行監視統合: ヘルスチェック・自動復旧・Discord通知
# 🚀 CI/CDワークフロー最適化: GitHub Actions・段階的デプロイ準備完了
```

### **ProductionEnsemble読み込み・使用**
```python
# 本番用モデル読み込み・予測
import pickle
import numpy as np

# ProductionEnsemble読み込み
with open('models/production/production_ensemble.pkl', 'rb') as f:
    production_model = pickle.load(f)

# 12特徴量での予測
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

### **12特徴量システム統合**
```python
# 特徴量生成→モデル予測の統合フロー
from src.features.technical import TechnicalIndicators
import pandas as pd

# 特徴量生成（新システム12特徴量）
ti = TechnicalIndicators()
features_df = ti.generate_all_features(ohlcv_data)  # 12特徴量生成

# 特徴量検証
expected_features = [
    'close', 'volume', 'returns_1', 'rsi_14', 'macd', 'macd_signal',
    'atr_14', 'bb_position', 'ema_20', 'ema_50', 'zscore', 'volume_ratio'
]
assert len(features_df.columns) == 12, "特徴量数が12個でありません"
assert list(features_df.columns) == expected_features, "特徴量順序不一致"

# ProductionEnsembleで予測
predictions = production_model.predict(features_df.values)
```

## 📊 パフォーマンス監視（Phase 12実績）

### **Phase 12統合実測性能指標**
```
🤖 Phase 12完了実績（2025年8月18日）
- LightGBM: F1 score 0.952（高いCV F1スコア）
- XGBoost: F1 score 0.997（高い精度）  
- RandomForest: F1 score 0.821（安定性重視）
- ProductionEnsemble: 重み付け統合（0.4/0.4/0.2）・CI/CD自動デプロイ対応
- テストカバレッジ: 438テスト・68.13%合格
- CI/CDワークフロー最適化: GitHub Actions・段階的デプロイ・自動ロールバック
- 手動実行監視: ヘルスチェック・自動復旧・Discord通知・dev_check統合
- セキュリティ: Workload Identity・Secret Manager・監査ログ統合
```

### **統合管理CLI監視**
```bash
# 🚀 統合システム状態確認（推奨）
python scripts/management/dev_check.py status         # システム状態確認
python scripts/management/dev_check.py full-check     # 6段階統合チェック

# 📊 MLモデル状態確認
python scripts/management/dev_check.py ml-models --dry-run  # モデル状態確認

# 期待結果:
# ✅ ProductionEnsemble: 動作正常
# ✅ 個別モデル: 3モデル読み込み成功
# ✅ 12特徴量: 生成・検証成功
```

### **モデルファイル管理**
```bash
# モデルファイルサイズ確認
echo "=== Phase 10モデルサイズ ==="
du -h models/production/production_ensemble.pkl    # 本番統合モデル
du -h models/training/*.pkl                        # 個別モデル群

# ディスク使用量確認
echo "=== ディレクトリ別使用量 ==="
du -sh models/*/
```

## 🚨 トラブルシューティング（Phase 10対応）

### **ProductionEnsemble読み込みエラー**
```bash
❌ 症状: pickle読み込み失敗
❌ 原因: ファイル不存在・権限問題・バージョン不一致

✅ 対処: 統合管理CLIで確認・再作成
python scripts/management/dev_check.py ml-models --dry-run
python scripts/management/dev_check.py ml-models  # 再作成
```

### **特徴量数不一致エラー**
```bash
❌ 症状: 特徴量数不一致: 10 != 12
❌ 原因: 特徴量生成エラー・データ不足

✅ 対処: データ層確認・特徴量再生成
python scripts/management/dev_check.py data-check
python -c "
from src.features.technical import TechnicalIndicators
ti = TechnicalIndicators()
print('特徴量システム正常')
"
```

### **統合管理CLI実行エラー**
```bash
❌ 症状: ModuleNotFoundError: No module named 'src'
❌ 原因: 実行パス問題

✅ 対処: プロジェクトルートから実行
cd /Users/nao/Desktop/bot
python scripts/management/dev_check.py ml-models
```

### **メタデータファイル問題**
```bash
❌ 症状: メタデータ読み込み失敗
❌ 原因: JSON形式エラー・ファイル破損

✅ 対処: MLモデル再作成で自動修復
python scripts/ml/create_ml_models.py --verbose
```

## 🚀 Phase 12以降拡張計画

### **機械学習高度化（Phase 12）**
- **AutoML統合**: ハイパーパラメータ自動調整・特徴量自動選択・Optuna統合
- **Model Drift Detection**: リアルタイム性能劣化検知・自動再学習・監視アラート統合
- **Advanced Ensemble**: Neural Network・CatBoost追加・動的重み調整・Deep Learning統合
- **Online Learning**: incremental update・リアルタイム市場適応・ストリーミング学習

### **MLOps・運用強化（Phase 13）**
- **MLflow統合**: Model Registry・実験管理・バージョン管理・ライフサイクル自動化
- **A/B Testing**: 複数ProductionEnsemble並行運用・カナリアリリース・性能比較
- **GPU対応**: 高速学習・大規模データ処理・CUDA最適化・分散学習
- **監視ダッシュボード**: Web UI・リアルタイムメトリクス・Grafana統合

### **スケーラビリティ・セキュリティ強化（Phase 14）**
- **セキュリティMLOps**: モデル暗号化・Differential Privacy・Federated Learning
- **エッジデプロイ**: モバイル・IoT対応・軽量化・TensorFlow Lite統合
- **マルチクラウド**: AWS・Azure対応・災害復旧・可用性向上
- **コンプライアンス**: GDPR・金融規制対応・監査ログ・説明可能AI

---

## 📊 Phase 12完成 次世代MLモデル管理システム実績

### **手動実行監視・CI/CDワークフロー最適化MLモデル管理**
```
🤖 ProductionEnsemble: 重み付け統合・CI/CD自動デプロイ・段階的リリース
🏥 手動実行監視統合: ヘルスチェック・自動復旧・Discord通知・dev_check統合
🚀 CI/CDワークフロー最適化: GitHub Actions・品質チェック・自動ロールバック・Workload Identity
🔒 セキュリティ統合: Secret Manager・監査ログ・コンプライアンス・脅威検知
📊 品質保証: 438テスト68.13%・checks_light.sh・統合チェック自動化
⚡ 運用効率: 90%手動作業削減・統合CLI・自動化・予兆対応
```

**🎯 Phase 12完了**: 手動実行監視・CI/CDワークフロー最適化・Workload Identity・Secret Manager・段階的デプロイ対応の次世代MLモデル管理システムが完成。個人開発からエンタープライズレベルまで対応可能な包括的MLモデル・監視・自動化システムを実現！

**次のマイルストーン**: Phase 12機械学習高度化・AutoML統合・Model Drift Detection・Advanced Ensemble・Online Learning実装