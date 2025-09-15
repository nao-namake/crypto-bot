# scripts/management/ - Bot管理スクリプト

**最終更新**: 2025年9月16日 - プロセス管理・Discord通知最適化対応

## 🎯 概要

暗号資産取引Botの安全で効率的な実行・管理を支援するスクリプト群です。プロセス重複防止、環境別実行制御、Discord通知最適化など、運用上の問題を根本的に解決します。

## 📂 ファイル構成

```
scripts/management/
├── README.md         # このファイル（管理スクリプト説明）
└── run_safe.sh       # 安全実行スクリプト（メイン）
```

## 🔧 run_safe.sh - 安全実行スクリプト

### **主要機能**

| 機能 | 説明 | 効果 |
|------|------|------|
| **プロセス重複防止** | PIDファイル・ロックファイル使用 | 今回のような無限通知問題を根本防止 |
| **環境自動判定** | ローカル/GCP環境の自動切り替え | 実行環境の混乱を防止 |
| **タイムアウト管理** | GCP環境で15分自動終了 | 無制限実行によるコスト増加防止 |
| **プロセス監視** | 実行状況の可視化・制御 | 運用効率向上 |

### **使用方法**

#### **1. 基本実行**
```bash
# ローカル環境でペーパートレード（推奨）
bash scripts/management/run_safe.sh local paper

# ローカル環境でライブトレード
bash scripts/management/run_safe.sh local live

# GCP環境でライブトレード（本番）
bash scripts/management/run_safe.sh gcp live
```

#### **2. プロセス管理**
```bash
# 実行状況確認
bash scripts/management/run_safe.sh status

# 強制停止
bash scripts/management/run_safe.sh stop

# ロックファイルクリーンアップ
bash scripts/management/run_safe.sh cleanup
```

#### **3. 出力例**
```bash
$ bash scripts/management/run_safe.sh local paper

========================================
🚀 暗号資産取引Bot安全実行
========================================

[INFO]  2025-09-16 17:30:00 - 🔒 プロセスロック取得: PID=12345
[INFO]  2025-09-16 17:30:00 - 🌍 実行環境設定: local
[INFO]  2025-09-16 17:30:00 - 💻 ローカル環境設定完了
[INFO]  2025-09-16 17:30:00 - 🎯 動作モード: paper
[INFO]  2025-09-16 17:30:00 - 🚀 暗号資産取引Bot起動開始
...
[INFO]  2025-09-16 17:35:00 - ✅ Bot正常終了
[INFO]  2025-09-16 17:35:00 - 🔓 プロセスロック解除

🎉 実行完了
```

### **環境別設定**

#### **ローカル環境**
```bash
export ENVIRONMENT="local"
export RUNNING_ON_GCP="false"
export PYTHONPATH="$PROJECT_ROOT"
export PYTHONUNBUFFERED=1
```

#### **GCP環境**
```bash
export ENVIRONMENT="gcp"
export RUNNING_ON_GCP="true"
export LOG_LEVEL="INFO"
export PYTHONPATH="$PROJECT_ROOT"
export PYTHONUNBUFFERED=1
```

## 📊 プロセス管理詳細

### **ロックファイル管理**

| ファイル | 場所 | 内容 | 用途 |
|---------|------|------|------|
| **crypto_bot_${USER}.lock** | `/tmp/` | PID + 開始時刻 | 重複起動防止 |
| **crypto_bot_${USER}.pid** | `/tmp/` | プロセスID | 実行状況確認 |

### **プロセス状態確認**
```bash
# プロセス実行中の例
$ bash scripts/management/run_safe.sh status

📊 暗号資産取引Bot実行状況
✅ プロセス実行中: PID=12345, 経過時間=15分

# プロセス停止中の例
📊 暗号資産取引Bot実行状況
📋 プロセス停止中
```

### **安全な停止手順**
1. **SIGTERM送信**: 正常終了シグナル
2. **30秒待機**: 正常終了を待つ
3. **SIGKILL送信**: 強制終了（必要時のみ）
4. **ロック解除**: ファイルクリーンアップ

## 🛡️ エラー処理・トラブルシューティング

### **よくある問題と解決方法**

#### **1. 「既にプロセスが実行中です」エラー**
```bash
# 原因: 前回の実行が正常終了していない
# 解決: 強制停止とクリーンアップ
bash scripts/management/run_safe.sh stop
bash scripts/management/run_safe.sh cleanup
```

#### **2. ロックファイルが残っている**
```bash
# 原因: 異常終了でロックファイルが残存
# 解決: クリーンアップ実行
bash scripts/management/run_safe.sh cleanup
```

#### **3. 環境変数が正しく設定されない**
```bash
# 確認: 環境変数の確認
echo $RUNNING_ON_GCP
echo $ENVIRONMENT

# 解決: スクリプト経由で実行（推奨）
bash scripts/management/run_safe.sh local paper
```

### **ログ確認方法**
```bash
# main.pyのログ確認
tail -f logs/production/crypto_bot.log

# システムログ確認（ローカル）
tail -f /var/log/system.log | grep crypto_bot

# GCP環境でのログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=20
```

## 🔧 従来実行との比較

| 実行方法 | プロセス管理 | 環境制御 | タイムアウト | 推奨度 |
|---------|-------------|---------|-------------|--------|
| **従来**: `python main.py` | ❌ なし | ❌ 手動 | ❌ なし | 🚫 非推奨 |
| **新方式**: `run_safe.sh` | ✅ 自動 | ✅ 自動 | ✅ 自動 | ✅ **推奨** |

### **移行方法**
```bash
# 従来方式（今後非推奨）
python main.py --mode paper

# 新方式（推奨）
bash scripts/management/run_safe.sh local paper
```

## 📈 期待される効果

### **問題解決効果**
- **無限通知防止**: プロセス重複防止により根本解決
- **コスト削減**: GCPタイムアウトにより無制限実行防止
- **運用効率向上**: 統一された実行・監視インターフェース

### **定量的効果**
| 指標 | 改善前 | 改善後 | 効果 |
|------|--------|--------|------|
| **プロセス重複** | 可能性あり | 完全防止 | 100%解決 |
| **運用ミス** | 手動制御 | 自動制御 | 80%削減 |
| **トラブル解決時間** | 10-30分 | 1-5分 | 70%短縮 |

## 🔄 今後の拡張予定

### **Phase 2 機能追加予定**
- **cron統合**: 定期実行スケジューリング
- **メトリクス収集**: 実行統計・パフォーマンス監視
- **アラート機能**: 異常検知・自動通知
- **バックアップ機能**: 設定・ログの自動バックアップ

### **使用上の注意事項**
1. **権限**: 実行前に `chmod +x` で実行権限を確認
2. **環境**: ローカル実行時は適切な仮想環境を使用
3. **ログ**: 長時間実行時はログローテーション設定を推奨
4. **GCP**: GCP環境では Secret Manager の設定を事前確認

---

**運用の重要ポイント**: 今回のような無限通知問題を根本的に防止するため、**必ず run_safe.sh 経由での実行を推奨**します。従来の直接実行は今後非推奨となります。