"""Phase 87/88 動作確認用 GCP メトリクス取得 wrapper（gcloud CLI ベース）。

設計:
- subprocess + gcloud CLI で Cloud Monitoring / Cloud Logging を呼び出す
- 既存 `scripts/live/standard_analysis.py` の `_count_gcp_logs` / `_fetch_gcp_logs` と
  同じパターン（google-cloud-monitoring ライブラリは追加しない）
- 認証失敗・gcloud 未インストール・timeout を全て吸収し、空 dict / 0 を返す fail-safe

公開関数（9 つ）:
- メモリ・インフラ系（I4 / I3 重点）
  - fetch_memory_percentiles
  - count_oom_incidents
  - fetch_cold_start_stats
  - fetch_trigger_endpoint_stats
- Phase 88 機能系
  - count_h11_orphan_sl_events
  - count_m5_gcs_backup_events
- Phase 87 機能系（補強）
  - count_recovery_testing_transitions
  - count_quality_filter_regime_outcomes
- 共通 helper
  - run_gcloud_logging_count
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

# Cloud Run のメモリ制限（Phase 88 R-Hc で 768Mi 確定）
MEMORY_LIMIT_MIB = 768.0

# subprocess 共通 timeout
_GCLOUD_TIMEOUT = 60

DEFAULT_SERVICE = "crypto-bot-service-prod"
DEFAULT_REGION = "asia-northeast1"

# Cloud Monitoring REST API endpoint
# 注意: gcloud CLI には `monitoring time-series list` サブコマンドが存在しないため、
# REST API + access token で直接取得する（curl 経由）。
_MONITORING_API_BASE = "https://monitoring.googleapis.com/v3/projects"


def _since_iso(hours: int) -> str:
    """ISO 形式（UTC）で `hours` 前の時刻文字列を返す。"""
    t = datetime.now(timezone.utc) - timedelta(hours=hours)
    return t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _run_subprocess(cmd: List[str], timeout: int = _GCLOUD_TIMEOUT) -> Optional[str]:
    """subprocess を共通エラーハンドリングで実行。失敗時は None。"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    except Exception:
        return None


# ========================================================================
# Cloud Logging ベースのカウント・取得 helper
# ========================================================================


def run_gcloud_logging_count(
    text_pattern: str,
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
    limit: int = 1000,
) -> int:
    """指定パターンを含むログ件数を返す（過去 `hours` 時間）。

    Args:
        text_pattern: gcloud logging クエリの正規表現（例: "Phase 88 H11"）
        hours: 集計対象時間
        service_name: Cloud Run サービス名
        limit: 取得上限（多すぎる場合はカウントが頭打ち）

    Returns:
        マッチした件数。エラー時は 0。
    """
    since = _since_iso(hours)
    query = (
        f'resource.type="cloud_run_revision" AND '
        f'resource.labels.service_name="{service_name}" AND '
        f'textPayload=~"{text_pattern}" AND '
        f'timestamp>="{since}"'
    )
    out = _run_subprocess(
        [
            "gcloud",
            "logging",
            "read",
            query,
            f"--limit={limit}",
            "--format=value(textPayload)",
        ]
    )
    if not out:
        return 0
    return len([line for line in out.strip().split("\n") if line])


def _fetch_logging_payloads(
    text_pattern: str,
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
    limit: int = 500,
) -> List[str]:
    """指定パターンに該当する textPayload を最大 limit 件取得。エラー時は []。"""
    since = _since_iso(hours)
    query = (
        f'resource.type="cloud_run_revision" AND '
        f'resource.labels.service_name="{service_name}" AND '
        f'textPayload=~"{text_pattern}" AND '
        f'timestamp>="{since}"'
    )
    out = _run_subprocess(
        [
            "gcloud",
            "logging",
            "read",
            query,
            f"--limit={limit}",
            "--format=value(textPayload)",
        ]
    )
    if not out:
        return []
    return [line for line in out.strip().split("\n") if line]


# ========================================================================
# Cloud Monitoring ベースのメトリクス取得
# ========================================================================


def _get_project_id() -> Optional[str]:
    """`gcloud config get-value project` でアクティブな project_id を取得。"""
    out = _run_subprocess(["gcloud", "config", "get-value", "project"])
    if not out:
        return None
    pid = out.strip()
    return pid or None


def _get_access_token() -> Optional[str]:
    """`gcloud auth print-access-token` で OAuth access token を取得。"""
    out = _run_subprocess(["gcloud", "auth", "print-access-token"])
    if not out:
        return None
    token = out.strip()
    return token or None


def _run_gcloud_monitoring(filter_expr: str, hours: int) -> List[Dict[str, Any]]:
    """Cloud Monitoring REST API でメトリクス time-series を JSON 取得。

    gcloud CLI には `monitoring time-series list` サブコマンドが存在しないため、
    REST API (`https://monitoring.googleapis.com/v3/projects/{pid}/timeSeries`) を
    curl で直接呼び出す。エラー時は []。
    """
    project_id = _get_project_id()
    if not project_id:
        return []
    token = _get_access_token()
    if not token:
        return []

    start_iso = _since_iso(hours)
    end_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    params = {
        "filter": filter_expr,
        "interval.startTime": start_iso,
        "interval.endTime": end_iso,
    }
    # URL-encode（filter 内のスペース・引用符を安全にエンコード）
    qs = urlencode(params, quote_via=quote)
    url = f"{_MONITORING_API_BASE}/{project_id}/timeSeries?{qs}"

    out = _run_subprocess(
        [
            "curl",
            "-s",
            "-H",
            f"Authorization: Bearer {token}",
            url,
        ],
        timeout=_GCLOUD_TIMEOUT,
    )
    if not out:
        return []
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            return data.get("timeSeries", []) or []
        return []
    except json.JSONDecodeError:
        return []


def _collect_point_values(series_list: List[Dict[str, Any]]) -> List[float]:
    """time-series JSON から point.value の数値を平坦化して取得。"""
    values: List[float] = []
    for series in series_list:
        for point in series.get("points", []):
            val = point.get("value", {})
            # double_value / int64_value / distribution_value(mean) の順に試す
            if "doubleValue" in val:
                values.append(float(val["doubleValue"]))
            elif "int64Value" in val:
                values.append(float(val["int64Value"]))
            elif "distributionValue" in val:
                mean = val["distributionValue"].get("mean")
                if mean is not None:
                    values.append(float(mean))
    return values


def _percentile(sorted_values: List[float], pct: float) -> float:
    """ソート済リストから percentile を取得。"""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_values) else f
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


# ========================================================================
# 公開関数: メモリ・インフラ系（I4 / I3 重点）
# ========================================================================


def fetch_memory_percentiles(
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
) -> Dict[str, Any]:
    """Phase 88 I4: Cloud Run メモリ使用率の P50 / P95 / P99 を取得。

    Cloud Monitoring metric: `run.googleapis.com/container/memory/utilizations`
    （0.0-1.0 の比率。768Mi 制限に対する使用率）。
    """
    filter_expr = (
        f'metric.type="run.googleapis.com/container/memory/utilizations" '
        f'AND resource.labels.service_name="{service_name}"'
    )
    series = _run_gcloud_monitoring(filter_expr, hours)
    values = _collect_point_values(series)
    if not values:
        return {
            "available": False,
            "memory_limit_mib": MEMORY_LIMIT_MIB,
            "reason": "no_data",
        }
    values.sort()
    p50 = _percentile(values, 0.50)
    p95 = _percentile(values, 0.95)
    p99 = _percentile(values, 0.99)
    max_v = values[-1]
    verdict = "OK"
    if max_v >= 0.95:
        verdict = "CRITICAL (memory >=95%)"
    elif p95 >= 0.85:
        verdict = "WARNING (P95 >=85%)"
    return {
        "available": True,
        "sample_count": len(values),
        "memory_limit_mib": MEMORY_LIMIT_MIB,
        "p50_ratio": round(p50, 4),
        "p95_ratio": round(p95, 4),
        "p99_ratio": round(p99, 4),
        "max_ratio": round(max_v, 4),
        "p50_mib": round(p50 * MEMORY_LIMIT_MIB, 1),
        "p95_mib": round(p95 * MEMORY_LIMIT_MIB, 1),
        "p99_mib": round(p99 * MEMORY_LIMIT_MIB, 1),
        "max_mib": round(max_v * MEMORY_LIMIT_MIB, 1),
        "verdict": verdict,
    }


def count_oom_incidents(
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
) -> Dict[str, Any]:
    """Phase 88 I4: OOM 発生件数を Cloud Logging から集計。

    Cloud Run の OOM は `Memory limit of X MiB exceeded` というテキストで記録される。
    """
    payloads = _fetch_logging_payloads(
        "Memory limit",
        hours=hours,
        service_name=service_name,
        limit=200,
    )
    return {
        "count": len(payloads),
        "last_occurrence": payloads[0] if payloads else None,
        "verdict": "OK" if not payloads else "CRITICAL",
    }


def fetch_cold_start_stats(
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
) -> Dict[str, Any]:
    """Phase 88 I3: cold start 回数と平均 / P95 レイテンシ。

    Cloud Monitoring metric: `run.googleapis.com/container/startup_latencies`
    """
    filter_expr = (
        f'metric.type="run.googleapis.com/container/startup_latencies" '
        f'AND resource.labels.service_name="{service_name}"'
    )
    series = _run_gcloud_monitoring(filter_expr, hours)
    values_ms = _collect_point_values(series)
    if not values_ms:
        return {"available": False, "count": 0, "reason": "no_data"}
    values_ms.sort()
    return {
        "available": True,
        "count": len(values_ms),
        "avg_ms": round(sum(values_ms) / len(values_ms), 1),
        "p95_ms": round(_percentile(values_ms, 0.95), 1),
        "max_ms": round(values_ms[-1], 1),
    }


def fetch_trigger_endpoint_stats(
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
) -> Dict[str, Any]:
    """Phase 88 I3: /trigger 呼び出しの成功 / 失敗カウント + 平均レイテンシ。

    成功は Cloud Logging の 200 OK ログ、失敗は 5xx ログから推定。
    """
    success_count = run_gcloud_logging_count(
        "trigger 実行|cycle_completed", hours=hours, service_name=service_name
    )
    failure_count = run_gcloud_logging_count(
        "trigger 実行失敗|trigger.*EMERGENCY_STOP",
        hours=hours,
        service_name=service_name,
    )

    # 平均レイテンシは request_latencies metric から取得
    filter_expr = (
        f'metric.type="run.googleapis.com/request_latencies" '
        f'AND resource.labels.service_name="{service_name}"'
    )
    series = _run_gcloud_monitoring(filter_expr, hours)
    values_ms = _collect_point_values(series)
    avg_ms = round(sum(values_ms) / len(values_ms), 1) if values_ms else None
    return {
        "success_count": success_count,
        "failure_count": failure_count,
        "total_count": success_count + failure_count,
        "avg_latency_ms": avg_ms,
        "verdict": "OK" if failure_count == 0 else f"WARNING ({failure_count} failures)",
    }


# ========================================================================
# 公開関数: Phase 88 機能系（H11 / M5）
# ========================================================================


def count_h11_orphan_sl_events(
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
) -> Dict[str, Any]:
    """Phase 88 H11: 孤児SL検出回数 + 70004 retryable/non-retryable 内訳。

    実装中のログ文言:
    - "Phase 88 H11: 孤児SL注文検出" (CRITICAL)
    - "Phase 88 H11: 孤児SLキャンセル成功" (INFO)
    - "Phase 88 H11: 孤児SLキャンセル失敗（リトライ可能）" (WARNING)
    - "Phase 88 H11: リトライ不可エラー、即時中断" (CRITICAL)
    - "Phase 88 H11: 孤児SL全N回キャンセル失敗" (CRITICAL)
    """
    detected = run_gcloud_logging_count(
        "Phase 88 H11: 孤児SL注文検出", hours=hours, service_name=service_name
    )
    cancel_success = run_gcloud_logging_count(
        "Phase 88 H11: 孤児SLキャンセル成功", hours=hours, service_name=service_name
    )
    retryable_fail = run_gcloud_logging_count(
        "Phase 88 H11: 孤児SLキャンセル失敗.*リトライ可能",
        hours=hours,
        service_name=service_name,
    )
    non_retryable = run_gcloud_logging_count(
        "Phase 88 H11: リトライ不可エラー、即時中断",
        hours=hours,
        service_name=service_name,
    )
    total_fail = run_gcloud_logging_count(
        "Phase 88 H11: 孤児SL全.*回キャンセル失敗",
        hours=hours,
        service_name=service_name,
    )
    return {
        "detected": detected,
        "cancel_success": cancel_success,
        "retryable_fail_attempts": retryable_fail,
        "non_retryable_abort": non_retryable,
        "exhausted_retries": total_fail,
        "verdict": (
            "OK"
            if detected == 0
            else f"DETECTED ({detected} 件、成功 {cancel_success} / 全失敗 {total_fail})"
        ),
    }


def count_m5_gcs_backup_events(
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
) -> Dict[str, Any]:
    """Phase 88 M5: GCS バックアップの restore / backup 成否を集計。"""
    restore_success = run_gcloud_logging_count(
        "Phase 88 M5: GCS .* ローカル復元完了",
        hours=hours,
        service_name=service_name,
    )
    backup_failure = run_gcloud_logging_count(
        "Phase 88 M5: GCS backup 失敗",
        hours=hours,
        service_name=service_name,
    )
    wal_warning = run_gcloud_logging_count(
        "Phase R-Ma: WAL checkpoint 失敗",
        hours=hours,
        service_name=service_name,
    )
    init_success = run_gcloud_logging_count(
        "Phase 88 M5: GCSTaxBackup 初期化成功",
        hours=hours,
        service_name=service_name,
    )
    return {
        "init_success": init_success,
        "restore_success": restore_success,
        "backup_failure": backup_failure,
        "wal_checkpoint_warning": wal_warning,
        "verdict": ("OK" if backup_failure == 0 else f"WARNING ({backup_failure} backup failures)"),
    }


# ========================================================================
# 公開関数: Phase 87 補強カバレッジ（H8 / H6 / C5）
# ========================================================================


def count_recovery_testing_transitions(
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
) -> Dict[str, Any]:
    """Phase 87 H8: RECOVERY_TESTING への遷移 + 完全復帰のカウント。"""
    entered = run_gcloud_logging_count(
        "Phase 87 H8.*RECOVERY_TESTING",
        hours=hours,
        service_name=service_name,
    )
    emergency_stop = run_gcloud_logging_count(
        "Phase 87 H8.*EMERGENCY_STOP",
        hours=hours,
        service_name=service_name,
    )
    recovered = run_gcloud_logging_count(
        "Phase 87 H8.*RECOVERY.*完了|RECOVERY_TESTING.*passed",
        hours=hours,
        service_name=service_name,
    )
    return {
        "entered_testing": entered,
        "recovered": recovered,
        "emergency_stop": emergency_stop,
    }


def count_quality_filter_regime_outcomes(
    hours: int = 24,
    service_name: str = DEFAULT_SERVICE,
) -> Dict[str, Any]:
    """Phase 87 H6: tight / normal / trending 各レジームでの品質フィルタ結果。"""
    tight_approved = run_gcloud_logging_count(
        "regime=tight_range.*承認|tight_range.*accept",
        hours=hours,
        service_name=service_name,
    )
    tight_rejected = run_gcloud_logging_count(
        "regime=tight_range.*拒否|tight_range.*reject",
        hours=hours,
        service_name=service_name,
    )
    normal_approved = run_gcloud_logging_count(
        "regime=normal_range.*承認|normal_range.*accept",
        hours=hours,
        service_name=service_name,
    )
    normal_rejected = run_gcloud_logging_count(
        "regime=normal_range.*拒否|normal_range.*reject",
        hours=hours,
        service_name=service_name,
    )
    trending_approved = run_gcloud_logging_count(
        "regime=trending.*承認|trending.*accept",
        hours=hours,
        service_name=service_name,
    )
    trending_rejected = run_gcloud_logging_count(
        "regime=trending.*拒否|trending.*reject",
        hours=hours,
        service_name=service_name,
    )
    return {
        "tight_range": {"approved": tight_approved, "rejected": tight_rejected},
        "normal_range": {"approved": normal_approved, "rejected": normal_rejected},
        "trending": {"approved": trending_approved, "rejected": trending_rejected},
    }
