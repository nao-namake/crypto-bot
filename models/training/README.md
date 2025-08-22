# models/training/ - 学習・検証用モデルディレクトリ

**Phase 13完了**: sklearn警告解消・設定最適化・306テスト100%成功・CI/CD本番稼働・create_ml_models.py個別モデル学習システム完成（2025年8月22日）

## 📁 実装完了ファイル構成

```
models/training/
├── lightgbm_model.pkl          # LightGBM個別モデル（F1: 0.941・578KB）
├── xgboost_model.pkl           # XGBoost個別モデル（F1: 0.992・881KB）
├── random_forest_model.pkl     # RandomForest個別モデル（F1: 0.699・5.9MB）
├── training_metadata.json      # 学習実行メタデータ・sklearn警告解消・最新性能指標
└── README.md                    # このファイル
```

## 🎯 役割・目的（Phase 13完了）

### **sklearn警告解消・設定最適化・CI/CD本番稼働create_ml_models.py**
- **目的**: sklearn警告完全解消・設定最適化・CI/CD本番稼働対応の個別モデル学習
- **Phase 13成果**: 306テスト100%成功・GitHub Actions本番稼働・品質保証完成
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク対応

### **Phase 13最新個別モデル検証・分析**
- **品質保証**: TimeSeriesSplit・sklearn警告解消・CI/CD本番稼働・品質チェック完成
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク
- **設定最適化**: config/gcp/・config/deployment/統合・不要ファイル削除対応

## 📄 実装完了ファイル詳細（Phase 13対応）

### 個別モデルファイル（最新実績）
**作成元**: `python scripts/ml/create_ml_models.py`（Phase 13 sklearn警告解消版）

#### `lightgbm_model.pkl` - LightGBMモデル
- **最新性能**: F1スコア 0.941（高安定性・sklearn警告解消・統合管理対応）
- **最適化設定**: n_estimators=200, learning_rate=0.1, max_depth=8, num_leaves=31
- **Phase 13統合**: sklearn警告解消・統合管理・品質チェック・ProductionEnsemble重み0.4

#### `xgboost_model.pkl` - XGBoostモデル  
- **最新性能**: F1スコア 0.992（最高精度維持・CI/CD本番稼働対応）
- **最適化設定**: n_estimators=200, learning_rate=0.1, max_depth=8
- **Phase 13統合**: GitHub Actions本番稼働・品質保証・設定最適化・ProductionEnsemble重み0.4

#### `random_forest_model.pkl` - RandomForestモデル
- **最新性能**: F1スコア 0.699（安定性重視・設定最適化対応・改善余地あり）
- **最適化設定**: n_estimators=200, max_depth=12, n_jobs=-1
- **Phase 13統合**: 設定最適化・統合管理・logs/reports/統合・ProductionEnsemble重み0.2

### `training_metadata.json` - 学習実行メタデータ
**目的**: create_ml_models.py実行結果・sklearn警告解消・統合管理・設定最適化統合情報

**Phase 13対応データ構造**:
```json
{
  "created_at": "2025-08-21T22:47:16",
  "phase": "Phase 13",
  "feature_optimization": "97→12特徴量削減",
  "sklearn_warnings": "全deprecation warning解消完了",
  "individual_models": {
    "lightgbm": {"f1_score": 0.941, "file": "lightgbm_model.pkl"},
    "xgboost": {"f1_score": 0.992, "file": "xgboost_model.pkl"},
    "random_forest": {"f1_score": 0.699, "file": "random_forest_model.pkl"}
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
  "phase13_completion": {
    "sklearn_warnings": "全deprecation warning解消完了",
    "config_optimization": "config/gcp/・config/deployment/統合",
    "logs_integration": "logs/reports/統合・ビジュアルナビゲーション",
    "test_coverage": "306テスト100%成功・coverage-reports/58.88%",
    "cicd_production": "GitHub Actions本番稼働・品質保証完成"
  }
}
```

## 🔧 統合管理・運用（Phase 13統合）

### **統合管理CLI運用（Phase 13完全統合・推奨）**
```bash
# 🚀 統合管理CLI - Phase 13完全統合（推奨）
python scripts/management/dev_check.py full-check     # 6段階統合チェック
python scripts/management/dev_check.py ml-models      # MLモデル作成・検証
python scripts/management/dev_check.py validate --mode light  # 軽量品質チェック

# 🔧 直接スクリプト実行（Phase 13 sklearn警告解消版）
python scripts/ml/create_ml_models.py --verbose         # 詳細ログ・統合管理
python scripts/ml/create_ml_models.py --days 360        # 学習期間指定・品質チェック

# Phase 13期待結果:
# 🤖 MLモデル作成成功！
# - LightGBM: F1 score 0.941（sklearn警告解消・統合管理対応）
# - XGBoost: F1 score 0.992（高精度維持・CI/CD本番稼働対応）  
# - RandomForest: F1 score 0.699（安定性重視・設定最適化対応）
# - ProductionEnsemble: 重み付け統合（0.4/0.4/0.2）・sklearn警告解消
# ✅ sklearn警告解消完了・306テスト100%成功
# 📊 CI/CD本番稼働・logs/reports/統合・品質保証完成
# 🔧 設定最適化: config/gcp/・config/deployment/統合
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
    print(f"sklearn警告: {training_meta.get('phase13_completion', {}).get('sklearn_warnings', 'N/A')}")
    
    return True
```

## 🚨 トラブルシューティング（Phase 13対応）

### **個別モデル読み込みエラー**
```bash
❌ 症状: pickle読み込み失敗・モデル不正・sklearn警告
❌ 原因: ファイル不存在・権限問題・scikit-learn バージョン不一致・deprecation warning

✅ 対処: MLモデル再作成（sklearn警告解消版）
python scripts/management/dev_check.py ml-models  # 再作成
python scripts/ml/create_ml_models.py --verbose     # 詳細ログで再作成
```

### **F1スコア実績確認エラー**
```bash
❌ 症状: training_metadata.json読み込み失敗・Phase情報不一致
❌ 原因: JSONファイル破損・形式エラー・Phase更新不備

✅ 対処: メタデータファイル再生成（Phase 13対応）
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

### **sklearn警告問題**
```bash
❌ 症状: sklearn deprecation warning大量発生
❌ 原因: 旧バージョンAPI使用・非推奨パラメータ

✅ 対処: sklearn警告解消済みMLモデル再作成
python scripts/ml/create_ml_models.py --verbose  # sklearn警告解消版
# 期待結果: Warning表示なし・最新API使用
```

## 🔧 ファイル管理ルール（Phase 13確立）

### **training/ディレクトリ管理ルール**
1. **個別モデルファイル**:
   - `{model_name}_model.pkl`形式必須
   - サイズ上限: 10MB（RandomForest: 5.9MB許容）
   - F1スコア0.5以上のモデルのみ保存（RandomForest: 0.699で許容）

2. **メタデータ管理**:
   - `training_metadata.json`: 学習実行結果統合・Phase 13情報必須
   - 実行時刻・性能指標・設定情報・sklearn警告状況記録必須
   - Phase情報・config最適化・logs統合状況記録

3. **保存期間**:
   - 最新1世代のみ保存（容量削減）
   - 古いモデルは必要に応じてアーカイブ・削除

### **品質保証ルール**
1. **sklearn警告解消**:
   - 全deprecation warning解消確認済みモデルのみ保存
   - 最新ライブラリ対応・互換性確保済み
   - create_ml_models.py実行時にwarning表示なし確認

2. **性能基準**:
   - LightGBM: F1スコア0.9以上維持
   - XGBoost: F1スコア0.9以上維持
   - RandomForest: F1スコア0.6以上許容（安定性重視）

3. **統合管理対応**:
   - logs/reports/統合対応確認
   - config/gcp/・config/deployment/統合対応
   - CI/CD本番稼働対応確認

### **バージョン管理ルール**
1. **Gitトラッキング**:
   - `.pkl`ファイル: Git LFS対象（大容量）
   - `.json`ファイル: 通常のGit管理
   - `README.md`: 必ずGit管理

2. **Phase更新ルール**:
   - 新Phase移行時は全メタデータのphase情報更新
   - sklearn警告解消状況記録
   - config最適化・logs統合状況記録

## 🚀 Phase 14以降拡張計画

### **機械学習高度化（Phase 14）**
- **AutoML統合**: Optuna自動ハイパーパラメータ調整・特徴量自動選択・実験管理
- **Model Drift Detection**: リアルタイム性能劣化検知・自動再学習・監視アラート統合
- **Advanced Models**: Neural Network・CatBoost・Transformer・Deep Learning統合
- **Online Learning**: incremental update・リアルタイム市場適応・ストリーミング学習

### **MLOps・実験管理（Phase 15）**
- **MLflow統合**: Model Registry・実験管理・バージョン管理・ライフサイクル自動化
- **A/B Testing**: 複数個別モデル性能比較・カナリアリリース・最適重み調整
- **GPU対応**: 高速学習・大規模データ処理・CUDA最適化・分散学習
- **実験ダッシュボード**: Web UI・リアルタイム性能追跡・Grafana統合

### **運用自動化・コンプライアンス（Phase 16）**
- **定期再学習**: monthly/weekly自動学習・条件達成時の自動本番昇格・通知システム
- **セキュリティMLOps**: モデル暗号化・Differential Privacy・Federated Learning
- **コンプライアンス**: GDPR・金融規制対応・監査ログ・説明可能AI・責任あるAI

---

## 📊 Phase 13完成 学習・検証用モデル統合実績

### **sklearn警告解消・設定最適化・CI/CD本番稼働create_ml_models.py**
```
🤖 個別モデル学習: LightGBM・XGBoost・RandomForest・sklearn警告解消・306テスト100%成功
📊 品質保証完成: CI/CD本番稼働・coverage-reports/58.88%・品質チェック自動化
🔧 統合管理: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク対応
⚙️ 設定最適化: config/gcp/・config/deployment/統合・不要ファイル削除・レガシー整理
✅ sklearn警告解消: 全deprecation warning解消・最新ライブラリ対応・互換性確保
🚀 CI/CD本番稼働: GitHub Actions本番稼働・段階的デプロイ・品質保証完成
```

**🎯 Phase 13完了**: sklearn警告解消・設定最適化・306テスト100%成功・CI/D本番稼働対応create_ml_models.py・個別モデル学習・ProductionEnsemble作成システムが完成。学習から本番デプロイまでの完全自動化・品質保証・統合管理による次世代MLOps環境を実現！

**次のマイルストーン**: Phase 14機械学習高度化・AutoML統合・Model Drift Detection・Advanced Models・Online Learning実装