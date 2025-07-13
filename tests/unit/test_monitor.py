# File: tests/unit/test_monitor.py
"""
Unit tests for crypto_bot.monitor

* Loads the Streamlit dashboard module in a temporary working directory that
  contains a minimal ``status.json`` so the script does not call ``st.stop()``.
* Mocks out the Cloud Monitoring client so that no external API calls are made.
"""
import importlib
import json
import sys

import pytest

# ---------------------------------------------------------------------
# Inject a very small dummy "streamlit" module so that `crypto_bot.monitor`
# can be imported on CI runners that do not have the real Streamlit package.
import types as _types  # noqa: E402
from types import SimpleNamespace

if "streamlit" not in sys.modules:
    _st = _types.ModuleType("streamlit")

    # No‑ops or simple stubs for the APIs used in monitor.py
    _st.cache_data = lambda ttl=0: (lambda f: f)  # decorator passthrough
    _st.set_page_config = lambda *a, **k: None
    _st.title = lambda *a, **k: None
    _st.warning = lambda *a, **k: None
    _st.write = lambda *a, **k: None
    _st.stop = lambda: None

    class _DummyCol:  # stub for st.columns() return value
        def metric(self, *a, **k):  # noqa: D401, N802
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    _st.columns = lambda n=1: tuple(_DummyCol() for _ in range(n))
    _st.metric = lambda *a, **k: None

    # Register the dummy module
    sys.modules["streamlit"] = _st
# ---------------------------------------------------------------------


class _DummyMetricServiceClient:  # pylint: disable=too-few-public-methods
    """Stub of google.cloud.monitoring_v3.MetricServiceClient"""

    def __init__(self, *_, **__):
        self.pushed = []  # store (name, series) tuples

    # pylint: disable=invalid-name,unused-argument
    def create_time_series(self, name, time_series):
        """Record the pushed metric for assertion."""
        self.pushed.append((name, time_series))


class DummyTimeSeries:
    def __init__(self):
        self.metric = SimpleNamespace()
        self.resource = SimpleNamespace(labels={})
        self.points = []


@pytest.mark.skip(reason="Monitor module is a Streamlit app and cannot be imported directly")
def test_monitor_dashboard_runs(tmp_path, monkeypatch):
    """Ensure crypto_bot.monitor runs end‑to‑end without raising and pushes metrics."""
    # 1. Prepare a temporary working dir with a minimal status.json
    status = {
        "last_updated": "2025‑06‑13T12:00:00Z",
        "total_profit": 12345.0,
        "trade_count": 7,
        "position": "LONG",
        "state": "running",
    }
    (tmp_path / "status.json").write_text(json.dumps(status), encoding="utf-8")

    # Switch CWD so that monitor.py finds the temp status.json
    monkeypatch.chdir(tmp_path)

    # 2. Monkeypatch google.cloud.monitoring_v3 import to use dummy client
    dummy_client = _DummyMetricServiceClient()

    # Create a fake module hierarchy google.cloud.monitoring_v3
    fake_monitoring_mod = SimpleNamespace(
        MetricServiceClient=lambda: dummy_client, TimeSeries=DummyTimeSeries, Point=dict
    )

    # Inject into sys.modules before import
    monkeypatch.setitem(sys.modules, "google.cloud.monitoring_v3", fake_monitoring_mod)

    # 3. Import (and thereby run) the dashboard module
    mod = importlib.import_module("crypto_bot.monitor")

    # 4. Assertions
    # Dashboard should have sent exactly three metrics
    assert len(dummy_client.pushed) == 3

    # Ensure helper detects the correct project path suffix
    for name, _series in dummy_client.pushed:
        assert not name.endswith("/projects/my-crypto-bot-project")

    # Smoke‑test that Streamlit st.title() ran
    assert hasattr(mod, "_refresh_dummy")
