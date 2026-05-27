# Crypto-Bot

bitbank信用取引・BTC/JPY専用のAI自動取引システム（GCP Cloud Run 24時間稼働）

[![Tests](https://img.shields.io/badge/tests-2400%2B%20passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-73%25%2B-green)](tests/)
[![Phase 87](https://img.shields.io/badge/Phase%2087-Complete-success)](docs/開発履歴/Phase_87.md)
[![Phase 88](https://img.shields.io/badge/Phase%2088-Complete-success)](docs/開発履歴/Phase_88.md)
[![Phase 89](https://img.shields.io/badge/Phase%2089-Complete%20%26%20Deployed-success)](docs/開発履歴/Phase_89.md)

---

## 現在の状態

**Phase 90γ-⑥ ローカル実装完了（2026-05-28）→ 本番デプロイ待ち**

| 項目 | 値 |
|------|-----|
| 最新成果 | 5/28 ライブ分析 + bitbank API 実取引履歴 168h 分析で **TP/SL confidence 属性名バグ** が発覚。`tp_sl_manager.py:2221` の `getattr(evaluation, "confidence", None)` が `TradeEvaluation` の実フィールド名（`confidence_level` / `adjusted_confidence`）と不一致のため、Phase 68.8（2026-03-13）以降 **約 2.5 ヶ月間 confidence_based 上書きが全エントリーでスキップ**されていた。結果 normal_range で TP=500 円、tight_range で TP=1500 円が混在。Phase 90γ-⑥ で fallback chain に修正 + TP 配置ログ 4 箇所 INFO→WARNING 格上げ + Maker disable_reason 観察可能化 |
| 🎯 Phase 90γ-⑥ 根本発見 | bitbank API 168h 実取引でユーザー観察「TP=500 円・SL=2000 円で RR 悪い」を定量化。`getattr(evaluation, "confidence", None)` の属性名不一致で confidence_based が機能せず、regime_based の値が直接採用。tight_range では偶然 1500 が正しく動作、normal_range では 500 が誤採用。修正により全レジームで信頼度ベース TP=1500/SL=2000 に統一（実効 RR 0.25:1 → 0.6-0.75:1 期待）|
| 🎯 Phase 90γ-③.5 根本発見（履歴）| bitbank 公式仕様により post_only=true は「反対側板マッチ時のみ cancel」。自側板への post_only=true は queue 末尾に並ぶ → Maker 約定可能。Phase 68/79 の「best_bid 直接配置で必ず reject」コメントは仕様誤読 |
| 🎯 Phase 90γ-⑤ 根本発見（履歴）| bitbank 50062 経路解明:SL トリガー成行決済 → ポジ消滅 → 同サイクル内で別経路の TP 配置が並行実行 → 50062。`_check_position_exists()` で TP/SL 配置直前に実ポジ確認するガード追加 |
| 🎯 分析スクリプト修正（履歴）| 本番 `LOG_LEVEL=WARNING` で Phase 61.9 INFO ログが Cloud Logging に出ず過少集計。API ベース win_count/loss_count で上書きする 2 行追加で修正 |
| 🎯 Phase 90γ-① 〜 ③.4（履歴）| Drift 検出再設計 / trigger EMERGENCY_STOP 解消 / 取引拒否 91% 解消 / Maker fallback 段階改善 / 観察可能化（詳細は `docs/開発履歴/Phase_90.md`）|
| 🎯 Phase 90α/β 根本発見（履歴）| 90α: メタラベリング有効化（CI に `--meta-label` フラグ追加 6 行）で macro F1 0.347 → 0.546・90β: 本番運用リスク 7 件根本修正 |
| v8e (新) macro F1 | LGB CV **0.546** / Test 0.486・RF CV 0.530・N-BEATS CV 0.514 Test 0.524・XGB CV 0.459 |
| v8e クラス分布 | success 30.8% / failure 69.2%（Triple Barrier 理想分布）|
| 特徴量数 | 37 → **55**（+18・6 カテゴリ追加）|
| ML モデル | 3 → **4**（N-BEATS 追加・重み 0.34/0.34/0.17/0.15） |
| Phase 90γ-⑥ 修正規模 | 5 ファイル変更（コード 4 + テスト 1）+ 4 テスト追加 / **全 PASS（カバレッジ 72%+）** |
| 本番効果（5/28 48h 時点）| エントリー 13 件・勝率 71.4% / 損益 ¥-753（手数料 ¥1,459 が利益を圧迫）/ **Taker 率 87.5% (Maker 1 / Taker 7)** / TP 距離 0.3%-0.9% 混在 → Phase 90γ-⑥ で正常化期待 |
| 次の予定 | Phase 90γ-⑥ + 既存 ③.5/⑤/分析スクリプト修正 統合デプロイ → 24h ライブ分析で TP 距離 0.7-0.9% 統一・実 NET TP +1,200 円以上を確認 |
| 詳細計画 | [docs/開発計画/ToDo.md](docs/開発計画/ToDo.md) / [docs/開発履歴/Phase_90.md](docs/開発履歴/Phase_90.md) / `~/.claude/plans/tp-tp-sl-tp-rr-gcp-atomic-spark.md`（Phase 90γ-⑥ 統合プラン）|
| 最終更新 | 2026年5月28日 - Phase 90γ-⑥ TP/SL confidence 属性名バグ修正 + 観察可能化 3 件 ローカル実装完了 |

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

**6 つの取引戦略**と**機械学習（4 モデルアンサンブル）**を統合し、**55 特徴量**を総合分析することで 24 時間自動取引を実現。**メタラベリング**（取引品質の Go/No-Go 判定・Phase 90α）と**レジーム別動的戦略選択**により、市場状況に適応した取引を行います。

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

**最終更新**: 2026年5月28日 - Phase 90γ-⑥ TP/SL confidence 属性名バグ修正 + 観察可能化 3 件 ローカル実装完了
