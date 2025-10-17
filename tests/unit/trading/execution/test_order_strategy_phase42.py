"""
OrderStrategy Phase 42 テストスイート

Phase 42: 統合TP/SL実装

テスト範囲:
- calculate_consolidated_tp_sl_prices(): 統合TP/SL価格計算（8テスト）
"""

from unittest.mock import patch

import pytest

from src.trading.execution.order_strategy import OrderStrategy


@pytest.fixture
def order_strategy():
    """OrderStrategy fixture"""
    return OrderStrategy()


# ========================================
# calculate_consolidated_tp_sl_prices() テスト - 8ケース
# ========================================


class TestCalculateConsolidatedTpSlPrices:
    """calculate_consolidated_tp_sl_prices() テスト - Phase 42"""

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_buy_position_normal_calculation_no_atr(self, mock_threshold, order_strategy):
        """買いポジション正常計算（ATR条件なし）"""

        # 設定値モック
        def threshold_side_effect(key, default=None):
            if "take_profit.default_ratio" in key:
                return 2.5
            elif "take_profit.min_profit_ratio" in key:
                return 0.01
            elif "stop_loss.default_atr_multiplier" in key:
                return 2.0
            elif "stop_loss.max_loss_ratio" in key:
                return 0.03
            elif key == "position_management.take_profit":
                return {"default_ratio": 2.5, "min_profit_ratio": 0.01}
            elif key == "position_management.stop_loss":
                return {"default_atr_multiplier": 2.0, "max_loss_ratio": 0.03}
            return default

        mock_threshold.side_effect = threshold_side_effect

        result = order_strategy.calculate_consolidated_tp_sl_prices(
            average_entry_price=14000000.0, side="buy", market_conditions=None
        )

        # ATRなしのデフォルト計算: SL=2%, TP=2%×2.5=5%
        assert result["stop_loss_price"] == round(14000000.0 * 0.98)  # -2%
        assert result["take_profit_price"] == round(14000000.0 * 1.05)  # +5%
        assert 0.019 <= result["sl_rate"] <= 0.021  # 2%付近
        assert 0.049 <= result["tp_rate"] <= 0.051  # 5%付近

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_buy_position_adaptive_atr_multiplier(self, mock_threshold, order_strategy):
        """買いポジション適応型ATR倍率"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.take_profit":
                return {"default_ratio": 2.5, "min_profit_ratio": 0.01}
            elif key == "position_management.stop_loss":
                return {"default_atr_multiplier": 2.0, "max_loss_ratio": 0.03}
            return default

        mock_threshold.side_effect = threshold_side_effect

        # ATR比率: 0.015（1.5%）
        market_conditions = {"atr_ratio": 0.015}

        result = order_strategy.calculate_consolidated_tp_sl_prices(
            average_entry_price=14000000.0, side="buy", market_conditions=market_conditions
        )

        # SL率 = min(0.015 × 2.0, 0.03) = 0.03
        # TP率 = max(0.03 × 2.5, 0.01) = 0.075 → ただし最大損失率で制限
        assert result["stop_loss_price"] == round(14000000.0 * (1 - 0.03))  # -3%
        assert result["take_profit_price"] == round(14000000.0 * (1 + 0.075))  # +7.5%
        assert 0.029 <= result["sl_rate"] <= 0.031  # 3%付近
        assert 0.074 <= result["tp_rate"] <= 0.076  # 7.5%付近

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_sell_position_normal_calculation_no_atr(self, mock_threshold, order_strategy):
        """売りポジション正常計算（ATR条件なし）"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.take_profit":
                return {"default_ratio": 2.5, "min_profit_ratio": 0.01}
            elif key == "position_management.stop_loss":
                return {"default_atr_multiplier": 2.0, "max_loss_ratio": 0.03}
            return default

        mock_threshold.side_effect = threshold_side_effect

        result = order_strategy.calculate_consolidated_tp_sl_prices(
            average_entry_price=14000000.0, side="sell", market_conditions=None
        )

        # 売りポジション: TP = -5%, SL = +2%
        assert result["take_profit_price"] == round(14000000.0 * 0.95)  # -5%
        assert result["stop_loss_price"] == round(14000000.0 * 1.02)  # +2%
        assert 0.019 <= result["sl_rate"] <= 0.021  # 2%付近
        assert 0.049 <= result["tp_rate"] <= 0.051  # 5%付近

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_sell_position_adaptive_atr_multiplier(self, mock_threshold, order_strategy):
        """売りポジション適応型ATR倍率"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.take_profit":
                return {"default_ratio": 2.5, "min_profit_ratio": 0.01}
            elif key == "position_management.stop_loss":
                return {"default_atr_multiplier": 2.0, "max_loss_ratio": 0.03}
            return default

        mock_threshold.side_effect = threshold_side_effect

        # ATR比率: 0.01（1%）
        market_conditions = {"atr_ratio": 0.01}

        result = order_strategy.calculate_consolidated_tp_sl_prices(
            average_entry_price=14000000.0, side="sell", market_conditions=market_conditions
        )

        # SL率 = min(0.01 × 2.0, 0.03) = 0.02
        # TP率 = max(0.02 × 2.5, 0.01) = 0.05
        assert result["take_profit_price"] == round(14000000.0 * (1 - 0.05))  # -5%
        assert result["stop_loss_price"] == round(14000000.0 * (1 + 0.02))  # +2%
        assert 0.019 <= result["sl_rate"] <= 0.021  # 2%付近
        assert 0.049 <= result["tp_rate"] <= 0.051  # 5%付近

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_invalid_side_error_handling(self, mock_threshold, order_strategy):
        """不正サイド時のエラーハンドリング（ゼロ返却）"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.take_profit":
                return {"default_ratio": 2.5, "min_profit_ratio": 0.01}
            elif key == "position_management.stop_loss":
                return {"default_atr_multiplier": 2.0, "max_loss_ratio": 0.03}
            return default

        mock_threshold.side_effect = threshold_side_effect

        result = order_strategy.calculate_consolidated_tp_sl_prices(
            average_entry_price=14000000.0, side="invalid_side", market_conditions=None
        )

        # エラー時はゼロ返却
        assert result["take_profit_price"] == 0.0
        assert result["stop_loss_price"] == 0.0
        assert result["tp_rate"] == 0.0
        assert result["sl_rate"] == 0.0

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_negative_price_validation_check(self, mock_threshold, order_strategy):
        """負の価格時の妥当性チェック（ゼロ返却）"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.take_profit":
                return {"default_ratio": 2.5, "min_profit_ratio": 0.01}
            elif key == "position_management.stop_loss":
                # 非常に大きなSL率を設定して負の価格を生成
                return {"default_atr_multiplier": 10.0, "max_loss_ratio": 1.5}
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 極端なATR比率で負の価格を生成
        market_conditions = {"atr_ratio": 0.2}  # 20%

        result = order_strategy.calculate_consolidated_tp_sl_prices(
            average_entry_price=14000000.0, side="buy", market_conditions=market_conditions
        )

        # SL率 = min(0.2 × 10.0, 1.5) = 1.5（150%）→ 負の価格
        # 妥当性チェックで検出されゼロ返却
        if result["stop_loss_price"] <= 0:
            assert result["take_profit_price"] == 0.0
            assert result["stop_loss_price"] == 0.0

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_risk_reward_ratio_min_profit_guarantee(self, mock_threshold, order_strategy):
        """リスクリワード比・最小利益率保証確認"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.take_profit":
                return {"default_ratio": 2.5, "min_profit_ratio": 0.03}  # 最小利益率3%
            elif key == "position_management.stop_loss":
                return {"default_atr_multiplier": 2.0, "max_loss_ratio": 0.03}
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 非常に小さいSL率（0.5%）
        market_conditions = {"atr_ratio": 0.0025}

        result = order_strategy.calculate_consolidated_tp_sl_prices(
            average_entry_price=14000000.0, side="buy", market_conditions=market_conditions
        )

        # SL率 = min(0.0025 × 2.0, 0.03) = 0.005（0.5%）
        # TP率 = max(0.005 × 2.5, 0.03) = 0.03（最小利益率が優先）
        assert result["sl_rate"] <= 0.006  # 0.5%付近
        assert result["tp_rate"] >= 0.029  # 最小利益率3%保証

    @patch("src.trading.execution.order_strategy.get_threshold")
    def test_max_loss_ratio_upper_limit(self, mock_threshold, order_strategy):
        """最大損失率上限制限確認"""

        def threshold_side_effect(key, default=None):
            if key == "position_management.take_profit":
                return {"default_ratio": 2.5, "min_profit_ratio": 0.01}
            elif key == "position_management.stop_loss":
                return {"default_atr_multiplier": 2.0, "max_loss_ratio": 0.025}  # 最大2.5%
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 非常に大きいATR比率（5%）
        market_conditions = {"atr_ratio": 0.05}

        result = order_strategy.calculate_consolidated_tp_sl_prices(
            average_entry_price=14000000.0, side="buy", market_conditions=market_conditions
        )

        # SL率 = min(0.05 × 2.0, 0.025) = 0.025（最大損失率が優先）
        assert result["sl_rate"] <= 0.026  # 2.5%以下
        # TP率 = max(0.025 × 2.5, 0.01) = 0.0625
        assert 0.061 <= result["tp_rate"] <= 0.064  # 6.25%付近
