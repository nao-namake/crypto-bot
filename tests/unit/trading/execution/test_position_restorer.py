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
        """Phase 64.12: 価格乖離3%超のSL注文を除外

        Phase 86 注: 孤児SLが除外されると緊急SL配置が試行されるため、
        本テストでは create_stop_loss_order が失敗するモックを設定し、
        sl_order_id=None を維持する。
        """
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

        # Phase 86: 緊急SL配置が試行されるが失敗するように設定
        mock_client.create_stop_loss_order = MagicMock(
            side_effect=Exception("test: emergency SL placement failure simulation")
        )

        virtual_positions = []
        await restorer.restore_positions_from_api(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

        # 復元されたがSLは除外（緊急配置も失敗）
        assert len(virtual_positions) == 1
        vp = virtual_positions[0]
        assert vp["tp_order_id"] == "tp_001"
        assert vp["sl_order_id"] is None  # 孤児SLは除外、緊急配置も失敗

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

    async def test_phase86_emergency_sl_placement_success(self, restorer):
        """Phase 86: SL注文がない場合に緊急SL配置が実行され、sl_order_idが設定される"""
        from unittest.mock import AsyncMock

        avg_price = 12_840_001.0

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.015, "average_price": avg_price}]
        )
        # TP注文のみ存在、SL注文なし
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_001",
                    "side": "sell",
                    "type": "limit",
                    "price": avg_price + 100_000,
                },
            ]
        )
        # 緊急SL配置成功
        mock_client.create_stop_loss_order = MagicMock(
            return_value={"id": "emergency_sl_42", "price": avg_price * 0.99}
        )

        virtual_positions = []
        await restorer.restore_positions_from_api(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

        # Phase 86: 緊急SL配置で sl_order_id が設定される
        assert len(virtual_positions) == 1
        vp = virtual_positions[0]
        assert vp["tp_order_id"] == "tp_001"
        assert vp["sl_order_id"] == "emergency_sl_42"
        # create_stop_loss_order が呼ばれたことを確認
        assert mock_client.create_stop_loss_order.called


# ========================================
# Phase 65.15: NoneType安全性・take_profit型判定テスト
# ========================================


class TestPhase6515NoneTypeSafety:
    """Phase 65.15: position_restorer.pyのNoneType安全性テスト"""

    @pytest.fixture
    def restorer(self):
        return PositionRestorer()

    async def test_restore_with_none_amount_in_orders(self, restorer):
        """Phase 65.15: active_ordersのamountがNoneでもTypeErrorにならない"""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": 10000000}]
        )
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_1",
                    "side": "sell",
                    "type": "limit",
                    "price": 10100000,
                    "amount": None,  # NoneでTypeError回避
                },
                {
                    "id": "sl_1",
                    "side": "sell",
                    "type": "stop_limit",
                    "price": 9900000,
                    "stopPrice": 9900000,
                    "amount": None,  # NoneでTypeError回避
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
        assert virtual_positions[0]["tp_order_id"] == "tp_1"
        assert virtual_positions[0]["sl_order_id"] == "sl_1"

    async def test_restore_with_none_trigger_prices(self, restorer):
        """Phase 65.15: stopPrice/triggerPrice/priceが全てNoneでもクラッシュしない"""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": 10000000}]
        )
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "sl_none_prices",
                    "side": "sell",
                    "type": "stop_limit",
                    "stopPrice": None,
                    "triggerPrice": None,
                    "price": None,
                    "amount": "0.01",
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

        # trigger_price=0で妥当性検証スキップされSLマッチング
        assert len(virtual_positions) == 1

    async def test_orphan_scan_with_none_amount(self, restorer):
        """Phase 65.15: 孤児スキャンでamount=NoneのTP/SL注文があってもクラッシュしない"""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": 10000000}]
        )
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_none",
                    "side": "sell",
                    "type": "take_profit",
                    "amount": None,
                },
                {
                    "id": "sl_none",
                    "side": "sell",
                    "type": "stop_limit",
                    "amount": None,
                },
            ]
        )

        mock_tp_sl = MagicMock()
        mock_tp_sl.calculate_recovery_tp_sl_prices = MagicMock(return_value=(10100000, 9900000))
        mock_tp_sl.place_tp_with_retry = AsyncMock(return_value={"order_id": "tp_new"})
        mock_tp_sl.place_sl_or_market_close = AsyncMock(return_value={"order_id": "sl_new"})

        virtual_positions = []
        restorer._last_orphan_scan_time = None
        await restorer.scan_orphan_positions(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            tp_sl_manager=mock_tp_sl,
        )

        # amount=NoneでもTypeErrorにならずTP/SL設置試行される
        assert len(virtual_positions) == 1


class TestPhase6515TakeProfitTypeDetection:
    """Phase 65.15: take_profit型TP注文の判定テスト"""

    @pytest.fixture
    def restorer(self):
        return PositionRestorer()

    async def test_restore_matches_take_profit_type_tp(self, restorer):
        """Phase 65.15: take_profit型注文がTPとしてマッチングされる"""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": 10000000}]
        )
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_native_001",
                    "side": "sell",
                    "type": "take_profit",  # take_profit型
                    "price": 10100000,
                    "amount": "0.01",
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
        assert virtual_positions[0]["tp_order_id"] == "tp_native_001"

    async def test_orphan_scan_detects_take_profit_type(self, restorer):
        """Phase 65.15: 孤児スキャンでtake_profit型注文がTPとして検出される"""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": 10000000}]
        )
        # take_profit型TP(0.01) + stop_limit型SL(0.01) → 95%カバレッジ達成
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_native",
                    "side": "sell",
                    "type": "take_profit",
                    "amount": "0.01",
                },
                {
                    "id": "sl_001",
                    "side": "sell",
                    "type": "stop_limit",
                    "amount": "0.01",
                },
            ]
        )

        virtual_positions = []
        restorer._last_orphan_scan_time = None
        await restorer.scan_orphan_positions(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            tp_sl_manager=MagicMock(),
        )

        # Phase 89 C7: TP/SL 両方検出されて「既設置」判定 + 実 order_id を保持
        assert len(virtual_positions) == 1
        assert virtual_positions[0]["tp_order_id"] == "tp_native"
        assert virtual_positions[0]["sl_order_id"] == "sl_001"


# ========================================
# Phase 89 C7: 孤児スキャンで実 order_id を保持（placeholder "existing" 廃止）
# ========================================


class TestPhase89C7OrphanScanRealOrderId:
    """Phase 89 C7: 孤児スキャン時に "existing" placeholder ではなく実 order_id を保存"""

    @pytest.fixture
    def restorer(self):
        return PositionRestorer()

    async def test_orphan_scan_keeps_largest_amount_order_id(self, restorer):
        """複数 SL 注文がある場合、最大 amount の注文 ID が選択される"""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": 10000000}]
        )
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {"id": "tp_small", "side": "sell", "type": "limit", "amount": "0.004"},
                {"id": "tp_main", "side": "sell", "type": "limit", "amount": "0.010"},
                {"id": "sl_small", "side": "sell", "type": "stop", "amount": "0.003"},
                {"id": "sl_main", "side": "sell", "type": "stop_limit", "amount": "0.010"},
            ]
        )

        virtual_positions = []
        restorer._last_orphan_scan_time = None
        await restorer.scan_orphan_positions(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            tp_sl_manager=MagicMock(),
        )

        assert len(virtual_positions) == 1
        assert virtual_positions[0]["tp_order_id"] == "tp_main"
        assert virtual_positions[0]["sl_order_id"] == "sl_main"
        # placeholder string が含まれていないこと
        assert virtual_positions[0]["tp_order_id"] != "existing"
        assert virtual_positions[0]["sl_order_id"] != "existing"

    async def test_orphan_scan_short_side_picks_sl_real_id(self, restorer):
        """SHORT ポジでも実 order_id が取得される"""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "short", "amount": 0.02, "average_price": 10000000}]
        )
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {"id": "tp_short", "side": "buy", "type": "take_profit", "amount": "0.02"},
                {"id": "sl_short", "side": "buy", "type": "stop", "amount": "0.02"},
            ]
        )

        virtual_positions = []
        restorer._last_orphan_scan_time = None
        await restorer.scan_orphan_positions(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            tp_sl_manager=MagicMock(),
        )

        assert len(virtual_positions) == 1
        assert virtual_positions[0]["tp_order_id"] == "tp_short"
        assert virtual_positions[0]["sl_order_id"] == "sl_short"

    async def test_orphan_scan_missing_id_keeps_none(self, restorer):
        """active_orders で id 欠落時は None が入る（"existing" placeholder は使わない）"""
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.01, "average_price": 10000000}]
        )
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                # id を欠いた異常な注文（実機の防御テスト）
                {"side": "sell", "type": "limit", "amount": "0.01"},
                {"side": "sell", "type": "stop_limit", "amount": "0.01"},
            ]
        )

        virtual_positions = []
        restorer._last_orphan_scan_time = None
        await restorer.scan_orphan_positions(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            tp_sl_manager=MagicMock(),
        )

        # virtual_positions には追加されるが、tp/sl_order_id は None（critical ログ済み）
        assert len(virtual_positions) == 1
        assert virtual_positions[0]["tp_order_id"] is None
        assert virtual_positions[0]["sl_order_id"] is None


# ========================================
# Phase 87 H2: 起動時SL欠損サイレント失敗修正テスト
# ========================================


class TestPhase87H2EmergencyClose:
    """Phase 87 H2: emergency_sl_order={"id": None} / 例外時に
    sl_monitor.emergency_market_close が呼ばれることを検証"""

    @pytest.fixture
    def restorer(self):
        return PositionRestorer()

    async def test_restore_positions_emergency_close_on_empty_sl_id(self, restorer):
        """create_stop_loss_order が {"id": None} を返したら emergency_market_close 起動"""
        from unittest.mock import AsyncMock

        avg_price = 12_840_001.0

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.015, "average_price": avg_price}]
        )
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        # 緊急SL配置: order_id 空のレスポンス（bitbank の異常応答シミュレーション）
        mock_client.create_stop_loss_order = MagicMock(return_value={"id": None})

        # sl_monitor.emergency_market_close を AsyncMock 化（呼び出し検証用）
        restorer.sl_monitor.emergency_market_close = AsyncMock(
            return_value={"order_id": "emergency_close_1", "dry_run": False, "reason": "x"}
        )

        virtual_positions = []
        await restorer.restore_positions_from_api(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

        # emergency_market_close が呼ばれたことを検証
        restorer.sl_monitor.emergency_market_close.assert_called_once()
        call_kwargs = restorer.sl_monitor.emergency_market_close.call_args.kwargs
        assert call_kwargs["entry_side"] == "buy"  # long → buy
        assert call_kwargs["amount"] == 0.015
        assert call_kwargs["reason"] == "startup_sl_placement_empty_id"

    async def test_restore_positions_emergency_close_on_exception(self, restorer):
        """create_stop_loss_order が例外を投げたら emergency_market_close 起動"""
        from unittest.mock import AsyncMock

        avg_price = 12_840_001.0

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "short", "amount": 0.02, "average_price": avg_price}]
        )
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        # 緊急SL配置: 例外発生
        mock_client.create_stop_loss_order = MagicMock(
            side_effect=RuntimeError("bitbank API error 50061")
        )

        restorer.sl_monitor.emergency_market_close = AsyncMock(
            return_value={"order_id": "emergency_close_2", "dry_run": False, "reason": "x"}
        )

        virtual_positions = []
        await restorer.restore_positions_from_api(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

        # except 分岐から emergency_market_close 呼ばれる
        restorer.sl_monitor.emergency_market_close.assert_called_once()
        call_kwargs = restorer.sl_monitor.emergency_market_close.call_args.kwargs
        assert call_kwargs["entry_side"] == "sell"  # short → sell
        assert call_kwargs["amount"] == 0.02
        assert call_kwargs["reason"] == "startup_sl_placement_exception"
