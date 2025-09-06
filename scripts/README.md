# scripts/ - Phase 19統合運用スクリプト・ツール管理システム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤完成・654テスト100%・59.24%カバレッジ達成に対応した運用・開発・分析・デプロイメント統合自動化ツール集（2025年9月4日現在）

## 📂 ディレクトリ構成

```
scripts/
├── analytics/          # 統合分析・データ収集・ダッシュボード [詳細: README.md]
│   ├── base_analyzer.py             # 共通基盤クラス・Cloud Run統合・Phase 19対応
│   ├── data_collector.py            # 実データ収集・MLOps統計分析・654テスト統合
│   ├── performance_analyzer.py      # システムパフォーマンス・feature_manager統合分析
│   └── dashboard.py                 # HTMLダッシュボード・Phase 19可視化・週次学習監視
├── ml/                 # 機械学習・モデル管理 [詳細: README.md]
│   └── create_ml_models.py          # MLOps統合・ProductionEnsemble・週次学習対応
├── deployment/         # デプロイメント・インフラ [詳細: README.md]
│   ├── deploy_production.sh         # GCP Cloud Run・段階的デプロイ・品質ゲート統合
│   ├── docker-entrypoint.sh         # Docker・MLOps・feature_manager統合エントリポイント
│   ├── setup_ci_prerequisites.sh    # CI/CD・654テスト・GitHub Actions統合
│   ├── setup_gcp_secrets.sh         # GCP Secret Manager・MLOps認証統合
│   └── verify_gcp_setup.sh          # GCP環境・Cloud Run・週次学習環境検証
└── testing/            # テスト・品質保証・統合開発管理 [詳細: README.md]
    ├── checks.sh                    # 654テスト統合品質チェック・59.24%カバレッジ
    └── dev_check.py                 # Phase 19統合開発管理CLI（多機能・MLOps対応）
```

## 🎯 役割・責任

**Phase 19 MLOps基盤**におけるシステム開発・運用・監視・デプロイメントの全工程を支援する統合ツール集を提供。feature_manager.py統一管理・ProductionEnsemble・週次自動再学習・654テスト品質保証による一貫した自動化・効率化・品質保証システムを担当します。

**主要機能**:
- **MLOps統合管理**: feature_manager.py・ProductionEnsemble・週次自動再学習統合対応
- **654テスト品質保証**: 統合品質チェック・59.24%カバレッジ・CI/CD品質ゲート
- **24時間運用監視**: Cloud Run監視・Discord通知・自動復旧・ヘルスチェック
- **段階的デプロイ**: paper→stage-10→stage-50→live・品質ゲート・自動ロールバック
- **統合分析**: データ収集・パフォーマンス分析・ダッシュボード・可視化

## 🔧 主要機能・実装（Phase 19統合）

### **testing/ - 品質保証・統合開発管理（核心機能）**

**Phase 19統合対応**:
- **`checks.sh`**: 654テスト実行・59.24%カバレッジ測定・品質ゲート・CI/CD統合
- **`dev_check.py`**: 統合開発管理・MLOps診断・システム状態確認・包括的品質チェック
- Phase 19 MLOps基盤・ProductionEnsemble・統合品質保証・継続的品質向上

### **ml/ - MLOps・モデル管理（Phase 19核心）**

**週次自動再学習統合**:
- **`create_ml_models.py`**: ProductionEnsemble・feature_manager統合・自動学習
- LightGBM・XGBoost・RandomForest・3モデル統合・重み最適化
- GitHub Actions・週次学習・バージョン管理・品質評価

### **deployment/ - インフラ・デプロイ（Phase 19対応）**

**段階的デプロイ統合**:
- **`deploy_production.sh`**: 段階的デプロイ・品質ゲート・Cloud Run統合
- **Docker統合**: feature_manager・ProductionEnsemble・MLOpsコンテナ化
- GCP・Secret Manager・CI/CD・自動化・監視・復旧統合

### **analytics/ - 分析・監視（Phase 19統合）**

**統合分析基盤**:
- **`base_analyzer.py`**: Phase 19共通基盤・Cloud Run・Discord統合
- **分析統合**: パフォーマンス・データ収集・ダッシュボード・可視化
- MLOps監視・feature_manager統計・週次学習効果分析

## 📝 使用方法・例（Phase 19対応）

### **日常開発・運用（推奨ワークフロー）**

```bash
# Phase 19統合品質チェック（開発時必須）
bash scripts/testing/checks.sh                         # 654テスト・30秒完了

# MLOps統合開発管理（多機能CLI）
python3 scripts/testing/dev_check.py full-check     # 統合診断・MLOps確認
python3 scripts/testing/dev_check.py ml-models      # ProductionEnsemble作成

# 24時間運用監視
python3 scripts/management/ops_monitor.py              # Cloud Run・Discord監視

# MLOps・週次学習
python3 scripts/ml/create_ml_models.py --verbose       # モデル作成・詳細ログ
```

### **デプロイメント・インフラ（本番運用）**

```bash
# GCP環境構築・検証
bash scripts/deployment/setup_ci_prerequisites.sh      # CI/CD環境構築
bash scripts/deployment/verify_gcp_setup.sh           # 環境検証・健全性確認

# 段階的本番デプロイ
bash scripts/deployment/deploy_production.sh          # paper→stage→live
```

### **分析・監視・ダッシュボード**

```python
# Phase 19統合分析実行
from scripts.analytics.performance_analyzer import PerformanceAnalyzer
from scripts.analytics.data_collector import DataCollector

# MLOps統合データ収集・分析
collector = DataCollector()
analyzer = PerformanceAnalyzer()

# feature_manager・ProductionEnsemble統合分析
collector.collect_mlops_data()                         # MLOps統計収集
analyzer.analyze_system_performance()                  # 総合性能分析
```

## ⚠️ 注意事項・制約（Phase 19運用）

### **Phase 19運用制約**

1. **MLOps統合**: feature_manager.py・ProductionEnsemble・週次学習との整合性必須
2. **654テスト品質**: 全スクリプト実行前後でテスト成功・カバレッジ維持必須
3. **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ遵守
4. **24時間監視**: Cloud Run・Discord通知・自動復旧機能依存

### **実行環境要件**

1. **Python環境**: Python 3.13・依存関係・仮想環境推奨
2. **GCP統合**: 認証・権限・Cloud Run・Secret Manager設定必須
3. **GitHub統合**: Actions・Workflows・OIDC・Workload Identity設定
4. **Discord統合**: Webhook・通知設定・アラート機能設定

### **セキュリティ・権限**

1. **認証管理**: GCP・GitHub・Discord・APIキー・Secret Manager統合
2. **権限制御**: 最小権限・実行権限・アクセス制御・監査ログ
3. **機密情報**: 環境変数・設定ファイル・ログマスキング・暗号化

## 🔗 関連ファイル・依存関係（Phase 19統合）

### **Phase 19 MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量・スクリプト統合
- **`src/ml/ensemble.py`**: ProductionEnsemble・モデル管理・学習統合
- **`.github/workflows/`**: 週次自動再学習・CI/CD・品質ゲート統合
- **`config/core/`**: 設定管理・閾値・パラメータ・スクリプト設定

### **品質保証・監視システム**
- **`tests/unit/`**: 654テスト・品質保証・スクリプト動作検証
- **`logs/`**: システムログ・レポート・分析結果・監視データ
- **`src/monitoring/discord_notifier.py`**: Discord通知・アラート・統合

### **インフラ・デプロイ統合**
- **`Dockerfile`**: コンテナ化・エントリポイント・MLOps統合
- **GCP Cloud Run**: 本番環境・24時間稼働・自動スケーリング
- **Secret Manager**: 認証・API キー・セキュリティ統合

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤・654テスト100%・59.24%カバレッジ統合による開発から本番運用まで一貫した品質保証・自動化・監視・デプロイメントの統合ツールシステムを実現