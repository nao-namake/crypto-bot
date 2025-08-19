# scripts/system_tools/ - システム管理ツール

## 📋 概要

GCP Cloud Run、インフラ、システムヘルスチェックなど、システム全体の管理・診断ツールを集約したディレクトリです。

## 🎯 ツール一覧

### **system_health_check.py** ⭐ 重要
システム全体の健全性チェック

```bash
python scripts/system_tools/system_health_check.py
```

**チェック項目:**
- API接続状態
- モデルファイル存在確認
- 設定ファイル検証
- 依存関係チェック
- メモリ・ディスク使用状況

### **quick_health_check.sh**
クイックヘルスチェック（簡易版）

```bash
bash scripts/system_tools/quick_health_check.sh
```

**実行内容:**
- 基本的な動作確認
- API疎通確認
- 設定ファイル存在確認

### **diagnose_cloud_run_apis.py**
Cloud Run APIの診断

```bash
python scripts/system_tools/diagnose_cloud_run_apis.py
```

**診断内容:**
- Cloud Run サービス状態
- リビジョン情報
- トラフィック配分
- エラーログ分析
- メトリクス確認

### **gcp_revision_manager.py**
GCPリビジョン管理

```bash
# リビジョン一覧表示
python scripts/system_tools/gcp_revision_manager.py list

# 古いリビジョン削除
python scripts/system_tools/gcp_revision_manager.py cleanup --keep 3

# トラフィック切り替え
python scripts/system_tools/gcp_revision_manager.py switch --revision latest
```

**機能:**
- リビジョン管理
- トラフィック制御
- 自動クリーンアップ
- ロールバック支援

### **cleanup_cloud_run_revisions.sh**
Cloud Runリビジョンのクリーンアップ

```bash
bash scripts/system_tools/cleanup_cloud_run_revisions.sh
```

**実行内容:**
- 古いリビジョン削除
- リビジョン競合解決
- ディスク容量確保

## 💡 使用シーン

### **日常監視**

```bash
# 毎朝の確認
bash scripts/system_tools/quick_health_check.sh

# 週次の詳細チェック
python scripts/system_tools/system_health_check.py
```

### **トラブルシューティング**

```bash
# 1. Cloud Run の状態確認
python scripts/system_tools/diagnose_cloud_run_apis.py

# 2. リビジョン問題の解決
python scripts/system_tools/gcp_revision_manager.py list
bash scripts/system_tools/cleanup_cloud_run_revisions.sh

# 3. システム全体診断
python scripts/system_tools/system_health_check.py
```

### **デプロイ後の確認**

```bash
# 1. ヘルスチェック
bash scripts/system_tools/quick_health_check.sh

# 2. Cloud Run 診断
python scripts/system_tools/diagnose_cloud_run_apis.py

# 3. トラフィック確認
python scripts/system_tools/gcp_revision_manager.py list
```

## 📊 監視項目

### **システムメトリクス**
- CPU使用率: < 80%
- メモリ使用率: < 90%
- ディスク使用率: < 85%
- レスポンスタイム: < 3秒

### **Cloud Run状態**
- サービス: READY
- リビジョン: 最新3つを保持
- トラフィック: 100% latest
- インスタンス: 自動スケーリング

### **API接続**
- Bitbank API: 接続可能
- GCP APIs: 認証済み
- レート制限: 余裕あり

## ⚠️ 注意事項

- **リビジョン削除** は慎重に（ロールバック不可）
- **トラフィック切り替え** は段階的に実施
- **本番環境** では必ずバックアップを確認
- **診断ツール** の実行はAPI制限に注意

## 🔍 トラブルシューティング

### **Cloud Run エラー**
```bash
# 診断実行
python scripts/system_tools/diagnose_cloud_run_apis.py

# リビジョン競合解決
bash scripts/system_tools/cleanup_cloud_run_revisions.sh
```

### **システムが重い**
```bash
# システム診断
python scripts/system_tools/system_health_check.py

# メモリ・CPU確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
```

### **API接続エラー**
```bash
# クイックチェック
bash scripts/system_tools/quick_health_check.sh

# 詳細診断
python scripts/system_tools/diagnose_cloud_run_apis.py
```

---

*最終更新: 2025年8月11日 - フォルダ整理実施*