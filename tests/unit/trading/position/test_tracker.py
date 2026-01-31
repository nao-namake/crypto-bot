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
    """PositionTracker fixture - Phase 42.4: 状態ファイルクリーンアップ"""
    import os

    # Phase 42.4: 各テスト前に永続化ファイルを削除してクリーンな状態で開始
    state_file = "src/core/state/consolidated_tp_sl_state.json"
    if os.path.exists(state_file):
        os.remove(state_file)

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

    # Phase 46: test_phase42_fields_initialization削除（統合TP/SLフィールド削除に伴い）


# ========================================
# Phase 42: 統合TP/SL機能テスト
# ========================================


class TestCalculateAverageEntryPrice:
    """calculate_average_entry_price() テスト - Phase 42"""

    def test_calculate_average_empty_positions(self, tracker):
        """空ポジション時は0.0を返す"""
        average = tracker.calculate_average_entry_price()
        assert average == 0.0

    def test_calculate_average_single_position(self, tracker):
        """単一ポジション時はそのままの価格"""
        tracker.add_position("order_1", "buy", 0.001, 10_000_000.0)

        average = tracker.calculate_average_entry_price()

        assert average == pytest.approx(10_000_000.0, abs=0.01)

    def test_calculate_average_multiple_positions(self, tracker):
        """複数ポジション時は加重平均を計算"""
        # 1,000万円 × 0.001 BTC = 10,000円相当
        tracker.add_position("order_1", "buy", 0.001, 10_000_000.0)
        # 1,050万円 × 0.002 BTC = 21,000円相当
        tracker.add_position("order_2", "buy", 0.002, 10_500_000.0)
        # 合計: 31,000円 / 0.003 BTC = 10,333,333.33円

        average = tracker.calculate_average_entry_price()
        expected = (10_000_000.0 * 0.001 + 10_500_000.0 * 0.002) / 0.003

        assert average == pytest.approx(expected, abs=0.01)

    def test_calculate_average_mixed_sides(self, tracker):
        """買い・売り混在時も正しく計算"""
        tracker.add_position("order_1", "buy", 0.001, 10_000_000.0)
        tracker.add_position("order_2", "sell", 0.002, 10_500_000.0)

        average = tracker.calculate_average_entry_price()
        expected = (10_000_000.0 * 0.001 + 10_500_000.0 * 0.002) / 0.003

        assert average == pytest.approx(expected, abs=0.01)


class TestUpdateAverageOnEntry:
    """update_average_on_entry() テスト - Phase 42"""

    def test_update_average_first_entry(self, tracker):
        """初回エントリー時は価格がそのまま設定"""
        new_average = tracker.update_average_on_entry(price=10_000_000.0, amount=0.001)

        assert new_average == pytest.approx(10_000_000.0, abs=0.01)
        assert tracker._average_entry_price == pytest.approx(10_000_000.0, abs=0.01)
        assert tracker._total_position_size == pytest.approx(0.001, abs=0.000001)

    def test_update_average_additional_entry(self, tracker):
        """追加エントリー時は加重平均で更新"""
        # 初回エントリー
        tracker.update_average_on_entry(price=10_000_000.0, amount=0.001)
        # 追加エントリー
        new_average = tracker.update_average_on_entry(price=10_500_000.0, amount=0.002)

        expected = (10_000_000.0 * 0.001 + 10_500_000.0 * 0.002) / 0.003
        assert new_average == pytest.approx(expected, abs=0.01)
        assert tracker._total_position_size == pytest.approx(0.003, abs=0.000001)

    def test_update_average_internal_state(self, tracker):
        """内部状態が正しく更新される"""
        tracker.update_average_on_entry(price=10_000_000.0, amount=0.001)
        tracker.update_average_on_entry(price=11_000_000.0, amount=0.001)

        assert tracker._average_entry_price == pytest.approx(10_500_000.0, abs=0.01)
        assert tracker._total_position_size == pytest.approx(0.002, abs=0.000001)


class TestUpdateAverageOnExit:
    """update_average_on_exit() テスト - Phase 42"""

    def test_update_average_partial_exit(self, tracker):
        """部分決済時は平均価格維持・数量のみ減少"""
        tracker.update_average_on_entry(price=10_000_000.0, amount=0.003)

        new_average = tracker.update_average_on_exit(amount=0.001)

        assert new_average == pytest.approx(10_000_000.0, abs=0.01)
        assert tracker._total_position_size == pytest.approx(0.002, abs=0.000001)

    def test_update_average_full_exit(self, tracker):
        """全決済時は平均価格・数量ともに0にリセット"""
        tracker.update_average_on_entry(price=10_000_000.0, amount=0.001)

        new_average = tracker.update_average_on_exit(amount=0.001)

        assert new_average == 0.0
        assert tracker._average_entry_price == 0.0
        assert tracker._total_position_size == 0.0


# ========================================
# Phase 49.6: remove_position_with_cleanup() テスト
# ========================================


class TestRemovePositionWithCleanup:
    """remove_position_with_cleanup() テスト - Phase 49.6"""

    def test_remove_with_cleanup_existing_position(self, tracker):
        """存在するポジションの削除とTP/SL情報取得"""
        tracker.add_position(
            "order_123",
            "buy",
            0.001,
            14000000.0,
            tp_order_id="tp_001",
            sl_order_id="sl_001",
        )

        result = tracker.remove_position_with_cleanup("order_123")

        assert result is not None
        assert result["position"]["order_id"] == "order_123"
        assert result["tp_order_id"] == "tp_001"
        assert result["sl_order_id"] == "sl_001"
        assert len(tracker.virtual_positions) == 0

    def test_remove_with_cleanup_no_tp_sl(self, tracker):
        """TP/SLなしのポジション削除"""
        tracker.add_position("order_456", "sell", 0.002, 14500000.0)

        result = tracker.remove_position_with_cleanup("order_456")

        assert result is not None
        assert result["position"]["order_id"] == "order_456"
        assert result["tp_order_id"] is None
        assert result["sl_order_id"] is None

    def test_remove_with_cleanup_only_tp(self, tracker):
        """TPのみ設定されたポジション削除"""
        tracker.add_position(
            "order_789", "buy", 0.001, 14000000.0, tp_order_id="tp_only_001"
        )

        result = tracker.remove_position_with_cleanup("order_789")

        assert result["tp_order_id"] == "tp_only_001"
        assert result["sl_order_id"] is None

    def test_remove_with_cleanup_only_sl(self, tracker):
        """SLのみ設定されたポジション削除"""
        tracker.add_position(
            "order_abc", "sell", 0.003, 14200000.0, sl_order_id="sl_only_001"
        )

        result = tracker.remove_position_with_cleanup("order_abc")

        assert result["tp_order_id"] is None
        assert result["sl_order_id"] == "sl_only_001"

    def test_remove_with_cleanup_nonexistent(self, tracker):
        """存在しないポジションの削除"""
        tracker.add_position("order_123", "buy", 0.001, 14000000.0)

        result = tracker.remove_position_with_cleanup("nonexistent_order")

        assert result is None
        assert len(tracker.virtual_positions) == 1

    def test_remove_with_cleanup_from_multiple(self, tracker):
        """複数ポジションから1つを削除"""
        tracker.add_position(
            "order_1", "buy", 0.001, 14000000.0, tp_order_id="tp_1", sl_order_id="sl_1"
        )
        tracker.add_position(
            "order_2", "sell", 0.002, 14500000.0, tp_order_id="tp_2", sl_order_id="sl_2"
        )
        tracker.add_position(
            "order_3", "buy", 0.003, 14200000.0, tp_order_id="tp_3", sl_order_id="sl_3"
        )

        result = tracker.remove_position_with_cleanup("order_2")

        assert result["position"]["order_id"] == "order_2"
        assert result["tp_order_id"] == "tp_2"
        assert result["sl_order_id"] == "sl_2"
        assert len(tracker.virtual_positions) == 2
        assert tracker.find_position("order_1") is not None
        assert tracker.find_position("order_3") is not None


# ========================================
# Phase 61.9: TP/SL注文ID検索テスト
# ========================================


class TestFindPositionByTpOrderId:
    """find_position_by_tp_order_id() テスト - Phase 61.9"""

    def test_find_by_tp_order_id_exists(self, tracker):
        """TP注文IDでポジション検索（存在する場合）"""
        tracker.add_position(
            "order_123",
            "buy",
            0.001,
            14000000.0,
            tp_order_id="tp_001",
            sl_order_id="sl_001",
        )

        result = tracker.find_position_by_tp_order_id("tp_001")

        assert result is not None
        assert result["order_id"] == "order_123"
        assert result["tp_order_id"] == "tp_001"

    def test_find_by_tp_order_id_not_exists(self, tracker):
        """TP注文IDでポジション検索（存在しない場合）"""
        tracker.add_position(
            "order_123", "buy", 0.001, 14000000.0, tp_order_id="tp_001"
        )

        result = tracker.find_position_by_tp_order_id("tp_nonexistent")

        assert result is None

    def test_find_by_tp_order_id_empty_tracker(self, tracker):
        """空トラッカーでTP注文ID検索"""
        result = tracker.find_position_by_tp_order_id("tp_001")

        assert result is None

    def test_find_by_tp_order_id_multiple_positions(self, tracker):
        """複数ポジションからTP注文IDで検索"""
        tracker.add_position(
            "order_1", "buy", 0.001, 14000000.0, tp_order_id="tp_1"
        )
        tracker.add_position(
            "order_2", "sell", 0.002, 14500000.0, tp_order_id="tp_2"
        )
        tracker.add_position(
            "order_3", "buy", 0.003, 14200000.0, tp_order_id="tp_3"
        )

        result = tracker.find_position_by_tp_order_id("tp_2")

        assert result is not None
        assert result["order_id"] == "order_2"


class TestFindPositionBySlOrderId:
    """find_position_by_sl_order_id() テスト - Phase 61.9"""

    def test_find_by_sl_order_id_exists(self, tracker):
        """SL注文IDでポジション検索（存在する場合）"""
        tracker.add_position(
            "order_123",
            "buy",
            0.001,
            14000000.0,
            tp_order_id="tp_001",
            sl_order_id="sl_001",
        )

        result = tracker.find_position_by_sl_order_id("sl_001")

        assert result is not None
        assert result["order_id"] == "order_123"
        assert result["sl_order_id"] == "sl_001"

    def test_find_by_sl_order_id_not_exists(self, tracker):
        """SL注文IDでポジション検索（存在しない場合）"""
        tracker.add_position(
            "order_123", "buy", 0.001, 14000000.0, sl_order_id="sl_001"
        )

        result = tracker.find_position_by_sl_order_id("sl_nonexistent")

        assert result is None

    def test_find_by_sl_order_id_empty_tracker(self, tracker):
        """空トラッカーでSL注文ID検索"""
        result = tracker.find_position_by_sl_order_id("sl_001")

        assert result is None

    def test_find_by_sl_order_id_multiple_positions(self, tracker):
        """複数ポジションからSL注文IDで検索"""
        tracker.add_position(
            "order_1", "buy", 0.001, 14000000.0, sl_order_id="sl_1"
        )
        tracker.add_position(
            "order_2", "sell", 0.002, 14500000.0, sl_order_id="sl_2"
        )
        tracker.add_position(
            "order_3", "buy", 0.003, 14200000.0, sl_order_id="sl_3"
        )

        result = tracker.find_position_by_sl_order_id("sl_3")

        assert result is not None
        assert result["order_id"] == "order_3"


class TestRemovePositionByTpOrSlOrderId:
    """remove_position_by_tp_or_sl_order_id() テスト - Phase 61.9"""

    def test_remove_by_tp_order_id(self, tracker):
        """TP注文IDでポジション削除"""
        tracker.add_position(
            "order_123",
            "buy",
            0.001,
            14000000.0,
            tp_order_id="tp_001",
            sl_order_id="sl_001",
        )

        result = tracker.remove_position_by_tp_or_sl_order_id("tp_001")

        assert result is not None
        assert result["order_id"] == "order_123"
        assert len(tracker.virtual_positions) == 0

    def test_remove_by_sl_order_id(self, tracker):
        """SL注文IDでポジション削除"""
        tracker.add_position(
            "order_456",
            "sell",
            0.002,
            14500000.0,
            tp_order_id="tp_002",
            sl_order_id="sl_002",
        )

        result = tracker.remove_position_by_tp_or_sl_order_id("sl_002")

        assert result is not None
        assert result["order_id"] == "order_456"
        assert len(tracker.virtual_positions) == 0

    def test_remove_by_tp_or_sl_nonexistent(self, tracker):
        """存在しないTP/SL注文IDで削除"""
        tracker.add_position(
            "order_123", "buy", 0.001, 14000000.0, tp_order_id="tp_001"
        )

        result = tracker.remove_position_by_tp_or_sl_order_id("nonexistent")

        assert result is None
        assert len(tracker.virtual_positions) == 1

    def test_remove_by_tp_or_sl_empty_tracker(self, tracker):
        """空トラッカーでTP/SL削除"""
        result = tracker.remove_position_by_tp_or_sl_order_id("tp_001")

        assert result is None

    def test_remove_by_tp_or_sl_from_multiple(self, tracker):
        """複数ポジションからTP/SL注文IDで削除"""
        tracker.add_position(
            "order_1", "buy", 0.001, 14000000.0, tp_order_id="tp_1", sl_order_id="sl_1"
        )
        tracker.add_position(
            "order_2", "sell", 0.002, 14500000.0, tp_order_id="tp_2", sl_order_id="sl_2"
        )
        tracker.add_position(
            "order_3", "buy", 0.003, 14200000.0, tp_order_id="tp_3", sl_order_id="sl_3"
        )

        result = tracker.remove_position_by_tp_or_sl_order_id("sl_2")

        assert result["order_id"] == "order_2"
        assert len(tracker.virtual_positions) == 2


# ========================================
# 追加テスト: エッジケース・カバレッジ向上
# ========================================


class TestCalculateAverageEntryPriceEdgeCases:
    """calculate_average_entry_price() エッジケーステスト"""

    def test_calculate_average_zero_amount_positions(self, tracker):
        """数量0のポジションがある場合"""
        # 内部的にamount=0のポジションを直接追加（通常はありえないが防御的テスト）
        tracker.virtual_positions.append({
            "order_id": "order_zero",
            "side": "buy",
            "amount": 0,
            "price": 10000000.0,
        })

        average = tracker.calculate_average_entry_price()

        assert average == 0.0  # total_size == 0の場合

    def test_calculate_average_missing_price_field(self, tracker):
        """priceフィールドがない場合のデフォルト値"""
        tracker.virtual_positions.append({
            "order_id": "order_no_price",
            "side": "buy",
            "amount": 0.001,
        })

        average = tracker.calculate_average_entry_price()

        assert average == 0.0  # price=0, amount=0.001 -> average=0

    def test_calculate_average_missing_amount_field(self, tracker):
        """amountフィールドがない場合のデフォルト値"""
        tracker.virtual_positions.append({
            "order_id": "order_no_amount",
            "side": "buy",
            "price": 10000000.0,
        })

        average = tracker.calculate_average_entry_price()

        assert average == 0.0  # amount=0なのでtotal_size=0


class TestUpdateAverageOnExitEdgeCases:
    """update_average_on_exit() エッジケーステスト"""

    def test_update_average_exit_more_than_size(self, tracker):
        """決済数量がポジション数量を超える場合"""
        tracker.update_average_on_entry(price=10_000_000.0, amount=0.001)

        # 0.002 BTCを決済（実際は0.001 BTCしかない）
        new_average = tracker.update_average_on_exit(amount=0.002)

        # max(0, 0.001 - 0.002) = 0 なので全決済扱い
        assert new_average == 0.0
        assert tracker._average_entry_price == 0.0
        assert tracker._total_position_size == 0.0

    def test_update_average_exit_zero_amount(self, tracker):
        """決済数量0の場合"""
        tracker.update_average_on_entry(price=10_000_000.0, amount=0.003)

        new_average = tracker.update_average_on_exit(amount=0)

        # 0を決済しても変わらない
        assert new_average == pytest.approx(10_000_000.0, abs=0.01)
        assert tracker._total_position_size == pytest.approx(0.003, abs=0.000001)


class TestUpdateAverageOnEntryEdgeCases:
    """update_average_on_entry() エッジケーステスト"""

    def test_update_average_entry_zero_amount(self, tracker):
        """エントリー数量0の場合"""
        tracker.update_average_on_entry(price=10_000_000.0, amount=0.001)

        # 0 BTCを追加エントリー
        new_average = tracker.update_average_on_entry(price=15_000_000.0, amount=0)

        # 平均価格は変わらないはず
        assert new_average == pytest.approx(10_000_000.0, abs=0.01)
        assert tracker._total_position_size == pytest.approx(0.001, abs=0.000001)

    def test_update_average_entry_negative_amount_results_zero_total(self, tracker):
        """負のamountでnew_total_sizeが0以下になる場合（防御的コードのテスト）"""
        # 初期値を設定せずに負のamountを渡す
        # old_size = 0, amount = -0.001 -> new_total_size = -0.001 < 0
        new_average = tracker.update_average_on_entry(price=10_000_000.0, amount=-0.001)

        # new_total_size <= 0 なのでリセット
        assert new_average == 0.0
        assert tracker._average_entry_price == 0.0
        assert tracker._total_position_size == 0.0

    def test_update_average_entry_negative_cancels_positive(self, tracker):
        """負のamountがちょうど既存サイズを打ち消す場合"""
        # 0.001 BTCをエントリー
        tracker.update_average_on_entry(price=10_000_000.0, amount=0.001)

        # -0.001 BTCで打ち消し -> new_total_size = 0
        new_average = tracker.update_average_on_entry(price=15_000_000.0, amount=-0.001)

        # new_total_size = 0 なのでリセット
        assert new_average == 0.0
        assert tracker._average_entry_price == 0.0
        assert tracker._total_position_size == 0.0


class TestUpdatePositionTpSlEdgeCases:
    """update_position_tp_sl() エッジケーステスト"""

    def test_update_with_none_values(self, tracker):
        """Noneを渡した場合は更新しない"""
        tracker.add_position(
            "order_123",
            "buy",
            0.001,
            14000000.0,
            tp_order_id="tp_old",
            sl_order_id="sl_old",
        )

        # Noneを渡す（更新しない）
        success = tracker.update_position_tp_sl("order_123", tp_order_id=None, sl_order_id=None)

        assert success is True
        position = tracker.find_position("order_123")
        # 既存の値が維持されている
        assert position["tp_order_id"] == "tp_old"
        assert position["sl_order_id"] == "sl_old"

    def test_update_tp_only_preserves_sl(self, tracker):
        """TPのみ更新時にSLは維持"""
        tracker.add_position(
            "order_123",
            "buy",
            0.001,
            14000000.0,
            tp_order_id="tp_old",
            sl_order_id="sl_old",
        )

        success = tracker.update_position_tp_sl("order_123", tp_order_id="tp_new")

        assert success is True
        position = tracker.find_position("order_123")
        assert position["tp_order_id"] == "tp_new"
        assert position["sl_order_id"] == "sl_old"

    def test_update_sl_only_preserves_tp(self, tracker):
        """SLのみ更新時にTPは維持"""
        tracker.add_position(
            "order_123",
            "buy",
            0.001,
            14000000.0,
            tp_order_id="tp_old",
            sl_order_id="sl_old",
        )

        success = tracker.update_position_tp_sl("order_123", sl_order_id="sl_new")

        assert success is True
        position = tracker.find_position("order_123")
        assert position["tp_order_id"] == "tp_old"
        assert position["sl_order_id"] == "sl_new"


class TestTrackerInternalState:
    """内部状態の初期化確認テスト"""

    def test_average_price_initial_state(self, tracker):
        """平均価格の初期状態"""
        assert tracker._average_entry_price == 0.0
        assert tracker._total_position_size == 0.0

    def test_internal_state_after_clear(self, tracker):
        """clear_all_positions後の内部状態"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.update_average_on_entry(price=14000000.0, amount=0.001)

        tracker.clear_all_positions()

        # virtual_positionsはクリアされるが、内部統計は別管理
        assert len(tracker.virtual_positions) == 0
        # 注意: clear_all_positionsは_average_entry_priceをリセットしない
        assert tracker._average_entry_price == pytest.approx(14000000.0, abs=0.01)


class TestGetOrphanedPositionsEdgeCases:
    """get_orphaned_positions() エッジケーステスト"""

    def test_orphaned_with_empty_side(self, tracker):
        """sideが空文字のポジション"""
        tracker.virtual_positions.append({
            "order_id": "order_empty_side",
            "side": "",
            "amount": 0.001,
            "price": 14000000.0,
        })

        actual_positions = [{"side": "", "amount": 0.001, "price": 14000000.0}]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 0  # 空文字同士で一致

    def test_orphaned_with_missing_side(self, tracker):
        """sideフィールドがないポジション"""
        tracker.virtual_positions.append({
            "order_id": "order_no_side",
            "amount": 0.001,
            "price": 14000000.0,
        })

        actual_positions = [{"amount": 0.001, "price": 14000000.0}]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 0  # sideなし同士で一致（""として扱われる）

    def test_orphaned_with_missing_amount(self, tracker):
        """amountフィールドがないポジション"""
        tracker.virtual_positions.append({
            "order_id": "order_no_amount",
            "side": "buy",
            "price": 14000000.0,
        })

        actual_positions = [{"side": "buy", "price": 14000000.0}]

        orphaned = tracker.get_orphaned_positions(actual_positions)

        assert len(orphaned) == 0  # amount=0同士で一致


class TestFindPositionsBySideEdgeCases:
    """find_positions_by_side() エッジケーステスト"""

    def test_find_positions_empty_side(self, tracker):
        """空文字sideで検索"""
        tracker.virtual_positions.append({
            "order_id": "order_empty_side",
            "side": "",
            "amount": 0.001,
            "price": 14000000.0,
        })

        result = tracker.find_positions_by_side("")

        assert len(result) == 1
        assert result[0]["order_id"] == "order_empty_side"

    def test_find_positions_missing_side(self, tracker):
        """sideフィールドがないポジションの検索"""
        tracker.virtual_positions.append({
            "order_id": "order_no_side",
            "amount": 0.001,
            "price": 14000000.0,
        })

        # sideが存在しない場合は空文字として扱われる
        result = tracker.find_positions_by_side("")

        assert len(result) == 1


class TestGetTotalExposureEdgeCases:
    """get_total_exposure() エッジケーステスト"""

    def test_exposure_with_uppercase_side(self, tracker):
        """大文字sideのエクスポージャー計算"""
        tracker.add_position("order_1", "BUY", 0.001, 14000000.0)
        tracker.add_position("order_2", "SELL", 0.002, 14500000.0)

        exposure = tracker.get_total_exposure()

        assert exposure["buy"] == pytest.approx(14000.0)
        assert exposure["sell"] == pytest.approx(29000.0)
        assert exposure["total"] == pytest.approx(43000.0)

    def test_exposure_with_mixed_case_side(self, tracker):
        """大文字小文字混在sideのエクスポージャー計算"""
        tracker.add_position("order_1", "Buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "Sell", 0.002, 14500000.0)

        exposure = tracker.get_total_exposure()

        assert exposure["buy"] == pytest.approx(14000.0)
        assert exposure["sell"] == pytest.approx(29000.0)


class TestGetLatestPositionsEdgeCases:
    """get_latest_positions() エッジケーステスト"""

    def test_latest_positions_count_zero(self, tracker):
        """count=0の場合（Pythonスライス: [-0:]は全リストを返す）"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14500000.0)

        latest = tracker.get_latest_positions(0)

        # Python slicing: [-0:] は全リストを返す（[-0] = [0]と同じ）
        assert len(latest) == 2

    def test_latest_positions_negative_count(self, tracker):
        """count負数の場合"""
        tracker.add_position("order_1", "buy", 0.001, 14000000.0)
        tracker.add_position("order_2", "sell", 0.002, 14500000.0)

        latest = tracker.get_latest_positions(-1)

        # Python slicing: [-1:] は最後の1つを返す
        assert len(latest) == 1
        assert latest[0]["order_id"] == "order_2"


class TestAddPositionDefaultStrategy:
    """add_position() デフォルト値テスト"""

    def test_add_position_default_strategy_name(self, tracker):
        """strategy_nameのデフォルト値"""
        result = tracker.add_position(
            order_id="order_123",
            side="buy",
            amount=0.001,
            price=14000000.0,
        )

        assert result["strategy_name"] == "unknown"


class TestRemovePositionFromEmptyTracker:
    """空トラッカーでのremove_position()テスト"""

    def test_remove_from_empty_tracker(self, tracker):
        """空トラッカーからの削除"""
        result = tracker.remove_position("nonexistent")

        assert result is None
        assert len(tracker.virtual_positions) == 0


class TestMultipleOperationsIntegration:
    """複数操作の統合テスト"""

    def test_add_find_update_remove_flow(self, tracker):
        """追加→検索→更新→削除の一連の流れ"""
        # 追加
        tracker.add_position(
            "order_flow", "buy", 0.001, 14000000.0, strategy_name="TestStrategy"
        )
        assert tracker.get_position_count() == 1

        # 検索
        pos = tracker.find_position("order_flow")
        assert pos is not None
        assert pos["strategy_name"] == "TestStrategy"

        # TP/SL更新
        success = tracker.update_position_tp_sl(
            "order_flow", tp_order_id="tp_flow", sl_order_id="sl_flow"
        )
        assert success is True

        # 再検索して確認
        pos = tracker.find_position("order_flow")
        assert pos["tp_order_id"] == "tp_flow"
        assert pos["sl_order_id"] == "sl_flow"

        # クリーンアップ付き削除
        result = tracker.remove_position_with_cleanup("order_flow")
        assert result["tp_order_id"] == "tp_flow"
        assert result["sl_order_id"] == "sl_flow"
        assert tracker.get_position_count() == 0

    def test_average_price_entry_exit_cycle(self, tracker):
        """平均価格のエントリー→決済サイクル"""
        # 初回エントリー
        avg1 = tracker.update_average_on_entry(price=10_000_000.0, amount=0.001)
        assert avg1 == pytest.approx(10_000_000.0, abs=0.01)

        # 追加エントリー
        avg2 = tracker.update_average_on_entry(price=11_000_000.0, amount=0.001)
        assert avg2 == pytest.approx(10_500_000.0, abs=0.01)

        # 部分決済
        avg3 = tracker.update_average_on_exit(amount=0.001)
        assert avg3 == pytest.approx(10_500_000.0, abs=0.01)  # 平均価格維持
        assert tracker._total_position_size == pytest.approx(0.001, abs=0.000001)

        # 全決済
        avg4 = tracker.update_average_on_exit(amount=0.001)
        assert avg4 == 0.0
        assert tracker._total_position_size == 0.0
