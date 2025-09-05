# scripts/ml/ - Phase 19 MLOps機械学習・週次自動再学習・モデル管理システム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤完成・654テスト100%・59.24%カバレッジ達成に対応したProductionEnsemble・週次自動再学習・feature_manager.py統合・GitHub Actions連携MLOpsシステム（2025年9月4日現在）

## 📂 ファイル構成

```
ml/
├── create_ml_models.py    # Phase 19 MLOps・ProductionEnsemble・feature_manager統合・GitHub Actions連携
└── README.md              # このファイル
```

## 🎯 役割・責任

**Phase 19 MLOps基盤**における機械学習・週次自動再学習・モデル管理の核心システムを担当。feature_manager.py 12特徴量統一管理・ProductionEnsemble 3モデル統合・GitHub Actions週次自動再学習・654テスト品質保証を統合した企業級MLOpsシステムを提供します。

**主要機能**:
- **週次自動再学習**: GitHub Actions統合・ProductionEnsemble更新・品質ゲート・自動デプロイ
- **MLOps統合**: feature_manager.py 12特徴量・3モデル統合（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- **654テスト品質保証**: モデル検証・予測テスト・CI/CD統合・59.24%カバレッジ確認
- **バージョン管理**: メタデータ管理・モデル版数管理・性能追跡・自動ロールバック

## 🔧 主要機能・実装（Phase 19 MLOps統合）

### **create_ml_models.py - 週次自動再学習システム（核心機能）**

**Phase 19 MLOps統合機能**:
- **feature_manager.py統合**: 12特徴量統一管理・DataFrame出力・マルチタイムフレーム対応
- **ProductionEnsemble構築**: 3モデル統合・LightGBM 40%・XGBoost 40%・RandomForest 20%・重み最適化
- **654テスト統合**: モデル検証・予測テスト・品質ゲート・自動テスト実行
- **週次自動再学習**: GitHub Actions統合・毎週日学習・自動デプロイ・性能評価

**技術統合詳細**:
- **ハイパーパラメータ最適化**: TimeSeriesSplit・GridSearchCV・Bayesian最適化・金融時系列特化
- **sklearn警告解消**: Phase 19対応・互換性確認・Deprecation対応・パフォーマンス最適化
- **メタデータ管理**: models/production/・models/training/・JSON統合・バージョン管理・性能追跡
- **CI/CD統合**: GitHub Actions・Workflow・Secret Manager・Cloud Run自動デプロイ・Discord通知

## 📝 使用方法・例（Phase 19 MLOpsワークフロー）

### **週次自動再学習実行（GitHub Actions統合）**

```bash
# Phase 19 MLOps統合実行（推奨・本畫連携）
python3 scripts/ml/create_ml_models.py --mlops --phase19

# 期待結果:
# ✅ feature_manager 12特徴量統合・データパイプライン統合
# ✅ ProductionEnsemble 3モデル統合・LightGBM 40%・XGBoost 40%・RandomForest 20%
# ✅ 654テスト実行・品質ゲート通過・59.24%カバレッジ確認
# ✅ メタデータ管理・バージョン管理・models/production/保存

# 統合管理CLI経由（日常運用推奨）
python3 scripts/management/dev_check.py ml-models --verbose

# 期待結果:
# ✅ 学習環境検証・feature_manager統合・ProductionEnsemble作成
# ✅ 自動テスト実行・CI/CD統合・品質確認・Discord通知
```

### **個別機能テスト（開発・デバッグ用）**

```bash
# ドライラン（シミュレーション・事前確認）
python3 scripts/ml/create_ml_models.py --dry-run --verbose

# feature_manager統合テスト（特徴量生成確認）
python3 scripts/ml/create_ml_models.py --test-features --days 30

# ProductionEnsemble個別テスト（モデル統合確認）
python3 scripts/ml/create_ml_models.py --test-ensemble --verbose

# 学習期間指定（カスタム学習）
python3 scripts/ml/create_ml_models.py --days 180 --custom-training

# GitHub Actionsシミュレーション（CI/CDテスト）
python3 scripts/ml/create_ml_models.py --simulate-github-actions
```

### **週次自動再学習結果例（Phase 19成功パターン）**

```python
# GitHub Actions週次学習結果例
training_result = {
    "timestamp": "2025-09-04T12:00:00Z",
    "phase": "Phase 19",
    "feature_manager": {
        "features_count": 12,
        "data_quality": "excellent",
        "missing_data": 0.0,
        "generation_time_ms": 245
    },
    "models": {
        "lightgbm": {"f1_score": 0.87, "accuracy": 0.89, "weight": 0.40},
        "xgboost": {"f1_score": 0.85, "accuracy": 0.88, "weight": 0.40}, 
        "randomforest": {"f1_score": 0.81, "accuracy": 0.84, "weight": 0.20}
    },
    "production_ensemble": {
        "combined_f1": 0.89,
        "combined_accuracy": 0.91,
        "model_path": "models/production/production_ensemble_20250904.pkl",
        "metadata_path": "models/production/ensemble_metadata_20250904.json"
    },
    "quality_gates": {
        "tests_passed": "654/654",
        "coverage": "59.24%",
        "deployment_ready": True,
        "performance_improvement": "+2.1%"
    }
}

print(f"✅ Phase 19週次学習成功: {training_result['production_ensemble']['combined_f1']}")
print(f"✅ 品質ゲート通過: {training_result['quality_gates']['tests_passed']}")
print(f"✅ 性能向上: {training_result['quality_gates']['performance_improvement']}")
```

## ⚠️ 注意事項・制約（Phase 19 MLOps制約）

### **Phase 19 MLOps統合制約**

1. **feature_manager.py統合**: 12特徴量統一管理・データパイプライン統合必須
2. **654テスト品質**: 全モデル学習前後でテスト成功・59.24%カバレッジ確認必須
3. **週次自動再学習**: GitHub Actions・CI/CD統合・自動デプロイシステム統合
4. **ProductionEnsemble統合**: 3モデル統合・重み最適化・バージョン管理必須

### **実行環境・機能要件**

1. **Python環境**: Python 3.13・MLOps依存関係完全・プロジェクトルートから実行必須
2. **ライブラリ**: scikit-learn・lightgbm・xgboost・pandas・numpy・Phase 19互換バージョン
3. **リソース**: 最低2GB RAM・MLOps統合・週次学習用計算リソース確保
4. **実行時間**: 10-30分（feature_manager統合・654テスト・3モデル統合含む）

### **MLOpsデータ要件**

- **特徴量feature_manager**: 12特徴量完全セット・DataFrame形式・欠損値ゼロ必須
- **最低データ量**: 2000サンプル以上（MLOps品質保証用）・時系列データ順序正しい
- **データ品質**: feature_manager事前処理済み・異常値検知・金融時系列特化
- **ラベル品質**: buy/sell/holdバランス確認・クラス不均衡対応・検証用データ分離

### **出力・バージョン管理（Phase 19統合）**

1. **models/production/**: ProductionEnsemble・feature_manager統合メタデータ・バージョン管理
2. **models/training/**: 3モデル個別保存・学習ログ・ハイパーパラメータ・性能指標
3. **logs/ml_training/**: 週次学習ログ・GitHub Actionsログ・CI/CD統合ログ
4. **バックアップ**: 前回モデル保持・ロールバック用・性能比較・安全性確保

### **CI/CD・GitHub Actions統合制約**

1. **週次学習スケジュール**: 毎週日 UTC 00:00実行・自動デプロイ・品質ゲート
2. **Secret Manager統合**: 認証情報・APIキー・セキュア管理・Workload Identity
3. **Discord通知**: 学翕結果・エラー通知・性能メトリクス・アラート統合
4. **品質管理**: 学習後654テスト必須・カバレッジ維持・性能改善確認

## 🔗 関連ファイル・依存関係（Phase 19 MLOps統合）

### **Phase 19 MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量・DataFrame出力・ML学習統合
- **`src/ml/ensemble.py`**: ProductionEnsemble・3モデル統合・重み最適化・予測エンジン
- **`.github/workflows/weekly_retrain.yml`**: 週次自動再学習・CI/CD統合・自動デプロイ・Discord通知
- **`scripts/management/dev_check.py`**: MLOps統合管理・ml-modelsコマンド・学習環境検証

### **品質保証・テストシステム**
- **`scripts/testing/checks.sh`**: 654テスト実行・59.24%カバレッジ・MLモデル品質ゲート
- **`tests/unit/ml/`**: MLモデルテスト・アンサンブルテスト・feature_manager統合テスト
- **`tests/unit/features/`**: 特徴量テスト・12特徴量検証・データ品質テスト

### **データ・設定・モデル管理**
- **`models/production/`**: ProductionEnsemble保存・メタデータJSON・Phase 19バージョン管理
- **`models/training/`**: 個別モデル・学習ログ・TimeSeriesSplit・ハイパーパラメータ管理
- **`config/core/`**: ML設定・feature_manager設定・アンサンブルパラメータ・週次学習設定
- **`data/processed/`**: 前処理済みデータ・feature_manager出力・学習用データセット

### **インフラ・監視・通知統合**
- **GCP Cloud Run**: MLOpsモデルサービング・自動スケーリング・24時間稼働環境
- **GCP Secret Manager**: MLモデル認証・APIキー・GitHub Actions統合認証
- **`src/monitoring/discord_notifier.py`**: 学習結果通知・モデル性能アラート・エラー通知
- **`logs/ml_training/`**: 週次学習ログ・CI/CDログ・性能メトリクス履歴

### **外部依存・ライブラリ・Phase 19統合**
- **scikit-learn 1.3+**: 機械学習アルゴリズム・TimeSeriesSplit・評価指標・Phase 19互換
- **LightGBM 4.0+・XGBoost 2.0+**: 勾配ブースティング・高性能学習・GPU対応
- **pandas 2.0+・numpy 1.24+**: データ処理・feature_manager統合・数値計算最適化
- **GitHub Actions**: CI/CD・週次学習システム・Workload Identity・自動デプロイ統合

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤・654テスト100%・59.24%カバレッジ統合によるProductionEnsemble・企業級機械学習システム・GitHub Actions週次自動再学習・24時間MLOps運用環境を実現