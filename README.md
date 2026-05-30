# Crypto-Bot

bitbank信用取引・BTC/JPY専用のAI自動取引システム（GCP Cloud Run 24時間稼働）

[![Tests](https://img.shields.io/badge/tests-2400%2B%20passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-73%25%2B-green)](tests/)
[![Phase 87](https://img.shields.io/badge/Phase%2087-Complete-success)](docs/開発履歴/Phase_87.md)
[![Phase 88](https://img.shields.io/badge/Phase%2088-Complete-success)](docs/開発履歴/Phase_88.md)
[![Phase 89](https://img.shields.io/badge/Phase%2089-Complete%20%26%20Deployed-success)](docs/開発履歴/Phase_89.md)
[![Phase 90](https://img.shields.io/badge/Phase%2090ε-Implemented-success)](docs/開発履歴/Phase_90.md)

---

## 現在の状態

**Phase 90ζ SL土日縮小の観察可能化 + 特徴量数37→55整合 デプロイ完了（2026-05-31）→ Day 1 検証待ち**（コミット `003d3a32`・CI/CD success・revision `...cost-opt-0530-2034`。Phase 90ε `b75d2f63` も本番稼働・土日TP500ログ確認済）

| 項目 | 値 |
|------|-----|
| 🎯 Phase 90ζ 観察可能化+整合 | Phase 90ε デプロイ後のライブ分析で①SL土日縮小が本番ログで見えない（SL適用ログが INFO で WARNING抑制）→ `strategy_utils.py` の SL適用ログを INFO→WARNING 昇格（TP昇格と対称・`(土日縮小→N円)` ラベル付きで検証可能化）、②特徴量数37/55の不整合（README図・checks.sh ログが旧37）→ 55に統一。テスト1件追加・取引挙動は不変 |
| 🎯 Phase 90ε 土日TP/SL縮小 | ユーザー指摘「日本の土日祝はBTCが狭いレンジに収まりやすく、TP1000-1200円では約定しないまま月曜を迎える」を起点に実装。実運用の confidence_based（固定金額）経路に **JST土日判定**（`weekday()>=5`・Phase 83C のJST明示変換踏襲）を追加し、**土日は信頼度に関係なくTPを一律500円**（距離≒0.36%でレンジ内利確優先）に上書き。SLは target1000円へ下げるが **floor 0.7% 据え置き（A案）** のため実効SL≒0.70%（≒1,733円@0.015BTC・平日2000円より縮小しつつノイズ耐性維持）。祝日は対象外（jpholiday 不採用・追加依存ゼロ）。変更3ファイル・テスト6件追加・black/isort/flake8 PASS・実config E2E確認済 |
| 最新成果（Phase 90δ）| ライブ分析調査で **Maker 戦略の致命バグを発見・修正（Phase 90δ）**：`bitbank_client.py:840` が `postOnly`（camelCase）を送信していたが bitbank は `post_only`（snake_case）を期待し、ccxt 4.5.1 は変換しないため **post_only が全注文で無視され通常指値化＝即時約定時テイカー約定**していた。旧「Maker 化率 100%」は約定種別を実 API で検証しない虚偽記録。post_only 名前修正 + 約定種別の真実観測 + 緊急決済 DRY_RUN 誤カウント修正 + 50062 レース対策の 4 件を実装、18 テスト追加・`checks.sh` 全 PASS |
| 🎯 Phase 90δ 追加調整 | (1) **レジーム別TP/SL が未適用（dead code）と判明**：`confidence_based` が `regime_based` を常に上書き（5/29 実証: TP適用99回全て信頼度別・normal TP500 は0回）。実態は全エントリーが信頼度別 → ドキュメント訂正。(2) **TP 引き下げ**：TP1500（距離0.956%）が遠く +1000円付近で反転→SL のケース多発のため、高 TP1500→1200 / 低 TP1200→1000 に引き下げ（SL維持・RR 0.83:1 許容）|
| 🎯 Phase 90γ-⑦+⑨ 統合実装内容 | ⑦-1 INFO→WARNING 格上げ 3 箇所 / ⑦-2 例外スワロー解消 3 箇所（trigger_server pragma 解除含む）/ ⑦-3 サイレント失敗ログ 3 箇所（DummyModel fallback・ml_confidence=None・drift skip）/ ⑦-4 persistence=None CRITICAL 警告 / ⑨ 25 件テスト追加（test_backtest_runner.py 新規 8 + _load_state 5 + Drift KS 異常入力系 6 + test_trigger_server.py 新規 6 + 補強 2）+ 副次バグ修正 1 件（時刻ハードコード）|
| 🎯 Phase 90γ-⑥ Day 1 検証結果（5/29 朝・完全成功）| bitbank API 実取引 + WARNING ログで TP 距離 **0.956%**（目標 0.7-0.9% 達成）・実効 RR **~1.02:1**（旧 0.25:1 から **4 倍改善**）・~~Maker 化率 100%~~（⚠️ **Phase 90δ で虚偽判明**：post_only 未機能で約定種別未検証だったため実態はテイカー約定）・信頼度ラベル付き TP 配置ログ **64/65 試行で機能**（旧バグ時 0%）。実取引件数は trending 相場継続で 24h 1 件のみだが、修正①の confidence_based 機能性は完全証明 |
| 🎯 同時エントリー仕様確認 | Phase 50.4 維持率予測拒否 48 件/24h は**バグではなく仕様通り**。証拠金 24 万円 / 1 エントリー 0.015 BTC ≒ 17 万円消費で維持率 130% → 追加エントリーで 76% へ落ちる予測 = 強制ロスカット 50% への 30pt 安全バッファ |
| 🎯 Phase 90γ-⑥ 根本発見（履歴）| `tp_sl_manager.py:2221` の `getattr(evaluation, "confidence", None)` が `TradeEvaluation` の実フィールド名（`confidence_level` / `adjusted_confidence`）と不一致 → Phase 68.8（2026-03-13）以降 **約 2.5 ヶ月間 confidence_based 上書きが全エントリーでスキップ**。修正により全レジームで信頼度ベース TP=1500/SL=2000 に統一 |
| 🎯 Phase 90γ-①〜⑤（履歴）| Drift 検出再設計 / trigger EMERGENCY_STOP 解消 / 取引拒否 91% 解消 / Maker fallback 段階改善 / 観察可能化 / Phase 79 仕様誤読訂正 / 50062 連発対策（詳細は `docs/開発履歴/Phase_90.md`）|
| 🎯 Phase 90α/β 根本発見（履歴）| 90α: メタラベリング有効化（`--meta-label` 追加 6 行）で macro F1 0.347 → 0.546・90β: 本番運用リスク 7 件根本修正 |
| v8e (新) macro F1 | LGB CV **0.546** / Test 0.486・RF CV 0.530・N-BEATS CV 0.514 Test 0.524・XGB CV 0.459 |
| v8e クラス分布 | success 30.8% / failure 69.2%（Triple Barrier 理想分布）|
| 特徴量数 | 37 → **55**（+18・6 カテゴリ追加）|
| ML モデル | 3 → **4**（N-BEATS 追加・重み 0.34/0.34/0.17/0.15） |
| Phase 90γ-⑦+⑨ 修正規模 | 8 ファイル変更（コード 4 + テスト新規 2 + テスト拡張 2）/ **+577 / -15 行・25 件テスト追加 / 全 PASS（カバレッジ 72%+）** |
| 過去 7 日損益（5/21-5/28）| 取引 15 ペア / 勝率 **66.7%** (10勝5敗) / 総 NET **¥-3,056** / **PF 0.496** / 平均勝利 ¥300 vs 平均損失 ¥1,212 (RR 0.25:1) / **月利 -2.6% / 年利 -31%**（目標 +10%/年 から -41pt 未達）→ **Phase 90γ-⑥ Day 1 で機能性確認済**・Day 7（6/4 頃）に PF > 1.2 / 月利 > 0% への改善見込み |
| 外部ソース検証 | bitbank + Binance + 業界標準 ADX で Bot のレジーム判定が **一致**（直近 24h で trending 60-66%）。「取引ない=trending 相場」は妥当。TP/SL 距離は ATR×6 と業界標準（×1.5-2.0）より広いが Phase 85 実証で意図的設定 |
| 次の予定 | **5/30 朝に Phase 90γ-⑦ Day 1 観察可能化検証**: 新規 WARNING 5 種以上が可視化されているか + Phase 90γ-⑥ Day 2 累積効果。健全なら **Phase 90γ-④（ML 改善）着手判断**（バックテスト経路統合 90γ-⑧ は優先度低でスキップ候補）|
| 詳細計画 | [docs/開発計画/ToDo.md](docs/開発計画/ToDo.md) / [docs/開発履歴/Phase_90.md](docs/開発履歴/Phase_90.md) / `~/.claude/plans/humming-prancing-lamport.md`（Phase 90γ-⑦+⑨ 統合プラン）|
| 最終更新 | 2026年5月29日 - Phase 90γ-⑦+⑨ デプロイ完了 + Phase 90γ-⑥ Day 1 検証完全成功 |

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
│  (Bitbank API)  │    │ (55 Features)   │    │ (6 Strategies)  │
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
├── features/       # 特徴量生成（55特徴量・Phase 89-β/γ/δ で 37→55 拡張）
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

**最終更新**: 2026年5月31日 - Phase 90ζ SL土日縮小の観察可能化（INFO→WARNING）+ 特徴量数37→55ドキュメント整合 実装完了
