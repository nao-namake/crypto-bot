# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 87 Stage 1 + Stage 1-R 実装完了**（ローカル）→ デプロイ待ち / Stage 2-3 未着手

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 87 Stage 1: SLMonitor 新規実装・ML信頼度統一・TP Maker _safe_cancel・H1 24h timeout・H2 サイレント失敗解消・H7 特徴量定数化・H9 戦略アサート / Stage 1-R: 連携テスト16件・docstring補強・数値同一性検証 |
| 品質ゲート | 2122 tests passed, カバレッジ 74.14%, flake8/isort/black 全PASS |
| ML方式 | メタラベリング（品質フィルタ Go/No-Go、Triple Barrier） |
| 特徴量 | 37特徴量（SHAP+Forward Selection最適化、LGB40%/XGB40%/RF20%） |
| 直近インシデント | 2026-05-12 10:41:10 SL stop注文がトリガー発火後 CANCELED_UNFILLED で約定失敗、6時間以上裸ポジ放置 → **Phase 87 Stage 1 で構造的に防止** |
| 次のアクション | (1) Stage 1 デプロイ + 48-72h dry_run 観察 → (2) `dry_run: false` 切替 → (3) Stage 2 (Firestore 永続化 H3/H4/H5/C4) → (4) Stage 3 (H6/H8/H10/分析共通化) |
| 最終更新 | 2026年5月13日 - Phase 87 Stage 1+1-R 完了 |

---

## 🚨 SL消失インシデント（2026-05-12）— Phase 87 着手の契機

### 機序（bitbank `fetch_order` 直接照会で確定）

```
05:55:45 SL stop注文配置（ID=57247842273, trigger=12,732,347）
10:31:45 SL健在確認（limit=1, stop=1）
10:39:21 GCPログ「価格急変検出: Zスコア=3.31」
10:41:10 SLトリガー到達 → 成行決済試行
         流動性不足/スリッページ過大で約定失敗
         bitbank が自動 CANCELED_UNFILLED に遷移
10:46:34 bot検出: stop=0（CANCELED状態は fetch_open_orders に返らない）
         botは検出する仕組みを持たず、ポジション裸放置
```

### 構造的正体

「過去にも繰り返されるSL配置漏れ」の3層欠陥:
1. bitbank stop注文がトリガー発火後に約定失敗する仕様（CANCELED_UNFILLED）
2. botがそれを検出する仕組みを一切持たない実装欠陥
3. Phase 78（stop_limit）↔ Phase 80（stop）の二択ループを抜け出していない設計

---

## 完了Phase

### Phase 87 Stage 1 + Stage 1-R ✅（2026-05-13 ローカル実装完了）
- **Critical 4件**: C1 SLMonitor 新規実装 / C2 ML信頼度 `predicted_class_proba` 統一 / C3 TP Maker `_safe_cancel` / C5 5分ループ内SL health check
- **High 4件**: H1 SL 24h timeout 判定 / H2 起動時SL欠損サイレント失敗解消 / H7 EXPECTED_FEATURE_COUNT 共有定数化 / H9 6戦略シグナル完全性アサート
- **Stage 1-R**: R1 統合連携テスト7件・R2 ml_confidenceエッジケース3件・R3 docstring補強3箇所・R4 数値同一性検証6件
- **品質ゲート**: 2122 tests passed, カバレッジ 74.14%, flake8/isort/black PASS
- **デプロイ前提**: `dry_run: true` 出荷 → 48-72h観察 → 誤発火0件確認後 `false` 切替
- 詳細: `docs/開発履歴/Phase_87.md`

### Phase 86: TP/SL/Entry根本再構築 ✅（2026-05-12 デプロイ）
- TPSLCalculator 単一実装化（旧4箇所分散を解消）
- bitbank API wrapper 強化（trigger_price 必須検証、配置後3秒×3回ポーリング）
- Atomic Entry 緊急成行決済（部分約定時のロールバック改善）
- 起動時SL自動修復（position_restorer.py 内）
- デプロイ後の実機検証: 現ポジへSL自動配置成功（trigger=12,732,347, 0.838%）

### Phase 85: レジーム別TP/SL再構築 ✅
- floor 0.7% 復活、trending エントリー停止
- レジーム別TP/SL（tight 1500/2000、normal 500/1500）
- sl_simulation.py の手数料加算バグ修正
- ML再学習（CV F1: LGB 0.602 / XGB 0.577 / RF 0.571）

### Phase 84: 品質フィルタ調整 ✅
- high_confidence_failure_threshold ハードコード→0.65 設定化
- confidence = max(p_0, p_1) 解釈に基づく閾値選定

### Phase 83A-3 / 83B / 83C: 固定金額TP/SL ✅
- 信頼度別TP/SL、SL floor 0.7% 強制
- 包括バグ修正13項目

### Phase 82: ゴーストポジション・SL異常値バグ修正 ✅
- ダスト検出ガード（min_valid_position_btc 0.001 BTC）
- SL極端値検出→配置中止

### Phase 81: stop_limit デッドコード削除 ✅
- Phase 62-68 構築の stop_limit 関連 818行削除

### Phase 80: SL注文タイプロールバック ✅
- stop_limit→stop（Phase 78 が逆効果と判明）
- Phase 69.8 の教訓を再確認

### Phase 71-79: パイプライン最適化・ML改善
（詳細は docs/開発履歴/Phase_71-81.md 参照）

---

## 🔧 Phase 87 + 88 完全リファクタリング 計画

### 概要

ユーザー要望「古いシステムを廃止し、最新の問題なく稼働するロジックだけを残したい」を実現する大規模リファクタリング。9回のExploreエージェント並列調査で **全23欠陥** を確定。

### 確定方針

- ✅ **実装範囲**: Phase 87 + 88 完全リファクタリング（全23欠陥対応）
- ✅ **永続化**: Firestore（無料枠内・月額0円）
  - bot 想定使用量: 約576 write/day vs 無料枠20,000 write/day
- ✅ **stop型**: stop_limit + slippage_buffer 0.008 で二重防衛（Phase 78/80 ジレンマ完全解決）

---

## 全23欠陥の包括リスト（重大度別）

### 🔴 Critical（5項目: 4/5 完了 ✅ / 残 1）

| # | 欠陥 | 状態 | 完了Phase |
|---|------|------|---------|
| C1 | SL CANCELED_UNFILLED 検出未実装 | ✅ 完了 | Stage 1 |
| C2 | ML信頼度計算が `max(p_0, p_1, p_2)` | ✅ 完了 | Stage 1 |
| C3 | TP Maker タイムアウト時の自動キャンセル無し | ✅ 完了 | Stage 1 |
| C4 | DummyModel フォールバックが品質フィルタモードで全拒否 | ⏳ **未着手** | Stage 2 予定 |
| C5 | 5分ループ内 SL health check 無し | ✅ 完了 | Stage 1 |

### 🟠 High（10項目: 4/10 完了 ✅ / 残 6）

| # | 欠陥 | 状態 | 完了/予定Phase |
|---|------|------|---------|
| H1 | SLタイムアウト判定（24h超過→強制決済）未実装 | ✅ 完了 | Stage 1 |
| H2 | Phase 86 サイレント失敗 | ✅ 完了 | Stage 1 |
| H3 | slippage_buffer 0.008 が定義済だが未使用 | ⏳ **未着手** | Stage 2 予定 |
| H4 | Phase 68.4 永続化が Cloud Run で機能しない | ⏳ **未着手** | Stage 2 (要GCP) |
| H5 | DrawdownManager の状態がContainer再起動でリセット | ⏳ **未着手** | Stage 2 (要GCP) |
| H6 | 品質フィルタ閾値がレジーム別採算ラインと矛盾 | ⏳ **未着手** | Stage 3 予定 |
| H7 | feature_count 不一致の silent ML failure | ✅ 完了 | Stage 1 |
| H8 | 連敗保護の解除即リセット | ⏳ **未着手** | Stage 3 予定 |
| H9 | 戦略シグナル完全性チェック無し | ✅ 完了 | Stage 1 |
| H10 | バックテスト vs ライブ整合性未確認 | 🟡 部分完了 | Stage 1-R (R4数値同一性のみ) / Stage 3 E2E未着手 |

### 🟡 Medium（Phase 88 で計画的に・5項目）

| # | 欠陥 | 影響 | ファイル |
|---|------|------|---------|
| M1 | Kelly基準のゼロサイズ理由が不明示 | 期待値負時のサイズ0で原因不明 | kelly.py:222-254 |
| M2 | bitbank API レート制限の実装と設定が不一致 | hardcode 200ms vs config 35000ms | bitbank_client.py:87 |
| M3 | TP/SL価格の丸め処理が不明示 | banker's rounding 意図不明 | tpsl_calculator.py |
| M4 | 異常検知が時間帯別に未調整 | 深夜と日中で同じZスコア閾値 | anomaly.py |
| M5 | 税務 SQLite が Container 再起動で失われる | 確定申告データ永続化破綻 | tax/trade_history.db |

### 🟢 Low（保守性向上・3項目）

| # | 欠陥 | 影響 | ファイル |
|---|------|------|---------|
| L1 | Phase XXX コメントが200ファイルに分散 | 保守負荷 | 全Pythonファイル |
| L2 | README.md と CLAUDE.md の乖離 | ユーザー混乱 | README.md |
| L3 | Dead code 削除計画なし | 約500行残存 | executor.py:1436-1450 等 |

### 💰 Infrastructure（GCPコスト削減・5項目）

**現状の月額 GCP コストは約3,000円**（CLAUDE.md 想定 700-900円の約3-4倍）。
最大の原因は Cloud Run の常時稼働（min_instances=1）。Phase 87/88 で構造的に削減する。

| # | 項目 | 削減効果 | Phase | 前提条件 |
|---|------|---------|-------|---------|
| I1 | Cloud Logging LOG_LEVEL DEBUG → WARNING | **-100~200円/月** | 88 (P1先行可) | なし（即時実施可能） |
| I2 | Artifact Registry リテンションポリシー | **-20~50円/月** | 88 (P1先行可) | なし（即時実施可能） |
| I3 | min_instances 1 → 0 + Cloud Scheduler 起動 | **-2,400円/月** | 88 (P0) | **Phase 87 H4-5 完了必須**（Firestore永続化なしでは状態消失） |
| I4 | Cloud Run メモリ 1GB → 512MB | **-150円/月** | 88 (P1) | Phase 87 完了後（feature_count等の安定化後） |
| I5 | bitbank API 呼び出しキャッシュ徹底 | **-20~50円/月** (Egress) | 88 (P2) | なし |

**目標**: 月額 3,000円 → **約300-500円**（**約83%削減**）

---

## Phase 87 実装計画（1-2週間）

### P0a: SLMonitor 新規実装（C1, C5）

**新規ファイル**: `src/trading/execution/sl_monitor.py`

```python
class SLMonitor:
    """SL注文のhealth check + CANCELED_UNFILLED 検出"""
    async def monitor_sl(self, vp, bitbank_client, symbol="BTC/JPY"):
        sl_order_id = vp.get("sl_order_id")
        order = await asyncio.to_thread(
            bitbank_client.exchange.fetch_order, sl_order_id, symbol
        )
        info_status = order.get("info", {}).get("status", "")
        if info_status == "CANCELED_UNFILLED":
            # 即時緊急成行決済
            return await self._emergency_market_close(vp, bitbank_client, symbol)
        ...
```

**統合先**: `executor.check_stop_conditions()` で5分ごと全VPに対して実行

### P0b: ML信頼度計算修正（C2）

**修正ファイル**: trading_cycle_manager.py:309-310, backtest_runner.py:257

```python
# 旧: confidence = float(np.max(ml_probabilities[-1]))
# 新:
predicted_class = int(np.argmax(ml_probabilities[-1]))
confidence = float(ml_probabilities[-1][predicted_class])
```

### P0c: TP Maker タイムアウト時の自動キャンセル（C3）

**修正ファイル**: order_strategy.py:120-160

タイムアウト時に `cancel_order()` を呼ぶ。

### P0d: DummyModel フォールバック警告（C4）

**修正ファイル**: ml_adapter.py:51-110

品質フィルタモードで DummyModel になったら critical ログ + サーキットブレーカー検討。

### P0e: 5分ループ内 SL health check（C5）

**修正ファイル**: tp_sl_manager.py:ensure_tp_sl_for_existing_positions

5分ごとに全VPに対して fetch_order(id) で個別検証 → CANCELED_UNFILLED 検出 → SLMonitor 起動。

### H1: SLタイムアウト判定実装

sl_placed_at から24h超過のSL → 強制決済。

### H2: Phase 86 サイレント失敗解消

position_restorer.py:269-293 で `emergency_sl_order={"id": None}` 時に critical ログ + 緊急成行決済。

### H3: stop_limit + slippage_buffer 0.008（Phase 78/80 ジレンマ解決）

```python
# tp_sl_manager.place_stop_loss
if order_type == "stop_limit":
    slippage_buffer = get_threshold("position_management.stop_loss.slippage_buffer", 0.008)
    if side == "buy":
        limit_price = stop_loss_price * (1 - slippage_buffer)
    else:
        limit_price = stop_loss_price * (1 + slippage_buffer)
```

**二重防衛**: 通常時 stop_limit で確実約定 + 価格急変時 CANCELED_UNFILLED → SLMonitor 緊急成行決済。

### H4-5: Firestore 永続化（無料枠内・月額0円）

**新規ファイル**: `src/core/persistence/firestore_state.py`

```python
class FirestoreStatePersistence:
    def __init__(self, bot_id="default"):
        self.db = firestore.Client()
        self.doc = self.db.collection("bots").document(bot_id)
    def save_sl_state(...): ...
    def save_drawdown_state(...): ...
```

**移行先**:
- sl_state_persistence.py の内部実装を Firestore に変更（API互換維持）
- drawdown.py の _save_state/_load_state を Firestore 経由

**🔑 GCPコスト削減（I3: min_instances=0）の前提条件**:
H4-5 は Phase 87 の SL対策のみならず、**Phase 88 I3（Cloud Run min=0 化による月額-2,400円削減）の必要条件**。状態を Firestore に永続化することで、Container 再起動時の VP・ドローダウン状態消失リスクを排除し、安全に min=0 へ移行可能となる。

### H6: 品質フィルタ閾値のレジーム別化

```yaml
ml.quality_filter:
  regime_thresholds:
    tight_range: { high_confidence_failure_threshold: 0.55 }
    normal_range: { high_confidence_failure_threshold: 0.85 }
    trending: { high_confidence_failure_threshold: 0.50 }
```

### H7: feature_count 一致確認

`EXPECTED_FEATURE_COUNT = 37` 共有定数化、特徴量数アサーション。

### H8: 連敗保護の段階的復帰

`TradingStatus.RECOVERY_TESTING` 状態追加、2-3取引の成功確認後完全復帰。

### H9: 戦略シグナル完全性チェック

6戦略全て揃っていることをアサート、不足時 critical ログ。

### H10: バックテスト vs ライブ整合性検証

confidence 計算の一貫性を統合テストで確認。

### 分析スクリプト改修

1. **新規 `scripts/analysis/lib/`** - 共通ライブラリ化
   - `sl_validators.py` (SL検証)
   - `canceled_unfilled_detector.py` (新規)
   - `tp_sl_calculator.py` (Phase 85 修正版で統一)
2. **`scripts/live/standard_analysis.py` 改修**:
   - `missing_sl_detected` を金額ベース→件数ベースに修正
   - C1-C5 新規検出機能追加
3. **`scripts/backtest/standard_analysis.py` 改修**:
   - Phase 85 手数料修正適用
   - 共通ライブラリ使用

---

## Phase 88 実装計画（2-3週間）

### 💰 Infrastructure（GCPコスト削減・最優先）

**目標**: 月額 GCP コスト **3,000円 → 約300-500円（83%削減）**

#### I1 + I2: 即時削減（リスク低・Phase 88 着手と同時）

```bash
# I1: Cloud Logging レベル変更（-100~200円/月）
gcloud run services update crypto-bot-service-prod \
  --region=asia-northeast1 \
  --update-env-vars=LOG_LEVEL=WARNING

# I2: Artifact Registry リテンションポリシー（-20~50円/月）
# 30日以上前の古いイメージを自動削除
gcloud artifacts repositories set-cleanup-policies crypto-bot-repo \
  --location=asia-northeast1 \
  --policy=scripts/deployment/artifact-cleanup-policy.json
```

**前提条件**: なし
**実施タイミング**: Phase 88 着手と同時、または Phase 87 完了直後に即時実施可能
**リスク**: なし（DEBUG ログは必要時のみ一時的に戻せる）

#### I3: min_instances=0 + Cloud Scheduler 起動（最大削減効果）

```bash
# 前提: Phase 87 H4-5 (Firestore永続化) 完了済みであること

# Step 1: Cloud Scheduler ジョブ作成（5分間隔）
gcloud scheduler jobs create http crypto-bot-trigger \
  --location=asia-northeast1 \
  --schedule="*/5 * * * *" \
  --http-method=POST \
  --uri=https://crypto-bot-service-prod-xxx.run.app/trigger \
  --oidc-service-account-email=cloud-scheduler-sa@PROJECT.iam.gserviceaccount.com

# Step 2: Cloud Run を on-demand 化
gcloud run services update crypto-bot-service-prod \
  --region=asia-northeast1 \
  --min-instances=0 \
  --max-instances=2 \
  --timeout=300

# Step 3: main.py に /trigger エンドポイントを追加（5分処理を1回実行）
# 起動毎に：
#   1. Firestore から状態復元（VP, ドローダウン, SL状態）
#   2. 5分処理サイクル実行
#   3. 状態を Firestore に保存
#   4. プロセス終了
```

**削減効果**: **-2,400円/月**（Cloud Run 常時稼働分が0に）
**前提条件**: **Phase 87 H4-5 (Firestore永続化) 完了必須**
**リスク**: Cold start 5-10秒（5分間隔なら許容範囲）
**コード変更**:
- `main.py`: Cloud Scheduler 用 `/trigger` HTTP エンドポイント追加
- `src/core/orchestration/`: 起動・終了ライフサイクル最適化
- `tax/trade_history.db` 等のローカル状態は M5 (GCS化) 完了後に min=0 可能

#### I4: Cloud Run メモリ最適化

```bash
# Phase 87 完了後（特徴量数37の安定化後）
gcloud run services update crypto-bot-service-prod \
  --region=asia-northeast1 \
  --memory=512Mi \
  --cpu=0.5
```

**削減効果**: **-150円/月**
**前提条件**: Phase 87 完了、ML推論ピークメモリ確認
**検証**: ペーパートレードで30分稼働し、メモリ使用量 < 400MB 確認

#### I5: bitbank API キャッシュ徹底（Egress 削減）

- `src/data/data_pipeline.py`: 既存キャッシュ TTL の見直し
- 不要な再フェッチを排除
- WebSocket 移行は Phase 91 で（Phase 88 では REST のキャッシュ強化のみ）

**削減効果**: **-20~50円/月**

#### 検証

```bash
# 削減前後のコスト比較
gcloud billing accounts get-spend-information \
  --account=<ACCOUNT_ID> \
  --start-time=2026-05-01 \
  --end-time=2026-05-31

# Cloud Run 使用量確認
gcloud monitoring time-series list \
  --filter="metric.type=\"run.googleapis.com/container/cpu/allocation_time\"" \
  --interval-start-time=2026-05-01T00:00:00Z
```

---

### Medium 対応
- M1: Kelly基準のゼロサイズ理由を明示化
- M2: bitbank API レート制限の hardcode を config 化
- M3: TP/SL価格の丸め処理を明示化（TP下丸め・SL上丸め）
- M4: 異常検知の時間帯別調整
- M5: 税務 SQLite を GCS/Cloud SQL に移行（I3 の min=0 化の前提でもある）

### Low / クリーンアップ
- L1: Phase XXX コメント整理（Phase 88で統一）
- L2: README.md を CLAUDE.md と整合
- L3: Dead code 一括削除（約500行）
  - executor.py:1436-1450 の「移動済み」コメント
  - stop_manager.py:1600-1604 の「移動済み」コメント
  - bitbank_client.py:1197-1219 stop_limit旧分岐（H3で再活用しない部分）
  - 0byte DB ファイル（data/trades.db, data/live_trades.db, etc.）
  - logs/orphan_sl_orders.json（Phase 59.6）
  - data/sl_state.json（ローカル汚染）
- .dockerignore 新規作成（防御）

### 重複統合
- TradeHistoryRecorder + TradeAnalysisRecorder 統合
- TP/SL欠損検出 4経路 → 2経路
- PositionRestorer → PositionTracker 経由化（カプセル化）

### テストカバレッジ
- test_sl_monitor.py（CANCELED_UNFILLED検出）
- test_canceled_unfilled_recovery.py（E2E）
- test_container_restart.py（VP復元、ドローダウン状態復元）
- test_confidence_calculation.py（max vs predicted_class_proba）
- test_tp_sl_manager.py:768 を tmp_path フィクスチャに変更
- test_cloud_scheduler_trigger.py（Cloud Scheduler 起動シナリオ・I3用）

---

## 緊急対応（並行・ユーザー実施）

bitbank UI で手動SL設置:
- side: sell, type: stop, amount: 0.015
- trigger: 12,732,347 or 現価格ベースで再計算

→ Phase 87 実装中も裸ポジ解消

---

## 検証方法

### Phase 87 P0 実装後
```bash
bash scripts/testing/checks.sh
# 全テスト成功・75%+カバレッジ・新規テスト成功
```

### ペーパートレード統合検証
```bash
bash scripts/paper/run_paper.sh
# 意図的に bitbank UI で SL注文をキャンセル → 5分以内に bot が検出・再配置
# CANCELED_UNFILLED 検出動作確認
```

### 本番デプロイ後24-48時間観測
```bash
python3 scripts/live/standard_analysis.py --hours 24
# 期待: SLカバレッジ100%、CANCELED_UNFILLED自動復旧成功ログ
```

---

## 期待される効果

| 改善項目 | Before | After |
|---------|--------|------|
| SL CANCELED_UNFILLED 検出 | 完全未実装 | 5分以内に検出・即時成行決済 |
| 稼働中のSL消失対応 | 警告ログのみ | 自動再配置 or 緊急成行決済 |
| 価格急変時のSL約定 | stop で失敗 | stop_limit + buffer で確実 |
| SL超過タイムアウト | 未実装 | 24hで強制決済 |
| ML信頼度の意味 | max(p_0,p_1,p_2) で誤解 | predicted_class_proba で正確 |
| TP Maker タイムアウト | 重複TP配置リスク | 自動キャンセル → 次ループ新規 |
| ML予測失敗時 | サーキットブレーカー無し | DummyModel 検出 → critical ログ |
| 連敗保護 | 即解除→再連敗リスク | RECOVERY_TESTING 経由で段階復帰 |
| ドローダウン状態 | Container再起動でリセット | Firestore で永続化 |
| 品質フィルタ閾値 | 一律0.65 で採算ラインと矛盾 | レジーム別で採算と整合 |
| 戦略シグナル完全性 | 0埋め silent | アサート + critical ログ |
| 分析スクリプト | missing_sl_detected が誤検出 | 件数ベースで正確 |
| Dead code | ~500行残存 | コアロジックのみ |
| 構造的SL配置漏れ | 未解決 | 構造的に防止 |

---

## 詳細プラン

実装計画の詳細: `/Users/nao/.claude/plans/golden-spinning-liskov.md`

---

## Phase 89-92 中長期計画（Webリサーチ結果に基づく）

> **進め方（ユーザー確定方針）**:
> - Phase 87/88 完了 → 都度 Phase 89+ を再計画
> - まず基盤を固め、安定動作を確認してから拡張
> - Phase 92 (PPO 強化学習) は Phase 91 完了時の Sharpe比達成状況で再検討

### 背景

最新MLbot技術（2024-2026）の Webリサーチで判明した既存botとのギャップを段階的に解消し、年利10% → 15-18% を目指す。

### 既存bot vs 最新MLbot ギャップ分析

| 領域 | 既存bot | 最新MLbot技術 | ギャップ | 追加コスト |
|------|---------|--------------|--------|----------|
| 特徴量 | OHLCV由来37個 | + オーダーブック (OFI/VPIN/OBI) + ファンダ (Funding/OI/Fear&Greed) + センチメント (LLM) | ⭐⭐⭐⭐ | 0円可 |
| 時系列予測 | LGB/XGB/RF アンサンブル | Transformer (Informer/Autoformer) / N-BEATS / TFT | ⭐⭐⭐⭐ | 0円可（軽量版） |
| 検証手法 | Walk-Forward 単一回 | Purged K-Fold CV + CPCV + DSR | ⭐⭐⭐ | 0円 |
| ポジションサイジング | Kelly基準（機能不全） | Fractional Kelly + Volatility Targeting + CVaR | ⭐⭐⭐ | 0円 |
| レジーム検出 | 4段階ルールベース | HMM (3-5状態) + BOCPD | ⭐⭐⭐ | 0円 |
| 取引戦略 | レンジ型重視（トレンド型重み0%） | 強化学習 (PPO/TD3/SAC) + マルチタイムフレーム融合 | ⭐⭐⭐⭐ | 0円可（PPOはGPU要） |
| モデル監視 | 手動 | Drift Detection (KL/KS) + Automated Retraining | ⭐⭐⭐ | 0円 |
| 約定戦略 | Maker実装も Taker率100% | Smart Routing + Queue Position Modeling | ⭐⭐⭐ | 0円 |
| データ取得 | REST polling (5分間隔) | WebSocket real-time depth stream | ⭐⭐⭐ | 0円 |
| クロスアセット | BTC/JPY単一 | BTC-ETH相関 + Funding rate arbitrage | ⭐⭐⭐ | 0円可 |

---

### Phase 89: シグナル品質向上（即時着手・月額0円・1ヶ月）

最も費用対効果が高く、現スケール（証拠金50万円・月額予算900円）で確実に効果が出る項目。

#### P1 必須項目

1. **Purged K-Fold CV 導入**（López de Prado）
   - lookahead bias 完全排除、CPCV で統計信頼性向上、DSR テスト
   - 工数: 2週間、効果: 検証信頼性 +30%

2. **Fractional Kelly + Volatility Targeting**
   - Full Kelly → 0.5倍 (Half Kelly) で安定性向上
   - target_vol=20% で動的レバレッジ調整
   - 工数: 1週間、効果: Max DD -20%

3. **Drift Detection 基本実装**
   - KL divergence / Kolmogorov-Smirnov test
   - Slack/Discord 通知 or Cloud Logging アラート
   - 工数: 2週間、効果: 自動アラート機能化

4. **OFI (Order Flow Imbalance) 特徴量追加**
   - 37 → 47-50 特徴量に拡張
   - 既存 `data/orderbook/` を活用
   - 過去研究で 65-87% の価格分散説明率
   - 工数: 3日、効果: リターン +0.8-1.5%

5. **外部シグナル統合（無料API）**
   - Binance Funding Rate（買い圧/売り圧の先行指標）
   - Open Interest 変化率
   - Fear & Greed Index（alternative.me free）
   - 工数: 3-5日、効果: シグナル精度 +10-15%

#### P2 検討項目
6. **Optuna ハイパーパラメータ自動最適化**
   - 工数: 2週間、効果: 戦略パラメータ最適化

---

### Phase 90: 時系列予測モデル + センチメント（2-3ヶ月・月額~300円）

Cloud Run 環境（メモリ512MB）で動作可能な軽量最新技術。

1. **N-BEATS 軽量版 試験導入**
   - GPU不要、メモリ ~50MB、推論時間 ~100ms
   - 既存 ProductionEnsemble に4つ目モデルとして追加
   - 工数: 4週間、効果: リターン +5-10%

2. **LLM センチメント統合（Claude API）**
   - ニュース記事の DK-CoT
   - 月額 100-300円程度（予算内）
   - 工数: 3週間、効果: シグナル精度 +10-15%

3. **HMM レジーム検出（4 → 3-5状態細分化）**
   - hmmlearn (Python) で Gaussian HMM
   - 既存ルールベースの**補強**
   - 研究事例: Sharpe Ratio 0.8 → 1.9
   - 工数: 4-5日、効果: 年利 +1.0-2.0%

4. **Automated Retraining Pipeline**
   - Drift Detection trigger 連動
   - Shadow Deployment、自動ロールバック
   - 工数: 2週間、効果: 自動最適化

5. **VPIN 計算**
   - 流動性悪化・toxic flow の早期検知
   - 工数: 2-3日、効果: リスク管理 +0.5-1.0%

---

### Phase 91: マーケットマイクロ構造（オーダーブック活用・月額0円）

1. **WebSocket depth stream 接続**
   - Bitbank `wss://stream.bitbank.cc/...`
   - REST polling (5秒) → WebSocket (100ms バッファ)
   - 工数: 3-4日、効果: 反応速度3-5秒 → 200-500ms

2. **OFI/OBI/Weighted Mid-Price 統合**
   - 既存特徴量と組み合わせて 50-55 特徴量
   - 多層レベル OFI (MLOFI) で精度向上
   - 工数: 1-2週間、効果: リターン +1-3%

3. **Maker 戦略の真の実装化（現状 Taker 100%）**
   - Queue Position Modeling（hftbacktest 参考）
   - post_only 価格の動的最適化
   - 工数: 2-3週間、効果: 年利 +0.5-1%

4. **BTC-ETH 相関活用**
   - Binance ETH/USDT データから 30-60日 rolling 相関
   - 相関急低下 → market stress → ポジション縮小
   - 工数: 1週間、効果: ドローダウン制御強化

---

### Phase 92: 高度化・条件付き実装（3ヶ月以上・Phase 91 完了後再検討）

**条件**: Phase 91 完了時 Sharpe比 > 2.0、3ヶ月ライブ取引で信頼性確認

1. **PPO 強化学習試験運用**（条件付き）
   - FinRL ベース、限定 5% capital
   - GPU 月500-1000円コスト
   - 工数: 6-8週間、効果: 期待 +3-5%（不確実）

2. **マルチペア展開**
   - BTC/JPY → + ETH/JPY、ADA/JPY
   - 工数: 4-6週間、効果: リターン +2-5%

3. **Transformer 本格導入**
   - Autoformer / Informer
   - Cloud Functions GPU 移行検討
   - 工数: 8-12週間、リスク: 高

---

### 段階的導入ロードマップ

| 期間 | Phase | 内容 | 期待 Sharpe | 期待年利 |
|------|-------|------|------------|--------|
| Week 1-3 | **Phase 87** | 決済システム再構築（C1-C5, H1-H10） | 維持 | 維持 |
| Week 4-6 | **Phase 88** | 運用基盤・クリーンアップ（M1-M5, L1-L3） | 1.5 | 10% (現状) |
| Month 2-3 | **Phase 89** | シグナル品質向上 | 1.8-2.0 | 12-13% |
| Month 4-6 | **Phase 90** | N-BEATS + LLM + HMM | 2.0-2.3 | 14-16% |
| Month 7-9 | **Phase 91** | WebSocket + Maker戦略 + クロスアセット | 2.2-2.5 | 15-18% |
| Month 10+ | **Phase 92** | PPO / マルチペア / Transformer（条件付き） | 2.3-2.8 | 17-20% |

---

### Phase 89-92 で参照すべきオープンソース・論文

- **Marcos Lopez de Prado**「Advances in Financial Machine Learning」（Triple Barrier、Purged K-Fold の原典）
- **N-BEATS**: https://github.com/philipperemy/n-beats（軽量、Cloud Run動作可）
- **Microsoft Qlib**: https://github.com/microsoft/qlib（Alpha158 特徴セット参考）
- **FinRL**: https://github.com/AI4Finance-Foundation/FinRL（強化学習）
- **Freqtrade**: https://github.com/freqtrade/freqtrade（戦略パイプライン参考）
- **hftbacktest**: https://github.com/nkaz001/hftbacktest（Queue Position Modeling）
- **DeepLOB**: https://arxiv.org/abs/1808.03668（オーダーブック CNN）
- **VPIN**: https://www.quantresearch.org/VPIN.pdf

---

### Phase 87/88 への影響（保持すべき設計）

Phase 89-92 で追加される機能は、Phase 87/88 の以下の設計を**前提**として動作:
- **Registry Pattern**: 新戦略・新ML モデルの追加が容易
- **thresholds.yaml 一元化**: 新特徴量・新閾値もここで管理
- **メタラベリング品質フィルタ**: 新モデルもメタラベリングで品質保証
- **Firestore 永続化（Phase 87 H4-5）**: HMM 状態、Drift Detection 結果も永続化
- **SLMonitor（Phase 87 P0a）**: 新戦略でも CANCELED_UNFILLED 検出が自動

→ Phase 87/88 を「土台」として、Phase 89-92 は段階的に積み上げる構造

---

### Phase 89-92 期待効果サマリー

| 項目 | Phase 88完了時 | Phase 89完了時 | Phase 90完了時 | Phase 91完了時 |
|------|--------------|--------------|--------------|--------------|
| 年利 | 10% | 12-13% | 14-16% | 15-18% |
| Sharpe比 | 1.5 | 1.8-2.0 | 2.0-2.3 | 2.2-2.5 |
| Max DD | 8-10% | 6-7% | 5-6% | 4-5% |
| 特徴量数 | 37 | 47-50 | 50-55 | 55-60 |
| 月額追加コスト | 0円 | 0円 | ~300円 | ~300円 |

---

**最終更新**: 2026年5月13日 - Phase 87/88 + Phase 89-92 中長期計画（Webリサーチ統合版）策定
