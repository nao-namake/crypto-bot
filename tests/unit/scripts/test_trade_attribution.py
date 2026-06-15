"""収益性アトリビューション分析（trade_attribution.py）の純粋ロジックテスト。

読み取り専用スクリプトのうち、API/GCP に依存しない以下を検証する:
  - parse_entry_strategy_log（ANSI除去 + 戦略/レジーム抽出）
  - build_round_trips（FIFOペアリング・long/short・部分約定按分）
  - attribute_trades（戦略/レジーム紐付け・unknownフォールバック・保有時間バケット）
  - bootstrap_ci（n<2でNone・seed固定で再現性）
  - _segment_stats / aggregate_by_segment / build_report（集計・判断保留判定）
"""

import importlib.util
from pathlib import Path

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "analysis" / "trade_attribution.py"
)
_spec = importlib.util.spec_from_file_location("trade_attribution", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

parse_entry_strategy_log = _mod.parse_entry_strategy_log
build_round_trips = _mod.build_round_trips
attribute_trades = _mod.attribute_trades
bootstrap_ci = _mod.bootstrap_ci
_segment_stats = _mod._segment_stats
aggregate_by_segment = _mod.aggregate_by_segment
build_report = _mod.build_report


# ============================================================
# ヘルパ
# ============================================================
def _trade(ts_ms, side, pos, amount, price, *, order_id=None, pl=0.0, fee=0.0, tid=None):
    """ccxt風の約定dictを作る。order_id は info.order_id に入れる。"""
    info = {"position_side": pos}
    if order_id is not None:
        info["order_id"] = order_id
    if pl:
        info["profit_loss"] = pl
    return {
        "id": tid or f"T{ts_ms}",
        "timestamp": ts_ms,
        "side": side,
        "amount": amount,
        "price": price,
        "fee": {"cost": fee},
        "info": info,
    }


# ============================================================
# parse_entry_strategy_log
# ============================================================
class TestParseEntryStrategyLog:
    def test_basic_extraction(self):
        raw = (
            "✅ Phase 51.6 Step 1/3: エントリー成功 - ID: 57997195838, 価格: 9769644円, "
            "戦略=BBReversal, レジーム=normal_range"
        )
        m = parse_entry_strategy_log(raw)
        assert m["57997195838"] == {"strategy": "BBReversal", "regime": "normal_range"}

    def test_strips_ansi_color_codes(self):
        raw = (
            "\x1b[32m✅ Step 1/3: エントリー成功 - ID: 123, 戦略=\x1b[1mATRBased\x1b[0m, "
            "レジーム=tight_range\x1b[0m"
        )
        m = parse_entry_strategy_log(raw)
        assert m["123"] == {"strategy": "ATRBased", "regime": "tight_range"}

    def test_multiple_entries(self):
        raw = (
            "ID: 1, 戦略=BBReversal, レジーム=normal_range\n"
            "ID: 2, 戦略=CMFReversal, レジーム=tight_range\n"
        )
        m = parse_entry_strategy_log(raw)
        assert len(m) == 2
        assert m["1"]["strategy"] == "BBReversal"
        assert m["2"]["regime"] == "tight_range"

    def test_empty_input(self):
        assert parse_entry_strategy_log("") == {}
        assert parse_entry_strategy_log(None) == {}


# ============================================================
# build_round_trips
# ============================================================
class TestBuildRoundTrips:
    def test_long_round_trip_uses_profit_loss(self):
        trades = [
            _trade(1_000, "buy", "long", 0.015, 10_000_000, order_id="E1", fee=100),
            _trade(
                1_000 + 60 * 60 * 1000,  # +1h
                "sell",
                "long",
                0.015,
                10_100_000,
                pl=1500,
                fee=200,
            ),
        ]
        rts = build_round_trips(trades)
        assert len(rts) == 1
        rt = rts[0]
        assert rt["entry_order_id"] == "E1"
        assert rt["pos_side"] == "long"
        assert rt["gross_pnl"] == 1500  # profit_loss優先
        assert rt["fee"] == 300  # entry100 + exit200
        assert rt["net_pnl"] == 1200
        assert rt["holding_min"] == 60

    def test_short_round_trip_price_diff_fallback(self):
        # profit_loss無し → 価格差から算出（short: entry-exit）
        trades = [
            _trade(2_000, "sell", "short", 0.01, 10_000_000, order_id="S1"),
            _trade(2_000 + 1000, "buy", "short", 0.01, 9_000_000),
        ]
        rts = build_round_trips(trades)
        assert len(rts) == 1
        # (entry 10,000,000 - exit 9,000,000) * 0.01 = 10,000
        assert rts[0]["gross_pnl"] == 10_000
        assert rts[0]["pos_side"] == "short"

    def test_partial_exit_prorates_pnl(self):
        # 0.02 BTC エントリー → 0.01 ずつ2回決済。profit_lossは決済約定ごと按分。
        trades = [
            _trade(3_000, "buy", "long", 0.02, 10_000_000, order_id="E2", fee=200),
            _trade(3_000 + 1000, "sell", "long", 0.01, 10_050_000, pl=500, fee=50),
            _trade(3_000 + 2000, "sell", "long", 0.01, 10_080_000, pl=800, fee=50),
        ]
        rts = build_round_trips(trades)
        assert len(rts) == 2
        # 1件目: gross=500, entry_fee按分=200*0.5=100, exit_fee=50 → net=350
        assert rts[0]["gross_pnl"] == 500
        assert rts[0]["amount"] == 0.01
        assert rts[0]["fee"] == 150
        assert rts[0]["net_pnl"] == 350
        # 2件目: gross=800, entry_fee=100, exit_fee=50 → net=650
        assert rts[1]["gross_pnl"] == 800
        assert rts[1]["net_pnl"] == 650

    def test_fifo_order_across_two_entries(self):
        # 2件エントリー → 1件決済。古いロット(E1)から消化される。
        trades = [
            _trade(4_000, "buy", "long", 0.01, 10_000_000, order_id="E1"),
            _trade(4_000 + 1000, "buy", "long", 0.01, 10_010_000, order_id="E2"),
            _trade(4_000 + 2000, "sell", "long", 0.01, 10_100_000, pl=900),
        ]
        rts = build_round_trips(trades)
        assert len(rts) == 1
        assert rts[0]["entry_order_id"] == "E1"  # FIFO: 古い方

    def test_ignores_invalid_position_side(self):
        trades = [_trade(5_000, "buy", "", 0.01, 10_000_000)]
        assert build_round_trips(trades) == []

    def test_weekday_and_hour_jst(self):
        # 2026-06-01 00:00 UTC = 2026-06-01 09:00 JST（月曜）
        entry_ms = 1_780_272_000_000  # 2026-06-01T00:00:00Z
        trades = [
            _trade(entry_ms, "buy", "long", 0.01, 10_000_000, order_id="E1"),
            _trade(entry_ms + 1000, "sell", "long", 0.01, 10_100_000, pl=100),
        ]
        rts = build_round_trips(trades)
        assert rts[0]["entry_weekday"] == 0  # 月曜
        assert rts[0]["entry_hour_jst"] == 9


# ============================================================
# attribute_trades
# ============================================================
class TestAttributeTrades:
    def _rt(self, order_id, holding_min, weekday=0, pos_side="long"):
        return {
            "entry_order_id": order_id,
            "pos_side": pos_side,
            "holding_min": holding_min,
            "entry_weekday": weekday,
        }

    def test_maps_strategy_and_regime(self):
        rts = [self._rt("E1", 30)]
        mapping = {"E1": {"strategy": "BBReversal", "regime": "normal_range"}}
        attribute_trades(rts, mapping)
        assert rts[0]["strategy"] == "BBReversal"
        assert rts[0]["regime"] == "normal_range"
        assert rts[0]["direction"] == "long"

    def test_unknown_fallback(self):
        rts = [self._rt("MISSING", 30)]
        attribute_trades(rts, {})
        assert rts[0]["strategy"] == "unknown"
        assert rts[0]["regime"] == "unknown"

    def test_holding_buckets(self):
        cases = [(30, "<1h"), (120, "1-4h"), (500, "4-12h"), (1000, "12-24h"), (2000, ">24h")]
        for minutes, expected in cases:
            rts = [self._rt("E", minutes)]
            attribute_trades(rts, {})
            assert rts[0]["holding_bucket"] == expected, minutes

    def test_weekday_label(self):
        rts = [self._rt("E", 30, weekday=5)]
        attribute_trades(rts, {})
        assert rts[0]["weekday_label"] == "土"

    def test_short_direction(self):
        rts = [self._rt("E", 30, pos_side="short")]
        attribute_trades(rts, {})
        assert rts[0]["direction"] == "short"


# ============================================================
# bootstrap_ci
# ============================================================
class TestBootstrapCi:
    def test_returns_none_for_small_sample(self):
        assert bootstrap_ci([]) == (None, None)
        assert bootstrap_ci([100]) == (None, None)

    def test_deterministic_with_seed(self):
        pnls = [100, -50, 200, -30, 80]
        a = bootstrap_ci(pnls, n=1000, seed=42)
        b = bootstrap_ci(pnls, n=1000, seed=42)
        assert a == b
        assert a[0] is not None and a[0] <= a[1]

    def test_ci_brackets_mean_region(self):
        pnls = [100, 100, 100, 100]  # 分散ゼロ → CIも100付近
        lo, hi = bootstrap_ci(pnls, n=500, seed=1)
        assert lo == 100 and hi == 100


# ============================================================
# 集計
# ============================================================
class TestSegmentStats:
    def test_basic_stats(self):
        trades = [{"net_pnl": 100}, {"net_pnl": -50}, {"net_pnl": 200}]
        st = _segment_stats(trades, bootstrap_n=500)
        assert st["n"] == 3
        assert abs(st["win_rate"] - (2 / 3 * 100)) < 1e-9
        assert st["total_pnl"] == 250
        assert abs(st["expectancy"] - 250 / 3) < 1e-9

    def test_inconclusive_when_ci_crosses_zero(self):
        # 大きく振れる損益 → CIが0をまたぐ → 判断保留
        trades = [{"net_pnl": 1000}, {"net_pnl": -1000}]
        st = _segment_stats(trades, bootstrap_n=500)
        assert st["inconclusive"] is True

    def test_single_trade_inconclusive(self):
        st = _segment_stats([{"net_pnl": 500}], bootstrap_n=500)
        assert st["n"] == 1
        assert st["ci_low"] is None
        assert st["inconclusive"] is True


class TestAggregateBySegment:
    def test_groups_and_sorts_by_count_desc(self):
        trades = [
            {"strategy": "A", "net_pnl": 100},
            {"strategy": "A", "net_pnl": -20},
            {"strategy": "B", "net_pnl": 50},
        ]
        rows = aggregate_by_segment(trades, lambda t: t["strategy"], bootstrap_n=200)
        assert [r["label"] for r in rows] == ["A", "B"]  # 件数降順
        assert rows[0]["n"] == 2


class TestBuildReport:
    def test_all_segment_keys_present(self):
        trades = [
            {
                "strategy": "BBReversal",
                "regime": "normal_range",
                "direction": "long",
                "weekday_label": "月",
                "holding_bucket": "1-4h",
                "net_pnl": 300,
            }
        ]
        report = build_report(trades, bootstrap_n=200)
        assert set(report.keys()) == {
            "overall",
            "strategy",
            "regime",
            "direction",
            "weekday",
            "holding",
        }
        assert report["overall"][0]["label"] == "全体"
        assert report["strategy"][0]["label"] == "BBReversal"
