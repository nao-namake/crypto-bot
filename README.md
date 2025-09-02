# 🚀 Crypto-Bot - AI自動取引システム

**個人向けAI自動取引システム（2025年9月 完全稼働中）**

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://python.org) [![Status](https://img.shields.io/badge/status-Fully%20Operational-success)](CLAUDE.md) [![Tests](https://img.shields.io/badge/tests-654%20passed%20100%25-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-59.24%25-green)](coverage-reports/) [![Quality](https://img.shields.io/badge/Quality%20Gate-PASS-success)](scripts/testing/checks.sh)

---

## 🎯 システム概要

**FeatureGenerator問題解決完了・システム機能完全復旧達成**により、12特徴量→4戦略→取引判断フローが完全稼働中の実用的AI自動取引システムです。

### **✅ 現在の状況**
- **機能状態**: FeatureGenerator→戦略→取引フロー **完全稼働**
- **品質保証**: 654テスト100%成功・59.24%カバレッジ・回帰防止完備
- **本番運用**: Cloud Run 24時間稼働・Discord監視・自動取引継続
- **開発環境**: Python 3.13・JST対応・CI/CD安定動作

## 🌟 主要特徴

### **🤖 AI取引システム**
- **12特徴量生成**: テクニカル指標・異常検知・マルチタイムフレーム対応
- **4戦略統合**: ATR・もちぽよアラート・MTF・フィボナッチ戦略
- **ProductionEnsemble**: 3モデル統合・高精度予測・フォールバック対応
- **リスク管理**: Kelly基準・ポジションサイジング・自動停止機能

### **🔧 品質保証体制**
- **654テスト100%成功**: 全機能・エラーケース・統合テスト完備
- **59.24%カバレッジ**: 継続監視・新機能での向上・企業級品質
- **CI/CD自動化**: GitHub Actions・品質ゲート・段階的デプロイ
- **JST対応ログ**: 構造化ログ・Discord通知・運用監視

### **⚡ 運用効率**
- **24時間自動取引**: Cloud Run・自動スケーリング・ヘルスチェック
- **Discord監視**: 3階層通知・リアルタイムアラート・運用状況確認
- **設定統一管理**: ハードコード完全排除・階層化設定・保守性向上
- **開発環境統一**: ローカル=CI環境・高速品質チェック・30秒実行

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
python3 scripts/management/dev_check.py validate  # 設定・整合性チェック

# 本番環境確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
```

## 🏗️ システム構成

### **📊 データフロー**
```
市場データ取得 → 特徴量生成(12個) → AI予測(4戦略) → リスク評価 → 取引実行・Discord通知
   ↓              ↓                ↓              ↓            ↓
Bitbank API   FeatureGenerator  StrategyManager  RiskManager  TradingExecutor
(4h/15m足)    (DataFrame出力)   (統合判定)      (Kelly基準)  (自動取引)
```

### **🎯 主要技術スタック**
- **言語**: Python 3.13・asyncio・型注釈
- **AI/ML**: ProductionEnsemble・LightGBM・XGBoost・RandomForest
- **取引所API**: Bitbank・信用取引対応・レート制限対応
- **インフラ**: Google Cloud Run・Secret Manager・Cloud Logging
- **監視**: Discord Webhooks・3階層通知・リアルタイムアラート
- **品質**: pytest・654テスト・59.24%カバレッジ・CI/CD自動化

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
- **設定問題**: `python3 scripts/management/dev_check.py validate`
- **本番環境**: `gcloud run services describe crypto-bot-service-prod`
- **詳細ガイド**: [CLAUDE.md](CLAUDE.md)のトラブルシューティング参照

## 🎉 システム成果

**✅ FeatureGenerator問題解決完了**: 12特徴量→戦略フロー復旧・DataFrame出力対応・マルチタイムフレーム対応により、システム機能完全復旧達成

**✅ 品質保証体制確立**: 654テスト100%成功・21テストケース追加・59.24%カバレッジ・CI/CD自動化により、企業級品質保証継続

**✅ 本番安定稼働**: Cloud Run 24時間稼働・Discord監視・自動取引継続・JST対応により、実用的AI自動取引システム稼働中

---

**🚀 システム完全稼働中**: 2025年9月3日現在・FeatureGenerator問題解決・654テスト100%・本番24時間稼働により、品質保証・機能完全性・運用安定性を確保した実用的AI自動取引システムが稼働継続** 🎯

**最終更新**: 2025年9月3日 - システム機能完全復旧・品質保証継続・本番安定稼働