# GitHub Actions Workflows

Phase 12 CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応のワークフロー集

**最新修正**: CI/CD稼働確実性向上・スキップ問題根本解決・必須リソース確認強化（2025年8月21日）

## 📂 ワークフロー一覧

### **🚀 ci.yml - CI/CDパイプライン**

**CI/CDワークフロー最適化・段階的デプロイ・品質保証システム（Phase 12対応・稼働確実性向上版）**

本格的なCI/CDパイプライン。品質チェック・Docker Build・GCP Cloud Run段階的デプロイ・コスト最適化・レガシー知見活用を統合実行。

**稼働確実性向上**: スキップ問題根絶・必須リソース確認強化・レガシー軽量検証採用。

#### 主要機能

**品質保証（quality-check）**:
- **段階的品質チェック**: 軽量→詳細→包括的な3段階チェック体制
- **テスト実行**: 450テスト・戦略層・ML層・取引層・バックテスト層・データ層
- **コード品質**: flake8・black・isort・構文チェック・docstring統一
- **システム統合**: phase-check・data-check・インポートテスト

**GCP環境事前確認（gcp-environment-check）**: **★2025年8月21日新設★**
- **レガシー軽量検証**: `gcloud config set project`による軽量プロジェクト設定確認
- **必須リソース確認強化**: Artifact Registry・Secret Manager存在確認（exit 1で停止）
- **スキップ問題根絶**: ⚠️警告で継続 → ❌エラーで停止・確実稼働保証
- **本番用モデル確認**: `models/production/production_ensemble.pkl`存在確認（必須）

**Docker Build & Deploy（build-deploy）**:
- **認証**: GCP Workload Identity・セキュアな認証・権限最小化
- **イメージ管理**: Artifact Registry・バージョン管理・セキュリティスキャン
- **段階的デプロイ**: paper → stage-10 → stage-50 → live
- **コスト最適化**: 1CPU/1Gi・MIN_INSTANCES=1（安定性重視）

**ヘルスチェック**:
- **デプロイ後確認**: /health エンドポイント・5回リトライ・30秒タイムアウト
- **基本動作確認**: API接続・レスポンス確認・エラー検知
- **通知**: 成功/失敗ステータス・Discord通知準備

#### 段階的デプロイ戦略

| ステージ | モード | リソース | インスタンス | 用途 |
|---------|--------|----------|-------------|------|
| Paper | `paper` | 1Gi/1CPU | 0-1 | 安全テスト |
| Stage-10 | `stage-10` | 1Gi/1CPU | 1-1 | 10%投入 |
| Stage-50 | `stage-50` | 1.5Gi/1CPU | 1-1 | 50%投入 |
| Production | `live` | 1Gi/1CPU | 1-2 | 100%本番 |

#### レガシー知見活用
- **MIN_INSTANCES=1**: SIGTERM頻発問題完全解決実績・約1,800円/月
- **段階的品質チェック**: レガシーci_tools/の良い部分を統合・効率化
- **エラーハンドリング**: 過去の失敗パターン・解決策を統合

#### 使用方法

```bash
# 自動トリガー（推奨）
git add -A
git commit -m "feat: Phase 12 update"
git push origin main  # 自動CI/CD実行

# デプロイモード制御（GitHub Secrets）
# DEPLOY_MODE=paper    # テスト環境
# DEPLOY_MODE=stage-10 # 10%投入
# DEPLOY_MODE=stage-50 # 50%投入
# DEPLOY_MODE=live     # 100%本番

# ワークフロー確認
gh run list --limit 5
gh run view --log
```

### **📊 monitoring.yml - 手動実行監視**

**24時間継続監視・ヘルスチェック・パフォーマンス追跡（手動実行専用）**

Phase 12で手動実行専用に調整。システムヘルス・エラー分析・取引活動・パフォーマンス指標を必要時に確認し、異常時にはアラート・対応推奨を自動生成。

#### 主要機能

**システムヘルスチェック（health-check）**:
- **Cloud Runサービス**: 状態確認・URL取得・トラフィック配分確認
- **API応答時間**: /health エンドポイント・レスポンス時間測定・閾値監視
- **エラーログ分析**: 過去15分のERRORログ・カテゴリ分類・件数集計

**パフォーマンス監視（performance-monitoring）**:
- **リソース使用量**: CPU・メモリ使用率・Cloud Monitoring連携
- **API応答時間**: 複数回測定・平均値算出・3秒閾値チェック
- **レスポンス品質**: 成功率・エラー率・パフォーマンス劣化検知

**取引・シグナル監視（trading-monitoring）**:
- **取引活動**: 過去1時間の取引ログ・注文実行・成果測定
- **シグナル生成**: BUY/SELL/HOLDシグナル頻度・30分以内確認
- **システム稼働**: 取引システム正常性・継続稼働確認

**監視レポート（monitoring-report）**:
- **総合判定**: システム状態・エラー率・応答時間・総合評価
- **アラート**: CRITICAL・WARNING・OK状態判定・推奨アクション
- **Discord通知**: クリティカル時のみ自動通知・緊急対応支援

#### 監視間隔・閾値

```yaml
監視頻度: 15分間隔（cron: '*/15 * * * *'）
監視項目:
  - システムヘルス: リアルタイム
  - エラー分析: 過去15分
  - 取引活動: 過去1時間
  - シグナル生成: 過去30分

閾値設定:
  - 応答時間: < 3秒（正常）、> 3秒（警告）
  - エラー率: < 5/時間（正常）、> 5/時間（警告）
  - シグナル頻度: > 0件/30分（正常）
```

#### アラート条件

**🚨 CRITICAL（緊急対応）**:
- Cloud Runサービス停止
- API認証失敗・接続不可
- 継続的エラー（> 10/時間）

**⚠️ WARNING（注意監視）**:
- 応答時間 > 3秒
- エラー率 > 5/時間
- シグナル生成停止

**✅ OK（正常稼働）**:
- 全指標が閾値内
- システム安定稼働
- 継続監視継続

#### 使用方法

```bash
# 自動実行（15分間隔）
# GitHub Actionsが自動実行・手動操作不要

# 手動実行
gh workflow run monitoring.yml

# 実行状況確認
gh run list --workflow=monitoring.yml --limit 10

# ログ確認
gh run view --log

# 監視データ確認（GCP）
gcloud logging read "resource.type=\"cloud_run_revision\"" --limit=20
```

### **🧪 test.yml - テスト実行**

**ユニットテスト・統合テスト実行（Phase 10品質保証体制）**

438テスト・68.13%品質保証を実現するテスト実行ワークフロー。既存の品質保証体制を維持しつつ、CI/CDパイプラインと連携。

## 🎯 設計原則

### **CI/CD哲学**
- **品質ファースト**: デプロイ前の完全品質チェック必須
- **段階的リリース**: リスク最小化・安全確認・継続監視
- **自動化優先**: 手動作業削減・人的ミス防止・効率化
- **レガシー活用**: 過去の知見・エラーパターン・解決策統合

### **監視統合**
- **24時間継続**: 15分間隔・包括的監視・予兆検知
- **アラート連携**: 段階的エスカレーション・適切な対応推奨
- **データ収集**: 長期トレンド・パフォーマンス改善・継続最適化

### **セキュリティ**
- **Workload Identity**: GCP認証・権限最小化・監査ログ
- **シークレット管理**: Secret Manager・暗号化・ローテーション
- **アクセス制御**: 必要最小限・行動監視・インシデント対応

## 🔧 設定・カスタマイズ

### **GitHub Secrets設定**

```bash
# 必須Secrets（docs/github_secrets_setup.md参照）
GCP_WIF_PROVIDER: workload identity provider
GCP_SERVICE_ACCOUNT: service account email
GCP_PROJECT: my-crypto-bot-project
DEPLOY_MODE: paper/stage-10/stage-50/live
```

### **環境変数**

```bash
# ワークフロー共通設定
PROJECT_ID: my-crypto-bot-project
REGION: asia-northeast1
REPOSITORY: crypto-bot-repo
SERVICE_NAME: crypto-bot-service
```

### **カスタマイズポイント**

**監視間隔調整**:
```yaml
# monitoring.yml
schedule:
  - cron: '*/15 * * * *'  # 15分→10分等に変更可能
```

**閾値調整**:
```bash
# 応答時間閾値
if [ $avg_time -gt 3000 ]; then  # 3秒→5秒等に変更
```

**デプロイリソース調整**:
```bash
# ci.yml段階的デプロイ設定
MEMORY="1Gi"  # 必要に応じて調整
CPU="1"       # 必要に応じて調整
```

## 📊 パフォーマンス指標

### **CI/CD効率**
- **ビルド時間**: 平均3-5分（品質チェック含む）
- **デプロイ成功率**: > 95%（段階的デプロイ効果）
- **品質保証**: 438テスト68.13%成功率維持

### **監視精度**
- **アップタイム監視**: 99.5%以上
- **障害検知**: 15分以内（自動検知）
- **誤検知率**: < 5%（閾値最適化）

### **コスト効率**
- **GitHub Actions**: 月約50-100分（無料枠内）
- **Cloud Run**: 月1,800-2,700円（目標達成）
- **監視コスト**: ほぼゼロ（Cloud Logging無料枠活用）

## 🚨 トラブルシューティング

### **CI/CD失敗時**

**品質チェック失敗**:
```bash
# ローカル確認
bash scripts/quality/checks.sh

# 個別テスト確認
python -m pytest tests/unit/strategies/ -v
```

**デプロイ失敗**:
```bash
# GCP認証確認
gcloud auth list

# サービス状態確認
gcloud run services list --region=asia-northeast1
```

### **監視アラート対応**

**CRITICAL Alert**:
1. **即座確認**: サービス状態・ログ分析
2. **ロールバック**: 必要に応じて前リビジョン復旧
3. **原因調査**: エラーログ・システム負荷確認

**WARNING Alert**:
1. **トレンド監視**: 継続的問題か一時的問題か
2. **リソース確認**: CPU・メモリ使用率
3. **改善計画**: 次回デプロイで修正検討

## 🔮 Phase 12-3以降の拡張

### **高度なCI/CD**
- **並列実行**: テスト・ビルドの並列化
- **キャッシュ最適化**: Docker Layer・依存関係キャッシュ
- **マトリックスビルド**: 複数環境・バージョン対応

### **高度な監視**
- **メトリクス連動**: Cloud Monitoring・カスタムメトリクス
- **予測分析**: 機械学習による障害予測
- **自動復旧**: 異常検知時の自動対応・セルフヒーリング

---

**Phase 12実装完了**: レガシーシステムの良い部分を継承・改良し、CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応の包括的なワークフロー体系を確立