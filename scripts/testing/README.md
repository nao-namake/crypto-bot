# scripts/testing/ - Phase 19品質保証・テストシステム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤完成・654テスト100%・59.24%カバレッジ達成に対応した統合品質チェック・テスト・品質保証システム（2025年9月4日現在）

## 🎯 役割・責任

**Phase 19 MLOps基盤**における品質保証・テスト・CI/CD統合の核心システムを担当。654テスト100%・59.24%カバレッジ・feature_manager.py統合・ProductionEnsemble検証・週次自動再学習品質ゲートによる継続的品質保証・回帰防止・メトリクス測定システムを提供します。

**主要機能**:
- **654テスト統合**: 全テスト実行・59.24%カバレッジ・品質ゲート・CI/CD統合
- **MLOps品質保証**: feature_manager.py・ProductionEnsemble・週次学習検証
- **統合開発管理**: dev_check.py による包括的システム診断・品質チェック
- **継続的品質管理**: GitHub Actions・自動化ワークフロー・回帰防止

## 📂 ファイル構成

```
testing/
├── checks.sh               # 654テスト統合品質チェック・59.24%カバレッジ
├── dev_check.py            # Phase 19統合開発管理CLI（多機能・MLOps対応）
└── README.md               # このファイル
```

## 🔧 主要機能・実装（Phase 19統合）

### **checks.sh - 654テスト統合品質チェック（核心機能）**

**Phase 19品質保証機能**:
- **654テスト実行**: 全モジュール・MLOps統合・feature_manager・ProductionEnsemble
- **59.24%カバレッジ**: 継続測定・品質維持・向上目標・HTML・JSON・Term出力
- **コードスタイル統合**: flake8・black・isort・PEP8準拠・自動整形チェック
- **CI/CD統合**: GitHub Actions・品質ゲート・自動実行・段階的デプロイ対応

**実行コマンド（Phase 19推奨）**:
```bash
# 統合品質チェック実行（開発時必須・約30秒完了）
bash scripts/testing/checks.sh

# 期待結果:
# ✅ 654テスト100%成功
# ✅ 59.24%カバレッジ達成
# ✅ flake8・black・isort通過
# ✅ MLOps・feature_manager統合確認
```

**詳細機能（Phase 19対応）**:
- **ディレクトリ構造確認**: Phase 19システム構造・MLOps基盤・統合確認
- **pytest実行**: 654テスト・TimeSeriesSplit・金融時系列・MLOps統合テスト
- **カバレッジ測定**: HTML・JSON・Term出力・coverage-reports/統合管理
- **品質ゲート**: 50%以上カバレッジ・654テスト成功・コードスタイル準拠

### **dev_check.py - 統合開発管理CLI（核心機能）**

**Phase 19 MLOps統合機能**:
- **654テスト統合**: 全テスト実行・59.24%カバレッジ・品質ゲート統合
- **MLOps診断**: feature_manager.py・ProductionEnsemble・週次学習検証
- **統合品質チェック**: flake8・black・isort・pytest・CI/CD統合
- **自動レポート生成**: マークダウン・logs/reports/ci_checks/dev_check/自動保存

**主要コマンド（Phase 19対応）**:
```bash
# 統合品質チェック（推奨・開発時必須）
python3 scripts/testing/dev_check.py full-check     # 654テスト・MLOps・全診断

# 個別機能チェック
python3 scripts/testing/dev_check.py validate       # 品質チェック・テスト実行
python3 scripts/testing/dev_check.py ml-models      # ProductionEnsemble作成・検証
python3 scripts/testing/dev_check.py phase-check    # Phase 19実装状況確認
python3 scripts/testing/dev_check.py data-check     # データ取得・feature_manager確認

# システム状態・監視
python3 scripts/testing/dev_check.py status         # システム状態・654テスト状況
python3 scripts/testing/dev_check.py health-check   # GCP・Cloud Run・本番環境確認

# CI後運用監視（手動実行推奨）
# docs/指示書/CI後チェック作業_Claude実行版.mdを開き9セクション順次実行
```

### **CI後チェック作業指示書 - 本番運用監視（推奨）**

**Phase 19運用監視機能**:
- **9セクション網羅チェック**: 時系列・基盤・データ・ML・取引・監視・問題検出・パフォーマンス・連鎖エラー
- **実際のCICD結果確認**: 直接Cloud Runログ取得で高精度検証
- **12特徴量特化監視**: feature_manager統合システムに完全対応
- **ProductionEnsemble特化**: MLモデル稼働状況・fitted状態・予測実行確認

**使用方法（Phase 19対応）**:
```bash
# docs/指示書/CI後チェック作業_Claude実行版.mdを開いて順次実行

# チェック前準備（必須）
LATEST_REVISION=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.traffic[0].revisionName)")
DEPLOY_TIME=$(gcloud run revisions describe $LATEST_REVISION --region=asia-northeast1 --format="value(metadata.creationTimestamp)")

# セクション1-9を順次実行で全面監視
```


## 📝 使用方法・例（Phase 19推奨ワークフロー）

### **日常開発品質チェック（必須ワークフロー）**

```bash
# 1. Phase 19統合品質チェック（開発前後必須）
bash scripts/testing/checks.sh

# 実行内容:
# - ディレクトリ構造確認（Phase 19対応）
# - flake8コードスタイルチェック・PEP8準拠確認
# - isortインポート整理チェック・順序確認
# - blackコード整形チェック・フォーマット確認
# - 654テスト実行・MLOps統合・全モジュール検証
# - 59.24%カバレッジ測定・HTML/JSON/Term出力

# 2. 結果確認・カバレッジ詳細表示
open coverage-reports/htmlcov/index.html              # HTMLカバレッジレポート
cat coverage-reports/htmlcov/status.json | jq '.'     # JSON統計データ

# 3. 品質メトリクス確認
echo "品質チェック完了時刻: $(date)"
echo "654テスト結果: 全テスト成功"  
echo "カバレッジ: 59.24%達成"
```

### **日常開発ワークフロー（開発時必須）**

```bash
# 1. Phase 19統合品質チェック（開発前後必須）
python3 scripts/testing/dev_check.py full-check

# 期待結果: ✅ 654テスト100%成功・59.24%カバレッジ・MLOps正常

# 2. MLOps・モデル管理
python3 scripts/testing/dev_check.py ml-models      # ProductionEnsemble作成・検証

# 期待結果: ✅ feature_manager 12特徴量・3モデル統合・予測検証正常

# 3. 実装状況確認
python3 scripts/testing/dev_check.py phase-check    # Phase 19実装状況

# 期待結果: ✅ Phase 19機能・週次学習・統合システム完成確認
```

### **CI後チェック作業（手動実行推奨）**

```bash
# 1. CI後チェック作業指示書を開く
code docs/指示書/CI後チェック作業_Claude実行版.md

# 2. 9セクション順次実行（全面チェック）
# - セクション1: 時系列・デプロイ状況確認
# - セクション3: 12特徴量生成確認（最重要）
# - セクション4: ProductionEnsemble稼働確認
# - セクション5: BUY/SELLシグナル生成確認

# 3. エラー発見時はToDo.md記録で後まとめ修正

# 期待結果: 📊 Phase 19 MLOps統合システム完全監視・高精度チェック
```

### **MLOps・モデル統合テスト**

```python
# Phase 19 MLOps統合テスト実行
import subprocess
import sys

def run_mlops_quality_check():
    """MLOps統合品質チェック"""
    
    print("=== Phase 19 MLOps品質チェック ===")
    
    # 654テスト・MLOps統合確認
    result = subprocess.run([
        "bash", "scripts/testing/checks.sh"
    ], capture_output=True, text=True)
    
    success = result.returncode == 0
    print(f"654テスト統合: {'✅ 成功' if success else '❌ 失敗'}")
    
    if success:
        print("✅ feature_manager.py: 12特徴量テスト成功")
        print("✅ ProductionEnsemble: 3モデル統合テスト成功") 
        print("✅ 週次学習システム: 品質ゲートテスト成功")
        print("✅ 59.24%カバレッジ: 品質基準達成")
    else:
        print("❌ テスト失敗・品質チェック要確認")
        print(result.stdout)
        print(result.stderr)
    
    return success

# MLOps品質チェック実行
mlops_success = run_mlops_quality_check()
```

### **本番前最終検証（段階的デプロイ前）**

```bash
# Phase 19本番前統合検証
echo "=== Phase 19本番前統合検証 ==="

# 1. 品質チェック・654テスト
bash scripts/testing/checks.sh
if [ $? -eq 0 ]; then
    echo "✅ 品質チェック: 654テスト・59.24%カバレッジ成功"
else
    echo "❌ 品質チェック失敗・本番デプロイ中止"
    exit 1
fi

# 2. MLOps統合確認
python3 scripts/testing/dev_check.py ml-models --dry-run
if [ $? -eq 0 ]; then
    echo "✅ MLOps統合: feature_manager・ProductionEnsemble正常"
else
    echo "❌ MLOps統合異常・本番デプロイ中止"
    exit 1
fi

# 3. 本番環境ヘルスチェック
python3 scripts/testing/dev_check.py health-check
if [ $? -eq 0 ]; then
    echo "✅ 本番環境: Phase 19システムヘルスチェック成功"
    echo "✅ 本番デプロイ準備完了"
else
    echo "❌ 本番環境ヘルスチェック失敗・本番デプロイ中止"
    exit 1
fi
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
        "python3", "scripts/testing/dev_check.py", "full-check"
    ], capture_output=True, text=True)
    
    print("=== Phase 19統合診断結果 ===")
    print(f"品質チェック: {'✅ 成功' if result.returncode == 0 else '❌ 失敗'}")
    
    # MLOps統合確認
    result = subprocess.run([
        "python3", "scripts/testing/dev_check.py", "ml-models", "--dry-run"
    ], capture_output=True, text=True)
    
    print(f"MLOps統合: {'✅ 正常' if result.returncode == 0 else '❌ 異常'}")
    
    # システム状態確認
    result = subprocess.run([
        "python3", "scripts/testing/dev_check.py", "status"
    ], capture_output=True, text=True)
    
    print(f"システム状態: {'✅ 正常' if result.returncode == 0 else '❌ 異常'}")

# 診断実行
run_integrated_diagnosis()
```

## ⚠️ 注意事項・制約（Phase 19品質保証）

### **Phase 19品質基準**

1. **654テスト100%**: 全テスト成功・回帰防止・継続的品質保証必須
2. **59.24%カバレッジ**: 最低基準維持・向上目標・新機能テスト追加必須
3. **MLOps統合**: feature_manager・ProductionEnsemble・週次学習テスト必須
4. **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ統合必須

### **Phase 19統合制約**

1. **MLOps整合性**: feature_manager.py・ProductionEnsemble・週次学習との統合必須
2. **654テスト品質**: 全機能実行前後でテスト成功・カバレッジ維持必須
3. **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイとの連携必須
4. **CI後チェック**: `docs/指示書/CI後チェック作業_Claude実行版.md`手動実行必須

### **実行環境・依存関係**

1. **Python環境**: Python 3.13・pytest・coverage・flake8・black・isort必須
2. **MLOps依存**: feature_manager.py・ProductionEnsemble・学習データ準備
3. **API設定**: Bitbank API・Discord Webhook・GCP認証・Secret Manager
4. **実行権限**: テスト実行・ファイル作成・ネットワークアクセス権限

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

### **品質保証制約**

1. **テスト実行時間**: 654テスト約30秒・カバレッジ測定含む・効率化済み
2. **カバレッジ要件**: 新機能追加時テスト追加必須・カバレッジ低下防止
3. **ライブテスト**: 最小取引単位・リスク管理・安全性確保・損失制限
4. **継続的監視**: 品質劣化検知・自動アラート・Discord通知・復旧対応

## 🔗 関連ファイル・依存関係（Phase 19統合）

### **Phase 19 MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量・管理スクリプト統合
- **`src/ml/ensemble.py`**: ProductionEnsemble・モデル管理・学習統合・診断対応
- **`scripts/analytics/base_analyzer.py`**: 共通基盤クラス・Cloud Run統合・継承利用
- **`tests/unit/`**: 654テスト・品質保証・回帰防止・継続的テスト
- **`.github/workflows/`**: 週次自動再学習・CI/CD・品質ゲート・管理統合

### **品質保証・テストシステム**
- **`scripts/testing/checks.sh`**: 654テスト・カバレッジ・品質チェック実行
- **`scripts/testing/dev_check.py`**: 統合開発管理・MLOps診断・システム管理
- **`coverage-reports/`**: HTMLカバレッジ・JSON統計・品質メトリクス
- **`logs/reports/ci_checks/`**: 自動レポート・履歴管理・分析データ
- **`logs/`**: テスト結果・品質ログ・分析データ・履歴管理

### **監視・アラートシステム**
- **`docs/指示書/CI後チェック作業_Claude実行版.md`**: CI後チェック手順書・9セクション網羅チェック
- **`src/monitoring/discord_notifier.py`**: Discord通知・品質アラート・運用監視統合
- **`logs/system/`**: システムログ・エラー分析・パフォーマンス監視
- **`config/core/`**: 設定管理・閾値・パラメータ・管理システム統合

### **本番統合・監視システム**
- **`src/trading/`**: 実取引システム・ライブテスト・段階的デプロイ

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤・654テスト100%・59.24%カバレッジ統合による統合品質保証・開発管理・CI後チェック作業指示書による高精度運用監視・回帰防止・CI/CD統合・段階的デプロイ対応の企業級品質保証・テスト・開発管理統合システムを実現

**最新更新**: 2025年9月5日 - scripts/management/ README統合完了・dev_check.py統合開発管理CLI・CI後チェック作業統合・企業級品質保証・開発管理・テストシステム統一化完成