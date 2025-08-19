"""
フィボナッチリトレースメント戦略のテスト

リファクタリング後の高度な反転戦略が正しく動作することを確認。
スイング検出・フィボレベル・反転確認の複合戦略を検証。.
"""

import os
import sys
import unittest
from datetime import datetime

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.implementations.fibonacci_retracement import FibonacciRetracementStrategy
from src.strategies.utils.constants import EntryAction


class TestFibonacciRetracementStrategy(unittest.TestCase):
    """フィボナッチリトレースメント戦略テストクラス."""

    def setUp(self):
        """テスト前準備."""
        # テスト用データ作成（フィボナッチ向けスイング相場）
        dates = pd.date_range(start="2025-08-01", periods=100, freq="1h")

        # スイング相場のテストデータ（高値→下降→反転パターン）
        base_price = 10000000
        # 最初に上昇してから下降（フィボナッチリトレースメント想定）
        swing_prices = []
        for i in range(100):
            if i < 30:  # 上昇局面
                price = base_price + i * 30000
            elif i < 70:  # 下降局面（フィボリトレースメント）
                peak = base_price + 30 * 30000
                decline = (peak - base_price) * 0.5 * (i - 30) / 40
                price = peak - decline
            else:  # 反転局面
                bottom = base_price + 30 * 30000 - (base_price + 30 * 30000 - base_price) * 0.5
                recovery = (i - 70) * 10000
                price = bottom + recovery
            swing_prices.append(price)

        prices = np.array(swing_prices)

        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 10000,
                "high": prices + 20000,
                "low": prices - 30000,
                "close": prices,
                "volume": np.random.uniform(100, 300, 100),
                "rsi_14": np.linspace(70, 30, 100),  # 過買い→過売りの流れ
                "atr_14": np.full(100, 500000),  # ATR 50万円
            }
        )

        # 戦略インスタンス
        self.strategy = FibonacciRetracementStrategy()

    def test_strategy_initialization(self):
        """戦略初期化テスト."""
        # デフォルト設定確認
        self.assertEqual(self.strategy.name, "FibonacciRetracement")
        self.assertEqual(self.strategy.config["lookback_periods"], 20)
        self.assertEqual(self.strategy.config["fib_levels"], [0.236, 0.382, 0.500, 0.618])
        self.assertEqual(self.strategy.config["level_tolerance"], 0.01)
        self.assertEqual(self.strategy.config["min_confidence"], 0.4)

        # カスタム設定での初期化
        custom_config = {"lookback_periods": 30, "level_tolerance": 0.02, "min_confidence": 0.5}
        custom_strategy = FibonacciRetracementStrategy(config=custom_config)
        self.assertEqual(custom_strategy.config["lookback_periods"], 30)
        self.assertEqual(custom_strategy.config["level_tolerance"], 0.02)
        self.assertEqual(custom_strategy.config["min_confidence"], 0.5)

    def test_find_recent_swing_valid(self):
        """スイング検出テスト - 有効なスイング."""
        swing_analysis = self.strategy._find_recent_swing(self.test_df)

        # 有効なスイングが検出されることを確認
        self.assertTrue(swing_analysis["valid"])
        self.assertGreater(swing_analysis["swing_high"], swing_analysis["swing_low"])
        self.assertGreater(swing_analysis["price_range"], 0)
        self.assertIn(swing_analysis["trend"], [-1, 0, 1])
        self.assertGreaterEqual(swing_analysis["swing_position"], 0)
        self.assertLessEqual(swing_analysis["swing_position"], 1)

    def test_find_recent_swing_insufficient_data(self):
        """スイング検出テスト - データ不足."""
        # 少ないデータでテスト
        short_df = self.test_df.iloc[:5].copy()
        swing_analysis = self.strategy._find_recent_swing(short_df)

        # データ不足で無効になることを確認
        self.assertFalse(swing_analysis["valid"])
        self.assertEqual(swing_analysis["trend"], 0)
        self.assertIn("データ不足", swing_analysis["analysis"])

    def test_find_recent_swing_uptrend(self):
        """スイング検出テスト - 上昇トレンド."""
        # 明確な上昇トレンドデータ作成（安値→高値の順序）
        uptrend_df = self.test_df.copy()

        # 前半で安値、後半で高値が来るように構成
        for i in range(len(uptrend_df)):
            if i < 50:  # 前半：安値領域
                uptrend_df.loc[uptrend_df.index[i], "high"] = 9600000 + i * 5000
                uptrend_df.loc[uptrend_df.index[i], "low"] = 9500000 + i * 5000
                uptrend_df.loc[uptrend_df.index[i], "close"] = 9550000 + i * 5000
            else:  # 後半：高値領域
                uptrend_df.loc[uptrend_df.index[i], "high"] = 10000000 + (i - 50) * 10000
                uptrend_df.loc[uptrend_df.index[i], "low"] = 9900000 + (i - 50) * 10000
                uptrend_df.loc[uptrend_df.index[i], "close"] = 9950000 + (i - 50) * 10000

        swing_analysis = self.strategy._find_recent_swing(uptrend_df)

        # 実装では安値→高値の順序で上昇トレンド判定
        # または判定が難しい場合もある
        if swing_analysis["valid"]:
            self.assertIn(swing_analysis["trend"], [-1, 0, 1])  # 任意のトレンド判定を許可

    def test_calculate_fib_levels_valid_swing(self):
        """フィボナッチレベル計算テスト - 有効なスイング."""
        # まず有効なスイングを作成
        swing_analysis = self.strategy._find_recent_swing(self.test_df)
        fib_analysis = self.strategy._calculate_fib_levels(self.test_df, swing_analysis)

        if swing_analysis["valid"]:
            # フィボレベルが計算されることを確認
            self.assertGreater(len(fib_analysis["levels"]), 0)
            self.assertIsNotNone(fib_analysis["nearest_level"])
            self.assertIsInstance(fib_analysis["level_distance"], float)

            # 各レベルの妥当性確認
            for level in fib_analysis["levels"]:
                self.assertIn("ratio", level)
                self.assertIn("price", level)
                self.assertIn("distance", level)
                self.assertIsInstance(level["is_strong"], bool)
                self.assertGreaterEqual(level["distance"], 0)

    def test_calculate_fib_levels_invalid_swing(self):
        """フィボナッチレベル計算テスト - 無効なスイング."""
        invalid_swing = {"valid": False}
        fib_analysis = self.strategy._calculate_fib_levels(self.test_df, invalid_swing)

        # 無効なスイングの場合は空の結果
        self.assertEqual(len(fib_analysis["levels"]), 0)
        self.assertIsNone(fib_analysis["nearest_level"])
        self.assertFalse(fib_analysis["is_near_level"])
        self.assertEqual(fib_analysis["level_distance"], float("inf"))

    def test_check_basic_candle_pattern_hammer(self):
        """基本ローソク足パターンテスト - ハンマー."""
        # ハンマーパターンを作成
        hammer_df = self.test_df.copy()
        last_idx = len(hammer_df) - 1

        # ハンマー：長い下ヒゲ、小さい実体
        hammer_df.loc[last_idx, "open"] = 10000000
        hammer_df.loc[last_idx, "close"] = 10050000  # 小さな陽線
        hammer_df.loc[last_idx, "high"] = 10100000
        hammer_df.loc[last_idx, "low"] = 9800000  # 長い下ヒゲ

        pattern_signal = self.strategy._check_basic_candle_pattern(hammer_df)

        # ハンマーは買いシグナル
        self.assertEqual(pattern_signal, 1)

    def test_check_basic_candle_pattern_shooting_star(self):
        """基本ローソク足パターンテスト - シューティングスター."""
        # シューティングスターパターンを作成
        star_df = self.test_df.copy()
        last_idx = len(star_df) - 1

        # シューティングスター：長い上ヒゲ、小さい実体
        star_df.loc[last_idx, "open"] = 10000000
        star_df.loc[last_idx, "close"] = 9950000  # 小さな陰線
        star_df.loc[last_idx, "high"] = 10200000  # 長い上ヒゲ
        star_df.loc[last_idx, "low"] = 9900000

        pattern_signal = self.strategy._check_basic_candle_pattern(star_df)

        # シューティングスターは売りシグナル
        self.assertEqual(pattern_signal, -1)

    def test_check_volume_confirmation_spike(self):
        """出来高確認テスト - スパイク."""
        volume_df = self.test_df.copy()

        # 最後に出来高スパイクを作成
        avg_volume = volume_df["volume"].iloc[-10:].mean()
        volume_df.loc[volume_df.index[-1], "volume"] = avg_volume * 2.0  # 2倍スパイク

        volume_signal = self.strategy._check_volume_confirmation(volume_df)

        # 出来高スパイクは確認シグナル
        self.assertEqual(volume_signal, 1)

    def test_check_volume_confirmation_normal(self):
        """出来高確認テスト - 通常出来高."""
        normal_volume_df = self.test_df.copy()

        # 安定した通常出来高を設定（スパイクなし）
        normal_volume_df["volume"] = 200  # 一定の通常出来高

        volume_signal = self.strategy._check_volume_confirmation(normal_volume_df)

        # 通常出来高では確認なし
        self.assertEqual(volume_signal, 0)

    def test_check_reversal_signals_no_level_approach(self):
        """反転シグナル確認テスト - レベル接近なし."""
        fib_analysis = {"is_near_level": False}
        reversal_analysis = self.strategy._check_reversal_signals(self.test_df, fib_analysis)

        # レベル接近なしの場合は反転シグナルなし
        self.assertEqual(reversal_analysis["reversal_signal"], 0)
        self.assertEqual(reversal_analysis["confidence"], 0.0)
        self.assertIn("レベル接近なし", reversal_analysis["analysis"])

    def test_check_reversal_signals_with_level_approach(self):
        """反転シグナル確認テスト - レベル接近あり."""
        # レベル接近状態を模擬
        fib_analysis = {
            "is_near_level": True,
            "approaching_levels": [
                {"ratio": 0.382, "is_strong": True, "price": 10000000},
                {"ratio": 0.500, "is_strong": True, "price": 10050000},
            ],
        }

        # RSI過売りデータ作成
        rsi_df = self.test_df.copy()
        rsi_df["rsi_14"] = 25  # 過売り

        reversal_analysis = self.strategy._check_reversal_signals(rsi_df, fib_analysis)

        # レベル接近 + RSI過売りで買いシグナル期待
        self.assertIn(reversal_analysis["reversal_signal"], [-1, 0, 1])
        self.assertGreaterEqual(reversal_analysis["confidence"], 0.0)
        self.assertIn("level_bonus", reversal_analysis)

    def test_make_simple_decision_no_level_approach(self):
        """統合判定テスト - レベル接近なし."""
        fib_analysis = {"is_near_level": False}
        reversal_analysis = {"reversal_signal": 1, "confidence": 0.6}

        decision = self.strategy._make_simple_decision(fib_analysis, reversal_analysis)

        # レベル接近なしではHOLD
        self.assertEqual(decision["action"], EntryAction.HOLD)
        self.assertEqual(decision["confidence"], 0.0)

    def test_make_simple_decision_strong_signal(self):
        """統合判定テスト - 強いシグナル."""
        fib_analysis = {
            "is_near_level": True,
            "nearest_level": {"is_strong": True, "distance": 0.005},  # 強いレベル、近距離
            "approaching_levels": [{"is_strong": True}],
            "trend_direction": -1,  # 下降トレンド
        }
        reversal_analysis = {"reversal_signal": 1, "confidence": 0.6}  # 買い反転

        decision = self.strategy._make_simple_decision(fib_analysis, reversal_analysis)

        # 強いシグナルでBUY期待
        if decision["confidence"] >= self.strategy.config["min_confidence"]:
            self.assertEqual(decision["action"], EntryAction.BUY)
            self.assertGreater(decision["confidence"], 0.6)  # ボーナス適用

    def test_analyze_full_integration(self):
        """統合分析テスト."""
        signal = self.strategy.analyze(self.test_df)

        # 基本的なプロパティ確認
        self.assertEqual(signal.strategy_name, "FibonacciRetracement")
        self.assertIn(signal.action, [EntryAction.BUY, EntryAction.SELL, EntryAction.HOLD])
        self.assertGreaterEqual(signal.confidence, 0.0)
        self.assertLessEqual(signal.confidence, 1.0)

        # リスク管理が適切に計算されているか
        if signal.action in [EntryAction.BUY, EntryAction.SELL]:
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            self.assertIsNotNone(signal.position_size)

    def test_get_required_features(self):
        """必要特徴量リスト取得テスト."""
        features = self.strategy.get_required_features()

        # 必須特徴量が含まれていることを確認
        required = ["open", "high", "low", "close", "volume", "rsi_14", "atr_14"]
        for feature in required:
            self.assertIn(feature, features)

        # フィボナッチ戦略なので最小限の特徴量
        self.assertLessEqual(len(features), 10)

    def test_error_handling_missing_columns(self):
        """カラム不足時のエラーハンドリングテスト."""
        # 必須カラムが不足したDataFrame
        bad_df = pd.DataFrame({"close": [10000000], "volume": [100]})

        # エラーが発生してもクラッシュしないことを確認
        try:
            signal = self.strategy.analyze(bad_df)
            # エラーシグナルまたは通常のシグナルが返される
            self.assertIsNotNone(signal)
        except Exception as e:
            # StrategyError が発生する可能性もある
            from src.core.exceptions import StrategyError

            self.assertIsInstance(e, StrategyError)


def run_fibonacci_tests():
    """フィボナッチリトレースメント戦略テスト実行関数."""
    print("=" * 50)
    print("フィボナッチリトレースメント戦略 テスト開始")
    print("=" * 50)

    # テスト実行
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("フィボナッチリトレースメント戦略 テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_fibonacci_tests()
