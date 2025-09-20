"""
戦略マネージャーの統合テスト

リファクタリング後の統合戦略管理システムが正しく動作することを確認。
複数戦略の登録・実行・シグナル統合・コンフリクト解決を検証。.
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from src.core.exceptions import StrategyError
from src.strategies.base.strategy_base import StrategyBase, StrategySignal
from src.strategies.base.strategy_manager import StrategyManager
from src.strategies.utils import EntryAction


class MockStrategy(StrategyBase):
    """テスト用モック戦略."""

    def __init__(self, name: str, return_signal: StrategySignal):
        super().__init__(name=name)
        self.return_signal = return_signal
        # 親クラスで is_enabled = True が設定される

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        return self.return_signal

    def get_required_features(self):
        return ["close", "volume"]

    def enable(self):
        self.is_enabled = True

    def disable(self):
        self.is_enabled = False


class TestStrategyManager(unittest.TestCase):
    """戦略マネージャーテストクラス."""

    def setUp(self):
        """テスト前準備."""
        # テスト用データフレーム
        dates = pd.date_range(start="2025-08-01", periods=50, freq="1h")
        prices = np.linspace(10000000, 10500000, 50)

        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "close": prices,
                "volume": np.random.uniform(100, 200, 50),
                "rsi_14": np.linspace(40, 60, 50),
                "atr_14": np.full(50, 500000),
            }
        )

        # マネージャーインスタンス
        self.manager = StrategyManager()

        # テスト用シグナル
        self.buy_signal = StrategySignal(
            strategy_name="TestBuy",
            timestamp=datetime.now(),
            action=EntryAction.BUY,
            confidence=0.7,
            strength=0.6,
            current_price=10250000,
            stop_loss=10000000,
            take_profit=10500000,
            position_size=0.02,
            reason="テスト買いシグナル",
        )

        self.sell_signal = StrategySignal(
            strategy_name="TestSell",
            timestamp=datetime.now(),
            action=EntryAction.SELL,
            confidence=0.6,
            strength=0.5,
            current_price=10250000,
            stop_loss=10500000,
            take_profit=10000000,
            position_size=0.02,
            reason="テスト売りシグナル",
        )

        self.hold_signal = StrategySignal(
            strategy_name="TestHold",
            timestamp=datetime.now(),
            action=EntryAction.HOLD,
            confidence=0.5,
            strength=0.0,
            current_price=10250000,
            reason="テストホールドシグナル",
        )

    def test_manager_initialization(self):
        """マネージャー初期化テスト."""
        # デフォルト初期化
        manager = StrategyManager()
        self.assertEqual(len(manager.strategies), 0)
        self.assertEqual(len(manager.strategy_weights), 0)
        self.assertEqual(manager.total_decisions, 0)
        self.assertEqual(manager.signal_conflicts, 0)

        # カスタム設定での初期化
        config = {"min_conflict_threshold": 0.15}
        custom_manager = StrategyManager(config=config)
        self.assertEqual(custom_manager.config["min_conflict_threshold"], 0.15)

    def test_register_strategy_success(self):
        """戦略登録成功テスト."""
        mock_strategy = MockStrategy("TestStrategy", self.buy_signal)

        # 正常登録
        self.manager.register_strategy(mock_strategy, weight=0.8)

        self.assertIn("TestStrategy", self.manager.strategies)
        self.assertEqual(self.manager.strategy_weights["TestStrategy"], 0.8)
        self.assertEqual(len(self.manager.strategies), 1)

    def test_register_strategy_invalid_type(self):
        """戦略登録エラーテスト - 無効な型."""
        invalid_strategy = "not_a_strategy"

        with self.assertRaises(StrategyError) as context:
            self.manager.register_strategy(invalid_strategy)

        self.assertIn("StrategyBase", str(context.exception))

    def test_register_strategy_invalid_weight(self):
        """戦略登録エラーテスト - 無効な重み."""
        mock_strategy = MockStrategy("TestStrategy", self.buy_signal)

        # 重みが範囲外
        with self.assertRaises(StrategyError) as context:
            self.manager.register_strategy(mock_strategy, weight=-0.1)

        self.assertIn("0.0-1.0", str(context.exception))

        with self.assertRaises(StrategyError) as context:
            self.manager.register_strategy(mock_strategy, weight=1.5)

        self.assertIn("0.0-1.0", str(context.exception))

    def test_unregister_strategy(self):
        """戦略登録解除テスト."""
        mock_strategy = MockStrategy("TestStrategy", self.buy_signal)

        # 登録してから解除
        self.manager.register_strategy(mock_strategy)
        self.assertEqual(len(self.manager.strategies), 1)

        self.manager.unregister_strategy("TestStrategy")
        self.assertEqual(len(self.manager.strategies), 0)
        self.assertNotIn("TestStrategy", self.manager.strategies)

        # 未登録戦略の解除（エラーにならない）
        self.manager.unregister_strategy("NonExistentStrategy")

    def test_analyze_market_single_strategy(self):
        """市場分析テスト - 単一戦略."""
        mock_strategy = MockStrategy("SingleStrategy", self.buy_signal)
        self.manager.register_strategy(mock_strategy)

        result = self.manager.analyze_market(self.test_df)

        self.assertEqual(result.action, EntryAction.BUY)
        self.assertEqual(result.strategy_name, "StrategyManager")
        self.assertGreater(result.confidence, 0)
        self.assertEqual(self.manager.total_decisions, 1)

    def test_analyze_market_consistent_signals(self):
        """市場分析テスト - 一貫したシグナル."""
        # 2つの買いシグナル戦略
        buy_strategy1 = MockStrategy("BuyStrategy1", self.buy_signal)
        buy_strategy2 = MockStrategy(
            "BuyStrategy2",
            StrategySignal(
                strategy_name="BuyStrategy2",
                timestamp=datetime.now(),
                action=EntryAction.BUY,
                confidence=0.8,
                strength=0.7,
                current_price=10250000,
                reason="テスト買いシグナル2",
            ),
        )

        self.manager.register_strategy(buy_strategy1, weight=0.6)
        self.manager.register_strategy(buy_strategy2, weight=0.4)

        result = self.manager.analyze_market(self.test_df)

        self.assertEqual(result.action, EntryAction.BUY)
        # 重み付けされた信頼度になるはず
        expected_confidence = (0.7 * 0.6 + 0.8 * 0.4) / (0.6 + 0.4)
        self.assertAlmostEqual(result.confidence, expected_confidence, places=2)

    def test_analyze_market_signal_conflict(self):
        """市場分析テスト - シグナルコンフリクト."""
        # より大きな信頼度差を作成
        strong_buy_signal = StrategySignal(
            strategy_name="StrongBuy",
            timestamp=datetime.now(),
            action=EntryAction.BUY,
            confidence=0.8,
            strength=0.7,
            current_price=10250000,
            reason="強い買いシグナル",
        )

        weak_sell_signal = StrategySignal(
            strategy_name="WeakSell",
            timestamp=datetime.now(),
            action=EntryAction.SELL,
            confidence=0.5,
            strength=0.4,
            current_price=10250000,
            reason="弱い売りシグナル",
        )

        buy_strategy = MockStrategy("BuyStrategy", strong_buy_signal)
        sell_strategy = MockStrategy("SellStrategy", weak_sell_signal)

        self.manager.register_strategy(buy_strategy, weight=0.5)
        self.manager.register_strategy(sell_strategy, weight=0.5)

        result = self.manager.analyze_market(self.test_df)

        # 差が大きい場合は信頼度が高い方が選ばれる
        if abs(0.8 - 0.5) >= self.manager.config.get("min_conflict_threshold", 0.1):
            self.assertEqual(result.action, EntryAction.BUY)
            self.assertTrue(result.metadata.get("conflict_resolved", False))
        else:
            # 差が小さい場合はホールド
            self.assertEqual(result.action, EntryAction.HOLD)

        self.assertEqual(self.manager.signal_conflicts, 1)

    def test_analyze_market_small_conflict_difference(self):
        """市場分析テスト - 小さなコンフリクト差."""
        # ほぼ同じ信頼度の相反シグナル
        close_buy_signal = StrategySignal(
            strategy_name="CloseBuy",
            timestamp=datetime.now(),
            action=EntryAction.BUY,
            confidence=0.65,
            strength=0.5,
            current_price=10250000,
            reason="僅差買いシグナル",
        )

        close_sell_signal = StrategySignal(
            strategy_name="CloseSell",
            timestamp=datetime.now(),
            action=EntryAction.SELL,
            confidence=0.63,
            strength=0.5,
            current_price=10250000,
            reason="僅差売りシグナル",
        )

        buy_strategy = MockStrategy("BuyStrategy", close_buy_signal)
        sell_strategy = MockStrategy("SellStrategy", close_sell_signal)

        # 小さな差の閾値を設定
        self.manager.config["min_conflict_threshold"] = 0.05

        self.manager.register_strategy(buy_strategy)
        self.manager.register_strategy(sell_strategy)

        result = self.manager.analyze_market(self.test_df)

        # 差が小さいのでホールドになるはず
        self.assertEqual(result.action, EntryAction.HOLD)
        self.assertIn("コンフリクト回避", result.reason)

    def test_analyze_market_no_strategies(self):
        """市場分析テスト - 戦略なし."""
        result = self.manager.analyze_market(self.test_df)

        self.assertEqual(result.action, EntryAction.HOLD)
        # 動的confidence: base_hold=0.35にボラティリティ調整適用で約0.42になる
        self.assertAlmostEqual(result.confidence, 0.42, places=2)

    def test_analyze_market_disabled_strategy(self):
        """市場分析テスト - 無効な戦略."""
        mock_strategy = MockStrategy("DisabledStrategy", self.buy_signal)
        mock_strategy.disable()  # 戦略を無効化

        self.manager.register_strategy(mock_strategy)
        result = self.manager.analyze_market(self.test_df)

        # 無効な戦略はスキップされ、ホールドになる
        self.assertEqual(result.action, EntryAction.HOLD)

    def test_analyze_market_strategy_error(self):
        """市場分析テスト - 戦略エラー."""
        # エラーを発生させるモック戦略
        error_strategy = Mock(spec=StrategyBase)
        error_strategy.name = "ErrorStrategy"
        error_strategy.is_enabled = True
        error_strategy.generate_signal.side_effect = Exception("テストエラー")

        self.manager.strategies["ErrorStrategy"] = error_strategy
        self.manager.strategy_weights["ErrorStrategy"] = 1.0

        # すべての戦略でエラーが発生した場合はStrategyErrorが発生
        with self.assertRaises(StrategyError) as context:
            self.manager.analyze_market(self.test_df)

        self.assertIn("全戦略でエラー", str(context.exception))

    def test_calculate_weighted_confidence(self):
        """重み付け信頼度計算テスト."""
        signals = [
            ("Strategy1", self.buy_signal),  # confidence: 0.7
            (
                "Strategy2",
                StrategySignal(
                    strategy_name="Strategy2",
                    timestamp=datetime.now(),
                    action=EntryAction.BUY,
                    confidence=0.8,
                    strength=0.6,
                    current_price=10250000,
                    reason="テスト",
                ),
            ),
        ]

        # 重み設定
        self.manager.strategy_weights = {"Strategy1": 0.3, "Strategy2": 0.7}

        weighted_confidence = self.manager._calculate_weighted_confidence(signals)

        # 期待値: (0.7 * 0.3 + 0.8 * 0.7) / (0.3 + 0.7) = 0.77
        expected = (0.7 * 0.3 + 0.8 * 0.7) / (0.3 + 0.7)
        self.assertAlmostEqual(weighted_confidence, expected, places=2)

    def test_get_strategy_performance(self):
        """戦略パフォーマンス取得テスト."""
        mock_strategy = MockStrategy("TestStrategy", self.buy_signal)
        mock_strategy.get_signal_stats = Mock(return_value={"total": 10, "success": 7})

        self.manager.register_strategy(mock_strategy, weight=0.8)

        performance = self.manager.get_strategy_performance()

        self.assertIn("TestStrategy", performance)
        self.assertEqual(performance["TestStrategy"]["weight"], 0.8)
        self.assertTrue(performance["TestStrategy"]["enabled"])
        self.assertEqual(performance["TestStrategy"]["stats"]["total"], 10)

    def test_get_manager_stats(self):
        """マネージャー統計取得テスト."""
        mock_strategy1 = MockStrategy("Strategy1", self.buy_signal)
        mock_strategy2 = MockStrategy("Strategy2", self.sell_signal)
        mock_strategy2.disable()  # 1つを無効化

        self.manager.register_strategy(mock_strategy1)
        self.manager.register_strategy(mock_strategy2)

        # いくつかの決定を実行
        self.manager.total_decisions = 5
        self.manager.signal_conflicts = 2

        stats = self.manager.get_manager_stats()

        self.assertEqual(stats["total_strategies"], 2)
        self.assertEqual(stats["enabled_strategies"], 1)
        self.assertEqual(stats["total_decisions"], 5)
        self.assertEqual(stats["signal_conflicts"], 2)
        self.assertIn("Strategy1", stats["strategy_weights"])

    def test_update_strategy_weights(self):
        """戦略重み更新テスト."""
        mock_strategy = MockStrategy("TestStrategy", self.buy_signal)
        self.manager.register_strategy(mock_strategy, weight=0.5)

        # 正常な重み更新
        self.manager.update_strategy_weights({"TestStrategy": 0.8})
        self.assertEqual(self.manager.strategy_weights["TestStrategy"], 0.8)

        # 無効な戦略名（警告のみ）
        self.manager.update_strategy_weights({"NonExistent": 0.5})

        # 無効な重み（警告のみ）
        self.manager.update_strategy_weights({"TestStrategy": 1.5})
        self.assertEqual(self.manager.strategy_weights["TestStrategy"], 0.8)  # 変更されない

    def test_reset_stats(self):
        """統計リセットテスト."""
        # 統計を設定
        self.manager.total_decisions = 10
        self.manager.signal_conflicts = 3
        self.manager.last_combined_signal = self.buy_signal

        # リセット実行
        self.manager.reset_stats()

        # リセット確認
        self.assertEqual(self.manager.total_decisions, 0)
        self.assertEqual(self.manager.signal_conflicts, 0)
        self.assertIsNone(self.manager.last_combined_signal)

    def test_hold_signals_integration(self):
        """ホールドシグナル統合テスト."""
        hold_strategy1 = MockStrategy("HoldStrategy1", self.hold_signal)
        hold_strategy2 = MockStrategy("HoldStrategy2", self.hold_signal)

        self.manager.register_strategy(hold_strategy1)
        self.manager.register_strategy(hold_strategy2)

        result = self.manager.analyze_market(self.test_df)

        self.assertEqual(result.action, EntryAction.HOLD)
        self.assertIn("ホールド推奨", result.reason)


def run_strategy_manager_tests():
    """戦略マネージャーテスト実行関数."""
    print("=" * 50)
    print("戦略マネージャー統合テスト開始")
    print("=" * 50)

    # テスト実行
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("戦略マネージャー統合テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_strategy_manager_tests()
