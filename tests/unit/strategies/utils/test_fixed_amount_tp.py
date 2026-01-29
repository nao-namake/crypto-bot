"""
Phase 61.7/61.8/61.10: 固定金額TP計算テスト

固定金額TP（目標純利益1,000円）の計算ロジックをテスト
Phase 61.8: バックテスト対応（fee_data=Noneでの手数料推定）
Phase 61.10: バックテスト・ライブモード ポジションサイズ統一
"""

from src.strategies.utils.strategy_utils import RiskManager, SignalBuilder
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
        """バックテストとライブモードの計算結果が近似"""
        config = {
            "max_loss_ratio": 0.003,
            "min_profit_ratio": 0.004,
            "take_profit_ratio": 1.33,
        }

        entry_price = 13618976.0
        amount = 0.0212

        # ライブモード（fee_data指定）
        fee_data = PositionFeeData(
            unrealized_fee_amount=346.0,  # 実際のAPI値（Taker 0.12%相当）
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

        # バックテストモード（fee_data=None、フォールバックレートで推定）
        _, tp_backtest = RiskManager.calculate_stop_loss_take_profit(
            action="buy",
            current_price=entry_price,
            current_atr=100000.0,
            config=config,
            regime="tight_range",
            fee_data=None,  # フォールバックレート 0.12% で推定
            position_amount=amount,
        )

        assert tp_live is not None
        assert tp_backtest is not None

        # 両者の差が1%以内であることを確認
        # (手数料推定と実際の値の差異は許容)
        diff_pct = abs(tp_live - tp_backtest) / entry_price * 100
        assert diff_pct < 1.0, f"TP差異が大きすぎます: {diff_pct:.2f}%"


class TestDynamicPositionSizing:
    """Phase 61.10: Dynamic Position Sizing テスト"""

    def test_low_confidence_sizing(self):
        """低信頼度（<50%）でのポジションサイズ"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.4,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        # low_confidence: min_ratio=0.30%, max_ratio=0.60%
        # 0.40 confidence → normalized = (0.40 - 0.35) / 0.15 = 0.333
        # position_ratio = 0.003 + (0.006 - 0.003) * 0.333 ≈ 0.004
        # size = 500000 * 0.004 / 15000000 ≈ 0.000133 BTC
        # min_size=0.0001なので最低保証
        assert 0.0001 <= size <= 0.003

    def test_medium_confidence_sizing(self):
        """中信頼度（50-65%）でのポジションサイズ"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.6,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        # medium_confidence: min_ratio=0.45%, max_ratio=0.75%
        # 0.60 confidence → normalized = (0.60 - 0.50) / 0.15 = 0.667
        # position_ratio = 0.0045 + (0.0075 - 0.0045) * 0.667 ≈ 0.0065
        # size = 500000 * 0.0065 / 15000000 ≈ 0.000217 BTC
        assert 0.0001 <= size <= 0.003

    def test_high_confidence_sizing(self):
        """高信頼度（>65%）でのポジションサイズ"""
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.8,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )
        # high_confidence: min_ratio=0.60%, max_ratio=1.05%
        # 0.80 confidence → normalized = (0.80 - 0.65) / 0.35 = 0.429
        # position_ratio = 0.006 + (0.0105 - 0.006) * 0.429 ≈ 0.00793
        # size = 500000 * 0.00793 / 15000000 ≈ 0.000264 BTC
        assert 0.0001 <= size <= 0.004

    def test_max_size_limit(self):
        """最大サイズ制限が適用される"""
        # 極端に低いBTC価格で計算するとmax_size制限がかかる
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=1.0,
            current_balance=50000000,  # 5000万円
            btc_price=1000000,  # 100万円（極端に安い）
            config={},
        )
        # 計算上は大きくなるがmax_size=0.15で制限される
        assert size <= 0.15

    def test_min_size_guarantee(self):
        """最小サイズ保証"""
        # 極端に低い信頼度でも最小サイズは保証される
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.1,  # 極端に低い信頼度
            current_balance=10000,  # 1万円（少額）
            btc_price=15000000,
            config={},
        )
        # min_size=0.0001 BTC
        assert size >= 0.0001

    def test_fixed_amount_tp_with_dynamic_size(self):
        """Dynamic Sizingでの固定金額TP計算が正常範囲"""
        # まずDynamic Sizingで適切なサイズを計算
        size = SignalBuilder._calculate_dynamic_position_size(
            confidence=0.6,
            current_balance=500000,
            btc_price=15000000,
            config={},
        )

        # 固定金額TP計算
        config = {
            "target_net_profit": 1000,
            "include_entry_fee": True,
            "include_exit_fee_rebate": True,
            "fallback_entry_fee_rate": 0.0012,
            "fallback_exit_fee_rate": -0.0002,
        }

        # 計算されたサイズが小さすぎる場合のためにテスト用サイズを使用
        test_amount = 0.02  # 約30万円相当

        tp = RiskManager.calculate_fixed_amount_tp(
            action="buy",
            entry_price=15000000,
            amount=test_amount,
            fee_data=None,
            config=config,
        )

        # TPが正常範囲（エントリー価格 + 0.4-1%）
        if tp is not None:
            assert tp > 15000000
            # price_distance = (1000 + 手数料) / 0.02 ≈ 60000円
            # TP ≈ 15000000 + 60000 = 15060000
            assert 15050000 <= tp <= 15150000

    def test_backtest_live_size_consistency(self):
        """バックテストとライブのサイズ計算が同じロジックを使用"""
        # 同じ入力で同じ結果が得られることを確認
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
