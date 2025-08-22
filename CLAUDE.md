# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 最重要：開発状況（2025年8月22日現在）

### **🚀 Phase 13完了・本番モード移行・システム最適化・GCP環境整備完了**

**プロジェクト概要**: 
- **目標**: 個人向けAI自動取引システムの完成・本番運用準備完了
- **方針**: レガシーシステム（56,355行）→新システム（完全リファクタリング・クリーンアーキテクチャ）
- **現状**: **Phase 13完了・本番モード（live）完全移行・システム最適化・GCPリソースクリーンアップ・CI/CD本番稼働準備完了**

**最終完了状況**: 
```
✅ Phase 1-13: 全フェーズ完了・基盤→データ→ML→戦略→リスク→実行→CI/CD→品質保証→本番運用最適化
🎯 本番モード（live）完全移行・全エラー解決・システム最適化・本番運用準備100%完了
📊 GCP環境整備: Cloud Run本番稼働・リソースクリーンアップ・設定最適化・認証強化
🗂️ 設定統合: MarketAnomalyDetector統一・Config型修正・パス整合性確保・本番設定刷新
📁 完全最適化: src/構造確認・スクリプトパス統一・production.yaml刷新・CI/CD準備完了
```

### **🏆 Phase 13最終成果（2025年8月22日）**

**本番運用システム完全移行**:
- **ライブモード移行**: base.yaml・Dockerfile・CI/CD・Cloud Run全環境本番モード化
- **GCP環境最適化**: Cloud Run本番稼働・古いリソース削除・設定最適化・認証強化
- **本番設定完成**: production.yaml刷新・セキュリティ強化・パフォーマンス最適化

**システム統合・エラー完全解決**:
- **インポートエラー解決**: MarketAnomalyDetector統一・__init__.py修正・全参照更新
- **Config型修正**: to_dict()メソッド追加・IntegratedRiskManager対応・型安全性確保
- **パス整合性確保**: quality/→testing/移行・スクリプトパス統一・参照修正完了

**構造最適化・品質保証完成**:
- **src/構造確認**: 重複なし・適切設計確認・個人開発最適化済み
- **GCPリソースクリーンアップ**: 古いリビジョン・イメージ削除・ログ整理・環境整備
- **全システム検証**: パス整合性・動作確認・本番運用準備100%完了

### **📂 システム構造（Phase 13最終版・統合最適化完了）**

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

config/                  # 設定管理（階層化・Phase 13整理完了）
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

## 🔧 開発ワークフロー（Phase 13最終版・統合最適化対応）

### **統合管理CLI（推奨・Phase 13統合対応）**
```bash
# CI前チェック（開発時・統合管理）
python3 scripts/management/dev_check.py full-check     # 6段階統合チェック
python3 scripts/management/dev_check.py validate       # 軽量品質チェック
python3 scripts/management/dev_check.py ml-models      # MLモデル作成・検証

# CI後チェック（デプロイ後・統合管理）
python3 scripts/management/dev_check.py operational    # 運用診断・稼働状況確認（統合）

# 統合分析基盤（Phase 13新機能）
python3 scripts/analytics/data_collector.py --hours 24 # 実データ収集
python3 scripts/analytics/dashboard.py --discord       # ダッシュボード生成
python3 scripts/analytics/performance_analyzer.py      # パフォーマンス分析

# 期待結果: ✅ 306テスト100%成功・sklearn警告解消・統合分析基盤活用
```

### **統合分析・レポート確認（Phase 13統合対応）**
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

### **システム実行（本番対応・sklearn警告解消済み）**
```bash
# メインシステム（python3統一・sklearn警告解消済み）
python3 main.py --mode paper    # ペーパートレード
python3 main.py --mode backtest # バックテスト
python3 main.py --mode live     # ライブトレード（本番）

# 期待結果: sklearn警告なし・306テスト対応・安定動作・レポート自動生成
```

### **品質チェック（Phase 13統合対応）**
```bash
# 統合品質チェック（306テスト・sklearn警告解消対応）
bash scripts/testing/checks.sh                         # 統合チェック（約30秒）

# 統合管理CLI経由（推奨）
python3 scripts/management/dev_check.py validate       # 軽量品質チェック

# 期待結果: ✅ 306テスト100%・sklearn警告なし・flake8・black・isort統合チェック
```

## 🎯 開発原則・方針（Phase 13完全版）

### **README.md優先原則 🚨 重要**
**各フォルダ作業前に必ずREADME.mdを読む**:
- **目的・設計原則**: そのディレクトリの責任範囲を理解
- **既存構成**: ファイル構成・命名規則を把握
- **実装方針**: コーディング標準・パターンを確認
- **Phase 13対応**: 最新状況・管理ルール・品質基準を理解

**完全README体制（Phase 13完了）**:
- **src/**: 18個README完備・各層詳細仕様・使用方法
- **scripts/**: 機能別README・統合管理・運用手順
- **config/**: 設定管理README・階層化・環境別設定
- **models/**: Phase 13対応README・ファイル管理ルール・品質保証

### **統合管理原則（Phase 13確立）**
**logs/reports/統合管理システム**:
- ✅ **ビジュアルナビゲーション**: INDEX.mdで絵文字分類・頻繁参照最適化
- ✅ **CI前後統合**: dev_check・ops_monitor新パス対応・動作確認済み
- ✅ **最新リンク**: シンボリックリンクで最新レポート高速アクセス
- ✅ **統一構造**: ci_checks/・trading/・operational/階層化完了

### **品質保証原則（Phase 13完成）**
**306テスト・100%合格維持**:
- ✅ **sklearn警告解消**: 全deprecation warning解消・最新ライブラリ対応
- ✅ **回帰防止**: 新機能追加時も既存テスト全合格維持
- ✅ **包括的カバレッジ**: 正常系・異常系・エラーハンドリング・58.88%カバレッジ
- ✅ **高速実行**: 全テスト約25秒以内での完了

### **models/管理原則（Phase 13確立）**
**ファイル管理ルール・品質保証**:
- ✅ **production/**: 本番用ProductionEnsemble・メタデータ・レガシー削除完了
- ✅ **training/**: 個別モデル・学習メタデータ・性能指標最新化
- ✅ **品質基準**: sklearn警告解消・F1スコア基準・12特徴量対応
- ✅ **管理ルール**: 命名規則・Phase情報記録・Git LFS対応

## 💻 技術仕様・アーキテクチャ（Phase 13最終版）

### **設計原則**
- **レイヤードアーキテクチャ**: 各層の責任明確分離・疎結合
- **統合管理**: logs/reports/統合・models/整理・config/最適化
- **エラーハンドリング階層化**: カスタム例外・適切なエラー管理
- **設定外部化**: 環境変数・YAML分離・階層化設定管理

### **成功指標（Phase 13達成）**
- **品質保証**: 306テスト100%合格・sklearn警告解消・包括的カバレッジ達成
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・頻繁参照最適化
- **models/整理**: Phase 13対応・レガシー削除・ファイル管理ルール確立
- **構成最適化**: config/gcp/統合・coverage-reports/管理・設定階層化

### **データフロー（Phase 13完了・統合最適化）**
```
📊 src/data/ → Bitbank API・マルチタイムフレーム・キャッシュ
    ↓
🔢 src/features/ → テクニカル指標12個厳選・異常検知
    ↓  
🎯 src/strategies/ → 4戦略統合・シグナル生成（113テスト100%）
    ↓
🤖 src/ml/ → ProductionEnsemble・sklearn警告解消（89テスト100%）
    ↓
📊 src/backtest/ → 性能評価・統計分析（84テスト100%）
    ↓
💼 src/trading/ → リスク管理・注文実行（113テスト100%）
    ↓
📡 src/monitoring/ → Discord通知・システム監視
    ↓
📋 logs/reports/ → 統合レポート・ビジュアルナビゲーション・頻繁参照最適化
    ↓
🎯 models/ → Phase 13対応・ProductionEnsemble最新化・ファイル管理ルール確立
```

## 🚨 トラブルシューティング（Phase 13対応）

### **よくある問題**
**1. インポートエラー・sklearn警告**
```bash
# プロジェクトルートから実行（python3統一）
cd /Users/nao/Desktop/bot
python3 -m pytest tests/unit/ -v
# 期待結果: sklearn警告なし・306テスト100%成功
```

**2. レポート・ログ確認**
```bash
# 統合レポートナビゲーション確認
cat logs/reports/INDEX.md
# 最新レポート確認
ls -la logs/reports/*/latest/
# 期待結果: ビジュアルナビゲーション・最新リンク機能
```

**3. models/管理問題**
```bash
# models/ディレクトリ状態確認
ls -la models/production/  # production_ensemble.pkl・production_model_metadata.json
ls -la models/training/    # 3個別モデル・training_metadata.json
# 期待結果: レガシーファイルなし・Phase 13対応メタデータ
```

**4. 品質チェック（sklearn警告解消確認）**
```bash
# sklearn警告解消確認
python3 scripts/ml/create_ml_models.py --verbose
# 期待結果: Warning表示なし・最新API使用・Phase 13対応
```

## 📋 ファイル管理・構成（Phase 13最終版）

### **重要ディレクトリ（Phase 13統合最適化完了）**
- **src/**: 新システム実装（18個README完備）・306テスト対応
- **logs/reports/**: 統合レポート管理・ビジュアルナビゲーション・頻繁参照最適化
- **scripts/**: 運用スクリプト（統合パス対応）・機能別整理
- **models/**: Phase 13対応・レガシー削除・ファイル管理ルール確立
- **config/**: 設定管理階層化・gcp/統合・deployment/整理

### **レガシーシステム（参考用）**
- **_legacy_v1/**: 56,355行旧システム（参考のみ・コピペ禁止）

### **🎉 Phase 13最終完了成果（2025年8月22日）**

**統合最適化・品質保証完成指標**:
- **306テスト100%成功**: sklearn警告解消・ML処理安定化・回帰防止・品質保証完成
- **logs/reports/統合**: ビジュアルナビゲーション・頻繁参照最適化・CI前後チェック統合
- **models/完全整理**: Phase 13対応・レガシー削除・ファイル管理ルール・品質保証確立
- **config/最適化**: gcp/統合・deployment/整理・設定階層化・管理強化

**統合管理システム実績**:
- **統合レポート管理**: logs/reports/統合・INDEX.mdビジュアルナビゲーション・最新リンク対応
- **スクリプトパス統合**: dev_check・ops_monitor新パス対応・動作確認完了・レポート自動保存
- **models/品質保証**: ProductionEnsemble最新化・個別モデル性能確認・sklearn警告解消・管理ルール確立
- **22個README完備**: src/・scripts/・config/・models/完全ドキュメント化・運用手順・品質基準

**技術成果**:
- **sklearn警告解消**: 全deprecation warning解消・最新ライブラリ対応・型安全性向上・互換性確保
- **統合アーキテクチャ**: logs/reports/統合・models/整理・config/最適化・一元管理実現
- **品質保証体制**: 306テスト・58.88%カバレッジ・CI/CD本番稼働・継続的品質管理
- **運用効率化**: ビジュアルナビゲーション・頻繁参照最適化・統合管理CLI・自動化推進

---

**🎉 Phase 13完了成果**: *sklearn警告解消・logs統合・models整理・config最適化・306テスト100%成功・58.88%カバレッジ・ビジュアルナビゲーション・統合管理により、品質保証と運用効率を大幅向上させた個人向けAI自動取引システムを完成* 🚀

*統合最適化・品質保証完成・CI/CD本番稼働・レガシー知見活用・実用性重視を重視した個人開発最適化アーキテクチャ*