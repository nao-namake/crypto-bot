# Scripts Directory

運用スクリプト集（Phase 12-2最適化完了）

**Phase 12-2完了**: BaseAnalyzer統合基盤・CI前/CI後役割分離・約520行重複コード削除・最適化された機能別フォルダ構成・統合管理システム・統合品質保証（2025年8月19日）

## 📂 フォルダ構成（Phase 12-2最適化完了）

```
scripts/
├── management/     # CI前/CI後チェック管理系 [README.md]
│   ├── dev_check.py               # CI前チェック統合管理CLI（Phase 12対応・開発フェーズ特化）
│   └── ops_monitor.py              # CI後チェック本番運用監視（BaseAnalyzer継承・約120行削除）
├── analytics/      # パフォーマンス分析・BaseAnalyzer統合基盤 [README.md]
│   ├── base_analyzer.py             # 統合共通基盤クラス（約520行重複コード削除達成）
│   └── performance_analyzer.py      # システムパフォーマンス分析（BaseAnalyzer継承・約100行削除）
├── dashboard/      # HTMLダッシュボード・可視化 [README.md]
│   └── trading_dashboard.py         # 取引成果ダッシュボード（BaseAnalyzer継承完了）
├── data_collection/ # 実データ収集・統計分析 [README.md]
│   └── trading_data_collector.py    # 実データ収集（BaseAnalyzer継承完了）
├── ab_testing/     # A/Bテスト・統計検定 [README.md]
│   └── simple_ab_test.py            # A/Bテスト実行（BaseAnalyzer継承完了）
├── quality/        # 品質保証・チェック系 [README.md]  
│   └── checks.sh                   # 完全品質チェック（438テスト・80%カバレッジ・CI/CD統合）
├── ml/            # 機械学習・モデル系 [README.md]
│   └── create_ml_models.py         # MLモデル作成（12特徴量・Phase 12アンサンブル統合）
├── deployment/    # デプロイ・Docker系 [README.md]
│   ├── deploy_production.sh        # 本番デプロイ（GCP Cloud Run・CI/CD統合・段階的デプロイ）
│   └── docker-entrypoint.sh        # Docker統合エントリポイント（lightweight・ヘルスチェック）
└── testing/       # テスト・検証系 [README.md]
    └── test_live_trading.py         # ライブトレードテスト（本番前検証・CI/CD統合）
```

## 🎯 推奨使用フロー（Phase 12-2対応）

### 日常開発・品質確認
```bash
# 🚀 統合管理CLI（推奨・最も簡単）
python scripts/management/dev_check.py full-check     # 6段階統合チェック
python scripts/management/dev_check.py phase-check    # Phase実装状況確認
python scripts/management/dev_check.py status         # システム状態確認

# ⚡ 軽量品質チェック（高速確認・統合管理CLI経由推奨）
python scripts/management/dev_check.py validate --mode light

# 期待結果:
# ✅ すべてのチェックに合格しました！
# 🚀 Phase 12-2システム最適化完了・BaseAnalyzer統合基盤適用
```

### MLモデル開発・管理
```bash
# 🤖 MLモデル管理（統合管理CLI経由・推奨）
python scripts/management/dev_check.py ml-models      # モデル作成・検証
python scripts/management/dev_check.py ml-models --dry-run  # ドライラン

# 🔧 直接実行（詳細制御が必要な場合）
python scripts/ml/create_ml_models.py --verbose         # 詳細ログ
python scripts/ml/create_ml_models.py --days 360        # 学習期間指定

# 期待結果:
# 🤖 MLモデル作成成功！
# - LightGBM: F1 score 0.952
# - XGBoost: F1 score 0.997  
# - RandomForest: F1 score 0.821
```

### 本番デプロイ準備・実行
```bash
# 📋 デプロイ前準備
bash scripts/quality/checks.sh                          # 完全品質チェック
python scripts/testing/test_live_trading.py --paper-trade  # ライブトレードテスト

# 🚀 本番デプロイ実行（Phase 12 CI/CD統合）
bash scripts/deployment/deploy_production.sh            # GCP Cloud Run デプロイ

# 📊 デプロイ後確認
python scripts/management/dev_check.py status         # システム状態確認
python scripts/management/dev_check.py health-check   # 本番環境ヘルスチェック
```

## 🎯 機能別詳細ガイド

### 📁 management/ - 統合管理系
**主要スクリプト**: `dev_check.py`（665行・6機能統合）

**コア機能**:
- **phase-check**: Phase実装状況確認（ディレクトリ・インポート・モデル・設定）
- **validate**: 品質チェック（full/light・checks.sh実行・438テスト対応）
- **ml-models**: MLモデル作成・検証（ドライラン対応・詳細ログ・メタデータ確認）
- **data-check**: データ層基本確認（Pipeline・TechnicalIndicators・Config）
- **full-check**: 6段階統合チェック（Phase→データ→品質→ML→完全→状態）
- **status**: システム状態確認（コンポーネント・重要ファイル・手動テスト）

**推奨用途**: 日常の統合管理・品質確認・システム状態把握

### 📁 quality/ - 品質保証系
**主要スクリプト**: `checks.sh`（完全版・Phase 12 CI/CD統合）

**checks.sh（完全版）**:
- **対象**: flake8・isort・black・pytest・カバレッジ・CI/CD統合
- **実行時間**: 2-5分
- **用途**: デプロイ前・Phase完了時の完全品質保証・GitHub Actions統合
- **Phase 12統合**: CI/CDパイプライン・段階的デプロイ・品質ゲート

**軽量品質チェック**:
- **統合管理CLI経由推奨**: `python scripts/management/dev_check.py validate --mode light`
- **対象**: 基本構造・インポート・438テスト・68.13%成功実績
- **実行時間**: 30秒
- **用途**: 日常開発・迅速な品質確認・CI/CD事前チェック

**推奨用途**: 開発時の品質管理・デプロイ前チェック・CI/CD統合・継続的品質保証

### 📁 ml/ - 機械学習系
**主要スクリプト**: `create_ml_models.py`（545行・包括的ML学習システム）

**機能詳細**:
- **12特徴量最適化**: 97個→12個への極限削減・過学習防止
- **3モデル学習**: LightGBM・XGBoost・RandomForest個別学習
- **アンサンブル統合**: ProductionEnsemble・重み付け投票（0.4/0.4/0.2）
- **本番対応**: models/production/・pickle対応・メタデータ管理

**推奨用途**: 定期的なモデル再学習・性能向上・本番モデル更新

### 📁 deployment/ - デプロイ系
**主要スクリプト**: `deploy_production.sh`・`docker-entrypoint.sh`

**deploy_production.sh**:
- **機能**: GCP Cloud Run自動デプロイ・品質チェック統合
- **安全性**: 段階的デプロイ・ロールバック機能・ヘルスチェック

**docker-entrypoint.sh**:
- **機能**: Docker統合エントリポイント・プロセス監視・グレースフルシャットダウン
- **軽量性**: Ultra-lightweight・最小リソース使用

**推奨用途**: 本番環境デプロイ・Docker環境構築・運用自動化

### 📁 testing/ - テスト系
**主要スクリプト**: `test_live_trading.py`

**機能詳細**:
- **エンドツーエンドテスト**: データ取得→特徴量→予測→リスク管理→注文
- **パフォーマンステスト**: レイテンシー・メモリ使用量・処理時間測定
- **異常系テスト**: ネットワーク断・APIエラー・例外処理検証
- **安全性**: ペーパートレード・最小取引単位・リスク制限

**推奨用途**: 本番前検証・性能測定・統合動作確認

## 📊 Phase 12整理成果

### 整理前後の比較
```
📂 整理前（Phase 9）:
scripts/
├── dev_check.py            # 665行・統合管理
├── checks.sh              # 品質チェック  
├── checks_light.sh         # 軽量品質チェック（削除済み）
├── create_ml_models.py     # MLモデル作成
├── deploy_production.sh    # 本番デプロイ
├── docker-entrypoint.sh    # Docker統合
├── test_live_trading.py    # ライブトレードテスト
└── README.md              # Phase 9版

📂 整理後（Phase 12）:
scripts/
├── management/    [README.md] # 統合管理系（1スクリプト・CI/CD統合）
├── quality/       [README.md] # 品質保証系（1スクリプト・CI/CD統合）
├── ml/           [README.md] # 機械学習系（1スクリプト・監視統合）
├── deployment/   [README.md] # デプロイ系（2スクリプト・段階的デプロイ）
├── testing/      [README.md] # テスト系（1スクリプト・CI/CD統合）
└── README.md              # Phase 12版（本ファイル）
```

### Phase 12整理効果
- **✅ CI/CD統合**: GitHub Actions・品質ゲート・自動デプロイ・段階的リリース
- **✅ 監視システム統合**: 手動実行監視・ヘルスチェック・自動復旧・Discord通知
- **✅ セキュリティ強化**: Workload Identity・Secret Manager・監査ログ・コンプライアンス
- **✅ 運用効率化**: 軽量チェック統合管理CLI化・checks_light.sh削除・機能集約
- **✅ 機能別分類**: 5カテゴリー・明確な責任分離・CI/CD対応
- **✅ ドキュメント充実**: 6個README・包括的使用方法・Phase 12対応・トラブルシューティング

## 🔧 トラブルシューティング

### よくあるエラー

**1. 統合管理CLI実行エラー**
```bash
❌ ModuleNotFoundError: No module named 'src'
```
**対処**: プロジェクトルートから実行
```bash
cd /Users/nao/Desktop/bot
python scripts/management/dev_check.py phase-check
```

**2. 品質チェック失敗**
```bash
❌ テスト実行失敗
```
**対処**: 軽量モードで原因特定
```bash
python scripts/management/dev_check.py validate --mode light
bash scripts/quality/checks.sh  # 完全チェック
```

**3. MLモデル作成失敗**
```bash
❌ 特徴量数不一致: 10 != 12
```
**対処**: データ確認・ドライラン実行
```bash
python scripts/management/dev_check.py data-check
python scripts/management/dev_check.py ml-models --dry-run
```

**4. デプロイエラー**
```bash
❌ GCP認証エラー
```
**対処**: 認証確認・権限設定
```bash
gcloud auth list
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

## 📈 Performance & Usage

### 実行時間目安
- **統合管理CLI**: full-check 2-5分・phase-check 30秒・validate --mode light 30秒
- **品質チェック**: checks.sh 2-5分（CI/CD統合）
- **MLモデル作成**: 10-30分（データサイズ依存・監視統合）
- **デプロイ**: 5-10分（Docker Build含む・段階的デプロイ）
- **ライブトレードテスト**: 1-24時間（モード依存・CI/CD統合）

### リソース使用量
- **メモリ使用量**: 200MB-2GB（機能依存）
- **ディスク使用量**: 一時ファイル100MB-1GB
- **ネットワーク**: API通信・Docker Registry・GCP通信

## 🔮 Future Enhancements

Phase 12以降の拡張予定:
- **scripts/monitoring/**: リアルタイム監視・アラート系スクリプト・手動実行監視拡張
- **scripts/maintenance/**: 定期メンテナンス・クリーンアップ系・自動化運用
- **scripts/analytics/**: 取引分析・レポート生成系・AI分析・パフォーマンス可視化
- **scripts/backup/**: バックアップ・復旧系スクリプト・災害復旧・データ保護
- **scripts/security/**: セキュリティ監査・脆弱性スキャン・コンプライアンス

**Phase 12整理原則の継続**:
- 機能別フォルダ分類の維持・CI/CD対応
- フォルダごとREADME充実・監視統合対応
- 統合管理CLIへの機能統合・ヘルスチェック・monitoring
- トラブルシューティングガイド更新・セキュリティ対応

---

**🎉 Phase 12完了成果**: *CI/CD統合・手動実行監視・セキュリティ強化・スクリプト機能別整理・統合管理システム・品質保証自動化・包括的ドキュメント化* 🚀

**運用効率**: CI/CD統合・統合管理CLI・手動実行監視導入により、本番運用から緊急対応まで1コマンドで実行可能・運用効率大幅向上・無人運用対応