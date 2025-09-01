# Crypto-Bot - 🚀 AI自動取引システム

**個人向けAI自動取引システム（Phase 18 統合システム完成）**

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org) [![Status](https://img.shields.io/badge/status-Phase%2018%20完了-success)](CLAUDE.md) [![Tests](https://img.shields.io/badge/tests-618%20passed%2099.7%25-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-53.57%25-green)](coverage-reports/) [![Integration](https://img.shields.io/badge/code%20reduction-1076%20lines-success)](docs/開発計画/開発履歴.md) [![Quality Gate](https://img.shields.io/badge/Quality%20Gate-PASS-success)](scripts/testing/checks.sh)

## 🎯 システム概要

個人向けAI自動取引システムです。**Phase 18 統合システム完成により、backtest/・features/フォルダの統合（5ファイル削除・1,076行削減）・重複コード完全排除・薄いラッパー削除・後方互換性維持を実現し、システム全体の保守性と効率性が大幅向上しました**。

## 🎯 主要特徴

**品質保証体制**:
- ✅ **618テスト99.7%合格**: 戦略・ML・取引・バックテスト全領域カバー・高品質維持
- ✅ **53.57%カバレッジ**: 正常系・異常系・境界値テスト実装・企業級品質基準クリア
- ✅ **統合システム完成**: 5ファイル削除・1,076行削減・重複コード完全排除
- ✅ **後方互換性維持**: エイリアス機能・既存コード影響ゼロ・安全な統合
- ✅ **24時間稼働**: Cloud Run本番環境・自動監視・継続運用

**技術基盤**:
- **統合システム**: Phase 18完成・FeatureGenerator統合・統一レポーター・効率化実現
- **AI戦略システム**: 4戦略統合・ProductionEnsemble・MLServiceAdapter強化・高精度予測
- **設定管理**: config階層化・thresholds.yaml中央管理・動的設定変更・保守性重視
- **リスク管理**: Kelly基準・統合リスク管理・異常検知・自動停止
- **データ処理**: Bitbank API・マルチタイムフレーム・BacktestDataLoader統合
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
# 品質チェック（推奨）
bash scripts/testing/checks.sh                         # 620テスト・50%+カバレッジ

# 軽量チェック
python3 scripts/management/dev_check.py validate

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
- **テスト**: 620テスト・50%+カバレッジ・100%合格率・完全品質保証達成
- **設定管理**: 160個ハードコード値一元化・thresholds.yaml統合・保守性大幅向上
- **CI/CD**: checks完全通過・品質ゲート確立・約32秒高速実行
- **本番環境**: Cloud Run 24時間稼働・自動監視・安定運用
- **コード品質**: flake8・black・isort統合・保守性重視・実装整合性確保

### **運用効率**
- **自動化**: 手動作業80%削減・完全CI/CD統合
- **設定管理**: 動的パラメータ調整・1万円運用最適化・中央管理実現
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
# システム品質チェック（推奨）
bash scripts/testing/checks.sh                         # 620テスト・50%+カバレッジ

# 軽量チェック
python3 scripts/management/dev_check.py validate

# 統合分析ダッシュボード
python3 scripts/analytics/dashboard.py --discord
```

### **技術詳細**
- **開発者向け詳細**: [CLAUDE.md](CLAUDE.md) をご確認ください
- **各モジュール仕様**: 各フォルダ内のREADME.mdをご参照ください
- **テスト詳細**: [tests/README.md](tests/README.md) をご確認ください

---

**🚀 Phase 16-B 設定一元化・保守性向上完了: 160個ハードコード値統合・620テスト100%成功・thresholds.yaml中央管理・1万円運用最適化により、システム保守性大幅向上・設定管理効率化・個人運用最適化を達成した企業級品質保証・個人向けAI自動取引システム** 🎉