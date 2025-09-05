# scripts/management/ - Phase 19統合管理・開発支援・監視システム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤完成・654テスト100%・59.24%カバレッジ達成に対応した統合管理CLI・開発支援・24時間運用監視システム（2025年9月4日現在）

## 🎯 役割・責任

**Phase 19 MLOps基盤**における統合管理・開発支援・運用監視の核心システムを担当。feature_manager.py統一管理・ProductionEnsemble・週次自動再学習・654テスト品質保証・Cloud Run 24時間監視を統合した開発から本番運用まで一貫したサポートシステムを提供します。

**主要機能**:
- **統合開発管理**: 654テスト・59.24%カバレッジ・MLOps診断・feature_manager検証
- **24時間運用監視**: Cloud Run監視・Discord統合・週次学習監視・自動復旧
- **品質ゲート**: CI/CD統合・段階的デプロイ・品質保証・自動レポート生成
- **MLOps統合**: ProductionEnsemble・週次学習・バージョン管理・性能評価

## 📂 ファイル構成

```
management/
├── dev_check.py           # Phase 19統合開発管理CLI（多機能・MLOps対応）
├── ops_monitor.py         # 24時間運用監視・ヘルスチェック・Discord統合
├── status_config.json     # システム状態設定・Phase 19対応
└── README.md              # このファイル
```

## 🔧 主要機能・実装（Phase 19対応）

### **dev_check.py - 統合開発管理CLI（核心機能）**

**Phase 19 MLOps統合機能**:
- **654テスト統合**: 全テスト実行・59.24%カバレッジ・品質ゲート統合
- **MLOps診断**: feature_manager.py・ProductionEnsemble・週次学習検証
- **統合品質チェック**: flake8・black・isort・pytest・CI/CD統合
- **自動レポート生成**: マークダウン・logs/reports/ci_checks/dev_check/自動保存

**主要コマンド（Phase 19対応）**:
```bash
# 統合品質チェック（推奨・開発時必須）
python3 scripts/management/dev_check.py full-check     # 654テスト・MLOps・全診断

# 個別機能チェック
python3 scripts/management/dev_check.py validate       # 品質チェック・テスト実行
python3 scripts/management/dev_check.py ml-models      # ProductionEnsemble作成・検証
python3 scripts/management/dev_check.py phase-check    # Phase 19実装状況確認
python3 scripts/management/dev_check.py data-check     # データ取得・feature_manager確認

# システム状態・監視
python3 scripts/management/dev_check.py status         # システム状態・654テスト状況
python3 scripts/management/dev_check.py health-check   # GCP・Cloud Run・本番環境確認
```

### **ops_monitor.py - 24時間運用監視（本番運用）**

**Phase 19運用監視機能**:
- **Cloud Run監視**: 24時間稼働・ヘルスチェック・パフォーマンス・自動復旧
- **Discord統合**: CRITICAL・ERROR・WARNING・AUDITレベル通知・緊急アラート
- **週次学習監視**: GitHub Actions・自動再学習・品質評価・デプロイ監視
- **MLOps統合監視**: feature_manager・ProductionEnsemble・予測性能・異常検知

**主要コマンド（Phase 19対応）**:
```bash
# 24時間本番監視（継続実行推奨）
python3 scripts/management/ops_monitor.py              # 総合運用監視・Discord通知

# 個別監視機能
python3 scripts/management/ops_monitor.py --health     # ヘルスチェック・システム状態
python3 scripts/management/ops_monitor.py --mlops      # MLOps監視・週次学習状況
python3 scripts/management/ops_monitor.py --alerts     # アラート確認・Discord通知状況
```

### **status_config.json - システム状態設定（Phase 19対応）**

**設定内容**:
- Phase 19 MLOps基盤・feature_manager・ProductionEnsemble設定
- 654テスト・59.24%カバレッジ・品質ゲート閾値設定
- Cloud Run・Discord・GitHub Actions統合設定
- 監視・アラート・自動復旧・通知設定

## 📝 使用方法・例（Phase 19推奨ワークフロー）

### **日常開発ワークフロー（開発時必須）**

```bash
# 1. Phase 19統合品質チェック（開発前後必須）
python3 scripts/management/dev_check.py full-check

# 期待結果: ✅ 654テスト100%成功・59.24%カバレッジ・MLOps正常

# 2. MLOps・モデル管理
python3 scripts/management/dev_check.py ml-models      # ProductionEnsemble作成・検証

# 期待結果: ✅ feature_manager 12特徴量・3モデル統合・予測検証正常

# 3. 実装状況確認
python3 scripts/management/dev_check.py phase-check    # Phase 19実装状況

# 期待結果: ✅ Phase 19機能・週次学習・統合システム完成確認
```

### **本番運用監視（24時間継続）**

```bash
# Cloud Run・Discord統合監視（本番環境）
python3 scripts/management/ops_monitor.py

# バックグラウンド実行（推奨）
nohup python3 scripts/management/ops_monitor.py > logs/ops_monitor.log 2>&1 &

# 期待結果: 📊 24時間監視・Discord通知・自動復旧・週次学習監視
```

### **トラブルシューティング・診断**

```python
# Python統合診断実行
import subprocess
import json

def run_integrated_diagnosis():
    """Phase 19統合診断実行"""
    
    # 654テスト・品質チェック
    result = subprocess.run([
        "python3", "scripts/management/dev_check.py", "full-check"
    ], capture_output=True, text=True)
    
    print("=== Phase 19統合診断結果 ===")
    print(f"品質チェック: {'✅ 成功' if result.returncode == 0 else '❌ 失敗'}")
    
    # MLOps統合確認
    result = subprocess.run([
        "python3", "scripts/management/dev_check.py", "ml-models", "--dry-run"
    ], capture_output=True, text=True)
    
    print(f"MLOps統合: {'✅ 正常' if result.returncode == 0 else '❌ 異常'}")
    
    # システム状態確認
    result = subprocess.run([
        "python3", "scripts/management/dev_check.py", "status"
    ], capture_output=True, text=True)
    
    print(f"システム状態: {'✅ 正常' if result.returncode == 0 else '❌ 異常'}")

# 診断実行
run_integrated_diagnosis()
```

## ⚠️ 注意事項・制約（Phase 19運用）

### **Phase 19統合制約**

1. **MLOps整合性**: feature_manager.py・ProductionEnsemble・週次学習との統合必須
2. **654テスト品質**: 全機能実行前後でテスト成功・カバレッジ維持必須
3. **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイとの連携必須
4. **24時間監視**: Cloud Run・Discord通知・自動復旧機能への依存

### **実行環境・権限要件**

1. **Python環境**: Python 3.13・依存関係完全・プロジェクトルートから実行
2. **GCP認証**: Workload Identity・Cloud Run・Secret Manager設定済み
3. **GitHub統合**: Actions権限・OIDC・統合テスト実行権限
4. **Discord統合**: Webhook URL・通知権限・アラート設定

### **レポート・ログ管理**

1. **自動生成**: dev_check.py実行時・logs/reports/ci_checks/dev_check/自動保存
2. **保存期間**: 30日間・定期クリーンアップ・重要レポート手動保護
3. **形式統一**: マークダウン・JSON・構造化・AI連携最適化
4. **履歴管理**: タイムスタンプ・バージョン・トレンド分析対応

## 🔗 関連ファイル・依存関係（Phase 19統合）

### **Phase 19 MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量・管理スクリプト統合
- **`src/ml/ensemble.py`**: ProductionEnsemble・モデル管理・学習統合・診断対応
- **`scripts/analytics/base_analyzer.py`**: 共通基盤クラス・Cloud Run統合・継承利用
- **`.github/workflows/`**: 週次自動再学習・CI/CD・品質ゲート・管理統合

### **品質保証・テストシステム**
- **`scripts/testing/checks.sh`**: 654テスト・カバレッジ・品質チェック実行
- **`tests/unit/`**: 654テスト・品質保証・管理スクリプト動作検証
- **`logs/reports/ci_checks/`**: 自動レポート・履歴管理・分析データ

### **監視・アラートシステム**
- **`src/monitoring/discord_notifier.py`**: Discord通知・アラート・運用監視統合
- **`logs/system/`**: システムログ・エラー分析・パフォーマンス監視
- **`config/core/`**: 設定管理・閾値・パラメータ・管理システム統合

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤・654テスト100%・59.24%カバレッジ統合による統合開発管理・24時間運用監視・品質保証・CI/CD統合システムを実現