"""Phase 89-α Stage 1: trade_gating の単体テスト

5 分間隔 trigger で 15 分足完成タイミング・既存ポジション状況に基づく
取引判断 gating の正当性を検証する。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.core.orchestration.trade_gating import (
    DEFAULT_BOUNDARY_TOLERANCE_MIN,
    check_candle_boundary,
    check_position_blocking,
    check_trade_gating,
)


class TestCheckCandleBoundary:
    """15 分足境界判定のテスト（00, 15, 30, 45 分 ±2 分以内）"""

    @pytest.mark.parametrize(
        "minute",
        [0, 1, 2, 13, 14, 15, 16, 17, 28, 29, 30, 31, 32, 43, 44, 45, 46, 47, 58, 59],
    )
    def test_within_boundary(self, minute):
        """境界 ±2 分以内は通過"""
        now = datetime(2026, 5, 15, 10, minute, 0)
        assert check_candle_boundary(now) is True

    @pytest.mark.parametrize("minute", [3, 4, 5, 10, 11, 12, 18, 19, 25, 26, 27, 33, 34, 41, 42])
    def test_outside_boundary(self, minute):
        """境界 ±2 分外は reject"""
        now = datetime(2026, 5, 15, 10, minute, 0)
        assert check_candle_boundary(now) is False

    def test_tolerance_min_default(self):
        """デフォルト tolerance が 2 分であることを確認"""
        # 17 分は境界 15 から +2 分 → 通過
        assert check_candle_boundary(datetime(2026, 5, 15, 10, 17, 0)) is True
        # 18 分は境界 15 から +3 分 → reject
        assert check_candle_boundary(datetime(2026, 5, 15, 10, 18, 0)) is False
        assert DEFAULT_BOUNDARY_TOLERANCE_MIN == 2

    def test_custom_tolerance(self):
        """tolerance_min=1 の場合は ±1 分に絞り込む"""
        # 14 分は境界 15 から -1 分 → 通過
        assert check_candle_boundary(datetime(2026, 5, 15, 10, 14, 0), tolerance_min=1) is True
        # 13 分は境界 15 から -2 分 → reject（tolerance=1 の場合）
        assert check_candle_boundary(datetime(2026, 5, 15, 10, 13, 0), tolerance_min=1) is False


class TestCheckPositionBlocking:
    """既存ポジションによるブロック判定のテスト"""

    def test_no_positions(self):
        """ポジション無し → 通過"""
        result = check_position_blocking([])
        assert result.allowed is True
        assert result.reason == "ok"

    def test_only_long(self):
        """long のみ → short 方向の機会あり → 通過"""
        result = check_position_blocking([{"side": "long", "amount": 0.015}])
        assert result.allowed is True

    def test_only_short(self):
        """short のみ → long 方向の機会あり → 通過"""
        result = check_position_blocking([{"side": "short", "amount": 0.01}])
        assert result.allowed is True

    def test_both_long_and_short(self):
        """両方向ポジあり → 完全ブロック"""
        result = check_position_blocking(
            [
                {"side": "long", "amount": 0.015},
                {"side": "short", "amount": 0.01},
            ]
        )
        assert result.allowed is False
        assert result.reason == "blocked_by_position"
        assert "long+short" in result.detail

    def test_zero_amount_ignored(self):
        """amount=0 の建玉は無視される"""
        result = check_position_blocking(
            [
                {"side": "long", "amount": 0},
                {"side": "short", "amount": 0.01},
            ]
        )
        # long は 0 なので無視 → short のみ扱い → 通過
        assert result.allowed is True

    def test_none_amount_safe(self):
        """amount=None でも例外が起きない"""
        result = check_position_blocking(
            [
                {"side": "long", "amount": None},
                {"side": "short", "amount": 0.01},
            ]
        )
        assert result.allowed is True


class TestCheckTradeGatingFullFlow:
    """check_trade_gating エンドツーエンドのテスト"""

    @pytest.mark.asyncio
    async def test_ok_when_boundary_and_no_positions(self):
        """境界内 + ポジション無し → 通過"""
        result = await check_trade_gating(
            now=datetime(2026, 5, 15, 10, 15, 0),
            margin_positions=[],
        )
        assert result.allowed is True
        assert result.reason == "ok"

    @pytest.mark.asyncio
    async def test_reject_outside_boundary(self):
        """境界外 → reject (positions は評価されない)"""
        result = await check_trade_gating(
            now=datetime(2026, 5, 15, 10, 10, 0),  # 境界外
            margin_positions=[],
        )
        assert result.allowed is False
        assert result.reason == "not_candle_boundary"
        assert "10" in result.detail  # 分の値が含まれる

    @pytest.mark.asyncio
    async def test_reject_both_positions(self):
        """境界内 + 両方向ポジあり → reject"""
        result = await check_trade_gating(
            now=datetime(2026, 5, 15, 10, 0, 0),
            margin_positions=[
                {"side": "long", "amount": 0.015},
                {"side": "short", "amount": 0.01},
            ],
        )
        assert result.allowed is False
        assert result.reason == "blocked_by_position"

    @pytest.mark.asyncio
    async def test_ok_with_single_direction_position(self):
        """境界内 + long のみ → 通過（short 方向の機会あり）"""
        result = await check_trade_gating(
            now=datetime(2026, 5, 15, 10, 30, 0),
            margin_positions=[{"side": "long", "amount": 0.015}],
        )
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_none_positions_treated_as_empty(self):
        """margin_positions=None でも安全に動作（空扱い）"""
        result = await check_trade_gating(
            now=datetime(2026, 5, 15, 10, 45, 0),
            margin_positions=None,
        )
        assert result.allowed is True
        assert result.reason == "ok"

    @pytest.mark.asyncio
    async def test_boundary_tolerance_propagates(self):
        """tolerance_min カスタム指定が check_candle_boundary に伝搬"""
        # 14 分は境界 15 から -1 分 → tolerance=1 で通過
        result = await check_trade_gating(
            now=datetime(2026, 5, 15, 10, 14, 0),
            margin_positions=[],
            tolerance_min=1,
        )
        assert result.allowed is True
        # 13 分は -2 分 → tolerance=1 で reject
        result = await check_trade_gating(
            now=datetime(2026, 5, 15, 10, 13, 0),
            margin_positions=[],
            tolerance_min=1,
        )
        assert result.allowed is False
