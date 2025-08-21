# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 最重要：開発状況（2025年8月21日現在）

### **🚀 Phase 12完了 - CI/CD全8回修正完了・Secret Manager統合・本番運用準備完了**

**プロジェクト概要**: 
- **目標**: 個人向けAI自動取引システムの完成（保守性・安定性・品質重視）
- **方針**: レガシーシステム（56,355行）→新システム（完全リファクタリング完了）
- **現状**: **Phase 12完了** - CI/CD全8回修正完了・Secret Manager統合・本番運用準備完了

**完了システム状況**: 
```
✅ Phase 1-12: 全フェーズ完了 - 基盤→データ→特徴量→戦略→ML→リスク→実行→バックテスト→運用→CI/CD全修正
🎯 316テスト・68.13%カバレッジ - 品質保証体制確立・CI/CD統合検証追加
📊 CI/CD全8回修正完了: 全根本原因解決・Secret Manager統合・構文修正・本番運用準備
🔧 品質最適化: flake8エラー54%削減（1,184→538）継続中
📁 完全ドキュメント化: 25個README完備（src/18個・scripts/7個・包括的ガイド追加）
```

### **🏆 Phase 12最新成果（2025年8月21日完成）**

**CI/CD全8回修正完了実績**:
- **全根本原因解決**: 環境変数・認証・Artifact Registry・ファイルパス・構文・Secret Manager統合
- **Secret Manager完全統合**: bitbank-api-key・bitbank-api-secret・discord-webhook-url正常動作
- **本番運用準備完了**: Workload Identity・段階的デプロイ・稼働確実性達成

**GCP CI/CD改善システム**:
- **verify_gcp_setup.sh**: CI/CD実行前の包括的環境検証・レガシーエラーパターン網羅・4モード対応
- **setup_ci_prerequisites.sh**: ワンクリック環境構築・自動修復・対話式セットアップ
- **統合設定管理**: config/ci/gcp_config.yaml・一元管理・環境別設定・レガシー継承

**自動診断・修復システム**:
- **事前問題検出**: CI/CD実行前の全前提条件チェック・デプロイ失敗防止
- **自動修復機能**: 軽微なGCP設定問題の自動解決・手動介入最小化
- **統合エラーハンドリング**: 診断フローチャート・解決手順・関連ドキュメント自動提示

**包括的ドキュメント体系**:
- **GCP事前設定ガイド**: 初回セットアップ完全手順・トラブルシューティング統合
- **CI/CD設定ガイド強化**: エラーハンドリングフローチャート・自動診断システム詳細
- **deployment README統合**: 新機能詳細・統合ワークフロー・レガシー改良点体系化

### **📂 システム構造**

```
src/                    # 新システム（18個README完備）
├── core/              # 基盤システム（設定管理・ログ・例外処理・統合制御）
├── data/              # データ層（Bitbank API・パイプライン・キャッシュ）
├── features/          # 特徴量（テクニカル指標12個・異常検知）
├── strategies/        # 戦略システム（4戦略・113テスト）
├── ml/                # 機械学習（アンサンブル・89テスト・本番モデル）
├── backtest/          # バックテスト（エンジン・評価・84テスト）
├── trading/           # 取引実行（リスク管理・Kelly基準・113テスト）
└── monitoring/        # 監視（Discord通知・3階層）

scripts/                # 運用スクリプト（25個README完備・Phase 12 GCP CI/CD改善対応）
├── management/        # 統合管理CLI（dev_check.py・6機能統合）
├── quality/           # 品質チェック（316テスト・flake8・isort・black）
├── analytics/         # 統合分析基盤（base_analyzer.py・重複500行削除）
├── data_collection/   # 実データ収集（統計分析・TradingStatisticsManager）
├── ab_testing/        # A/Bテスト（統計的検定・p値計算）
├── dashboard/         # ダッシュボード（HTML可視化・Chart.js）
├── ml/               # MLモデル作成（12特徴量・アンサンブル）
├── deployment/       # デプロイ（GCP CI/CD改善・自動診断・統合設定管理）⭐Phase 12強化
└── testing/          # ライブトレードテスト

config/ci/             # CI/CD統合設定（Phase 12新設）⭐
└── gcp_config.yaml    # GCP統合設定・環境別管理・レガシー継承

docs/CI-CD設定/        # CI/CD包括的ガイド（Phase 12強化）⭐
├── GCP事前設定ガイド.md          # 初回セットアップ完全手順
└── CI-CD設定・デプロイメントガイド.md # エラーハンドリング・自動診断統合

logs/                   # ログ・レポート（9個README完備・Phase 12レポート機能）
├── dev_check_reports/     # CI前チェック結果
├── ops_monitor_reports/   # CI後チェック結果
├── backtest_reports/      # バックテストレポート
├── paper_trading_reports/ # ペーパートレードセッション
├── operational_reports/   # JSON形式運用診断
├── operational_status/    # キャッシュ・デバッグデータ
├── state/                # 状態管理（ドローダウン・ヘルス・監視・セキュリティ）
└── trading/              # 取引ログ（316テスト実績）
```

## 🔧 開発ワークフロー

### **統合管理CLI（推奨）**
```bash
# 注意: 環境によってはpython3コマンドが必要
# CI前チェック（開発時）
python3 scripts/management/dev_check.py full-check     # 6段階統合チェック
python3 scripts/management/dev_check.py validate       # 軽量品質チェック  
python3 scripts/management/dev_check.py ml-models      # MLモデル作成・検証

# CI後チェック（デプロイ後）
python3 scripts/management/ops_monitor.py              # 運用診断・4フェーズ確認

# 期待結果: ✅ すべてのチェックに合格・レポート自動保存（logs/配下）
```

### **GCP CI/CD改善システム（⭐ Phase 12新機能）**
```bash
# GCP環境検証・準備
bash scripts/deployment/verify_gcp_setup.sh --full     # 包括的環境検証
bash scripts/deployment/setup_ci_prerequisites.sh --interactive  # 自動セットアップ

# 問題修復・メンテナンス
bash scripts/deployment/verify_gcp_setup.sh --ci       # CI実行前検証
bash scripts/deployment/setup_ci_prerequisites.sh --repair      # 自動修復

# 期待結果: ✅ GCP環境準備完了・CI/CD失敗率90%削減・デプロイ成功
```

### **システム実行**
```bash
# メインシステム（環境によってはpython3を使用）
python3 main.py --mode paper     # ペーパートレード（推奨・安全確認）
python3 main.py --mode backtest  # バックテスト（過去データ検証）
python3 main.py --mode live      # ライブトレード（本番取引）

# 統合分析（Phase 12新機能）  
python3 scripts/data_collection/trading_data_collector.py --hours 24  # 実データ収集
python3 scripts/ab_testing/simple_ab_test.py --hours 24               # A/Bテスト
python3 scripts/dashboard/trading_dashboard.py --discord              # ダッシュボード
```

### **品質チェック**
```bash
# 品質チェック（推奨）
bash scripts/quality/checks.sh                        # 316テスト・flake8・isort・black

# 手動テスト
python3 tests/manual/test_phase2_components.py         # データ層基盤確認
```

## 🎯 開発原則・方針

### **🚨 重要：README.md優先原則**
**各フォルダ作業前に必ずREADME.mdを読む**:
- **目的・設計原則**: そのディレクトリの責任範囲を理解
- **既存構成**: ファイル構成・命名規則を把握  
- **実装方針**: コーディング標準・パターンを確認

**31個README完備**: src/18個・scripts/4個・logs/9個

### **品質保証原則**
- **316テスト・68.13%カバレッジ維持**: 新機能追加時も全合格維持
- **高速実行**: 全テスト約25秒以内完了
- **統合確認**: エンドツーエンド動作・base_analyzer.py基盤品質保証

### **個人開発最適化**
- **シンプル性**: 個人が理解・保守可能な実装
- **実用性**: 実際の取引に必要な機能のみ
- **コスト効率**: 月額2,000円以内運用

## 💻 技術仕様

### **設計原則**
- **レイヤードアーキテクチャ**: 各層の責任明確分離・疎結合
- **エラーハンドリング階層化**: カスタム例外・適切なエラー管理
- **設定外部化**: 環境変数・YAML分離

### **データフロー**
```
📊 data → 🔢 features → 🎯 strategies → 🤖 ml → 💼 trading → 📡 monitoring
                                       ↓
📊 backtest → 📈 analytics → 📊 data_collection → 🎨 dashboard
```

### **成功指標（Phase 12達成）**
- **品質保証**: 316テスト・68.13%カバレッジ・統合分析基盤対応
- **保守性**: 重複コード500行削除・base_analyzer.py基盤・統一インターフェース  
- **性能**: バックテスト30-50%高速化・Cloud Runログ取得効率化

## 🚨 トラブルシューティング

### **よくある問題**

**1. インポートエラー**
```bash
# プロジェクトルートから実行（python3使用）
cd /Users/nao/Desktop/bot
python3 -m pytest tests/unit/ -v
```

**2. テスト失敗**
```bash
# 個別テスト実行で問題特定
python3 -m pytest tests/unit/strategies/test_atr_based.py -v -s
python3 -m pytest tests/unit/ml/test_ensemble_model.py -v -s
```

**3. バックテストエラー**
```bash
# バックテストシステム確認
python3 -c "from src.backtest.engine import BacktestEngine; print('✅ OK')"
```

**4. 品質チェックエラー**
```bash
# 軽量品質チェック（推奨）
bash scripts/quality/checks_light.sh

# 完全品質チェック
bash scripts/quality/checks.sh
```

## 📋 重要ファイル

- **src/**: 新システム実装（18個README完備）
- **scripts/**: 運用スクリプト（22個README・base_analyzer.py基盤）
- **tests/**: 316テスト・68.13%品質保証環境
- **logs/**: レポート・状態管理（9個README・Phase 12レポート機能）
- **config/**: 設定管理（production.yaml含む）

---

**🎯 Phase 12完了**: 統合分析基盤・重複コード500行削除・レポート生成機能・CI/CD統合・手動実行監視により、保守性と運用効率を大幅向上させた個人向けAI自動取引システムを完成