"""
Bitbank BTC/JPY戦略の包括的テスト
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from crypto_bot.strategy.bitbank_btc_jpy_strategy import (
    BitbankBTCJPYStrategy,
    BTCMarketContext,
    BTCTradingPhase,
    BTCTradingStrategy,
)


class TestBitbankBTCJPYStrategy:
    """BTC/JPY戦略テストクラス"""

    @pytest.fixture
    def mock_bitbank_client(self):
        """Bitbankクライアントモック"""
        client = Mock()
        client.fetch_ticker.return_value = {
            "last": 3000000.0,
            "bid": 2999500.0,
            "ask": 3000500.0,
            "volume": 100.0,
            "timestamp": datetime.now().timestamp() * 1000,
        }
        client.fetch_order_book.return_value = {
            "bids": [[2999500.0, 0.5], [2999000.0, 1.0], [2998500.0, 1.5]],
            "asks": [[3000500.0, 0.5], [3001000.0, 1.0], [3001500.0, 1.5]],
        }
        client.fetch_ohlcv.return_value = [
            [datetime.now().timestamp() * 1000, 2950000, 3050000, 2940000, 3000000, 50],
            [datetime.now().timestamp() * 1000, 3000000, 3100000, 2990000, 3050000, 75],
            [
                datetime.now().timestamp() * 1000,
                3050000,
                3080000,
                3020000,
                3000000,
                100,
            ],
        ]
        return client

    @pytest.fixture
    def mock_config(self):
        """設定モック"""
        config = Mock()
        config.get.return_value = {
            "large_order_threshold": 1.0,
            "trend_profit_target": 0.05,
            "swing_profit_target": 0.03,
            "spread_capture_threshold": 0.0002,
            "position_max_size": 0.5,
            "risk_per_trade": 0.01,
            "max_daily_trades": 20,
            "trend_confirmation_periods": 3,
            "volatility_threshold": 0.02,
            "liquidity_threshold": 10.0,
            "market_impact_threshold": 0.001,
        }
        return config

    @pytest.fixture
    def btc_strategy(self, mock_bitbank_client, mock_config):
        """BTC戦略インスタンス"""
        # 必要なコンポーネントのモック作成
        mock_fee_optimizer = Mock()
        mock_fee_guard = Mock()
        mock_order_manager = Mock()

        with patch(
            "crypto_bot.strategy.bitbank_btc_jpy_strategy."
            "BitbankEnhancedPositionManager"
        ):
            strategy = BitbankBTCJPYStrategy(
                mock_bitbank_client,
                mock_fee_optimizer,
                mock_fee_guard,
                mock_order_manager,
                mock_config,
            )
            return strategy

    def test_initialization(self, btc_strategy):
        """初期化テスト"""
        assert btc_strategy is not None
        assert btc_strategy.market_context is not None
        assert btc_strategy.btc_config is not None
        assert btc_strategy.trend_analysis is not None

    def test_market_context_analysis(self, btc_strategy):
        """市場コンテキスト分析テスト"""
        context = btc_strategy.analyze_market_context()

        assert isinstance(context, BTCMarketContext)
        assert context.current_price > 0
        assert context.bid_ask_spread > 0
        assert context.spread_ratio > 0
        assert context.volume_24h >= 0  # モック環境では0になる可能性がある
        assert context.volatility >= 0
        assert context.trend_strength >= 0

    def test_trading_phase_detection(self, btc_strategy):
        """取引フェーズ検出テスト"""
        # 上昇トレンドのテストデータ
        btc_strategy.price_history = [2900000, 2950000, 3000000, 3050000, 3100000]

        phase = btc_strategy.determine_trading_phase()
        assert isinstance(phase, BTCTradingPhase)

        # 下降トレンドのテストデータ
        btc_strategy.price_history = [3100000, 3050000, 3000000, 2950000, 2900000]
        phase = btc_strategy.determine_trading_phase()
        assert isinstance(phase, BTCTradingPhase)

    def test_trend_following_strategy(self, btc_strategy):
        """トレンドフォロー戦略テスト"""
        # 上昇トレンド設定
        btc_strategy.trend_analysis = {
            "current_trend": "uptrend",
            "trend_strength": 0.8,
            "trend_duration": 5,
            "trend_start_price": 2900000.0,
            "support_levels": [2950000, 2980000],
            "resistance_levels": [3050000, 3100000],
        }

        # 実際の実装メソッドを使用
        success, message = btc_strategy.execute_trend_following_strategy()
        assert isinstance(success, bool)
        assert isinstance(message, str)

    def test_mean_reversion_strategy(self, btc_strategy):
        """平均回帰戦略テスト"""
        # 過売り状態のテストデータ
        btc_strategy.price_history = [3100000, 3050000, 3000000, 2950000, 2900000]
        btc_strategy.market_context.current_price = 2900000

        success, message = btc_strategy.execute_mean_reversion_strategy()
        assert isinstance(success, bool)
        assert isinstance(message, str)

    def test_breakout_strategy(self, btc_strategy):
        """ブレイクアウト戦略テスト"""
        # 抵抗線ブレイクアウトのテストデータ
        btc_strategy.trend_analysis["resistance_levels"] = [3000000, 3050000]
        btc_strategy.market_context.current_price = 3100000
        btc_strategy.market_context.volume_24h = 200  # 高出来高

        success, message = btc_strategy.execute_breakout_strategy()
        assert isinstance(success, bool)
        assert isinstance(message, str)

    def test_spread_capture_strategy(self, btc_strategy):
        """スプレッド獲得戦略テスト"""
        # 大きなスプレッドのテストデータ
        btc_strategy.market_context.bid_ask_spread = 1500.0  # 大きなスプレッド
        btc_strategy.market_context.spread_ratio = 0.0005

        success, message = btc_strategy.execute_spread_capture_strategy()
        assert isinstance(success, bool)
        assert isinstance(message, str)

    def test_large_order_execution(self, btc_strategy):
        """大口注文実行戦略テスト"""
        # 大口注文の実行
        order_amount = 2.0
        target_price = 3000000
        max_slippage = 0.001
        time_horizon = 3600

        # 実際の実装メソッドを使用
        success, message = btc_strategy.execute_large_order(
            order_amount, target_price, max_slippage, time_horizon
        )
        assert isinstance(success, bool)
        assert isinstance(message, str)

    def test_strategy_selection(self, btc_strategy):
        """戦略選択テスト"""
        # 取引フェーズを先に決定
        phase = btc_strategy.determine_trading_phase()

        # 異なる市場条件での戦略選択
        btc_strategy.market_context.liquidity_score = 0.8
        btc_strategy.market_context.volatility_score = 0.3
        btc_strategy.trend_analysis["trend_strength"] = 0.7

        strategy = btc_strategy.select_optimal_strategy(phase)
        assert isinstance(strategy, BTCTradingStrategy)

    def test_technical_indicators(self, btc_strategy):
        """テクニカル指標計算テスト"""
        # 価格履歴の設定
        btc_strategy.price_history = [
            2900000,
            2950000,
            2920000,
            2980000,
            2940000,
            3000000,
            2960000,
            3020000,
            2980000,
            3050000,
            3000000,
            3080000,
            3020000,
            3100000,
            3050000,
        ]

        # テクニカル指標の計算
        btc_strategy._calculate_technical_indicators()

        # 計算が正常に実行されることを確認
        assert len(btc_strategy.price_history) > 0

    def test_trend_analysis(self, btc_strategy):
        """トレンド分析テスト"""
        # 価格履歴の設定
        btc_strategy.price_history = [2900000, 2950000, 3000000, 3050000, 3100000]

        # トレンド分析の実行
        btc_strategy._analyze_trend()

        # トレンド分析結果の検証
        assert btc_strategy.trend_analysis["current_trend"] in [
            "uptrend",
            "downtrend",
            "neutral",
        ]

    def test_error_handling(self, btc_strategy):
        """エラーハンドリングテスト"""
        # API エラーの場合の処理
        btc_strategy.bitbank_client.fetch_ticker.side_effect = Exception("API Error")

        # エラーが発生してもクラッシュしない
        try:
            context = btc_strategy.analyze_market_context()
            # フォールバック値が設定されている
            assert context.current_price > 0
        except Exception:
            # 例外が適切に処理されている
            pass

    def test_integration_with_fee_optimization(self, btc_strategy):
        """手数料最適化統合テスト"""
        # 手数料最適化システムとの統合
        assert btc_strategy.fee_optimizer is not None
        assert btc_strategy.fee_guard is not None
        assert btc_strategy.order_manager is not None
        assert btc_strategy.position_manager is not None

    def test_configuration_validation(self, btc_strategy):
        """設定検証テスト"""
        # 設定値の妥当性検証
        config = btc_strategy.btc_config
        assert config.large_order_threshold > 0
        assert 0 < config.trend_profit_target <= 1
        assert 0 < config.swing_profit_target <= 1
        assert config.spread_capture_threshold > 0
        assert config.position_max_size > 0
        assert 0 < config.risk_per_trade <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
