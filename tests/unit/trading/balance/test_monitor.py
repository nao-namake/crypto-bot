"""
残高・保証金監視サービステスト - Phase 64整理版

BalanceMonitorの包括的テストスイート。

テスト範囲:
- 保証金維持率計算（API優先・フォールバック）
- 直接計算ロジック（正常・極小値・異常値）
- API取得（成功・失敗）
- 維持率判定（SAFE/CAUTION/WARNING/CRITICAL）
- 新規ポジション追加後の維持率予測
- 推奨アクション生成
- ユーザー警告判定
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading.balance.monitor import BalanceMonitor
from src.trading.core import MarginData, MarginPrediction, MarginStatus


class TestBalanceMonitorCalculation:
    """保証金維持率計算テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    def test_monitor_initialization(self):
        """BalanceMonitor初期化テスト."""
        assert hasattr(self.monitor, "logger")

    def test_calculate_margin_ratio_direct_normal(self):
        """保証金維持率直接計算テスト（正常値）."""
        # 100万円残高、50万円建玉 → 200%
        ratio = self.monitor._calculate_margin_ratio_direct(
            balance_jpy=1000000, position_value_jpy=500000
        )
        assert ratio == pytest.approx(200.0, rel=0.01)

        # 50万円残高、100万円建玉 → 50%
        ratio2 = self.monitor._calculate_margin_ratio_direct(
            balance_jpy=500000, position_value_jpy=1000000
        )
        assert ratio2 == pytest.approx(50.0, rel=0.01)

    def test_calculate_margin_ratio_direct_no_position(self):
        """建玉なし時の保証金維持率計算テスト."""
        ratio = self.monitor._calculate_margin_ratio_direct(
            balance_jpy=1000000, position_value_jpy=0
        )
        assert ratio == float("inf")

    def test_calculate_margin_ratio_direct_negative_position(self):
        """負の建玉値時の保証金維持率計算テスト."""
        ratio = self.monitor._calculate_margin_ratio_direct(
            balance_jpy=1000000, position_value_jpy=-100000
        )
        assert ratio == float("inf")

    @patch("src.trading.balance.monitor.get_threshold")
    def test_calculate_margin_ratio_direct_tiny_position(self, mock_threshold):
        """極小建玉値時の保証金維持率計算テスト."""
        mock_threshold.return_value = 1000.0

        # 建玉が極小値（1000円未満）→ 安全値500%を返す
        ratio = self.monitor._calculate_margin_ratio_direct(
            balance_jpy=100000, position_value_jpy=500
        )
        assert ratio == 500.0
        mock_threshold.assert_called_with("margin.min_position_value", 1000.0)

    @patch("src.trading.balance.monitor.get_threshold")
    def test_calculate_margin_ratio_direct_extreme_high(self, mock_threshold):
        """異常な高維持率時のキャップテスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.min_position_value": 1000.0,
            "margin.max_ratio_cap": 10000.0,
        }.get(key, default)

        # 1億円残高、100円建玉 → 極小建玉なので500%を返す
        # （建玉が1000円未満のため極小値扱い）
        ratio = self.monitor._calculate_margin_ratio_direct(
            balance_jpy=100000000, position_value_jpy=100
        )
        assert ratio == 500.0

    @patch("src.trading.balance.monitor.get_threshold")
    def test_calculate_margin_ratio_direct_negative_balance(self, mock_threshold):
        """負の残高時の保証金維持率計算テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.min_position_value": 1000.0,
            "margin.max_ratio_cap": 10000.0,
        }.get(key, default)

        # 負の残高 → 0にクリップ
        ratio = self.monitor._calculate_margin_ratio_direct(
            balance_jpy=-100000, position_value_jpy=500000
        )
        assert ratio == 0.0


class TestBalanceMonitorAPI:
    """API取得関連テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    @pytest.mark.asyncio
    async def test_fetch_margin_ratio_from_api_success(self):
        """API直接取得成功テスト."""
        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"margin_ratio": 150.5})

        ratio = await self.monitor._fetch_margin_ratio_from_api(mock_client)

        assert ratio == 150.5
        mock_client.fetch_margin_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_margin_ratio_from_api_no_data(self):
        """API応答にデータなし時のテスト."""
        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={})

        ratio = await self.monitor._fetch_margin_ratio_from_api(mock_client)

        assert ratio is None

    @pytest.mark.asyncio
    async def test_fetch_margin_ratio_from_api_error(self):
        """API取得失敗時のテスト."""
        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(side_effect=Exception("API connection error"))

        ratio = await self.monitor._fetch_margin_ratio_from_api(mock_client)

        assert ratio is None

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    async def test_calculate_margin_ratio_backtest_mode(self, mock_backtest):
        """バックテストモード時のAPI呼び出しスキップテスト."""
        mock_backtest.return_value = True
        mock_client = Mock()

        ratio = await self.monitor.calculate_margin_ratio(
            balance_jpy=1000000, position_value_jpy=500000, bitbank_client=mock_client
        )

        # バックテストモード時はAPIを呼ばず直接計算
        assert ratio == pytest.approx(200.0, rel=0.01)
        assert not mock_client.fetch_margin_status.called

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    async def test_calculate_margin_ratio_api_priority(self, mock_backtest):
        """API優先取得テスト."""
        mock_backtest.return_value = False
        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"margin_ratio": 175.0})

        ratio = await self.monitor.calculate_margin_ratio(
            balance_jpy=1000000, position_value_jpy=500000, bitbank_client=mock_client
        )

        # API値が優先される
        assert ratio == 175.0
        mock_client.fetch_margin_status.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    async def test_calculate_margin_ratio_fallback(self, mock_backtest):
        """APIフォールバック計算テスト."""
        mock_backtest.return_value = False
        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(side_effect=Exception("API error"))

        ratio = await self.monitor.calculate_margin_ratio(
            balance_jpy=1000000, position_value_jpy=500000, bitbank_client=mock_client
        )

        # API失敗時は直接計算にフォールバック
        assert ratio == pytest.approx(200.0, rel=0.01)


class TestMarginStatus:
    """維持率判定テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    @patch("src.trading.balance.monitor.get_threshold")
    def test_get_margin_status_safe(self, mock_threshold):
        """SAFE状態判定テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        status, message = self.monitor.get_margin_status(250.0)
        assert status == MarginStatus.SAFE
        assert "安全" in message

    @patch("src.trading.balance.monitor.get_threshold")
    def test_get_margin_status_caution(self, mock_threshold):
        """CAUTION状態判定テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        status, message = self.monitor.get_margin_status(175.0)
        assert status == MarginStatus.CAUTION
        assert "低下" in message

    @patch("src.trading.balance.monitor.get_threshold")
    def test_get_margin_status_warning(self, mock_threshold):
        """WARNING状態判定テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        status, message = self.monitor.get_margin_status(125.0)
        assert status == MarginStatus.WARNING
        assert "警告" in message

    @patch("src.trading.balance.monitor.get_threshold")
    def test_get_margin_status_critical(self, mock_threshold):
        """CRITICAL状態判定テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        status, message = self.monitor.get_margin_status(80.0)
        assert status == MarginStatus.CRITICAL
        assert "危険" in message or "追証" in message


class TestMarginPrediction:
    """維持率予測テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_predict_future_margin(self, mock_threshold, mock_backtest):
        """新規ポジション追加後の維持率予測テスト."""
        mock_backtest.return_value = True
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        # 現在: 100万円残高、50万円建玉（200%）
        # 追加: 0.01 BTC @ 500万円 = 5万円建玉
        # 予測: 100万円残高、55万円建玉（181.8%）→ CAUTION
        prediction = await self.monitor.predict_future_margin(
            current_balance_jpy=1000000,
            current_position_value_jpy=500000,
            new_position_size_btc=0.01,
            btc_price_jpy=5000000,
        )

        assert isinstance(prediction, MarginPrediction)
        assert prediction.current_margin.margin_ratio == pytest.approx(200.0, rel=0.01)
        assert prediction.future_margin_ratio == pytest.approx(181.8, rel=0.01)
        assert prediction.future_status == MarginStatus.CAUTION
        assert prediction.position_size_btc == 0.01
        assert prediction.btc_price == 5000000
        assert len(prediction.recommendation) > 0

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_predict_future_margin_safe_to_critical(self, mock_threshold, mock_backtest):
        """安全→危険への予測テスト."""
        mock_backtest.return_value = True
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        # 現在: 100万円残高、10万円建玉（1000%）
        # 追加: 0.2 BTC @ 500万円 = 100万円建玉
        # 予測: 100万円残高、110万円建玉（90.9%）→ CRITICAL
        prediction = await self.monitor.predict_future_margin(
            current_balance_jpy=1000000,
            current_position_value_jpy=100000,
            new_position_size_btc=0.2,
            btc_price_jpy=5000000,
        )

        assert prediction.current_margin.status == MarginStatus.SAFE
        assert prediction.future_status == MarginStatus.CRITICAL
        assert "警告" in prediction.recommendation or "拒否" in prediction.recommendation


class TestRecommendations:
    """推奨アクション生成テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    @patch("src.trading.balance.monitor.get_threshold")
    def test_get_recommendation_safe(self, mock_threshold):
        """安全維持率時の推奨アクションテスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        recommendation = self.monitor._get_recommendation(250.0)
        assert "問題なし" in recommendation or "✅" in recommendation

    @patch("src.trading.balance.monitor.get_threshold")
    def test_get_recommendation_caution(self, mock_threshold):
        """注意維持率時の推奨アクションテスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        recommendation = self.monitor._get_recommendation(175.0)
        assert "監視" in recommendation or "注意" in recommendation

    @patch("src.trading.balance.monitor.get_threshold")
    def test_get_recommendation_warning(self, mock_threshold):
        """警告維持率時の推奨アクションテスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        recommendation = self.monitor._get_recommendation(125.0)
        assert "削減" in recommendation or "ポジション" in recommendation

    @patch("src.trading.balance.monitor.get_threshold")
    def test_get_recommendation_critical(self, mock_threshold):
        """危険維持率時の推奨アクションテスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        recommendation = self.monitor._get_recommendation(80.0)
        assert "拒否" in recommendation or "警告" in recommendation


class TestUserWarning:
    """ユーザー警告判定テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    @patch("src.trading.balance.monitor.get_threshold")
    def test_should_warn_user_critical(self, mock_threshold):
        """追証レベル警告判定テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.warning": 100.0,
            "margin.thresholds.caution": 150.0,
            "margin.large_drop_threshold": 50.0,
        }.get(key, default)

        current_margin = MarginData(
            current_balance=1000000,
            position_value_jpy=500000,
            margin_ratio=200.0,
            status=MarginStatus.SAFE,
            message="",
            timestamp=datetime.now(),
        )

        prediction = MarginPrediction(
            current_margin=current_margin,
            future_margin_ratio=80.0,  # 100%未満
            future_status=MarginStatus.CRITICAL,
            position_size_btc=0.1,
            btc_price=5000000,
            recommendation="",
        )

        should_warn, message = self.monitor.should_warn_user(prediction)

        assert should_warn is True
        assert "警告" in message or "低下" in message or "拒否" in message

    @patch("src.trading.balance.monitor.get_threshold")
    def test_should_warn_user_large_drop(self, mock_threshold):
        """大幅低下警告判定テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.warning": 100.0,
            "margin.thresholds.caution": 150.0,
            "margin.large_drop_threshold": 50.0,
        }.get(key, default)

        current_margin = MarginData(
            current_balance=1000000,
            position_value_jpy=500000,
            margin_ratio=200.0,
            status=MarginStatus.SAFE,
            message="",
            timestamp=datetime.now(),
        )

        prediction = MarginPrediction(
            current_margin=current_margin,
            future_margin_ratio=140.0,  # 60%低下
            future_status=MarginStatus.CAUTION,
            position_size_btc=0.05,
            btc_price=5000000,
            recommendation="",
        )

        should_warn, message = self.monitor.should_warn_user(prediction)

        assert should_warn is True
        assert "大幅" in message or "低下" in message

    @patch("src.trading.balance.monitor.get_threshold")
    def test_should_warn_user_below_warning_threshold(self, mock_threshold):
        """警告閾値以下での警告判定テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.warning": 100.0,
            "margin.thresholds.caution": 150.0,
            "margin.large_drop_threshold": 50.0,
        }.get(key, default)

        current_margin = MarginData(
            current_balance=1000000,
            position_value_jpy=500000,
            margin_ratio=200.0,
            status=MarginStatus.SAFE,
            message="",
            timestamp=datetime.now(),
        )

        prediction = MarginPrediction(
            current_margin=current_margin,
            future_margin_ratio=140.0,  # 150%未満
            future_status=MarginStatus.CAUTION,
            position_size_btc=0.03,
            btc_price=5000000,
            recommendation="",
        )

        should_warn, message = self.monitor.should_warn_user(prediction)

        assert should_warn is True
        assert "注意" in message or "140" in message

    @patch("src.trading.balance.monitor.get_threshold")
    def test_should_warn_user_no_warning(self, mock_threshold):
        """警告不要判定テスト."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.warning": 100.0,
            "margin.thresholds.caution": 150.0,
            "margin.large_drop_threshold": 50.0,
        }.get(key, default)

        current_margin = MarginData(
            current_balance=1000000,
            position_value_jpy=500000,
            margin_ratio=200.0,
            status=MarginStatus.SAFE,
            message="",
            timestamp=datetime.now(),
        )

        prediction = MarginPrediction(
            current_margin=current_margin,
            future_margin_ratio=180.0,  # 安全範囲内
            future_status=MarginStatus.CAUTION,
            position_size_btc=0.01,
            btc_price=5000000,
            recommendation="",
        )

        should_warn, message = self.monitor.should_warn_user(prediction)

        assert should_warn is False
        assert message == ""


class TestMarginRatioHighCap:
    """高維持率キャップテスト."""

    def setup_method(self):
        self.monitor = BalanceMonitor()

    @patch("src.trading.balance.monitor.get_threshold")
    def test_margin_ratio_capped(self, mock_threshold):
        """異常に高い維持率はキャップされる."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.min_position_value": 1000.0,
            "margin.max_ratio_cap": 10000.0,
        }.get(key, default)

        # 1億円残高、5000円建玉 → 2000000% → 10000%にキャップ
        ratio = self.monitor._calculate_margin_ratio_direct(
            balance_jpy=100000000, position_value_jpy=5000
        )
        assert ratio == 10000.0


class TestPredictFutureMarginAPI:
    """API連携時の維持率予測テスト."""

    def setup_method(self):
        self.monitor = BalanceMonitor()

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_predict_with_api_margin(self, mock_threshold, mock_backtest):
        """API取得成功時の維持率予測."""
        mock_backtest.return_value = False
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
            "margin.min_position_value": 1000.0,
            "margin.max_ratio_cap": 10000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"margin_ratio": 200.0})
        mock_client.has_open_positions = AsyncMock(return_value=True)

        prediction = await self.monitor.predict_future_margin(
            current_balance_jpy=1000000,
            current_position_value_jpy=500000,
            new_position_size_btc=0.01,
            btc_price_jpy=5000000,
            bitbank_client=mock_client,
        )

        assert isinstance(prediction, MarginPrediction)
        assert prediction.current_margin.margin_ratio == 200.0

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_predict_no_positions(self, mock_threshold, mock_backtest):
        """ポジションなし時の予測."""
        mock_backtest.return_value = False
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
            "margin.min_position_value": 1000.0,
            "margin.max_ratio_cap": 10000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"margin_ratio": 500.0})
        mock_client.has_open_positions = AsyncMock(return_value=False)

        prediction = await self.monitor.predict_future_margin(
            current_balance_jpy=1000000,
            current_position_value_jpy=0,
            new_position_size_btc=0.01,
            btc_price_jpy=5000000,
            bitbank_client=mock_client,
        )

        assert isinstance(prediction, MarginPrediction)

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_predict_api_failure_fallback(self, mock_threshold, mock_backtest):
        """API取得失敗時のフォールバック."""
        mock_backtest.return_value = False
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
            "margin.min_position_value": 1000.0,
            "margin.max_ratio_cap": 10000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(side_effect=Exception("API error"))
        mock_client.has_open_positions = AsyncMock(side_effect=Exception("API error"))

        prediction = await self.monitor.predict_future_margin(
            current_balance_jpy=1000000,
            current_position_value_jpy=500000,
            new_position_size_btc=0.01,
            btc_price_jpy=5000000,
            bitbank_client=mock_client,
        )

        assert isinstance(prediction, MarginPrediction)

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_predict_warning_log_on_ratio_drop(self, mock_threshold, mock_backtest):
        """維持率低下時の警告ログ."""
        mock_backtest.return_value = False
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
            "margin.min_position_value": 1000.0,
            "margin.max_ratio_cap": 10000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"margin_ratio": 300.0})
        mock_client.has_open_positions = AsyncMock(return_value=True)

        prediction = await self.monitor.predict_future_margin(
            current_balance_jpy=1000000,
            current_position_value_jpy=500000,
            new_position_size_btc=0.1,
            btc_price_jpy=5000000,
            bitbank_client=mock_client,
        )

        # 維持率低下するはず
        assert prediction.future_margin_ratio < 300.0


class TestGetRecommendationCritical:
    """推奨アクションテスト: critical閾値."""

    def setup_method(self):
        self.monitor = BalanceMonitor()

    @patch("src.trading.balance.monitor.get_threshold")
    def test_recommendation_below_critical(self, mock_threshold):
        """critical閾値未満で拒否推奨."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.critical": 80.0,
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        recommendation = self.monitor._get_recommendation(70.0)
        assert "拒否" in recommendation


class TestShouldWarnCritical:
    """should_warn_user: critical threshold テスト."""

    def setup_method(self):
        self.monitor = BalanceMonitor()

    @patch("src.trading.balance.monitor.get_threshold")
    def test_warn_below_critical(self, mock_threshold):
        """critical閾値未満で警告."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.critical": 80.0,
            "margin.thresholds.warning": 100.0,
            "margin.thresholds.caution": 150.0,
            "margin.large_drop_threshold": 50.0,
        }.get(key, default)

        current_margin = MarginData(
            current_balance=1000000,
            position_value_jpy=500000,
            margin_ratio=200.0,
            status=MarginStatus.SAFE,
            message="",
            timestamp=datetime.now(),
        )

        prediction = MarginPrediction(
            current_margin=current_margin,
            future_margin_ratio=70.0,
            future_status=MarginStatus.CRITICAL,
            position_size_btc=0.1,
            btc_price=5000000,
            recommendation="",
        )

        should_warn, message = self.monitor.should_warn_user(prediction)
        assert should_warn is True
        assert "危険" in message or "拒否" in message

    @patch("src.trading.balance.monitor.get_threshold")
    def test_warn_below_caution(self, mock_threshold):
        """caution閾値未満で注意."""
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.critical": 80.0,
            "margin.thresholds.warning": 100.0,
            "margin.thresholds.caution": 150.0,
            "margin.large_drop_threshold": 50.0,
        }.get(key, default)

        current_margin = MarginData(
            current_balance=1000000,
            position_value_jpy=500000,
            margin_ratio=170.0,  # 低下幅を50未満に抑える
            status=MarginStatus.CAUTION,
            message="",
            timestamp=datetime.now(),
        )

        prediction = MarginPrediction(
            current_margin=current_margin,
            future_margin_ratio=135.0,  # 150未満
            future_status=MarginStatus.CAUTION,
            position_size_btc=0.03,
            btc_price=5000000,
            recommendation="",
        )

        should_warn, message = self.monitor.should_warn_user(prediction)
        assert should_warn is True
        assert "注意" in message


class TestValidateMarginBalance:
    """validate_margin_balance テスト."""

    def setup_method(self):
        self.monitor = BalanceMonitor()

    @pytest.mark.asyncio
    async def test_non_live_mode(self):
        """ライブモード以外はsufficient=True."""
        result = await self.monitor.validate_margin_balance(mode="paper")
        assert result["sufficient"] is True

    @pytest.mark.asyncio
    async def test_no_client(self):
        """クライアントなしはsufficient=True."""
        result = await self.monitor.validate_margin_balance(mode="live", bitbank_client=None)
        assert result["sufficient"] is True

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_sufficient_balance(self, mock_threshold):
        """十分な残高."""
        mock_threshold.side_effect = lambda key, default: {
            "balance_alert.enabled": True,
            "balance_alert.min_required_margin": 14000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"available_balance": 500000})

        result = await self.monitor.validate_margin_balance(mode="live", bitbank_client=mock_client)
        assert result["sufficient"] is True
        assert result["available"] == 500000

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_insufficient_balance(self, mock_threshold):
        """残高不足."""
        mock_threshold.side_effect = lambda key, default: {
            "balance_alert.enabled": True,
            "balance_alert.min_required_margin": 14000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"available_balance": 5000})

        result = await self.monitor.validate_margin_balance(mode="live", bitbank_client=mock_client)
        assert result["sufficient"] is False

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_api_auth_error_retry(self, mock_threshold):
        """API認証エラーでリトライカウント増加."""
        mock_threshold.side_effect = lambda key, default: {
            "balance_alert.enabled": True,
            "balance_alert.min_required_margin": 14000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(side_effect=Exception("API エラー: 20001"))

        self.monitor._margin_check_failure_count = 0
        result = await self.monitor.validate_margin_balance(mode="live", bitbank_client=mock_client)
        assert self.monitor._margin_check_failure_count == 1
        assert result["sufficient"] is True  # リトライ内は取引続行

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_api_auth_error_max_retries(self, mock_threshold):
        """API認証エラーリトライ上限到達."""
        mock_threshold.side_effect = lambda key, default: {
            "balance_alert.enabled": True,
            "balance_alert.min_required_margin": 14000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(side_effect=Exception("API エラー: 20001"))

        self.monitor._margin_check_failure_count = 2  # あと1回で上限
        result = await self.monitor.validate_margin_balance(mode="live", bitbank_client=mock_client)
        assert result["sufficient"] is False
        assert result.get("error") == "margin_check_failure_auth_error"

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_network_error_no_count(self, mock_threshold):
        """ネットワークエラーはカウントしない."""
        mock_threshold.side_effect = lambda key, default: {
            "balance_alert.enabled": True,
            "balance_alert.min_required_margin": 14000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(side_effect=Exception("Connection timeout"))

        self.monitor._margin_check_failure_count = 0
        result = await self.monitor.validate_margin_balance(mode="live", bitbank_client=mock_client)
        assert self.monitor._margin_check_failure_count == 0
        assert result["sufficient"] is True

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_balance_alert_disabled(self, mock_threshold):
        """残高アラート無効時."""
        mock_threshold.side_effect = lambda key, default: {
            "balance_alert.enabled": False,
        }.get(key, default)

        mock_client = Mock()
        result = await self.monitor.validate_margin_balance(mode="live", bitbank_client=mock_client)
        assert result["sufficient"] is True

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_retry_counter_reset(self, mock_threshold):
        """成功時にリトライカウンターリセット."""
        mock_threshold.side_effect = lambda key, default: {
            "balance_alert.enabled": True,
            "balance_alert.min_required_margin": 14000.0,
        }.get(key, default)

        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"available_balance": 500000})

        self.monitor._margin_check_failure_count = 2
        result = await self.monitor.validate_margin_balance(mode="live", bitbank_client=mock_client)
        assert self.monitor._margin_check_failure_count == 0
        assert result["sufficient"] is True
