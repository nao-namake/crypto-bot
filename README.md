# Crypto-Bot - 🚀 AI自動取引システム

**個人向けAI自動取引システム（Phase 13.6 緊急対応完了・本番安定稼働中）**

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org) [![Status](https://img.shields.io/badge/status-本番安定稼働中-success)](CLAUDE.md) [![Tests](https://img.shields.io/badge/tests-400%20passed%20100%25-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-58.88%25-green)](coverage-reports/) [![Cloud Run](https://img.shields.io/badge/Cloud%20Run-24時間稼働-success)](https://console.cloud.google.com/run) [![Emergency Fix](https://img.shields.io/badge/Emergency%20Fix-完了-success)](docs/開発計画/開発履歴.md)

## 🎯 システム概要

個人向けAI自動取引システムです。**Phase 13.6 緊急対応完了により、Discord通知復旧・API認証修正・CI統合修正・400テスト100%を達成し、本番システムの安定稼働を確保しました**。

## 🎯 主要特徴

**品質保証体制**:
- ✅ **400テスト100%合格**: 戦略・ML・取引・バックテスト全領域カバー
- ✅ **58.88%カバレッジ**: 正常系・異常系・境界値テスト実装
- ✅ **CI/CD統合**: GitHub Actions自動品質チェック・自動デプロイ
- ✅ **24時間稼働**: Cloud Run本番環境・自動監視・継続運用

**技術基盤**:
- **AI戦略システム**: 4戦略統合・ProductionEnsemble・MLServiceAdapter3段階フォールバック・高精度予測
- **リスク管理**: Kelly基準・統合リスク管理・異常検知・自動停止
- **データ処理**: Bitbank API・マルチタイムフレーム・リアルタイム分析
- **監視・通知**: Discord統合・3階層アラート・状態監視

## 🛠️ 使用方法

### **基本実行**
```bash
# ペーパートレード（安全・推奨）
python3 main.py --mode paper

# 本番取引（十分な検証後のみ）
python3 main.py --mode live

# バックテスト
python3 main.py --mode backtest
```

### **開発・保守**
```bash
# 品質チェック
python3 scripts/management/dev_check.py validate

# 全テスト実行
python3 -m pytest tests/unit/ -v

# 統合分析
python3 scripts/analytics/dashboard.py --discord
```

### **CI/CD自動化**
```bash
# コードプッシュで全工程自動実行
git add .
git commit -m "feat: システム改善"
git push origin main
# → 自動: 品質チェック→ビルド→デプロイ→監視
```

## 📊 品質指標

### **システム品質**
- **テスト**: 400テスト・58.88%カバレッジ・100%合格率
- **CI/CD**: GitHub Actions自動化・3-5分実行・高成功率
- **本番環境**: Cloud Run 24時間稼働・自動監視・安定運用
- **コード品質**: flake8・black・isort統合・保守性重視

### **運用効率**
- **自動化**: 手動作業80%削減・完全CI/CD統合
- **監視**: 異常検知・Discord通知・3階層アラート
- **コスト**: GCPリソース最適化・効率運用
- **保守**: README完備・統合CLI・開発者体験向上

## 🏗️ システム概要

### **アーキテクチャ**
- **データ層**: Bitbank API接続・マルチタイムフレーム取得
- **特徴量**: テクニカル指標12種・異常検知・リアルタイム分析  
- **AI戦略**: 4戦略統合・ProductionEnsemble・MLServiceAdapter統合制御・高精度予測
- **リスク管理**: Kelly基準・統合管理・自動停止機能
- **実行層**: 取引実行・Discord通知・継続監視

### **データフロー**
```
📊 市場データ取得 → 🔢 特徴量生成 → 🤖 AI予測 → 💼 リスク評価 → 📡 取引実行・通知
```

## 🔧 サポート

### **基本確認**
```bash
# システム品質チェック
python3 scripts/management/dev_check.py validate

# 全テスト実行
python3 -m pytest tests/unit/ -v

# 統合分析ダッシュボード
python3 scripts/analytics/dashboard.py --discord
```

### **技術詳細**
- **開発者向け詳細**: [CLAUDE.md](CLAUDE.md) をご確認ください
- **各モジュール仕様**: 各フォルダ内のREADME.mdをご参照ください
- **テスト詳細**: [tests/README.md](tests/README.md) をご確認ください

---

**🚀 Phase 13.6 緊急対応完了: Discord通知復旧・API認証修正・CI統合修正・400テスト100%により、本番稼働中の全緊急問題を根本解決し、システム安定性・品質保証・継続稼働を確保した個人向けAI自動取引システム** 🎉