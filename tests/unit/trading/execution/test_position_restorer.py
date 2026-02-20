"""
PositionRestorer テスト - Phase 64

stop_manager.py から移動したクリーンアップメソッドのテスト:
- cleanup_old_unfilled_orders (Phase 51.6)
- cleanup_orphan_sl_orders (Phase 59.6)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.trading.execution.position_restorer import PositionRestorer

pytestmark = pytest.mark.asyncio


# ========================================
# Phase 51.6: 古い注文クリーンアップテスト
# ========================================


class TestPhase516CleanupOldUnfilledOrders:
    """Phase 51.6: 古い未約定注文クリーンアップのテスト"""

    @pytest.fixture
    def restorer(self):
        """PositionRestorerインスタンス"""
        return PositionRestorer()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        return client

    async def test_cleanup_old_orphan_orders_success(self, restorer, mock_bitbank_client):
        """Phase 51.6: 古い孤児注文クリーンアップ - 成功"""
        # 24時間以上前の古い注文
        old_time = (datetime.now() - timedelta(hours=25)).timestamp() * 1000

        # アクティブ注文をモック（31件・30件制限超過）
        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                # 古い孤児TP注文（削除対象）
                {
                    "id": "old_tp_1",
                    "pair": "btc_jpy",
                    "side": "sell",
                    "type": "limit",
                    "timestamp": old_time,
                },
                {
                    "id": "old_tp_2",
                    "pair": "btc_jpy",
                    "side": "sell",
                    "type": "limit",
                    "timestamp": old_time,
                },
                # アクティブポジションのTP/SL注文（保護対象）
                {
                    "id": "active_tp_1",
                    "pair": "btc_jpy",
                    "side": "sell",
                    "type": "limit",
                    "timestamp": old_time,
                },
                {
                    "id": "active_sl_1",
                    "pair": "btc_jpy",
                    "side": "buy",
                    "type": "limit",
                    "timestamp": old_time,
                },
            ]
        )

        # アクティブポジション（TP/SL注文IDを持つ）
        virtual_positions = [
            {
                "order_id": "position_1",
                "tp_order_id": "active_tp_1",  # 保護対象
                "sl_order_id": "active_sl_1",  # 保護対象
            }
        ]

        # キャンセル成功をモック
        mock_bitbank_client.cancel_order = MagicMock(return_value={"success": True})

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=virtual_positions,
            max_age_hours=24,
            threshold_count=3,  # 3件以上で発動
        )

        # 2件の古い孤児注文がキャンセルされることを確認
        assert result["cancelled_count"] == 2
        assert mock_bitbank_client.cancel_order.call_count == 2

    async def test_cleanup_protects_active_positions(self, restorer, mock_bitbank_client):
        """Phase 51.6: アクティブポジションのTP/SL注文を保護"""
        old_time = (datetime.now() - timedelta(hours=25)).timestamp() * 1000

        # アクティブ注文をモック
        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                # アクティブポジションのTP/SL注文（保護対象・削除しない）
                {
                    "id": "active_tp_1",
                    "pair": "btc_jpy",
                    "side": "sell",
                    "type": "limit",
                    "timestamp": old_time,
                },
                {
                    "id": "active_sl_1",
                    "pair": "btc_jpy",
                    "side": "buy",
                    "type": "limit",
                    "timestamp": old_time,
                },
            ]
        )

        # アクティブポジション
        virtual_positions = [
            {
                "order_id": "position_1",
                "tp_order_id": "active_tp_1",  # 保護対象
                "sl_order_id": "active_sl_1",  # 保護対象
            }
        ]

        mock_bitbank_client.cancel_order = MagicMock(return_value={"success": True})

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=virtual_positions,
            max_age_hours=24,
            threshold_count=1,
        )

        # アクティブポジションのTP/SL注文は削除されない
        assert result["cancelled_count"] == 0
        assert mock_bitbank_client.cancel_order.call_count == 0

    async def test_cleanup_below_threshold_skips(self, restorer, mock_bitbank_client):
        """Phase 51.6: 閾値未満の場合はクリーンアップスキップ"""
        old_time = (datetime.now() - timedelta(hours=25)).timestamp() * 1000

        # アクティブ注文をモック（2件のみ）
        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "old_tp_1",
                    "pair": "btc_jpy",
                    "side": "sell",
                    "type": "limit",
                    "timestamp": old_time,
                },
                {
                    "id": "old_tp_2",
                    "pair": "btc_jpy",
                    "side": "sell",
                    "type": "limit",
                    "timestamp": old_time,
                },
            ]
        )

        virtual_positions = []

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=virtual_positions,
            max_age_hours=24,
            threshold_count=25,  # 閾値25件（2件では未達）
        )

        # 閾値未満のためスキップ（cancelled_count=0, order_count=2）
        assert result["cancelled_count"] == 0
        assert result["order_count"] == 2
        assert result["errors"] == []


# ========================================
# Phase 51.6: cleanup_old_unfilled_orders() 詳細テスト
# ========================================


class TestCleanupOldUnfilledOrdersDetailed:
    """Phase 51.6: cleanup_old_unfilled_orders() 詳細テスト"""

    @pytest.fixture
    def restorer(self):
        """PositionRestorerインスタンス"""
        return PositionRestorer()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        return client

    async def test_cleanup_cancel_failure_non_not_found(self, restorer, mock_bitbank_client):
        """Phase 51.6: キャンセル失敗（OrderNotFound以外）はエラー記録"""
        old_time = (datetime.now() - timedelta(hours=25)).timestamp() * 1000

        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "old_tp_1",
                    "type": "limit",
                    "timestamp": old_time,
                }
            ]
        )
        mock_bitbank_client.cancel_order = MagicMock(
            side_effect=Exception("API Rate Limit")  # OrderNotFound以外
        )

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=[],
            max_age_hours=24,
            threshold_count=1,
        )

        # エラーが記録される
        assert len(result["errors"]) == 1
        assert "API Rate Limit" in result["errors"][0]

    async def test_cleanup_exception_handling(self, restorer, mock_bitbank_client):
        """Phase 51.6: 例外発生時のエラーハンドリング"""
        mock_bitbank_client.fetch_active_orders = MagicMock(side_effect=Exception("API Error"))

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=[],
            max_age_hours=24,
            threshold_count=1,
        )

        # 例外発生時はエラーを返す
        assert result["cancelled_count"] == 0
        assert result["order_count"] == 0
        assert "API Error" in result["errors"][0]

    async def test_cleanup_no_old_orphan_orders(self, restorer, mock_bitbank_client):
        """Phase 51.6: 古い孤児注文なし"""
        # 1時間前の注文（24時間以内なので対象外）
        recent_time = (datetime.now() - timedelta(hours=1)).timestamp() * 1000

        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "recent_tp_1",
                    "type": "limit",
                    "timestamp": recent_time,
                }
            ]
            * 30  # 30件（閾値超過）
        )

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=[],
            max_age_hours=24,
            threshold_count=25,
        )

        # 24時間以内なのでクリーンアップなし
        assert result["cancelled_count"] == 0
        assert result["order_count"] == 30

    async def test_cleanup_restored_positions_protected(self, restorer, mock_bitbank_client):
        """Phase 53.12: 復元されたポジションのorder_idを保護"""
        old_time = (datetime.now() - timedelta(hours=25)).timestamp() * 1000

        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "restored_order_1",
                    "type": "limit",
                    "timestamp": old_time,
                }
            ]
        )

        # 復元されたポジション
        virtual_positions = [
            {
                "order_id": "restored_order_1",
                "restored": True,  # 復元フラグ
            }
        ]

        mock_bitbank_client.cancel_order = MagicMock(return_value={"success": True})

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=virtual_positions,
            max_age_hours=24,
            threshold_count=1,
        )

        # 復元されたポジションのorder_idは保護される
        assert result["cancelled_count"] == 0

    async def test_cleanup_skips_non_limit_orders(self, restorer, mock_bitbank_client):
        """Phase 51.6: limit以外の注文タイプはスキップ"""
        old_time = (datetime.now() - timedelta(hours=25)).timestamp() * 1000

        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "stop_order_1",
                    "type": "stop",  # limit以外
                    "timestamp": old_time,
                },
                {
                    "id": "market_order_1",
                    "type": "market",  # limit以外
                    "timestamp": old_time,
                },
            ]
        )

        mock_bitbank_client.cancel_order = MagicMock(return_value={"success": True})

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=[],
            max_age_hours=24,
            threshold_count=1,
        )

        # limit以外はスキップ
        assert result["cancelled_count"] == 0

    async def test_cleanup_cancel_order_not_found(self, restorer, mock_bitbank_client):
        """Phase 51.6: OrderNotFoundは許容（キャンセル成功扱い）"""
        old_time = (datetime.now() - timedelta(hours=25)).timestamp() * 1000

        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "old_tp_1",
                    "type": "limit",
                    "timestamp": old_time,
                }
            ]
        )
        mock_bitbank_client.cancel_order = MagicMock(
            side_effect=Exception("OrderNotFound: not found")
        )

        result = await restorer.cleanup_old_unfilled_orders(
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            virtual_positions=[],
            max_age_hours=24,
            threshold_count=1,
        )

        # OrderNotFoundは許容（エラー記録なし）
        assert len(result["errors"]) == 0


# ========================================
# Phase 59.6: 孤児SLクリーンアップテスト
# ========================================


class TestPhase596OrphanSLCleanup:
    """Phase 59.6: 孤児SLクリーンアップ - PositionRestorer版"""

    @pytest.fixture
    def restorer(self):
        """PositionRestorerインスタンス"""
        return PositionRestorer()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック（同期メソッドとして呼ばれる）"""
        client = MagicMock()
        client.cancel_order = MagicMock(return_value={"success": True})
        return client

    async def test_cleanup_orphan_sl_orders_no_file(self, restorer, mock_bitbank_client):
        """Phase 59.6: 孤児SLクリーンアップ - ファイルなし"""
        # ファイルが存在しない場合
        with patch.object(Path, "exists", return_value=False):
            result = await restorer.cleanup_orphan_sl_orders(
                bitbank_client=mock_bitbank_client, symbol="BTC/JPY"
            )

        assert result["cleaned"] == 0
        assert result["failed"] == 0

    async def test_cleanup_orphan_sl_orders_success(self, restorer, mock_bitbank_client):
        """Phase 59.6: 孤児SLクリーンアップ - 成功"""
        orphan_data = [
            {"sl_order_id": "sl_001", "reason": "take_profit", "timestamp": "2026-01-16T10:00:00"},
            {"sl_order_id": "sl_002", "reason": "manual", "timestamp": "2026-01-16T11:00:00"},
        ]

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(orphan_data)
        mock_path.unlink = MagicMock()

        with patch("src.trading.execution.position_restorer.Path", return_value=mock_path):
            result = await restorer.cleanup_orphan_sl_orders(
                bitbank_client=mock_bitbank_client, symbol="BTC/JPY"
            )

        # 2件の孤児SLがクリーンアップされる
        assert result["cleaned"] == 2
        assert result["failed"] == 0
        assert mock_bitbank_client.cancel_order.call_count == 2

    async def test_cleanup_orphan_sl_orders_partial_failure(self, restorer, mock_bitbank_client):
        """Phase 59.6: 孤児SLクリーンアップ - 部分失敗"""
        orphan_data = [
            {"sl_order_id": "sl_001", "reason": "take_profit", "timestamp": "2026-01-16T10:00:00"},
            {"sl_order_id": "sl_002", "reason": "manual", "timestamp": "2026-01-16T11:00:00"},
        ]

        # 1件目成功、2件目失敗（APIエラー - "not found"を含まないエラー）
        mock_bitbank_client.cancel_order = MagicMock(
            side_effect=[{"success": True}, Exception("API rate limit exceeded")]
        )

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(orphan_data)
        mock_path.unlink = MagicMock()

        with patch("src.trading.execution.position_restorer.Path", return_value=mock_path):
            result = await restorer.cleanup_orphan_sl_orders(
                bitbank_client=mock_bitbank_client, symbol="BTC/JPY"
            )

        assert result["cleaned"] == 1
        assert result["failed"] == 1


# ========================================
# Phase 59.6: cleanup_orphan_sl_orders() エッジケーステスト
# ========================================


class TestCleanupOrphanSLOrdersEdgeCases:
    """Phase 59.6: cleanup_orphan_sl_orders() エッジケーステスト"""

    @pytest.fixture
    def restorer(self):
        """PositionRestorerインスタンス"""
        return PositionRestorer()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.cancel_order = MagicMock(return_value={"success": True})
        return client

    async def test_empty_orphans_list(self, restorer, mock_bitbank_client):
        """空の孤児リストの場合"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps([])
        mock_path.unlink = MagicMock()

        with patch("src.trading.execution.position_restorer.Path", return_value=mock_path):
            result = await restorer.cleanup_orphan_sl_orders(
                bitbank_client=mock_bitbank_client, symbol="BTC/JPY"
            )

        assert result["cleaned"] == 0
        assert result["failed"] == 0

    async def test_json_decode_error(self, restorer, mock_bitbank_client):
        """JSONデコードエラーの場合"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "invalid json"
        mock_path.unlink = MagicMock()

        with patch("src.trading.execution.position_restorer.Path", return_value=mock_path):
            result = await restorer.cleanup_orphan_sl_orders(
                bitbank_client=mock_bitbank_client, symbol="BTC/JPY"
            )

        assert result["cleaned"] == 0
        assert "JSONデコードエラー" in result["errors"]

    async def test_orphan_without_order_id(self, restorer, mock_bitbank_client):
        """order_idがない孤児は無視"""
        orphan_data = [
            {"reason": "take_profit", "timestamp": "2026-01-16T10:00:00"},  # sl_order_idなし
        ]

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps(orphan_data)
        mock_path.unlink = MagicMock()

        with patch("src.trading.execution.position_restorer.Path", return_value=mock_path):
            result = await restorer.cleanup_orphan_sl_orders(
                bitbank_client=mock_bitbank_client, symbol="BTC/JPY"
            )

        assert result["cleaned"] == 0
        mock_bitbank_client.cancel_order.assert_not_called()


# ========================================
# Phase 64.12: SL安全網テスト
# ========================================


class TestPhase6412SLSafetyNet:
    """Phase 64.12: SL復元マッチング価格検証テスト"""

    @pytest.fixture
    def restorer(self):
        return PositionRestorer()

    async def test_restore_skips_orphan_sl(self, restorer):
        """Phase 64.12: 価格乖離3%超のSL注文を除外"""
        from unittest.mock import AsyncMock

        avg_price = 10000000.0

        mock_client = MagicMock()
        # fetch_margin_positions is awaited directly (not via asyncio.to_thread)
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": avg_price}]
        )

        # fetch_active_orders is called via asyncio.to_thread (sync)
        orphan_sl_price = avg_price * 0.94  # 6%乖離 > 3%閾値
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_001",
                    "side": "sell",
                    "type": "limit",
                    "price": avg_price * 1.01,
                },
                {
                    "id": "orphan_sl_001",
                    "side": "sell",
                    "type": "stop_limit",
                    "price": orphan_sl_price,
                    "stopPrice": orphan_sl_price,
                },
            ]
        )

        virtual_positions = []
        await restorer.restore_positions_from_api(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

        # 復元されたがSLは除外
        assert len(virtual_positions) == 1
        vp = virtual_positions[0]
        assert vp["tp_order_id"] == "tp_001"
        assert vp["sl_order_id"] is None  # 孤児SLは除外

    async def test_restore_accepts_valid_sl(self, restorer):
        """Phase 64.12: 価格乖離3%以内のSL注文は正常マッチング"""
        from unittest.mock import AsyncMock

        avg_price = 10000000.0

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": avg_price}]
        )

        # SL価格が1%乖離（正常範囲）
        valid_sl_price = avg_price * 0.99
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "sl_valid",
                    "side": "sell",
                    "type": "stop_limit",
                    "price": valid_sl_price,
                    "stopPrice": valid_sl_price,
                },
            ]
        )

        virtual_positions = []
        await restorer.restore_positions_from_api(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

        assert len(virtual_positions) == 1
        assert virtual_positions[0]["sl_order_id"] == "sl_valid"
