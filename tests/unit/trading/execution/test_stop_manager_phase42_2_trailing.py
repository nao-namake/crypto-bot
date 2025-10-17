"""
Phase 42.2: トレーリングストップ Unit Tests

Phase 42.2トレーリングストップ機能のテストスイート（8テストケース）

テスト範囲:
- update_trailing_stop_loss(): トレーリングSL更新（8テスト）
  1. トレーリング発動基本ケース
  2. 価格計算正確性（買い/売り）
  3. min_profit_lock適用（買いポジション）
  4. min_profit_lock適用（売りポジション）
  5. 発動閾値未達時のスキップ
  6. 最小更新距離フィルター
  7. 一方向移動制約
  8. トレーリング無効時スキップ
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading.execution.stop_manager import StopManager


@pytest.fixture
def stop_manager():
    """StopManager fixture"""
    return StopManager()


@pytest.fixture
def mock_bitbank_client():
    """BitbankClient mock fixture"""
    client = Mock()
    client.create_stop_loss_order = Mock(return_value={"id": "trailing_sl_123"})
    client.cancel_order = Mock(return_value={"success": True})
    return client


# ========================================
# update_trailing_stop_loss() テスト - 8ケース
# ========================================


class TestUpdateTrailingStopLoss:
    """Phase 42.2 トレーリングストップテスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    @patch("asyncio.to_thread")
    async def test_trailing_stop_activation(
        self, mock_to_thread, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Test 1: トレーリング発動基本ケース（2%含み益で発動）"""

        # トレーリング設定モック
        def threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": True,
                    "activation_profit": 0.02,  # 2%
                    "trailing_percent": 0.03,  # 3%
                    "min_update_distance": 200,
                    "min_profit_lock": 0.005,  # 0.5%
                }
            elif "stop_loss" in key:
                return {"enabled": True}
            return default

        mock_threshold.side_effect = threshold_side_effect

        # asyncio.to_thread()のモック（キャンセル処理）
        async def mock_to_thread_impl(func, *args):
            return {"success": True}

        mock_to_thread.side_effect = mock_to_thread_impl

        # テストデータ
        entry_price = 14_000_000.0  # エントリー価格
        current_price = 14_280_000.0  # 現在価格（+2.0%）
        current_sl_price = 13_700_000.0  # 現在のSL価格

        # トレーリングSL更新実行
        result = await stop_manager.update_trailing_stop_loss(
            current_price=current_price,
            average_entry_price=entry_price,
            current_sl_price=current_sl_price,
            side="buy",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id="tp_123",
            existing_sl_id="sl_456",
        )

        # 検証: トレーリング発動成功
        assert result["trailing_activated"] is True
        assert result["new_sl_order_id"] == "trailing_sl_123"
        # 新SL価格計算: 14,280,000 × 0.97 = 13,851,600円
        # しかし、min_profit_lockが適用される: entry_price × 1.005 = 14,070,000円
        # 13,851,600円 < 14,070,000円なので、min_profit_lock SLが採用される
        expected_sl_price = entry_price * 1.005  # min_profit_lock適用後
        assert abs(result["new_sl_price"] - expected_sl_price) < 1.0  # 誤差1円未満
        assert result["unrealized_pnl_ratio"] == pytest.approx(0.02, abs=0.0001)

        # 検証: SL注文が配置された
        mock_bitbank_client.create_stop_loss_order.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_trailing_stop_update_price_calculation(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Test 2: 価格計算正確性検証（買い/売り両サイド）"""

        def threshold_side_effect(key, default=None):
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

        mock_threshold.side_effect = threshold_side_effect

        # テストケース1: 買いポジション（含み益大きくしてmin_profit_lock影響なし）
        current_price = 14_500_000.0
        entry_price = 13_720_000.0  # +5.69%（含み益大）
        current_sl = 13_400_000.0

        result_buy = await stop_manager.update_trailing_stop_loss(
            current_price=current_price,
            average_entry_price=entry_price,
            current_sl_price=current_sl,
            side="buy",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_buy",
        )

        # 買い: new_sl = current_price × (1 - trailing_percent) = 14,500,000 × 0.97 = 14,065,000円
        # min_profit_lock SL = 13,720,000 × 1.005 = 13,788,600円
        # 14,065,000円 > 13,788,600円なので、min_profit_lockの影響なし
        expected_buy_sl = current_price * 0.97
        assert abs(result_buy["new_sl_price"] - expected_buy_sl) < 1.0

        # テストケース2: 売りポジション（含み益2.0%、min_profit_lock適用）
        mock_bitbank_client.create_stop_loss_order.reset_mock()

        current_price_sell = 13_720_000.0
        entry_price_sell = 14_000_000.0  # -2.0%
        current_sl_sell = 14_300_000.0

        result_sell = await stop_manager.update_trailing_stop_loss(
            current_price=current_price_sell,
            average_entry_price=entry_price_sell,
            current_sl_price=current_sl_sell,
            side="sell",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_sell",
        )

        # 売り: new_sl = current_price × (1 + trailing_percent) = 13,720,000 × 1.03 = 14,131,600円
        # min_profit_lock SL: 14,000,000 × 0.995 = 13,930,000円
        # 14,131,600円 > 13,930,000円なので、min_profit_lock SLが採用される
        expected_sell_sl = entry_price_sell * 0.995  # min_profit_lock適用後
        assert abs(result_sell["new_sl_price"] - expected_sell_sl) < 1.0

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_min_profit_lock_buy(self, mock_threshold, stop_manager, mock_bitbank_client):
        """Test 3: 買いポジション min_profit_lock適用（entry+0.5%を下回らない）"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": True,
                    "activation_profit": 0.02,
                    "trailing_percent": 0.03,
                    "min_update_distance": 200,
                    "min_profit_lock": 0.005,  # 0.5%
                }
            elif "stop_loss" in key:
                return {"enabled": True}
            return default

        mock_threshold.side_effect = threshold_side_effect

        # エッジケース: 含み益2.0%だが、trailing_percent=3%でSLが下がりすぎる場合
        entry_price = 14_000_000.0
        current_price = 14_280_000.0  # +2.0%
        current_sl = 13_700_000.0

        # 計算されるSL: 14,280,000 × 0.97 = 13,851,600円
        # min_profit_lock SL: 14,000,000 × 1.005 = 14,070,000円
        # → min_profit_lockの方が高いので、14,070,000円が採用される

        result = await stop_manager.update_trailing_stop_loss(
            current_price=current_price,
            average_entry_price=entry_price,
            current_sl_price=current_sl,
            side="buy",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_buy",
        )

        # 検証: min_profit_lockが適用されている
        min_sl_price = entry_price * 1.005
        # Phase 42.2実装では計算SL（13,851,600円）とmin_profit_lock SL（14,070,000円）を比較
        # 計算SL < min_profit_lock SLなので、min_profit_lock SLが採用される
        # しかし、min_profit_lock SL（14,070,000円） > current_sl（13,700,000円）なので更新される
        assert result["trailing_activated"] is True
        assert result["new_sl_price"] == pytest.approx(min_sl_price, abs=1.0)

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_min_profit_lock_sell(self, mock_threshold, stop_manager, mock_bitbank_client):
        """Test 4: 売りポジション min_profit_lock適用（entry-0.5%を上回らない）"""

        def threshold_side_effect(key, default=None):
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

        mock_threshold.side_effect = threshold_side_effect

        # エッジケース: 売りポジションで含み益2.0%、trailing_percent=3%でSLが上がりすぎる場合
        entry_price = 14_000_000.0
        current_price = 13_720_000.0  # -2.0%
        current_sl = 14_300_000.0

        # 計算されるSL: 13,720,000 × 1.03 = 14,131,600円
        # min_profit_lock SL: 14,000,000 × 0.995 = 13,930,000円
        # → min_profit_lockの方が低いので、13,930,000円が採用される

        result = await stop_manager.update_trailing_stop_loss(
            current_price=current_price,
            average_entry_price=entry_price,
            current_sl_price=current_sl,
            side="sell",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_sell",
        )

        # 検証: min_profit_lockが適用されている
        max_sl_price = entry_price * 0.995
        # 計算SL（14,131,600円） > min_profit_lock SL（13,930,000円）なので、min_profit_lock SLが採用
        # min_profit_lock SL（13,930,000円） < current_sl（14,300,000円）なので更新される
        assert result["trailing_activated"] is True
        assert result["new_sl_price"] == pytest.approx(max_sl_price, abs=1.0)

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_trailing_stop_no_activation_below_threshold(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Test 5: 発動閾値未達時のスキップ（含み益 < 2%）"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": True,
                    "activation_profit": 0.02,  # 2%
                    "trailing_percent": 0.03,
                    "min_update_distance": 200,
                    "min_profit_lock": 0.005,
                }
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 含み益1.0%（< 2%）
        entry_price = 14_000_000.0
        current_price = 14_140_000.0  # +1.0%
        current_sl = 13_700_000.0

        result = await stop_manager.update_trailing_stop_loss(
            current_price=current_price,
            average_entry_price=entry_price,
            current_sl_price=current_sl,
            side="buy",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_123",
        )

        # 検証: トレーリング未発動
        assert result["trailing_activated"] is False
        assert result["new_sl_price"] == current_sl  # SL価格変更なし
        assert result["new_sl_order_id"] == "sl_123"  # 既存SL ID維持
        assert result["unrealized_pnl_ratio"] == pytest.approx(0.01, abs=0.0001)

        # 検証: SL注文は配置されない
        mock_bitbank_client.create_stop_loss_order.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_min_update_distance_filtering(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Test 6: 最小更新距離フィルター（200円未満は更新しない）"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": True,
                    "activation_profit": 0.02,
                    "trailing_percent": 0.03,
                    "min_update_distance": 200,  # 200円
                    "min_profit_lock": 0.005,
                }
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 含み益を大きくして、min_profit_lockの影響を回避
        entry_price = 14_000_000.0
        current_price = 14_500_000.0  # +3.57%（含み益大）
        # 新SL計算: 14,500,000 × 0.97 = 14,065,000円
        # min_profit_lock SL: 14,000,000 × 1.005 = 14,070,000円
        # 14,065,000円 < 14,070,000円なので、min_profit_lockが適用される
        # しかし、テストの目的は「最小更新距離」なので、現在SLを14,069,900円に設定（差100円）
        current_sl = 14_069_900.0  # min_profit_lock SL (14,070,000円) から100円下

        result = await stop_manager.update_trailing_stop_loss(
            current_price=current_price,
            average_entry_price=entry_price,
            current_sl_price=current_sl,
            side="buy",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_123",
        )

        # 検証: 最小更新距離未達でスキップ
        assert result["trailing_activated"] is False
        assert result["new_sl_price"] == current_sl  # SL価格変更なし

        # 検証: SL注文は配置されない
        mock_bitbank_client.create_stop_loss_order.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_trailing_stop_one_way_movement(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Test 7: 一方向移動制約（買い: 上昇のみ、売り: 下降のみ）"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": True,
                    "activation_profit": 0.02,
                    "trailing_percent": 0.03,
                    "min_update_distance": 200,
                    "min_profit_lock": 0.005,
                }
            return default

        mock_threshold.side_effect = threshold_side_effect

        # テストケース1: 買いポジション - 新SL価格 <= 現在SL価格（不利な方向）
        entry_price = 14_000_000.0
        current_price = 14_500_000.0  # +3.57%（含み益大）
        # 新SL計算: 14,500,000 × 0.97 = 14,065,000円
        # current_slを14,100,000円に設定（新SL < current_sl）
        current_sl_buy = 14_100_000.0

        result_buy = await stop_manager.update_trailing_stop_loss(
            current_price=current_price,
            average_entry_price=entry_price,
            current_sl_price=current_sl_buy,
            side="buy",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_buy",
        )

        # 検証: 新SL <= 現在SLなので更新しない
        assert result_buy["trailing_activated"] is False
        assert result_buy["new_sl_price"] == current_sl_buy

        # テストケース2: 売りポジション - 新SL価格 >= 現在SL価格（不利な方向）
        mock_bitbank_client.create_stop_loss_order.reset_mock()

        entry_price_sell = 14_000_000.0
        current_price_sell = 13_500_000.0  # -3.57%（含み益大）
        # 新SL計算: 13,500,000 × 1.03 = 13,905,000円
        # current_slを13,850,000円に設定（新SL > current_sl）
        current_sl_sell = 13_850_000.0

        result_sell = await stop_manager.update_trailing_stop_loss(
            current_price=current_price_sell,
            average_entry_price=entry_price_sell,
            current_sl_price=current_sl_sell,
            side="sell",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_sell",
        )

        # 検証: 新SL >= 現在SLなので更新しない
        assert result_sell["trailing_activated"] is False
        assert result_sell["new_sl_price"] == current_sl_sell

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_trailing_disabled_skip(self, mock_threshold, stop_manager, mock_bitbank_client):
        """Test 8: トレーリング無効時スキップ"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.stop_loss.trailing":
                return {
                    "enabled": False,  # トレーリング無効
                }
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 含み益2.0%でもトレーリング無効
        entry_price = 14_000_000.0
        current_price = 14_280_000.0  # +2.0%
        current_sl = 13_700_000.0

        result = await stop_manager.update_trailing_stop_loss(
            current_price=current_price,
            average_entry_price=entry_price,
            current_sl_price=current_sl,
            side="buy",
            symbol="btc_jpy",
            total_amount=0.003,
            bitbank_client=mock_bitbank_client,
            existing_tp_id=None,
            existing_sl_id="sl_123",
        )

        # 検証: トレーリング未発動
        assert result["trailing_activated"] is False
        assert result["new_sl_price"] == current_sl
        assert result["new_sl_order_id"] == "sl_123"

        # 検証: SL注文は配置されない
        mock_bitbank_client.create_stop_loss_order.assert_not_called()
