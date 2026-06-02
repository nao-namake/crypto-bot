"""Phase 90ι: full_entry_simulation の MFE/MAE 分析機能テスト。

calculate_mfe_mae（各エントリーの最大含み益/含み損の算出）と
analyze_mfe_mae_statistics（全体＋レジーム別分位統計）を検証する。
"""

import importlib.util
from pathlib import Path

import pandas as pd

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "analysis" / "full_entry_simulation.py"
)
_spec = importlib.util.spec_from_file_location("full_entry_sim_mfe", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

calculate_mfe_mae = _mod.calculate_mfe_mae
analyze_mfe_mae_statistics = _mod.analyze_mfe_mae_statistics
_pct_stats = _mod._pct_stats


def _candles():
    idx = pd.to_datetime(
        [
            "2026-06-01T00:00:00Z",
            "2026-06-01T00:15:00Z",
            "2026-06-01T00:30:00Z",
        ],
        utc=True,
    )
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 108.0, 103.0],  # 窓内 high 最大 = 108
            "low": [98.0, 99.0, 95.0],  # 窓内 low 最小 = 95
            "close": [101.0, 102.0, 100.0],
        },
        index=idx,
    )


def _entry(side, regime="unknown", entry_price=100.0):
    ts_ms = pd.Timestamp("2026-06-01T00:00:00Z").value // 10**6
    return {
        "order_id": f"OID-{side}",
        "datetime": "2026-06-01T00:00:00",
        "timestamp_ms": ts_ms,
        "side": side,
        "amount": 0.015,
        "entry_price": entry_price,
        "regime": regime,
    }


class TestCalculateMfeMae:
    def test_buy_mfe_mae(self):
        """buy: MFE=有利(上昇)=108-100=8 / MAE=逆行(下落)=100-95=5"""
        data = calculate_mfe_mae([_entry("buy")], _candles(), max_window_min=60)
        assert len(data) == 1
        d = data[0]
        assert abs(d["mfe_dist"] - 8.0) < 1e-6
        assert abs(d["mae_dist"] - 5.0) < 1e-6
        assert abs(d["mfe_pct"] - 8.0) < 1e-6  # 8/100*100
        assert abs(d["mae_pct"] - 5.0) < 1e-6
        assert abs(d["mfe_jpy_015"] - 8.0 * 0.015) < 1e-6

    def test_sell_mfe_mae(self):
        """sell(short): MFE=有利(下落)=100-95=5 / MAE=逆行(上昇)=108-100=8"""
        data = calculate_mfe_mae([_entry("sell")], _candles(), max_window_min=60)
        d = data[0]
        assert abs(d["mfe_dist"] - 5.0) < 1e-6
        assert abs(d["mae_dist"] - 8.0) < 1e-6

    def test_empty_window_skipped(self):
        """保有窓にローソク足が無いエントリーはスキップ"""
        e = _entry("buy")
        e["timestamp_ms"] = pd.Timestamp("2027-01-01T00:00:00Z").value // 10**6
        data = calculate_mfe_mae([e], _candles(), max_window_min=60)
        assert data == []

    def test_mfe_mae_non_negative(self):
        """MFE/MAE は定義上 0 以上"""
        data = calculate_mfe_mae([_entry("buy")], _candles(), max_window_min=60)
        assert data[0]["mfe_dist"] >= 0
        assert data[0]["mae_dist"] >= 0


class TestPctStats:
    def test_basic_quantiles(self):
        s = _pct_stats([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert s["n"] == 10
        assert abs(s["mean"] - 5.5) < 1e-6
        assert s["p50"] == 6  # int(10*0.5)=5 → 0-indexed の6番目=6
        assert s["p90"] == 10

    def test_empty_returns_none(self):
        assert _pct_stats([]) is None


class TestAnalyzeStatistics:
    def test_overall_and_by_regime(self):
        data = calculate_mfe_mae(
            [
                _entry("buy", regime="tight_range"),
                _entry("sell", regime="normal_range"),
            ],
            _candles(),
            max_window_min=60,
        )
        stats = analyze_mfe_mae_statistics(data)
        assert stats["overall"]["count"] == 2
        assert "tight_range" in stats["by_regime"]
        assert "normal_range" in stats["by_regime"]
        assert stats["by_regime"]["tight_range"]["count"] == 1
        # レジーム別の MFE 統計が存在
        assert stats["by_regime"]["tight_range"]["mfe_pct"] is not None
