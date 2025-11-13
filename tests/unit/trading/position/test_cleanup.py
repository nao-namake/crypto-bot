"""
PositionCleanup テストスイート - Phase 38リファクタリング

Phase 37.5.3: 孤児ポジションクリーンアップ機能のテスト。

テスト範囲:
- cleanup_orphaned_positions(): 孤児ポジションクリーンアップ
- _fetch_actual_positions(): 実ポジション取得
- _cancel_order(): 注文キャンセル
- check_stale_positions(): 古いポジション検出
- get_cleanup_stats(): クリーンアップ統計
- emergency_cleanup(): 緊急クリーンアップ
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading.position.cleanup import PositionCleanup


@pytest.fixture
def cleanup():
    """PositionCleanup fixture"""
    return PositionCleanup()


@pytest.fixture
def mock_bitbank_client():
    """BitbankClient mock fixture"""
    client = AsyncMock()
    client.fetch_margin_positions = AsyncMock(return_value=[])
    client.cancel_order = AsyncMock(return_value={"status": "CANCELED_UNFILLED"})
    return client


@pytest.fixture
def mock_position_tracker():
    """PositionTracker mock fixture"""
    tracker = Mock()
    tracker.get_orphaned_positions = Mock(return_value=[])
    tracker.remove_position = Mock()
    tracker.get_all_positions = Mock(return_value=[])
    tracker.get_total_exposure = Mock(return_value={"buy": 0, "sell": 0, "total": 0})
    tracker.clear_all_positions = Mock(return_value=0)
    return tracker


class TestCleanupOrphanedPositions:
    """cleanup_orphaned_positions() テスト"""

    @pytest.mark.asyncio
    async def test_no_position_tracker(self, cleanup, mock_bitbank_client):
        """PositionTracker未注入"""
        result = await cleanup.cleanup_orphaned_positions(mock_bitbank_client)

        assert result["success"] is False
        assert "PositionTrackerが未注入" in result["message"]
        assert result["cleaned"] == 0

    @pytest.mark.asyncio
    async def test_no_bitbank_client(self, cleanup, mock_position_tracker):
        """BitbankClient未指定"""
        cleanup.inject_position_tracker(mock_position_tracker)

        result = await cleanup.cleanup_orphaned_positions(None)

        assert result["success"] is False
        assert "BitbankClientが未指定" in result["message"]
        assert result["cleaned"] == 0

    @pytest.mark.asyncio
    async def test_fetch_actual_positions_failure(self, cleanup, mock_position_tracker):
        """実ポジション取得失敗"""
        cleanup.inject_position_tracker(mock_position_tracker)

        mock_client = AsyncMock()
        mock_client.fetch_margin_positions = AsyncMock(return_value=None)

        result = await cleanup.cleanup_orphaned_positions(mock_client)

        assert result["success"] is False
        assert "実ポジション取得失敗" in result["message"]

    @pytest.mark.asyncio
    async def test_no_orphaned_positions(self, cleanup, mock_position_tracker, mock_bitbank_client):
        """孤児ポジションなし"""
        cleanup.inject_position_tracker(mock_position_tracker)
        mock_position_tracker.get_orphaned_positions.return_value = []

        mock_bitbank_client.fetch_margin_positions.return_value = [
            {"side": "buy", "amount": 0.001, "price": 14000000.0}
        ]

        result = await cleanup.cleanup_orphaned_positions(mock_bitbank_client)

        assert result["success"] is True
        assert "孤児ポジションなし" in result["message"]
        assert result["cleaned"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_tp_order_only(self, cleanup, mock_position_tracker, mock_bitbank_client):
        """TP注文のみクリーンアップ"""
        cleanup.inject_position_tracker(mock_position_tracker)

        orphaned = [
            {
                "order_id": "order_123",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": "tp_001",
                "sl_order_id": None,
            }
        ]
        mock_position_tracker.get_orphaned_positions.return_value = orphaned
        mock_bitbank_client.fetch_margin_positions.return_value = []

        result = await cleanup.cleanup_orphaned_positions(mock_bitbank_client)

        assert result["success"] is True
        assert result["cleaned"] == 1
        assert result["orphaned_positions"] == 1
        mock_position_tracker.remove_position.assert_called_once_with("order_123")

    @pytest.mark.asyncio
    async def test_cleanup_sl_order_only(self, cleanup, mock_position_tracker, mock_bitbank_client):
        """SL注文のみクリーンアップ"""
        cleanup.inject_position_tracker(mock_position_tracker)

        orphaned = [
            {
                "order_id": "order_123",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": None,
                "sl_order_id": "sl_001",
            }
        ]
        mock_position_tracker.get_orphaned_positions.return_value = orphaned
        mock_bitbank_client.fetch_margin_positions.return_value = []

        result = await cleanup.cleanup_orphaned_positions(mock_bitbank_client)

        assert result["success"] is True
        assert result["cleaned"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_both_tp_sl_orders(self, cleanup, mock_position_tracker, mock_bitbank_client):
        """TP/SL両方クリーンアップ"""
        cleanup.inject_position_tracker(mock_position_tracker)

        orphaned = [
            {
                "order_id": "order_123",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": "tp_001",
                "sl_order_id": "sl_001",
            }
        ]
        mock_position_tracker.get_orphaned_positions.return_value = orphaned
        mock_bitbank_client.fetch_margin_positions.return_value = []

        result = await cleanup.cleanup_orphaned_positions(mock_bitbank_client)

        assert result["success"] is True
        assert result["cleaned"] == 2  # TP + SL

    @pytest.mark.asyncio
    async def test_cleanup_multiple_orphaned_positions(self, cleanup, mock_position_tracker, mock_bitbank_client):
        """複数孤児ポジションクリーンアップ"""
        cleanup.inject_position_tracker(mock_position_tracker)

        orphaned = [
            {"order_id": "order_1", "tp_order_id": "tp_001", "sl_order_id": "sl_001"},
            {"order_id": "order_2", "tp_order_id": "tp_002", "sl_order_id": None},
            {"order_id": "order_3", "tp_order_id": None, "sl_order_id": "sl_003"},
        ]
        mock_position_tracker.get_orphaned_positions.return_value = orphaned
        mock_bitbank_client.fetch_margin_positions.return_value = []

        result = await cleanup.cleanup_orphaned_positions(mock_bitbank_client)

        assert result["success"] is True
        assert result["cleaned"] == 4  # 2 + 1 + 1
        assert result["orphaned_positions"] == 3
        assert mock_position_tracker.remove_position.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_partial_failure(self, cleanup, mock_position_tracker):
        """一部注文キャンセル失敗"""
        cleanup.inject_position_tracker(mock_position_tracker)

        orphaned = [{"order_id": "order_123", "tp_order_id": "tp_001", "sl_order_id": "sl_001"}]
        mock_position_tracker.get_orphaned_positions.return_value = orphaned

        mock_client = AsyncMock()
        mock_client.fetch_margin_positions.return_value = []
        # TP成功、SL失敗
        mock_client.cancel_order = AsyncMock(
            side_effect=[
                {"status": "CANCELED_UNFILLED"},  # TP成功
                Exception("API Error"),  # SL失敗
            ]
        )

        result = await cleanup.cleanup_orphaned_positions(mock_client)

        assert result["success"] is True
        assert result["cleaned"] == 1  # TPのみ
        assert len(result["failed_cancels"]) == 1
        assert "SL:sl_001" in result["failed_cancels"]

    @pytest.mark.asyncio
    async def test_cleanup_exception_handling(self, cleanup, mock_position_tracker):
        """例外ハンドリング"""
        cleanup.inject_position_tracker(mock_position_tracker)

        mock_client = AsyncMock()
        mock_client.fetch_margin_positions = AsyncMock(side_effect=Exception("API Error"))

        result = await cleanup.cleanup_orphaned_positions(mock_client)

        assert result["success"] is False
        assert "クリーンアップエラー" in result["message"] or "実ポジション取得失敗" in result["message"]


class TestFetchActualPositions:
    """_fetch_actual_positions() テスト"""

    @pytest.mark.asyncio
    async def test_fetch_success(self, cleanup, mock_bitbank_client):
        """ポジション取得成功"""
        mock_bitbank_client.fetch_margin_positions.return_value = [
            {"side": "buy", "amount": "0.001", "price": "14000000"},
            {"side": "sell", "amount": "0.002", "price": "14500000"},
        ]

        result = await cleanup._fetch_actual_positions(mock_bitbank_client)

        assert result is not None
        assert len(result) == 2
        assert result[0]["side"] == "buy"
        assert result[0]["amount"] == 0.001
        assert result[0]["price"] == 14000000.0

    @pytest.mark.asyncio
    async def test_fetch_empty_positions(self, cleanup, mock_bitbank_client):
        """空ポジション取得"""
        mock_bitbank_client.fetch_margin_positions.return_value = []

        result = await cleanup._fetch_actual_positions(mock_bitbank_client)

        assert result is not None
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_failure(self, cleanup):
        """ポジション取得失敗"""
        mock_client = AsyncMock()
        mock_client.fetch_margin_positions = AsyncMock(return_value=None)

        result = await cleanup._fetch_actual_positions(mock_client)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_exception(self, cleanup):
        """ポジション取得例外"""
        mock_client = AsyncMock()
        mock_client.fetch_margin_positions = AsyncMock(side_effect=Exception("API Error"))

        result = await cleanup._fetch_actual_positions(mock_client)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_side_normalization(self, cleanup, mock_bitbank_client):
        """サイド正規化（小文字化）"""
        mock_bitbank_client.fetch_margin_positions.return_value = [
            {"side": "BUY", "amount": "0.001", "price": "14000000"},
            {"side": "SELL", "amount": "0.002", "price": "14500000"},
        ]

        result = await cleanup._fetch_actual_positions(mock_bitbank_client)

        assert result[0]["side"] == "buy"
        assert result[1]["side"] == "sell"


class TestCancelOrder:
    """_cancel_order() テスト"""

    @pytest.mark.asyncio
    async def test_cancel_success(self, cleanup, mock_bitbank_client):
        """キャンセル成功"""
        mock_bitbank_client.cancel_order.return_value = {"status": "CANCELED_UNFILLED"}

        result = await cleanup._cancel_order(mock_bitbank_client, "order_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_already_canceled(self, cleanup, mock_bitbank_client):
        """既にキャンセル済み"""
        mock_bitbank_client.cancel_order.return_value = {"status": "CANCELED_PARTIALLY_FILLED"}

        result = await cleanup._cancel_order(mock_bitbank_client, "order_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_already_filled(self, cleanup, mock_bitbank_client):
        """既に約定済み"""
        mock_bitbank_client.cancel_order.return_value = {"status": "FULLY_FILLED"}

        result = await cleanup._cancel_order(mock_bitbank_client, "order_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_not_found(self, cleanup):
        """注文が存在しない（エラー60002）"""
        mock_client = AsyncMock()
        mock_client.cancel_order = AsyncMock(side_effect=Exception("bitbank API Error 60002: Order not found"))

        result = await cleanup._cancel_order(mock_client, "order_123")

        assert result is True  # 既に削除済みとして成功扱い

    @pytest.mark.asyncio
    async def test_cancel_other_error(self, cleanup):
        """その他のエラー"""
        mock_client = AsyncMock()
        mock_client.cancel_order = AsyncMock(side_effect=Exception("API connection error"))

        result = await cleanup._cancel_order(mock_client, "order_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_unknown_status(self, cleanup, mock_bitbank_client):
        """不明なステータス"""
        mock_bitbank_client.cancel_order.return_value = {"status": "UNKNOWN_STATUS"}

        result = await cleanup._cancel_order(mock_bitbank_client, "order_123")

        assert result is False


class TestCheckStalePositions:
    """check_stale_positions() テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.position.cleanup.get_threshold")
    async def test_no_tracker(self, mock_threshold, cleanup):
        """PositionTracker未注入"""
        result = await cleanup.check_stale_positions()

        assert result == []

    @pytest.mark.asyncio
    @patch("src.trading.position.cleanup.get_threshold")
    async def test_no_stale_positions(self, mock_threshold, cleanup, mock_position_tracker):
        """古いポジションなし"""
        mock_threshold.return_value = 24
        cleanup.inject_position_tracker(mock_position_tracker)

        recent_position = {"order_id": "order_123", "timestamp": datetime.now()}
        mock_position_tracker.get_all_positions.return_value = [recent_position]

        result = await cleanup.check_stale_positions()

        assert len(result) == 0

    @pytest.mark.asyncio
    @patch("src.trading.position.cleanup.get_threshold")
    async def test_stale_positions_detected(self, mock_threshold, cleanup, mock_position_tracker):
        """古いポジション検出"""
        mock_threshold.return_value = 24
        cleanup.inject_position_tracker(mock_position_tracker)

        old_position = {
            "order_id": "order_123",
            "timestamp": datetime.now() - timedelta(hours=25),
        }
        recent_position = {"order_id": "order_456", "timestamp": datetime.now()}

        mock_position_tracker.get_all_positions.return_value = [old_position, recent_position]

        result = await cleanup.check_stale_positions()

        assert len(result) == 1
        assert result[0]["order_id"] == "order_123"

    @pytest.mark.asyncio
    @patch("src.trading.position.cleanup.get_threshold")
    async def test_custom_max_age(self, mock_threshold, cleanup, mock_position_tracker):
        """カスタム最大保持時間"""
        cleanup.inject_position_tracker(mock_position_tracker)

        old_position = {
            "order_id": "order_123",
            "timestamp": datetime.now() - timedelta(hours=13),
        }
        mock_position_tracker.get_all_positions.return_value = [old_position]

        result = await cleanup.check_stale_positions(max_age_hours=12)

        assert len(result) == 1

    @pytest.mark.asyncio
    @patch("src.trading.position.cleanup.get_threshold")
    async def test_invalid_timestamp_ignored(self, mock_threshold, cleanup, mock_position_tracker):
        """無効なtimestampは無視"""
        mock_threshold.return_value = 24
        cleanup.inject_position_tracker(mock_position_tracker)

        invalid_position = {"order_id": "order_123", "timestamp": "invalid"}
        mock_position_tracker.get_all_positions.return_value = [invalid_position]

        result = await cleanup.check_stale_positions()

        assert len(result) == 0


class TestGetCleanupStats:
    """get_cleanup_stats() テスト"""

    def test_no_tracker(self, cleanup):
        """PositionTracker未注入"""
        stats = cleanup.get_cleanup_stats()

        assert stats["virtual_positions"] == 0
        assert stats["total_exposure"] == 0

    def test_empty_positions(self, cleanup, mock_position_tracker):
        """空ポジション統計"""
        cleanup.inject_position_tracker(mock_position_tracker)
        mock_position_tracker.get_all_positions.return_value = []
        mock_position_tracker.get_total_exposure.return_value = {"buy": 0, "sell": 0, "total": 0}

        stats = cleanup.get_cleanup_stats()

        assert stats["virtual_positions"] == 0
        assert stats["total_exposure"] == 0
        assert stats["position_sides"]["buy"] == 0
        assert stats["position_sides"]["sell"] == 0

    def test_mixed_positions(self, cleanup, mock_position_tracker):
        """買い・売り混在統計"""
        cleanup.inject_position_tracker(mock_position_tracker)

        positions = [
            {"side": "buy", "amount": 0.001},
            {"side": "buy", "amount": 0.002},
            {"side": "sell", "amount": 0.003},
        ]
        mock_position_tracker.get_all_positions.return_value = positions
        mock_position_tracker.get_total_exposure.return_value = {
            "buy": 30000.0,
            "sell": 42000.0,
            "total": 72000.0,
        }

        stats = cleanup.get_cleanup_stats()

        assert stats["virtual_positions"] == 3
        assert stats["total_exposure"] == 72000.0
        assert stats["position_sides"]["buy"] == 2
        assert stats["position_sides"]["sell"] == 1
        assert stats["buy_exposure"] == 30000.0
        assert stats["sell_exposure"] == 42000.0

    def test_case_insensitive_side(self, cleanup, mock_position_tracker):
        """サイド大文字小文字対応"""
        cleanup.inject_position_tracker(mock_position_tracker)

        positions = [
            {"side": "BUY", "amount": 0.001},
            {"side": "SELL", "amount": 0.002},
        ]
        mock_position_tracker.get_all_positions.return_value = positions
        mock_position_tracker.get_total_exposure.return_value = {
            "buy": 14000.0,
            "sell": 28000.0,
            "total": 42000.0,
        }

        stats = cleanup.get_cleanup_stats()

        assert stats["position_sides"]["buy"] == 1
        assert stats["position_sides"]["sell"] == 1


class TestEmergencyCleanup:
    """emergency_cleanup() テスト"""

    @pytest.mark.asyncio
    async def test_no_tracker(self, cleanup, mock_bitbank_client):
        """PositionTracker未注入"""
        result = await cleanup.emergency_cleanup(mock_bitbank_client)

        assert result["success"] is False
        assert "PositionTrackerが未注入" in result["message"]

    @pytest.mark.asyncio
    async def test_no_positions(self, cleanup, mock_position_tracker, mock_bitbank_client):
        """仮想ポジションなし"""
        cleanup.inject_position_tracker(mock_position_tracker)
        mock_position_tracker.get_all_positions.return_value = []

        result = await cleanup.emergency_cleanup(mock_bitbank_client)

        assert result["success"] is True
        assert "仮想ポジションなし" in result["message"]
        assert result["cleaned"] == 0

    @pytest.mark.asyncio
    async def test_emergency_cleanup_without_client(self, cleanup, mock_position_tracker):
        """BitbankClientなしで緊急クリーンアップ"""
        cleanup.inject_position_tracker(mock_position_tracker)

        positions = [
            {"order_id": "order_1", "tp_order_id": "tp_001", "sl_order_id": "sl_001"},
            {"order_id": "order_2", "tp_order_id": "tp_002", "sl_order_id": None},
        ]
        mock_position_tracker.get_all_positions.return_value = positions
        mock_position_tracker.clear_all_positions.return_value = 2

        result = await cleanup.emergency_cleanup(None)

        assert result["success"] is True
        assert result["cleaned"] == 2
        assert result["canceled_orders"] == 0

    @pytest.mark.asyncio
    async def test_emergency_cleanup_with_client(self, cleanup, mock_position_tracker):
        """BitbankClient利用で緊急クリーンアップ"""
        cleanup.inject_position_tracker(mock_position_tracker)

        positions = [
            {"order_id": "order_1", "tp_order_id": "tp_001", "sl_order_id": "sl_001"},
            {"order_id": "order_2", "tp_order_id": "tp_002", "sl_order_id": None},
        ]
        mock_position_tracker.get_all_positions.return_value = positions
        mock_position_tracker.clear_all_positions.return_value = 2

        mock_client = AsyncMock()
        mock_client.cancel_order = AsyncMock(return_value={"status": "CANCELED_UNFILLED"})

        result = await cleanup.emergency_cleanup(mock_client)

        assert result["success"] is True
        assert result["cleaned"] == 2
        assert result["canceled_orders"] == 3  # tp_001, sl_001, tp_002

    @pytest.mark.asyncio
    async def test_emergency_cleanup_partial_cancel_failure(self, cleanup, mock_position_tracker):
        """一部注文キャンセル失敗"""
        cleanup.inject_position_tracker(mock_position_tracker)

        positions = [{"order_id": "order_1", "tp_order_id": "tp_001", "sl_order_id": "sl_001"}]
        mock_position_tracker.get_all_positions.return_value = positions
        mock_position_tracker.clear_all_positions.return_value = 1

        mock_client = AsyncMock()
        mock_client.cancel_order = AsyncMock(
            side_effect=[
                {"status": "CANCELED_UNFILLED"},  # TP成功
                Exception("API Error"),  # SL失敗
            ]
        )

        result = await cleanup.emergency_cleanup(mock_client)

        assert result["success"] is True
        assert result["cleaned"] == 1
        assert result["canceled_orders"] == 1  # TPのみ

    @pytest.mark.asyncio
    async def test_emergency_cleanup_exception(self, cleanup, mock_position_tracker):
        """例外ハンドリング"""
        cleanup.inject_position_tracker(mock_position_tracker)
        mock_position_tracker.get_all_positions.side_effect = Exception("Tracker error")

        result = await cleanup.emergency_cleanup(None)

        assert result["success"] is False
        assert "緊急クリーンアップエラー" in result["message"]


class TestInitialization:
    """初期化テスト"""

    def test_cleanup_initialization(self, cleanup):
        """PositionCleanup初期化"""
        assert hasattr(cleanup, "logger")
        assert hasattr(cleanup, "position_tracker")
        assert cleanup.position_tracker is None

    def test_inject_position_tracker(self, cleanup, mock_position_tracker):
        """PositionTracker注入"""
        cleanup.inject_position_tracker(mock_position_tracker)

        assert cleanup.position_tracker is mock_position_tracker
