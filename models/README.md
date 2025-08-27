# models/ - 機械学習モデル管理ディレクトリ

**Phase 13対応**: ProductionEnsemble統合モデル・個別学習モデル・メタデータ管理システム完成（2025年8月26日現在）

## 📂 ディレクトリ構成

```
models/
├── production/                      # 本番環境用モデル [詳細: README.md]
│   ├── production_ensemble.pkl     # ProductionEnsemble統合モデル（実取引用）
│   └── production_model_metadata.json  # 本番用メタデータ・性能指標
├── training/                        # 学習・検証用モデル [詳細: README.md]
│   ├── lightgbm_model.pkl          # LightGBM個別モデル（高性能）
│   ├── xgboost_model.pkl           # XGBoost個別モデル（最高精度）
│   ├── random_forest_model.pkl     # RandomForest個別モデル（安定性）
│   └── training_metadata.json      # 学習メタデータ・性能記録
└── README.md                        # このファイル
```

## 🎯 役割・責任

機械学習モデルの学習・保存・本番運用を統合管理するディレクトリです。個別モデルの学習からProductionEnsemble構築まで、一貫した品質保証された機械学習パイプラインを提供します。

**主要機能**:
- ProductionEnsemble統合モデルの本番運用管理
- 個別モデル（LightGBM・XGBoost・RandomForest）の学習・保存
- モデル性能指標・メタデータの体系的管理

**システム構成**:
- **production/**: 実取引で使用するProductionEnsembleモデル
- **training/**: 学習用個別モデル・性能評価・基盤提供

## 🔧 主要機能・実装

### **production/ - 本番環境用モデル**

実取引で使用する本番用モデルを管理。詳細は `models/production/README.md` 参照。

**主要ファイル**:
- **`production_ensemble.pkl`**: ProductionEnsemble統合モデル（約7MB）
- **`production_model_metadata.json`**: 本番用メタデータ・性能指標・重み設定

**特徴**:
- 3モデル統合（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- 12特徴量対応・実取引最適化済み
- 高精度予測・アンサンブル学習効果

### **training/ - 学習・検証用モデル**

個別モデルの学習・性能評価を管理。詳細は `models/training/README.md` 参照。

**主要ファイル**:
- **`lightgbm_model.pkl`**: LightGBM個別モデル（F1: 0.958）
- **`xgboost_model.pkl`**: XGBoost個別モデル（F1: 0.995）  
- **`random_forest_model.pkl`**: RandomForest個別モデル（F1: 0.755）
- **`training_metadata.json`**: 学習メタデータ・性能記録・設定情報

**特徴**:
- TimeSeriesSplit交差検証・高品質学習
- 個別性能評価・ProductionEnsemble構築基盤
- 学習サンプル4320件・12特徴量対応

## 📝 使用方法・例

### **モデル作成・更新**
```bash
# 統合管理CLI（推奨）
python scripts/management/dev_check.py ml-models

# 直接スクリプト実行
python scripts/ml/create_ml_models.py --verbose

# 学習期間指定
python scripts/ml/create_ml_models.py --days 360
```

### **ProductionEnsembleの使用**
```python
import pickle
import numpy as np

# 本番モデル読み込み
with open('models/production/production_ensemble.pkl', 'rb') as f:
    model = pickle.load(f)

# 予測実行（12特徴量必須）
features = np.random.random((1, 12))
prediction = model.predict(features)
probabilities = model.predict_proba(features)

# モデル情報確認
info = model.get_model_info()
print(f"モデル数: {len(info['individual_models'])}")
print(f"重み設定: {info['weights']}")
```

## ⚠️ 注意事項・制約

### **モデル使用時の制約**
1. **特徴量数**: 全モデル12特徴量固定（feature_names順序遵守）
2. **データ型**: numpy配列形式（shape: (n_samples, 12)）
3. **メモリ使用量**: ProductionEnsemble読み込み時約50-100MB使用

### **ファイル管理上の制約**
1. **ファイルサイズ**: 各.pklファイルは数MB～7MB程度
2. **Git LFS**: 全.pklファイルはGit LFS管理対象
3. **同期更新**: モデル更新時はメタデータも同時更新必須

### **運用時の注意点**
1. **学習データ**: 最低4000サンプル以上推奨
2. **性能基準**: F1スコア0.5以上を品質基準として設定
3. **バージョン管理**: Phase情報・作成日時の記録必須

## 🔗 関連ファイル・依存関係

### **システム統合**
- **`src/ml/`**: 機械学習モジュール・ProductionEnsemble実装
- **`src/features/`**: 特徴量生成システム・12特徴量定義
- **`scripts/ml/create_ml_models.py`**: モデル学習・作成・更新スクリプト

### **設定・管理**
- **`config/core/base.yaml`**: 基本設定・学習パラメータ
- **`config/core/feature_order.json`**: 特徴量順序定義
- **`logs/reports/`**: モデル性能・学習結果レポート

### **外部依存**
- **scikit-learn**: 機械学習ライブラリ基盤
- **LightGBM・XGBoost**: 勾配ブースティングライブラリ
- **pandas・numpy**: データ処理・数値計算
- **pickle**: モデルシリアライゼーション

---

**🎯 Phase 13対応完了**: ProductionEnsemble統合モデル・個別学習モデル・メタデータ管理システムを確立。学習から本番運用まで一貫した品質保証された機械学習パイプラインを実現。