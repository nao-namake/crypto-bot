"""Phase 90δ: post_only パラメータ名修正のテスト。

bitbank API は snake_case "post_only" を期待する。ccxt 4.5.x の create_order は
params をそのまま extend で渡すだけで camelCase→snake_case 変換をしないため、
"postOnly" だと無視され通常指値化（即時約定時はテイカー約定）していた。
本テストは create_order が ccxt exchange へ "post_only": True を渡し、
"postOnly" を渡さないことを保証する（リグレッション防止）。
"""

from unittest.mock import MagicMock

from src.data.bitbank_client import BitbankClient


def _make_client():
    """__init__ をバイパスし、create_order に必要な属性のみ持つ client を生成。"""
    client = BitbankClient.__new__(BitbankClient)
    client.api_key = "test_key"
    client.api_secret = "test_secret"
    client.leverage = 1.0
    client.logger = MagicMock()
    client.exchange = MagicMock()
    client.exchange.create_order = MagicMock(return_value={"id": "order_test_1"})
    return client


class TestPhase90DeltaPostOnlyParamName:
    """Phase 90δ: post_only パラメータ名（snake_case）検証。"""

    def test_post_only_limit_sends_snake_case(self):
        client = _make_client()
        client.create_order(
            symbol="BTC/JPY",
            side="sell",
            order_type="limit",
            amount=0.02,
            price=11_000_000,
            post_only=True,
        )
        params = client.exchange.create_order.call_args.kwargs["params"]
        # bitbank API が解釈する snake_case であること
        assert params.get("post_only") is True
        # 旧バグの camelCase が混入しないこと
        assert "postOnly" not in params

    def test_post_only_false_omits_flag(self):
        client = _make_client()
        client.create_order(
            symbol="BTC/JPY",
            side="buy",
            order_type="limit",
            amount=0.02,
            price=11_000_000,
            post_only=False,
        )
        params = client.exchange.create_order.call_args.kwargs["params"]
        assert "post_only" not in params
        assert "postOnly" not in params

    def test_post_only_ignored_for_market_order(self):
        client = _make_client()
        client.create_order(
            symbol="BTC/JPY",
            side="buy",
            order_type="market",
            amount=0.02,
            post_only=True,  # market では post_only 非対象
        )
        params = client.exchange.create_order.call_args.kwargs["params"]
        assert "post_only" not in params
        assert "postOnly" not in params
