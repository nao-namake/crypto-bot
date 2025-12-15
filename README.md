# Crypto-Bot - AI自動取引システム

**Phase 54開発中・bitbank BTC/JPY専用・GCP本番稼働中**

[![Tests](https://img.shields.io/badge/tests-passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-64%25%2B-green)](coverage-reports/)
[![Phase](https://img.shields.io/badge/Phase%2054-In%20Progress-blue)](docs/)

---

## クイックスタート

### ローカル実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境設定
cp config/secrets/.env.example config/secrets/.env
# → .envにbitbank API・Discord Webhook設定

# 品質チェック
bash scripts/testing/checks.sh  # 全テスト成功・64%+カバレッジ

# 実行
bash scripts/management/run_safe.sh local paper  # ペーパートレード
bash scripts/management/run_safe.sh local live   # ライブトレード
```

### GCP確認

```bash
# 稼働状況
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 --format="value(status.conditions[0].status,status.url)"

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

---

## システム概要

AI自動取引システムは、**bitbank信用取引専用のBTC/JPY自動取引ボット**です。

**6つの取引戦略**と**機械学習**を統合し、**55の特徴量**を総合分析することで24時間自動取引を実現。**真の3クラス分類**（BUY/HOLD/SELL）と**レジーム別動的TP/SL**により、市場状況に適応した取引を行います。

### 運用仕様

| 項目 | 値 |
|------|-----|
| **対象市場** | bitbank信用取引・BTC/JPY専用 |
| **資金規模** | 1万円スタート → 最大50万円 |
| **取引頻度** | 月100-200回・5分間隔実行 |
| **稼働体制** | 24時間・GCP Cloud Run |
| **月額コスト** | 700-900円 |

### 最新バックテスト結果（Phase 53.13）

| 指標 | 値 | 目標 |
|------|-----|------|
| **PF** | 1.25 | ≥1.34 |
| **勝率** | 47.9% | ≥51% |
| **取引数** | 697件 | - |
| **シャープレシオ** | 7.83 | - |
| **最大DD** | 0.33% | ≤0.5% |

### 6戦略構成

| 区分 | 戦略名 | 特性 |
|------|--------|------|
| レンジ型 | ATRBased | ATRベース逆張り |
| レンジ型 | DonchianChannel | チャネルブレイクアウト |
| レンジ型 | BBReversal | ボリンジャーバンド反転 |
| トレンド型 | ADXTrendStrength | ADXトレンド強度 |
| トレンド型 | StochasticReversal | ストキャスティクス反転 |
| トレンド型 | MACDEMACrossover | MACD・EMAクロス |

### レジーム別TP/SL設定

| レジーム | TP | SL | RR比 |
|---------|-----|-----|------|
| tight_range | 0.8% | 0.6% | 1.33:1 |
| normal_range | 1.0% | 0.7% | 1.43:1 |
| trending | 1.5% | 1.0% | 1.50:1 |

---

## 主要機能

### AI取引システム

- **6戦略統合**: レンジ型3 + トレンド型3・Registry Pattern
- **55特徴量**: 49基本 + 6戦略シグナル
- **真の3クラス分類**: BUY / HOLD / SELL直接予測
- **3モデルアンサンブル**: LightGBM 50% / XGBoost 30% / RandomForest 20%
- **Graceful Degradation**: ensemble_full.pkl → ensemble_basic.pkl → DummyModel

### リスク管理

- **レジーム別動的TP/SL**: 市場状況に応じた自動調整
- **適応型ATR**: ボラティリティ別SL調整（低2.5x / 通常2.0x / 高1.5x）
- **完全指値オンリー**: 年間¥150,000削減・約定率90-95%
- **証拠金維持率80%遵守**: API直接取得・過剰レバレッジ防止

### 運用監視

- **24時間稼働**: GCP Cloud Run・ゼロダウンタイム
- **週間レポート**: Discord通知・損益曲線グラフ
- **確定申告システム**: SQLite取引記録・移動平均法

---

## システムアーキテクチャ

```
レイヤードアーキテクチャ設計
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Data Layer     │───▶│ Feature Layer   │───▶│ Strategy Layer  │
│  (Bitbank API)  │    │ (15 Indicators) │    │ (6 Strategies)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ML Layer       │───▶│ Risk Layer      │───▶│ExecutionService │
│ (3 Model Ens.)  │    │ (Kelly Crit.)   │    │(BitbankClient)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### ディレクトリ構成

```
src/
├── core/           # 基盤システム（設定・実行制御・レポート）
├── data/           # データ層（Bitbank API・キャッシュ）
├── features/       # 特徴量生成（15指標）
├── strategies/     # 6戦略（Registry Pattern）
├── ml/             # ML統合（3モデルアンサンブル）
├── trading/        # 取引管理層（5層アーキテクチャ）
├── backtest/       # バックテストシステム
└── monitoring/     # 週間レポート

tax/                # 確定申告システム
scripts/            # 運用スクリプト
config/core/        # 設定ファイル群
models/production/  # MLモデル（週次更新）
```

---

## 技術スタック

### 言語・フレームワーク

- **Python 3.13**: MLライブラリ互換性最適化
- **ccxt**: bitbank API統合・信用取引対応
- **pandas/numpy**: データ処理・特徴量生成
- **scikit-learn/XGBoost/LightGBM**: 機械学習モデル

### インフラストラクチャ（GCP）

- **Cloud Run**: 24時間稼働・1Gi・1CPU
- **Secret Manager**: API認証情報管理
- **Artifact Registry**: Dockerイメージ管理
- **Cloud Logging**: ログ管理・JST時刻対応

### CI/CD・品質管理

- **GitHub Actions**: 自動テスト・週次ML学習・デプロイ
- **pytest**: 全テスト成功
- **coverage**: 64%以上
- **flake8/black/isort**: コード品質統一

---

## 設定・カスタマイズ

### 設定ファイル

```
config/core/
├── unified.yaml      # 統合設定（残高・実行間隔）
├── thresholds.yaml   # 閾値・パラメータ（ML統合・レジーム別TP/SL）
├── features.yaml     # 機能トグル
└── feature_order.json # 特徴量定義
```

### 実行モード

- **paper**: ペーパートレード（検証用）
- **live**: ライブトレード（本番取引）
- **backtest**: バックテスト（戦略検証）

---

## ドキュメント

### 開発者向け

- **[CLAUDE.md](CLAUDE.md)**: 開発ガイド・品質基準・Phase 54計画
- **[ToDo.md](docs/開発計画/ToDo.md)**: 開発計画・タスク管理

### 運用者向け

- **[統合運用ガイド](docs/運用ガイド/統合運用ガイド.md)**: デプロイ・監視・トラブル対応
- **[GCP運用ガイド](docs/運用ガイド/GCP運用ガイド.md)**: IAM権限・リソース管理
- **[システム機能一覧](docs/運用ガイド/システム機能一覧.md)**: 実装機能リファレンス
- **[開発履歴サマリー](docs/開発履歴/SUMMARY.md)**: Phase 1-53総括

---

## パフォーマンス・品質指標

| 指標 | 値 |
|------|-----|
| **テスト成功率** | 100% |
| **カバレッジ** | 64%以上 |
| **バックテストPF** | 1.25 |
| **バックテスト勝率** | 47.9% |
| **月額コスト** | 700-900円 |
| **手数料削減** | 年間¥150,000 |

---

## 開発状況

### Phase 54（現在）: ML性能検証・戦略最適化

| ステージ | Phase | 内容 | 状態 |
|----------|-------|------|------|
| 分析 | 54.0 | ML予測分析 | 進行中 |
| 分析 | 54.1 | 戦略別性能分析 | 予定 |
| 実装 | 54.2 | 設定調整 | 予定 |
| 実装 | 54.3 | コード変更 | 予定 |
| 検証 | 54.4 | 最終検証 | 予定 |

**目標**: PF 1.25 → 1.34+、勝率 47.9% → 51%+

---

## リスク・免責事項

- **投資リスク**: 仮想通貨取引には元本割れのリスクがあります
- **システムリスク**: 自動取引システムの不具合による損失の可能性
- **市場リスク**: 急激な市場変動への対応限界
- **免責**: 本システムの使用による損失について作成者は責任を負いません

**推奨**: 少額資金（1万円）でのテスト運用から開始し、段階的拡大

---

## サポート

- **Issues**: GitHub Issuesでの問題報告
- **Discussion**: 機能要望・質問・フィードバック
- **Security**: セキュリティ問題は非公開で報告

---

**最終更新**: 2025年12月16日 - **Phase 54開発中**（ML性能検証・戦略最適化）
