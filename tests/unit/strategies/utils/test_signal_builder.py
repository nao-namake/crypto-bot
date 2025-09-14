"""
シグナル生成統合モジュールのテスト

新しく作成したutils/signal_builder.pyのシグナル生成ロジックをテスト。
4つの戦略で重複していたStrategySignal生成処理の統合効果を検証。.
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.base.strategy_base import StrategySignal
from src.strategies.utils import EntryAction, SignalBuilder, StrategyType


class TestSignalBuilder(unittest.TestCase):
    """シグナル生成統合モジュールテストクラス."""

    def setUp(self):
        """テスト前準備."""
        self.strategy_name = "TestStrategy"
        self.current_price = 10000000.0  # 1000万円
        self.basic_config = {
            "stop_loss_atr_multiplier": 2.0,
            "take_profit_ratio": 2.5,
            "position_size_base": 0.02,
        }

        # テスト用DataFrame（ATR含む）
        self.test_df = pd.DataFrame(
            {
                "close": [9900000, 9950000, 10000000],
                "atr_14": [500000, 520000, 500000],
                "volume": [100, 120, 110],
            }
        )

        # 基本的な決定辞書
        self.buy_decision = {
            "action": EntryAction.BUY,
            "confidence": 0.8,
            "strength": 0.7,
            "analysis": "テスト買いシグナル",
        }

        self.sell_decision = {
            "action": EntryAction.SELL,
            "confidence": 0.6,
            "strength": 0.5,
            "analysis": "テスト売りシグナル",
        }

        self.hold_decision = {
            "action": EntryAction.HOLD,
            "confidence": 0.5,
            "strength": 0.0,
            "analysis": "テストホールド",
        }

    def test_create_signal_with_risk_management_buy(self):
        """買いシグナル生成のリスク管理付きテスト."""
        signal = SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=self.buy_decision,
            current_price=self.current_price,
            df=self.test_df,
            config=self.basic_config,
            strategy_type=StrategyType.MOCHIPOY_ALERT,
        )

        # 基本プロパティの確認
        self.assertEqual(signal.strategy_name, self.strategy_name)
        self.assertEqual(signal.action, EntryAction.BUY)
        self.assertEqual(signal.confidence, 0.8)
        self.assertEqual(signal.strength, 0.7)
        self.assertEqual(signal.current_price, self.current_price)
        self.assertEqual(signal.reason, "テスト買いシグナル")

        # リスク管理計算の確認
        self.assertIsNotNone(signal.stop_loss)
        self.assertIsNotNone(signal.take_profit)
        self.assertIsNotNone(signal.position_size)
        self.assertIsNotNone(signal.risk_ratio)

        # 買いポジションの妥当性確認
        self.assertLess(signal.stop_loss, self.current_price)
        self.assertGreater(signal.take_profit, self.current_price)
        self.assertGreater(signal.position_size, 0)
        self.assertGreater(signal.risk_ratio, 0)

        # メタデータの確認
        self.assertEqual(signal.metadata["strategy_type"], StrategyType.MOCHIPOY_ALERT)
        self.assertTrue(signal.metadata["risk_calculated"])

    def test_create_signal_with_risk_management_sell(self):
        """売りシグナル生成のリスク管理付きテスト."""
        signal = SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=self.sell_decision,
            current_price=self.current_price,
            df=self.test_df,
            config=self.basic_config,
            strategy_type=StrategyType.ATR_BASED,
        )

        # 売りポジションの妥当性確認
        self.assertEqual(signal.action, EntryAction.SELL)
        self.assertGreater(signal.stop_loss, self.current_price)
        self.assertLess(signal.take_profit, self.current_price)
        self.assertGreater(signal.position_size, 0)

        # メタデータの確認
        self.assertEqual(signal.metadata["strategy_type"], StrategyType.ATR_BASED)
        self.assertTrue(signal.metadata["risk_calculated"])

    def test_create_signal_with_risk_management_hold(self):
        """ホールドシグナル生成テスト."""
        signal = SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=self.hold_decision,
            current_price=self.current_price,
            df=self.test_df,
            config=self.basic_config,
            strategy_type=StrategyType.DONCHIAN_CHANNEL,
        )

        # ホールドシグナルの確認
        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIsNone(signal.stop_loss)
        self.assertIsNone(signal.take_profit)
        self.assertIsNone(signal.position_size)
        self.assertIsNone(signal.risk_ratio)

        # メタデータの確認
        self.assertEqual(signal.metadata["strategy_type"], StrategyType.DONCHIAN_CHANNEL)
        self.assertFalse(signal.metadata["risk_calculated"])

    def test_create_signal_with_decision_metadata(self):
        """決定メタデータ付きシグナル生成テスト."""
        decision_with_metadata = {
            "action": EntryAction.BUY,
            "confidence": 0.7,
            "strength": 0.6,
            "analysis": "メタデータテスト",
            "metadata": {"tf_4h_signal": 1, "tf_15m_signal": 1, "agreement": True},
        }

        signal = SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=decision_with_metadata,
            current_price=self.current_price,
            df=self.test_df,
            config=self.basic_config,
            strategy_type=StrategyType.MULTI_TIMEFRAME,
        )

        # 決定メタデータが保持されていることを確認
        self.assertIn("decision_metadata", signal.metadata)
        self.assertEqual(signal.metadata["decision_metadata"]["tf_4h_signal"], 1)
        self.assertEqual(signal.metadata["decision_metadata"]["tf_15m_signal"], 1)
        self.assertTrue(signal.metadata["decision_metadata"]["agreement"])

    def test_create_signal_with_missing_atr(self):
        """ATR不足時のエラーハンドリングテスト."""
        # ATRなしのDataFrame
        no_atr_df = pd.DataFrame({"close": [10000000], "volume": [100]})

        signal = SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=self.buy_decision,
            current_price=self.current_price,
            df=no_atr_df,
            config=self.basic_config,
        )

        # エラーシグナルが生成されることを確認
        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertEqual(signal.confidence, 0.0)
        self.assertEqual(signal.strength, 0.0)
        self.assertIn("ATR取得失敗", signal.reason)
        self.assertTrue(signal.metadata.get("error", False))

    def test_create_signal_with_empty_dataframe(self):
        """空DataFrame時のエラーハンドリングテスト."""
        empty_df = pd.DataFrame()

        signal = SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=self.buy_decision,
            current_price=self.current_price,
            df=empty_df,
            config=self.basic_config,
        )

        # エラーシグナルが生成されることを確認
        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertEqual(signal.confidence, 0.0)
        self.assertIn("ATR取得失敗", signal.reason)

    def test_create_hold_signal_basic(self):
        """基本ホールドシグナル生成テスト."""
        signal = SignalBuilder.create_hold_signal(
            strategy_name=self.strategy_name,
            current_price=self.current_price,
            reason="テスト理由",
            strategy_type=StrategyType.ATR_BASED,
        )

        # ホールドシグナルの確認
        self.assertEqual(signal.strategy_name, self.strategy_name)
        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertEqual(signal.confidence, 0.5)
        self.assertEqual(signal.strength, 0.0)
        self.assertEqual(signal.current_price, self.current_price)
        self.assertEqual(signal.reason, "テスト理由")
        self.assertEqual(signal.metadata["strategy_type"], StrategyType.ATR_BASED)

        # リスク管理なし
        self.assertIsNone(signal.stop_loss)
        self.assertIsNone(signal.take_profit)
        self.assertIsNone(signal.position_size)
        self.assertIsNone(signal.risk_ratio)

    def test_get_current_atr_success(self):
        """ATR取得成功テスト."""
        atr_value = SignalBuilder._get_current_atr(self.test_df)
        self.assertEqual(atr_value, 500000.0)
        self.assertIsInstance(atr_value, float)

    def test_get_current_atr_missing_column(self):
        """ATR列不足時のテスト."""
        no_atr_df = pd.DataFrame({"close": [10000000]})
        atr_value = SignalBuilder._get_current_atr(no_atr_df)
        self.assertIsNone(atr_value)

    def test_get_current_atr_zero_value(self):
        """ATRゼロ値時のテスト."""
        zero_atr_df = pd.DataFrame({"atr_14": [0.0]})
        atr_value = SignalBuilder._get_current_atr(zero_atr_df)
        self.assertIsNone(atr_value)

    def test_create_error_signal(self):
        """エラーシグナル生成テスト."""
        error_message = "テストエラーメッセージ"
        signal = SignalBuilder._create_error_signal(
            strategy_name=self.strategy_name,
            current_price=self.current_price,
            error_message=error_message,
        )

        # エラーシグナルの確認
        self.assertEqual(signal.strategy_name, self.strategy_name)
        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertEqual(signal.confidence, 0.0)
        self.assertEqual(signal.strength, 0.0)
        self.assertEqual(signal.current_price, self.current_price)
        self.assertEqual(signal.reason, error_message)
        self.assertTrue(signal.metadata.get("error", False))

    def test_signal_timestamp(self):
        """シグナルタイムスタンプテスト."""
        before_time = datetime.now()

        signal = SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=self.buy_decision,
            current_price=self.current_price,
            df=self.test_df,
            config=self.basic_config,
        )

        after_time = datetime.now()

        # タイムスタンプが適切な範囲内であることを確認
        self.assertGreaterEqual(signal.timestamp, before_time)
        self.assertLessEqual(signal.timestamp, after_time)
        self.assertIsInstance(signal.timestamp, datetime)

    def test_multiple_strategy_types(self):
        """全戦略タイプでのテスト."""
        strategy_types = [
            StrategyType.MOCHIPOY_ALERT,
            StrategyType.ATR_BASED,
            StrategyType.DONCHIAN_CHANNEL,
            StrategyType.MULTI_TIMEFRAME,
        ]

        for strategy_type in strategy_types:
            signal = SignalBuilder.create_signal_with_risk_management(
                strategy_name=f"Test_{strategy_type}",
                decision=self.buy_decision,
                current_price=self.current_price,
                df=self.test_df,
                config=self.basic_config,
                strategy_type=strategy_type,
            )

            self.assertEqual(signal.metadata["strategy_type"], strategy_type)
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)

    @patch("src.strategies.utils.strategy_utils.get_logger")
    def test_logging_integration(self, mock_get_logger):
        """ログ統合テスト."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # 正常ケース
        SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=self.buy_decision,
            current_price=self.current_price,
            df=self.test_df,
            config=self.basic_config,
        )

        # エラーケース（空DataFrame）
        SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.strategy_name,
            decision=self.buy_decision,
            current_price=self.current_price,
            df=pd.DataFrame(),
            config=self.basic_config,
        )

        # ログメソッドが呼ばれたことを確認
        self.assertTrue(mock_get_logger.called)


def run_signal_builder_tests():
    """シグナル生成統合テスト実行関数."""
    print("=" * 50)
    print("シグナル生成統合モジュール テスト開始")
    print("=" * 50)

    # テスト実行
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("シグナル生成統合モジュール テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_signal_builder_tests()
