# 48時間ペーパートレード デプロイ準備完了

## 🚀 デプロイ実行手順

### 1. デプロイ開始
```bash
git add .
git commit -m "Start 48h paper trading deployment to dev environment"
git push origin develop
```

### 2. 監視開始
デプロイ完了後（約5-10分後）に以下のコマンドで監視開始：

```bash
# 連続監視（5分間隔、Ctrl+Cで停止）
./scripts/monitor_48h_deployment.sh

# ワンタイム確認
./scripts/monitor_48h_deployment.sh --once

# レポート生成のみ
./scripts/monitor_48h_deployment.sh --report
```

### 3. エラー時の対応
エラーが発生した場合：

```bash
# 包括的診断実行
./scripts/troubleshoot_deployment.sh

# 個別診断
./scripts/troubleshoot_deployment.sh --github     # GitHub Actions確認
./scripts/troubleshoot_deployment.sh --cloudrun   # Cloud Run確認
./scripts/troubleshoot_deployment.sh --logs       # ログ確認
```

## 📋 設定確認済み

### ✅ Dev環境設定
- **プロジェクト**: my-crypto-bot-project
- **サービス名**: crypto-bot-dev
- **モード**: paper (ペーパートレード)
- **リージョン**: asia-northeast1

### ✅ 監視・トラブルシューティング
- **48時間監視スクリプト**: `scripts/monitor_48h_deployment.sh`
- **エラー診断スクリプト**: `scripts/troubleshoot_deployment.sh`
- **自動ログ解析**: GitHub Actions・Cloud Run・Terraform対応

### ✅ GitHub Actions設定
- **バージョン更新済み**: auth@v1.8.3, setup-gcloud@v1.14.0
- **環境分岐実装済み**: develop→dev, main→prod, tags→HA-prod

## 🔧 エラー対応フロー

1. **ユーザー**: 「エラーが出ました」と報告
2. **Claude**: `./scripts/troubleshoot_deployment.sh` でログ自動取得・解析
3. **Claude**: 原因特定 → 修正コード提供
4. **ユーザー**: 修正を `git push` するだけ

## 📊 48時間後の検証ポイント

- ✅ **稼働率**: 48時間連続稼働確認
- ✅ **エラー率**: エラーログ件数・種類分析
- ✅ **パフォーマンス**: レスポンス時間・メモリ使用量
- ✅ **トレーディング**: ペーパートレード実行履歴確認

---

## 🎯 デプロイ準備完了！

上記の `git push origin develop` コマンドを実行してください。
GitHub Actionsが自動でdev環境へのデプロイを開始します。