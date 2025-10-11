"""
PositionTracker テストスイート - Phase 38リファクタリング

仮想ポジション管理・追跡機能のテスト。

テスト範囲:
- add_position(): ポジション追加・TP/SL注文ID保存
- remove_position(): ポジション削除・存在しない場合の処理
- find_position(): 注文ID検索
- find_positions_by_side(): サイド別検索
- get_all_positions(): 全ポジション取得
- get_position_count(): ポジション数カウント
- get_total_exposure(): エクスポージャー計算
- get_latest_positions(): 最新ポジション取得
- clear_all_positions(): 全クリア
- update_position_tp_sl(): TP/SL注文ID更新
- get_orphaned_positions(): 孤児ポジション検出
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.trading.position.tracker import PositionTracker


@pytest.fixture
def tracker():
    """PositionTracker fixture"""
    return PositionTracker()


@pytest.fixture
def sample_position():
    """サンプルポジション fixture"""
    return {
        "order_id": "order_123",
        "side": "buy",
        "amount": 0.001,
        "price": 14000000.0,
        "timestamp": datetime.now(),
        "take_profit": 14300000.0,
        "stop_loss": 13700000.0,
        "strategy_name": "ATR",
        "tp_order_id": "tp_001",
        "sl_order_id": "sl_001",
    }


class TestAddPosition:
    """add_position() テスト"""

    def test_add_position_basic(self, tracker):
        """基本的なポジション追加"""
        result = tracker.add_position(
            order_id="order_123",
            side="buy",
            amount=0.001,
            price=14000000.0,
            strategy_name="ATR",
        )

        assert result["order_id"] == "order_123"
        assert result["side"] == "buy"
        assert result["amount"] == 0.001
        assert result["price"] == 14000000.0
        assert result["strategy_name"] == "ATR"
        assert isinstance(result["timestamp"], datetime)
        assert len(tracker.virtual_positions) == 1

    def test_add_position_with_tp_sl(self, tracker):
        """TP/SL付きポジション追加"""
        result = tracker.add_position(
            order_id="order_456",
            side="sell",
            amount=0.002,
            price=14500000.0,
            take_profit=14200000.0,
            stop_loss=14800000.0,
            strategy_name="MochiPoy",
            tp_order_id="tp_order_999",
            sl_order_id="sl_order_888",
        )

        assert result["take_profit"] == 14200000.0
        assert result["stop_loss"] == 14800000.0
        assert result["tp_order_id"] == "tp_order_999"
        assert result["sl_order_id"] == "sl_order_888"

    def test_add_position_without_tp_sl(self, tracker):
        """TP/SLなしでポジション追加"""
        result = tracker.add_position(
            order_id="order_789",
            side="buy",
            amount=0.003,
            price=14100000.0,
        )

        assert result.get("take_profit") is None
        assert result.get("stop_loss") is None
        assert "tp_order_id" not in result
        assert "sl_order_id" not in result

    def test_add_multiple_positions(self, tracker):
        """複数ポジション追加"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)
        tracker.add_position("order_3", "buy", 0.003, 14200000.0)

        assert len(tracker.virtual_positions) == 3
        assert tracker.get_position_count() == 3


class TestRemovePosition:
    """remove_position() テスト"""

    def test_remove_existing_position(self, tracker):
        """存在するポジション削除"""
        tracker.add_position("order_123", "buy", 0.001, 14000000.0)
        assert len(tracker.virtual_positions) == 1

        removed = tracker.remove_position("order_123")

        assert removed is not None
        assert removed["order_id"] == "order_123"
        assert len(tracker.virtual_positions) == 0

    def test_remove_nonexistent_position(self, tracker):
        """存在しないポジション削除"""
        tracker.add_position("order_123", "buy", 0.001, 14000000.0)

        removed = tracker.remove_position("nonexistent_order")

        assert removed is None
        assert len(tracker.virtual_positions) == 1

    def test_remove_from_multiple_positions(self, tracker):
        """複数ポジションから1つ削除"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)
        tracker.add_position("order_3", "buy", 0.003, 14200000.0)

        removed = tracker.remove_position("order_2")

        assert removed["order_id"] == "order_2"
        assert len(tracker.virtual_positions) == 2
        assert tracker.find_position("order_1") is not None
        assert tracker.find_position("order_3") is not None


class TestFindPosition:
    """find_position() テスト"""

    def test_find_existing_position(self, tracker):
        """存在するポジション検索"""
        tracker.add_position("order_123", "buy", 0.001, 14000000.0, strategy_name="ATR")

        found = tracker.find_position("order_123")

        assert found is not None
        assert found["order_id"] == "order_123"
        assert found["strategy_name"] == "ATR"

    def test_find_nonexistent_position(self, tracker):
        """存在しないポジション検索"""
        tracker.add_position("order_123", "buy", 0.001, 14000000.0)

        found = tracker.find_position("nonexistent")

        assert found is None

    def test_find_position_empty_tracker(self, tracker):
        """空トラッカーで検索"""
        found = tracker.find_position("order_123")

        assert found is None


class TestFindPositionsBySide:
    """find_positions_by_side() テスト"""

    def test_find_buy_positions(self, tracker):
        """買いポジション検索"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)
        tracker.add_position("order_3", "buy", 0.003, 14200000.0)

        buy_positions = tracker.find_positions_by_side("buy")

        assert len(buy_positions) == 2
        assert all(pos["side"] == "buy" for pos in buy_positions)

    def test_find_sell_positions(self, tracker):
        """売りポジション検索"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)
        tracker.add_position("order_3", "sell", 0.003, 14200000.0)

        sell_positions = tracker.find_positions_by_side("sell")

        assert len(sell_positions) == 2
        assert all(pos["side"] == "sell" for pos in sell_positions)

    def test_find_positions_case_insensitive(self, tracker):
        """大文字小文字を区別しない検索"""
        tracker.add_position("order_1", "BUY", 0.001, 14000000.0)
        tracker.add_position("order_2", "SELL", 0.002, 14100000.0)

        buy_positions = tracker.find_positions_by_side("buy")
        sell_positions = tracker.find_positions_by_side("SELL")

        assert len(buy_positions) == 1
        assert len(sell_positions) == 1

    def test_find_positions_no_match(self, tracker):
        """該当なし"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)

        sell_positions = tracker.find_positions_by_side("sell")

        assert len(sell_positions) == 0


class TestGetAllPositions:
    """get_all_positions() テスト"""

    def test_get_all_positions_empty(self, tracker):
        """空リスト取得"""
        positions = tracker.get_all_positions()

        assert positions == []
        assert len(positions) == 0

    def test_get_all_positions_multiple(self, tracker):
        """複数ポジション取得"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)

        positions = tracker.get_all_positions()

        assert len(positions) == 2
        assert positions[0]["order_id"] == "order_1"
        assert positions[1]["order_id"] == "order_2"

    def test_get_all_positions_returns_copy(self, tracker):
        """コピーを返すことを確認"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)

        positions = tracker.get_all_positions()
        positions.append({"order_id": "fake"})

        # 元のvirtual_positionsは変更されない
        assert len(tracker.virtual_positions) == 1


class TestGetPositionCount:
    """get_position_count() テスト"""

    def test_position_count_zero(self, tracker):
        """ポジション数0"""
        assert tracker.get_position_count() == 0

    def test_position_count_multiple(self, tracker):
        """複数ポジションカウント"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)
        tracker.add_position("order_3", "buy", 0.003, 14200000.0)

        assert tracker.get_position_count() == 3

    def test_position_count_after_removal(self, tracker):
        """削除後のカウント"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)
        tracker.remove_position("order_1")

        assert tracker.get_position_count() == 1


class TestGetTotalExposure:
    """get_total_exposure() テスト"""

    def test_exposure_empty(self, tracker):
        """空ポジションのエクスポージャー"""
        exposure = tracker.get_total_exposure()

        assert exposure["buy"] == 0
        assert exposure["sell"] == 0
        assert exposure["total"] == 0

    def test_exposure_buy_only(self, tracker):
        """買いポジションのみ"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "buy", 0.002, 14500000.0)

        exposure = tracker.get_total_exposure()

        assert exposure["buy"] == pytest.approx(14000.0 + 29000.0)
        assert exposure["sell"] == 0
        assert exposure["total"] == pytest.approx(43000.0)

    def test_exposure_sell_only(self, tracker):
        """売りポジションのみ"""
        tracker.add_position("order_1", "sell", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.003, 14200000.0)

        exposure = tracker.get_total_exposure()

        assert exposure["buy"] == 0
        assert exposure["sell"] == pytest.approx(14000.0 + 42600.0)
        assert exposure["total"] == pytest.approx(56600.0)

    def test_exposure_mixed(self, tracker):
        """買い・売り混在"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14500000.0)

        exposure = tracker.get_total_exposure()

        assert exposure["buy"] == pytest.approx(14000.0)
        assert exposure["sell"] == pytest.approx(29000.0)
        assert exposure["total"] == pytest.approx(43000.0)


class TestGetLatestPositions:
    """get_latest_positions() テスト"""

    def test_latest_positions_empty(self, tracker):
        """空リスト時"""
        latest = tracker.get_latest_positions(5)

        assert latest == []

    def test_latest_positions_less_than_count(self, tracker):
        """ポジション数がcount未満"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)

        latest = tracker.get_latest_positions(5)

        assert len(latest) == 2

    def test_latest_positions_more_than_count(self, tracker):
        """ポジション数がcount超過"""
        for i in range(10):
            tracker.add_position(f"order_{i}", "buy", 0.001, 14000000.0)

        latest = tracker.get_latest_positions(5)

        assert len(latest) == 5
        assert latest[0]["order_id"] == "order_5"
        assert latest[-1]["order_id"] == "order_9"

    def test_latest_positions_default_count(self, tracker):
        """デフォルトcount=5"""
        for i in range(7):
            tracker.add_position(f"order_{i}", "buy", 0.001, 14000000.0)

        latest = tracker.get_latest_positions()

        assert len(latest) == 5


class TestClearAllPositions:
    """clear_all_positions() テスト"""

    def test_clear_empty(self, tracker):
        """空リストのクリア"""
        count = tracker.clear_all_positions()

        assert count == 0
        assert len(tracker.virtual_positions) == 0

    def test_clear_multiple_positions(self, tracker):
        """複数ポジションクリア"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14100000.0)
        tracker.add_position("order_3", "buy", 0.003, 14200000.0)

        count = tracker.clear_all_positions()

        assert count == 3
        assert len(tracker.virtual_positions) == 0
        assert tracker.get_position_count() == 0


class TestUpdatePositionTpSl:
    """update_position_tp_sl() テスト"""

    def test_update_tp_order_id(self, tracker):
        """TP注文ID更新"""
        tracker.add_position("order_123", "buy", 0.001, 14000000.0)

        success = tracker.update_position_tp_sl("order_123", tp_order_id="tp_new_001")

        assert success is True
        position = tracker.find_position("order_123")
        assert position["tp_order_id"] == "tp_new_001"

    def test_update_sl_order_id(self, tracker):
        """SL注文ID更新"""
        tracker.add_position("order_123", "buy", 0.001, 14000000.0)

        success = tracker.update_position_tp_sl("order_123", sl_order_id="sl_new_001")

        assert success is True
        position = tracker.find_position("order_123")
        assert position["sl_order_id"] == "sl_new_001"

    def test_update_both_tp_sl_order_ids(self, tracker):
        """TP/SL両方更新"""
        tracker.add_position("order_123", "buy", 0.001, 14000000.0)

        success = tracker.update_position_tp_sl(
            "order_123", tp_order_id="tp_new_001", sl_order_id="sl_new_002"
        )

        assert success is True
        position = tracker.find_position("order_123")
        assert position["tp_order_id"] == "tp_new_001"
        assert position["sl_order_id"] == "sl_new_002"

    def test_update_nonexistent_position(self, tracker):
        """存在しないポジション更新"""
        success = tracker.update_position_tp_sl("nonexistent", tp_order_id="tp_001")

        assert success is False

    def test_update_overwrites_existing_ids(self, tracker):
        """既存ID上書き"""
        tracker.add_position(
            "order_123",
            "buy",
            0.001,
            14000000.0,
            tp_order_id="tp_old",
            sl_order_id="sl_old",
        )

        tracker.update_position_tp_sl("order_123", tp_order_id="tp_new", sl_order_id="sl_new")

        position = tracker.find_position("order_123")
        assert position["tp_order_id"] == "tp_new"
        assert position["sl_order_id"] == "sl_new"


class TestGetOrphanedPositions:
    """get_orphaned_positions() テスト"""

    def test_no_virtual_positions(self, tracker):
        """仮想ポジションなし"""
        actual_positions = [{"side": "buy", "amount": 0.001, "price": 14000000.0}]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert orphaned == []

    def test_all_positions_matched(self, tracker):
        """全ポジション一致"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14500000.0)

        actual_positions = [
            {"side": "buy", "amount": 0.001, "price": 14000000.0},
            {"side": "sell", "amount": 0.002, "price": 14500000.0},
        ]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 0

    def test_one_orphaned_position(self, tracker):
        """1つ消失"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14500000.0)

        actual_positions = [
            {"side": "buy", "amount": 0.001, "price": 14000000.0},
            # order_2が消失
        ]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 1
        assert orphaned[0]["order_id"] == "order_2"

    def test_all_positions_orphaned(self, tracker):
        """全ポジション消失"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14500000.0)

        actual_positions = []  # 実ポジションなし

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 2

    def test_amount_tolerance(self, tracker):
        """数量の許容誤差（0.00001未満）"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)

        # 実ポジションは微妙に異なる数量
        actual_positions = [{"side": "buy", "amount": 0.0010000001, "price": 14000000.0}]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 0  # 許容誤差内なので一致

    def test_side_mismatch_orphaned(self, tracker):
        """サイド不一致で孤児扱い"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)

        actual_positions = [{"side": "sell", "amount": 0.001, "price": 14000000.0}]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 1

    def test_amount_mismatch_orphaned(self, tracker):
        """数量不一致で孤児扱い"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)

        actual_positions = [{"side": "buy", "amount": 0.002, "price": 14000000.0}]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 1


class TestInitialization:
    """初期化テスト"""

    def test_tracker_initialization(self, tracker):
        """PositionTracker初期化"""
        assert hasattr(tracker, "logger")
        assert hasattr(tracker, "virtual_positions")
        assert isinstance(tracker.virtual_positions, list)
        assert len(tracker.virtual_positions) == 0

    def test_initial_state(self, tracker):
        """初期状態確認"""
        assert tracker.get_position_count() == 0
        assert tracker.get_all_positions() == []
        exposure = tracker.get_total_exposure()
        assert exposure["total"] == 0
