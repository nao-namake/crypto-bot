# docs/ - AI自動取引システムドキュメント

**Phase 56完了版**: 1,252テスト100%成功・66.78%カバレッジ達成・6戦略統合・55特徴量システム・Cloud Storage統合

---

## 📂 ディレクトリ構成・使い分けガイド

```
docs/
├── 📊 稼働チェック/          # システム診断・ヘルスチェック（デプロイ後・定期確認）
├── 🔧 運用ガイド/            # 日常運用・API設定・税務対応ガイド
├── 📝 開発計画/              # 未達成タスク・要件定義・GCPクリーンアップ
├── 📚 開発履歴/              # Phase別実装履歴（Phase 1-56完了記録）
└── 📈 検証記録/              # バックテスト結果・パフォーマンス分析記録
```

---

## 📊 稼働チェック/ - システム診断・ヘルスチェック

**目的**: デプロイ後・定期的なシステム稼働確認・問題早期検知

### 📋 ファイル一覧

| ファイル | 内容 | 使用場面 |
|---------|------|---------|
| `README.md` | このディレクトリの使い方 | 初回確認時 |
| `01_システム稼働診断.md` | 基盤システム稼働確認（Cloud Run・Discord・残高等） | デプロイ後・毎時確認 |
| `02_Bot機能診断.md` | Bot機能診断（ML予測・戦略実行・取引実行等） | 基盤正常後に実行 |
| `03_緊急対応マニュアル.md` | 問題発生時の緊急対応手順 | エラー検知時 |

### 🚀 推奨実行順序

```bash
# 1. 基盤システム稼働確認（必須・最優先）
bash scripts/testing/validate_system.sh
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# 2. Bot機能診断（基盤正常後）
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"ML予測\"" --limit=5

# 3. 問題発生時のみ
# → 03_緊急対応マニュアル.md 参照
```

**重要**: 必ず実行順序を守る（01 → 02 → 問題時03）

---

## 🔧 運用ガイド/ - 日常運用・API設定・税務対応

**目的**: 日常運用で必要な各種手順・設定ガイド

### 📋 ファイル一覧

| ファイル | 内容 | 使用場面 |
|---------|------|---------|
| `統合運用ガイド.md` | デプロイ・検証・運用の統合ガイド | デプロイ時・運用時 |
| `GCP運用ガイド.md` | GCP Cloud Run運用・監視・トラブルシューティング | GCP運用時 |
| `bitbank API.md` | bitbank API仕様・エラー対応 | API連携時・エラー時 |
| `GCP権限.md` | GCP IAM権限設定・Secret Manager | GCP設定時 |
| `税務対応ガイド.md` | Phase 47確定申告システム使用方法 | 確定申告時（年1回） |

### 🎯 主要使用場面

**デプロイ時**:
```bash
# 統合運用ガイド参照
# Step 1: ML学習実行
python3 scripts/ml/create_ml_models.py --mode backtest

# Step 2: 品質チェック
bash scripts/testing/checks.sh

# Step 3: デプロイ実行
# → 統合運用ガイド.md 参照
```

**確定申告時（Phase 47機能）**:
```bash
# 税務対応ガイド参照
python3 tax/scripts/export_trade_history.py --start-date 2025-01-01 --end-date 2025-12-31 --output tax/exports/trades_2025.csv
python3 tax/scripts/generate_tax_report.py --year 2025 --output tax/reports/tax_report_2025.txt
```

---

## 📝 開発計画/ - 未達成タスク・要件定義

**目的**: 次に実装すべき機能・システム要件定義・開発方針

### 📋 ファイル一覧

| ファイル | 内容 | 使用場面 |
|---------|------|---------|
| `ToDo.md` | 未達成タスク一覧（Phase 50以降） | 次期開発計画時 |
| `要件定義.md` | システム要件定義・判断基準 | 実装時・迷った時 |
| `GCPクリーンアップ指示.md` | GCPリソース定期削減手順 | 月1-2回・デプロイ前 |

### 🎯 Phase 49完了・Phase 50開始準備

**Phase 47-49完了サマリー**:
- **Phase 47**: 確定申告対応システム（95%時間削減・10時間→30分）
- **Phase 48**: 週間レポート実装（Discord通知99%削減・コスト35%削減）
- **Phase 49**: バックテスト完全改修（信頼性100%・TP/SL完全同期・TradeTracker統合）

**Phase 50以降の開発優先度** (ToDo.md参照):
1. ⭐ **Phase 50**: 情報源多様化（ML精度+15-25%・55→75-88特徴量） - 最優先
2. 📈 **Phase 51**: エントリー戦略高度化（エントリー精度+8-15%）
3. 🌐 **Phase 52**: 複数通貨ペア対応（収益機会+30-50%）

---

## 📈 検証記録/ - バックテスト結果・パフォーマンス分析

**目的**: バックテスト実行結果とパフォーマンス分析記録を管理

### 📋 ファイル一覧

| ファイル | 内容 | 実施日 |
|---------|------|-------|
| `Phase_56_20251129.md` | Phase 56検証結果（最新） | 2025/11/29 |
| `Phase_52.2-production-simulation-final_20251112.md` | Phase 52.2本番シミュレーション | 2025/11/12 |
| `Phase_52.1_20251115.md` | Phase 52.1検証結果 | 2025/11/15 |
| `Phase_51.10-B_20251111.md` | Phase 51.10-B検証結果 | 2025/11/11 |

### 🎯 使用場面

**バックテスト実行**:
```bash
# GitHub Actions（推奨）
gh workflow run backtest.yml --field phase_name=57 --field backtest_days=180

# ローカル実行
bash scripts/backtest/run_backtest.sh

# Markdownレポート生成
python scripts/backtest/generate_markdown_report.py src/backtest/logs/backtest_*.json --phase 57
```

**結果確認**:
```bash
# 最新レポート確認
ls -lt docs/検証記録/Phase_*.md | head -3
```

---

## 📚 開発履歴/ - Phase別実装履歴

**目的**: 過去の実装内容・設計判断・技術的詳細の記録

### 📋 ファイル一覧

| ファイル | 対象Phase | 内容 |
|---------|----------|------|
| `Phase_01-10.md` | Phase 1-10 | 初期システム構築 |
| `Phase_11-20.md` | Phase 11-20 | 戦略実装・ML統合 |
| `Phase_21-30.md` | Phase 21-30 | 動的信頼度計算 |
| `Phase_31-37.md` | Phase 31-37 | SL/TP実装・API対応 |
| `Phase_38-39.md` | Phase 38-39 | レイヤードアーキテクチャ |
| `Phase_40-46.md` | Phase 40-46 | Optuna最適化・統合TP/SL |
| `Phase_47-48.md` | Phase 47-48 | 確定申告・週間レポート |
| `Phase_49.md` | Phase 49 | バックテスト完全改修 |
| `Phase_51.md` | Phase 51 | 6戦略統合・動的戦略管理 |
| `Phase_52.md` | Phase 52 | 55特徴量システム・設定最適化 |
| `Phase_53.md` | Phase 53 | RandomForestクラッシュ修正・ML統合最適化 |

### 🔍 使用場面

**過去実装を確認したい時**:
```bash
# Phase 47の確定申告システム実装詳細を確認
cat docs/開発履歴/Phase_47-48.md | grep -A 50 "Phase 47"

# Phase 49のバックテスト改修詳細を確認
cat docs/開発履歴/Phase_49.md
```

**設計判断の理由を知りたい時**:
- 各Phaseドキュメントに実装背景・設計判断・技術詳細を記載
- トラブルシューティング時の参考情報として活用

---

## 🎯 Phase 56完了時点のシステム状態

### ✅ テスト・品質保証

```bash
# 品質チェック（開発前後必須）
bash scripts/testing/checks.sh

# 期待結果:
# ✅ 1,252テスト100%成功
# ✅ 66.78%カバレッジ達成
# ✅ flake8・black・isort通過
```

### 📊 主要機能

**取引システム**:
- 6戦略統合（ATRBased・DonchianChannel・BBReversal・ADXTrendStrength・StochasticReversal・MACDEMACrossover）
- 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%・n_jobs=1設定）
- 55特徴量Strategy-Aware学習（49基本 + 6戦略信号）
- 完全指値オンリー実装（年間¥150,000削減・約定率90-95%）

**リスク管理**:
- レジーム別動的TP/SL設定（tight_range・normal_range・trending）
- 適応型ATR倍率（低2.5x・通常2.0x・高1.5x）
- 証拠金維持率80%確実遵守

**バックテストシステム**:
- 戦略シグナル事前計算（look-ahead bias防止）
- TP/SL決済ロジック実装（ライブモード完全一致）
- TradeTracker統合・matplotlib可視化
- **GitHub Actions統合**: `docs/検証記録/`に自動コミット

**CI/CD・自動化**（Phase 56）:
- **週次MLモデル学習**: `.github/workflows/model-training.yml`（毎週日曜 9:00 JST）
- **週間レポート**: `.github/workflows/weekly-report.yml`（毎週月曜 9:00 JST）
- **バックテスト**: `.github/workflows/backtest.yml`（手動実行）
- **Cloud Storage統合**: 取引履歴DBの永続化・週間レポート連携

### 🏗️ インフラ

- **Cloud Run**: 1Gi・1CPU・asia-northeast1
- **Cloud Storage**: `gs://crypto-bot-trade-data`（取引履歴永続化）
- **実行頻度**: 5分間隔（Phase 37.3最適化）
- **監視**: Discord週間レポート（毎週月曜9:00 JST）
- **月額コスト**: 700-900円

---

## 📖 ドキュメント使い分けフローチャート

```
🎯 あなたの目的は？
│
├─ 🚀 システムが正常稼働しているか確認したい
│   └→ 📊 稼働チェック/01_システム稼働診断.md
│
├─ 🔧 デプロイ・運用手順を確認したい
│   └→ 🔧 運用ガイド/統合運用ガイド.md
│
├─ 📈 バックテスト結果を確認したい
│   └→ 📈 検証記録/Phase_*.md
│
├─ 💼 確定申告の準備をしたい（年1回）
│   └→ 🔧 運用ガイド/税務対応ガイド.md
│
├─ 📝 次に何を実装すべきか知りたい
│   └→ 📝 開発計画/ToDo.md
│
├─ ❓ システム要件・判断基準を確認したい
│   └→ 📝 開発計画/要件定義.md
│
├─ 🧹 GCPリソースを削減したい（月1-2回）
│   └→ 📝 開発計画/GCPクリーンアップ指示.md
│
└─ 📚 過去の実装履歴・設計判断を知りたい
    └→ 📚 開発履歴/Phase_XX.md
```

---

## 🔗 関連ファイル

### システム全体

- `CLAUDE.md`: Claude Code最適化ガイド（開発時必読）
- `README.md`: プロジェクトルート・全体概要
- `.github/workflows/`: CI/CD・週間レポート自動実行

### 設定ファイル

- `config/core/features.yaml`: 機能トグル設定
- `config/core/unified.yaml`: 統合設定ファイル
- `config/core/thresholds.yaml`: ML統合・リスク管理設定

### スクリプト

- `scripts/testing/checks.sh`: 品質チェック（開発必須）
- `scripts/reports/weekly_report.py`: 週間レポート生成（Phase 48）
- `tax/scripts/`: 確定申告スクリプト（Phase 47）

---

**最終更新**: 2025年11月30日 - Phase 56完了時点のドキュメント構成
