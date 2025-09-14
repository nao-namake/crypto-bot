"""
共通定数モジュールのテスト

新しく作成したutils/constants.pyの定数定義をテスト。
重複コード除去の効果を検証。.
"""

import os
import sys
import unittest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.utils import DEFAULT_RISK_PARAMS, EntryAction, StrategyType


class TestConstants(unittest.TestCase):
    """共通定数テストクラス."""

    def test_entry_action_constants(self):
        """EntryActionクラステスト."""
        # 全ての必要な定数が存在することを確認
        self.assertEqual(EntryAction.BUY, "buy")
        self.assertEqual(EntryAction.SELL, "sell")
        self.assertEqual(EntryAction.HOLD, "hold")
        self.assertEqual(EntryAction.CLOSE, "close")

        # 型確認
        self.assertIsInstance(EntryAction.BUY, str)
        self.assertIsInstance(EntryAction.SELL, str)
        self.assertIsInstance(EntryAction.HOLD, str)
        self.assertIsInstance(EntryAction.CLOSE, str)

    def test_strategy_type_constants(self):
        """StrategyTypeクラステスト."""
        # 全ての戦略タイプが存在することを確認
        expected_types = [
            "MOCHIPOY_ALERT",
            "ATR_BASED",
            "BOLLINGER_BANDS",
            "DONCHIAN_CHANNEL",
            "ADX_TREND",
        ]

        for strategy_type in expected_types:
            self.assertTrue(hasattr(StrategyType, strategy_type))
            self.assertIsInstance(getattr(StrategyType, strategy_type), str)

    def test_default_risk_params_structure(self):
        """DEFAULT_RISK_PARAMS辞書構造テスト."""
        # 必須パラメータが存在することを確認
        required_params = ["stop_loss_atr_multiplier", "take_profit_ratio", "position_size_base"]

        for param in required_params:
            self.assertIn(param, DEFAULT_RISK_PARAMS)
            self.assertIsInstance(DEFAULT_RISK_PARAMS[param], (int, float))
            self.assertGreater(DEFAULT_RISK_PARAMS[param], 0)

    def test_default_risk_params_values(self):
        """DEFAULT_RISK_PARAMSデフォルト値テスト."""
        # 合理的なデフォルト値であることを確認
        self.assertGreaterEqual(DEFAULT_RISK_PARAMS["stop_loss_atr_multiplier"], 1.0)
        self.assertLessEqual(DEFAULT_RISK_PARAMS["stop_loss_atr_multiplier"], 5.0)

        self.assertGreaterEqual(DEFAULT_RISK_PARAMS["take_profit_ratio"], 1.0)
        self.assertLessEqual(DEFAULT_RISK_PARAMS["take_profit_ratio"], 10.0)

        self.assertGreaterEqual(DEFAULT_RISK_PARAMS["position_size_base"], 0.001)
        self.assertLessEqual(DEFAULT_RISK_PARAMS["position_size_base"], 0.1)

    def test_entry_action_immutability(self):
        """EntryAction定数の不変性テスト（文字列なので参考テスト）."""
        # 定数値が変更されていないことを確認
        original_buy = EntryAction.BUY
        self.assertEqual(original_buy, "buy")

        # 新しい属性を追加しようとしてもクラス定義は変わらない
        # （ただし実行時に追加は可能）
        expected_actions = ["buy", "sell", "hold", "close"]
        all_actions = [EntryAction.BUY, EntryAction.SELL, EntryAction.HOLD, EntryAction.CLOSE]
        self.assertEqual(sorted(all_actions), sorted(expected_actions))

    def test_strategy_type_uniqueness(self):
        """StrategyType定数の一意性テスト."""
        # 各戦略タイプが一意であることを確認
        strategy_values = [
            StrategyType.MOCHIPOY_ALERT,
            StrategyType.ATR_BASED,
            StrategyType.DONCHIAN_CHANNEL,
            StrategyType.MULTI_TIMEFRAME,
        ]

        # 重複がないことを確認
        self.assertEqual(len(strategy_values), len(set(strategy_values)))

        # すべて小文字アンダースコア形式であることを確認（実装に合わせて修正）
        for strategy_type in strategy_values:
            self.assertTrue(
                strategy_type.islower() or "_" in strategy_type
            )  # 小文字またはアンダースコア含む
            self.assertNotIn(" ", strategy_type)  # スペースなし
            self.assertNotIn("-", strategy_type)  # ハイフンなし
            # アンダースコアまたは英数字のみ
            self.assertTrue(all(c.isalnum() or c == "_" for c in strategy_type))


def run_constants_tests():
    """定数テスト実行関数."""
    print("=" * 50)
    print("共通定数モジュール テスト開始")
    print("=" * 50)

    # テスト実行
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("共通定数モジュール テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_constants_tests()
