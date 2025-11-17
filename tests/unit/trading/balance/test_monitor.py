"""
残高・保証金監視サービステスト - Phase 38リファクタリング

BalanceMonitorの包括的テストスイート。
Phase 28/29保証金維持率監視システムの完全テスト。

テスト範囲:
- 保証金維持率計算（API優先・フォールバック）
- 直接計算ロジック（正常・極小値・異常値）
- API取得（成功・失敗）
- 維持率判定（SAFE/CAUTION/WARNING/CRITICAL）
- 保証金分析
- 新規ポジション追加後の維持率予測
- 推奨アクション生成
- サマリー生成・トレンド分析
- ユーザー警告判定
- 残高充足性チェック
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
        assert isinstance(self.monitor.margin_history, list)
        assert len(self.monitor.margin_history) == 0

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


class TestMarginAnalysis:
    """保証金分析テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_analyze_current_margin(self, mock_threshold, mock_backtest):
        """現在の保証金状況分析テスト."""
        mock_backtest.return_value = True
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        margin_data = await self.monitor.analyze_current_margin(
            balance_jpy=1000000, position_value_jpy=500000
        )

        assert isinstance(margin_data, MarginData)
        assert margin_data.current_balance == 1000000
        assert margin_data.position_value_jpy == 500000
        assert margin_data.margin_ratio == pytest.approx(200.0, rel=0.01)
        assert margin_data.status == MarginStatus.SAFE
        assert len(margin_data.message) > 0
        assert isinstance(margin_data.timestamp, datetime)

        # 履歴に追加されていることを確認
        assert len(self.monitor.margin_history) == 1

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_margin_history_management(self, mock_threshold, mock_backtest):
        """履歴管理テスト（最大100件保持）."""
        mock_backtest.return_value = True
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
            "margin.max_history_count": 10,
        }.get(key, default)

        # 15件追加して最大10件に制限されることを確認
        for i in range(15):
            await self.monitor.analyze_current_margin(
                balance_jpy=1000000 + i * 1000, position_value_jpy=500000
            )

        assert len(self.monitor.margin_history) == 10
        # 最新のデータが保持されている
        assert self.monitor.margin_history[-1].current_balance == 1014000


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


class TestMarginSummary:
    """サマリー生成・トレンド分析テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    def test_get_margin_summary_no_data(self):
        """データなし時のサマリーテスト."""
        summary = self.monitor.get_margin_summary()

        assert summary["status"] == "no_data"
        assert "message" in summary

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_get_margin_summary_with_data(self, mock_threshold, mock_backtest):
        """データあり時のサマリーテスト."""
        mock_backtest.return_value = True
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        # データ追加
        await self.monitor.analyze_current_margin(balance_jpy=1000000, position_value_jpy=500000)

        summary = self.monitor.get_margin_summary()

        assert "current_status" in summary
        assert summary["current_status"]["margin_ratio"] == pytest.approx(200.0, rel=0.01)
        assert "trend" in summary
        assert "history_count" in summary
        assert summary["history_count"] == 1
        assert "recommendations" in summary

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_margin_trend_improving(self, mock_threshold, mock_backtest):
        """維持率改善トレンドテスト."""
        mock_backtest.return_value = True
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        # 維持率が改善するデータ追加
        await self.monitor.analyze_current_margin(
            balance_jpy=1000000, position_value_jpy=1000000
        )  # 100%
        await self.monitor.analyze_current_margin(
            balance_jpy=1000000, position_value_jpy=500000
        )  # 200%

        summary = self.monitor.get_margin_summary()
        assert summary["trend"] == "improving"

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_margin_trend_declining(self, mock_threshold, mock_backtest):
        """維持率悪化トレンドテスト."""
        mock_backtest.return_value = True
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        # 維持率が悪化するデータ追加
        await self.monitor.analyze_current_margin(
            balance_jpy=1000000, position_value_jpy=500000
        )  # 200%
        await self.monitor.analyze_current_margin(
            balance_jpy=1000000, position_value_jpy=1000000
        )  # 100%

        summary = self.monitor.get_margin_summary()
        assert summary["trend"] == "declining"

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    @patch("src.trading.balance.monitor.get_threshold")
    async def test_margin_trend_stable(self, mock_threshold, mock_backtest):
        """維持率安定トレンドテスト."""
        mock_backtest.return_value = True
        mock_threshold.side_effect = lambda key, default: {
            "margin.thresholds.safe": 200.0,
            "margin.thresholds.caution": 150.0,
            "margin.thresholds.warning": 100.0,
        }.get(key, default)

        # 同じ維持率のデータ追加
        await self.monitor.analyze_current_margin(balance_jpy=1000000, position_value_jpy=500000)
        await self.monitor.analyze_current_margin(balance_jpy=1000000, position_value_jpy=500000)

        summary = self.monitor.get_margin_summary()
        assert summary["trend"] == "stable"


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


class TestBalanceSufficiency:
    """残高充足性チェックテスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    async def test_check_balance_sufficiency_sufficient(self, mock_backtest):
        """残高充足テスト."""
        mock_backtest.return_value = True

        result = await self.monitor.check_balance_sufficiency(
            required_amount=500000, current_balance=1000000
        )

        assert result["sufficient"] is True
        assert result["current_balance"] == 1000000
        assert result["available_balance"] == 1000000
        assert result["required_amount"] == 500000
        assert result["shortage"] == 0

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    async def test_check_balance_sufficiency_insufficient(self, mock_backtest):
        """残高不足テスト."""
        mock_backtest.return_value = True

        result = await self.monitor.check_balance_sufficiency(
            required_amount=1500000, current_balance=1000000
        )

        assert result["sufficient"] is False
        assert result["shortage"] == 500000

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    async def test_check_balance_sufficiency_with_api(self, mock_backtest):
        """API利用可能残高取得テスト."""
        mock_backtest.return_value = False
        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(return_value={"available_balance": 800000})

        result = await self.monitor.check_balance_sufficiency(
            required_amount=500000, current_balance=1000000, bitbank_client=mock_client
        )

        assert result["sufficient"] is True
        assert result["available_balance"] == 800000

    @pytest.mark.asyncio
    @patch("src.trading.balance.monitor.is_backtest_mode")
    async def test_check_balance_sufficiency_api_error(self, mock_backtest):
        """API取得失敗時のフォールバックテスト."""
        mock_backtest.return_value = False
        mock_client = Mock()
        mock_client.fetch_margin_status = AsyncMock(side_effect=Exception("API error"))

        result = await self.monitor.check_balance_sufficiency(
            required_amount=500000, current_balance=1000000, bitbank_client=mock_client
        )

        # エラー時は現在残高を使用
        assert result["available_balance"] == 1000000


class TestMarginRecommendations:
    """保証金推奨アクションテスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.monitor = BalanceMonitor()

    def test_get_margin_recommendations_critical(self):
        """CRITICAL状態の推奨アクションテスト."""
        margin_data = MarginData(
            current_balance=500000,
            position_value_jpy=1000000,
            margin_ratio=50.0,
            status=MarginStatus.CRITICAL,
            message="",
            timestamp=datetime.now(),
        )

        recommendations = self.monitor._get_margin_recommendations(margin_data)

        assert len(recommendations) > 0
        assert any("緊急" in rec or "追証" in rec for rec in recommendations)
        assert any("入金" in rec for rec in recommendations)
        assert any("ポジション" in rec or "縮小" in rec for rec in recommendations)

    def test_get_margin_recommendations_warning(self):
        """WARNING状態の推奨アクションテスト."""
        margin_data = MarginData(
            current_balance=1000000,
            position_value_jpy=900000,
            margin_ratio=111.0,
            status=MarginStatus.WARNING,
            message="",
            timestamp=datetime.now(),
        )

        recommendations = self.monitor._get_margin_recommendations(margin_data)

        assert len(recommendations) > 0
        assert any("低下" in rec or "維持率" in rec for rec in recommendations)
        assert any("入金" in rec for rec in recommendations)

    def test_get_margin_recommendations_caution(self):
        """CAUTION状態の推奨アクションテスト."""
        margin_data = MarginData(
            current_balance=1000000,
            position_value_jpy=600000,
            margin_ratio=166.0,
            status=MarginStatus.CAUTION,
            message="",
            timestamp=datetime.now(),
        )

        recommendations = self.monitor._get_margin_recommendations(margin_data)

        assert len(recommendations) > 0
        assert any("注意" in rec or "維持率" in rec for rec in recommendations)

    def test_get_margin_recommendations_safe(self):
        """SAFE状態の推奨アクションテスト."""
        margin_data = MarginData(
            current_balance=1000000,
            position_value_jpy=400000,
            margin_ratio=250.0,
            status=MarginStatus.SAFE,
            message="",
            timestamp=datetime.now(),
        )

        recommendations = self.monitor._get_margin_recommendations(margin_data)

        assert len(recommendations) > 0
        assert any("安全" in rec for rec in recommendations)
        assert any("通常" in rec or "可能" in rec for rec in recommendations)
