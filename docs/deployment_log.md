# Phase 12 デプロイメントログ

CI/CD統合・24時間監視・段階的デプロイ対応の実行記録

## 📋 概要

Phase 12では、レガシーシステムの良い部分を継承・改良し、本格的なCI/CDパイプライン稼働を開始します。

### レガシー活用実績
- **signal_monitor.py** → 24時間監視ワークフロー
- **pre_deploy_validation.py** → CI/CD品質チェック強化
- **deploy_production.sh** → 段階的デプロイ機能
- **error_analyzer.py** → パフォーマンス分析ツール

## 🚀 デプロイメント履歴

### Phase 12.1 - CI/CDパイプライン基盤構築

#### 2025-08-18 基盤構築完了

**実装内容**:
- ✅ GitHub Secrets設定ガイド作成 (`docs/github_secrets_setup.md`)
- ✅ GCP Secret Manager自動設定スクリプト改良 (`scripts/deployment/setup_gcp_secrets.sh`)
- ✅ 24時間監視ワークフロー作成 (`.github/workflows/monitoring.yml`)
- ✅ CI/CD段階的デプロイ対応 (`.github/workflows/ci.yml`)
- ✅ パフォーマンス分析ツール作成 (`scripts/analytics/performance_analyzer.py`)

**レガシー改良箇所**:
```diff
+ レガシーsignal_monitor.py → GitHub Actions 24時間監視
+ レガシーci_tools/ → 段階的品質チェック統合
+ レガシーdeploy_production.sh → Cloud Run段階的デプロイ
+ レガシーerror_analyzer.py → 包括的パフォーマンス分析
```

**技術仕様**:
- **GitHub Actions**: 15分間隔24時間監視
- **段階的デプロイ**: paper → stage-10 → stage-50 → live
- **トラフィック分割**: 10% → 50% → 100%移行
- **品質保証**: 398/399テスト・flake8・コード整形統合

## 📊 段階的デプロイメント戦略

### デプロイステージ定義（コスト最適化版）

| ステージ | モード | リソース | 最小/最大インスタンス | タイムアウト | 用途 |
|---------|--------|----------|---------------------|------------|------|
| Paper | `paper` | 1Gi/1CPU | 0-1 | 30分 | 安全テスト |
| Stage-10 | `stage-10` | 1Gi/1CPU | 1-1 | 30分 | 10%投入 |
| Stage-50 | `stage-50` | 1.5Gi/1CPU | 1-1 | 40分 | 50%投入 |
| Production | `live` | 1Gi/1CPU | 1-2 | 60分 | 100%本番 |

**⚖️ 安定性優先のバランス設定**:
- **CPU統一**: 全ステージ1CPU（個人開発に最適）
- **メモリ効率化**: Productionも1Gi（軽量システム設計活用）
- **取引継続性**: MIN_INSTANCES=1（レガシー知見活用・SIGTERM問題回避）
- **スケール対応**: MAX_INSTANCES=2（負荷時自動拡張）

**🚨 レガシー学習ポイント**:
- **MIN_INSTANCES=0問題**: アイドルタイムアウト・状態リセット・SIGTERM頻発
- **レガシー解決策**: min-instances=1設定で問題完全解決実績
- **コスト実績**: 約1,800円/月（目標2,000円以内達成）

**月間コスト試算** (安定性重視):
- **通常時**: 月約$12-18 (1,800-2,700円)
- **高負荷時**: 月約$20-30 (3,000-4,500円)
- **目標**: 月額2,000円前後・安定性確保

### トラフィック移行戦略

```yaml
段階的移行:
  paper: 100% 新リビジョン（テスト専用）
  stage-10: 10% 新リビジョン + 90% 旧リビジョン
  stage-50: 50% 新リビジョン + 50% 旧リビジョン  
  live: 100% 新リビジョン（完全移行）
```

## 🏥 24時間監視体制

### 監視間隔
- **基本監視**: 15分間隔（GitHub Actions）
- **ヘルスチェック**: リアルタイム（Cloud Run）
- **エラー分析**: 1時間間隔
- **パフォーマンス分析**: 手動実行・日次推奨

### 監視項目

#### システムヘルス
- Cloud Runサービス状態
- API応答時間（目標: < 3秒）
- エラー率（目標: < 1%/時間）
- リソース使用率

#### 取引パフォーマンス
- シグナル生成頻度
- 注文成功率（目標: > 95%）
- 取引実行レイテンシ
- 戦略別成績

#### アラート条件
- **Critical**: サービス停止・API認証失敗
- **Warning**: エラー率 > 5/時間・応答時間 > 3秒
- **Info**: 取引活動・定期レポート

## 🔧 使用方法

### 1. GitHub Secrets設定

```bash
# 設定ガイド参照
cat docs/github_secrets_setup.md

# 必要なSecrets:
# - GCP_WIF_PROVIDER
# - GCP_SERVICE_ACCOUNT  
# - GCP_PROJECT
# - DEPLOY_MODE (paper/stage-10/stage-50/live)
```

### 2. GCP Secret Manager設定

```bash
# 対話式設定
bash scripts/deployment/setup_gcp_secrets.sh --interactive

# 設定確認
bash scripts/deployment/setup_gcp_secrets.sh --check
```

### 3. CI/CDパイプライン実行

```bash
# GitHub Actionsトリガー
git add -A
git commit -m "feat: Phase 12 CI/CD初回稼働"
git push origin main

# ワークフロー確認
gh run list --limit 5
gh run view --log
```

### 4. 段階的デプロイ実行

```bash
# 1. ペーパートレード確認
# GitHub Secrets: DEPLOY_MODE=paper

# 2. 10%段階移行  
# GitHub Secrets: DEPLOY_MODE=stage-10

# 3. 50%段階移行
# GitHub Secrets: DEPLOY_MODE=stage-50

# 4. 100%本番移行
# GitHub Secrets: DEPLOY_MODE=live
```

### 5. パフォーマンス分析

```bash
# 24時間分析
python scripts/analytics/performance_analyzer.py --period 24h --format markdown

# 週次分析
python scripts/analytics/performance_analyzer.py --period 7d --format json
```

## 📈 期待される効果

### CI/CD統合効果
- **デプロイ時間**: 手動30分 → 自動5分
- **品質保証**: 手動チェック → 自動398テスト
- **リスク軽減**: 一括デプロイ → 段階的移行

### 24時間監視効果  
- **障害検知**: 手動発見 → 15分以内自動検知
- **復旧時間**: 平均60分 → 目標15分
- **予防保守**: 事後対応 → 予兆検知

### 運用効率化効果
- **手動作業**: 70%削減
- **監視負荷**: 24時間 → 自動化
- **品質安定性**: 人的ミス削減

## ⚠️ レガシー知見による重要な注意事項

### MIN_INSTANCES=0による既知の問題

**レガシーシステムで確認された重大エラー**:
```yaml
問題: Cloud Runアイドルタイムアウト・SIGTERM頻発
原因: min-instances=0設定
影響: 取引中の状態リセット・継続性阻害
解決: min-instances=1で完全解決（レガシー実績）
```

**Phase 12での対策**:
- ✅ **本番環境**: MIN_INSTANCES=1（取引継続性重視）
- ✅ **テスト環境**: MIN_INSTANCES=0（コスト削減）
- ✅ **段階移行**: Paper→Stage→Liveで安全確認

**レガシーから学んだベストプラクティス**:
1. **取引システムでは継続稼働が必須**
2. **コスト vs 安定性のバランス重要**
3. **min-instances=1で約1,800円/月実績**

## 🚨 トラブルシューティング

### CI/CD失敗時

#### 1. GitHub Actions失敗
```bash
# ログ確認
gh run view --log

# よくある原因:
# - GitHub Secrets未設定
# - GCP認証失敗
# - テスト失敗
```

#### 2. デプロイ失敗
```bash
# Cloud Run確認
gcloud run services list --region=asia-northeast1

# ログ確認
gcloud logging read "resource.type=\"cloud_run_revision\"" --limit=20

# ロールバック
gcloud run services update-traffic SERVICE_NAME --to-revisions=PREVIOUS_REVISION=100
```

### 監視アラート対応

#### Critical Alert
1. **即座に確認**: `gcloud run services describe SERVICE_NAME`
2. **ログ分析**: `gcloud logging read "severity >= ERROR"`
3. **ロールバック**: 必要に応じて前リビジョンに戻す
4. **報告**: Discord通知・原因分析

#### Warning Alert
1. **トレンド確認**: 継続的な問題か一時的な問題か
2. **リソース監視**: CPU・メモリ使用率確認
3. **改善計画**: 次回デプロイで修正検討

## 📋 チェックリスト

### デプロイ前確認
- [ ] GitHub Secrets設定完了
- [ ] GCP Secret Manager設定完了
- [ ] ローカルテスト実行済み（398/399テスト合格）
- [ ] コード品質チェック済み（flake8エラー < 50）
- [ ] MLモデル確認済み

### デプロイ後確認
- [ ] ヘルスチェック成功
- [ ] 24時間監視稼働
- [ ] 取引活動正常
- [ ] エラー率正常（< 1%/時間）
- [ ] パフォーマンス分析実行

### 段階移行確認
- [ ] Paper段階：ペーパートレード正常
- [ ] Stage-10段階：10%投入・監視24時間
- [ ] Stage-50段階：50%投入・監視24時間
- [ ] Live段階：100%移行・継続監視

## 🎯 成功指標

### CI/CD指標
- **ビルド成功率**: > 95%
- **テスト合格率**: > 99%（398/399）
- **デプロイ成功率**: > 95%
- **デプロイ時間**: < 5分

### 運用指標
- **アップタイム**: > 99.5%
- **応答時間**: < 3秒
- **エラー率**: < 1%/時間
- **監視精度**: > 90%

### 取引指標
- **取引成功率**: > 95%
- **API応答時間**: < 3秒
- **ポジション精度**: > 90%
- **リスク制御**: ドローダウン < 20%

---

**Phase 12実装完了**: レガシーシステムの良い部分を継承・改良し、CI/CD統合・24時間監視・段階的デプロイ対応の包括的な本番運用体制を確立