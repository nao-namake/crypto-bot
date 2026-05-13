# Phase 87: SL CANCELED_UNFILLED 検出層構築 (Stage 1 + Stage 1-R)

**期間**: 2026年5月13日
**状態**: Stage 1 + Stage 1-R 実装完了 / Stage 2-3 未着手

---

## 背景: 2026-05-12 SL消失インシデント

Phase 86 デプロイ後、bitbank `fetch_order` 直接照会で SL消失機序が確定:

```
05:55:45 SL stop注文配置（ID=57247842273, trigger=12,732,347）
10:31:45 SL健在確認（limit=1, stop=1）
10:39:21 GCPログ「価格急変検出: Zスコア=3.31」
10:41:10 SLトリガー到達 → 成行決済試行
         流動性不足/スリッページ過大で約定失敗
         bitbank が自動 CANCELED_UNFILLED に遷移
10:46:34 bot検出: stop=0（CANCELED状態は fetch_open_orders に返らない）
         botは検出する仕組みを持たず、6時間以上裸ポジション放置
```

### 構造的正体（3層欠陥）

1. **bitbank仕様**: stop注文がトリガー発火後に約定失敗する状態（CANCELED_UNFILLED）が存在
2. **実装欠陥**: bot にそれを検出する仕組みが一切ない
3. **設計ループ未脱出**: Phase 78（stop_limit）↔ Phase 80（stop）の二択ループで本質を見落としていた

Phase 86 までは「TP/SL計算の正確化」「起動時SL自動修復」までを完了済み。
Phase 87 では「bot が SL異常を検出して自動復旧する」レイヤを新規構築する。

---

## 実装内容（Stage 1: Critical 4 + High 4）

9エージェント並列調査で確定した全28欠陥（C1-C5, H1-H10, M1-M5, L1-L3, I1-I5）のうち、
GCP変更不要で即日デプロイ可能な8項目を Stage 1 として実装した。

### Critical 4項目

#### C1: SLMonitor 新規実装 + CANCELED_UNFILLED 検出

**新規ファイル**: `src/trading/execution/sl_monitor.py`

```python
@dataclass
class SLHealthResult:
    is_healthy: bool
    failure_reason: Optional[str]  # canceled_unfilled / expired / rejected / timeout_24h / not_found / fetch_error
    requires_emergency_close: bool
    order_info: Optional[Dict[str, Any]]

class SLMonitor:
    @staticmethod
    def is_canceled_unfilled(order) -> bool: ...
    async def check_sl_health(sl_order_id, sl_placed_at_iso, bitbank_client, symbol) -> SLHealthResult: ...
    async def emergency_market_close(entry_side, amount, reason, bitbank_client, symbol) -> Optional[dict]: ...
```

- `fetch_order` で `info.status` を取得し、CANCELED_UNFILLED / EXPIRED / REJECTED を判定
- 反対側 market 注文（`is_closing_order=True`）で緊急成行決済
- `dry_run: true` 初期化で本番投入時の誤発火を回避する設計

#### C2: ML信頼度を `predicted_class_proba` に統一

**新規ヘルパー**: `src/core/orchestration/ml_confidence.py`

```python
def get_predicted_class_proba(probabilities) -> Tuple[int, float]:
    last = probabilities[-1] if probabilities.ndim > 1 else probabilities
    predicted_class = int(np.argmax(last))
    confidence = float(last[predicted_class])
    return predicted_class, confidence
```

旧 `float(np.max(probs[-1]))` を3箇所（`trading_cycle_manager.py:448`、`backtest_runner.py:684,1244`）で統一。
H10 (バックテスト vs ライブ整合性) の基盤となる。

#### C3: TP Maker timeout 時の確実 cancel_order

**修正**: `tp_sl_manager._place_tp_maker`

- ローカル関数 `_safe_cancel(order_id, context)` を新設し、timeout / リトライ / final_failure で確実にキャンセル
- PostOnly キャンセル時は `last_order_id = None` でクリアし二重キャンセル防止

#### C5: 5分ループ内 SL health check

**修正**: `tp_sl_manager.ensure_tp_sl_for_existing_positions`

冒頭で各 VP の `sl_order_id` を `fetch_order` で個別検証 → unhealthy なら `emergency_market_close` + VP削除。
既存の Step 1-3（margin_positions fetch・INACTIVE SL検証・カバレッジ判定）と競合しない位置に挿入。

### High 4項目

#### H1: SL 24h タイムアウト判定

**修正**: `stop_manager.check_stop_conditions`

各 VP の `sl_placed_at` ISO から 24h 超過を判定（API消費ゼロの軽量チェック）。超過時 `emergency_market_close(reason="sl_timeout_24h")`。
24h超過SLは流動性枯渇等で約定リスクが高いため強制成行決済。

#### H2: position_restorer サイレント失敗修正

**修正**: `position_restorer.py:269-323`

Phase 86 で起動時SL自動配置を実装したが、`emergency_sl_order={"id": None}` を返した場合に critical ログだけで素通りしていた。
else 分岐と except ブロックの両方で `sl_monitor.emergency_market_close` を呼ぶよう改修。

#### H7: `EXPECTED_FEATURE_COUNT` 共有定数化

**新規ファイル**: `src/features/constants.py`

```python
EXPECTED_FEATURE_COUNT: int = 37
STRATEGY_COUNT: int = 6
```

`feature_generator.py` の `expected_count=37` ハードコードを定数参照に変更。
不一致時の警告を `logger.warning` → `logger.critical` に格上げ（silent failure 防止）。

#### H9: 6戦略シグナル完全性アサート

**修正**: `feature_generator._add_strategy_signal_features`

`num_strategies != STRATEGY_COUNT` 時 `DataProcessingError` を raise。
`strategy_signals=None` 時は debug ログから warning へ格上げ（バックテスト事前計算では正常、ライブ運用では異常）。

### 設定追加 (`config/core/thresholds.yaml`)

```yaml
position_management.stop_loss:
  timeout_hours: 24                     # Phase 87 H1
  sl_monitor:
    enabled: true
    dry_run: true                       # 初期は dry_run でログのみ、安定後 false
```

---

## Stage 1-R: コードレビュー結果に基づく追加実装

Stage 1 完了後、3エージェント並列レビューで以下の不足を発見・補完した。

### R1: SLMonitor 統合連携テスト追加（3ファイル × 計7件）

新規 SLMonitor 単体は29テストで網羅されていたが、3つの統合点での連携フローテストが欠落していた。

- `test_position_restorer.py::TestPhase87H2EmergencyClose` (2件)
  - `test_restore_positions_emergency_close_on_empty_sl_id`
  - `test_restore_positions_emergency_close_on_exception`
- `test_stop_manager.py::TestPhase87H1Timeout` (2件)
  - `test_check_stop_conditions_timeout_24h_removes_vp`
  - `test_check_stop_conditions_no_timeout_keeps_vp`
- `test_tp_sl_manager.py::TestPhase87C5HealthCheckIntegration` + `TestPhase87C3TPMakerSafeCancel` (3件)
  - `test_ensure_tp_sl_health_check_triggers_emergency`
  - `test_place_tp_maker_safe_cancel_on_timeout`
  - `test_place_tp_maker_safe_cancel_on_final_failure`

### R2: ml_confidence エッジケーステスト追加（3件）

- 空配列で IndexError / ValueError を発生（silent failure 防止）
- NaN を含む probabilities でも戻り値の型は `(int, float)` を保つ
- n_classes=1 で predicted_class=0, confidence=1.0 を返す

### R3: docstring / コメント補強

- `sl_monitor._is_timed_out`: 「naive datetime は UTC として解釈」と明記
- `stop_manager.check_stop_conditions`: `bitbank_client is None` の理由（dry_run/backtest/paper 時）を明示
- `ml_confidence.get_predicted_class_proba`: 同値時 argmax 先勝ち（class 0 が選ばれる）の挙動を注記

### R4: バックテスト数値同一性検証テスト（新規・6件）

**新規ファイル**: `tests/integration/test_confidence_backward_compat.py`

旧 `float(np.max(probs[-1]))` と新 `get_predicted_class_proba(probs)[1]` が同一値を返すことを多様な分布（典型ケース5種 + ランダム100件）で検証。
H10 整合性の数学的基盤を確立。

---

## 変更ファイル一覧

### 新規

| ファイル | 役割 |
|---|---|
| `src/features/constants.py` | EXPECTED_FEATURE_COUNT / STRATEGY_COUNT 共有定数 (H7) |
| `src/core/orchestration/ml_confidence.py` | `get_predicted_class_proba` ヘルパー (C2/H10基盤) |
| `src/trading/execution/sl_monitor.py` | SLMonitor + SLHealthResult (C1/C5/H1/H2 共通基盤) |
| `tests/unit/trading/execution/test_sl_monitor.py` | SLMonitor 単体テスト 29件 |
| `tests/unit/core/orchestration/test_ml_confidence.py` | ヘルパー単体テスト 9件 |
| `tests/integration/test_confidence_backward_compat.py` | 数値同一性 6件 (R4) |

### 修正

| ファイル | 主な変更 |
|---|---|
| `src/features/feature_generator.py` | H7 定数参照 + critical 格上げ、H9 戦略数アサート |
| `src/core/services/trading_cycle_manager.py:448` | C2 ヘルパー化 |
| `src/core/execution/backtest_runner.py:684, 1244` | C2 ヘルパー化 |
| `src/trading/execution/position_restorer.py` | H2 サイレント失敗解消 + SLMonitor 初期化 |
| `src/trading/execution/stop_manager.py` | H1 24h タイムアウト判定 + SLMonitor 初期化 |
| `src/trading/execution/tp_sl_manager.py` | C5 5分ループ health check + C3 _safe_cancel + SLMonitor 初期化 |
| `config/core/thresholds.yaml` | timeout_hours / sl_monitor 設定追加 |
| `tests/unit/trading/execution/test_position_restorer.py` | R1-a H2 連携テスト 2件 |
| `tests/unit/trading/execution/test_stop_manager.py` | R1-b H1 連携テスト 2件 |
| `tests/unit/trading/execution/test_tp_sl_manager.py` | R1-c C5+C3 連携テスト 3件 |

---

## 品質ゲート結果

- **2122 tests passed, 1 skipped**（Stage 1 で +35件、Stage 1-R で +16件、合計 +51件）
- **カバレッジ 74.14%**（Phase 86 終了時 73.91% → +0.23%）
- flake8 / isort / black 全 PASS
- ML検証（37特徴量）/ システム整合性 PASS
- 実行時間 59秒

---

## 期待効果

1. **SL CANCELED_UNFILLED の構造的検出** - 5分以内に検出して緊急成行決済 → 6時間放置インシデントの再発を構造的に防止
2. **ML信頼度の意味の正確化** - メタラベリング判定で「予測クラスの確率」を使うようになり品質フィルタの判定が安定化
3. **TP Maker timeout の確実なキャンセル** - 重複TP配置リスク排除
4. **起動時SL欠損のサイレント失敗解消** - Phase 86 の `emergency_sl_order={"id": None}` 経路に safety net
5. **24h超過SLの強制決済** - 流動性枯渇等で機能不全になったSLを24hで切り捨て
6. **特徴量数・戦略数の silent failure 防止** - 37/6 から外れた場合に必ず critical ログ
7. **バックテスト/ライブ間の confidence 数値同一性** - H10 (整合性) の数学的保証

---

## Phase 87 残作業（Stage 2 + Stage 3）

Phase 87 全体15項目（C1-C5 + H1-H10）のうち、**完了 8項目 / 残 7項目**。

### Stage 2 (要 GCP Firestore セットアップ・未着手・4項目)

| ID | 内容 | 前提 |
|---|---|---|
| **H4** | SL状態を Firestore に永続化（ローカル `data/sl_state.json` → Cloud Run ephemeral FS消失対策） | Firestore Native モード有効化 + IAM `roles/datastore.user` |
| **H5** | DrawdownManager 状態を Firestore に永続化（連敗カウント・cooldown_until の Container 再起動保護） | 同上 |
| **C4** | DummyModel フォールバック時のサーキットブレーカー（`MLHealthMonitor` 新規・連続失敗で EMERGENCY_STOP） | H4-5 完了後（永続化必須） |
| **H3** | SL `stop_limit` + `slippage_buffer 0.008` の二重防衛実装（設定値は `stop` のまま、コードのみ先行投入） | なし |

### Stage 3 (運用観測強化・未着手・3項目 + 分析改修)

| ID | 内容 |
|---|---|
| **H6** | 品質フィルタ閾値のレジーム別化（tight 0.55 / normal 0.85 / trending 0.50） |
| **H8** | TradingStatus に RECOVERY_TESTING 追加（連敗保護の段階的復帰フロー） |
| **H10** | バックテスト vs ライブ整合性の E2E 統合テスト（R4 は計算ロジックのみ済、フルラン検証は未着手） |
| - | 分析スクリプト共通化（`scripts/analysis/lib/sl_validators.py` 他 + `standard_analysis.py` 改修） |

### 運用補強項目（任意）

- **R5** (Stage 1-R から先送り): CLAUDE.md に Phase 87 SLMonitor 運用フロー（dry_run 切替手順）を追記

---

## 注意点とリスク

1. **C1 SLMonitor 誤発火**: 初期 `dry_run: true` で出荷。本番投入後48-72h の観察期間で誤発火0件確認後 `false` に切替
2. **C2 confidence 変更**: 数学的には旧実装と等価（R4 で 106 ケース検証済）。ただし「同値時 argmax 先勝ち」の挙動で稀に class 0 が選ばれる
3. **C5 fetch_order API レート消費**: 5分ループ × 全 VP（≤10件）の `fetch_order` 呼び出し増加。bitbank 35秒制限内で安全だが、VP 数が増えた場合は要監視
4. **H1 timeout 判定の VP 削除順序**: stop_manager.check_stop_conditions の冒頭で削除するため、その後の `_check_take_profit_stop_loss` 処理の対象外となる。仕様上 OK

---

## デプロイ後の観測手順

```bash
# 1. 通常運用ログ
python3 scripts/live/standard_analysis.py --hours 24

# 2. CANCELED_UNFILLED 検出ログの存在確認（誤発火0件確認）
gcloud logging read 'resource.type=cloud_run_revision AND textPayload=~"CANCELED_UNFILLED"' --limit=20

# 3. dry_run シミュレーションログ
gcloud logging read 'resource.type=cloud_run_revision AND textPayload=~"DRY_RUN"' --limit=20

# 4. 24h timeout 発火（古いポジションがあれば）
gcloud logging read 'resource.type=cloud_run_revision AND textPayload=~"sl_timeout_24h"' --limit=10

# 5. 誤発火0件を48-72h確認後、dry_run: false へ
# config/core/thresholds.yaml: position_management.stop_loss.sl_monitor.dry_run: false
# git commit & push → 自動デプロイ
```

確認指標:
- `🚨 Phase 87 C1: 緊急成行決済発動` ログの頻度（dry_run=true なら `🧪 [DRY_RUN]` 表記）
- `🚨 Phase 87 H1: SL 24h超過検出` の有無（古いポジが滞留していないか）
- `🚨 Phase 87 H2: 起動時緊急SL配置で order_id 空` の有無（Phase 86 の retry が機能しているか）
- `🚨 Phase 87 H9: 戦略数不一致` の出現（thresholds.yaml の strategies が破損していないか）

---

## 想定スケジュール（Stage 2 以降）

- **Stage 2 着手前**: ユーザー側 GCP Firestore セットアップ（Firestore Native 有効化 + IAM 設定）
- **Stage 2**: 1週間（H3 / H4 / H5 / C4 実装 + テスト）
- **Stage 2 安定期**: 本番デプロイ後 72h 観察
- **Stage 3**: 1週間（H6 / H8 / H10 / 分析スクリプト共通化）

Phase 87 完了後、Phase 88（GCP コスト削減 = min_instances=0 + Cloud Scheduler）に進む。
Stage 2 の H4-5 (Firestore 永続化) が Phase 88 I3 の前提条件となる。
