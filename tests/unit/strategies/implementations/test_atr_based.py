"""
ATRレンジ消尽戦略のテスト

Phase 54.12: 完全リファクタリング

核心思想:
「今日の価格変動がATRの大部分を消費した → これ以上動かない → 反転を狙う」
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd
import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.implementations.atr_based import ATRBasedStrategy
from src.strategies.utils import EntryAction


@pytest.fixture(scope="session", autouse=True)
def init_config():
    """テスト用設定初期化"""
    try:
        from src.core.config import load_config

        load_config("config/core/unified.yaml")
    except Exception:
        from src.core.config import config_manager

        config_manager._config = {
            "trading": {"mode": "paper"},
            "features": {"selected": ["close", "high", "low", "rsi_14", "atr_14", "adx_14"]},
            "strategies": {"default_config": {}},
            "ml": {"models": {}},
            "data": {"timeframes": ["15m", "1h", "4h"]},
            "monitoring": {"enabled": False},
        }


class TestATRBasedStrategy(unittest.TestCase):
    """ATRレンジ消尽戦略テストクラス"""

    def setUp(self):
        """テスト前準備"""
        dates = pd.date_range(start="2025-08-01", periods=100, freq="1h")
        base_price = 10000000

        # レンジ相場のテストデータ
        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "close": np.full(100, base_price),
                "high": np.full(100, base_price + 300000),  # +30万
                "low": np.full(100, base_price - 300000),  # -30万
                "atr_14": np.full(100, 500000),  # ATR 50万円
                "adx_14": np.full(100, 20),  # レンジ相場（ADX < 25）
                "rsi_14": np.full(100, 50),  # 中立
                "volume": np.random.uniform(100, 200, 100),
            }
        )

        self.strategy = ATRBasedStrategy()

    def test_strategy_initialization(self):
        """戦略初期化テスト"""
        self.assertEqual(self.strategy.name, "ATRBased")
        # Phase 55.1: 閾値はthresholds.yamlから読み込まれる
        # 値の存在確認のみ行う（具体的な値はyaml設定に依存）
        self.assertIn("exhaustion_threshold", self.strategy.config)
        self.assertIn("high_exhaustion_threshold", self.strategy.config)
        self.assertIn("adx_range_threshold", self.strategy.config)
        self.assertIn("rsi_upper", self.strategy.config)
        self.assertIn("rsi_lower", self.strategy.config)

    def test_calculate_exhaustion_ratio_low(self):
        """消尽率計算テスト - 低消尽"""
        # 値幅 = 60万（30万 - (-30万)）、ATR = 50万 → 消尽率 = 1.2（120%）
        result = self.strategy._calculate_exhaustion_ratio(self.test_df)

        self.assertGreater(result["ratio"], 0)
        self.assertEqual(result["daily_range"], 600000)  # 60万
        self.assertEqual(result["atr_14"], 500000)  # 50万

    def test_calculate_exhaustion_ratio_exhausted(self):
        """消尽率計算テスト - 消尽"""
        # 消尽率 80%のデータ
        exhausted_df = self.test_df.copy()
        exhausted_df["high"] = 10200000  # +20万
        exhausted_df["low"] = 9800000  # -20万
        # 値幅 = 40万、ATR = 50万 → 消尽率 = 0.8（80%）

        result = self.strategy._calculate_exhaustion_ratio(exhausted_df)

        self.assertAlmostEqual(result["ratio"], 0.8, places=1)
        self.assertTrue(result["is_exhausted"])

    def test_calculate_exhaustion_ratio_high_exhaustion(self):
        """消尽率計算テスト - 高消尽"""
        # 消尽率 90%のデータ
        high_exhausted_df = self.test_df.copy()
        high_exhausted_df["high"] = 10225000  # +22.5万
        high_exhausted_df["low"] = 9775000  # -22.5万
        # 値幅 = 45万、ATR = 50万 → 消尽率 = 0.9（90%）

        result = self.strategy._calculate_exhaustion_ratio(high_exhausted_df)

        self.assertAlmostEqual(result["ratio"], 0.9, places=1)
        self.assertTrue(result["is_exhausted"])
        self.assertTrue(result["is_high_exhaustion"])

    def test_check_range_market_range(self):
        """レンジ相場判定テスト - レンジ"""
        result = self.strategy._check_range_market(self.test_df)

        self.assertTrue(result["is_range"])
        self.assertEqual(result["adx"], 20)
        self.assertIn("レンジ相場", result["reason"])

    def test_check_range_market_trend(self):
        """レンジ相場判定テスト - トレンド"""
        trend_df = self.test_df.copy()
        trend_df["adx_14"] = 35  # トレンド相場

        result = self.strategy._check_range_market(trend_df)

        self.assertFalse(result["is_range"])
        self.assertIn("トレンド相場", result["reason"])

    def test_check_range_market_no_adx(self):
        """レンジ相場判定テスト - ADXなし"""
        no_adx_df = self.test_df.drop(columns=["adx_14"])

        result = self.strategy._check_range_market(no_adx_df)

        self.assertTrue(result["is_range"])  # デフォルトでレンジと仮定

    def test_determine_reversal_direction_sell(self):
        """反転方向判定テスト - SELL"""
        sell_df = self.test_df.copy()
        sell_df["rsi_14"] = 70  # RSI > 60

        result = self.strategy._determine_reversal_direction(sell_df)

        self.assertEqual(result["action"], EntryAction.SELL)
        self.assertIn("下への反転期待", result["reason"])

    def test_determine_reversal_direction_buy(self):
        """反転方向判定テスト - BUY"""
        buy_df = self.test_df.copy()
        buy_df["rsi_14"] = 30  # RSI < 40

        result = self.strategy._determine_reversal_direction(buy_df)

        self.assertEqual(result["action"], EntryAction.BUY)
        self.assertIn("上への反転期待", result["reason"])

    def test_determine_reversal_direction_hold(self):
        """反転方向判定テスト - HOLD"""
        hold_df = self.test_df.copy()
        hold_df["rsi_14"] = 50  # 40 < RSI < 60

        result = self.strategy._determine_reversal_direction(hold_df)

        self.assertEqual(result["action"], EntryAction.HOLD)
        self.assertIn("方向不明", result["reason"])

    def test_analyze_full_buy_signal(self):
        """統合分析テスト - BUYシグナル"""
        # 条件: レンジ相場 + 消尽 + RSI低い → BUY
        buy_df = self.test_df.copy()
        buy_df["adx_14"] = 20  # レンジ相場
        buy_df["high"] = 10225000  # 消尽率 90%
        buy_df["low"] = 9775000
        buy_df["rsi_14"] = 30  # RSI低い → BUY方向

        signal = self.strategy.analyze(buy_df)

        self.assertEqual(signal.action, EntryAction.BUY)
        self.assertGreater(signal.confidence, 0.35)

    def test_analyze_full_sell_signal(self):
        """統合分析テスト - SELLシグナル"""
        # 条件: レンジ相場 + 消尽 + RSI高い → SELL
        sell_df = self.test_df.copy()
        sell_df["adx_14"] = 20  # レンジ相場
        sell_df["high"] = 10225000  # 消尽率 90%
        sell_df["low"] = 9775000
        sell_df["rsi_14"] = 70  # RSI高い → SELL方向

        signal = self.strategy.analyze(sell_df)

        self.assertEqual(signal.action, EntryAction.SELL)
        self.assertGreater(signal.confidence, 0.35)

    def test_analyze_hold_trend_market(self):
        """統合分析テスト - トレンド相場でHOLD"""
        trend_df = self.test_df.copy()
        trend_df["adx_14"] = 35  # トレンド相場

        signal = self.strategy.analyze(trend_df)

        self.assertEqual(signal.action, EntryAction.HOLD)

    def test_analyze_hold_not_exhausted(self):
        """統合分析テスト - 未消尽でHOLD"""
        not_exhausted_df = self.test_df.copy()
        not_exhausted_df["high"] = 10100000  # 消尽率 40%
        not_exhausted_df["low"] = 9900000

        signal = self.strategy.analyze(not_exhausted_df)

        self.assertEqual(signal.action, EntryAction.HOLD)

    def test_analyze_hold_neutral_rsi(self):
        """統合分析テスト - RSI中立でHOLD"""
        neutral_df = self.test_df.copy()
        neutral_df["adx_14"] = 20  # レンジ相場
        neutral_df["high"] = 10225000  # 消尽率 90%
        neutral_df["low"] = 9775000
        neutral_df["rsi_14"] = 50  # RSI中立

        signal = self.strategy.analyze(neutral_df)

        self.assertEqual(signal.action, EntryAction.HOLD)

    def test_get_required_features(self):
        """必要特徴量リスト取得テスト"""
        features = self.strategy.get_required_features()

        # Phase 55.4 Approach B: BB位置確認用にbb_upper, bb_lower追加
        required = ["close", "high", "low", "atr_14", "adx_14", "rsi_14", "bb_upper", "bb_lower"]
        for feature in required:
            self.assertIn(feature, features)

        self.assertEqual(len(features), 8)

    def test_create_decision_high_exhaustion(self):
        """統合判定テスト - 高消尽"""
        exhaustion = {
            "ratio": 0.90,
            "is_exhausted": True,
            "is_high_exhaustion": True,
            "reason": "高消尽",
        }
        direction = {
            "action": EntryAction.BUY,
            "rsi": 30,
            "strength": 0.5,
            "reason": "BUY方向",
        }
        range_check = {"is_range": True, "adx": 20, "reason": "レンジ"}

        decision = self.strategy._create_decision(exhaustion, direction, range_check)

        self.assertEqual(decision["action"], EntryAction.BUY)
        self.assertGreaterEqual(decision["confidence"], 0.60)  # 高信頼度

    def test_create_decision_normal_exhaustion(self):
        """統合判定テスト - 通常消尽"""
        exhaustion = {
            "ratio": 0.75,
            "is_exhausted": True,
            "is_high_exhaustion": False,
            "reason": "消尽",
        }
        direction = {
            "action": EntryAction.SELL,
            "rsi": 70,
            "strength": 0.5,
            "reason": "SELL方向",
        }
        range_check = {"is_range": True, "adx": 20, "reason": "レンジ"}

        decision = self.strategy._create_decision(exhaustion, direction, range_check)

        self.assertEqual(decision["action"], EntryAction.SELL)
        self.assertGreaterEqual(decision["confidence"], 0.40)  # 基本信頼度
        self.assertLess(decision["confidence"], 0.60)

    def test_analyze_with_multi_timeframe_data(self):
        """マルチタイムフレームデータを使用した分析テスト"""
        multi_tf_data = {
            "15m": pd.DataFrame(
                {
                    "close": [10500000],
                    "atr_14": [300000],
                }
            )
        }

        # BUYシグナル条件
        buy_df = self.test_df.copy()
        buy_df["adx_14"] = 20
        buy_df["high"] = 10225000
        buy_df["low"] = 9775000
        buy_df["rsi_14"] = 30

        signal = self.strategy.analyze(buy_df, multi_timeframe_data=multi_tf_data)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, EntryAction.BUY)

    def test_calculate_exhaustion_ratio_error_handling(self):
        """消尽率計算エラーハンドリングテスト"""
        error_df = self.test_df.copy()
        error_df["atr_14"] = None

        result = self.strategy._calculate_exhaustion_ratio(error_df)

        self.assertEqual(result["ratio"], 0.0)
        self.assertFalse(result["is_exhausted"])
        self.assertIn("計算エラー", result["reason"])

    def test_determine_reversal_direction_error_handling(self):
        """反転方向判定エラーハンドリングテスト"""
        error_df = self.test_df.copy()
        error_df["rsi_14"] = None

        result = self.strategy._determine_reversal_direction(error_df)

        self.assertEqual(result["action"], EntryAction.HOLD)
        self.assertIn("判定エラー", result["reason"])

    def test_confidence_max_limit(self):
        """信頼度上限テスト"""
        exhaustion = {
            "ratio": 0.95,
            "is_exhausted": True,
            "is_high_exhaustion": True,
            "reason": "高消尽",
        }
        direction = {
            "action": EntryAction.BUY,
            "rsi": 20,  # 非常に強いシグナル
            "strength": 1.0,
            "reason": "BUY方向",
        }
        range_check = {"is_range": True, "adx": 15, "reason": "レンジ"}

        decision = self.strategy._create_decision(exhaustion, direction, range_check)

        self.assertLessEqual(decision["confidence"], 0.75)  # 上限0.75


def run_atr_based_tests():
    """ATRレンジ消尽戦略テスト実行関数"""
    print("=" * 50)
    print("ATRレンジ消尽戦略 テスト開始")
    print("=" * 50)

    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("ATRレンジ消尽戦略 テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_atr_based_tests()
