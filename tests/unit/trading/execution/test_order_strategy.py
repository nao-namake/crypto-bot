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
