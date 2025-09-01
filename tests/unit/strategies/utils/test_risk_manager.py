"""
リスク管理モジュールのテスト

新しく作成したutils/risk_manager.pyの計算ロジックをテスト。
4つの戦略で重複していた計算の統合効果を検証。.
"""

import os
import sys
import unittest
from unittest.mock import patch

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.utils import EntryAction, RiskManager


class TestRiskManager(unittest.TestCase):
    """リスク管理モジュールテストクラス."""

    def setUp(self):
        """テスト前準備."""
        self.current_price = 10000000.0  # 1000万円（BTC/JPY想定）
        self.current_atr = 500000.0  # 50万円のATR
        self.basic_config = {
            "stop_loss_atr_multiplier": 2.0,
            "take_profit_ratio": 2.5,
            "position_size_base": 0.02,
        }

    def test_calculate_stop_loss_take_profit_buy(self):
        """買いポジションのストップロス・テイクプロフィット計算テスト."""
        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action=EntryAction.BUY,
            current_price=self.current_price,
            current_atr=self.current_atr,
            config=self.basic_config,
        )

        # 買いポジション: ストップロスは下、テイクプロフィットは上
        expected_stop_loss = self.current_price - (self.current_atr * 2.0)  # 9,000,000
        expected_take_profit = self.current_price + (self.current_atr * 2.0 * 2.5)  # 12,500,000

        self.assertEqual(stop_loss, expected_stop_loss)
        self.assertEqual(take_profit, expected_take_profit)
        self.assertLess(stop_loss, self.current_price)
        self.assertGreater(take_profit, self.current_price)

    def test_calculate_stop_loss_take_profit_sell(self):
        """売りポジションのストップロス・テイクプロフィット計算テスト."""
        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action=EntryAction.SELL,
            current_price=self.current_price,
            current_atr=self.current_atr,
            config=self.basic_config,
        )

        # 売りポジション: ストップロスは上、テイクプロフィットは下
        expected_stop_loss = self.current_price + (self.current_atr * 2.0)  # 11,000,000
        expected_take_profit = self.current_price - (self.current_atr * 2.0 * 2.5)  # 7,500,000

        self.assertEqual(stop_loss, expected_stop_loss)
        self.assertEqual(take_profit, expected_take_profit)
        self.assertGreater(stop_loss, self.current_price)
        self.assertLess(take_profit, self.current_price)

    def test_calculate_stop_loss_take_profit_hold(self):
        """ホールドポジションの計算テスト（None応答）."""
        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action=EntryAction.HOLD,
            current_price=self.current_price,
            current_atr=self.current_atr,
            config=self.basic_config,
        )

        self.assertIsNone(stop_loss)
        self.assertIsNone(take_profit)

    def test_calculate_stop_loss_take_profit_custom_multipliers(self):
        """カスタム倍率でのテスト."""
        custom_config = {
            "stop_loss_atr_multiplier": 1.5,
            "take_profit_ratio": 3.0,
            "position_size_base": 0.02,
        }

        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action=EntryAction.BUY,
            current_price=self.current_price,
            current_atr=self.current_atr,
            config=custom_config,
        )

        expected_stop_loss = self.current_price - (self.current_atr * 1.5)
        expected_take_profit = self.current_price + (self.current_atr * 1.5 * 3.0)

        self.assertEqual(stop_loss, expected_stop_loss)
        self.assertEqual(take_profit, expected_take_profit)

    def test_calculate_position_size_basic(self):
        """基本ポジションサイズ計算テスト."""
        confidence = 0.8
        position_size = RiskManager.calculate_position_size(confidence, self.basic_config)

        # 基本サイズ * confidence
        expected_size = self.basic_config["position_size_base"] * confidence
        self.assertEqual(position_size, expected_size)
        self.assertLessEqual(position_size, self.basic_config["position_size_base"])

    def test_calculate_position_size_confidence_limits(self):
        """信頼度境界値でのポジションサイズテスト."""
        # 信頼度0.0
        size_zero = RiskManager.calculate_position_size(0.0, self.basic_config)
        self.assertEqual(size_zero, 0.0)

        # 信頼度1.0
        size_max = RiskManager.calculate_position_size(1.0, self.basic_config)
        self.assertEqual(size_max, self.basic_config["position_size_base"])

        # 信頼度1.0超（上限処理）
        size_over = RiskManager.calculate_position_size(1.5, self.basic_config)
        self.assertEqual(size_over, self.basic_config["position_size_base"])

    def test_calculate_position_size_custom_base(self):
        """カスタム基本サイズでのテスト."""
        custom_config = {"position_size_base": 0.05}  # 5%

        confidence = 0.6
        position_size = RiskManager.calculate_position_size(confidence, custom_config)

        expected_size = 0.05 * 0.6
        self.assertEqual(position_size, expected_size)

    def test_calculate_risk_ratio_basic(self):
        """基本リスク比率計算テスト."""
        stop_loss = 9000000.0  # 100万円損失
        risk_ratio = RiskManager.calculate_risk_ratio(self.current_price, stop_loss)

        expected_ratio = abs(self.current_price - stop_loss) / self.current_price
        self.assertEqual(risk_ratio, expected_ratio)
        self.assertAlmostEqual(risk_ratio, 0.1, places=3)  # 10%リスク

    def test_calculate_risk_ratio_none_stop_loss(self):
        """ストップロスNoneの場合のリスク比率テスト."""
        risk_ratio = RiskManager.calculate_risk_ratio(self.current_price, None)
        self.assertIsNone(risk_ratio)

    def test_calculate_risk_ratio_zero_price(self):
        """価格ゼロの場合のリスク比率テスト（異常系）."""
        risk_ratio = RiskManager.calculate_risk_ratio(0.0, 1000.0)
        self.assertIsNone(risk_ratio)

    def test_error_handling_missing_config(self):
        """設定項目不足時のエラーハンドリングテスト."""
        incomplete_config = {
            "stop_loss_atr_multiplier": 2.0
            # take_profit_ratio, position_size_base が不足
        }

        # デフォルト値で動作することを確認
        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action=EntryAction.BUY,
            current_price=self.current_price,
            current_atr=self.current_atr,
            config=incomplete_config,
        )

        # 計算は実行されるが、不足分はデフォルト値（例外を発生させない）
        self.assertIsNotNone(stop_loss)
        # take_profit_ratioがないとKeyErrorになるはずなので、
        # 実際の実装でエラーハンドリングが必要

    def test_risk_calculation_consistency(self):
        """リスク計算の一貫性テスト."""
        # 同じパラメータで複数回計算して一貫性を確認
        results = []
        for _ in range(5):
            stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
                action=EntryAction.BUY,
                current_price=self.current_price,
                current_atr=self.current_atr,
                config=self.basic_config,
            )
            results.append((stop_loss, take_profit))

        # すべて同じ結果であることを確認
        first_result = results[0]
        for result in results[1:]:
            self.assertEqual(result, first_result)

    def test_realistic_btc_scenario(self):
        """現実的なBTC価格シナリオテスト."""
        # 2025年想定BTC価格: 1500万円、ATR: 75万円
        btc_price = 15000000.0
        btc_atr = 750000.0

        config = {
            "stop_loss_atr_multiplier": 1.8,
            "take_profit_ratio": 2.2,
            "position_size_base": 0.025,
        }

        stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
            action=EntryAction.BUY, current_price=btc_price, current_atr=btc_atr, config=config
        )

        # リスク・リワード比の確認
        risk = btc_price - stop_loss
        reward = take_profit - btc_price
        risk_reward_ratio = reward / risk

        self.assertAlmostEqual(risk_reward_ratio, config["take_profit_ratio"], places=1)

        # 現実的な範囲内であることを確認
        self.assertGreater(stop_loss, btc_price * 0.8)  # 最大20%損失
        self.assertLess(take_profit, btc_price * 1.5)  # 最大50%利益


def run_risk_manager_tests():
    """リスク管理テスト実行関数."""
    print("=" * 50)
    print("リスク管理モジュール テスト開始")
    print("=" * 50)

    # テスト実行
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("リスク管理モジュール テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_risk_manager_tests()
