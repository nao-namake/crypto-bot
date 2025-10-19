"""
PositionLimits テストスイート - Phase 38リファクタリング

ポジション制限管理機能のテスト。

テスト範囲:
- check_limits(): 統合制限チェック
- _check_minimum_balance(): 最小資金要件チェック
- _check_cooldown(): クールダウンチェック（Phase 31.1柔軟判定）
- _check_max_positions(): 最大ポジション数チェック
- _check_capital_usage(): 資金利用率チェック
- _check_daily_trades(): 日次取引回数チェック
- _check_trade_size(): 取引サイズチェック（ML信頼度連動）
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading.core import RiskDecision, TradeEvaluation
from src.trading.position.limits import PositionLimits


@pytest.fixture
def limits():
    """PositionLimits fixture"""
    return PositionLimits()


@pytest.fixture
def sample_evaluation():
    """TradeEvaluation fixture"""
    return TradeEvaluation(
        decision=RiskDecision.APPROVED,
        side="buy",
        risk_score=0.1,
        position_size=0.001,
        stop_loss=13700000.0,
        take_profit=14300000.0,
        confidence_level=0.75,
        warnings=[],
        denial_reasons=[],
        evaluation_timestamp=datetime.now(),
        kelly_recommendation=0.05,
        drawdown_status="normal",
        anomaly_alerts=[],
        market_conditions={"market_data": {}},
    )


class TestCheckMinimumBalance:
    """_check_minimum_balance() テスト"""

    @patch("src.trading.position.limits.get_threshold")
    def test_sufficient_balance_dynamic_disabled(self, mock_threshold, limits):
        """十分な残高（動的サイジング無効）"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_account_balance": 10000.0,
            "position_management.dynamic_position_sizing.enabled": False,
        }.get(key, default)

        result = limits._check_minimum_balance(50000.0)

        assert result["allowed"] is True
        assert "資金要件OK" in result["reason"]

    @patch("src.trading.position.limits.get_threshold")
    def test_insufficient_balance_dynamic_disabled(self, mock_threshold, limits):
        """残高不足（動的サイジング無効）"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_account_balance": 10000.0,
            "position_management.dynamic_position_sizing.enabled": False,
        }.get(key, default)

        result = limits._check_minimum_balance(5000.0)

        assert result["allowed"] is False
        assert "最小運用資金要件" in result["reason"]
        assert "5000" in result["reason"]

    @patch("src.trading.position.limits.get_threshold")
    def test_sufficient_balance_dynamic_enabled(self, mock_threshold, limits):
        """動的サイジング有効・最小ロット取引可能"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.dynamic_position_sizing.enabled": True,
            "position_management.min_trade_size": 0.0001,
            "trading.fallback_btc_jpy": 10000000.0,
        }.get(key, default)

        # 0.0001 * 10,000,000 * 1.1 = 1,100円必要
        result = limits._check_minimum_balance(2000.0)

        assert result["allowed"] is True

    @patch("src.trading.position.limits.get_threshold")
    def test_insufficient_balance_dynamic_enabled(self, mock_threshold, limits):
        """動的サイジング有効・最小ロット取引不可"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.dynamic_position_sizing.enabled": True,
            "position_management.min_trade_size": 0.0001,
            "trading.fallback_btc_jpy": 10000000.0,
        }.get(key, default)

        # 0.0001 * 10,000,000 * 1.1 = 1,100円必要
        result = limits._check_minimum_balance(500.0)

        assert result["allowed"] is False
        assert "最小ロット取引に必要な資金" in result["reason"]


class TestCheckCooldown:
    """_check_cooldown() テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.position.limits.get_threshold")
    async def test_no_last_order_time(self, mock_threshold, limits, sample_evaluation):
        """最終注文時刻なし"""
        result = await limits._check_cooldown(sample_evaluation, None)

        assert result["allowed"] is True
        assert "クールダウンなし" in result["reason"]

    @pytest.mark.asyncio
    @patch("src.trading.position.limits.get_threshold")
    async def test_cooldown_zero(self, mock_threshold, limits, sample_evaluation):
        """クールダウン0分設定"""
        mock_threshold.return_value = 0

        last_order_time = datetime.now() - timedelta(minutes=5)
        result = await limits._check_cooldown(sample_evaluation, last_order_time)

        assert result["allowed"] is True

    @pytest.mark.asyncio
    @patch("src.trading.position.limits.get_threshold")
    async def test_cooldown_period_passed(self, mock_threshold, limits, sample_evaluation):
        """クールダウン期間経過"""
        mock_threshold.return_value = 30

        last_order_time = datetime.now() - timedelta(minutes=35)
        result = await limits._check_cooldown(sample_evaluation, last_order_time)

        assert result["allowed"] is True
        assert "クールダウンOK" in result["reason"]

    @pytest.mark.asyncio
    @patch("src.trading.position.limits.get_threshold")
    async def test_cooldown_period_active(self, mock_threshold, limits, sample_evaluation):
        """クールダウン期間中（柔軟判定なし）"""
        mock_threshold.return_value = 30

        last_order_time = datetime.now() - timedelta(minutes=10)
        result = await limits._check_cooldown(sample_evaluation, last_order_time)

        assert result["allowed"] is False
        assert "クールダウン期間中" in result["reason"]
        assert "残り" in result["reason"]

    @pytest.mark.asyncio
    @patch("src.trading.position.limits.get_threshold")
    async def test_cooldown_skipped_strong_trend(self, mock_threshold, limits, sample_evaluation):
        """Phase 31.1: 強トレンド時クールダウンスキップ"""
        mock_threshold.return_value = 30

        # CooldownManagerをモック注入
        mock_cooldown_manager = Mock()
        mock_cooldown_manager.should_apply_cooldown = AsyncMock(return_value=False)
        limits.inject_cooldown_manager(mock_cooldown_manager)

        last_order_time = datetime.now() - timedelta(minutes=10)
        result = await limits._check_cooldown(sample_evaluation, last_order_time)

        assert result["allowed"] is True
        assert "クールダウンOK" in result["reason"]

    @pytest.mark.asyncio
    @patch("src.trading.position.limits.get_threshold")
    async def test_cooldown_applied_weak_trend(self, mock_threshold, limits, sample_evaluation):
        """Phase 31.1: 弱トレンド時クールダウン適用"""
        mock_threshold.return_value = 30

        # CooldownManagerをモック注入
        mock_cooldown_manager = Mock()
        mock_cooldown_manager.should_apply_cooldown = AsyncMock(return_value=True)
        limits.inject_cooldown_manager(mock_cooldown_manager)

        last_order_time = datetime.now() - timedelta(minutes=10)
        result = await limits._check_cooldown(sample_evaluation, last_order_time)

        assert result["allowed"] is False
        assert "クールダウン期間中" in result["reason"]


class TestCheckMaxPositions:
    """_check_max_positions() テスト"""

    @patch("src.trading.position.limits.get_threshold")
    def test_within_limit(self, mock_threshold, limits):
        """制限内"""
        mock_threshold.return_value = 3

        virtual_positions = [{"order_id": "1"}, {"order_id": "2"}]
        result = limits._check_max_positions(virtual_positions)

        assert result["allowed"] is True
        assert "ポジション数OK" in result["reason"]

    @patch("src.trading.position.limits.get_threshold")
    def test_at_limit(self, mock_threshold, limits):
        """制限到達"""
        mock_threshold.return_value = 3

        virtual_positions = [{"order_id": "1"}, {"order_id": "2"}, {"order_id": "3"}]
        result = limits._check_max_positions(virtual_positions)

        assert result["allowed"] is False
        assert "最大ポジション数制限" in result["reason"]
        assert "3個" in result["reason"]

    @patch("src.trading.position.limits.get_threshold")
    def test_empty_positions(self, mock_threshold, limits):
        """ポジションなし"""
        mock_threshold.return_value = 3

        result = limits._check_max_positions([])

        assert result["allowed"] is True


class TestCheckCapitalUsage:
    """_check_capital_usage() テスト"""

    @patch("src.core.config.load_config")
    @patch("src.trading.position.limits.get_threshold")
    def test_capital_usage_within_limit(self, mock_threshold, mock_load_config, limits):
        """資金利用率制限内"""
        mock_threshold.return_value = 0.3
        mock_config = Mock()
        mock_config.mode_balances = {
            "paper": {"initial_balance": 10000.0},
            "live": {"initial_balance": 100000.0},
        }
        mock_load_config.return_value = mock_config

        # 10,000円初期残高、8,000円現在残高 = 20%使用
        result = limits._check_capital_usage(8000.0)

        assert result["allowed"] is True
        assert "資金利用率OK" in result["reason"]

    @patch("src.core.config.load_config")
    @patch("src.trading.position.limits.get_threshold")
    def test_capital_usage_at_limit(self, mock_threshold, mock_load_config, limits):
        """資金利用率制限到達"""
        mock_threshold.return_value = 0.3
        mock_config = Mock()
        mock_config.mode_balances = {
            "paper": {"initial_balance": 10000.0},
            "live": {"initial_balance": 100000.0},
        }
        mock_load_config.return_value = mock_config

        # 10,000円初期残高、6,800円現在残高 = 32%使用
        result = limits._check_capital_usage(6800.0)

        assert result["allowed"] is False
        assert "資金利用率制限" in result["reason"]

    @patch("src.core.config.load_config")
    @patch("src.trading.position.limits.get_threshold")
    def test_capital_usage_live_mode_detection(self, mock_threshold, mock_load_config, limits):
        """ライブモード検出"""
        mock_threshold.return_value = 0.3
        mock_config = Mock()
        mock_config.mode_balances = {
            "paper": {"initial_balance": 10000.0},
            "live": {"initial_balance": 100000.0},
        }
        mock_load_config.return_value = mock_config

        # 100,000円初期残高、95,000円現在残高 = 5%使用
        result = limits._check_capital_usage(95000.0)

        assert result["allowed"] is True


class TestCheckDailyTrades:
    """_check_daily_trades() テスト"""

    @patch("src.trading.position.limits.get_threshold")
    def test_daily_trades_within_limit(self, mock_threshold, limits):
        """日次取引回数制限内"""
        mock_threshold.return_value = 20

        virtual_positions = [
            {"timestamp": datetime.now() - timedelta(hours=1)},
            {"timestamp": datetime.now() - timedelta(hours=2)},
        ]
        result = limits._check_daily_trades(virtual_positions)

        assert result["allowed"] is True

    @patch("src.trading.position.limits.get_threshold")
    def test_daily_trades_at_limit(self, mock_threshold, limits):
        """日次取引回数制限到達"""
        mock_threshold.return_value = 5

        # 確実に今日の日付内に収まるように12時を基準にする（UTC/JST境界対策）
        today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        virtual_positions = [{"timestamp": today - timedelta(minutes=i * 30)} for i in range(5)]

        result = limits._check_daily_trades(virtual_positions)

        assert result["allowed"] is False
        assert "日次取引回数制限" in result["reason"]

    @patch("src.trading.position.limits.get_threshold")
    def test_daily_trades_cross_day(self, mock_threshold, limits):
        """日付跨ぎ（昨日の取引はカウントしない）"""
        mock_threshold.return_value = 5

        today = datetime.now()
        yesterday = today - timedelta(days=1)

        virtual_positions = [
            {"timestamp": today - timedelta(hours=1)},
            {"timestamp": today - timedelta(hours=2)},
            {"timestamp": yesterday - timedelta(hours=1)},
            {"timestamp": yesterday - timedelta(hours=2)},
        ]

        result = limits._check_daily_trades(virtual_positions)

        # 今日は2件のみ
        assert result["allowed"] is True

    @patch("src.trading.position.limits.get_threshold")
    def test_daily_trades_string_timestamp(self, mock_threshold, limits):
        """文字列timestamp処理"""
        mock_threshold.return_value = 10

        virtual_positions = [
            {"timestamp": datetime.now().isoformat()},
            {"timestamp": (datetime.now() - timedelta(hours=1)).isoformat()},
        ]

        result = limits._check_daily_trades(virtual_positions)

        assert result["allowed"] is True


class TestCheckTradeSize:
    """_check_trade_size() テスト"""

    @patch("src.trading.position.limits.get_threshold")
    def test_trade_size_low_confidence(self, mock_threshold, limits, sample_evaluation):
        """低信頼度（3%制限）"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_trade_size": 0.0001,
            "trading.fallback_btc_jpy": 10000000.0,
            "position_management.max_position_ratio_per_trade.low_confidence": 0.03,
            "position_management.max_position_ratio_per_trade.enforce_minimum": True,
        }.get(key, default)

        sample_evaluation.confidence_level = 0.55
        sample_evaluation.position_size = 0.0002  # 2,000円分

        result = limits._check_trade_size(sample_evaluation, 100000.0)

        # 100,000 * 0.03 = 3,000円まで許可
        assert result["allowed"] is True

    @patch("src.trading.position.limits.get_threshold")
    def test_trade_size_medium_confidence(self, mock_threshold, limits, sample_evaluation):
        """中信頼度（5%制限）"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_trade_size": 0.0001,
            "trading.fallback_btc_jpy": 10000000.0,
            "position_management.max_position_ratio_per_trade.medium_confidence": 0.05,
            "position_management.max_position_ratio_per_trade.enforce_minimum": True,
        }.get(key, default)

        sample_evaluation.confidence_level = 0.70
        sample_evaluation.position_size = 0.0004  # 4,000円分

        result = limits._check_trade_size(sample_evaluation, 100000.0)

        # 100,000 * 0.05 = 5,000円まで許可
        assert result["allowed"] is True

    @patch("src.trading.position.limits.get_threshold")
    def test_trade_size_high_confidence(self, mock_threshold, limits, sample_evaluation):
        """高信頼度（10%制限）"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_trade_size": 0.0001,
            "trading.fallback_btc_jpy": 10000000.0,
            "position_management.max_position_ratio_per_trade.high_confidence": 0.10,
            "position_management.max_position_ratio_per_trade.enforce_minimum": True,
        }.get(key, default)

        sample_evaluation.confidence_level = 0.80
        sample_evaluation.position_size = 0.0008  # 8,000円分

        result = limits._check_trade_size(sample_evaluation, 100000.0)

        # 100,000 * 0.10 = 10,000円まで許可
        assert result["allowed"] is True

    @patch("src.trading.position.limits.get_threshold")
    def test_trade_size_exceeds_limit(self, mock_threshold, limits, sample_evaluation):
        """取引サイズ超過"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_trade_size": 0.0001,
            "trading.fallback_btc_jpy": 10000000.0,
            "position_management.max_position_ratio_per_trade.high_confidence": 0.10,
            "position_management.max_position_ratio_per_trade.enforce_minimum": True,
        }.get(key, default)

        sample_evaluation.confidence_level = 0.80
        sample_evaluation.position_size = 0.0015  # 15,000円分

        result = limits._check_trade_size(sample_evaluation, 100000.0)

        # 100,000 * 0.10 = 10,000円まで → 超過
        assert result["allowed"] is False
        assert "最大金額制限" in result["reason"]

    @patch("src.trading.position.limits.get_threshold")
    def test_trade_size_minimum_lot_priority(self, mock_threshold, limits, sample_evaluation):
        """最小ロット優先適用"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_trade_size": 0.001,  # 10,000円分
            "trading.fallback_btc_jpy": 10000000.0,
            "position_management.max_position_ratio_per_trade.low_confidence": 0.03,  # 3%
            "position_management.max_position_ratio_per_trade.enforce_minimum": True,
        }.get(key, default)

        sample_evaluation.confidence_level = 0.50
        sample_evaluation.position_size = 0.001  # 10,000円分（最小ロット）

        # 残高20,000円 * 0.03 = 600円 < 10,000円（最小ロット）
        result = limits._check_trade_size(sample_evaluation, 20000.0)

        # 最小ロット優先で許可
        assert result["allowed"] is True
        assert "最小ロット優先" in result["reason"]

    @patch("src.trading.position.limits.get_threshold")
    def test_trade_size_enforce_minimum_disabled(self, mock_threshold, limits, sample_evaluation):
        """最小ロット優先無効"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_trade_size": 0.001,
            "trading.fallback_btc_jpy": 10000000.0,
            "position_management.max_position_ratio_per_trade.low_confidence": 0.03,
            "position_management.max_position_ratio_per_trade.enforce_minimum": False,
        }.get(key, default)

        sample_evaluation.confidence_level = 0.50
        sample_evaluation.position_size = 0.001  # 10,000円分

        # 残高20,000円 * 0.03 = 600円 < 10,000円
        result = limits._check_trade_size(sample_evaluation, 20000.0)

        # 制限により拒否
        assert result["allowed"] is False


class TestCheckLimits:
    """check_limits() 統合テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.position.limits.get_threshold")
    async def test_minimum_balance_check_fails(self, mock_threshold, limits, sample_evaluation):
        """最小残高チェック失敗"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_account_balance": 10000.0,
            "position_management.dynamic_position_sizing.enabled": False,
        }.get(key, default)

        result = await limits.check_limits(
            evaluation=sample_evaluation,
            virtual_positions=[],
            last_order_time=None,
            current_balance=5000.0,
        )

        assert result["allowed"] is False
        assert "最小運用資金要件" in result["reason"]

    @pytest.mark.asyncio
    @patch("src.trading.position.limits.get_threshold")
    async def test_max_positions_check_fails(self, mock_threshold, limits, sample_evaluation):
        """最大ポジション数チェック失敗"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.min_account_balance": 10000.0,
            "position_management.dynamic_position_sizing.enabled": False,
            "position_management.cooldown_minutes": 0,
            "position_management.max_open_positions": 2,
        }.get(key, default)

        virtual_positions = [{"order_id": "1"}, {"order_id": "2"}]

        result = await limits.check_limits(
            evaluation=sample_evaluation,
            virtual_positions=virtual_positions,
            last_order_time=None,
            current_balance=50000.0,
        )

        assert result["allowed"] is False
        assert "最大ポジション数制限" in result["reason"]

    @pytest.mark.asyncio
    async def test_exception_handling(self, limits, sample_evaluation):
        """例外ハンドリング"""
        # 不正なevaluation（position_size未設定）
        sample_evaluation.position_size = None

        result = await limits.check_limits(
            evaluation=sample_evaluation,
            virtual_positions=[],
            last_order_time=None,
            current_balance=50000.0,
        )

        assert result["allowed"] is False
        assert "制限チェック処理エラー" in result["reason"]


class TestInitialization:
    """初期化テスト"""

    def test_limits_initialization(self, limits):
        """PositionLimits初期化"""
        assert hasattr(limits, "logger")
        assert hasattr(limits, "cooldown_manager")
        assert limits.cooldown_manager is None

    def test_inject_cooldown_manager(self, limits):
        """CooldownManager注入"""
        mock_cooldown_manager = Mock()
        limits.inject_cooldown_manager(mock_cooldown_manager)

        assert limits.cooldown_manager is mock_cooldown_manager
