# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 最重要：開発状況（2025年8月20日現在）

### **🚀 Phase 12完了 - 統合分析基盤・レポート生成・本番運用システム完成**

**プロジェクト概要**: 
- **目標**: 個人向けAI自動取引システムの完成（保守性・安定性・品質重視）
- **方針**: レガシーシステム（56,355行）→新システム（完全リファクタリング完了）
- **現状**: **Phase 12完了** - 統合分析基盤・重複コード削除・レポート生成機能・本番運用準備完了

**完了システム状況**: 
```
✅ Phase 1-12: 全フェーズ完了 - 基盤→データ→特徴量→戦略→ML→リスク→実行→バックテスト→運用→CI/CD
🎯 316テスト・68.13%カバレッジ - 品質保証体制確立
📊 統合分析基盤: base_analyzer.py・重複コード500行削除・4種レポート生成機能
🔧 品質最適化: flake8エラー54%削減（1,184→538）継続中
📁 完全ドキュメント化: 22個README完備（src/18個・scripts/4個・logs/9個）
```

### **🏆 Phase 12主要成果**

**統合分析基盤完成**:
- **base_analyzer.py基盤**: 共通Cloud Runログ取得・重複コード500行削除・4スクリプト統合
- **レポート生成機能**: dev_check・ops_monitor・backtest・paper_trading自動レポート保存
- **実データ収集**: trading_data_collector.py・A/Bテスト・ダッシュボード統合

**CI/CD・運用システム強化**:
- **GitHub Actions**: Secret Manager統合・セキュリティ強化・段階的デプロイ対応
- **手動実行監視**: monitoring.yml・パフォーマンス分析・自動アラート
- **品質保証体制**: 316テスト・68.13%カバレッジ・統合チェック自動化

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

scripts/                # 運用スクリプト（22個README完備）
├── management/        # 統合管理CLI（dev_check.py・6機能統合）
├── quality/           # 品質チェック（316テスト・flake8・isort・black）
├── analytics/         # 統合分析基盤（base_analyzer.py・重複500行削除）
├── data_collection/   # 実データ収集（統計分析・TradingStatisticsManager）
├── ab_testing/        # A/Bテスト（統計的検定・p値計算）
├── dashboard/         # ダッシュボード（HTML可視化・Chart.js）
├── ml/               # MLモデル作成（12特徴量・アンサンブル）
├── deployment/       # デプロイ（GCP Cloud Run・Docker）
└── testing/          # ライブトレードテスト

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
# 軽量チェック（推奨・日常）
bash scripts/quality/checks_light.sh                  # 高速チェック

# 完全チェック（本格確認）
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