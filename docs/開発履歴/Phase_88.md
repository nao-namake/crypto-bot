# Phase 88: GCP コスト削減 + 孤児SL再発防止 + クリーンアップ

**期間**: 2026年5月15日 着手
**状態**: コード変更完了（B-1/B-2/C-1/C-3/D-1/D-2/E + I3 全実装） / GCP コマンド適用予定

---

## 背景

Phase 87 全 Stage 完了で SL消失検出層・Firestore 永続化・段階復帰を達成し、実機 12h で勝率 100% +¥1,500（5/13 比 +¥6,716改善）を確認。残る課題は:

1. **GCP 月額 ¥3,000**（min_instances=1 常時稼働 + Cloud Logging INFO 全出力が主因）
2. **2026-05-14 09:05 孤児SL残存**（TP約定後 bitbank 70004 で cancel 失敗・12時間放置）
3. **保守性低下**（Phase 64 移動済みコメント等の Dead code、CLAUDE.md / README.md の状態乖離）

→ GCP コスト ¥3,000 → ¥300-500 目標（83% 削減）+ 孤児SL再発防止 + クリーンアップ。

---

## 実装内容

### 💰 Infrastructure 5件（コスト削減）

#### I1: Cloud Logging WARNING 化（`-¥100~200/月`想定・実効ほぼゼロ）

- **対象**: `.github/workflows/ci.yml:359`
- **変更**: `LOG_LEVEL=INFO` → `LOG_LEVEL=WARNING`
- **Web 調査結果**: bot のログ量は無料枠 50GB/月 の数 % 程度 → 実効削減はほぼゼロ。実施意義は「将来の量増加に備える防御策」と「重要ログのみ残し可読性向上」

#### I2: Artifact Registry cleanup policy（`-¥20~50/月`）

- **新規**: `scripts/deployment/artifact-cleanup-policy.json`
- 30日以上前のイメージ削除 + 最新10件保持
- **適用方法**: `gcloud artifacts repositories set-cleanup-policies` を dry-run → 24h 監査ログ確認 → no-dry-run で本適用
- **重要**: 反映は約 1 日後にバックグラウンドジョブで実行（即時削除ではない）

#### I3: Cloud Run min_instances=0 + Cloud Scheduler 駆動化（`-¥970~¥2,400/月`想定）

最大規模の変更。orchestrator daemon ループから Cloud Scheduler 駆動 FastAPI に移行。

**新規**: `src/core/orchestration/trigger_server.py`
- FastAPI（既存依存）で `/trigger` (POST) + `/health` (GET) を提供
- 起動時 Firestore 接続確認 → 不通なら `/health` が 503 を返し Cloud Run readiness fail
- 1 リクエスト = 1 取引サイクル（`orchestrator.run_trading_cycle()` を 1 回実行）
- リクエスト処理中のみ CPU フル割当 → idle 時間は CPU 課金ゼロ

**修正**:
- `main.py`: `--mode trigger` 選択肢追加 + ローカル開発用 uvicorn 起動分岐
- `scripts/deployment/docker-entrypoint.sh`: `MODE=trigger` 時に `uvicorn` を直接 exec
- `.github/workflows/ci.yml`:
  - `MIN_INSTANCES=0`, `TIMEOUT=600`
  - `MODE=trigger` 環境変数で本番起動
  - `--no-allow-unauthenticated`（OIDC 必須化）

**Cloud Scheduler 設計値**:
- `--attempt-deadline=600s`: Cloud Run timeout と整合
- `--max-retry-attempts=2`: 過剰リトライで重複取引リスク防止
- `--schedule="*/5 * * * *"`: 既存 5 分間隔と同一
- OIDC token + `roles/run.invoker`

**Web 調査で判明した重要仕様**:
- Cloud Run idle timeout 約 15 分 → 5 分間隔リクエストでは scale-to-zero しない
- `--cpu-boost`/`--no-cpu-throttling` 未指定はデフォルト request-only → CPU 課金が 5 分中の処理時間（1-3分）のみに圧縮
- 削減効果は CPU allocation 設定の現状値次第（事前 gcloud 確認推奨）

#### I4: メモリ 1Gi → 512Mi（`-¥150/月`）

- **対象**: `.github/workflows/ci.yml:327`
- `MEMORY="1Gi"` → `MEMORY="512Mi"`
- Cloud Run 512MiB 時の最小 CPU は 0.08 vCPU、現状 `CPU=1` 維持で問題なし
- **検証**: デプロイ後 24h で OOM ログがないことを確認

#### I5: API キャッシュ TTL 拡張（先送り・Phase 89 候補）

- bitbank_client.py の fetch_ticker / fetch_order_book に既存キャッシュ機構がない
- 新規キャッシュ層構築が必要だが効果 ¥20-50/月で投資対効果薄
- → Phase 89 の OFI 特徴量導入時の WebSocket 化と同時実施予定

### 🟠 High 1件

#### H11: 孤児 SL 注文の再発防止（最重要・運用安定化）

**背景**: 2026-05-14 09:05 BUYポジ TP約定後の `cancel_order` が bitbank `70004` (transaction currently suspended) で失敗 → 12時間孤児SL放置。

**Web 調査結果**: bitbank `70004` = "We are unable to accept orders as the transaction is currently suspended" → リトライ可能な一時的エラー。

**実装** (`src/trading/execution/tp_sl_manager.py`):
- `_detect_and_cancel_orphan_sl()` 新規: margin_positions + active_orders 取得直後にスキャン
  - long ポジ無し + sell stop 注文 → 孤児
  - short ポジ無し + buy stop 注文 → 孤児
- `_cancel_with_exponential_backoff()` 新規: 指数バックオフ（1s / 2s / 4s）でリトライ
  - 70004 / "suspended" を判定して critical ログにマーク
  - 3 回連続失敗時は critical ログのみ・次の 5 分サイクルで再試行（無限ループ防止）

**設定** (`config/core/thresholds.yaml`):
```yaml
position_management.stop_loss.orphan_scan:
  enabled: true
  cancel_max_retries: 3
  cancel_base_delay_seconds: 1.0
```

**テスト** (`tests/unit/trading/execution/test_tp_sl_manager.py`): `TestPhase88H11OrphanSL` 6 件追加
- 孤児検出 / 正常SL扱い / 70004 リトライ成功 / 3回失敗 / 無効化 / short ポジ向け buy stop

### 🟡 Medium 5件 / 🟢 Low 3件

| ID | 内容 | 実装状況 |
|----|------|---------|
| M1 | Kelly 計算不能時の critical ログ明示 | ✅ 実装（kelly.py L218-225） |
| M2 | bitbank API rateLimit を thresholds.yaml 参照に統一 | ✅ 実装（`exchange.ccxt_rate_limit_ms`） |
| M3 | TP/SL 価格丸めポリシーを docstring に明文化 | ✅ 実装（tpsl_calculator.py） |
| M4 | 異常検知の時間帯別 Z スコア閾値 | 📌 マーカー追加・Phase 89 候補 |
| M5 | 税務 SQLite を GCS バックアップ方式へ | ✅ 実装（tax/gcs_persistence.py） |
| L1 | Phase XXX コメント整理 | 📌 Phase 89 候補（保守性のみ） |
| L2 | SUMMARY.md / Phase_88.md 整備 | ✅ Phase_88.md 作成 |
| L3 | Dead code 削除 + .dockerignore | ✅ 実装（14 ファイル削除 + .dockerignore 新規） |

### Phase A: ドキュメント同期

- `CLAUDE.md` L5-13 のしおりテーブルを「Phase 87 全 Stage 完了・本番デプロイ済 → Phase 88 着手予定」に書き換え
- `README.md` L7-22 / L141-179 / L200 / L212-214 / L224 を Phase 87 全 Stage 完了 + Phase 88 計画概要に同期

---

## 変更ファイル一覧

### 新規

| ファイル | 役割 |
|---|---|
| `src/core/orchestration/trigger_server.py` | I3: Cloud Scheduler 駆動 FastAPI アプリ |
| `tax/gcs_persistence.py` | M5: 税務 SQLite GCS バックアップ |
| `scripts/deployment/artifact-cleanup-policy.json` | I2: Artifact Registry リテンション設定 |
| `.dockerignore` | L3: Docker イメージ最小化 |

### 修正

| ファイル | 主な変更 |
|---|---|
| `CLAUDE.md` | しおり同期更新 (A) |
| `README.md` | 状態テーブル + 計画概要同期更新 (A) |
| `.github/workflows/ci.yml` | I1 LOG_LEVEL / I3 MIN_INSTANCES+TIMEOUT+MODE+no-allow-unauthenticated / I4 MEMORY |
| `src/trading/execution/tp_sl_manager.py` | H11 `_detect_and_cancel_orphan_sl` + `_cancel_with_exponential_backoff` + `ensure_tp_sl_for_existing_positions` 統合点 |
| `config/core/thresholds.yaml` | H11 orphan_scan / M2 ccxt_rate_limit_ms |
| `tests/unit/trading/execution/test_tp_sl_manager.py` | H11 `TestPhase88H11OrphanSL` 6 件 |
| `src/trading/execution/executor.py` | L3 移動済みコメント削除（15 行） |
| `main.py` | I3 `--mode trigger` 選択肢 + uvicorn 起動分岐 |
| `scripts/deployment/docker-entrypoint.sh` | I3 `MODE=trigger` 分岐 |
| `src/data/bitbank_client.py` | M2 rateLimit を get_threshold 参照に + I5 マーカー |
| `src/trading/risk/kelly.py` | M1 critical ログ追加 |
| `src/trading/execution/tpsl_calculator.py` | M3 価格丸めポリシー docstring |
| `src/trading/risk/anomaly.py` | M4 マーカー |
| `tax/trade_history_recorder.py` | M5 GCSTaxBackup 統合 + record_trade 直後の backup |

### 削除（L3 Dead code）

- `data/live_trades.db` / `data/trade_history.db` / `data/trades.db` (0 byte)
- `logs/orphan_sl_orders.json` (348 byte / 2026-01-31)
- `logs/test_*.log` 0 byte 9 ファイル
- `logs/trade_history.db` (0 byte)
- `src/trading/execution/executor.py:1436-1450` の Phase 64 移動済みコメント 15 行

---

## GCP コマンド実行手順（Phase 88 デプロイと並行・ユーザー側）

### 1. 事前確認（B-0 ステップ）

```bash
# 現状コスト内訳確認
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 \
  --format="yaml(spec.template.spec.containers[0].resources, spec.template.metadata.annotations)"

# CPU allocation 設定（cpu-throttling: true / false / 未設定）
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 \
  --format="value(spec.template.metadata.annotations.run\.googleapis\.com/cpu-throttling)"
```

### 2. Cloud Scheduler API 有効化

```bash
gcloud services enable cloudscheduler.googleapis.com
```

### 3. Cloud Scheduler 用 Service Account 作成 + 権限付与

```bash
gcloud iam service-accounts create crypto-bot-scheduler \
  --display-name="Crypto Bot Cloud Scheduler invoker"

SA_EMAIL="crypto-bot-scheduler@$(gcloud config get-value project).iam.gserviceaccount.com"
gcloud run services add-iam-policy-binding crypto-bot-service-prod \
  --region=asia-northeast1 \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker"
```

### 4. Cloud Scheduler ジョブ作成（5分間隔）

```bash
SERVICE_URL=$(gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 --format="value(status.url)")

gcloud scheduler jobs create http crypto-bot-trigger \
  --location=asia-northeast1 \
  --schedule="*/5 * * * *" \
  --time-zone="Asia/Tokyo" \
  --uri="${SERVICE_URL}/trigger" \
  --http-method=POST \
  --oidc-service-account-email="${SA_EMAIL}" \
  --oidc-token-audience="${SERVICE_URL}" \
  --attempt-deadline="600s" \
  --max-retry-attempts=2 \
  --min-backoff="30s" \
  --max-backoff="120s"
```

### 5. Artifact Registry cleanup policy 適用

```bash
# dry-run 確認
gcloud artifacts repositories set-cleanup-policies crypto-bot-repo \
  --location=asia-northeast1 \
  --policy=scripts/deployment/artifact-cleanup-policy.json \
  --dry-run

# 24h 待機後・監査ログ確認
gcloud logging read 'resource.type="artifactregistry.googleapis.com/Repository" AND protoPayload.metadata.validateOnly=true' --limit=20

# 本適用
gcloud artifacts repositories set-cleanup-policies crypto-bot-repo \
  --location=asia-northeast1 \
  --policy=scripts/deployment/artifact-cleanup-policy.json \
  --no-dry-run
```

### 6. GCS バケット作成 + 既存 DB 移行（M5）

```bash
# バケット作成
gsutil mb -l asia-northeast1 gs://crypto-bot-tax-backup

# Cloud Run の Service Account に objectAdmin 権限付与
CLOUD_RUN_SA=$(gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)")
gsutil iam ch serviceAccount:${CLOUD_RUN_SA}:objectAdmin gs://crypto-bot-tax-backup

# 初回マイグレーション
gsutil cp tax/trade_history.db gs://crypto-bot-tax-backup/trade_history.db
```

### 7. ロールバック手順

```bash
# Cloud Scheduler 停止 + Cloud Run min=1 復元
gcloud scheduler jobs pause crypto-bot-trigger --location=asia-northeast1
gcloud run services update crypto-bot-service-prod \
  --region=asia-northeast1 \
  --min-instances=1 \
  --memory=1Gi \
  --timeout=3600 \
  --allow-unauthenticated \
  --update-env-vars="MODE=live,LOG_LEVEL=INFO"
```

---

## 期待効果

| 項目 | Before | After |
|------|--------|-------|
| GCP 月額 | ¥3,000 | ¥300-500（83% 削減目標） |
| 孤児SL 残存リスク | 12時間放置事案あり | 5分以内に検出 + 3回リトライ + 70004 自動判定 |
| Cloud Run 常時稼働 | min_instances=1 | min_instances=0 + 5分ごと Cloud Scheduler 駆動 |
| Cloud Run CPU 課金 | リクエストレス daemon で 24h | リクエスト処理中（1-3分/サイクル）のみ |
| メモリ | 1 GiB | 512 MiB |
| Cloud Run 認証 | `--allow-unauthenticated` | OIDC 必須（Cloud Scheduler SA のみ） |
| 税務 SQLite | Cloud Run ephemeral FS で消失リスク | GCS バックアップで永続化 |
| Dead code | Phase 64 移動済みコメント等 | 削除 + `.dockerignore` で Docker 層から除外 |

---

## リスクと緩和策

| 順位 | リスク | 緩和策 |
|------|--------|--------|
| **高** | I3 cold start で 5 分間隔の取引機会逸失 | container/startup_latency メトリクス監視・Cloud Scheduler max-retries=2 |
| **高** | I3 Firestore 接続失敗時の状態消失 | trigger_server 起動時に /health が 503 で readiness fail |
| **高** | I3 `--no-allow-unauthenticated` で既存クライアントが叩けなくなる | scheduler SA 以外の access 棚卸し |
| **中** | H11 cancel リトライで bitbank レート制限抵触 | 指数バックオフ 1/2/4s で 7秒以内に完了 |
| **中** | M5 GCS 移行で既存 SQLite データ消失 | 初回デプロイ前に手動 `gsutil cp` でアップロード |
| **中** | I4 メモリ 512Mi で OOM | デプロイ後 24h で `OOMKilled` ログ監視 |
| **低** | B-1 WARNING 化で重要 INFO ログが消える | Phase 87 で重要箇所を critical/warning に格上げ済 |

---

## 検証手順

```bash
# 1. 全テスト
bash scripts/testing/checks.sh
# 期待: 2200+ tests passed (H11 で 6件追加), coverage 74%+

# 2. デプロイ後ヘルスチェック
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 \
  --format="value(status.conditions[0].status,status.url)"

# 3. Cloud Scheduler 実行確認
gcloud scheduler jobs describe crypto-bot-trigger --location=asia-northeast1

# 4. H11 ログ確認
gcloud logging read 'resource.type=cloud_run_revision AND textPayload=~"Phase 88 H11"' --limit=20

# 5. I3 trigger 動作確認
gcloud logging read 'resource.type=cloud_run_revision AND textPayload=~"Phase 88 I3"' --limit=20

# 6. メモリ使用率
gcloud logging read 'resource.type=cloud_run_revision AND severity=ERROR AND textPayload=~"OOMKilled|Memory limit"' --limit=10
```

---

## 次フェーズ

Phase 88 完了後、Phase 89（Webリサーチ統合: Purged K-Fold + Fractional Kelly + OFI + Funding Rate）へ。
詳細プラン: `~/.claude/plans/phase-iterative-biscuit.md`
