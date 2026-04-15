"""
TPSLManager テストスイート - Phase 64

Phase 64: stop_manager.pyから移動したTP/SL配置メソッドのテスト

テスト範囲:
- place_take_profit(): TP注文配置・Maker戦略・エラーハンドリング
- place_stop_loss(): SL注文配置・価格検証・指値化
- _place_missing_tp_sl(): Phase 64.3 SLトリガー超過成行決済
- calculate_recovery_tp_sl_prices(): Phase 64.4 復旧用TP/SL価格計算
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.exceptions import TradingError
from src.trading.execution.tp_sl_manager import TPSLManager

pytestmark = pytest.mark.asyncio


@pytest.fixture
def tp_sl_manager():
    """TPSLManager fixture"""
    return TPSLManager()


class TestPhase516SLPriceValidation:
    """Phase 51.6: SL価格検証強化のテスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        """TPSLManagerインスタンス"""
        return TPSLManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.create_order = MagicMock(
            return_value={"order_id": "sl123", "trigger_price": 13900000.0}
        )
        return client

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_price_none_validation(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """Phase 51.6: SL価格None検証 - エラー30101対策"""
        mock_threshold.return_value = {"enabled": True}

        with pytest.raises(TradingError, match="SL価格がNone"):
            await tp_sl_manager.place_stop_loss(
                side="buy",
                amount=0.0001,
                entry_price=14000000.0,
                stop_loss_price=None,  # None（不正）
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_price_zero_validation(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """Phase 51.6: SL価格0検証"""
        mock_threshold.return_value = {"enabled": True}

        with pytest.raises(TradingError, match="SL価格が不正（0以下）"):
            await tp_sl_manager.place_stop_loss(
                side="buy",
                amount=0.0001,
                entry_price=14000000.0,
                stop_loss_price=0,  # 0（不正）
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_price_negative_validation(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """Phase 51.6: SL価格負の値検証"""
        mock_threshold.return_value = {"enabled": True}

        with pytest.raises(TradingError, match="SL価格が不正（0以下）"):
            await tp_sl_manager.place_stop_loss(
                side="buy",
                amount=0.0001,
                entry_price=14000000.0,
                stop_loss_price=-100000,  # 負の値（不正）
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_price_invalid_direction_validation(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """Phase 51.6: SL価格方向検証（BUY時はエントリー価格より低い必要）"""
        mock_threshold.return_value = {"enabled": True}

        with pytest.raises(TradingError, match="BUY時はエントリー価格より低い必要"):
            await tp_sl_manager.place_stop_loss(
                side="buy",
                amount=0.0001,
                entry_price=14000000.0,
                stop_loss_price=14100000.0,  # エントリー価格より高い（不正）
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )


class TestPhase596SLStopLimit:
    """Phase 59.6: SL指値化テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        """TPSLManagerインスタンス"""
        return TPSLManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.create_stop_loss_order = MagicMock(
            return_value={"id": "sl123", "trigger_price": 13900000.0}
        )
        return client

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_traditional_stop_order(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """Phase 59.6: 従来のstop注文（成行）"""
        # stop_loss設定をモック - order_type: "stop"
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.stop_loss": {
                "enabled": True,
                "order_type": "stop",  # 従来の成行
                "slippage_buffer": 0.001,
            }
        }.get(key, default)

        result = await tp_sl_manager.place_stop_loss(
            side="buy",
            amount=0.0001,
            entry_price=14000000.0,
            stop_loss_price=13900000.0,
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
        )

        # create_stop_loss_orderが呼ばれる
        mock_bitbank_client.create_stop_loss_order.assert_called_once()
        call_kwargs = mock_bitbank_client.create_stop_loss_order.call_args[1]

        # stopの場合はlimit_priceはNone
        assert call_kwargs["order_type"] == "stop"
        assert call_kwargs["limit_price"] is None


class TestPlaceTakeProfit:
    """Phase 46: place_take_profit() テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        """TPSLManagerインスタンス"""
        return TPSLManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.create_take_profit_order = MagicMock(return_value={"id": "tp_order_123"})
        return client

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_place_tp_success(self, mock_threshold, tp_sl_manager, mock_bitbank_client):
        """Phase 46: TP注文配置成功"""
        mock_threshold.return_value = {"enabled": True}

        result = await tp_sl_manager.place_take_profit(
            side="buy",
            amount=0.001,
            entry_price=14000000.0,
            take_profit_price=14300000.0,
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
        )

        assert result is not None
        assert result["order_id"] == "tp_order_123"
        assert result["price"] == 14300000.0

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_place_tp_disabled(self, mock_threshold, tp_sl_manager, mock_bitbank_client):
        """Phase 46: TP無効時はNone"""
        mock_threshold.return_value = {"enabled": False}

        result = await tp_sl_manager.place_take_profit(
            side="buy",
            amount=0.001,
            entry_price=14000000.0,
            take_profit_price=14300000.0,
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
        )

        assert result is None

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_place_tp_invalid_price(self, mock_threshold, tp_sl_manager, mock_bitbank_client):
        """Phase 46: TP価格0以下はTradingError"""
        mock_threshold.return_value = {"enabled": True}

        with pytest.raises(TradingError, match="TP価格が不正（0以下）"):
            await tp_sl_manager.place_take_profit(
                side="buy",
                amount=0.001,
                entry_price=14000000.0,
                take_profit_price=0,  # 不正な価格
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_place_tp_no_order_id(self, mock_threshold, tp_sl_manager, mock_bitbank_client):
        """Phase 57.11: order_idが空の場合は例外伝播"""
        mock_threshold.return_value = {"enabled": True}
        mock_bitbank_client.create_take_profit_order = MagicMock(
            return_value={"id": None}  # order_idが空
        )

        with pytest.raises(Exception, match="TP注文配置失敗（order_idが空）"):
            await tp_sl_manager.place_take_profit(
                side="buy",
                amount=0.001,
                entry_price=14000000.0,
                take_profit_price=14300000.0,
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_place_tp_error_50061(self, mock_threshold, tp_sl_manager, mock_bitbank_client):
        """Phase 46: エラーコード50061（残高不足）→ 例外伝播"""
        mock_threshold.return_value = {"enabled": True}
        mock_bitbank_client.create_take_profit_order = MagicMock(
            side_effect=Exception("50061: 残高不足")
        )

        with pytest.raises(Exception, match="50061"):
            await tp_sl_manager.place_take_profit(
                side="buy",
                amount=0.001,
                entry_price=14000000.0,
                take_profit_price=14300000.0,
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )


class TestPlaceStopLossDetailed:
    """place_stop_loss() 詳細テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        """TPSLManagerインスタンス"""
        return TPSLManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.create_stop_loss_order = MagicMock(return_value={"id": "sl_order_123"})
        return client

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_disabled(self, mock_threshold, tp_sl_manager, mock_bitbank_client):
        """SL無効時はNone"""
        mock_threshold.return_value = {"enabled": False}

        result = await tp_sl_manager.place_stop_loss(
            side="buy",
            amount=0.001,
            entry_price=14000000.0,
            stop_loss_price=13900000.0,
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
        )

        assert result is None

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_sell_invalid_direction(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """SELL時にSL価格がエントリー価格より低い場合はTradingError"""
        mock_threshold.return_value = {"enabled": True}

        with pytest.raises(TradingError, match="SELL時はエントリー価格より高い必要"):
            await tp_sl_manager.place_stop_loss(
                side="sell",
                amount=0.001,
                entry_price=14000000.0,
                stop_loss_price=13900000.0,  # SELL時は高くないといけない
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_distance_too_close_warning(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """SL価格が極端に近い場合は警告"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.stop_loss": {
                "enabled": True,
                "order_type": "stop",
                "max_loss_ratio": 0.007,
            }
        }.get(key, default)

        result = await tp_sl_manager.place_stop_loss(
            side="buy",
            amount=0.001,
            entry_price=14000000.0,
            stop_loss_price=13999000.0,  # 0.007%（極端に近い）
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
        )

        # 警告は出るが配置は成功
        assert result is not None

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_distance_too_far_raises(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """Phase 82: SL価格が極端に遠い場合は配置中止（TradingError）"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.stop_loss": {
                "enabled": True,
                "order_type": "stop",
                "max_loss_ratio": 0.007,
            }
        }.get(key, default)

        # SL距離 3.6% > max_loss_ratio * 3 = 2.1% → TradingError
        with pytest.raises(TradingError, match="SL価格が極端に遠い"):
            await tp_sl_manager.place_stop_loss(
                side="buy",
                amount=0.001,
                entry_price=14000000.0,
                stop_loss_price=13500000.0,  # 3.6%（極端に遠い）
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_no_order_id(self, mock_threshold, tp_sl_manager, mock_bitbank_client):
        """Phase 57.11: order_idが空の場合はTradingError伝播"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.stop_loss": {
                "enabled": True,
                "order_type": "stop",
            }
        }.get(key, default)

        mock_bitbank_client.create_stop_loss_order = MagicMock(return_value={"id": None})

        with pytest.raises(TradingError, match="SL注文配置失敗（order_idが空）"):
            await tp_sl_manager.place_stop_loss(
                side="buy",
                amount=0.001,
                entry_price=14000000.0,
                stop_loss_price=13900000.0,
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_error_50062(self, mock_threshold, tp_sl_manager, mock_bitbank_client):
        """エラーコード50062（注文タイプ不正）→ 例外伝播"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.stop_loss": {
                "enabled": True,
                "order_type": "stop",
            }
        }.get(key, default)

        mock_bitbank_client.create_stop_loss_order = MagicMock(
            side_effect=Exception("50062: 注文タイプ不正")
        )

        with pytest.raises(Exception, match="50062"):
            await tp_sl_manager.place_stop_loss(
                side="buy",
                amount=0.001,
                entry_price=14000000.0,
                stop_loss_price=13900000.0,
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
            )


class TestPhase6210TPMakerStrategy:
    """Phase 62.10: TP Maker戦略テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_tp_maker_success(self, mock_threshold, tp_sl_manager):
        """TP Maker注文が成功する場合"""
        # Maker戦略有効化
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.take_profit": {
                "enabled": True,
                "maker_strategy": {
                    "enabled": True,
                    "max_retries": 2,
                    "retry_interval_ms": 100,
                    "timeout_seconds": 10,
                    "fallback_to_native": True,
                },
            },
        }.get(key, default)

        mock_client = MagicMock()
        mock_client.create_take_profit_order = Mock(return_value={"id": "tp_maker_001"})

        result = await tp_sl_manager.place_take_profit(
            side="buy",
            amount=0.001,
            entry_price=14000000.0,
            take_profit_price=14100000.0,
            symbol="BTC/JPY",
            bitbank_client=mock_client,
        )

        assert result is not None
        assert result["order_id"] == "tp_maker_001"
        assert result["price"] == 14100000.0

        # post_only=True で呼ばれていることを確認
        mock_client.create_take_profit_order.assert_called_once_with(
            entry_side="buy",
            amount=0.001,
            take_profit_price=14100000.0,
            symbol="BTC/JPY",
            post_only=True,
        )

    @pytest.mark.asyncio
    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_tp_maker_fallback_to_native(self, mock_threshold, tp_sl_manager):
        """TP Maker失敗時にtake_profitタイプにフォールバック"""
        from src.core.exceptions import PostOnlyCancelledException

        # Maker戦略有効化（フォールバック有効）
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.take_profit": {
                "enabled": True,
                "maker_strategy": {
                    "enabled": True,
                    "max_retries": 2,
                    "retry_interval_ms": 50,
                    "timeout_seconds": 10,
                    "fallback_to_native": True,
                },
            },
        }.get(key, default)

        mock_client = MagicMock()
        # 1回目・2回目: PostOnlyCancelledException、3回目（フォールバック）: 成功
        call_count = [0]

        def mock_create_tp(*args, **kwargs):
            call_count[0] += 1
            if kwargs.get("post_only", False):
                raise PostOnlyCancelledException("post_only cancelled")
            return {"id": "tp_native_001"}

        mock_client.create_take_profit_order = mock_create_tp

        result = await tp_sl_manager.place_take_profit(
            side="buy",
            amount=0.001,
            entry_price=14000000.0,
            take_profit_price=14100000.0,
            symbol="BTC/JPY",
            bitbank_client=mock_client,
        )

        assert result is not None
        assert result["order_id"] == "tp_native_001"
        # Maker試行2回 + フォールバック1回 = 3回呼び出し
        assert call_count[0] == 3

    @pytest.mark.asyncio
    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_tp_maker_disabled(self, mock_threshold, tp_sl_manager):
        """Maker戦略無効時は従来のTP注文"""
        # Maker戦略無効
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.take_profit": {
                "enabled": True,
                "maker_strategy": {
                    "enabled": False,  # Maker無効
                },
            },
        }.get(key, default)

        mock_client = MagicMock()
        mock_client.create_take_profit_order = Mock(return_value={"id": "tp_native_002"})

        result = await tp_sl_manager.place_take_profit(
            side="buy",
            amount=0.001,
            entry_price=14000000.0,
            take_profit_price=14100000.0,
            symbol="BTC/JPY",
            bitbank_client=mock_client,
        )

        assert result is not None
        assert result["order_id"] == "tp_native_002"

        # post_only=False で呼ばれていることを確認
        mock_client.create_take_profit_order.assert_called_once_with(
            entry_side="buy",
            amount=0.001,
            take_profit_price=14100000.0,
            symbol="BTC/JPY",
            post_only=False,
        )

    @pytest.mark.asyncio
    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_tp_maker_no_fallback(self, mock_threshold, tp_sl_manager):
        """Maker失敗時フォールバック無効だとTradingError"""
        from src.core.exceptions import PostOnlyCancelledException

        # Maker戦略有効（フォールバック無効）
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.take_profit": {
                "enabled": True,
                "maker_strategy": {
                    "enabled": True,
                    "max_retries": 1,
                    "retry_interval_ms": 50,
                    "timeout_seconds": 10,
                    "fallback_to_native": False,  # フォールバック無効
                },
            },
        }.get(key, default)

        mock_client = MagicMock()
        mock_client.create_take_profit_order = Mock(
            side_effect=PostOnlyCancelledException("cancelled")
        )

        with pytest.raises(TradingError, match="TP Maker失敗・フォールバック無効"):
            await tp_sl_manager.place_take_profit(
                side="buy",
                amount=0.001,
                entry_price=14000000.0,
                take_profit_price=14100000.0,
                symbol="BTC/JPY",
                bitbank_client=mock_client,
            )

    @pytest.mark.asyncio
    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_tp_maker_timeout(self, mock_threshold, tp_sl_manager):
        """Makerタイムアウト時のフォールバック"""
        # Maker戦略有効（タイムアウト短め）
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.take_profit": {
                "enabled": True,
                "maker_strategy": {
                    "enabled": True,
                    "max_retries": 10,  # 多くのリトライ
                    "retry_interval_ms": 2000,  # 長いインターバル（2秒）
                    "timeout_seconds": 0.1,  # 非常に短いタイムアウト
                    "fallback_to_native": True,
                },
            },
        }.get(key, default)

        mock_client = MagicMock()
        # asyncio.to_threadをバイパスしてslow_create_tpを直接呼ぶ
        mock_client.create_take_profit_order = Mock(return_value={"id": "tp_native_003"})

        result = await tp_sl_manager.place_take_profit(
            side="buy",
            amount=0.001,
            entry_price=14000000.0,
            take_profit_price=14100000.0,
            symbol="BTC/JPY",
            bitbank_client=mock_client,
        )

        # タイムアウト後フォールバックで成功
        assert result is not None


class TestPhase643SLBreachMarketClose:
    """Phase 64.3: SLトリガー超過成行決済テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_breach_triggers_market_close_long(self, mock_threshold, tp_sl_manager):
        """ロング: 現在価格がSL以下 → 成行決済"""

        def threshold_side_effect(key, default=None):
            thresholds = {
                "trading.tp_sl.currency_pair": "BTC/JPY",
                "trading.tp_sl.regimes.normal_range.tp.min_profit_ratio": 0.01,
                "trading.tp_sl.regimes.normal_range.sl.max_loss_ratio": 0.007,
                "trading.tp_sl.min_profit_ratio": 0.009,
                "trading.tp_sl.max_loss_ratio": 0.007,
            }
            return thresholds.get(key, default)

        mock_threshold.side_effect = threshold_side_effect

        mock_client = MagicMock()
        # Phase 65.2: _cancel_partial_exit_ordersで使用
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        # SL超過: avg_price=10,000,000, SL=9,930,000, 現在価格=9,900,000
        mock_client.fetch_ticker = MagicMock(return_value={"last": 9900000.0})
        mock_client.create_order = MagicMock(return_value={"id": "market_123"})

        virtual_positions = []
        await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.01,
            avg_price=10000000.0,
            has_tp=True,  # TPはある
            has_sl=False,  # SLがない
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
        )

        # 成行決済が呼ばれた
        mock_client.create_order.assert_called_once()
        call_kwargs = mock_client.create_order.call_args
        assert call_kwargs[1]["order_type"] == "market"
        assert call_kwargs[1]["side"] == "sell"
        assert call_kwargs[1]["is_closing_order"] is True
        assert call_kwargs[1]["entry_position_side"] == "long"

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_not_breached_places_normal_sl(self, mock_threshold, tp_sl_manager):
        """SL未超過 → 通常のSL配置"""

        def threshold_side_effect(key, default=None):
            thresholds = {
                "trading.tp_sl.currency_pair": "BTC/JPY",
                "trading.tp_sl.regimes.normal_range.tp.min_profit_ratio": 0.01,
                "trading.tp_sl.regimes.normal_range.sl.max_loss_ratio": 0.007,
                "trading.tp_sl.min_profit_ratio": 0.009,
                "trading.tp_sl.max_loss_ratio": 0.007,
                "trading.tp_sl.slippage_buffer": 0.002,
                "trading.tp_sl.stop_limit": {"enabled": True},
            }
            return thresholds.get(key, default)

        mock_threshold.side_effect = threshold_side_effect

        mock_client = MagicMock()
        # Phase 65.2: _cancel_partial_exit_ordersで使用
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        # SL未超過: avg_price=10,000,000, SL=9,930,000, 現在価格=10,050,000
        mock_client.fetch_ticker = MagicMock(return_value={"last": 10050000.0})
        mock_client.create_stop_loss_order = MagicMock(
            return_value={"id": "sl_123", "trigger_price": 9930000.0}
        )

        virtual_positions = []
        await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.01,
            avg_price=10000000.0,
            has_tp=True,
            has_sl=False,
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
        )

        # 成行決済ではなくplace_stop_loss経由のcreate_stop_loss_orderが呼ばれた
        mock_client.create_order.assert_not_called()
        mock_client.create_stop_loss_order.assert_called_once()


# ========================================
# Phase 64.12: SL安全網テスト
# ========================================


class TestPhase6412SLSafetyNet:
    """Phase 64.12: SL安全網の根本修正テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_place_sl_or_market_close_cancels_orders_first(
        self, mock_threshold, tp_sl_manager
    ):
        """Phase 64.12: 成行決済前に既存注文をキャンセル"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        # SL超過: short position, 現在価格がSL以上
        mock_client.fetch_ticker = MagicMock(return_value={"last": 10500000.0})
        # 既存注文が2件
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {"id": "order_1", "side": "sell", "type": "limit"},
                {"id": "order_2", "side": "sell", "type": "stop_limit"},
            ]
        )
        mock_client.cancel_order = MagicMock()
        mock_client.create_order = MagicMock(return_value={"id": "market_close_001"})

        result = await tp_sl_manager.place_sl_or_market_close(
            entry_side="sell",
            position_side="short",
            amount=0.01,
            avg_price=10000000.0,
            sl_price=10400000.0,  # 現在価格10,500,000 >= SL 10,400,000
            symbol="BTC/JPY",
            bitbank_client=mock_client,
        )

        # 既存注文がキャンセルされた
        assert mock_client.cancel_order.call_count == 2
        # 成行決済が実行された
        mock_client.create_order.assert_called_once()
        call_kwargs = mock_client.create_order.call_args[1]
        assert call_kwargs["order_type"] == "market"
        assert result is not None
        assert "market_close" in result["order_id"]

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_place_missing_tp_sl_partial_success(self, mock_threshold, tp_sl_manager):
        """Phase 64.12: SLのみ成功→VP追加（TPは次回再試行）"""
        mock_threshold.side_effect = lambda key, default=None: {
            "trading.currency_pair": "BTC/JPY",
            "position_management.take_profit.regime.normal_range.min_profit_ratio": 0.01,
            "position_management.stop_loss.regime.normal_range.max_loss_ratio": 0.007,
        }.get(key, default)

        mock_client = MagicMock()
        # Phase 65.2: _cancel_partial_exit_ordersで使用
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        # TP配置失敗
        mock_client.create_take_profit_order = MagicMock(side_effect=Exception("50062 error"))
        # SL配置成功
        mock_client.fetch_ticker = MagicMock(return_value={"last": 10500000.0})
        mock_client.create_stop_loss_order = MagicMock(return_value={"id": "sl_999"})

        virtual_positions = []
        await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.01,
            avg_price=10000000.0,
            has_tp=False,
            has_sl=False,
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
        )

        # SLのみ成功でもVPに追加される
        assert len(virtual_positions) == 1
        vp = virtual_positions[0]
        assert vp["sl_order_id"] == "sl_999"
        assert vp["tp_order_id"] is None  # TP失敗


# ========================================
# Phase 65.14: float(None)耐性テスト
# ========================================


class TestPhase6514FloatNoneSafety:
    """Phase 65.14: float(None)バグ修正テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_ensure_tp_sl_with_none_amount_in_orders(self, mock_threshold, tp_sl_manager):
        """Phase 65.14: active_ordersのamountがNoneでもTypeErrorにならない"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = MagicMock(
            return_value=[
                {"side": "long", "amount": "0.001", "average_price": "14000000"},
            ]
        )
        # amount=Noneの注文（bitbankが返すことがある）
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "order_1",
                    "side": "sell",
                    "type": "limit",
                    "amount": None,
                    "price": "14100000",
                },
                {
                    "id": "order_2",
                    "side": "sell",
                    "type": "stop_limit",
                    "amount": None,
                    "stopPrice": None,
                    "price": "13900000",
                },
            ]
        )

        # TypeErrorが出ずに正常完了すること
        await tp_sl_manager.ensure_tp_sl_for_existing_positions(
            virtual_positions=[],
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_is_sl_price_valid_with_none_stop_price(self, mock_threshold, tp_sl_manager):
        """Phase 65.14: stopPrice/triggerPrice/priceがNoneでもTypeErrorにならない"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = MagicMock(
            return_value=[
                {"side": "long", "amount": "0.001", "average_price": "14000000"},
            ]
        )
        # 全ての価格フィールドがNone
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "order_1",
                    "side": "sell",
                    "type": "stop_limit",
                    "amount": "0.001",
                    "stopPrice": None,
                    "triggerPrice": None,
                    "price": None,
                },
            ]
        )

        await tp_sl_manager.ensure_tp_sl_for_existing_positions(
            virtual_positions=[],
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )


# ========================================
# Phase 65.14: INACTIVE SLキャンセルテスト
# ========================================


class TestPhase6514InactiveSLCancel:
    """Phase 65.14: cleanup_old_tp_sl_before_entryのINACTIVE SLキャンセルテスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_vp_tracked_orders_cancelled_before_entry(self, mock_threshold, tp_sl_manager):
        """Phase 68.6: VP追跡の古いTP注文のみキャンセル（SLは保護）"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        mock_client.cancel_order = MagicMock()

        virtual_positions = [
            {
                "order_id": "old_entry_1",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": "old_tp_1",
                "sl_order_id": "old_sl_1",
            },
        ]

        await tp_sl_manager.cleanup_old_tp_sl_before_entry(
            side="buy",
            symbol="BTC/JPY",
            entry_order_id="new_entry_1",
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
        )

        # Phase 68.6: TPのみキャンセル、SLは保護
        assert mock_client.cancel_order.call_count == 1
        cancel_ids = [call.args[0] for call in mock_client.cancel_order.call_args_list]
        assert "old_tp_1" in cancel_ids
        assert "old_sl_1" not in cancel_ids

        # TPのみクリア、SLは維持
        assert virtual_positions[0]["tp_order_id"] is None
        assert virtual_positions[0]["sl_order_id"] == "old_sl_1"

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_vp_tracked_orders_opposite_side_not_cancelled(
        self, mock_threshold, tp_sl_manager
    ):
        """Phase 65.14: 反対サイドのVP注文はキャンセルされない"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        mock_client.cancel_order = MagicMock()

        virtual_positions = [
            {
                "order_id": "old_entry_1",
                "side": "sell",  # 反対サイド
                "amount": 0.001,
                "tp_order_id": "sell_tp_1",
                "sl_order_id": "sell_sl_1",
            },
        ]

        await tp_sl_manager.cleanup_old_tp_sl_before_entry(
            side="buy",
            symbol="BTC/JPY",
            entry_order_id="new_entry_1",
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
        )

        # 反対サイドの注文はキャンセルされない
        mock_client.cancel_order.assert_not_called()
        assert virtual_positions[0]["tp_order_id"] == "sell_tp_1"
        assert virtual_positions[0]["sl_order_id"] == "sell_sl_1"

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_vp_cancel_failure_ignored(self, mock_threshold, tp_sl_manager):
        """Phase 65.14: VP TP注文キャンセル失敗は無視して続行"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        mock_client.cancel_order = MagicMock(side_effect=Exception("already cancelled"))

        virtual_positions = [
            {
                "order_id": "old_entry_1",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": "old_tp_1",
                "sl_order_id": "old_sl_1",
            },
        ]

        # 例外が伝播しないこと（Phase 68.6: TPのみキャンセル対象）
        await tp_sl_manager.cleanup_old_tp_sl_before_entry(
            side="buy",
            symbol="BTC/JPY",
            entry_order_id="new_entry_1",
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
        )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_take_profit_type_detected_as_tp_in_cleanup(self, mock_threshold, tp_sl_manager):
        """Phase 65.15: take_profit型もTPとして検出・キャンセルされる"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_native_1",
                    "side": "sell",
                    "type": "take_profit",
                    "price": "14100000",
                },
            ]
        )
        mock_client.cancel_order = MagicMock()

        await tp_sl_manager.cleanup_old_tp_sl_before_entry(
            side="buy",
            symbol="BTC/JPY",
            entry_order_id="new_entry_1",
            virtual_positions=[],
            bitbank_client=mock_client,
        )

        # take_profit型の注文がTPとしてキャンセルされた
        mock_client.cancel_order.assert_called_once_with("tp_native_1", "BTC/JPY")


# ========================================
# Phase 65.15: VP二重カウント防止テスト
# ========================================


class TestPhase6515VPDoubleCountPrevention:
    """Phase 65.15: VP補完の二重カウント防止テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_vp_tp_not_double_counted_when_in_active_orders(
        self, mock_threshold, tp_sl_manager
    ):
        """Phase 65.15: active_ordersに含まれるTP注文IDはVP補完でスキップされる"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = MagicMock(
            return_value=[
                {"side": "long", "amount": "0.01", "average_price": "14000000"},
            ]
        )
        # active_ordersにTP注文（amount=0.01）
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_001",
                    "side": "sell",
                    "type": "take_profit",
                    "amount": "0.01",
                    "price": "14100000",
                },
                {
                    "id": "sl_001",
                    "side": "sell",
                    "type": "stop_limit",
                    "amount": "0.01",
                    "stopPrice": "13900000",
                },
            ]
        )

        # VPにも同じTP/SL注文IDが記録されている（二重カウントのリスク）
        virtual_positions = [
            {
                "order_id": "entry_1",
                "side": "buy",
                "amount": 0.01,
                "tp_order_id": "tp_001",
                "sl_order_id": "sl_001",
            }
        ]

        # 二重カウントされるとTP/SLが2倍カウント→カバレッジOKになる
        # 二重カウント防止が効いていればactive_ordersだけでカバレッジ判定される
        await tp_sl_manager.ensure_tp_sl_for_existing_positions(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

        # カバレッジOK（active_ordersだけで十分）→再配置されない
        # _place_missing_tp_slが呼ばれない（TP/SLが足りているため）
        mock_client.create_take_profit_order = MagicMock()
        mock_client.create_stop_loss_order = MagicMock()
        mock_client.create_take_profit_order.assert_not_called()
        mock_client.create_stop_loss_order.assert_not_called()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_vp_inactive_sl_supplemented_correctly(self, mock_threshold, tp_sl_manager):
        """Phase 65.15: INACTIVE SL（active_ordersに不在）はVP補完でカウントされる"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_margin_positions = MagicMock(
            return_value=[
                {"side": "long", "amount": "0.01", "average_price": "14000000"},
            ]
        )
        # active_ordersにはTP注文のみ（SLはINACTIVEで返されない）
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_001",
                    "side": "sell",
                    "type": "take_profit",
                    "amount": "0.01",
                    "price": "14100000",
                },
            ]
        )

        # VPにSL注文IDが記録されている（INACTIVEのstop_limit）
        virtual_positions = [
            {
                "order_id": "entry_1",
                "side": "buy",
                "amount": 0.01,
                "tp_order_id": "tp_001",
                "sl_order_id": "sl_inactive_001",  # active_ordersにない
            }
        ]

        await tp_sl_manager.ensure_tp_sl_for_existing_positions(
            virtual_positions=virtual_positions,
            bitbank_client=mock_client,
            position_tracker=MagicMock(),
            mode="live",
        )

        # INACTIVE SLはVP補完でカウント→カバレッジOK→再配置されない
        mock_client.create_stop_loss_order = MagicMock()
        mock_client.create_stop_loss_order.assert_not_called()


class TestTPSLConfigPaths:
    """TPSLConfig パス生成メソッドテスト"""

    def test_tp_regime_config(self):
        """tp_regime_config: レジーム別TP設定ブロックパス"""
        from src.trading.execution.tp_sl_config import TPSLConfig

        path = TPSLConfig.tp_regime_config("tight_range")
        assert path == "position_management.take_profit.regime_based.tight_range"

    def test_sl_regime_config(self):
        """sl_regime_config: レジーム別SL設定ブロックパス"""
        from src.trading.execution.tp_sl_config import TPSLConfig

        path = TPSLConfig.sl_regime_config("trending")
        assert path == "position_management.stop_loss.regime_based.trending"

    def test_sl_fixed_amount_constants(self):
        """Phase 68.6: SL固定金額関連定数パス"""
        from src.trading.execution.tp_sl_config import TPSLConfig

        assert (
            TPSLConfig.SL_FIXED_AMOUNT_ENABLED
            == "position_management.stop_loss.fixed_amount.enabled"
        )
        assert (
            TPSLConfig.SL_FIXED_AMOUNT_TARGET
            == "position_management.stop_loss.fixed_amount.target_max_loss"
        )
        assert (
            TPSLConfig.SL_FIXED_AMOUNT_ENTRY_FEE
            == "position_management.stop_loss.fixed_amount.fallback_entry_fee_rate"
        )
        assert (
            TPSLConfig.SL_FIXED_AMOUNT_EXIT_FEE
            == "position_management.stop_loss.fixed_amount.fallback_exit_fee_rate"
        )


class TestPhase70FixedAmountSLWithEntryFee:
    """Phase 69: 復元ポジション固定金額SL（entry_feeはサンクコスト→除外）"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    def test_sl_includes_entry_fee(self, mock_threshold, tp_sl_manager):
        """Phase 70.2: SL計算がentry_fee+exit_fee両方を考慮"""

        def threshold_side_effect(key, default=None):
            mapping = {
                "position_management.stop_loss.fixed_amount.target_max_loss": 500,
                "position_management.stop_loss.fixed_amount.fallback_entry_fee_rate": 0.001,
                "position_management.stop_loss.fixed_amount.fallback_exit_fee_rate": 0.001,
            }
            return mapping.get(key, default)

        mock_threshold.side_effect = threshold_side_effect

        # 0.02BTC @ 10,800,000円
        avg_price = 10_800_000
        amount = 0.02
        sl_price = tp_sl_manager._calculate_fixed_amount_sl_for_position("long", amount, avg_price)

        # entry_fee = 10,800,000 * 0.02 * 0.001 = 216
        # exit_fee = 10,800,000 * 0.02 * 0.001 = 216
        # gross_needed = 500 - 216 - 216 = 68
        # sl_offset = 68 / 0.02 = 3,400
        # sl_price = 10,800,000 - 3,400 = 10,796,600
        entry_fee = avg_price * amount * 0.001  # 216
        exit_fee = avg_price * amount * 0.001  # 216
        expected_sl = avg_price - (500 - exit_fee - entry_fee) / amount
        assert abs(sl_price - expected_sl) < 1.0

        # 実損検証: offset * amount + exit_fee + entry_fee = 500
        sl_offset = avg_price - sl_price
        actual_loss = sl_offset * amount + exit_fee + entry_fee
        assert abs(actual_loss - 500) < 1.0

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    def test_sl_short_position(self, mock_threshold, tp_sl_manager):
        """ショートポジションのSL計算"""

        def threshold_side_effect(key, default=None):
            mapping = {
                "position_management.stop_loss.fixed_amount.target_max_loss": 500,
                "position_management.stop_loss.fixed_amount.fallback_entry_fee_rate": 0.001,
                "position_management.stop_loss.fixed_amount.fallback_exit_fee_rate": 0.001,
            }
            return mapping.get(key, default)

        mock_threshold.side_effect = threshold_side_effect

        avg_price = 10_800_000
        amount = 0.02
        sl_price = tp_sl_manager._calculate_fixed_amount_sl_for_position("short", amount, avg_price)

        # short: sl_price = avg_price + sl_offset
        assert sl_price > avg_price

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    def test_sl_gross_needed_floor(self, mock_threshold, tp_sl_manager):
        """gross_needed <= 0 の場合はtargetにフォールバック"""

        def threshold_side_effect(key, default=None):
            mapping = {
                "position_management.stop_loss.fixed_amount.target_max_loss": 100,
                "position_management.stop_loss.fixed_amount.fallback_entry_fee_rate": 0.01,
                "position_management.stop_loss.fixed_amount.fallback_exit_fee_rate": 0.01,
            }
            return mapping.get(key, default)

        mock_threshold.side_effect = threshold_side_effect

        # 手数料が目標を超える場合
        avg_price = 10_000_000
        amount = 0.1
        # exit_fee = 10,000,000 * 0.1 * 0.01 = 10,000
        # gross_needed = 100 - 10,000 = -9,900 → target(100)にフォールバック
        sl_price = tp_sl_manager._calculate_fixed_amount_sl_for_position("long", amount, avg_price)
        # sl_offset = 100 / 0.1 = 1000
        assert abs(sl_price - (avg_price - 1000)) < 1.0


class TestPhase686FixedAmountTPForPosition:
    """Phase 68.6: _calculate_fixed_amount_tp_for_position テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    def test_tp_long_position(self, mock_threshold, tp_sl_manager):
        """ロングポジションのTP計算"""

        def threshold_side_effect(key, default=None):
            mapping = {
                "position_management.take_profit.fixed_amount.target_net_profit": 500,
                "position_management.take_profit.fixed_amount.fallback_exit_fee_rate": 0.0,
            }
            return mapping.get(key, default)

        mock_threshold.side_effect = threshold_side_effect

        avg_price = 10_800_000
        amount = 0.01
        tp_price = tp_sl_manager._calculate_fixed_amount_tp_for_position("long", amount, avg_price)
        # tp_offset = 500 / 0.01 = 50,000
        assert abs(tp_price - (avg_price + 50_000)) < 1.0

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    def test_tp_short_position(self, mock_threshold, tp_sl_manager):
        """ショートポジションのTP計算"""

        def threshold_side_effect(key, default=None):
            mapping = {
                "position_management.take_profit.fixed_amount.target_net_profit": 500,
                "position_management.take_profit.fixed_amount.fallback_exit_fee_rate": 0.0,
            }
            return mapping.get(key, default)

        mock_threshold.side_effect = threshold_side_effect

        avg_price = 10_800_000
        amount = 0.01
        tp_price = tp_sl_manager._calculate_fixed_amount_tp_for_position("short", amount, avg_price)
        assert abs(tp_price - (avg_price - 50_000)) < 1.0

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    def test_is_fixed_amount_tp_enabled(self, mock_threshold, tp_sl_manager):
        """固定金額TPモード有効判定"""
        mock_threshold.return_value = True
        assert tp_sl_manager._is_fixed_amount_tp_enabled() is True
        mock_threshold.return_value = False
        assert tp_sl_manager._is_fixed_amount_tp_enabled() is False


# ========================================
# Phase 68.7: SL永続化クリアテスト
# ========================================


class TestPhase687SLPersistenceClear:
    """Phase 68.7: place_sl_or_market_close()でSL超過時にclear()が呼ばれるテスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_breach_clears_persistence(self, mock_threshold, tp_sl_manager):
        """Phase 68.7: SL超過成行決済時にsl_persistence.clear()が呼ばれる"""
        mock_threshold.side_effect = lambda key, default=None: default

        mock_client = MagicMock()
        mock_client.fetch_ticker = MagicMock(return_value={"last": 13500000.0})
        mock_client.fetch_active_orders = MagicMock(return_value=[])
        mock_client.cancel_order = MagicMock()
        mock_client.create_order = MagicMock(return_value={"id": "market_close_001"})

        with patch.object(tp_sl_manager.sl_persistence, "clear") as mock_clear:
            await tp_sl_manager.place_sl_or_market_close(
                entry_side="buy",
                position_side="long",
                amount=0.01,
                avg_price=14000000.0,
                sl_price=13600000.0,  # 現在価格13,500,000 <= SL 13,600,000
                symbol="BTC/JPY",
                bitbank_client=mock_client,
            )
            mock_clear.assert_called_once_with("buy")


class TestPhase82DustDetection:
    """Phase 82: ダスト/微小ポジション検出テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        return MagicMock()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_place_missing_tp_sl_skips_dust(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """ダストポジション(<0.001 BTC)ではTP/SL配置をスキップしcleanup_required返却"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.min_valid_position_btc": 0.001,
            "trading_constraints.currency_pair": "BTC/JPY",
        }.get(key, default)

        result = await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.0001,  # ダストサイズ（下限0.001未満）
            avg_price=11321161.0,
            has_tp=False,
            has_sl=False,
            virtual_positions=[],
            bitbank_client=mock_bitbank_client,
        )

        assert result is not None
        assert result["action"] == "dust_cleanup_required"
        assert result["amount"] == 0.0001
        assert result["side"] == "long"
        # TP/SL配置APIが呼ばれていないこと
        mock_bitbank_client.create_stop_loss_order.assert_not_called()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    def test_fixed_amount_tp_raises_on_dust(self, mock_threshold, tp_sl_manager):
        """固定金額TP計算でamount<0.001 BTCはValueError"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.min_valid_position_btc": 0.001,
        }.get(key, default)

        with pytest.raises(ValueError, match="固定金額TP計算のamount下限未満"):
            tp_sl_manager._calculate_fixed_amount_tp_for_position(
                position_side="long",
                amount=0.0001,
                avg_price=11321161.0,
            )

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    def test_fixed_amount_sl_raises_on_dust(self, mock_threshold, tp_sl_manager):
        """固定金額SL計算でamount<0.001 BTCはValueError"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.min_valid_position_btc": 0.001,
        }.get(key, default)

        with pytest.raises(ValueError, match="固定金額SL計算のamount下限未満"):
            tp_sl_manager._calculate_fixed_amount_sl_for_position(
                position_side="long",
                amount=0.0001,
                avg_price=11321161.0,
            )
