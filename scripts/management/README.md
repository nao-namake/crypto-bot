# Management Scripts

統合管理・運用管理系スクリプト集

## 🔄 CI前/CI後チェック役割分離

レガシーシステムの知見を活用し、開発フェーズと本番運用フェーズで役割分離を実現。

### CI前チェック（開発・検証フェーズ）
- **dev_check.py**: 開発中の品質保証・デプロイ前確認・統合テスト
- 目的: コード品質・機能完整性・デプロイ準備状況の確認

### CI後チェック（本番運用フェーズ）  
- **ops_monitor.py**: 本番環境運用監視・システム診断・障害検知
- 目的: 本番システム稼働状況・パフォーマンス・運用品質の確認

## 📂 スクリプト一覧

### dev_check.py
**CI前チェック統合管理CLI（Phase 12対応・開発フェーズ特化）**

開発・検証フェーズ用統合管理CLIツール。品質保証・デプロイ前確認・統合テスト機能を統合した開発者向け管理システム。

#### 役割：CI前チェック（開発フェーズ）
- コード品質確認（flake8・isort・black）
- 単体/統合テスト実行（316テスト）
- Phase実装完整性確認
- MLモデル作成・検証
- デプロイ前準備状況チェック

#### 主要機能
- **phase-check**: Phase実装状況確認（ディレクトリ・インポート・モデル・設定・CI/CD対応）
- **validate**: 品質チェック（full/light・checks.sh実行・438テスト対応・GitHub Actions統合）
- **ml-models**: MLモデル作成・検証（ドライラン対応・詳細ログ・メタデータ確認・監視統合）
- **data-check**: データ層基本確認（Pipeline・TechnicalIndicators・Config・API接続）
- **full-check**: 6段階統合チェック（Phase→データ→品質→ML→完全→状態・本番運用対応）
- **status**: システム状態確認（コンポーネント・重要ファイル・手動テスト・CI/CD状況）
- **operational**: 本番運用診断（ops_monitor.py委譲実行）

#### 使用例
```bash
# 推奨：6段階統合チェック
python scripts/management/dev_check.py full-check

# Phase実装状況確認
python scripts/management/dev_check.py phase-check

# 軽量品質チェック
python scripts/management/dev_check.py validate --mode light

# MLモデル作成・検証
python scripts/management/dev_check.py ml-models

# システム状態確認
python scripts/management/dev_check.py status

# 本番運用診断（ops_monitor.py委譲実行）
python scripts/management/dev_check.py operational
```

#### 期待結果
```
✅ すべてのチェックに合格しました！
🚀 Phase 12システムデプロイ準備完了
🔄 CI前チェック・品質保証完了
```

### ops_monitor.py  
**CI後チェック本番運用監視ツール（Phase 12対応・BaseAnalyzer活用）**

本番環境運用監視・システム診断ツール。Cloud Runサービス稼働状況・パフォーマンス監視・障害検知機能を提供。

#### 役割：CI後チェック（本番運用フェーズ）
- Cloud Runサービス状態監視
- リアルタイムログ分析
- パフォーマンス指標モニタリング  
- 障害検知・アラート
- 運用品質継続監視

#### 主要機能  
- **総合運用診断**: 4フェーズ統合チェックシステム
- **BaseAnalyzer活用**: Cloud Runログ取得・サービス状態確認
- **詳細レポート**: JSON/テキスト形式出力
- **Discord通知**: 重要アラート自動通知

#### 使用例
```bash
# 直接実行（本番運用監視）
python scripts/management/ops_monitor.py --verbose

# dev_check.py経由実行（委譲実行）
python scripts/management/dev_check.py operational
```

#### 期待結果
```
📊 Phase 12-3 新システム運用状況チェッカー
✅ Phase 1: サービス状態確認 完了
✅ Phase 2: ログ品質分析 完了  
✅ Phase 3: システムメトリクス分析 完了
✅ Phase 4: 総合スコア算出 完了
🎆 総合スコア: 95.2/100 - 本番環境正常稼働中
```

## 🎯 設計原則

### CI前/CI後役割分離哲学
- **明確な責任分界**: 開発フェーズと運用フェーズの機能分離
- **最適化されたツール**: 各フェーズに特化した機能設計
- **相互連携**: dev_check.pyからops_monitor.py委謗実行
- **BaseAnalyzer統合**: 共通機能をBaseAnalyzerで統合・重複コード削除

### 統合管理哲学（dev_check.py）
- **CI前品質保証**: コード品質・テスト・デプロイ準備確認
- **段階的チェック**: Phase確認→データ→品質→ML→完全→状態の6段階
- **タイムアウト対応**: 300秒制限で安定実行・CI/CD環境適応
- **開発者フレンドリー**: 詳細ログ・問題特定容易化

### 運用監視哲学（ops_monitor.py）
- **本番環境特化**: Cloud Runサービス状態・ログ品質・パフォーマンス監視
- **継続監視**: リアルタイム状態確認・障害早期発見
- **自動化**: BaseAnalyzer活用・コマンド一元化
- **運用品質**: 総合スコア算出・最適化推奨

### エラーハンドリング
- **包括的例外処理**: subprocess・タイムアウト・ファイル存在確認
- **継続可能設計**: 1つの失敗で全体停止しない
- **詳細ログ出力**: 問題箇所の特定容易化
- **BaseAnalyzer例外統合**: Cloud Runアクセスエラー、コマンド実行失敗の統一処理

## 🔧 トラブルシューティング

### よくあるエラー

**1. インポートエラー**
```bash
❌ インポートエラー: No module named 'src.core.config'
```
**対処**: プロジェクトルートから実行
```bash
cd /Users/nao/Desktop/bot
python scripts/management/dev_check.py phase-check
```

**2. タイムアウトエラー**
```bash
⏰ タイムアウト: checks.sh
```
**対処**: 軽量モード使用
```bash
python scripts/management/dev_check.py validate --mode light
```

**3. Phase確認失敗**
```bash
❌ 失敗: 3 項目
```
**対処**: 不足コンポーネントの確認・作成
```bash
# 不足ディレクトリ作成
mkdir -p src/ml models/production

# MLモデル作成
python scripts/ml/create_ml_models.py
```

**4. 本番運用監視エラー**
```bash
❌ Cloud Runアクセスエラー
```
**対処**: GCP認証・権限確認
```bash
# GCP認証確認
gcloud auth list
gcloud config get-value project

# ops_monitor.py直接実行
python scripts/management/ops_monitor.py --verbose
```

## 📈 Performance Notes

### CI前チェック（dev_check.py）
- **実行時間**: full-check約2-5分（モード依存）
- **軽量モード**: validate light約30秒
- **並列実行**: 複数チェックの同時実行対応
- **メモリ使用量**: 最大200MB程度

### CI後チェック（ops_monitor.py）
- **実行時間**: 総合診断約1-2分
- **BaseAnalyzer最適化**: Cloud Runログ取得高速化
- **メモリ使用量**: 最大100MB程度
- **リアルタイム性**: Cloud Run API直接アクセス

## 🔮 Future Enhancements

### Phase 13以降の拡張予定

#### CI前チェック強化（dev_check.py）
- **auto-fix**: 自動コード修正機能・flake8/black自動適用
- **security-scan**: セキュリティスキャン・脆弱性検知・CVEチェック  
- **performance-test**: パフォーマンステスト・ベンチマーク自動実行
- **dependency-check**: 依存ライブラリアップデート確認

#### CI後チェック強化（ops_monitor.py）
- **live-trading**: 実取引モニタリング機能・パフォーマンス追跡
- **alert-system**: Slack/Teams通知統合・エスカレーション・SLA監視
- **auto-recovery**: 障害自動復旧・ロールバック・サービス再起動
- **ml-ops**: MLモデルパフォーマンス監視・drift detection

#### 統合機能
- **dashboard**: Web UI統合管理・リアルタイムダッシュボード
- **analytics**: パフォーマンス分析・トレンド分析・改善推奨
- **compliance**: コンプライアンスチェック・監査ログ・レポート生成