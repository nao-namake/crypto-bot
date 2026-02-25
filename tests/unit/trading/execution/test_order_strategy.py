"""
OrderStrategyテスト - Phase 38リファクタリング対応

テスト範囲:
- get_optimal_execution_config() - デフォルト動作（smart_order無効時）
- get_optimal_execution_config() - 指値注文価格計算（smart_order無効・limit注文）
- get_optimal_execution_config() - スマート注文機能（smart_order有効時）
- _assess_market_conditions() - 板情報取得・スプレッド計算
- _determine_order_strategy() - ML信頼度に基づく戦略決定
- _calculate_limit_price() - 買い注文・売り注文の指値価格計算
- エラーハンドリング - API失敗時のフォールバック

カバレッジ目標: 60-70%（20テストケース）
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading import TradeEvaluation
from src.trading.execution.order_strategy import OrderStrategy


class TestOrderStrategyBasicFunctionality:
    """OrderStrategy基本機能テスト"""

    def setup_method(self):
        """各テスト前の初期化"""
        self.order_strategy = OrderStrategy()

        # テスト用TradeEvaluation
        from src.trading import RiskDecision

        self.evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_smart_order_disabled_returns_default_market(self, mock_threshold):
        """smart_order無効時はデフォルト成行注文を返す

        設定:
        - order_execution.smart_order_enabled = False
        - trading_constraints.default_order_type = market

        期待結果:
        - order_type: "market"
        - price: None
        - strategy: "default"
        """
        # モック設定
        mock_threshold.side_effect = lambda key, default: {
            "order_execution.smart_order_enabled": False,
            "trading_constraints.default_order_type": "market",
        }.get(key, default)

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            self.evaluation, bitbank_client=None
        )

        # 検証
        assert result["order_type"] == "market"
        assert result["price"] is None
        assert result["strategy"] == "default"

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_smart_order_disabled_limit_calculates_price(self, mock_threshold):
        """smart_order無効・limit注文設定時は簡易指値価格計算

        設定:
        - order_execution.smart_order_enabled = False
        - trading_constraints.default_order_type = limit

        期待結果:
        - order_type: "limit"
        - price: 計算された指値価格
        - strategy: "simple_limit"
        """
        # モック設定
        mock_threshold.side_effect = lambda key, default: {
            "order_execution.smart_order_enabled": False,
            "trading_constraints.default_order_type": "limit",
        }.get(key, default)

        # モックBitbankClient
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={
                "bids": [[14500000, 0.5], [14490000, 1.0]],
                "asks": [[14510000, 0.3], [14520000, 0.8]],
            }
        )

        # 実行（買い注文）
        result = await self.order_strategy.get_optimal_execution_config(
            self.evaluation, bitbank_client=mock_client
        )

        # 検証
        assert result["order_type"] == "limit"
        assert result["price"] is not None
        assert result["strategy"] == "simple_limit"

        # 買い注文: best_ask * 1.0005 = 14510000 * 1.0005 = 14517255
        expected_price = 14510000 * 1.0005
        assert abs(result["price"] - expected_price) < 1000  # 許容誤差1000円

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_smart_order_disabled_limit_sell_calculates_price(self, mock_threshold):
        """smart_order無効・limit注文・売り注文時の指値価格計算

        期待結果:
        - 売り注文: best_bid * 0.9995 = 有利な売り価格
        """
        # モック設定
        mock_threshold.side_effect = lambda key, default: {
            "order_execution.smart_order_enabled": False,
            "trading_constraints.default_order_type": "limit",
        }.get(key, default)

        # モックBitbankClient
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={
                "bids": [[14500000, 0.5], [14490000, 1.0]],
                "asks": [[14510000, 0.3], [14520000, 0.8]],
            }
        )

        # 売り注文用評価
        sell_evaluation = TradeEvaluation(
            decision=self.evaluation.decision,
            side="sell",
            risk_score=self.evaluation.risk_score,
            position_size=self.evaluation.position_size,
            stop_loss=self.evaluation.stop_loss,
            take_profit=self.evaluation.take_profit,
            confidence_level=self.evaluation.confidence_level,
            warnings=self.evaluation.warnings,
            denial_reasons=self.evaluation.denial_reasons,
            evaluation_timestamp=self.evaluation.evaluation_timestamp,
            kelly_recommendation=self.evaluation.kelly_recommendation,
            drawdown_status=self.evaluation.drawdown_status,
            anomaly_alerts=self.evaluation.anomaly_alerts,
            market_conditions=self.evaluation.market_conditions,
        )

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            sell_evaluation, bitbank_client=mock_client
        )

        # 検証
        assert result["order_type"] == "limit"
        assert result["price"] is not None
        assert result["strategy"] == "simple_limit"

        # 売り注文: best_bid * 0.9995 = 14500000 * 0.9995 = 14492750
        expected_price = 14500000 * 0.9995
        assert abs(result["price"] - expected_price) < 1000  # 許容誤差1000円

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_smart_order_disabled_limit_orderbook_error_fallback(self, mock_threshold):
        """smart_order無効・limit注文・板情報取得エラー時のフォールバック

        期待結果:
        - 板情報取得失敗時は成行注文にフォールバック
        - order_type: "market"
        - strategy: "fallback_market"
        """
        # モック設定
        mock_threshold.side_effect = lambda key, default: {
            "order_execution.smart_order_enabled": False,
            "trading_constraints.default_order_type": "limit",
        }.get(key, default)

        # モックBitbankClient（エラー発生）
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(side_effect=Exception("API Error"))

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            self.evaluation, bitbank_client=mock_client
        )

        # 検証
        assert result["order_type"] == "market"
        assert result["price"] is None
        assert result["strategy"] == "fallback_market"


class TestOrderStrategySmartOrderMode:
    """OrderStrategyスマート注文機能テスト"""

    def setup_method(self):
        """各テスト前の初期化"""
        self.order_strategy = OrderStrategy()

        # テスト用TradeEvaluation（高信頼度）
        from src.trading import RiskDecision

        self.high_confidence_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,  # 高信頼度
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

        self.low_confidence_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.35,  # 低信頼度
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_smart_order_high_confidence_limit_order(self, mock_threshold):
        """スマート注文有効・高信頼度時は指値注文

        設定:
        - order_execution.smart_order_enabled = True
        - ML信頼度 >= high_confidence_threshold (0.75)
        - 市場条件良好

        期待結果:
        - order_type: "limit"
        - strategy: "high_confidence_limit"
        """

        # モック設定
        def threshold_mock(key, default):
            thresholds = {
                "order_execution.smart_order_enabled": True,
                "order_execution.high_confidence_threshold": 0.75,
                "order_execution.max_spread_ratio_for_limit": 0.005,
                "order_execution.price_improvement_ratio": 0.001,
            }
            return thresholds.get(key, default)

        mock_threshold.side_effect = threshold_mock

        # モックBitbankClient
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={
                "bids": [[14500000, 0.5], [14490000, 1.0]],
                "asks": [[14510000, 0.3], [14520000, 0.8]],
            }
        )

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            self.high_confidence_evaluation, bitbank_client=mock_client
        )

        # 検証
        assert result["order_type"] == "limit"
        assert result["strategy"] == "high_confidence_limit"
        assert result["price"] is not None
        assert result.get("expected_fee") == "maker_rebate"

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_smart_order_low_confidence_market_order(self, mock_threshold):
        """スマート注文有効・低信頼度時は成行注文

        設定:
        - order_execution.smart_order_enabled = True
        - ML信頼度 < low_confidence_threshold (0.4)

        期待結果:
        - order_type: "market"
        - strategy: "low_confidence_market"
        """

        # モック設定
        def threshold_mock(key, default):
            thresholds = {
                "order_execution.smart_order_enabled": True,
                "order_execution.low_confidence_threshold": 0.4,
            }
            return thresholds.get(key, default)

        mock_threshold.side_effect = threshold_mock

        # モックBitbankClient
        mock_client = AsyncMock()

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            self.low_confidence_evaluation, bitbank_client=mock_client
        )

        # 検証
        assert result["order_type"] == "market"
        assert result["strategy"] == "low_confidence_market"
        assert result["price"] is None

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_smart_order_medium_confidence_market_order(self, mock_threshold):
        """スマート注文有効・中信頼度時は成行注文（安全重視）

        設定:
        - ML信頼度が中間（0.4 <= confidence < 0.75）

        期待結果:
        - order_type: "market"
        - strategy: "medium_confidence_market"
        """

        # モック設定
        def threshold_mock(key, default):
            thresholds = {
                "order_execution.smart_order_enabled": True,
                "order_execution.high_confidence_threshold": 0.75,
                "order_execution.low_confidence_threshold": 0.4,
                "order_execution.max_spread_ratio_for_limit": 0.005,
            }
            return thresholds.get(key, default)

        mock_threshold.side_effect = threshold_mock

        # 中信頼度評価
        medium_confidence_evaluation = TradeEvaluation(
            decision=self.high_confidence_evaluation.decision,
            side="buy",
            risk_score=self.high_confidence_evaluation.risk_score,
            position_size=self.high_confidence_evaluation.position_size,
            stop_loss=self.high_confidence_evaluation.stop_loss,
            take_profit=self.high_confidence_evaluation.take_profit,
            confidence_level=0.60,  # 中信頼度
            warnings=self.high_confidence_evaluation.warnings,
            denial_reasons=self.high_confidence_evaluation.denial_reasons,
            evaluation_timestamp=self.high_confidence_evaluation.evaluation_timestamp,
            kelly_recommendation=self.high_confidence_evaluation.kelly_recommendation,
            drawdown_status=self.high_confidence_evaluation.drawdown_status,
            anomaly_alerts=self.high_confidence_evaluation.anomaly_alerts,
            market_conditions=self.high_confidence_evaluation.market_conditions,
        )

        # モックBitbankClient
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={
                "bids": [[14500000, 0.5]],
                "asks": [[14510000, 0.3]],
            }
        )

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            medium_confidence_evaluation, bitbank_client=mock_client
        )

        # 検証
        assert result["order_type"] == "market"
        assert result["strategy"] == "medium_confidence_market"


class TestOrderStrategyMarketConditions:
    """OrderStrategy市場条件評価テスト"""

    def setup_method(self):
        """各テスト前の初期化"""
        self.order_strategy = OrderStrategy()

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_assess_market_conditions_normal_spread(self, mock_threshold):
        """市場条件評価 - 正常なスプレッド

        期待結果:
        - spread_ratio計算成功
        - spread_too_wide = False
        """
        # モック設定
        mock_threshold.return_value = 0.005  # max_spread_ratio_for_limit = 0.5%

        # モックBitbankClient
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={
                "bids": [[14500000, 0.5], [14490000, 1.0]],
                "asks": [[14510000, 0.3], [14520000, 0.8]],
            }
        )

        # 実行
        conditions = await self.order_strategy._assess_market_conditions(mock_client)

        # 検証
        assert "spread_ratio" in conditions
        assert conditions["spread_ratio"] > 0
        assert "spread_too_wide" not in conditions  # 正常スプレッド
        assert conditions["best_bid"] == 14500000
        assert conditions["best_ask"] == 14510000

        # スプレッド計算確認: (14510000 - 14500000) / 14500000 = 0.00069
        expected_spread = (14510000 - 14500000) / 14500000
        assert abs(conditions["spread_ratio"] - expected_spread) < 0.0001

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_assess_market_conditions_wide_spread(self, mock_threshold):
        """市場条件評価 - スプレッド拡大

        期待結果:
        - spread_too_wide = True
        """
        # モック設定
        mock_threshold.return_value = 0.005  # max_spread_ratio_for_limit = 0.5%

        # モックBitbankClient（スプレッド1%）
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={
                "bids": [[14500000, 0.5]],
                "asks": [[14650000, 0.3]],  # 1%以上のスプレッド
            }
        )

        # 実行
        conditions = await self.order_strategy._assess_market_conditions(mock_client)

        # 検証
        assert conditions.get("spread_too_wide") is True
        assert conditions["spread_ratio"] > 0.005  # 0.5%超過

    @pytest.mark.asyncio
    async def test_assess_market_conditions_no_client(self):
        """市場条件評価 - BitbankClientなし

        期待結果:
        - assessment = "unable_to_assess"
        - デフォルト値返却
        """
        # 実行
        conditions = await self.order_strategy._assess_market_conditions(None)

        # 検証
        assert conditions["assessment"] == "unable_to_assess"
        assert conditions["spread_ratio"] == 0.0
        assert conditions["volume_adequate"] is True

    @pytest.mark.asyncio
    async def test_assess_market_conditions_orderbook_error(self):
        """市場条件評価 - 板情報取得エラー

        期待結果:
        - orderbook_error記録
        - デフォルト値返却
        """
        # モックBitbankClient（エラー発生）
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(side_effect=Exception("API Error"))

        # 実行
        conditions = await self.order_strategy._assess_market_conditions(mock_client)

        # 検証
        assert "orderbook_error" in conditions
        assert conditions["orderbook_error"] == "API Error"


class TestOrderStrategyLimitPriceCalculation:
    """OrderStrategy指値価格計算テスト"""

    def setup_method(self):
        """各テスト前の初期化"""
        self.order_strategy = OrderStrategy()

        # テスト用TradeEvaluation
        from src.trading import RiskDecision

        self.buy_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

        self.sell_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="sell",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_calculate_limit_price_buy_order(self, mock_threshold):
        """指値価格計算 - 買い注文

        期待結果:
        - 買い注文: best_bid * (1 + price_improvement_ratio)
        - ask価格を超えない制限
        """
        # モック設定
        mock_threshold.return_value = 0.001  # price_improvement_ratio = 0.1%

        # 市場条件
        market_conditions = {
            "best_bid": 14500000,
            "best_ask": 14510000,
        }

        # 実行
        limit_price = await self.order_strategy._calculate_limit_price(
            self.buy_evaluation, market_conditions
        )

        # 検証
        assert limit_price > 0

        # 買い注文: best_bid * 1.001 = 14500000 * 1.001 = 14514500
        # ただし、ask * 0.999 = 14510000 * 0.999 = 14495490 より小さくする
        # → min(14514500, 14495490) = 14495490
        max_buy_price = 14510000 * 0.999
        assert limit_price <= max_buy_price

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_calculate_limit_price_sell_order(self, mock_threshold):
        """指値価格計算 - 売り注文

        期待結果:
        - 売り注文: best_ask * (1 - price_improvement_ratio)
        - bid価格を下回らない制限
        """
        # モック設定
        mock_threshold.return_value = 0.001  # price_improvement_ratio = 0.1%

        # 市場条件
        market_conditions = {
            "best_bid": 14500000,
            "best_ask": 14510000,
        }

        # 実行
        limit_price = await self.order_strategy._calculate_limit_price(
            self.sell_evaluation, market_conditions
        )

        # 検証
        assert limit_price > 0

        # 売り注文: best_ask * 0.999 = 14510000 * 0.999 = 14495490
        # ただし、bid * 1.001 = 14500000 * 1.001 = 14514500 より大きくする
        # → max(14495490, 14514500) = 14514500
        min_sell_price = 14500000 * 1.001
        assert limit_price >= min_sell_price

    @pytest.mark.asyncio
    async def test_calculate_limit_price_missing_bid_ask(self):
        """指値価格計算 - bid/ask情報なし

        期待結果:
        - 価格計算失敗（0返却）
        """
        # 市場条件（bid/askなし）
        market_conditions = {
            "best_bid": 0,
            "best_ask": 0,
        }

        # 実行
        limit_price = await self.order_strategy._calculate_limit_price(
            self.buy_evaluation, market_conditions
        )

        # 検証
        assert limit_price == 0

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_calculate_limit_price_invalid_side(self, mock_threshold):
        """指値価格計算 - 不正な注文サイド

        期待結果:
        - 価格計算失敗（0返却）
        """
        # モック設定
        mock_threshold.return_value = 0.001

        # 不正なサイド
        invalid_evaluation = TradeEvaluation(
            decision=self.buy_evaluation.decision,
            side="invalid_side",  # 不正なサイド
            risk_score=self.buy_evaluation.risk_score,
            position_size=self.buy_evaluation.position_size,
            stop_loss=self.buy_evaluation.stop_loss,
            take_profit=self.buy_evaluation.take_profit,
            confidence_level=self.buy_evaluation.confidence_level,
            warnings=self.buy_evaluation.warnings,
            denial_reasons=self.buy_evaluation.denial_reasons,
            evaluation_timestamp=self.buy_evaluation.evaluation_timestamp,
            kelly_recommendation=self.buy_evaluation.kelly_recommendation,
            drawdown_status=self.buy_evaluation.drawdown_status,
            anomaly_alerts=self.buy_evaluation.anomaly_alerts,
            market_conditions=self.buy_evaluation.market_conditions,
        )

        # 市場条件
        market_conditions = {
            "best_bid": 14500000,
            "best_ask": 14510000,
        }

        # 実行
        limit_price = await self.order_strategy._calculate_limit_price(
            invalid_evaluation, market_conditions
        )

        # 検証
        assert limit_price == 0


class TestMakerPriceCalculation:
    """Phase 65.16: Maker価格計算テスト（1円スプレッド対応）"""

    def setup_method(self):
        self.order_strategy = OrderStrategy()

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_buy_normal_spread(self, mock_threshold):
        """買い注文: スプレッド2円以上 → inside配置（bid+1）"""
        mock_threshold.return_value = 1  # tick=1
        price = self.order_strategy._calculate_maker_price("buy", 14500000, 14500002)
        assert price == 14500001  # bid+1

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_sell_normal_spread(self, mock_threshold):
        """売り注文: スプレッド2円以上 → inside配置（ask-1）"""
        mock_threshold.return_value = 1
        price = self.order_strategy._calculate_maker_price("sell", 14500000, 14500002)
        assert price == 14500001  # ask-1

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_buy_1yen_spread(self, mock_threshold):
        """Phase 65.16: 買い注文・スプレッド1円 → best_bid配置"""
        mock_threshold.return_value = 1
        price = self.order_strategy._calculate_maker_price("buy", 14500000, 14500001)
        assert price == 14500000  # best_bid

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_sell_1yen_spread(self, mock_threshold):
        """Phase 65.16: 売り注文・スプレッド1円 → best_ask配置"""
        mock_threshold.return_value = 1
        price = self.order_strategy._calculate_maker_price("sell", 14500000, 14500001)
        assert price == 14500001  # best_ask

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_buy_zero_spread(self, mock_threshold):
        """買い注文: スプレッド0円（bid=ask） → best_bid配置"""
        mock_threshold.return_value = 1
        price = self.order_strategy._calculate_maker_price("buy", 14500000, 14500000)
        assert price == 14500000

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_sell_zero_spread(self, mock_threshold):
        """売り注文: スプレッド0円（bid=ask） → best_ask配置"""
        mock_threshold.return_value = 1
        price = self.order_strategy._calculate_maker_price("sell", 14500000, 14500000)
        assert price == 14500000

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_invalid_side(self, mock_threshold):
        """不正なside → 0返却"""
        mock_threshold.return_value = 1
        price = self.order_strategy._calculate_maker_price("invalid", 14500000, 14500001)
        assert price == 0

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_buy_never_returns_zero(self, mock_threshold):
        """Phase 65.16: 買い注文は0を返さない（フォールバック不要）"""
        mock_threshold.return_value = 1
        # どのスプレッドでも有効な価格を返す
        for spread in [0, 1, 2, 5, 100]:
            price = self.order_strategy._calculate_maker_price("buy", 14500000, 14500000 + spread)
            assert price > 0, f"spread={spread}でprice=0が返された"

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_sell_never_returns_zero(self, mock_threshold):
        """Phase 65.16: 売り注文は0を返さない（フォールバック不要）"""
        mock_threshold.return_value = 1
        for spread in [0, 1, 2, 5, 100]:
            price = self.order_strategy._calculate_maker_price("sell", 14500000, 14500000 + spread)
            assert price > 0, f"spread={spread}でprice=0が返された"


class TestOrderStrategyErrorHandling:
    """OrderStrategyエラーハンドリングテスト"""

    def setup_method(self):
        """各テスト前の初期化"""
        self.order_strategy = OrderStrategy()

        # テスト用TradeEvaluation
        from src.trading import RiskDecision

        self.evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_get_optimal_execution_config_error_fallback(self, mock_threshold):
        """get_optimal_execution_config() エラー時のフォールバック

        期待結果:
        - エラー発生時は成行注文にフォールバック
        - strategy: "fallback_market"
        """
        # モック設定（エラー発生）
        mock_threshold.side_effect = Exception("Threshold Error")

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            self.evaluation, bitbank_client=None
        )

        # 検証
        assert result["order_type"] == "market"
        assert result["price"] is None
        assert result["strategy"] == "fallback_market"

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_smart_order_wide_spread_market_order(self, mock_threshold):
        """スマート注文有効・スプレッド拡大時は成行注文

        期待結果:
        - spread_too_wide時は成行注文
        - strategy: "wide_spread_market"
        """

        # モック設定
        def threshold_mock(key, default):
            thresholds = {
                "order_execution.smart_order_enabled": True,
                "order_execution.high_confidence_threshold": 0.75,
                "order_execution.max_spread_ratio_for_limit": 0.005,
            }
            return thresholds.get(key, default)

        mock_threshold.side_effect = threshold_mock

        # モックBitbankClient（スプレッド拡大）
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={
                "bids": [[14500000, 0.5]],
                "asks": [[14650000, 0.3]],  # 1%スプレッド
            }
        )

        # 高信頼度評価
        high_confidence_evaluation = TradeEvaluation(
            decision=self.evaluation.decision,
            side="buy",
            risk_score=self.evaluation.risk_score,
            position_size=self.evaluation.position_size,
            stop_loss=self.evaluation.stop_loss,
            take_profit=self.evaluation.take_profit,
            confidence_level=0.85,  # 高信頼度
            warnings=self.evaluation.warnings,
            denial_reasons=self.evaluation.denial_reasons,
            evaluation_timestamp=self.evaluation.evaluation_timestamp,
            kelly_recommendation=self.evaluation.kelly_recommendation,
            drawdown_status=self.evaluation.drawdown_status,
            anomaly_alerts=self.evaluation.anomaly_alerts,
            market_conditions=self.evaluation.market_conditions,
        )

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            high_confidence_evaluation, bitbank_client=mock_client
        )

        # 検証
        assert result["order_type"] == "market"
        assert result["strategy"] == "wide_spread_market"

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_emergency_exit_market_order(self, mock_threshold):
        """緊急時は成行注文

        期待結果:
        - emergency_exit=True時は成行注文
        - strategy: "emergency_market"
        """

        # モック設定
        def threshold_mock(key, default):
            thresholds = {
                "order_execution.smart_order_enabled": True,
            }
            return thresholds.get(key, default)

        mock_threshold.side_effect = threshold_mock

        # 緊急退出評価
        emergency_evaluation = TradeEvaluation(
            decision=self.evaluation.decision,
            side="sell",
            risk_score=self.evaluation.risk_score,
            position_size=self.evaluation.position_size,
            stop_loss=self.evaluation.stop_loss,
            take_profit=self.evaluation.take_profit,
            confidence_level=0.85,
            warnings=self.evaluation.warnings,
            denial_reasons=self.evaluation.denial_reasons,
            evaluation_timestamp=self.evaluation.evaluation_timestamp,
            kelly_recommendation=self.evaluation.kelly_recommendation,
            drawdown_status=self.evaluation.drawdown_status,
            anomaly_alerts=self.evaluation.anomaly_alerts,
            market_conditions=self.evaluation.market_conditions,
        )
        # emergency_exit属性追加
        emergency_evaluation.emergency_exit = True

        # モックBitbankClient
        mock_client = AsyncMock()

        # 実行
        result = await self.order_strategy.get_optimal_execution_config(
            emergency_evaluation, bitbank_client=mock_client
        )

        # 検証
        assert result["order_type"] == "market"
        assert result["strategy"] == "emergency_market"


class TestOrderStrategyUnfavorableStrategy:
    """確実約定戦略テスト（entry_price_strategy=unfavorable）"""

    def setup_method(self):
        self.order_strategy = OrderStrategy()

        from src.trading import RiskDecision

        self.buy_eval = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

        self.sell_eval = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="sell",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_unfavorable_buy_price(self, mock_threshold):
        """確実約定戦略: 買いはask+premium"""
        mock_threshold.side_effect = lambda key, default: {
            "order_execution.entry_price_strategy": "unfavorable",
            "order_execution.guaranteed_execution_premium": 0.0005,
        }.get(key, default)

        conditions = {"best_bid": 14500000, "best_ask": 14510000}
        price = await self.order_strategy._calculate_limit_price(self.buy_eval, conditions)
        expected = round(14510000 * 1.0005)
        assert price == expected

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_unfavorable_sell_price(self, mock_threshold):
        """確実約定戦略: 売りはbid-premium"""
        mock_threshold.side_effect = lambda key, default: {
            "order_execution.entry_price_strategy": "unfavorable",
            "order_execution.guaranteed_execution_premium": 0.0005,
        }.get(key, default)

        conditions = {"best_bid": 14500000, "best_ask": 14510000}
        price = await self.order_strategy._calculate_limit_price(self.sell_eval, conditions)
        expected = round(14500000 * 0.9995)
        assert price == expected

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_unfavorable_invalid_side(self, mock_threshold):
        """確実約定戦略: 不正side→0"""
        mock_threshold.side_effect = lambda key, default: {
            "order_execution.entry_price_strategy": "unfavorable",
            "order_execution.guaranteed_execution_premium": 0.0005,
        }.get(key, default)

        from src.trading import RiskDecision

        invalid_eval = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="invalid",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )
        conditions = {"best_bid": 14500000, "best_ask": 14510000}
        price = await self.order_strategy._calculate_limit_price(invalid_eval, conditions)
        assert price == 0

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_limit_price_exception(self, mock_threshold):
        """_calculate_limit_price: 例外発生時は0を返す"""
        mock_threshold.side_effect = Exception("threshold error")
        conditions = {"best_bid": 14500000, "best_ask": 14510000}
        price = await self.order_strategy._calculate_limit_price(self.buy_eval, conditions)
        assert price == 0

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_determine_order_strategy_exception(self, mock_threshold):
        """_determine_order_strategy: 例外時はerror_fallback_market"""
        mock_threshold.side_effect = Exception("error")
        from src.trading import RiskDecision

        eval_ = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )
        result = await self.order_strategy._determine_order_strategy(0.8, 0.75, {}, eval_)
        assert result["strategy"] == "error_fallback_market"

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_assess_market_conditions_inner_exception(self, mock_threshold):
        """_assess_market_conditions: 板情報取得エラーでorderbook_error"""
        mock_threshold.return_value = 0.005
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(side_effect=Exception("inner error"))
        result = await self.order_strategy._assess_market_conditions(mock_client)
        assert "orderbook_error" in result


class TestMakerExecutionConfig:
    """get_maker_execution_config テスト"""

    def setup_method(self):
        self.order_strategy = OrderStrategy()

        from src.trading import RiskDecision

        self.eval_ = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_maker_disabled(self, mock_threshold):
        """Maker戦略無効時"""
        mock_threshold.return_value = {"enabled": False}
        result = await self.order_strategy.get_maker_execution_config(self.eval_)
        assert result["use_maker"] is False
        assert result["disable_reason"] == "disabled"

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_maker_no_client(self, mock_threshold):
        """クライアントなし時"""
        mock_threshold.return_value = {"enabled": True}
        result = await self.order_strategy.get_maker_execution_config(self.eval_)
        assert result["use_maker"] is False
        assert result["disable_reason"] == "no_client"

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_maker_conditions_not_viable(self, mock_threshold):
        """市場条件不適格時"""
        mock_threshold.side_effect = lambda key, default=None: {
            "order_execution.maker_strategy": {
                "enabled": True,
                "volatility_threshold": 0.02,
            },
            "order_execution.maker_strategy.price_adjustment_tick": 1,
        }.get(key, default)

        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(return_value=None)

        result = await self.order_strategy.get_maker_execution_config(
            self.eval_, bitbank_client=mock_client
        )
        assert result["use_maker"] is False

    @pytest.mark.asyncio
    @patch("src.trading.execution.order_strategy.get_threshold")
    async def test_maker_success(self, mock_threshold):
        """Maker戦略成功時"""
        mock_threshold.side_effect = lambda key, default=None: {
            "order_execution.maker_strategy": {
                "enabled": True,
                "min_spread_for_maker": 0,
                "volatility_threshold": 0.02,
            },
            "order_execution.maker_strategy.price_adjustment_tick": 1,
        }.get(key, default)

        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={
                "bids": [[14500000, 0.5]],
                "asks": [[14500010, 0.3]],
            }
        )

        result = await self.order_strategy.get_maker_execution_config(
            self.eval_, bitbank_client=mock_client
        )
        assert result["use_maker"] is True
        assert result["price"] > 0


class TestAssessMakerConditions:
    """_assess_maker_conditions テスト"""

    def setup_method(self):
        self.order_strategy = OrderStrategy()

    @pytest.mark.asyncio
    async def test_orderbook_unavailable(self):
        """板情報取得失敗"""
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(return_value=None)
        config = {"volatility_threshold": 0.02}
        result = await self.order_strategy._assess_maker_conditions(mock_client, config)
        assert result["maker_viable"] is False

    @pytest.mark.asyncio
    async def test_empty_bids(self):
        """bidsが空"""
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(return_value={"bids": [], "asks": [[14500000, 0.3]]})
        config = {"volatility_threshold": 0.02}
        result = await self.order_strategy._assess_maker_conditions(mock_client, config)
        assert result["maker_viable"] is False

    @pytest.mark.asyncio
    async def test_invalid_prices(self):
        """無効な価格"""
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={"bids": [[0, 0.5]], "asks": [[14500000, 0.3]]}
        )
        config = {"volatility_threshold": 0.02}
        result = await self.order_strategy._assess_maker_conditions(mock_client, config)
        assert result["maker_viable"] is False

    @pytest.mark.asyncio
    async def test_spread_too_narrow(self):
        """スプレッドが狭すぎる"""
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={"bids": [[14500000, 0.5]], "asks": [[14500001, 0.3]]}
        )
        config = {"min_spread_for_maker": 0.001, "volatility_threshold": 0.02}
        result = await self.order_strategy._assess_maker_conditions(mock_client, config)
        assert result["maker_viable"] is False
        assert result["disable_reason"] == "spread_too_narrow"

    @pytest.mark.asyncio
    async def test_high_volatility(self):
        """高ボラティリティ"""
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={"bids": [[14500000, 0.5]], "asks": [[14800000, 0.3]]}
        )
        config = {"min_spread_for_maker": 0, "volatility_threshold": 0.01}
        result = await self.order_strategy._assess_maker_conditions(mock_client, config)
        assert result["maker_viable"] is False
        assert result["disable_reason"] == "high_volatility"

    @pytest.mark.asyncio
    async def test_viable(self):
        """条件適格"""
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(
            return_value={"bids": [[14500000, 0.5]], "asks": [[14500100, 0.3]]}
        )
        config = {"min_spread_for_maker": 0, "volatility_threshold": 0.02}
        result = await self.order_strategy._assess_maker_conditions(mock_client, config)
        assert result["maker_viable"] is True

    @pytest.mark.asyncio
    async def test_exception(self):
        """例外発生時"""
        mock_client = AsyncMock()
        mock_client.fetch_order_book = Mock(side_effect=Exception("network error"))
        config = {"volatility_threshold": 0.02}
        result = await self.order_strategy._assess_maker_conditions(mock_client, config)
        assert result["maker_viable"] is False


class TestEnsureMinimumTradeSize:
    """ensure_minimum_trade_size テスト"""

    def setup_method(self):
        self.order_strategy = OrderStrategy()

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_dynamic_disabled(self, mock_threshold):
        """動的ポジションサイジング無効時は変更なし"""
        mock_threshold.return_value = False
        from src.trading import RiskDecision

        eval_ = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.00005,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )
        result = self.order_strategy.ensure_minimum_trade_size(eval_)
        assert result.position_size == 0.00005

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_below_minimum(self, mock_threshold):
        """最小ロット未満の場合最小ロットに補正"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.dynamic_position_sizing.enabled": True,
            "trading_constraints.min_trade_size": 0.0001,
        }.get(key, default)

        from src.trading import RiskDecision

        eval_ = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.00005,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )
        result = self.order_strategy.ensure_minimum_trade_size(eval_)
        assert result.position_size == 0.0001

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_above_minimum(self, mock_threshold):
        """最小ロット以上の場合変更なし"""
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.dynamic_position_sizing.enabled": True,
            "trading_constraints.min_trade_size": 0.0001,
        }.get(key, default)

        from src.trading import RiskDecision

        eval_ = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )
        result = self.order_strategy.ensure_minimum_trade_size(eval_)
        assert result.position_size == 0.001

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_exception(self, mock_threshold):
        """例外時は元のevaluation返却"""
        mock_threshold.side_effect = Exception("error")
        from src.trading import RiskDecision

        eval_ = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.00005,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.85,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )
        result = self.order_strategy.ensure_minimum_trade_size(eval_)
        assert result.position_size == 0.00005
