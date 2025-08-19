"""
ATRベース戦略のテスト

リファクタリング後の逆張り戦略が正しく動作することを確認。
ボラティリティベースの判定ロジックを検証。.
"""

import os
import sys
import unittest
from datetime import datetime

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.implementations.atr_based import ATRBasedStrategy
from src.strategies.utils.constants import EntryAction


class TestATRBasedStrategy(unittest.TestCase):
    """ATRベース戦略テストクラス."""

    def setUp(self):
        """テスト前準備."""
        # テスト用データ作成（横ばい相場）
        dates = pd.date_range(start="2025-08-01", periods=100, freq="1h")

        # 横ばい相場のテストデータ（逆張り向き）
        base_price = 10000000
        prices = base_price + np.sin(np.linspace(0, 4 * np.pi, 100)) * 500000  # ±50万円の振動

        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "close": prices,
                "volume": np.random.uniform(100, 200, 100),
                "atr_14": np.full(100, 500000),  # ATR 50万円
                "bb_position": np.linspace(0.1, 0.9, 100),  # BBポジション変動
                "rsi_14": np.linspace(25, 75, 100),  # RSI変動
                "market_stress": np.full(100, 0.3),  # 低ストレス
            }
        )

        # 戦略インスタンス
        self.strategy = ATRBasedStrategy()

    def test_strategy_initialization(self):
        """戦略初期化テスト."""
        # デフォルト設定確認
        self.assertEqual(self.strategy.name, "ATRBased")
        self.assertEqual(self.strategy.config["bb_overbought"], 0.8)
        self.assertEqual(self.strategy.config["bb_oversold"], 0.2)
        self.assertEqual(self.strategy.config["min_confidence"], 0.4)
        self.assertEqual(self.strategy.config["position_size_base"], 0.015)  # 逆張りなので控えめ

    def test_analyze_bb_position_overbought(self):
        """ボリンジャーバンド位置分析 - 過買いテスト."""
        overbought_df = self.test_df.copy()
        overbought_df["bb_position"] = 0.85  # 過買い領域

        result = self.strategy._analyze_bb_position(overbought_df)

        self.assertEqual(result["signal"], -1)  # 売りシグナル（逆張り）
        self.assertGreater(result["strength"], 0)
        self.assertGreater(result["confidence"], 0)

    def test_analyze_bb_position_oversold(self):
        """ボリンジャーバンド位置分析 - 過売りテスト."""
        oversold_df = self.test_df.copy()
        oversold_df["bb_position"] = 0.15  # 過売り領域

        result = self.strategy._analyze_bb_position(oversold_df)

        self.assertEqual(result["signal"], 1)  # 買いシグナル（逆張り）
        self.assertGreater(result["strength"], 0)
        self.assertGreater(result["confidence"], 0)

    def test_analyze_bb_position_neutral(self):
        """ボリンジャーバンド位置分析 - 中立テスト."""
        neutral_df = self.test_df.copy()
        neutral_df["bb_position"] = 0.5  # 中立領域

        result = self.strategy._analyze_bb_position(neutral_df)

        self.assertEqual(result["signal"], 0)  # ニュートラル
        self.assertEqual(result["strength"], 0.0)
        self.assertEqual(result["confidence"], 0.0)

    def test_analyze_rsi_momentum_overbought(self):
        """RSIモメンタム分析 - 過買いテスト."""
        overbought_df = self.test_df.copy()
        overbought_df["rsi_14"] = 75  # 過買い

        result = self.strategy._analyze_rsi_momentum(overbought_df)

        self.assertEqual(result["signal"], -1)  # 売りシグナル（逆張り）
        self.assertGreater(result["confidence"], 0)

    def test_analyze_rsi_momentum_oversold(self):
        """RSIモメンタム分析 - 過売りテスト."""
        oversold_df = self.test_df.copy()
        oversold_df["rsi_14"] = 25  # 過売り

        result = self.strategy._analyze_rsi_momentum(oversold_df)

        self.assertEqual(result["signal"], 1)  # 買いシグナル（逆張り）
        self.assertGreater(result["confidence"], 0)

    def test_analyze_atr_volatility(self):
        """ATRボラティリティ分析テスト."""
        result = self.strategy._analyze_atr_volatility(self.test_df)

        # 結果の妥当性確認
        self.assertIn(result["regime"], ["low", "normal", "high"])
        self.assertGreaterEqual(result["strength"], 0.0)
        self.assertGreater(result["atr_ratio"], 0)
        self.assertIsNotNone(result["volatility_multiplier"])

    def test_analyze_market_stress_high(self):
        """市場ストレス分析 - 高ストレステスト."""
        high_stress_df = self.test_df.copy()
        high_stress_df["market_stress"] = 0.8  # 高ストレス

        result = self.strategy._analyze_market_stress(high_stress_df)

        self.assertEqual(result["state"], "high")
        self.assertFalse(result["filter_ok"])  # 取引回避

    def test_analyze_market_stress_normal(self):
        """市場ストレス分析 - 通常テスト."""
        result = self.strategy._analyze_market_stress(self.test_df)

        self.assertEqual(result["state"], "normal")
        self.assertTrue(result["filter_ok"])  # 取引可能

    def test_make_decision_both_signals(self):
        """統合判定 - 両シグナル一致テスト."""
        bb_analysis = {"signal": 1, "confidence": 0.6, "strength": 0.7}
        rsi_analysis = {"signal": 1, "confidence": 0.5, "strength": 0.6}
        atr_analysis = {"regime": "normal", "strength": 0.5}
        stress_analysis = {"filter_ok": True}

        decision = self.strategy._make_decision(
            bb_analysis, rsi_analysis, atr_analysis, stress_analysis
        )

        self.assertEqual(decision["action"], EntryAction.BUY)
        self.assertGreater(decision["confidence"], 0.4)

    def test_make_decision_conflict(self):
        """統合判定 - シグナル不一致テスト."""
        bb_analysis = {"signal": 1, "confidence": 0.6, "strength": 0.7}
        rsi_analysis = {"signal": -1, "confidence": 0.5, "strength": 0.6}
        atr_analysis = {"regime": "normal", "strength": 0.5}
        stress_analysis = {"filter_ok": True}

        decision = self.strategy._make_decision(
            bb_analysis, rsi_analysis, atr_analysis, stress_analysis
        )

        self.assertEqual(decision["action"], EntryAction.HOLD)
        self.assertIn("シグナル不一致", decision["analysis"])

    def test_make_decision_high_stress_filter(self):
        """統合判定 - 高ストレスフィルターテスト."""
        bb_analysis = {"signal": 1, "confidence": 0.6, "strength": 0.7}
        rsi_analysis = {"signal": 1, "confidence": 0.5, "strength": 0.6}
        atr_analysis = {"regime": "normal", "strength": 0.5}
        stress_analysis = {"filter_ok": False}  # 高ストレス

        decision = self.strategy._make_decision(
            bb_analysis, rsi_analysis, atr_analysis, stress_analysis
        )

        self.assertEqual(decision["action"], EntryAction.HOLD)
        self.assertIn("市場ストレス高", decision["analysis"])

    def test_analyze_full_integration(self):
        """統合分析テスト."""
        signal = self.strategy.analyze(self.test_df)

        # 基本的なプロパティ確認
        self.assertEqual(signal.strategy_name, "ATRBased")
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
        required = ["close", "atr_14", "bb_position", "rsi_14", "market_stress"]
        for feature in required:
            self.assertIn(feature, features)

        # 特徴量数が適切（最小限）
        self.assertLessEqual(len(features), 10)

    def test_high_volatility_bonus(self):
        """高ボラティリティボーナステスト."""
        bb_analysis = {"signal": 1, "confidence": 0.5, "strength": 0.7}
        rsi_analysis = {"signal": 1, "confidence": 0.4, "strength": 0.6}
        atr_analysis = {"regime": "high", "strength": 0.8}  # 高ボラティリティ
        stress_analysis = {"filter_ok": True}

        decision = self.strategy._make_decision(
            bb_analysis, rsi_analysis, atr_analysis, stress_analysis
        )

        # 高ボラティリティで信頼度ボーナスが適用されることを確認
        base_confidence = bb_analysis["confidence"] + rsi_analysis["confidence"]
        self.assertGreater(decision["confidence"], base_confidence)


def run_atr_based_tests():
    """ATRベース戦略テスト実行関数."""
    print("=" * 50)
    print("ATRベース戦略 テスト開始")
    print("=" * 50)

    # テスト実行
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("ATRベース戦略 テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_atr_based_tests()
