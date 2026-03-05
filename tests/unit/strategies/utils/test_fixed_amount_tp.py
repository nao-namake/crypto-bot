"""
Phase 61.7/61.8/61.10/63.2/64: 固定金額TP計算テスト

固定金額TP（目標純利益1,000円）の計算ロジックをテスト
Phase 61.8: バックテスト対応（fee_data=Noneでの手数料推定）
Phase 61.10: バックテスト・ライブモード ポジションサイズ統一
Phase 63.2: fee_data累積手数料バグ修正（集約ポジション問題）
Phase 64: Dynamic Position Sizing統合（sizer.pyに一本化）
"""

from src.strategies.utils.strategy_utils import RiskManager, SignalBuilder
from src.trading.core.types import PositionFeeData


class TestCalculateFixedAmountTP:
    """固定金額TP計算テスト"""

    def test_buy_position_basic(self):
        """BUYポジションの基本計算"""
        # Phase 62.19: 手数料改定対応（Maker 0%）
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0,
            "fallback_exit_fee_rate": 0.0,
        }

        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,  # 累積手数料（Phase 63.2: 無視される）
            unrealized_interest_amount=0.0,
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

        # Phase 63.2: fee_data.unrealized_fee_amount=346は無視される
        # 必要含み益 = 1000 + 0 + 0 + 0 = 1000円（fallback_entry_fee_rate=0.0）
        expected_required_profit = 1000 + 0 + 0  # entry_fee=0, interest=0, exit_fee=0
        expected_tp = 13618976.0 + (expected_required_profit / 0.0212)
        assert abs(tp_price - expected_tp) < 1  # 1円以内の誤差

    def test_sell_position_basic(self):
        """SELLポジションの基本計算"""
        # Phase 62.19: 手数料改定対応（Maker 0%）
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0,
            "fallback_exit_fee_rate": 0.0,
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
        # Phase 62.19: 手数料改定対応（Maker 0%）
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0,
            "fallback_exit_fee_rate": 0.0,
        }

        tp_price = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=13618976.0,
            amount=0.0212,
            fee_data=None,  # API取得失敗をシミュレート
            config=config,
        )

        assert tp_price is not None
        # Phase 62.19: フォールバック（Maker 0%）: エントリー手数料 = 0
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
        """Phase 63.2: 利息がfee_dataにあってもTP計算に影響しない"""
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0,
            "fallback_exit_fee_rate": 0.0,
        }

        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,
            unrealized_interest_amount=50.0,  # 累積利息（Phase 63.2: 無視される）
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
        # Phase 63.2: fee_data.unrealized_interest_amount=50は無視される
        # 必要含み益 = 1000 + 0 + 0 = 1000円
        expected_tp = 13618976.0 + (1000 / 0.0212)
        assert abs(tp_price - expected_tp) < 1

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


class TestPhase618BacktestSupport:
    """Phase 61.8: バックテスト対応テスト"""

    def test_backtest_mode_fee_estimation(self):
        """バックテストモード: fee_data=Noneでも固定金額TPが計算される"""
        config = {
            "max_loss_ratio": 0.003,
            "min_profit_ratio": 0.004,
            "take_profit_ratio": 1.33,
        }

        # バックテストモード: fee_data=None, position_amount=有効値
        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action="buy",
            current_price=13618976.0,
            current_atr=100000.0,
            config=config,
            regime="tight_range",
            fee_data=None,  # バックテストではAPIデータなし
            position_amount=0.0212,  # Phase 61.8: ポジション数量を指定
        )

        assert stop_loss is not None
        assert take_profit is not None
        # BUYなのでSLはエントリーより低い、TPは高い
        assert stop_loss < 13618976.0
        assert take_profit > 13618976.0

    def test_backtest_sell_with_fee_estimation(self):
        """バックテストモード: SELLポジションの手数料推定"""
        config = {
            "max_loss_ratio": 0.003,
            "min_profit_ratio": 0.004,
            "take_profit_ratio": 1.33,
        }

        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action="sell",
            current_price=13618976.0,
            current_atr=100000.0,
            config=config,
            regime="tight_range",
            fee_data=None,
            position_amount=0.0212,
        )

        assert stop_loss is not None
        assert take_profit is not None
        # SELLなのでSLはエントリーより高い、TPは低い
        assert stop_loss > 13618976.0
        assert take_profit < 13618976.0

    def test_backtest_vs_live_consistency(self):
        """Phase 63.2: バックテストとライブモードの計算結果が完全一致"""
        config = {
            "max_loss_ratio": 0.003,
            "min_profit_ratio": 0.004,
            "take_profit_ratio": 1.33,
        }

        entry_price = 13618976.0
        amount = 0.0212

        # ライブモード（fee_data指定 - Phase 63.2で無視される）
        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,  # 累積手数料（無視される）
            unrealized_interest_amount=0.0,
            average_price=entry_price,
            open_amount=amount,
        )

        _, tp_live = RiskManager.calculate_stop_loss_take_profit(
            action="buy",
            current_price=entry_price,
            current_atr=100000.0,
            config=config,
            regime="tight_range",
            fee_data=fee_data,
            position_amount=amount,
        )

        # バックテストモード（fee_data=None）
        _, tp_backtest = RiskManager.calculate_stop_loss_take_profit(
            action="buy",
            current_price=entry_price,
            current_atr=100000.0,
            config=config,
            regime="tight_range",
            fee_data=None,
            position_amount=amount,
        )

        assert tp_live is not None
        assert tp_backtest is not None

        # Phase 63.2: fee_dataが無視されるため完全一致
        assert tp_live == tp_backtest


class TestPhase68EntryFeeCorrection:
    """Phase 68: TP/SLエントリー手数料計算テスト"""

    def test_tp_with_taker_entry_fee(self):
        """TP計算にTakerエントリー手数料が含まれる"""
        config = {
            "target_net_profit": 500,
            "include_entry_fee": True,
            "fallback_entry_fee_rate": 0.001,
            "include_exit_fee_rebate": True,
            "fallback_exit_fee_rate": 0.0,
            "include_interest": True,
        }
        tp = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=11500000,
            amount=0.01,
            fee_data=None,
            config=config,
        )
        # entry_fee = 11500000 * 0.01 * 0.001 = 115
        # required = 500 + 115 = 615
        # distance = 615 / 0.01 = 61500
        # tp = 11500000 + 61500 = 11561500
        assert tp is not None
        assert abs(tp - 11561500) < 1

    def test_tp_without_entry_fee_for_comparison(self):
        """エントリー手数料なしのTP（比較用）"""
        config = {
            "target_net_profit": 500,
            "include_entry_fee": True,
            "fallback_entry_fee_rate": 0.0,
            "include_exit_fee_rebate": True,
            "fallback_exit_fee_rate": 0.0,
            "include_interest": True,
        }
        tp = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=11500000,
            amount=0.01,
            fee_data=None,
            config=config,
        )
        # entry_fee = 0
        # required = 500
        # distance = 500 / 0.01 = 50000
        # tp = 11500000 + 50000 = 11550000
        assert tp is not None
        assert abs(tp - 11550000) < 1

    def test_tp_entry_fee_increases_distance(self):
        """エントリー手数料によりTP距離が拡大する"""
        config_no_fee = {
            "target_net_profit": 500,
            "include_entry_fee": True,
            "fallback_entry_fee_rate": 0.0,
            "include_exit_fee_rebate": True,
            "fallback_exit_fee_rate": 0.0,
        }
        config_with_fee = {
            "target_net_profit": 500,
            "include_entry_fee": True,
            "fallback_entry_fee_rate": 0.001,
            "include_exit_fee_rebate": True,
            "fallback_exit_fee_rate": 0.0,
        }
        tp_no_fee = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=11500000,
            amount=0.01,
            fee_data=None,
            config=config_no_fee,
        )
        tp_with_fee = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=11500000,
            amount=0.01,
            fee_data=None,
            config=config_with_fee,
        )
        # 手数料込みのほうがTP距離が大きい
        assert tp_with_fee > tp_no_fee
        # 差分 = 115 / 0.01 = 11500円
        assert abs((tp_with_fee - tp_no_fee) - 11500) < 1

    def test_sell_tp_with_taker_entry_fee(self):
        """SELLでもTP計算にTakerエントリー手数料が含まれる"""
        config = {
            "target_net_profit": 500,
            "include_entry_fee": True,
            "fallback_entry_fee_rate": 0.001,
            "include_exit_fee_rebate": True,
            "fallback_exit_fee_rate": 0.0,
            "include_interest": True,
        }
        tp = RiskManager.calculate_fixed_amount_tp(
            action="sell",
            entry_price=11500000,
            amount=0.01,
            fee_data=None,
            config=config,
        )
        # SELL: tp = 11500000 - 61500 = 11438500
        assert tp is not None
        assert abs(tp - 11438500) < 1


class TestDynamicPositionSizing:
    """Phase 67.4: 固定ポジションサイズテーブル テスト"""

    def test_low_confidence_sizing(self):
        """低信頼度（<50%）でのポジションサイズ → 固定0.01 BTC"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.4,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        # Phase 67.4: 固定テーブル mode=fixed → low=0.01 BTC
        assert size == 0.01

    def test_medium_confidence_sizing(self):
        """中信頼度（50-65%）でのポジションサイズ → 固定0.015 BTC"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.6,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        # Phase 67.4: 固定テーブル mode=fixed → medium=0.015 BTC
        assert size == 0.015

    def test_high_confidence_sizing(self):
        """高信頼度（>65%）でのポジションサイズ → 固定0.02 BTC"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.8,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        # Phase 67.4: 固定テーブル mode=fixed → high=0.02 BTC
        assert size == 0.02

    def test_boundary_medium_confidence(self):
        """境界値: 信頼度50%ちょうどは medium"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.50,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        assert size == 0.015

    def test_boundary_high_confidence(self):
        """境界値: 信頼度65%ちょうどは high"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.65,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        assert size == 0.02

    def test_fixed_size_independent_of_balance_and_price(self):
        """固定サイズは残高・BTC価格に依存しない"""
        size1 = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.6,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        size2 = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.6,
            current_balance=100000,  # 残高1/5
            btc_price=20000000,  # 価格1.3倍
            config={},
        )
        # Phase 67.4: 固定テーブルなので同じ
        assert size1 == size2

    def test_fixed_amount_tp_with_fixed_size(self):
        """固定サイズでの固定金額TP計算が正常範囲"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.6,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        assert size == 0.015  # medium

        # Phase 62.19: 固定金額TP計算（Maker 0%）
        config = {
            "target_net_profit": 500,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "fallback_entry_fee_rate": 0.0,
            "fallback_exit_fee_rate": 0.0,
        }

        tp = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=15000000,
            amount=size,
            fee_data=None,
            config=config,
        )

        # TPが正常範囲
        # price_distance = 500 / 0.015 ≈ 33333円
        # TP ≈ 15000000 + 33333 = 15033333
        assert tp is not None
        assert tp > 15000000
        assert 15030000 <= tp <= 15040000

    def test_backtest_live_size_consistency(self):
        """バックテストとライブのサイズ計算が同じロジックを使用"""
        size1 = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.55,
            current_balance=500000,
            btc_price=14500000,
            config={},
        )

        size2 = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.55,
            current_balance=500000,
            btc_price=14500000,
            config={},
        )

        assert size1 == size2


class TestPhase632FeeDataIgnored:
    """Phase 63.2: fee_dataの累積手数料がTP計算に使われないことを確認"""

    def test_phase_63_2_fee_data_ignored(self):
        """fee_dataの累積手数料がTP計算に影響しないことを検証"""
        config = {
            "target_net_profit": 500,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0,
            "fallback_exit_fee_rate": 0.0,
        }
        # 集約ポジションの大きな累積手数料
        fee_data = PositionFeeData(
            unrealized_fee_amount=500.0,
            unrealized_interest_amount=100.0,
            average_price=11000000.0,
            open_amount=0.0300,
        )
        tp_with_fee = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=11000000.0,
            amount=0.0100,
            fee_data=fee_data,
            config=config,
        )
        tp_without_fee = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=11000000.0,
            amount=0.0100,
            fee_data=None,
            config=config,
        )
        # Phase 63.2: fee_data有無で結果が同一
        assert tp_with_fee == tp_without_fee
        # 必要含み益=500円のみ → price_distance = 500/0.01 = 50000
        assert abs(tp_with_fee - 11050000.0) < 1

    def test_phase_63_2_sell_fee_data_ignored(self):
        """SELLでもfee_dataが無視されることを検証"""
        config = {
            "target_net_profit": 500,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "include_interest": True,
            "fallback_entry_fee_rate": 0.0,
            "fallback_exit_fee_rate": 0.0,
        }
        fee_data = PositionFeeData(
            unrealized_fee_amount=300.0,
            unrealized_interest_amount=50.0,
            average_price=11000000.0,
            open_amount=0.0200,
        )
        tp_with_fee = RiskManager.calculate_fixed_amount_tp(
            action="sell",
            entry_price=11000000.0,
            amount=0.0100,
            fee_data=fee_data,
            config=config,
        )
        tp_without_fee = RiskManager.calculate_fixed_amount_tp(
            action="sell",
            entry_price=11000000.0,
            amount=0.0100,
            fee_data=None,
            config=config,
        )
        # Phase 63.2: fee_data有無で結果が同一
        assert tp_with_fee == tp_without_fee
        # 必要含み益=500円 → price_distance = 500/0.01 = 50000
        assert abs(tp_with_fee - 10950000.0) < 1
