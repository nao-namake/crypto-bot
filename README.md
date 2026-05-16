# Crypto-Bot

bitbank信用取引・BTC/JPY専用のAI自動取引システム（GCP Cloud Run 24時間稼働）

[![Tests](https://img.shields.io/badge/tests-2400%2B%20passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-73%25%2B-green)](tests/)
[![Phase 87](https://img.shields.io/badge/Phase%2087-Complete-success)](docs/開発履歴/Phase_87.md)
[![Phase 88](https://img.shields.io/badge/Phase%2088-Complete-success)](docs/開発履歴/Phase_88.md)
[![Phase 89](https://img.shields.io/badge/Phase%2089-Complete%20%26%20Deployed-success)](docs/開発履歴/Phase_89.md)

---

## 現在の状態

**Phase 86-89 総合レビュー + P0+P1 軽微修正完了（2026-05-16）→ ML 再学習 v7 待ち（macro F1 で真の性能確認）**

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 86-89 全 72 観点 3-agent レビュー + ML 評価指標の構造的歪み発見・修正（weighted→macro F1）+ cross_asset リーク防止 + 訓練 180→365 日統一 |
| Phase 86-89 レビュー | Critical ゼロ・軽微 9 件（P0+P1 4 件修正完了・P2 5 件 Phase 90 繰越） |
| 特徴量数 | 37 → **55**（+18・6 カテゴリ追加） |
| ML モデル | 3 → **4**（N-BEATS 追加・重み 0.34/0.34/0.17/0.15） |
| ⚠️ 旧 weighted F1 性能 | LGB 0.612→0.893 等の改善は**評価指標歪み**（HOLD 94% 不均衡 + weighted F1 = ランダム予測 0.893 と同水準） |
| 🔄 真の性能 (macro F1) | ML 再学習 v7 で確認予定（Phase 84/85 と公平比較可能化） |
| N-BEATS 修復は本物 | confidence_std 2.98e-08 → **0.115**（400 万倍改善・定数予測脱出は事実） |
| TPSL 検証結果 | TPSLCalculator 実装は健全。Phase 85 報告 +362 円/件は**手数料未控除**・真の期待値は +138-254 円/件 |
| 次の予定 | ML 再学習 v7 → macro F1 確認 → 実機 1 週間観察 → Phase 90 計画 |
| 詳細計画 | [docs/開発計画/ToDo.md](docs/開発計画/ToDo.md) / [docs/開発履歴/Phase_89.md](docs/開発履歴/Phase_89.md) / `~/.claude/plans/c-gleaming-ladybug.md` |
| 最終更新 | 2026年5月16日 - Phase 86-89 総合レビュー + P0+P1 修正完了 |

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

## Phase 87/88 計画概要

9エージェント並列調査で **全28欠陥** を確定。決済システム再構築 + 運用基盤強化 + GCPコスト削減を統合実施。

### Phase 87 全 Stage ✅ 完了（2026-05-14 本番デプロイ済）

Critical 5 + High 10 を全完了。SL消失インシデント（2026-05-12）を構造的に防止する仕組みを確立。

**🔴 Critical (5/5 完了 ✅)**:
- ✅ C1: SL CANCELED_UNFILLED 検出（SLMonitor 新規実装）
- ✅ C2: ML信頼度を `predicted_class_proba` に統一
- ✅ C3: TP Maker タイムアウト時の自動キャンセル（_safe_cancel）
- ✅ C4: DummyModel サーキットブレーカー（MLHealthMonitor、3回連続失敗で EMERGENCY_STOP）
- ✅ C5: 5分ループ内 SL health check

**🟠 High (10/10 完了 ✅)**:
- ✅ H1 (SL 24h timeout) / H2 (起動時SL失敗) / H3 (stop_limit+slippage 二重防衛) / H4 (SL Firestore永続化) / H5 (Drawdown Firestore永続化)
- ✅ H6 (品質フィルタ レジーム別閾値: tight 0.55 / normal 0.75 / trending 0.50) / H7 (特徴量定数) / H8 (RECOVERY_TESTING 段階復帰) / H9 (6戦略アサート) / H10 (品質フィルタ共通モジュール化)
- ✅ 補強: src/analysis/common/（sl_validators / canceled_unfilled_detector / tp_sl_helpers）

**実機検証**: 5/13 24h: 勝率25% -¥5,216 → 5/14 12h: 勝率100% +¥1,500（+¥6,716改善）

### Phase 88（GCPコスト削減 + 孤児SL再発防止 + クリーンアップ・2-3週間）

**詳細プラン**: `~/.claude/plans/phase-iterative-biscuit.md`（GCP 仕様 Web 調査反映版）

**💰 Infrastructure 5件（月額¥3,000 → ¥300-500 目標）**:
- I1: Cloud Logging WARNING化（-¥100~200/月、実効ほぼゼロだが防御的に実施）
- I2: Artifact Registry リテンション（30日以上削除・最新10件保持、-¥20~50/月）
- I3: min_instances=0 + Cloud Scheduler（**-¥2,400/月想定**、Flask /trigger endpoint + OIDC認証）
- I4: メモリ 1GiB → 512MiB（-¥150/月、ペーパー稼働で <400MB 確認後）
- I5: bitbank API キャッシュ徹底（-¥20~50/月、Egress 削減）

**🟠 High 1件**:
- H11: 孤児SL注文の再発防止（5分ループ検出 + 指数バックオフ + bitbank 70004 ハンドリング）

**🟡 Medium 5件 + 🟢 Low 3件**: Kelly理由明示(M1)、APIレート制限統一(M2)、TP/SL丸め(M3)、異常検知時間帯別(M4)、税務SQLite GCS化(M5)、Phase XXX コメント整理(L1)、README/CLAUDE同期(L2)、Dead code約500行一掃(L3)

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
| **インフラ** | GCP Cloud Run / Secret Manager / Artifact Registry / Firestore (Phase 87 H4-5) / Cloud Scheduler (Phase 88 I3 予定) / Cloud Storage (Phase 88 M5 予定) |
| **CI/CD** | GitHub Actions（自動テスト・週次ML学習・デプロイ） |
| **品質管理** | pytest / coverage 75%+ / flake8 / black / isort |

---

## ドキュメント

- **[CLAUDE.md](CLAUDE.md)**: 開発ガイド・品質基準・設定詳細
- **[ToDo.md](docs/開発計画/ToDo.md)**: 開発計画・Phase 87/88 詳細・Phase 89-92 中長期計画
- **[統合運用ガイド](docs/運用ガイド/統合運用ガイド.md)**: デプロイ・監視・トラブル対応
- **[開発履歴サマリー](docs/開発履歴/SUMMARY.md)**: Phase 1-77総括
- **[Phase 87](docs/開発履歴/Phase_87.md)**: 全 Stage 実装記録（Critical 5 + High 10 達成）
- **[Phase 86](docs/開発履歴/Phase_86.md)**: TP/SL/Entry 根本再構築
- **詳細プラン**: `~/.claude/plans/phase-iterative-biscuit.md`（Phase 88 詳細設計・GCP仕様 Web 調査反映版）

---

## リスク・免責事項

仮想通貨取引には元本割れのリスクがあります。本システムの使用による損失について作成者は責任を負いません。

---

**最終更新**: 2026年5月15日 - Phase 87 全 Stage 完了・本番デプロイ済 / Phase 88 計画策定完了（GCP仕様 Web 調査反映版・着手予定）
