# models/ - 学習済みモデル・アンサンブルファイル保存ディレクトリ

**Phase 13完了**: sklearn警告解消・設定最適化・306テスト100%成功・CI/CD本番稼働・ProductionEnsemble統合モデル管理システム完成（2025年8月22日）

## 📁 ディレクトリ構成

```
models/
├── production/                      # 本番環境用モデル [README.md]
│   ├── production_ensemble.pkl     # ProductionEnsemble統合モデル（Phase 13対応）
│   ├── production_model_metadata.json  # 本番用メタデータ・306テスト実績・sklearn警告解消
│   └── model_metadata.json         # レガシー互換メタデータ（要整理）
├── training/                        # 学習・検証用モデル [README.md]
│   ├── lightgbm_model.pkl          # LightGBM個別モデル（F1: 0.941）
│   ├── xgboost_model.pkl           # XGBoost個別モデル（F1: 0.992）
│   ├── random_forest_model.pkl     # RandomForest個別モデル（F1: 0.699）
│   └── training_metadata.json      # 学習実行メタデータ・最新性能指標
└── README.md                        # このファイル
```

## 🎯 役割・目的（Phase 13完了）

### **sklearn警告解消・設定最適化・CI/CD本番稼働MLモデル管理**
- **目的**: 本番用ProductionEnsemble・sklearn警告完全解消・設定最適化・CI/CD本番稼働
- **効果**: 306テスト100%成功・CI/CD本番稼働・logs/reports/統合・coverage-reports/58.88%
- **Phase 13成果**: sklearn警告解消・config/gcp/統合・deployment/整理・品質保証完成

### **ProductionEnsemble統合（Phase 13最新版）**
- **3モデル統合**: LightGBM（0.4重み・F1: 0.941）・XGBoost（0.4重み・F1: 0.992）・RandomForest（0.2重み・F1: 0.699）
- **sklearn警告解消**: 全deprecation warning解消・最新ライブラリ対応・互換性確保
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク対応

## 📄 ファイル詳細（Phase 13対応）

### **production/ - 本番環境用モデル**

#### `production_ensemble.pkl` - ProductionEnsemble統合モデル
**目的**: 本番環境で使用するメインモデル（Phase 13最新版）

**Phase 13統合内容**:
- **ProductionEnsemble**: pickle互換・重み付け投票・12特徴量・sklearn警告解消対応
- **CI/CD本番稼働**: GitHub Actions本番稼働・306テスト100%・品質保証完成
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク

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
**目的**: ProductionEnsemble性能・バージョン・設定情報管理

**Phase 13対応データ構造**:
```json
{
  "created_at": "2025-08-22T07:00:00",
  "model_type": "ProductionEnsemble",
  "phase": "Phase 13",
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
    "lightgbm_f1": 0.941,
    "xgboost_f1": 0.992,
    "random_forest_f1": 0.699,
    "ensemble_expected_f1": "0.85以上"
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

#### `model_metadata.json` - レガシー互換メタデータ（要整理）
**現状**: Phase 9時代のメタデータファイル・production/内に配置不適切
**問題**: 個別モデルパスがproduction/を指している（実際はtraining/に存在）
**対処**: このファイルは削除候補・production_model_metadata.jsonに統合済み

### **training/ - 学習・検証用モデル**

**目的**: 個別モデル学習・create_ml_models.py実行結果・性能検証

#### 個別モデルファイル（最新実績）
- **`lightgbm_model.pkl`**: LightGBMモデル・F1スコア0.941実績・578KB
- **`xgboost_model.pkl`**: XGBoostモデル・F1スコア0.992実績・881KB  
- **`random_forest_model.pkl`**: RandomForestモデル・F1スコア0.699実績・5.9MB

#### `training_metadata.json` - 学習実行メタデータ
**Phase 13対応**: create_ml_models.py実行結果・最新性能指標・sklearn警告解消対応

```json
{
  "created_at": "2025-08-21T22:47:16",
  "phase": "Phase 13",
  "feature_optimization": "97→12特徴量削減",
  "sklearn_warnings": "解消完了",
  "individual_models": {
    "lightgbm": {"f1_score": 0.941, "file": "lightgbm_model.pkl"},
    "xgboost": {"f1_score": 0.992, "file": "xgboost_model.pkl"},
    "random_forest": {"f1_score": 0.699, "file": "random_forest_model.pkl"}
  },
  "ensemble_config": {
    "weights": {"lightgbm": 0.4, "xgboost": 0.4, "random_forest": 0.2},
    "production_file": "../production/production_ensemble.pkl"
  }
}
```

## 🔧 モデル管理・操作（Phase 13統合）

### **統合管理CLI（Phase 13完全統合・推奨）**
```bash
# 🚀 統合管理CLI - Phase 13完全統合（推奨）
python scripts/management/dev_check.py full-check     # 6段階統合チェック
python scripts/management/dev_check.py ml-models      # MLモデル作成・検証
python scripts/management/dev_check.py validate --mode light  # 軽量品質チェック

# 🔧 直接スクリプト実行（詳細制御）
python scripts/ml/create_ml_models.py --verbose         # 詳細ログ・Phase 13対応
python scripts/ml/create_ml_models.py --days 360        # 学習期間指定

# Phase 13期待結果:
# 🤖 MLモデル作成成功！
# - LightGBM: F1 score 0.941（sklearn警告解消）
# - XGBoost: F1 score 0.992（高精度維持）  
# - RandomForest: F1 score 0.699（安定性重視）
# - ProductionEnsemble: 重み付け統合（0.4/0.4/0.2）
# ✅ sklearn警告解消完了・306テスト100%成功
# 📊 CI/CD本番稼働・logs/reports/統合・品質保証完成
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

## 📊 パフォーマンス監視（Phase 13実績）

### **Phase 13統合実測性能指標**
```
🤖 Phase 13完了実績（2025年8月22日）
- LightGBM: F1 score 0.941（高安定性・sklearn警告解消）
- XGBoost: F1 score 0.992（最高精度維持）  
- RandomForest: F1 score 0.699（安定性重視・改善余地あり）
- ProductionEnsemble: 重み付け統合（0.4/0.4/0.2）・sklearn警告解消対応
- テストカバレッジ: 306テスト100%成功・coverage-reports/58.88%
- CI/CD本番稼働: GitHub Actions本番稼働・品質保証完成
- logs/reports/統合: ビジュアルナビゲーション・最新レポートリンク対応
- 設定最適化: config/gcp/・config/deployment/統合・不要ファイル削除
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
# ✅ sklearn警告: 解消完了
```

### **モデルファイル管理**
```bash
# モデルファイルサイズ確認
echo "=== Phase 13モデルサイズ ==="
du -h models/production/production_ensemble.pkl    # 本番統合モデル（7.4MB）
du -h models/training/*.pkl                        # 個別モデル群（合計7.4MB）

# ディスク使用量確認
echo "=== ディレクトリ別使用量 ==="
du -sh models/*/
# production/: 7.4MB
# training/: 7.4MB
```

## 🚨 トラブルシューティング（Phase 13対応）

### **ProductionEnsemble読み込みエラー**
```bash
❌ 症状: pickle読み込み失敗・sklearn警告
❌ 原因: ファイル不存在・権限問題・sklearn deprecation warning

✅ 対処: 統合管理CLIで確認・再作成（sklearn警告解消版）
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
❌ 症状: メタデータ読み込み失敗・レガシーファイル混在
❌ 原因: JSON形式エラー・ファイル重複・Phase不一致

✅ 対処: MLモデル再作成で自動修復・不要ファイル削除
python scripts/ml/create_ml_models.py --verbose
# model_metadata.jsonは削除候補（production_model_metadata.jsonに統合済み）
```

## 🔧 ファイル管理ルール（Phase 13確立）

### **production/ディレクトリルール**
1. **必須ファイル**:
   - `production_ensemble.pkl`: メインの本番用統合モデル
   - `production_model_metadata.json`: 本番用メタデータ（最新）
   - `README.md`: 本番環境用ドキュメント

2. **削除候補ファイル**:
   - `model_metadata.json`: Phase 9レガシー・パス不整合・重複機能

3. **命名規則**:
   - 本番用ファイルは`production_`プレフィックス
   - メタデータは必ず`.json`拡張子
   - Phase情報を含むファイル名推奨

### **training/ディレクトリルール**
1. **個別モデルファイル**:
   - `{model_name}_model.pkl`形式
   - サイズ上限: 10MB（large fileは別途管理）
   - F1スコア0.5以上のモデルのみ保存

2. **メタデータ管理**:
   - `training_metadata.json`: 学習実行結果統合
   - 実行時刻・性能指標・設定情報を必ず記録
   - Phase情報・sklearn警告状況を記録

3. **保存期間**:
   - 最新1世代のみ保存（容量削減）
   - 古いモデルは必要に応じてアーカイブ

### **バージョン管理ルール**
1. **Gitトラッキング**:
   - `.pkl`ファイル: Git LFS対象（大容量）
   - `.json`ファイル: 通常のGit管理
   - `README.md`: 必ずGit管理

2. **Phase更新ルール**:
   - 新Phase移行時は全メタデータのphase情報更新
   - 古いPhase情報は削除または明記
   - 互換性確保のためバージョン情報記録

## 🚀 Phase 14以降拡張計画

### **機械学習高度化（Phase 14）**
- **AutoML統合**: ハイパーパラメータ自動調整・特徴量自動選択・Optuna統合
- **Model Drift Detection**: リアルタイム性能劣化検知・自動再学習・監視アラート統合
- **Advanced Ensemble**: Neural Network・CatBoost追加・動的重み調整・Deep Learning統合
- **Online Learning**: incremental update・リアルタイム市場適応・ストリーミング学習

### **MLOps・運用強化（Phase 15）**
- **MLflow統合**: Model Registry・実験管理・バージョン管理・ライフサイクル自動化
- **A/B Testing**: 複数ProductionEnsemble並行運用・カナリアリリース・性能比較
- **GPU対応**: 高速学習・大規模データ処理・CUDA最適化・分散学習
- **監視ダッシュボード**: Web UI・リアルタイムメトリクス・Grafana統合

### **スケーラビリティ・セキュリティ強化（Phase 16）**
- **セキュリティMLOps**: モデル暗号化・Differential Privacy・Federated Learning
- **エッジデプロイ**: モバイル・IoT対応・軽量化・TensorFlow Lite統合
- **マルチクラウド**: AWS・Azure対応・災害復旧・可用性向上
- **コンプライアンス**: GDPR・金融規制対応・監査ログ・説明可能AI

---

## 📊 Phase 13完成 次世代MLモデル管理システム実績

### **sklearn警告解消・設定最適化・CI/D本番稼働MLモデル管理**
```
🤖 ProductionEnsemble: 重み付け統合・sklearn警告解消・306テスト100%成功
📊 品質保証完成: CI/CD本番稼働・coverage-reports/58.88%・品質チェック自動化
🔧 統合管理: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク
⚙️ 設定最適化: config/gcp/・config/deployment/統合・不要ファイル削除
✅ sklearn警告解消: 全deprecation warning解消・最新ライブラリ対応
🚀 CI/CD本番稼働: GitHub Actions本番稼働・段階的デプロイ・品質保証
```

**🎯 Phase 13完了**: sklearn警告解消・設定最適化・306テスト100%成功・CI/CD本番稼働対応の次世代MLモデル管理システムが完成。個人開発最適化と企業級品質を兼ね備えた包括的MLモデル・設定・品質保証システムを実現！

**次のマイルストーン**: Phase 14機械学習高度化・AutoML統合・Model Drift Detection・Advanced Ensemble・Online Learning実装