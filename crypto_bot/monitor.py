# =============================================================================
# File: crypto_bot/monitor.py
# Description:
#   Streamlit dashboard to monitor Crypto Bot status and push custom metrics
#   (PnL, trade count, position flag) to Cloud Monitoring so they can be shown
#   on a Cloud Monitoring dashboard / alert policy.
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import os

import streamlit as st
from google.cloud import monitoring_v3

# ---------------------- Streamlit basic settings -----------------------------
st.set_page_config(page_title="Crypto‑Bot Monitor", page_icon="📈", layout="wide")
st.title("📈  Crypto‑Bot Monitor")

# Auto‑refresh by caching a dummy function to expire every 60 seconds
@st.cache_data(ttl=60)
def _refresh_dummy():
    return None

# Calling this ensures the dashboard re-executes every ttl interval
_ = _refresh_dummy()

# ---------------------- Metric push helpers ----------------------------------
_MONITORING_CLIENT: monitoring_v3.MetricServiceClient | None = None


def _get_monitoring_client() -> monitoring_v3.MetricServiceClient:
    global _MONITORING_CLIENT
    if _MONITORING_CLIENT is None:
        _MONITORING_CLIENT = monitoring_v3.MetricServiceClient()
    return _MONITORING_CLIENT


def send_custom_metric(metric_suffix: str, value: float | int) -> None:
    """
    Push a single‑value custom metric to Cloud Monitoring.

    Parameters
    ----------
    metric_suffix : str
        e.g. "pnl", "trade_count", "position_flag"
    value : float | int
        Gauge value to publish
    """
    client = _get_monitoring_client()

    # Detect GCP project ID from ADC or fallback env var / hard‑coded default
    try:
        from google.auth import default as _gcp_default

        _, project_id = _gcp_default()
    except Exception:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "my-crypto-bot-project")

    project_name = f"projects/{project_id}"

    series = monitoring_v3.TimeSeries()
    series.metric.type = f"custom.googleapis.com/crypto_bot/{metric_suffix}"
    series.resource.type = "global"
    series.resource.labels["project_id"] = project_id
    import time
    from google.protobuf.timestamp_pb2 import Timestamp

    now_ts = Timestamp()
    now_ts.GetCurrentTime()

    point = monitoring_v3.Point({
        "interval": {"end_time": now_ts},
        "value": {"double_value": float(value)},
    })
    series.points.append(point)

    # Best‑effort push; ignore API errors so the dashboard keeps rendering
    try:
        client.create_time_series(name=project_name, time_series=[series])
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Metrics push failed: {exc}")


# ---------------------- Load status.json -------------------------------------
status_file = Path("status.json")
if not status_file.exists():
    st.warning("status.json がまだ生成されていません")
    st.stop()

with status_file.open(encoding="utf-8") as fp:
    status: dict[str, Any] = json.load(fp)

# ---------------------- Display & push metrics -------------------------------
st.write("最終更新:", status.get("last_updated", "-"), "UTC")

# First row: cumulative PnL & trade count
col1, col2, col3, col4 = st.columns(4)
with col1:
    pnl_val: float = float(status.get("total_profit", 0.0))
    st.metric("累積利益 (PnL)", f"{pnl_val:,.0f} 円")
with col2:
    trades: int = int(status.get("trade_count", 0))
    st.metric("取引回数", f"{trades:,}")

# Second row: position & state
with col3:
    pos = status.get("position") or "なし"
    st.metric("ポジション", pos)
with col4:
    state = status.get("state", "unknown")
    st.metric("状態", state)

# Push metrics to Cloud Monitoring so that GCP dashboard can pick them up
send_custom_metric("pnl", pnl_val)
send_custom_metric("trade_count", trades)
position_flag = 0 if pos in ("なし", "", None) else 1
send_custom_metric("position_flag", position_flag)
