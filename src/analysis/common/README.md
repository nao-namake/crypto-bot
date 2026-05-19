# src/analysis/common/ - 分析共通モジュール

ライブ分析・バックテスト分析・テストから利用される共通分析ユーティリティ。Phase 87 Stage 3 で新規作成。

## ファイル構成（Phase 90α）

| ファイル | 行数 | 役割 | 起源 Phase |
|---|---|---|---|
| `gcp_metrics.py` | 835 | Cloud Monitoring / Logging メトリクス取得（メモリ・cold start・H11 孤児SL・M5 GCS バックアップ・H8 段階復帰・H6 品質フィルタ・Phase 89 gating/drift/N-BEATS/WebSocket/Kelly・Phase 90α メタラベリング監視）| Phase 88 拡充 |
| `canceled_unfilled_detector.py` | 203 | SL 注文の CANCELED_UNFILLED / EXPIRED / REJECTED 検出 | Phase 87 C1 |
| `sl_validators.py` | 125 | SL 状態の妥当性検証（trigger_price・有効性チェック）| Phase 87 H2 |
| `tp_sl_helpers.py` | 59 | TP/SL 距離計算・手数料込み実効率算出ヘルパー | Phase 87 R4 |

## gcp_metrics.py 主要関数（17 関数）

### Cloud Logging ベース（カウント取得）

| 関数 | 役割 |
|---|---|
| `run_gcloud_logging_count(filter, hours)` | 汎用カウント |
| `count_oom_incidents(hours)` | OOM 発生数 |
| `count_h11_orphan_sl_events(hours)` | 孤児 SL 検出数（Phase 88 H11）|
| `count_m5_gcs_backup_events(hours)` | GCS バックアップ成功/失敗（Phase 88 M5）|
| `count_recovery_testing_transitions(hours)` | RECOVERY_TESTING 遷移（Phase 87 H8）|
| `count_quality_filter_regime_outcomes(hours)` | 品質フィルタ accept/reject（Phase 87 H6）|

### Cloud Monitoring ベース（メトリクス取得）

| 関数 | 役割 |
|---|---|
| `fetch_memory_percentiles(hours)` | メモリ使用率 P50/P95/P99（**Phase 88 I4: 768Mi 制限**）|
| `fetch_cold_start_stats(hours)` | Cold start 回数 + レイテンシ（Phase 88 I3）|
| `fetch_trigger_endpoint_stats(hours)` | `/trigger` endpoint 統計 |

### Phase 89 機能監視

| 関数 | 役割 |
|---|---|
| `count_phase89_gating_stats(hours)` | Phase 89-α gating の monitor_only スキップ率 |
| `count_phase89_drift_events(hours)` | Phase 89-β Drift 検出件数 |
| `count_phase89_nbeats_health(hours)` | Phase 89-γ N-BEATS 健全性 |
| `count_phase89_websocket_status(hours)` | Phase 89-δ WebSocket 接続 |
| `count_phase89_kelly_safety(hours)` | Phase 89-β Fractional Kelly safety_factor |

### Phase 90α メタラベリング監視

| 関数 | 役割 |
|---|---|
| `count_phase90_quality_filter_stats(hours)` | 品質フィルタ accept/reject/uncertain 比率 |
| `count_phase90_ml_prediction_dist(hours)` | 高品質/低品質ラベル分布 + 旧 3 クラス残存検出 |
| `count_phase90_model_health(hours)` | DummyModel フォールバック + 予測失敗 + サーキットブレーカー候補 |

### 重要定数

```python
MEMORY_LIMIT_MIB = 768.0  # Phase 88 I4 で 1Gi → 768Mi に削減
```

## canceled_unfilled_detector.py

bitbank stop 注文の **CANCELED_UNFILLED 検出**（Phase 87 C1）。トリガー発火後に流動性不足/スリッページ過大で約定失敗 → bitbank が自動的に CANCELED 遷移 → ポジション裸放置を検出して緊急成行決済。

```python
class CanceledUnfilledDetector:
    def detect_canceled_unfilled(self, sl_order_id, bitbank_client) -> bool
    def is_canceled_state(self, order_status) -> bool
```

## sl_validators.py

SL 注文の妥当性検証ヘルパー。

```python
def validate_sl_trigger_price(price, current_price, action) -> bool
def is_sl_active(order_status) -> bool
```

## tp_sl_helpers.py

TP/SL 距離計算・実効率算出。

```python
def calculate_tp_distance_ratio(tp_price, entry_price, action) -> float
def calculate_sl_distance_ratio(sl_price, entry_price, action) -> float
```

## 関連リンク

- 親 README: [../README.md](../README.md)
- ライブ分析: [../../scripts/live/standard_analysis.py](../../scripts/live/standard_analysis.py)
- バックテスト分析: [../../scripts/backtest/standard_analysis.py](../../scripts/backtest/standard_analysis.py)
- テスト: [../../tests/unit/analysis/common/](../../tests/unit/analysis/common/)

---

**最終更新**: 2026年5月19日（Phase 90α: 新規作成・Phase 87/88/89/90α 全機能対応・MEMORY_LIMIT_MIB 768.0 反映）
