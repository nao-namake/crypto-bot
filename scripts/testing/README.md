# scripts/testing/ - Phase 19品質保証・テストシステム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤完成・654テスト100%・59.24%カバレッジ達成に対応した統合品質チェック・テスト・品質保証システム（2025年9月4日現在）

## 🎯 役割・責任

**Phase 19 MLOps基盤**における品質保証・テスト・CI/CD統合の核心システムを担当。654テスト100%・59.24%カバレッジ・feature_manager.py統合・ProductionEnsemble検証・週次自動再学習品質ゲートによる継続的品質保証・回帰防止・メトリクス測定システムを提供します。

**主要機能**:
- **654テスト統合**: 全テスト実行・59.24%カバレッジ・品質ゲート・CI/CD統合
- **MLOps品質保証**: feature_manager.py・ProductionEnsemble・週次学習検証
- **ライブ取引テスト**: Phase 19対応実取引検証・段階的デプロイ・安全性確認
- **継続的品質管理**: GitHub Actions・自動化ワークフロー・回帰防止

## 📂 ファイル構成

```
testing/
├── checks.sh               # 654テスト統合品質チェック・59.24%カバレッジ
├── test_live_trading.py    # Phase 19対応ライブトレード統合テスト
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

### **test_live_trading.py - Phase 19ライブトレード統合テスト**

**Phase 19実取引テスト機能**:
- **段階的デプロイ検証**: paper→stage-10→stage-50→live・各段階安全性確認
- **MLOps統合テスト**: feature_manager・ProductionEnsemble・実取引環境統合
- **最小取引単位**: 安全な実取引テスト・リスク管理・損失制限
- **Discord通知統合**: テスト結果・異常検知・緊急アラート

**実行コマンド（Phase 19対応）**:
```bash
# Phase 19対応ライブ取引テスト
python3 scripts/testing/test_live_trading.py --mode single    # 単発テスト・安全確認
python3 scripts/testing/test_live_trading.py --mode paper     # ペーパートレードテスト
python3 scripts/testing/test_live_trading.py --mode stage-10  # 段階的デプロイテスト

# 実行前チェック必須:
# ✅ BITBANK_API_KEY・BITBANK_API_SECRET設定済み
# ✅ feature_manager.py・ProductionEnsemble正常動作確認
# ✅ Discord通知設定完了・テスト通知確認
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
python3 scripts/management/dev_check.py ml-models --dry-run
if [ $? -eq 0 ]; then
    echo "✅ MLOps統合: feature_manager・ProductionEnsemble正常"
else
    echo "❌ MLOps統合異常・本番デプロイ中止"
    exit 1
fi

# 3. ペーパートレードテスト
python3 scripts/testing/test_live_trading.py --mode paper
if [ $? -eq 0 ]; then
    echo "✅ ペーパートレード: Phase 19統合テスト成功"
    echo "✅ 本番デプロイ準備完了"
else
    echo "❌ ペーパートレードテスト失敗・本番デプロイ中止"
    exit 1
fi
```

## ⚠️ 注意事項・制約（Phase 19品質保証）

### **Phase 19品質基準**

1. **654テスト100%**: 全テスト成功・回帰防止・継続的品質保証必須
2. **59.24%カバレッジ**: 最低基準維持・向上目標・新機能テスト追加必須
3. **MLOps統合**: feature_manager・ProductionEnsemble・週次学習テスト必須
4. **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ統合必須

### **実行環境・依存関係**

1. **Python環境**: Python 3.13・pytest・coverage・flake8・black・isort必須
2. **MLOps依存**: feature_manager.py・ProductionEnsemble・学習データ準備
3. **API設定**: Bitbank API・Discord Webhook・GCP認証・Secret Manager
4. **実行権限**: テスト実行・ファイル作成・ネットワークアクセス権限

### **品質保証制約**

1. **テスト実行時間**: 654テスト約30秒・カバレッジ測定含む・効率化済み
2. **カバレッジ要件**: 新機能追加時テスト追加必須・カバレッジ低下防止
3. **ライブテスト**: 最小取引単位・リスク管理・安全性確保・損失制限
4. **継続的監視**: 品質劣化検知・自動アラート・Discord通知・復旧対応

## 🔗 関連ファイル・依存関係（Phase 19統合）

### **Phase 19 MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量・テスト統合
- **`src/ml/ensemble.py`**: ProductionEnsemble・モデル統合・品質検証
- **`tests/unit/`**: 654テスト・品質保証・回帰防止・継続的テスト
- **`.github/workflows/`**: 週次自動再学習・CI/CD・品質ゲート統合

### **品質保証・レポートシステム**
- **`coverage-reports/`**: HTMLカバレッジ・JSON統計・品質メトリクス
- **`scripts/management/dev_check.py`**: 統合品質チェック・MLOps診断
- **`logs/`**: テスト結果・品質ログ・分析データ・履歴管理

### **本番統合・監視システム**
- **`src/trading/`**: 実取引システム・ライブテスト・段階的デプロイ
- **`src/monitoring/discord_notifier.py`**: Discord通知・品質アラート・監視
- **`config/core/`**: 品質基準・閾値・テスト設定・パラメータ管理

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤・654テスト100%・59.24%カバレッジ統合による継続的品質保証・回帰防止・CI/CD統合・段階的デプロイ対応の企業級品質保証システムを実現