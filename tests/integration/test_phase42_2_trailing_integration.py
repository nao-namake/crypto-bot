"""
Phase 42.2: トレーリングストップ Integration Tests

ExecutionService統合フローテスト（3ケース）

テスト範囲:
1. End-to-end トレーリング発動フロー
2. TPキャンセル統合処理
3. 複数回段階的トレーリング更新
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading.execution.executor import ExecutionService
from src.trading.execution.order_strategy import OrderStrategy
from src.trading.execution.stop_manager import StopManager
from src.trading.position.tracker import PositionTracker


@pytest.fixture
def execution_service():
    """ExecutionService fixture"""
    service = ExecutionService(mode="paper", bitbank_client=None)
    return service


@pytest.fixture
def position_tracker():
    """PositionTracker fixture"""
    return PositionTracker()


@pytest.fixture
def order_strategy():
    """OrderStrategy fixture"""
    return OrderStrategy()


@pytest.fixture
def stop_manager():
    """StopManager fixture"""
    return StopManager()


@pytest.fixture
def mock_bitbank_client():
    """BitbankClient mock fixture"""
    client = AsyncMock()
    client.cancel_order = AsyncMock(return_value={"success": True})
    client.create_stop_loss_order = Mock(return_value={"id": "trailing_sl_integration_123"})
    return client


class TestTrailingStopIntegration:
    """Phase 42.2 トレーリングストップ Integration Tests"""

    @pytest.mark.asyncio
    @patch("asyncio.to_thread")
    @patch("src.trading.execution.executor.get_threshold")
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_end_to_end_trailing_activation(
        self,
        mock_stop_threshold,
        mock_exec_threshold,
        mock_to_thread,
        execution_service,
        position_tracker,
        order_strategy,
        stop_manager,
        mock_bitbank_client,
    ):
        """Test 1: End-to-end トレーリング発動完全フロー"""

        # 設定モック: ExecutionService
        def exec_threshold_side_effect(key, default=None):
            if key == "position_management.tp_sl_mode":
                return "consolidated"
            elif "take_profit" in key:
                return {"enabled": True, "default_ratio": 2.5}
            elif "stop_loss" in key:
                return {"enabled": True}
            return default

        mock_exec_threshold.side_effect = exec_threshold_side_effect

        # 設定モック: StopManager
        def stop_threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": True,
                    "activation_profit": 0.02,
                    "trailing_percent": 0.03,
                    "min_update_distance": 200,
                    "min_profit_lock": 0.005,
                }
            elif "stop_loss" in key:
                return {"enabled": True}
            return default

        mock_stop_threshold.side_effect = stop_threshold_side_effect

        # asyncio.to_thread mock
        async def mock_to_thread_impl(func, *args):
            return {"success": True}

        mock_to_thread.side_effect = mock_to_thread_impl

        # サービス注入
        execution_service.bitbank_client = mock_bitbank_client
        execution_service.inject_services(
            order_strategy=order_strategy,
            stop_manager=stop_manager,
            position_tracker=position_tracker,
        )

        # Step 1: 統合ポジション作成・PositionTrackerにポジション追加
        position_tracker.add_position(
            order_id="order_123",
            side="buy",
            amount=0.003,
            price=14_000_000.0,
            take_profit=14_350_000.0,
            stop_loss=13_700_000.0,
            strategy_name="test_strategy",
        )
        position_tracker._average_entry_price = 14_000_000.0
        position_tracker._total_position_size = 0.003
        position_tracker.set_consolidated_tp_sl_ids(
            tp_order_id="tp_123",
            sl_order_id="sl_456",
            tp_price=14_350_000.0,  # TP: +2.5%
            sl_price=13_700_000.0,  # SL: -2.14%
            side="buy",
        )

        # Step 2: 価格上昇（+2.0%）→ トレーリング発動
        current_price = 14_280_000.0  # +2.0%

        result = await execution_service.monitor_trailing_conditions(current_price)

        # 検証: トレーリング発動成功
        assert result["trailing_activated"] is True
        assert result["new_sl_order_id"] == "trailing_sl_integration_123"
        # 新SL価格計算: 14,280,000 × 0.97 = 13,851,600円
        # しかし、min_profit_lockが適用される: 14,000,000 × 1.005 = 14,070,000円
        expected_new_sl = 14_000_000.0 * 1.005  # min_profit_lock適用後
        assert abs(result["new_sl_price"] - expected_new_sl) < 1.0

        # 検証: PositionTrackerのSL価格が更新されている
        consolidated_ids = position_tracker.get_consolidated_tp_sl_ids()
        assert consolidated_ids["sl_order_id"] == "trailing_sl_integration_123"
        assert abs(consolidated_ids["sl_price"] - expected_new_sl) < 1.0
        # TP価格は変更されていない
        assert consolidated_ids["tp_price"] == 14_350_000.0
        assert consolidated_ids["tp_order_id"] == "tp_123"

    @pytest.mark.asyncio
    @patch("asyncio.to_thread")
    @patch("src.trading.execution.executor.get_threshold")
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_trailing_with_tp_cancellation(
        self,
        mock_stop_threshold,
        mock_exec_threshold,
        mock_to_thread,
        execution_service,
        position_tracker,
        order_strategy,
        stop_manager,
        mock_bitbank_client,
    ):
        """Test 2: トレーリングSLがTP超過時のTPキャンセル統合処理"""

        # 設定モック: ExecutionService
        def exec_threshold_side_effect(key, default=None):
            if key == "position_management.tp_sl_mode":
                return "consolidated"
            elif key == "position_management.stop_loss.trailing.cancel_tp_when_exceeds":
                return True  # TPキャンセル有効
            elif "take_profit" in key:
                return {"enabled": True, "default_ratio": 2.5}
            elif "stop_loss" in key:
                return {"enabled": True}
            return default

        mock_exec_threshold.side_effect = exec_threshold_side_effect

        # 設定モック: StopManager
        def stop_threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": True,
                    "activation_profit": 0.02,
                    "trailing_percent": 0.03,
                    "min_update_distance": 200,
                    "min_profit_lock": 0.005,
                    "cancel_tp_when_exceeds": True,
                }
            elif "stop_loss" in key:
                return {"enabled": True}
            return default

        mock_stop_threshold.side_effect = stop_threshold_side_effect

        # asyncio.to_thread mock
        async def mock_to_thread_impl(func, *args):
            return {"success": True}

        mock_to_thread.side_effect = mock_to_thread_impl

        # サービス注入
        execution_service.bitbank_client = mock_bitbank_client
        execution_service.inject_services(
            order_strategy=order_strategy,
            stop_manager=stop_manager,
            position_tracker=position_tracker,
        )

        # ポジション設定: エントリー価格14,000,000円
        position_tracker.add_position(
            order_id="order_123",
            side="buy",
            amount=0.003,
            price=14_000_000.0,
            take_profit=14_350_000.0,
            stop_loss=13_700_000.0,
            strategy_name="test_strategy",
        )
        position_tracker._average_entry_price = 14_000_000.0
        position_tracker._total_position_size = 0.003
        position_tracker.set_consolidated_tp_sl_ids(
            tp_order_id="tp_123",
            sl_order_id="sl_456",
            tp_price=14_350_000.0,  # TP: +2.5%
            sl_price=13_700_000.0,  # SL: -2.14%
            side="buy",
        )

        # 価格大幅上昇（+3.5%）→ トレーリングSL発動 & TP超過
        current_price = 14_490_000.0  # +3.5%
        # 新SL計算: 14,490,000 × 0.97 = 14,055,300円
        # → 新SL（14,055,300円） < TP（14,350,000円）なのでTPキャンセルは発生しない

        # より大きな価格上昇でテスト: +5.0%
        current_price = 14_700_000.0  # +5.0%
        # 新SL計算: 14,700,000 × 0.97 = 14,259,000円
        # → 新SL（14,259,000円） < TP（14,350,000円）なのでまだTPキャンセルは発生しない

        # さらに大きな価格上昇: +7.0%
        current_price = 14_980_000.0  # +7.0%
        # 新SL計算: 14,980,000 × 0.97 = 14,530,600円
        # → 新SL（14,530,600円） > TP（14,350,000円）なのでTPキャンセル発生

        result = await execution_service.monitor_trailing_conditions(current_price)

        # 検証: トレーリング発動成功 & TPキャンセル実行
        assert result["trailing_activated"] is True
        new_sl_price = current_price * 0.97
        assert abs(result["new_sl_price"] - new_sl_price) < 1.0

        # 検証: TP注文がキャンセルされた（cancel_orderが2回呼ばれる: 既存SL + TP）
        # asyncio.to_threadがモックされているので、実際の呼び出し数は検証不可
        # しかし、PositionTrackerのTP注文IDがクリアされていることで確認できる
        consolidated_ids = position_tracker.get_consolidated_tp_sl_ids()
        assert consolidated_ids["tp_order_id"] is None  # TPキャンセル済み
        assert consolidated_ids["tp_price"] == 0.0
        # SL情報は更新されている
        assert consolidated_ids["sl_order_id"] == "trailing_sl_integration_123"
        assert abs(consolidated_ids["sl_price"] - new_sl_price) < 1.0

    @pytest.mark.asyncio
    @patch("asyncio.to_thread")
    @patch("src.trading.execution.executor.get_threshold")
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_multiple_trailing_updates(
        self,
        mock_stop_threshold,
        mock_exec_threshold,
        mock_to_thread,
        execution_service,
        position_tracker,
        order_strategy,
        stop_manager,
        mock_bitbank_client,
    ):
        """Test 3: 複数回段階的トレーリング更新シナリオ"""

        # 設定モック: ExecutionService
        def exec_threshold_side_effect(key, default=None):
            if key == "position_management.tp_sl_mode":
                return "consolidated"
            elif "take_profit" in key:
                return {"enabled": True}
            elif "stop_loss" in key:
                return {"enabled": True}
            return default

        mock_exec_threshold.side_effect = exec_threshold_side_effect

        # 設定モック: StopManager
        def stop_threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": True,
                    "activation_profit": 0.02,
                    "trailing_percent": 0.03,
                    "min_update_distance": 200,
                    "min_profit_lock": 0.005,
                }
            elif "stop_loss" in key:
                return {"enabled": True}
            return default

        mock_stop_threshold.side_effect = stop_threshold_side_effect

        # asyncio.to_thread mock（SL注文IDを動的に変更）
        call_count = [0]

        async def mock_to_thread_impl(func, *args):
            call_count[0] += 1
            return {"success": True}

        mock_to_thread.side_effect = mock_to_thread_impl

        # BitbankClientモック（SL注文IDを動的に変更）
        sl_order_ids = ["trailing_sl_1", "trailing_sl_2", "trailing_sl_3"]
        call_index = [0]

        def create_sl_side_effect(*args, **kwargs):
            current_id = sl_order_ids[call_index[0]]
            call_index[0] = min(call_index[0] + 1, len(sl_order_ids) - 1)
            return {"id": current_id}

        mock_bitbank_client.create_stop_loss_order.side_effect = create_sl_side_effect

        # サービス注入
        execution_service.bitbank_client = mock_bitbank_client
        execution_service.inject_services(
            order_strategy=order_strategy,
            stop_manager=stop_manager,
            position_tracker=position_tracker,
        )

        # 初期ポジション設定
        entry_price = 14_000_000.0
        position_tracker.add_position(
            order_id="order_123",
            side="buy",
            amount=0.003,
            price=entry_price,
            take_profit=14_350_000.0,
            stop_loss=13_700_000.0,
            strategy_name="test_strategy",
        )
        position_tracker._average_entry_price = entry_price
        position_tracker._total_position_size = 0.003
        position_tracker.set_consolidated_tp_sl_ids(
            tp_order_id="tp_123",
            sl_order_id="sl_initial",
            tp_price=14_350_000.0,
            sl_price=13_700_000.0,
            side="buy",
        )

        # トレーリング更新1回目: 価格+2.5%
        current_price_1 = 14_350_000.0  # +2.5%
        result_1 = await execution_service.monitor_trailing_conditions(current_price_1)

        assert result_1["trailing_activated"] is True
        assert result_1["new_sl_order_id"] == "trailing_sl_1"
        # 新SL計算: 14,350,000 × 0.97 = 13,919,500円
        # しかし、min_profit_lockが適用される: 14,000,000 × 1.005 = 14,070,000円
        new_sl_1 = entry_price * 1.005  # min_profit_lock適用後
        assert abs(result_1["new_sl_price"] - new_sl_1) < 1.0

        # PositionTracker更新確認
        consolidated_ids_1 = position_tracker.get_consolidated_tp_sl_ids()
        assert consolidated_ids_1["sl_order_id"] == "trailing_sl_1"
        assert abs(consolidated_ids_1["sl_price"] - new_sl_1) < 1.0

        # トレーリング更新2回目: 価格さらに上昇 +4.0%
        # 注意: +3.5%だとmin_profit_lock適用で新SL=14,070,000円となり、
        # 1回目のSL(14,070,000円)と同じになるため、min_update_distance(200円)フィルターでスキップされる
        # したがって、+4.0%に変更してmin_update_distanceを超えるようにする
        current_price_2 = 14_560_000.0  # +4.0%
        result_2 = await execution_service.monitor_trailing_conditions(current_price_2)

        assert result_2["trailing_activated"] is True
        assert result_2["new_sl_order_id"] == "trailing_sl_2"
        # 新SL計算: 14,560,000 × 0.97 = 14,123,200円
        # min_profit_lock: 14,000,000 × 1.005 = 14,070,000円
        # 14,123,200 > 14,070,000なのでトレーリング計算適用
        new_sl_2 = current_price_2 * 0.97  # トレーリング計算適用
        assert abs(result_2["new_sl_price"] - new_sl_2) < 1.0

        # PositionTracker更新確認
        consolidated_ids_2 = position_tracker.get_consolidated_tp_sl_ids()
        assert consolidated_ids_2["sl_order_id"] == "trailing_sl_2"
        assert abs(consolidated_ids_2["sl_price"] - new_sl_2) < 1.0

        # トレーリング更新3回目: 価格さらに上昇 +5.0%
        current_price_3 = 14_700_000.0  # +5.0%
        result_3 = await execution_service.monitor_trailing_conditions(current_price_3)

        assert result_3["trailing_activated"] is True
        assert result_3["new_sl_order_id"] == "trailing_sl_3"
        # 新SL計算: 14,700,000 × 0.97 = 14,259,000円
        # min_profit_lock: 14,000,000 × 1.005 = 14,070,000円
        # 14,259,000 > 14,070,000なのでトレーリング計算適用
        new_sl_3 = current_price_3 * 0.97  # トレーリング計算適用
        assert abs(result_3["new_sl_price"] - new_sl_3) < 1.0

        # PositionTracker最終確認
        consolidated_ids_3 = position_tracker.get_consolidated_tp_sl_ids()
        assert consolidated_ids_3["sl_order_id"] == "trailing_sl_3"
        assert abs(consolidated_ids_3["sl_price"] - new_sl_3) < 1.0

        # 検証: SL価格が段階的に引き上げられている
        assert new_sl_1 < new_sl_2 < new_sl_3
        # 最終SL価格（14,259,000円） > 初期エントリー価格（14,000,000円）
        assert new_sl_3 > entry_price
