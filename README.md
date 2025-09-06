# 🚀 Crypto-Bot - AI自動取引システム

**個人向け攻撃的AI自動取引システム（2025年9月 Phase 19+攻撃的設定完成・MLOps基盤確立）**

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://python.org) [![Status](https://img.shields.io/badge/status-Phase%2019%2B%20Aggressive%20Complete-success)](CLAUDE.md) [![Tests](https://img.shields.io/badge/tests-625%20passed%20100%25-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-58.64%25-green)](coverage-reports/) [![Quality](https://img.shields.io/badge/Quality%20Gate-PASS-success)](scripts/testing/checks.sh) [![MLOps](https://img.shields.io/badge/MLOps-Automated-blue)](.github/workflows/model-training.yml) [![Trading](https://img.shields.io/badge/trading-100--200%2Fmonth-orange)](config/core/thresholds.yaml)

---

## 🎯 システム概要

**Phase 19+攻撃的設定完成・特徴量定義一元化・攻撃的戦略ロジック実装・Dynamic Confidence完成**により、12特徴量統一管理・Git情報追跡・週次自動学習・**月100-200取引対応攻撃的戦略システム**を実現したMLOps基盤確立の実用的攻撃的AI自動取引システムです。

### **✅ 現在の状況（Phase 19+攻撃的設定完成）**
- **攻撃的MLOps基盤**: 特徴量統一管理・攻撃的戦略ロジック・Dynamic Confidence・Git追跡・自動アーカイブ・週次再学習**完全確立**
- **攻撃的取引システム**: **月100-200取引対応**・ATRBased不一致取引・MochipoyAlert 1票取引・1万円運用最適化
- **品質保証**: 625テスト100%成功・58.64%カバレッジ・攻撃的設定対応・回帰防止完備
- **本番運用**: Cloud Run 24時間攻撃的稼働・Discord監視・攻撃的自動取引継続
- **開発環境**: Python 3.13・JST対応・3段階CI/CD統合

## 🌟 主要特徴

### **🤖 攻撃的AI取引システム・MLOps基盤**
- **12特徴量統一管理**: feature_manager.py一元管理・feature_order.json単一真実源
- **4攻撃的戦略統合**: ATR不一致取引・もちぽよ1票取引・MTF攻撃的・フィボナッチ戦略・12特徴量対応
- **Dynamic Confidence**: HOLD固定0.5問題解決・市場ボラティリティ連動・0.1-0.8動的変動
- **攻撃的設定システム**: 月100-200取引対応・信頼度攻撃化・リスク管理攻撃化・ポジション拡大
- **ProductionEnsemble**: 3モデル統合・Git情報追跡・自動アーカイブ対応
- **週次自動学習**: model-training.yml・手動実行対応・品質検証統合

### **🔧 攻撃的品質保証・CI/CD統合体制**
- **625テスト100%成功**: 全機能・攻撃的設定対応・エラーケース・統合テスト完備
- **58.64%カバレッジ**: 継続監視・新機能での向上・企業級品質
- **3段階CI/CD**: ci.yml（攻撃的品質・デプロイ）・model-training.yml（週次学習）・cleanup.yml（月次掃除）
- **バージョン管理**: Git追跡・詳細メタデータ・自動アーカイブ・品質担保

### **⚡ 運用効率・MLOps自動化**
- **24時間自動取引**: Cloud Run・自動スケーリング・ヘルスチェック
- **Discord監視**: 3階層通知・リアルタイムアラート・運用状況確認
- **設定統一管理**: 特徴量定義一元化・ハードコード完全排除・保守性向上
- **モデル運用自動化**: 週次再学習・Git情報追跡・履歴管理・品質保証

## 🚀 クイックスタート

### **📋 前提条件**
```bash
# Python 3.11以降 (推奨: 3.13)
python3 --version

# 依存関係インストール
pip install -r requirements.txt
```

### **🎮 基本実行**
```bash
# ペーパートレード（安全・推奨）
python3 main.py --mode paper

# 本番取引（十分な検証後のみ）
python3 main.py --mode live

# バックテスト実行
python3 main.py --mode backtest
```

### **🔍 システム確認**
```bash
# 品質チェック（開発時推奨）
bash scripts/testing/checks.sh                    # 654テスト・約30秒

# システム状態確認
python3 scripts/testing/dev_check.py validate  # 設定・整合性チェック

# 本番環境確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
```

## 🏗️ システム構成

### **📊 データフロー（Phase 19 MLOps対応）**
```
市場データ取得 → 特徴量統一管理 → AI予測(4戦略) → リスク評価 → 取引実行・Discord通知
   ↓              ↓                ↓              ↓            ↓
Bitbank API   feature_manager.py  StrategyManager  RiskManager  TradingExecutor
(4h/15m足)    (12特徴量統一)     (統合判定)      (Kelly基準)  (自動取引)
   ↓              ↓                
週次自動学習   Git情報追跡       
model-training.yml  (メタデータ管理)
```

### **🎯 主要技術スタック（MLOps強化）**
- **言語**: Python 3.13・asyncio・型注釈
- **AI/ML**: ProductionEnsemble・LightGBM・XGBoost・RandomForest・Git追跡
- **MLOps**: 週次自動学習・バージョン管理・アーカイブ機能・品質検証
- **取引所API**: Bitbank・信用取引対応・レート制限対応
- **インフラ**: Google Cloud Run・Secret Manager・Cloud Logging
- **監視**: Discord Webhooks・3階層通知・リアルタイムアラート
- **品質**: pytest・654テスト・59.24%カバレッジ・3段階CI/CD自動化

### **📁 システム構造**
```
src/
├── core/              # 基盤システム（設定・ログ・例外・ML統合）
├── features/          # 特徴量生成（FeatureGenerator・12特徴量）
├── strategies/        # 取引戦略（4戦略・統合判定）
├── ml/                # 機械学習（ProductionEnsemble・モデル管理）
├── data/              # データ取得（Bitbank API・キャッシュ）
├── trading/           # 取引実行（リスク管理・注文処理）
├── backtest/          # バックテスト（性能評価・統計分析）
└── monitoring/        # 監視・通知（Discord・アラート）
```

## 📊 品質・運用実績

### **🎯 品質指標**
- **テスト**: 654テスト100%成功・59.24%カバレッジ・回帰防止完備
- **コード品質**: flake8・black・isort通過・型注釈・JST対応
- **CI/CD**: GitHub Actions・自動品質ゲート・30秒高速実行
- **設定管理**: ハードコード完全排除・階層化設定・保守性向上

### **⚙️ 運用状況**
- **稼働率**: 24時間連続稼働・Cloud Run自動スケーリング
- **監視体制**: Discord通知・3階層アラート・異常検知
- **データ処理**: 4h/15m足取得・12特徴量生成・リアルタイム分析
- **取引実行**: Kelly基準リスク管理・自動ポジション管理

## 🛠️ 開発・サポート

### **📚 ドキュメント**
- **開発者ガイド**: [CLAUDE.md](CLAUDE.md) - システム詳細・開発手順
- **設定管理**: [config/README.md](config/README.md) - 設定システム
- **テスト仕様**: [tests/README.md](tests/README.md) - テスト構成・品質基準

### **🔧 開発コマンド**
```bash
# 開発環境セットアップ
pip install -r requirements.txt
python3 scripts/ml/create_ml_models.py --verbose

# コード品質チェック
bash scripts/testing/checks.sh              # 全品質チェック
python3 -m pytest tests/ -v                 # 個別テスト実行
python3 -m flake8 src/                      # コード品質確認

# 本番デプロイ準備
git add . && git commit -m "feat: 機能追加"
git push origin main                         # CI/CD自動実行
```

### **📞 サポート・問題解決**
- **システム状態確認**: `bash scripts/testing/checks.sh`
- **設定問題**: `python3 scripts/testing/dev_check.py validate`
- **本番環境**: `gcloud run services describe crypto-bot-service-prod`
- **詳細ガイド**: [CLAUDE.md](CLAUDE.md)のトラブルシューティング参照

## 🎉 システム成果（Phase 19完了）

**✅ 特徴量定義一元化完了**: feature_manager.py統一管理・feature_order.json単一真実源・12特徴量完全統一により、モデル互換性確保・保守性向上達成

**✅ バージョン管理システム改良**: Git情報追跡・自動アーカイブ・詳細メタデータ管理により、品質トレーサビリティ・履歴管理・障害対応力強化達成

**✅ 定期再学習CI完成**: model-training.yml週次自動実行・手動実行対応・品質検証統合により、MLOps基盤確立・運用自動化達成

**✅ 企業級品質保証継続**: 654テスト100%・59.24%カバレッジ・3段階CI/CD統合により、品質保証・開発効率・運用安定性確保達成

---

**🚀 Phase 19完了・MLOps基盤確立**: 2025年9月4日現在・特徴量定義一元化・バージョン管理システム改良・定期再学習CI完成により、12特徴量統一管理・Git情報追跡・週次自動学習・企業級品質保証を実現したMLOps基盤確立の実用的AI自動取引システムが稼働継続** 🎯

**最終更新**: 2025年9月4日 - Phase 19完了・特徴量定義一元化・バージョン管理システム改良・定期再学習CI完成・MLOps基盤確立