# Crypto-Bot

bitbank信用取引・BTC/JPY専用のAI自動取引システム（GCP Cloud Run 24時間稼働）

[![Tests](https://img.shields.io/badge/tests-2122%20passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-74.14%25-green)](tests/)
[![Phase](https://img.shields.io/badge/Phase%2087%20Stage%201-Implemented-blue)](docs/開発履歴/Phase_87.md)
[![Next](https://img.shields.io/badge/Stage%202%2F3-Pending-orange)](docs/開発計画/ToDo.md)

---

## 現在の状態

**Phase 87 Stage 1 + Stage 1-R 実装完了**（ローカル）→ デプロイ待ち / Stage 2-3 未着手

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 87 Stage 1: SLMonitor 新規実装（CANCELED_UNFILLED/EXPIRED/REJECTED/24h timeout 検出 + dry_run付き緊急成行決済）、ML信頼度 predicted_class_proba 統一、TP Maker _safe_cancel、起動時SL欠損サイレント失敗解消、EXPECTED_FEATURE_COUNT 共有定数化 |
| 直近インシデント | 2026-05-12 SL stop注文が CANCELED_UNFILLED で約定失敗（6時間裸ポジ放置）→ Phase 87 Stage 1 で構造的に防止 |
| 次の予定 | (1) Stage 1 デプロイ + 48-72h dry_run 観察 → (2) `dry_run: false` 切替 → (3) Stage 2 (Firestore 永続化 H3/H4/H5/C4) → (4) Stage 3 (H6/H8/H10/分析共通化) |
| 詳細計画 | [docs/開発計画/ToDo.md](docs/開発計画/ToDo.md) / [docs/開発履歴/Phase_87.md](docs/開発履歴/Phase_87.md) |
| 最終更新 | 2026年5月13日 |

---

## クイックスタート

### ローカル実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境設定
cp config/secrets/.env.example config/secrets/.env
# → .envにbitbank API設定

# 品質チェック
bash scripts/testing/checks.sh  # 全テスト成功・75%+カバレッジ

# ペーパートレード
bash scripts/paper/run_paper.sh

# ライブトレード
python3 main.py --mode live
```

### GCP確認

```bash
# 稼働状況
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 --format="value(status.conditions[0].status,status.url)"

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# ライブ分析（24時間）
python3 scripts/live/standard_analysis.py --hours 24
```

---

## システム概要

**6つの取引戦略**と**機械学習**を統合し、**37特徴量**を総合分析することで24時間自動取引を実現。**メタラベリング**（取引品質のGo/No-Go判定）と**レジーム別動的戦略選択**により、市場状況に適応した取引を行います。

| 項目 | 値 |
|------|-----|
| **対象市場** | bitbank信用取引・BTC/JPY専用 |
| **証拠金** | 50万円 |
| **年利目標** | 10%（Phase 88まで） / **15-18%（Phase 91完了後）** |
| **取引頻度** | 5分間隔実行 |
| **稼働体制** | 24時間・GCP Cloud Run |
| **月額コスト** | 現状約3,000円 / **Phase 88 I3 完了後 300-500円目標** |

---

## 6戦略構成（Phase 85 trending全停止）

| 区分 | 戦略名 | 核心ロジック |
|------|--------|-------------|
| **レンジ型** | BBReversal | BB位置主導 + RSIボーナス → 平均回帰 |
| **レンジ型** | StochasticDivergence | 価格とStochasticの乖離検出 → 反転 |
| **レンジ型** | ATRBased | ATR消尽率70%以上 → 反転期待（主力） |
| **レンジ型** | CMFReversal | CMF売り圧力減少→BUY / 買い圧力減少→SELL |
| **トレンド型** | MACDEMACrossover | MACDクロス + EMAトレンド確認 |
| **トレンド型** | ADXTrendStrength | ADX≥22 + DIクロス → トレンドフォロー |

### レジーム別重みづけ

| 戦略 | tight_range | normal_range | trending |
|------|-------------|--------------|----------|
| ATRBased | 0.35 | 0.25 | **0.0** |
| CMFReversal | 0.20 | 0.15 | **0.0** |
| BBReversal | 0.20 | 0.15 | **0.0** |
| StochasticReversal | 0.10 | 0.15 | **0.0** |
| ADXTrendStrength | 0.10 | 0.15 | **0.0** |
| MACDEMACrossover | 0.05 | 0.15 | **0.0** |

**Phase 85 trending全停止根拠**: 過去30日 trending 23件で全シナリオ赤字。「レンジ専用bot」設計と完全合致。

---

## システムアーキテクチャ

```
レイヤードアーキテクチャ設計
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Data Layer     │───▶│ Feature Layer   │───▶│ Strategy Layer  │
│  (Bitbank API)  │    │ (37 Indicators) │    │ (6 Strategies)  │
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
├── features/       # 特徴量生成（37指標）
├── strategies/     # 6戦略（Registry Pattern）
├── ml/             # ML統合（3モデルアンサンブル）
├── trading/        # 取引管理層（5層アーキテクチャ）
└── backtest/       # バックテストシステム

tax/                # 確定申告システム
scripts/            # 運用スクリプト
config/core/        # 設定ファイル群
models/production/  # MLモデル（週次更新）
```

---

## Phase 87/88 計画概要（Stage 1 実装完了 / 残作業あり）

9エージェント並列調査で **全28欠陥** を確定。決済システム再構築 + 運用基盤強化 + GCPコスト削減を統合実施。

### Phase 87 Stage 1 + Stage 1-R ✅ 実装完了（2026-05-13）

**🔴 Critical (4/5 完了)**:
- ✅ C1: SL CANCELED_UNFILLED 検出（SLMonitor 新規実装）
- ✅ C2: ML信頼度を `predicted_class_proba` に修正
- ✅ C3: TP Maker タイムアウト時の自動キャンセル（_safe_cancel）
- ⏳ C4: DummyModel サーキットブレーカー（Stage 2 で実装予定）
- ✅ C5: 5分ループ内 SL health check

**🟠 High (4/10 完了)**: ✅ H1 (24h timeout) / ✅ H2 (起動時SL失敗) / ✅ H7 (特徴量定数) / ✅ H9 (戦略アサート)

**残作業 (Stage 2/3 で実施)**:
- Stage 2: H3 (stop_limit+slippage 二重防衛) / H4 (SL Firestore永続化) / H5 (Drawdown Firestore永続化) / C4 (DummyModel CB)
- Stage 3: H6 (品質フィルタレジーム別) / H8 (RECOVERY_TESTING) / H10 (バックテストvsライブ E2E整合性) / 分析スクリプト共通化

### Phase 88（運用基盤・クリーンアップ・GCPコスト削減・2-3週間）

**💰 Infrastructure 5件（月額3,000円 → 300-500円）**:
- I1: Cloud Logging WARNING化（-100~200円）
- I2: Artifact Registry リテンション（-20~50円）
- I3: min_instances=0 + Cloud Scheduler（**-2,400円**、要 Phase 87 H4-5）
- I4: メモリ 1GB → 512MB（-150円）
- I5: bitbank API キャッシュ徹底（-20~50円）

**🟡 Medium 5件 + 🟢 Low 3件**: Kelly理由明示、APIレート制限統一、TP/SL丸め、異常検知時間帯別、税務SQLite GCS化、Dead code約500行一掃 ほか

### Phase 89-92 中長期計画（Webリサーチ統合）

Phase 87/88 完了後、最新MLbot技術を段階的に導入:
- **Phase 89**: Purged K-Fold + Fractional Kelly + OFI + Funding Rate（年利12-13%）
- **Phase 90**: N-BEATS + LLM センチメント + HMM（年利14-16%）
- **Phase 91**: WebSocket depth stream + Maker戦略実装化 + BTC-ETH相関（年利15-18%）
- **Phase 92**: PPO/マルチペア/Transformer（条件付き・年利17-20%）

詳細: [docs/開発計画/ToDo.md](docs/開発計画/ToDo.md)

---

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **言語** | Python 3.13 |
| **取引所API** | ccxt（bitbank信用取引対応） |
| **データ処理** | pandas / numpy |
| **機械学習** | scikit-learn / XGBoost / LightGBM |
| **インフラ** | GCP Cloud Run / Secret Manager / Artifact Registry / **Firestore (Phase 87 H4-5)** / **Cloud Scheduler (Phase 88 I3)** |
| **CI/CD** | GitHub Actions（自動テスト・週次ML学習・デプロイ） |
| **品質管理** | pytest / coverage 75%+ / flake8 / black / isort |

---

## ドキュメント

- **[CLAUDE.md](CLAUDE.md)**: 開発ガイド・品質基準・設定詳細
- **[ToDo.md](docs/開発計画/ToDo.md)**: 開発計画・Phase 87/88 詳細・Phase 89-92 中長期計画
- **[統合運用ガイド](docs/運用ガイド/統合運用ガイド.md)**: デプロイ・監視・トラブル対応
- **[開発履歴サマリー](docs/開発履歴/SUMMARY.md)**: Phase 1-77総括
- **[Phase 87](docs/開発履歴/Phase_87.md)**: Stage 1+1-R 実装記録（最新）
- **[Phase 86](docs/開発履歴/Phase_86.md)**: TP/SL/Entry 根本再構築
- **詳細プラン**: `~/.claude/plans/phase-nifty-pizza.md`（Phase 87 Stage 1/1-R/2/3 + 89-92 完全版）

---

## リスク・免責事項

仮想通貨取引には元本割れのリスクがあります。本システムの使用による損失について作成者は責任を負いません。

---

**最終更新**: 2026年5月13日 - Phase 87 Stage 1+Stage 1-R 実装完了（残作業: Stage 2 Firestore永続化 / Stage 3 品質向上）
