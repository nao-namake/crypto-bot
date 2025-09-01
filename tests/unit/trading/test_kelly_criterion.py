"""
Kelly基準ポジションサイジングテスト

Phase 6リスク管理層の中核機能である
Kelly基準ポジションサイジングの包括的テスト。

テスト範囲:
- Kelly公式計算の正確性
- 取引履歴管理
- 安全制限の適用
- ダイナミックポジションサイジング
- エラーハンドリング.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.trading.risk_manager import (
    KellyCalculationResult,
    KellyCriterion,
    PositionSizeIntegrator,
    TradeResult,
)


class TestKellyCriterion:
    """Kelly基準ポジションサイジングテスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.kelly = KellyCriterion(
            max_position_ratio=0.03,
            safety_factor=0.5,
            min_trades_for_kelly=5,  # テスト用に小さく設定
        )

    def test_kelly_initialization(self):
        """Kelly基準初期化テスト."""
        assert self.kelly.max_position_ratio == 0.03
        assert self.kelly.safety_factor == 0.5
        assert self.kelly.min_trades_for_kelly == 5
        assert len(self.kelly.trade_history) == 0

    def test_kelly_formula_calculation(self):
        """Kelly公式計算テスト."""
        # 勝率60%, 平均利益1.5, 平均損失1.0の場合
        # Kelly = (1.5 * 0.6 - 0.4) / 1.5 = 0.3333...
        kelly_fraction = self.kelly.calculate_kelly_fraction(
            win_rate=0.6, avg_win=1.5, avg_loss=1.0
        )

        expected = (1.5 * 0.6 - 0.4) / 1.5
        assert abs(kelly_fraction - expected) < 0.001

    def test_kelly_formula_edge_cases(self):
        """Kelly公式エッジケーステスト."""
        # 勝率0%の場合
        kelly_zero = self.kelly.calculate_kelly_fraction(0.0, 1.0, 1.0)
        assert kelly_zero == 0.0

        # 勝率100%の場合（実装では無効パラメータとして扱われる）
        kelly_hundred = self.kelly.calculate_kelly_fraction(1.0, 1.0, 1.0)
        assert kelly_hundred == 0.0  # 実装の仕様により無効パラメータは0.0を返す

        # 負のKelly値になる場合（勝率が低すぎる）
        kelly_negative = self.kelly.calculate_kelly_fraction(0.3, 1.0, 1.0)
        assert kelly_negative == 0.0  # 負値は0にクリップされる

    def test_add_trade_result(self):
        """取引結果追加テスト."""
        # 利益取引追加
        self.kelly.add_trade_result(profit_loss=100.0, strategy="test_strategy", confidence=0.8)

        assert len(self.kelly.trade_history) == 1
        trade = self.kelly.trade_history[0]
        assert trade.profit_loss == 100.0
        assert trade.is_win == True
        assert trade.strategy == "test_strategy"
        assert trade.confidence == 0.8

        # 損失取引追加
        self.kelly.add_trade_result(profit_loss=-50.0, strategy="test_strategy2")

        assert len(self.kelly.trade_history) == 2
        trade2 = self.kelly.trade_history[1]
        assert trade2.profit_loss == -50.0
        assert trade2.is_win == False

    def test_calculate_from_history_insufficient_data(self):
        """履歴データ不足時のテスト."""
        # データなしの場合
        result = self.kelly.calculate_from_history()
        assert result is None

        # データ不足の場合（min_trades_for_kellyより少ない）
        for _i in range(3):
            self.kelly.add_trade_result(100.0, "test")

        result = self.kelly.calculate_from_history()
        assert result is None

    def test_calculate_from_history_sufficient_data(self):
        """履歴データ十分時のテスト."""
        # 勝率60%のデータを作成
        profits = [100, 150, 120]  # 3勝
        losses = [-80, -100]  # 2敗

        for profit in profits:
            self.kelly.add_trade_result(profit, "test")
        for loss in losses:
            self.kelly.add_trade_result(loss, "test")

        result = self.kelly.calculate_from_history()
        assert result is not None
        assert isinstance(result, KellyCalculationResult)
        assert result.win_rate == 0.6  # 3/5
        assert result.kelly_fraction > 0
        assert result.recommended_position_size <= self.kelly.max_position_ratio

    def test_calculate_optimal_size(self):
        """最適ポジションサイズ計算テスト."""
        # 履歴データなしの場合（保守的サイズ）
        size = self.kelly.calculate_optimal_size(ml_confidence=0.8)
        assert 0 < size <= self.kelly.max_position_ratio

        # 履歴データありの場合
        for i in range(10):
            profit = 100 if i < 6 else -80  # 60%勝率
            self.kelly.add_trade_result(profit, "test")

        size_with_history = self.kelly.calculate_optimal_size(ml_confidence=0.8)
        assert size_with_history > 0
        assert size_with_history <= self.kelly.max_position_ratio

    def test_dynamic_position_sizing(self):
        """ダイナミックポジションサイジングテスト."""
        balance = 1000000  # 100万円
        entry_price = 50000  # 5万円
        atr_value = 1000  # ATR 1000円
        ml_confidence = 0.8

        position_size, stop_loss = self.kelly.calculate_dynamic_position_size(
            balance=balance,
            entry_price=entry_price,
            atr_value=atr_value,
            ml_confidence=ml_confidence,
        )

        assert position_size > 0
        assert stop_loss > 0
        assert stop_loss < entry_price  # ロングポジションのストップロス

        # 安全制限チェック
        max_safe = balance * 0.3 / entry_price
        assert position_size <= max_safe

    def test_dynamic_position_sizing_high_volatility(self):
        """高ボラティリティ時のダイナミックサイジングテスト."""
        balance = 1000000
        entry_price = 50000
        high_atr = 5000  # 高ATR（高ボラティリティ）

        position_size, _ = self.kelly.calculate_dynamic_position_size(
            balance=balance, entry_price=entry_price, atr_value=high_atr, ml_confidence=0.8
        )

        # 低ボラティリティの場合と比較
        low_atr = 500  # 低ATR
        position_size_low_vol, _ = self.kelly.calculate_dynamic_position_size(
            balance=balance, entry_price=entry_price, atr_value=low_atr, ml_confidence=0.8
        )

        # 高ボラティリティ時はポジションサイズが小さくなる
        assert position_size < position_size_low_vol

    def test_fallback_position_size(self):
        """フォールバックポジションサイズテスト."""
        balance = 1000000
        entry_price = 50000

        # プライベートメソッドを直接テスト
        position_size, stop_loss = self.kelly._safe_fallback_position_size(balance, entry_price)

        assert position_size > 0
        assert stop_loss > 0
        assert stop_loss < entry_price

        # 最大制限チェック
        max_safe = balance * 0.1 / entry_price
        assert position_size <= max_safe

    def test_kelly_statistics(self):
        """Kelly統計情報テスト."""
        # データなしの場合
        stats = self.kelly.get_kelly_statistics()
        assert "status" in stats

        # データありの場合
        for i in range(10):
            profit = 100 if i < 7 else -80  # 70%勝率
            self.kelly.add_trade_result(profit, "test")

        stats_with_data = self.kelly.get_kelly_statistics()
        assert "current_kelly_fraction" in stats_with_data
        assert "recommended_size" in stats_with_data
        assert "win_rate" in stats_with_data
        assert stats_with_data["win_rate"] == 0.7

    def test_parameter_validation(self):
        """パラメータ検証テスト."""
        assert self.kelly.validate_kelly_parameters() == True

        # 無効なパラメータのKelly作成
        invalid_kelly = KellyCriterion(
            max_position_ratio=0.5,  # 無効（50%は大きすぎる）
            safety_factor=2.0,  # 無効（100%超）
            min_trades_for_kelly=200,  # 無効（大きすぎる）
        )

        assert invalid_kelly.validate_kelly_parameters() == False

    def test_error_handling(self):
        """エラーハンドリングテスト."""
        # 無効な勝率でのKelly計算
        kelly_invalid = self.kelly.calculate_kelly_fraction(
            win_rate=1.5, avg_win=1.0, avg_loss=1.0  # 無効（100%超）
        )
        assert kelly_invalid == 0.0

        # 無効な損失値
        kelly_invalid2 = self.kelly.calculate_kelly_fraction(
            win_rate=0.6, avg_win=1.0, avg_loss=0  # 無効（ゼロ除算）
        )
        assert kelly_invalid2 == 0.0

    def test_strategy_filtering(self):
        """戦略別フィルタリングテスト."""
        # 複数戦略の取引追加（勝ち負け両方を含む）
        for _i in range(4):
            self.kelly.add_trade_result(100, "strategy_a")  # 勝ち取引
        self.kelly.add_trade_result(-50, "strategy_a")  # 負け取引を1つ追加

        for _i in range(3):
            self.kelly.add_trade_result(-50, "strategy_b")

        # strategy_aのみでKelly計算（勝ち負け混在）
        result_a = self.kelly.calculate_from_history(strategy_filter="strategy_a")
        assert result_a is not None
        assert result_a.win_rate == 0.8  # 5取引中4勝（80%）

        # strategy_bのみでKelly計算
        result_b = self.kelly.calculate_from_history(strategy_filter="strategy_b")
        # strategy_bはデータ不足でNone
        assert result_b is None


class TestPositionSizeIntegrator:
    """ポジションサイズ統合テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        self.kelly = KellyCriterion()
        self.integrator = PositionSizeIntegrator(self.kelly)

    def test_integrated_position_size(self):
        """統合ポジションサイズ計算テスト."""
        # テスト用設定
        config = {"position_size_base": 0.02, "max_position_size": 0.05}

        # 実際のインポートパスでRiskManagerをモック
        with patch("src.strategies.utils.strategy_utils.RiskManager") as mock_risk_manager_class:
            # calculate_position_sizeをクラスメソッドとしてモック
            mock_risk_manager_class.calculate_position_size.return_value = 0.025

            size = self.integrator.calculate_integrated_position_size(
                ml_confidence=0.8, risk_manager_confidence=0.7, strategy_name="test", config=config
            )

            assert size > 0
            # より保守的な値（Kelly vs RiskManagerの小さい方）が採用される
            assert size <= 0.025


# テスト実行時のフィクスチャ
@pytest.fixture
def sample_trade_data():
    """サンプル取引データ."""
    return [
        (100, True, "strategy_a", 0.8),
        (-50, False, "strategy_a", 0.6),
        (150, True, "strategy_b", 0.9),
        (-80, False, "strategy_b", 0.5),
        (120, True, "strategy_a", 0.7),
    ]


def test_kelly_with_real_data(sample_trade_data):
    """実際の取引データでのKellyテスト."""
    kelly = KellyCriterion(min_trades_for_kelly=3)

    for profit_loss, _is_win, strategy, confidence in sample_trade_data:
        kelly.add_trade_result(profit_loss, strategy, confidence)

    result = kelly.calculate_from_history()
    assert result is not None
    assert 0 <= result.win_rate <= 1
    assert result.kelly_fraction >= 0
