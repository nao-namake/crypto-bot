# scripts/deployment/ - Phase 19インフラ・デプロイメント・統合管理システム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤完成・654テスト100%・59.24%カバレッジ達成に対応したGCP Cloud Run・Docker統合・段階的デプロイ・品質ゲート統合システム（2025年9月4日現在）

## 📂 ファイル構成

```
deployment/
├── deploy_production.sh         # Phase 19対応段階的デプロイ・品質ゲート・Cloud Run統合
├── docker-entrypoint.sh         # MLOps統合エントリポイント・feature_manager・ProductionEnsemble対応
├── setup_ci_prerequisites.sh    # CI/CD・654テスト・GitHub Actions・週次学習環境構築
├── setup_gcp_secrets.sh         # GCP Secret Manager・MLOps認証・統合管理
├── verify_gcp_setup.sh          # Phase 19環境検証・MLOps基盤・品質保証確認
└── README.md                    # このファイル
```

## 🎯 役割・責任

**Phase 19 MLOps基盤**におけるインフラ・デプロイメント・統合管理の核心システムを担当。feature_manager.py統一管理・ProductionEnsemble・週次自動再学習・654テスト品質保証を統合した企業級段階的デプロイ・品質ゲート・24時間運用監視システムを提供します。

**主要機能**:
- **段階的MLOpsデプロイ**: paper→stage-10→stage-50→live・品質ゲート・自動ロールバック
- **654テスト品質ゲート**: 全デプロイ前後でテスト成功・59.24%カバレッジ確認必須
- **週次学習統合**: GitHub Actions自動再学習・モデル更新・デプロイ連携
- **Cloud Run統合**: 24時間稼働・自動スケーリング・Discord監視・ヘルスチェック

## 🔧 主要機能・実装（Phase 19統合）

### **deploy_production.sh - 段階的MLOpsデプロイ（核心機能）**

**Phase 19段階的デプロイ統合**:
- **654テスト品質ゲート**: デプロイ前後でchecks.sh実行・100%成功・59.24%カバレッジ確認
- **段階的リリース**: paper→stage-10→stage-50→live・各段階品質確認・自動プロモーション
- **MLOps統合**: feature_manager.py・ProductionEnsemble・週次学習モデル統合デプロイ
- **Cloud Run統合**: サービス更新・環境変数・ヘルスチェック・Discord監視・自動復旧

### **docker-entrypoint.sh - MLOps統合エントリポイント（Phase 19対応）**

**統合システム起動機能**:
- **feature_manager統合**: 12特徴量生成・DataFrame出力・起動時検証・統合確認
- **ProductionEnsemble**: 3モデル統合・予測テスト・起動時学習済み確認・フォールバック対応
- **システム統合**: main.py統合システム・環境変数・プロセス監視・グレースフルシャットダウン
- **654テスト統合**: 起動時テスト実行・品質確認・エラーハンドリング・Discord通知

### **verify_gcp_setup.sh - Phase 19環境検証**

**MLOps基盤検証機能**:
- **包括的環境検証**: GCP・GitHub Actions・週次学習・CI/CD失敗防止・自動診断
- **MLOps環境確認**: Secret Manager・Workload Identity・モデル格納・学習環境
- **654テスト環境**: pytest・coverage・品質ゲート・テスト実行環境確認
- **Discord統合確認**: Webhook・通知・アラート・監視システム接続確認

### **setup_ci_prerequisites.sh - CI/CD・MLOps環境構築**

**週次自動再学習環境構築**:
- **GitHub Actions環境**: 週次学習・OIDC・Workload Identity・自動デプロイ
- **GCP環境構築**: Cloud Run・Artifact Registry・Secret Manager・学習環境
- **654テスト環境**: pytest・coverage・品質ゲート・CI/CD統合
- **対話式設定**: 自動修復・設定確認・問題診断・レポート生成

### **setup_gcp_secrets.sh - MLOps認証・シークレット管理**

**統合認証管理**:
- **MLOps認証**: モデル格納・学習データアクセス・予測API・統合管理
- **取引認証**: Bitbank API・Discord Webhook・リアルタイム通知・セキュア管理
- **CI/CD認証**: GitHub Actions・自動デプロイ・週次学習・権限管理
- **セキュリティ強化**: 暗号化・アクセス制御・監査ログ・最小権限原則

## 📝 使用方法・例（Phase 19推奨ワークフロー）

### **Phase 19統合デプロイフロー（本番運用必須）**

```bash
# 1. Phase 19品質チェック（デプロイ前必須）
bash scripts/testing/checks.sh

# 期待結果: ✅ 654テスト100%成功・59.24%カバレッジ・feature_manager検証正常

# 2. MLOps環境検証（Phase 19対応）
bash scripts/deployment/verify_gcp_setup.sh --full --mlops

# 期待結果: ✅ GCP・週次学習・ProductionEnsemble・Discord通知確認

# 3. 段階的MLOpsデプロイ（推奨・安全性最優先）
bash scripts/deployment/deploy_production.sh --staged --mlops

# 実行内容:
# - paper環境: feature_manager・ProductionEnsemble動作確認
# - stage-10: 10%トラフィック・654テスト確認・監視強化
# - stage-50: 50%トラフィック・性能確認・週次学習テスト
# - live: 100%本番・24時間監視・Discord通知有効

# 期待結果: ✅ 段階的プロモーション成功・品質ゲート通過・監視確立
```

### **週次自動再学習デプロイ（GitHub Actions統合）**

```bash
# GitHub Actions環境確認・週次学習準備
bash scripts/deployment/verify_gcp_setup.sh --weekly-training

# 週次学習デプロイメント（自動実行・手動確認用）
bash scripts/deployment/deploy_production.sh --weekly-model-update

# 期待結果:
# ✅ 新ProductionEnsemble配置・feature_manager更新・654テスト成功
# ✅ 段階的デプロイ・性能確認・自動プロモーション・監視統合
```

### **初回Phase 19環境構築**

```bash
# 1. Phase 19包括的環境検証
bash scripts/deployment/verify_gcp_setup.sh --full --phase19

# 期待結果: 環境診断・問題検出・修復提案・設定確認

# 2. MLOps統合環境セットアップ
bash scripts/deployment/setup_ci_prerequisites.sh --interactive --mlops

# 設定内容:
# - GCP・Cloud Run・Artifact Registry・Secret Manager
# - GitHub Actions・週次学習・OIDC・Workload Identity
# - 654テスト・pytest・coverage・品質ゲート

# 3. 統合認証・シークレット設定
bash scripts/deployment/setup_gcp_secrets.sh --interactive --phase19

# 設定内容:
# - Bitbank API・Discord Webhook・MLOps認証
# - モデル格納・学習データ・予測API認証
# - CI/CD・自動デプロイ・セキュリティ設定

# 4. Phase 19統合検証・確認
bash scripts/deployment/verify_gcp_setup.sh --ci --mlops --final-check

# 期待結果: ✅ 全環境確認・654テスト実行・MLOps動作確認・デプロイ準備完了
```

### **トラブルシューティング・診断（Phase 19対応）**

```python
# Phase 19統合診断スクリプト
import subprocess

def run_phase19_diagnosis():
    """Phase 19統合診断実行"""
    
    print("=== Phase 19統合診断開始 ===")
    
    # 654テスト品質確認
    result = subprocess.run(["bash", "scripts/testing/checks.sh"], capture_output=True)
    print(f"654テスト: {'✅ 成功' if result.returncode == 0 else '❌ 失敗'}")
    
    # MLOps環境確認
    result = subprocess.run([
        "bash", "scripts/deployment/verify_gcp_setup.sh", "--full", "--mlops"
    ], capture_output=True)
    print(f"MLOps環境: {'✅ 正常' if result.returncode == 0 else '❌ 異常'}")
    
    # Cloud Run稼働確認
    result = subprocess.run([
        "gcloud", "run", "services", "describe", "crypto-bot-service-prod", 
        "--region=asia-northeast1"
    ], capture_output=True)
    print(f"Cloud Run: {'✅ 稼働中' if result.returncode == 0 else '❌ 停止'}")

# 診断実行
run_phase19_diagnosis()
```

## ⚠️ 注意事項・制約（Phase 19運用制約）

### **Phase 19統合制約**

1. **MLOps整合性**: feature_manager.py・ProductionEnsemble・週次学習システムとの統合必須
2. **654テスト品質ゲート**: 全デプロイ前後でテスト成功・59.24%カバレッジ確認必須
3. **段階的デプロイ遵守**: paper→stage-10→stage-50→live順次実行・各段階品質確認必須
4. **24時間監視統合**: Cloud Run・Discord通知・自動復旧システムへの依存

### **実行環境・権限要件**

1. **Python環境**: Python 3.13・MLOps依存関係・feature_manager・ProductionEnsemble
2. **GCP統合**: Workload Identity・Cloud Run・Artifact Registry・Secret Manager設定
3. **GitHub統合**: Actions権限・OIDC・週次学習ワークフロー・自動デプロイ設定
4. **Docker環境**: コンテナ化・MLOps統合・依存関係・セキュリティ設定

### **デプロイ品質制約**

1. **品質ゲート通過**: 654テスト100%成功・カバレッジ59.24%以上・コード品質確認
2. **MLOps統合確認**: feature_manager 12特徴量・ProductionEnsemble 3モデル・予測精度
3. **環境検証必須**: verify_gcp_setup.sh --mlops --phase19合格確認
4. **監視確立**: Discord通知・ヘルスチェック・エラー検知・自動復旧確認

### **ロールバック・復旧体制**

1. **即座復旧**: 前回リビジョン保持・1分以内復旧・自動ヘルスチェック
2. **段階的復旧**: live→stage-50→stage-10→paper段階的切り戻し
3. **MLOps復旧**: 前回学習済みモデル・feature_manager設定・統合状態復旧
4. **監視強化**: 復旧後24時間集中監視・Discord通知・性能確認

## 🔗 関連ファイル・依存関係（Phase 19統合）

### **Phase 19 MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量・デプロイ統合・起動時検証
- **`src/ml/ensemble.py`**: ProductionEnsemble・モデル管理・学習統合・デプロイ連携
- **`.github/workflows/`**: 週次自動再学習・CI/CD・品質ゲート・自動デプロイ統合
- **`scripts/management/dev_check.py`**: 統合開発管理・MLOps診断・デプロイ前確認

### **品質保証・テストシステム**
- **`scripts/testing/checks.sh`**: 654テスト・59.24%カバレッジ・品質ゲート・デプロイ前必須
- **`tests/unit/`**: 654テスト・品質保証・デプロイメントスクリプト動作検証
- **`logs/reports/ci_checks/`**: デプロイ品質レポート・履歴管理・分析データ

### **設定・環境・統合**
- **`config/core/`**: Phase 19設定・MLOps・デプロイ設定・環境変数統合管理
- **`Dockerfile`**: MLOps統合コンテナ・feature_manager・ProductionEnsemble対応
- **`docker-compose.yml`**: 開発環境・テスト環境・段階的デプロイテスト対応

### **外部依存・クラウド統合**
- **GCP Cloud Run**: Phase 19本番実行環境・MLOps稼働・24時間自動スケーリング
- **GCP Artifact Registry**: MLOps統合Dockerイメージ・セキュリティ・バージョン管理
- **GCP Secret Manager**: 統合認証・MLOps・取引API・Discord・セキュア管理
- **GitHub Actions**: 週次自動再学習・CI/CD・品質ゲート・自動デプロイ統合

### **監視・アラートシステム**
- **`src/monitoring/discord_notifier.py`**: Discord通知・デプロイ監視・アラート統合
- **Cloud Run監視**: ヘルスチェック・パフォーマンス・エラー検知・自動復旧
- **`scripts/analytics/`**: デプロイ後パフォーマンス分析・MLOps監視・統合ダッシュボード

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤・654テスト100%・59.24%カバレッジ統合による企業級段階的デプロイ・品質ゲート・24時間運用監視・自動復旧システムを実現