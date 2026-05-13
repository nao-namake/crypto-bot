"""Phase 87 Stage 3: SL未設置検出（detect_missing_sl）テスト"""

from src.analysis.common.sl_validators import MissingSLResult, detect_missing_sl


class TestDetectMissingSL:
    def test_no_positions_returns_not_detected(self):
        result = detect_missing_sl(positions=[], orders=[])
        assert result.detected is False
        assert result.position_amount == 0.0
        assert result.coverage_ratio == 1.0

    def test_long_position_with_full_sl_coverage(self):
        positions = [{"side": "long", "amount": 0.015}]
        orders = [{"type": "stop", "side": "sell", "amount": 0.015}]
        result = detect_missing_sl(positions, orders)
        assert result.detected is False
        assert result.sides["long"]["covered"] is True

    def test_long_position_without_sl(self):
        positions = [{"side": "long", "amount": 0.015}]
        orders = []
        result = detect_missing_sl(positions, orders)
        assert result.detected is True
        assert result.sides["long"]["covered"] is False
        assert "SL未設置検出" in result.reason

    def test_short_position_with_buy_sl(self):
        positions = [{"side": "short", "amount": 0.02}]
        orders = [{"type": "stop_limit", "side": "buy", "amount": 0.02}]
        result = detect_missing_sl(positions, orders)
        assert result.detected is False
        assert result.sides["short"]["covered"] is True

    def test_short_position_with_wrong_side_sl(self):
        """short ポジションに sell 側 SL は対応しない（buy 側で発注すべき）"""
        positions = [{"side": "short", "amount": 0.02}]
        orders = [{"type": "stop", "side": "sell", "amount": 0.02}]
        result = detect_missing_sl(positions, orders)
        assert result.detected is True  # short → buy 側 SL が必要だが sell しかない

    def test_partial_sl_coverage_below_threshold(self):
        positions = [{"side": "long", "amount": 0.015}]
        orders = [{"type": "stop", "side": "sell", "amount": 0.010}]  # 67% カバレッジ
        result = detect_missing_sl(positions, orders, threshold_pct=0.95)
        assert result.detected is True

    def test_partial_sl_coverage_above_threshold(self):
        positions = [{"side": "long", "amount": 0.015}]
        orders = [{"type": "stop", "side": "sell", "amount": 0.0145}]  # 96.7% > 95%
        result = detect_missing_sl(positions, orders, threshold_pct=0.95)
        assert result.detected is False

    def test_long_and_short_mixed(self):
        positions = [
            {"side": "long", "amount": 0.015},
            {"side": "short", "amount": 0.02},
        ]
        orders = [
            {"type": "stop", "side": "sell", "amount": 0.015},
            {"type": "stop", "side": "buy", "amount": 0.02},
        ]
        result = detect_missing_sl(positions, orders)
        assert result.detected is False
        assert result.position_amount == 0.035

    def test_none_amount_in_orders_doesnt_crash(self):
        """amount=None でも TypeError を起こさない"""
        positions = [{"side": "long", "amount": 0.015}]
        orders = [{"type": "stop", "side": "sell", "amount": None}]
        result = detect_missing_sl(positions, orders)
        # amount=None は 0 扱い → SL未設置検出
        assert result.detected is True

    def test_non_stop_orders_ignored(self):
        """limit 注文は SL とみなさない"""
        positions = [{"side": "long", "amount": 0.015}]
        orders = [{"type": "limit", "side": "sell", "amount": 0.015}]  # TP相当
        result = detect_missing_sl(positions, orders)
        assert result.detected is True

    def test_coverage_ratio_calculation(self):
        positions = [{"side": "long", "amount": 0.02}]
        orders = [{"type": "stop", "side": "sell", "amount": 0.01}]
        result = detect_missing_sl(positions, orders)
        assert result.coverage_ratio == 0.5
