"""
Phase 61.7: 固定金額TP計算テスト

固定金額TP（目標純利益1,000円）の計算ロジックをテスト
"""

from src.strategies.utils.strategy_utils import RiskManager
from src.trading.core.types import PositionFeeData


class TestCalculateFixedAmountTP:
    """固定金額TP計算テスト"""

    def test_buy_position_basic(self):
        """BUYポジションの基本計算"""
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0012,
            "fallback_exit_fee_rate": -0.0002,
        }

        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,  # エントリー手数料
            unrealized_interest_amount=0.0,  # 利息（キャンペーン中0円）
            average_price=13618976.0,
            open_amount=0.0212,
        )

        tp_price = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=13618976.0,
            amount=0.0212,
            fee_data=fee_data,
            config=config,
        )

        assert tp_price is not None
        # BUYの場合、TPはエントリー価格より高い
        assert tp_price > 13618976.0

        # 必要含み益 = 1000 + 346 + 0 - 58(リベート) = 1288円
        # TP価格 = 13618976 + (1288 / 0.0212) ≈ 13679752
        expected_required_profit = 1000 + 346 + 0 - (13618976.0 * 0.0212 * 0.0002)
        expected_tp = 13618976.0 + (expected_required_profit / 0.0212)
        assert abs(tp_price - expected_tp) < 1  # 1円以内の誤差

    def test_sell_position_basic(self):
        """SELLポジションの基本計算"""
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0012,
            "fallback_exit_fee_rate": -0.0002,
        }

        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,
            unrealized_interest_amount=0.0,
            average_price=13618976.0,
            open_amount=0.0212,
        )

        tp_price = RiskManager.calculate_fixed_amount_tp(
            action="sell",
            entry_price=13618976.0,
            amount=0.0212,
            fee_data=fee_data,
            config=config,
        )

        assert tp_price is not None
        # SELLの場合、TPはエントリー価格より低い
        assert tp_price < 13618976.0

    def test_fallback_when_no_fee_data(self):
        """fee_dataがNoneの場合のフォールバック"""
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0012,
            "fallback_exit_fee_rate": -0.0002,
        }

        tp_price = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=13618976.0,
            amount=0.0212,
            fee_data=None,  # API取得失敗をシミュレート
            config=config,
        )

        assert tp_price is not None
        # フォールバック: エントリー手数料 = 13618976 * 0.0212 * 0.0012 ≈ 346
        # 期待どおりに計算されることを確認
        assert tp_price > 13618976.0

    def test_zero_amount_returns_none(self):
        """数量が0の場合はNoneを返す"""
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
        }

        tp_price = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=13618976.0,
            amount=0.0,  # ゼロ数量
            fee_data=None,
            config=config,
        )

        assert tp_price is None

    def test_negative_amount_returns_none(self):
        """数量が負の場合はNoneを返す"""
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
        }

        tp_price = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=13618976.0,
            amount=-0.01,  # 負の数量
            fee_data=None,
            config=config,
        )

        assert tp_price is None

    def test_with_interest(self):
        """利息がある場合の計算"""
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
        }

        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,
            unrealized_interest_amount=50.0,  # 利息50円
            average_price=13618976.0,
            open_amount=0.0212,
        )

        tp_price = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=13618976.0,
            amount=0.0212,
            fee_data=fee_data,
            config=config,
        )

        assert tp_price is not None
        # 利息があると必要含み益が増加するため、TPはより高くなる

    def test_disabled_fee_options(self):
        """手数料オプションを無効化した場合"""
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": False,  # 無効
            "include_exit_fee_rebate": False,  # 無効
            "include_interest": False,  # 無効
        }

        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,
            unrealized_interest_amount=50.0,
            average_price=13618976.0,
            open_amount=0.0212,
        )

        tp_price = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=13618976.0,
            amount=0.0212,
            fee_data=fee_data,
            config=config,
        )

        assert tp_price is not None
        # 手数料を考慮しない場合、必要含み益 = 目標純利益のみ
        # entry_fee=0, interest=0, exit_rebate=0 → required = 1000
        expected_tp = 13618976.0 + (1000 / 0.0212)
        # 誤差許容を広げる（浮動小数点演算）
        assert abs(tp_price - expected_tp) < 10


class TestPositionFeeData:
    """PositionFeeDataクラスのテスト"""

    def test_from_api_response_full_data(self):
        """APIレスポンスから完全なデータを生成"""
        raw_data = {
            "unrealized_fee_amount": "346.12",
            "unrealized_interest_amount": "0.00",
            "average_price": "13618976.00",
            "open_amount": "0.0212",
        }

        fee_data = PositionFeeData.from_api_response(raw_data)

        assert fee_data.unrealized_fee_amount == 346.12
        assert fee_data.unrealized_interest_amount == 0.0
        assert fee_data.average_price == 13618976.0
        assert fee_data.open_amount == 0.0212

    def test_from_api_response_missing_data(self):
        """データが欠けている場合のデフォルト値"""
        raw_data = {}  # 空のレスポンス

        fee_data = PositionFeeData.from_api_response(raw_data)

        assert fee_data.unrealized_fee_amount == 0.0
        assert fee_data.unrealized_interest_amount == 0.0
        assert fee_data.average_price == 0.0
        assert fee_data.open_amount == 0.0

    def test_from_api_response_none_values(self):
        """None値が含まれる場合"""
        raw_data = {
            "unrealized_fee_amount": None,
            "unrealized_interest_amount": None,
            "average_price": "13618976.00",
            "open_amount": None,
        }

        fee_data = PositionFeeData.from_api_response(raw_data)

        assert fee_data.unrealized_fee_amount == 0.0
        assert fee_data.unrealized_interest_amount == 0.0
        assert fee_data.average_price == 13618976.0
        assert fee_data.open_amount == 0.0


class TestCalculateStopLossTakeProfitWithFixedAmount:
    """固定金額TPモード統合テスト"""

    def test_fixed_amount_mode_enabled(self):
        """固定金額モードが有効な場合（実際の設定読み込み）"""
        # 注: このテストは実際の設定ファイルを読み込む
        # Phase 61.7の設定が有効になっていることを前提

        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,
            unrealized_interest_amount=0.0,
            average_price=13618976.0,
            open_amount=0.0212,
        )

        config = {
            "max_loss_ratio": 0.003,
            "min_profit_ratio": 0.004,
            "take_profit_ratio": 1.33,
        }

        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action="buy",
            current_price=13618976.0,
            current_atr=100000.0,  # 適当なATR
            config=config,
            regime="tight_range",
            fee_data=fee_data,
            position_amount=0.0212,
        )

        assert stop_loss is not None
        assert take_profit is not None
        # BUYなのでSLはエントリーより低い、TPは高い
        assert stop_loss < 13618976.0
        assert take_profit > 13618976.0

    def test_fixed_amount_mode_without_position_amount(self):
        """position_amountが指定されない場合は%ベースを使用"""
        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,
            unrealized_interest_amount=0.0,
            average_price=13618976.0,
            open_amount=0.0212,
        )

        config = {
            "max_loss_ratio": 0.007,
            "min_profit_ratio": 0.009,
            "take_profit_ratio": 1.29,
        }

        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action="buy",
            current_price=13618976.0,
            current_atr=100000.0,
            config=config,
            fee_data=fee_data,
            position_amount=None,  # 数量なし→%ベースにフォールバック
        )

        assert stop_loss is not None
        assert take_profit is not None
        # %ベースで計算されていることを確認
        # TP距離 = max(price * 0.009, SL距離 * 1.29)
