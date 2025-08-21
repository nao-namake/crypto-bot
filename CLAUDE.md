# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 最重要：開発状況（2025年8月21日現在）

### **🚀 Phase 12完了・CI/CD最終修正・GCP完全クリーンアップ完了**

**プロジェクト概要**: 
- **目標**: 個人向けAI自動取引システムの完成・本番運用準備完了
- **方針**: レガシーシステム（56,355行）→新システム（完全リファクタリング・クリーンアーキテクチャ）
- **現状**: **Phase 12完了・CI/CD最終修正・GCP337個リソース削除・本番運用開始**

**最終完了状況**: 
```
✅ Phase 1-12: 全フェーズ完了・基盤→データ→ML→戦略→リスク→実行→CI/CD
🎯 400+テスト・99.7%成功率・品質保証体制確立・CI/CD統合完了
📊 CI/CD最終修正: 設定パス修正・python3統一・Secret Manager統合・稼働確実性達成
🗑️ GCP完全クリーンアップ: 337個リソース削除・月額最適化・セキュリティ向上
📁 完全ドキュメント化: 31個README完備・包括的ガイド・運用手順
```

### **🏆 Phase 12最終成果（2025年8月21日）**

**CI/CD最終修正完了**:
- **根本原因解決**: 設定ファイルパス統一（config/base.yaml → config/core/base.yaml）
- **環境統一**: pythonコマンド → python3コマンド統一
- **Secret Manager完全動作**: API認証・Discord通知・本番運用準備完了

**GCP完全クリーンアップ達成**:
- **337個リソース削除**: BigQuery326個・Cloud Storage7個・Cloud Run8個
- **月額コスト最適化**: 不要ストレージ・リソース完全削除・数千円削減
- **セキュリティ向上**: 古いデータ排除・攻撃対象最小化・権限管理簡素化

**システム品質保証**:
- **400+テスト99.7%成功**: 統合テスト・回帰テスト・品質ゲート完了
- **完全ドキュメント化**: 31個README・運用手順・トラブルシューティング完備
- **本番運用体制**: 24時間監視・自動診断・段階的デプロイ対応

### **📂 システム構造（Phase 12最終版）**

```
src/                    # 新システム（18個README完備）
├── core/              # 基盤システム（設定管理・ログ・例外処理・統合制御）
├── data/              # データ層（Bitbank API・パイプライン・キャッシュ）
├── features/          # 特徴量（テクニカル指標12個厳選・異常検知）
├── strategies/        # 戦略システム（4戦略実装・113テスト100%）
├── ml/                # 機械学習（アンサンブル・89テスト・本番モデル）
├── backtest/          # バックテスト（エンジン・評価・84テスト・統合分析）
├── trading/           # 取引実行（リスク管理・Kelly基準・113テスト）
└── monitoring/        # 監視（Discord通知・3階層アラート）

scripts/                # 運用スクリプト（機能別整理・6カテゴリ）
├── management/        # 統合管理CLI（dev_check.py・6機能統合）
├── quality/           # 品質チェック（400+テスト・flake8・isort・black）
├── analytics/         # 統合分析基盤（base_analyzer.py・重複削除）
├── data_collection/   # 実データ収集（TradingStatisticsManager）
├── ab_testing/        # A/Bテスト（統計的検定・p値計算）
├── dashboard/         # ダッシュボード（HTML可視化・Chart.js）
├── ml/               # MLモデル（12特徴量・アンサンブル）
├── deployment/       # デプロイ（GCP CI/CD・自動診断）
└── testing/          # ライブトレードテスト

models/                 # MLモデル管理（本番用・学習用分離）
├── production/         # 本番用統合モデル・メタデータ
└── training/           # 学習用個別モデル・実験用

logs/                   # ログ・レポート（自動生成・4種類）
├── dev_check_reports/     # CI前チェック結果（markdown）
├── ops_monitor_reports/   # CI後運用診断（JSON・markdown）
├── backtest_reports/      # バックテストレポート（分析用）
└── paper_trading_reports/ # ペーパートレードセッション（実取引前検証）
```

## 🔧 開発ワークフロー（最終版）

### **統合管理CLI（推奨・python3使用）**
```bash
# CI前チェック（開発時）
python3 scripts/management/dev_check.py full-check     # 6段階統合チェック
python3 scripts/management/dev_check.py validate       # 軽量品質チェック
python3 scripts/management/dev_check.py ml-models      # MLモデル作成・検証

# CI後チェック（デプロイ後）
python3 scripts/management/ops_monitor.py              # 運用診断・稼働状況確認

# 期待結果: ✅ 400+テスト成功・自動レポート保存（logs/配下）
```

### **システム実行（本番対応）**
```bash
# メインシステム（python3統一）
python3 main.py --mode paper     # ペーパートレード（推奨・安全確認）
python3 main.py --mode backtest  # バックテスト（過去データ検証）
python3 main.py --mode live      # ライブトレード（本番取引・要注意）

# 分析・監視
python3 scripts/data_collection/trading_data_collector.py --hours 24  # 実データ収集
python3 scripts/ab_testing/simple_ab_test.py --hours 24               # A/Bテスト
python3 scripts/dashboard/trading_dashboard.py --discord              # ダッシュボード
```

### **品質チェック（本番運用）**
```bash
# 推奨品質チェック
bash scripts/quality/checks.sh           # 400+テスト・flake8・isort・black
bash scripts/quality/checks_light.sh     # 軽量版（99.7%成功実績）

# 手動検証
python3 tests/manual/test_phase2_components.py  # データ層基盤確認
```

## 🎯 開発原則・方針

### **README優先原則 🚨 重要**
**各フォルダ作業前に必ずREADME.mdを読む**:
- **目的・設計原則**: ディレクトリの責任範囲理解
- **既存構成**: ファイル構成・命名規則把握  
- **実装方針**: コーディング標準・パターン確認

**31個README完備**: src/18個・scripts/6個・logs/4個・その他3個

### **品質保証原則（Phase 12達成）**
- **400+テスト・99.7%成功率**: 新機能追加時も全合格維持必須
- **高速実行**: 全テスト約25秒以内完了
- **統合確認**: エンドツーエンド動作・システム連携確認

### **GCPリソース管理原則 🚨 新要件**
- **定期クリーンアップ必須**: 古いログ・リソースの定期削除（月1回推奨）
- **コスト最適化**: 不要なBigQueryテーブル・Cloud Storageファイル削除
- **セキュリティ維持**: 古いデータからの情報漏洩リスク排除
- **運用効率化**: 必要リソースのみ保持・GCPコンソール高速化

### **個人開発最適化**
- **シンプル性**: 個人が理解・保守可能な実装
- **実用性**: 実際の取引に必要な機能のみ
- **コスト効率**: 月額2,000円以内運用・定期クリーンアップで維持

## 💻 技術仕様

### **アーキテクチャ原則**
- **レイヤードアーキテクチャ**: 各層の責任明確分離・疎結合設計
- **エラーハンドリング階層化**: カスタム例外・適切なエラー管理
- **設定外部化**: 環境変数・YAML分離・config/core/base.yaml統一

### **データフロー（統合システム）**
```
📊 data → 🔢 features → 🎯 strategies → 🤖 ml → 💼 trading → 📡 monitoring
                                       ↓
📊 backtest → 📈 analytics → 📊 data_collection → 🎨 dashboard
                     ↓
            📁 logs/reports → 🗑️ 定期クリーンアップ
```

### **成功指標（Phase 12達成）**
- **品質保証**: 400+テスト・99.7%成功率・統合分析基盤対応
- **保守性**: 重複コード削除・統一インターフェース・README完備  
- **性能**: バックテスト高速化・GCP最適化・月額コスト削減

## 🗑️ GCPリソース定期クリーンアップ（新要件）

### **月次クリーンアップ手順**
```bash
# 1. 古いBigQueryテーブル確認・削除
bq ls crypto_bot_service_prod_logs | grep -E "$(date -d '30 days ago' '+%Y%m')" | head -20
# → 30日以上前のテーブルを個別確認・削除

# 2. Cloud Storageファイル確認
gsutil ls -l gs://my-crypto-bot-project_cloudbuild/source/ | awk '$2 < "'$(date -d '30 days ago' '+%Y-%m-%d')'"'
# → 古いビルドファイル削除

# 3. Cloud Runリビジョン確認
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --filter="metadata.creationTimestamp < '$(date -d '30 days ago' '+%Y-%m-%d')'"
# → 古いリビジョン削除（トラフィック0%のもの）

# 4. ログレポート整理
find logs/ -name "*.md" -mtime +30 -delete
find logs/ -name "*.json" -mtime +30 -delete
# → 30日以上前のレポート削除
```

### **自動化推奨スケジュール**
```bash
# crontabに追加（月1回実行）
0 0 1 * * cd /path/to/bot && bash scripts/deployment/monthly_cleanup.sh >> /tmp/gcp_cleanup.log 2>&1
```

### **削除対象・保持対象**
**🗑️ 削除対象**:
- 30日以前のBigQueryログテーブル
- 30日以前のCloud Buildソースファイル
- トラフィック0%の古いCloud Runリビジョン
- 30日以前のローカルレポートファイル

**✅ 保持対象**:
- 現在稼働中のCloud Runサービス
- アクティブなCloud Functions
- 必要なSecret Manager・IAM設定
- 本番用モデルファイル・設定

## 🚨 トラブルシューティング

### **よくある問題（python3環境対応）**

**1. インポートエラー**
```bash
# プロジェクトルートから実行（python3必須）
cd /Users/nao/Desktop/bot
python3 -m pytest tests/unit/ -v
```

**2. 設定ファイルエラー**
```bash
# 正しいパス確認
ls -la config/core/base.yaml  # ✅ 正しいパス
python3 -c "from src.core.config import load_config; print(load_config('config/core/base.yaml'))"
```

**3. GCPエラー**
```bash
# Secret Manager確認
gcloud secrets versions access latest --secret="bitbank-api-key"
gcloud secrets versions access latest --secret="discord-webhook-url"

# CI/CD環境確認  
bash scripts/deployment/verify_gcp_setup.sh --quick
```

**4. 品質チェックエラー**
```bash
# 軽量チェック（推奨）
bash scripts/quality/checks_light.sh

# python3環境確認
python3 --version  # 3.11.x推奨
```

**5. Docker環境クリーンアップ（月次推奨）**
```bash
# Docker Desktop手動削除
# 1. Docker Desktop → Builds → Build History全削除
# 2. Docker Desktop → Images → 古いイメージ削除

# コマンドラインクリーンアップ
docker system prune -a -f --volumes    # 全要素削除
docker buildx prune -a -f               # Build キャッシュ削除
docker builder prune -a -f              # Builder削除

# 期待結果: 25GB→数GB削減・Docker Desktop Build History 0個
```

## 📋 重要ファイル（Phase 12最終版）

### **必須ファイル**
- **config/core/base.yaml**: メイン設定ファイル（統一パス）
- **src/**: 新システム実装（18個README完備）
- **scripts/management/dev_check.py**: 統合管理CLI（6機能）
- **models/production/**: 本番用MLモデル・メタデータ

### **運用・監視**
- **logs/**: 自動レポート（4種類・定期クリーンアップ対象）
- **scripts/deployment/**: GCP CI/CD・自動診断
- **scripts/quality/**: 品質チェック（400+テスト）
- **Docker環境**: 定期クリーンアップ必須（Build History・キャッシュ・古いイメージ）

### **レガシー参考**
- **_legacy_v1/**: 旧システム（参考のみ・コピペ禁止）

---

## 🎉 Phase 12完了成果

**🚀 個人向けAI自動取引システム完全版**:
- **技術的完成**: 400+テスト・CI/CD統合・本番運用準備
- **運用効率化**: GCP337個リソース削除・Docker環境23.9GB削除・月額最適化・定期クリーンアップ体制
- **品質保証**: 99.7%テスト成功・統合分析・24時間監視対応
- **保守性向上**: 31個README・統一インターフェース・トラブルシューティング完備・Docker履歴管理

**🎯 月額2,000円以内・高品質・個人開発最適化を達成した究極のAI自動取引システム**

*GCP・Docker定期クリーンアップ・品質保証継続・実用性重視を基盤とした持続可能なシステム運用体制確立*