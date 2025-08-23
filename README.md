# Crypto-Bot - 🚀 AI自動取引システム

**個人向けAI自動取引システム（Phase 14: 本番デプロイ・エラー修正段階）**

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org) [![Phase](https://img.shields.io/badge/phase-14%20進行中-orange)](CLAUDE.md) [![Status](https://img.shields.io/badge/status-デプロイ・修正繰り返し中-yellow)](CLAUDE.md) [![CI/CD](https://img.shields.io/badge/CI%2FCD-実行中-blue)](.github/workflows/) [![Tests](https://img.shields.io/badge/tests-306%20passed%20100%25-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-58.88%25-orange)](coverage-reports/) [![Cloud Run](https://img.shields.io/badge/Cloud%20Run-修正コード反映待ち-yellow)](https://console.cloud.google.com/run)

## 🎯 システム概要

個人向けAI自動取引システムです。レガシーシステム（56,355行）から保守性の高い新システムへの全面リファクタリングが完了し、**現在は本番デプロイ・エラー修正を繰り返し実行中**です。Phase 13で基盤完成、Phase 14で実運用開始を目指しています。

## ⚡ Phase 14 現在進行状況（本番デプロイ・エラー修正段階）

### **🔄 現在実行中の作業（2025年8月23日 午後8時）**

**✅ 完了済み修正**:
- **TradingOrchestrator取引サイクル**: Protocol定義・メソッドシグネチャ統一完了
- **async/sync統一**: RiskService不正await削除・全同期処理統一
- **StrategyManager初期化**: 戦略登録方式修正・正常組み立て確認済み
- **包括的エラーチェック**: 7項目解決・ローカル動作確認完了

**🔄 実行中**:
- **CI/CDパイプライン**: プッシュ成功・品質チェック通過・デプロイ実行中
- **Cloud Runデプロイ**: 修正コード反映待ち・exit(1)エラー解消予定
- **取引サイクル正常化**: エントリーシグナル→トレード実行復旧予定

**🎯 解決予定**:
- **24時間継続稼働**: 全修正適用により安定稼働開始
- **エントリーシグナル処理**: 正常な取引判定・実行フロー復旧
- **Phase 14完了**: 本番運用開始・自動取引体制確立

### 📊 品質保証・デプロイ状況

```
🔄 デプロイ段階: CI/CD実行中・Cloud Run反映待ち（修正コード準備完了）
✅ ローカル品質: 全モジュールインポート成功・構文チェック全て通過・設定適切
🎯 修正完了項目: Protocol不整合・async/sync統一・StrategyManager初期化
🚀 次回マイルストーン: CI/CD成功→Cloud Run正常稼働→取引機能検証→Phase 14完了
```

## 🔧 開発原則

### **🚨 重要：README.md優先原則**
**各フォルダ作業前に必ずREADME.mdを読む**
- **22個README完備**: src/18個・scripts/・config/・models/包括的ガイド・完全ドキュメント化
- **Phase 13対応**: 最新状況・統合最適化・ファイル管理ルール・品質基準理解

## 🚀 現在の実行状況・確認方法

### **⚡ Phase 14: デプロイ・修正繰り返し段階での確認コマンド**

```bash
# 【1. デプロイ状況確認】
gh run list --limit 3                                  # CI/CD実行状況確認
gcloud run services list --region=asia-northeast1      # Cloud Runサービス一覧

# 【2. ローカル修正確認】
python3 scripts/management/dev_check.py validate       # 軽量品質チェック
python3 scripts/management/dev_check.py operational    # 運用診断（修正後確認）

# 【3. Cloud Run稼働確認】
gcloud logging read "resource.type=cloud_run_revision" --limit=10  # 最新ログ確認
gcloud run services describe crypto-bot-service-prod-prod --region=asia-northeast1  # サービス状態

# 【4. エラー状況確認】
gcloud logging read "severity>=WARNING" --limit=5      # 警告・エラーログ確認

# 期待結果: 🎯 CI/CD成功→Cloud Run正常稼働→exit(1)エラー解消→取引開始
```

## 🛠️ Phase 14 - 本番デプロイ・エラー修正段階

**現在の状況**: 重要な修正（Protocol統一・async/sync修正・StrategyManager初期化）が完了し、CI/CDパイプラインが実行中です。修正コードがCloud Runに反映され次第、安定した24時間自動取引が開始される予定です。

### デプロイ・修正の流れ

1. **ローカル修正完了** ✅ - 全エラーを特定・修正コード作成
2. **CI/CDパイプライン** 🔄 - プッシュ成功・品質チェック通過・デプロイ実行中  
3. **Cloud Run反映** ⏳ - 修正コード反映待ち・exit(1)エラー解消予定
4. **取引機能検証** 📋 - エントリーシグナル→実取引の動作確認予定
5. **Phase 14完了** 🎯 - 本番運用開始・24時間自動取引体制確立予定

### 統合分析・レポート確認

```bash
# 統合レポートナビゲーション
cat logs/reports/INDEX.md                              # ビジュアルナビゲーション・頻繁参照最適化

# 統合分析基盤レポート（Phase 13新機能）
ls logs/reports/analytics/                             # データ収集・ダッシュボード・パフォーマンスレポート
ls logs/reports/testing/                               # 統合品質チェック・ライブテスト結果

# 最新レポート確認（シンボリックリンク）
cat logs/reports/ci_checks/latest/latest_dev_check.md   # 最新CI前チェック
cat logs/reports/trading/latest/latest_backtest.md      # 最新バックテスト結果
cat logs/reports/trading/latest/latest_paper.md         # 最新ペーパートレード結果
```

### システム実行（sklearn警告解消済み）

```bash
# メインシステム（python3統一・sklearn警告解消済み）
python3 main.py --mode paper     # ペーパートレード（推奨・安全確認）
python3 main.py --mode backtest  # バックテスト（過去データ検証）
python3 main.py --mode live      # ライブトレード（本番取引）

# 期待結果: 🚀 Phase 13システム起動・sklearn警告なし・統合レポート生成
```

### 品質チェック（Phase 13統合対応）

```bash
# 統合品質チェック（306テスト・sklearn警告解消対応）
bash scripts/testing/checks.sh                        # 統合チェック（約30秒）

# 統合管理CLI経由（推奨）
python3 scripts/management/dev_check.py validate       # 軽量品質チェック

# 期待結果: ✅ 306テスト100%・sklearn警告なし・flake8・black・isort統合チェック
```

## 🏗️ システム構成（Phase 13最終版・統合最適化完了）

### **統合最適化・品質保証完成・ビジュアルナビゲーション対応**

```
src/                    # 新システム（18個README完備）
├── core/              # 基盤システム（設定管理・ログ・例外処理・統合制御）
├── data/              # データ層（Bitbank API・パイプライン・キャッシュ）
├── features/          # 特徴量（テクニカル指標12個厳選・異常検知）
├── strategies/        # 戦略システム（4戦略・113テスト100%）
├── ml/                # 機械学習（アンサンブル・89テスト100%・sklearn警告解消）
├── backtest/          # バックテスト（エンジン・評価・84テスト100%）
├── trading/           # 取引実行（リスク管理・Kelly基準・113テスト100%）
└── monitoring/        # 監視（Discord通知・3階層）

logs/                   # 統合ログ管理システム（Phase 13統合完了）
├── reports/           # 統合レポート管理・ビジュアルナビゲーション
│   ├── ci_checks/     # CI前後チェック（頻繁参照・最新リンク対応）
│   ├── trading/       # バックテスト・ペーパートレード（頻繁参照）
│   ├── operational/   # 運用診断・システム状態
│   └── INDEX.md       # ビジュアルナビゲーション・頻繁参照最適化
├── system/            # システムログ（crypto_bot.log等）
├── trading_history/   # 実取引履歴（CSVファイル）
├── state/             # システム状態管理
└── deployment/        # デプロイ関連ログ

scripts/                # 運用スクリプト（9→5フォルダ統合・44%削減・重複コード500行削除）
├── analytics/         # 統合分析基盤（dashboard/data_collection/ab_testing統合）
│   ├── base_analyzer.py　　 # 共通基盤クラス（500行重複コード削除）
│   ├── data_collector.py    # 実データ収集（旧trading_data_collector.py）
│   ├── dashboard.py         # HTMLダッシュボード（旧trading_dashboard.py）
│   └── performance_analyzer.py # システムパフォーマンス分析
├── management/        # 統合管理CLI（dev_check.py・665行6機能統合）
├── testing/           # 統合テスト・品質チェック（quality統合）
│   ├── checks.sh              # 統合品質チェック（306テスト・sklearn警告解消）
│   └── test_live_trading.py   # ライブトレーディングテスト
├── ml/               # MLモデル（sklearn警告解消・アンサンブル）
└── deployment/       # デプロイ（GCP CI/CD・自動診断）

config/                  # 設定管理（Phase 13階層化・最適化完了）
├── core/              # 基本設定（base.yaml・feature_order.json）
├── gcp/               # GCP関連設定（CI/CD・Secret Manager）
├── deployment/        # デプロイ設定（Cloud Run・Docker）
├── development/       # 開発環境設定
├── production/        # 本番環境設定
├── staging/           # ステージング環境設定
└── validation/        # 検証・テスト設定

models/                 # MLモデル管理（Phase 13完全整理・レガシー削除完了）
├── production/         # 本番用統合モデル（ProductionEnsemble・メタデータ・README）
└── training/           # 学習用個別モデル（LightGBM・XGBoost・RandomForest・README）

coverage-reports/       # テストカバレッジ（58.88%・品質目標設定）
├── htmlcov/           # HTMLカバレッジレポート
├── .coverage          # カバレッジデータ
└── README.md          # カバレッジ管理ルール・品質目標
```

## 🎯 主要機能

### **ML・アンサンブル（sklearn警告解消・品質保証完成）**
- **ProductionEnsemble**: LightGBM・XGBoost・RandomForest統合（重み: 0.4/0.4/0.2）
- **12特徴量最適化**: 97個→12個厳選・高精度維持・処理効率向上
- **sklearn警告解消**: 全deprecation warning解消・最新ライブラリ対応・型安全性確保
- **品質保証**: F1スコア0.85以上・306テスト100%・メタデータ管理

### **スクリプト統合・分析基盤（Phase 13完成）**
- **scripts/統合**: 9→5フォルダ（44%削減）・統合分析基盤・重複コード500行削除
- **統合分析基盤**: dashboard/data_collection/ab_testing→analytics統合・base_analyzer.py基盤
- **品質チェック統合**: quality→testing統合・checks.sh・test_live_trading.py一元化
- **統合管理CLI**: dev_check.py 665行6機能統合・operationalコマンド統合

### **戦略・リスク管理（品質保証完成）**
- **4戦略統合**: ATR・もちぽよ・MTF・フィボナッチ（113テスト100%）
- **Kelly基準**: 最適ポジションサイジング・リスク管理
- **統合リスク**: ドローダウン制御・異常検知・自動停止機能
- **バックテスト**: 統合エンジン・評価システム（84テスト100%）

### **CI/CD・運用（本番稼働中）**
- **GitHub Actions**: 自動ビルド・テスト・デプロイ・Secret Manager統合
- **Cloud Run**: 本番環境安定動作・24時間監視・自動スケーリング
- **品質ゲート**: 306テスト・flake8・isort・black統合チェック
- **監視システム**: Discord通知・3階層アラート・運用診断

## 📊 技術仕様

### **技術スタック**
- **言語**: Python 3.11・型ヒント・非同期処理
- **ML**: scikit-learn・LightGBM・XGBoost・pandas・numpy（sklearn警告解消済み）
- **API**: Bitbank信用取引API・Discord Webhook・GCP APIs
- **インフラ**: GCP Cloud Run・Secret Manager・GitHub Actions
- **品質保証**: pytest・flake8・black・isort・カバレッジ58.88%

### **アーキテクチャ原則**
- **レイヤードアーキテクチャ**: 各層責任分離・疎結合・依存性注入
- **統合管理**: logs/reports/統合・models/整理・config/最適化
- **品質保証**: 306テスト・sklearn警告解消・包括的カバレッジ
- **運用効率**: ビジュアルナビゲーション・頻繁参照最適化・自動化

### **成功指標（Phase 13達成）**
- **品質保証**: 306テスト100%・sklearn警告解消・58.88%カバレッジ
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・最新リンク
- **models/整理**: レガシー削除・ファイル管理ルール・品質基準確立
- **運用効率**: CI前後チェック統合・自動レポート・統合管理CLI

## 🚨 注意事項

### **実取引リスク**
- **投資リスク**: 暗号資産取引は元本保証なし・損失可能性あり
- **動作確認**: 必ずペーパートレードで十分な検証実施
- **責任範囲**: 取引結果の責任は利用者に帰属

### **技術要件**
- **Python 3.11+**: sklearn警告解消・最新ライブラリ対応必須
- **メモリ**: 最低2GB推奨（MLモデル読み込み用）
- **ストレージ**: 1GB以上（ログ・レポート・モデル保存用）

### **セキュリティ**
- **API キー**: 環境変数・Secret Manager管理必須
- **アクセス制御**: GCP IAM・Workload Identity設定
- **ログ管理**: 機密情報除外・適切なログローテーション

## 📞 サポート

### **ドキュメント**
- **CLAUDE.md**: 開発ガイド・Phase 13完了状況・統合最適化詳細
- **各README**: 22個完備・機能詳細・使用方法・トラブルシューティング
- **logs/reports/INDEX.md**: ビジュアルナビゲーション・頻繁参照最適化

### **品質保証**
- **306テスト**: 継続的品質保証・回帰防止・ML処理安定性
- **sklearn警告解消**: 最新ライブラリ対応・型安全性・互換性確保
- **統合管理**: logs/reports/統合・models/整理・config/最適化

### **運用支援**
- **統合管理CLI**: dev_check・ops_monitor・自動レポート生成
- **ビジュアルナビゲーション**: 頻繁参照最適化・最新リンク対応
- **CI/CD本番稼働**: GitHub Actions・品質ゲート・自動デプロイ

---

**🎯 Phase 13完了**: sklearn警告解消・スクリプト統合（9→5フォルダ）・重複コード500行削除・306テスト100%成功・58.88%カバレッジ・統合分析基盤確立・品質保証完成により、保守性と運用効率を大幅向上させた個人向けAI自動取引システムを完成しました 🚀

**個人開発最適化と企業級品質を兼ね備えた次世代AI自動取引システム**