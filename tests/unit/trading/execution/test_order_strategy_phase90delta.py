"""Phase 90δ: Maker約定種別の真実観測テスト。

旧実装は post_only 注文が約定すると無条件で「Maker約定成功・手数料Maker(0%)」と
記録していた（fee=0.0 ハードコード）。実態がテイカー約定でも虚偽の Maker 記録が
残るため、bitbank 約定履歴（fetch_my_trades）から takerOrMaker / 実 fee を取得して
ログ・ExecutionResult に反映するよう修正した。本テストはその取得・ログ分岐を検証する。
"""

from unittest.mock import Mock

import pytest

from src.trading.execution.order_strategy import OrderStrategy


class TestPhase90DeltaResolveFillType:
    """_resolve_fill_type: 約定種別・実手数料の取得。"""

    def setup_method(self):
        self.order_strategy = OrderStrategy()
        self.order_strategy.logger = Mock()

    @pytest.mark.asyncio
    async def test_taker_fill_detected(self):
        client = Mock()
        client.exchange.fetch_my_trades = Mock(
            return_value=[
                {"order": "123", "takerOrMaker": "taker", "fee": {"cost": "5.5"}},
            ]
        )
        tom, fee = await self.order_strategy._resolve_fill_type("123", "BTC/JPY", client)
        assert tom == "taker"
        assert fee == 5.5

    @pytest.mark.asyncio
    async def test_maker_fill_aggregates_only_matching_order(self):
        client = Mock()
        client.exchange.fetch_my_trades = Mock(
            return_value=[
                {"order": "777", "takerOrMaker": "maker", "fee": {"cost": "1.0"}},
                {"order": "777", "takerOrMaker": "maker", "fee": {"cost": "2.0"}},
                {"order": "999", "takerOrMaker": "taker", "fee": {"cost": "9.0"}},
            ]
        )
        tom, fee = await self.order_strategy._resolve_fill_type("777", "BTC/JPY", client)
        assert tom == "maker"
        assert fee == 3.0  # 同一 order の約定分のみ合算（order 999 は除外）

    @pytest.mark.asyncio
    async def test_no_matching_trade_returns_none(self):
        client = Mock()
        client.exchange.fetch_my_trades = Mock(
            return_value=[{"order": "other", "takerOrMaker": "maker"}]
        )
        tom, fee = await self.order_strategy._resolve_fill_type("123", "BTC/JPY", client)
        assert tom is None
        assert fee is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        client = Mock()
        client.exchange.fetch_my_trades = Mock(side_effect=Exception("api down"))
        tom, fee = await self.order_strategy._resolve_fill_type("123", "BTC/JPY", client)
        assert tom is None
        assert fee is None


class TestPhase90DeltaLogMakerFillResult:
    """_log_maker_fill_result: 約定種別に応じたログ分岐。"""

    def setup_method(self):
        self.order_strategy = OrderStrategy()
        self.order_strategy.logger = Mock()

    def test_taker_emits_warning(self):
        self.order_strategy._log_maker_fill_result("123", 11_685_990, 11_685_306, "taker", 5.5)
        msg = self.order_strategy.logger.warning.call_args[0][0]
        assert "Taker約定" in msg
        assert "11685306" in msg  # 指値価格も併記される

    def test_maker_emits_success(self):
        self.order_strategy._log_maker_fill_result("123", 11_685_990, 11_685_306, "maker", 0.0)
        msg = self.order_strategy.logger.warning.call_args[0][0]
        assert "Maker約定成功" in msg

    def test_unknown_type_labeled(self):
        self.order_strategy._log_maker_fill_result("123", 11_685_990, 11_685_306, None, None)
        msg = self.order_strategy.logger.warning.call_args[0][0]
        assert "約定種別不明" in msg
