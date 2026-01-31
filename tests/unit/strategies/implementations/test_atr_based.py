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
        no_adx_df = self.test_df.copy().drop(columns=["adx_14"])

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


class TestATRBasedStrategyAdvanced(unittest.TestCase):
    """ATRレンジ消尽戦略 追加テストクラス（カバレッジ向上用）"""

    def setUp(self):
        """テスト前準備"""
        dates = pd.date_range(start="2025-08-01", periods=100, freq="1h")
        base_price = 10000000

        # BB帯端のテストデータ（BB位置メインモード用）
        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "close": np.full(100, base_price),
                "high": np.full(100, base_price + 225000),  # 消尽率90%
                "low": np.full(100, base_price - 225000),
                "atr_14": np.full(100, 500000),
                "adx_14": np.full(100, 20),  # レンジ相場
                "rsi_14": np.full(100, 50),
                "bb_upper": np.full(100, base_price + 200000),
                "bb_lower": np.full(100, base_price - 200000),
                "volume": np.random.uniform(100, 200, 100),
            }
        )

        # BB位置メインモード有効化
        self.strategy = ATRBasedStrategy({"bb_as_main_condition": True})

    # ===== _check_bb_position テスト =====
    def test_check_bb_position_at_lower_band(self):
        """BB位置確認テスト - 下端"""
        lower_df = self.test_df.copy()
        lower_df["close"] = 9850000  # BB下端付近

        result = self.strategy._check_bb_position(lower_df)

        self.assertTrue(result["at_band_edge"])
        self.assertEqual(result["direction"], "BUY")
        self.assertLess(result["position"], 0.20)

    def test_check_bb_position_at_upper_band(self):
        """BB位置確認テスト - 上端"""
        upper_df = self.test_df.copy()
        upper_df["close"] = 10150000  # BB上端付近

        result = self.strategy._check_bb_position(upper_df)

        self.assertTrue(result["at_band_edge"])
        self.assertEqual(result["direction"], "SELL")
        self.assertGreater(result["position"], 0.80)

    def test_check_bb_position_middle(self):
        """BB位置確認テスト - 中間"""
        middle_df = self.test_df.copy()
        middle_df["close"] = 10000000  # BB中間

        result = self.strategy._check_bb_position(middle_df)

        self.assertFalse(result["at_band_edge"])
        self.assertEqual(result["direction"], "HOLD")

    def test_check_bb_position_no_bb_data(self):
        """BB位置確認テスト - BBデータなし"""
        no_bb_df = self.test_df.copy().drop(columns=["bb_upper", "bb_lower"])

        result = self.strategy._check_bb_position(no_bb_df)

        self.assertFalse(result["at_band_edge"])
        self.assertEqual(result["direction"], "HOLD")
        self.assertIn("BBデータなし", result["reason"])

    def test_check_bb_position_zero_width(self):
        """BB位置確認テスト - BB幅ゼロ"""
        zero_width_df = self.test_df.copy()
        zero_width_df["bb_upper"] = 10000000
        zero_width_df["bb_lower"] = 10000000

        result = self.strategy._check_bb_position(zero_width_df)

        self.assertFalse(result["at_band_edge"])
        self.assertEqual(result["direction"], "HOLD")
        self.assertIn("BB幅ゼロ", result["reason"])

    def test_check_bb_position_error_handling(self):
        """BB位置確認テスト - エラーハンドリング"""
        error_df = self.test_df.copy()
        error_df["bb_upper"] = None
        error_df["bb_lower"] = None

        result = self.strategy._check_bb_position(error_df)

        self.assertFalse(result["at_band_edge"])
        self.assertEqual(result["direction"], "HOLD")
        self.assertIn("判定エラー", result["reason"])

    # ===== _check_rsi_confirmation テスト =====
    def test_check_rsi_confirmation_buy_confirms(self):
        """RSI確認テスト - BUY方向確認"""
        low_rsi_df = self.test_df.copy()
        low_rsi_df["rsi_14"] = 30

        result = self.strategy._check_rsi_confirmation(low_rsi_df, "BUY")

        self.assertTrue(result["confirms"])
        self.assertEqual(result["rsi"], 30)

    def test_check_rsi_confirmation_sell_confirms(self):
        """RSI確認テスト - SELL方向確認"""
        high_rsi_df = self.test_df.copy()
        high_rsi_df["rsi_14"] = 70

        result = self.strategy._check_rsi_confirmation(high_rsi_df, "SELL")

        self.assertTrue(result["confirms"])
        self.assertEqual(result["rsi"], 70)

    def test_check_rsi_confirmation_no_match(self):
        """RSI確認テスト - 方向不一致"""
        neutral_rsi_df = self.test_df.copy()
        neutral_rsi_df["rsi_14"] = 50

        result = self.strategy._check_rsi_confirmation(neutral_rsi_df, "BUY")

        self.assertFalse(result["confirms"])
        self.assertIn("中間", result["reason"])

    def test_check_rsi_confirmation_error_handling(self):
        """RSI確認テスト - エラーハンドリング"""
        error_df = self.test_df.copy()
        error_df["rsi_14"] = None

        result = self.strategy._check_rsi_confirmation(error_df, "BUY")

        self.assertFalse(result["confirms"])
        self.assertEqual(result["rsi"], 50.0)
        self.assertIn("確認エラー", result["reason"])

    # ===== _analyze_bb_main_mode テスト =====
    def test_analyze_bb_main_mode_buy_signal(self):
        """BB主導モード分析テスト - BUYシグナル"""
        buy_df = self.test_df.copy()
        buy_df["close"] = 9850000  # BB下端
        buy_df["rsi_14"] = 30  # RSI確認成功

        signal = self.strategy.analyze(buy_df)

        self.assertEqual(signal.action, EntryAction.BUY)
        self.assertGreater(signal.confidence, 0.35)

    def test_analyze_bb_main_mode_sell_signal(self):
        """BB主導モード分析テスト - SELLシグナル"""
        sell_df = self.test_df.copy()
        sell_df["close"] = 10150000  # BB上端
        sell_df["rsi_14"] = 70  # RSI確認成功

        signal = self.strategy.analyze(sell_df)

        self.assertEqual(signal.action, EntryAction.SELL)
        self.assertGreater(signal.confidence, 0.35)

    def test_analyze_bb_main_mode_hold_middle(self):
        """BB主導モード分析テスト - 中間でHOLD"""
        middle_df = self.test_df.copy()
        middle_df["close"] = 10000000  # BB中間

        signal = self.strategy.analyze(middle_df)

        self.assertEqual(signal.action, EntryAction.HOLD)

    def test_analyze_bb_main_mode_with_rsi_bonus(self):
        """BB主導モード分析テスト - RSIボーナス付き"""
        buy_df = self.test_df.copy()
        buy_df["close"] = 9850000  # BB下端
        buy_df["rsi_14"] = 25  # 強いRSI確認

        signal = self.strategy.analyze(buy_df)

        self.assertEqual(signal.action, EntryAction.BUY)
        # RSI確認ボーナスで信頼度上昇
        self.assertGreaterEqual(signal.confidence, 0.40)

    def test_analyze_bb_main_mode_high_exhaustion(self):
        """BB主導モード分析テスト - 高消尽での信頼度"""
        buy_df = self.test_df.copy()
        buy_df["close"] = 9850000  # BB下端
        buy_df["high"] = 10235000  # 消尽率 94%
        buy_df["low"] = 9765000

        signal = self.strategy.analyze(buy_df)

        self.assertEqual(signal.action, EntryAction.BUY)
        # 高消尽でより高い信頼度
        self.assertGreaterEqual(signal.confidence, 0.55)

    # ===== _infer_direction_from_price テスト =====
    def test_infer_direction_from_price_sell(self):
        """価格変動からの方向推定テスト - SELL"""
        up_df = self.test_df.copy()
        # 直近5本で上昇
        up_df.iloc[-5:, up_df.columns.get_loc("close")] = [
            9960000,
            9980000,
            10000000,
            10020000,
            10050000,
        ]

        result = self.strategy._infer_direction_from_price(up_df)

        self.assertEqual(result["action"], EntryAction.SELL)
        self.assertIn("価格上昇後", result["reason"])

    def test_infer_direction_from_price_buy(self):
        """価格変動からの方向推定テスト - BUY"""
        down_df = self.test_df.copy()
        # 直近5本で下落
        down_df.iloc[-5:, down_df.columns.get_loc("close")] = [
            10050000,
            10020000,
            10000000,
            9980000,
            9960000,
        ]

        result = self.strategy._infer_direction_from_price(down_df)

        self.assertEqual(result["action"], EntryAction.BUY)
        self.assertIn("価格下落後", result["reason"])

    def test_infer_direction_from_price_hold(self):
        """価格変動からの方向推定テスト - HOLD"""
        flat_df = self.test_df.copy()
        # 直近5本で変動なし
        flat_df.iloc[-5:, flat_df.columns.get_loc("close")] = [
            10000000,
            10000100,
            10000050,
            10000100,
            10000050,
        ]

        result = self.strategy._infer_direction_from_price(flat_df)

        self.assertEqual(result["action"], EntryAction.HOLD)
        self.assertIn("価格変動不足", result["reason"])

    def test_infer_direction_from_price_error_handling(self):
        """価格変動からの方向推定テスト - エラーハンドリング"""
        error_df = self.test_df.copy()
        error_df["close"] = None

        result = self.strategy._infer_direction_from_price(error_df)

        self.assertEqual(result["action"], EntryAction.HOLD)
        self.assertIn("推定エラー", result["reason"])

    # ===== _create_decision_with_score テスト =====
    def test_create_decision_with_score_high_score(self):
        """スコアベース判定テスト - 高スコア"""
        exhaustion = {
            "ratio": 0.90,
            "is_exhausted": True,
            "is_high_exhaustion": True,
        }
        direction = {
            "action": EntryAction.BUY,
            "rsi": 30,
            "strength": 0.5,
        }
        range_check = {"is_range": True, "adx": 20}

        decision = self.strategy._create_decision_with_score(
            exhaustion, direction, range_check, score=0.85
        )

        self.assertEqual(decision["action"], EntryAction.BUY)
        self.assertGreater(decision["confidence"], 0.50)
        self.assertIn("スコア=0.85", decision["analysis"])

    def test_create_decision_with_score_low_score(self):
        """スコアベース判定テスト - 低スコア"""
        exhaustion = {
            "ratio": 0.75,
            "is_exhausted": True,
            "is_high_exhaustion": False,
        }
        direction = {
            "action": EntryAction.SELL,
            "rsi": 60,
            "strength": 0.1,
        }
        range_check = {"is_range": True, "adx": 22}

        decision = self.strategy._create_decision_with_score(
            exhaustion, direction, range_check, score=0.55
        )

        self.assertEqual(decision["action"], EntryAction.SELL)
        self.assertGreaterEqual(decision["confidence"], 0.35)  # min_confidence

    def test_create_decision_with_score_max_limit(self):
        """スコアベース判定テスト - 上限チェック"""
        exhaustion = {
            "ratio": 0.95,
            "is_exhausted": True,
            "is_high_exhaustion": True,
        }
        direction = {
            "action": EntryAction.BUY,
            "rsi": 20,
            "strength": 1.0,
        }
        range_check = {"is_range": True, "adx": 15}

        decision = self.strategy._create_decision_with_score(
            exhaustion, direction, range_check, score=1.0
        )

        self.assertLessEqual(decision["confidence"], 0.75)

    # ===== 境界値テスト =====
    def test_exhaustion_threshold_boundary_just_below(self):
        """消尽閾値境界テスト - ぎりぎり未達"""
        threshold = self.strategy.config["exhaustion_threshold"]
        # 閾値直下の消尽率を設定
        boundary_df = self.test_df.copy()
        # 閾値の99%の値幅
        target_range = 500000 * (threshold - 0.01)  # ATR * (threshold - 0.01)
        boundary_df["high"] = 10000000 + target_range / 2
        boundary_df["low"] = 10000000 - target_range / 2

        result = self.strategy._calculate_exhaustion_ratio(boundary_df)

        self.assertFalse(result["is_exhausted"])
        self.assertIn("未消尽", result["reason"])

    def test_exhaustion_threshold_boundary_just_above(self):
        """消尽閾値境界テスト - ぎりぎり達成"""
        threshold = self.strategy.config["exhaustion_threshold"]
        # 閾値直上の消尽率を設定
        boundary_df = self.test_df.copy()
        target_range = 500000 * (threshold + 0.01)  # ATR * (threshold + 0.01)
        boundary_df["high"] = 10000000 + target_range / 2
        boundary_df["low"] = 10000000 - target_range / 2

        result = self.strategy._calculate_exhaustion_ratio(boundary_df)

        self.assertTrue(result["is_exhausted"])
        self.assertIn("消尽", result["reason"])

    def test_adx_threshold_boundary_just_below(self):
        """ADX閾値境界テスト - ぎりぎりレンジ"""
        threshold = self.strategy.config["adx_range_threshold"]
        boundary_df = self.test_df.copy()
        boundary_df["adx_14"] = threshold - 0.1

        result = self.strategy._check_range_market(boundary_df)

        self.assertTrue(result["is_range"])

    def test_adx_threshold_boundary_just_above(self):
        """ADX閾値境界テスト - ぎりぎりトレンド"""
        threshold = self.strategy.config["adx_range_threshold"]
        boundary_df = self.test_df.copy()
        boundary_df["adx_14"] = threshold + 0.1

        result = self.strategy._check_range_market(boundary_df)

        self.assertFalse(result["is_range"])

    def test_rsi_upper_boundary(self):
        """RSI上限境界テスト"""
        rsi_upper = self.strategy.config["rsi_upper"]
        boundary_df = self.test_df.copy()

        # ぎりぎり上限超え → SELL
        boundary_df["rsi_14"] = rsi_upper + 0.1
        result = self.strategy._determine_reversal_direction(boundary_df)
        self.assertEqual(result["action"], EntryAction.SELL)

        # ぎりぎり上限未満 → HOLD
        boundary_df["rsi_14"] = rsi_upper - 0.1
        result = self.strategy._determine_reversal_direction(boundary_df)
        self.assertEqual(result["action"], EntryAction.HOLD)

    def test_rsi_lower_boundary(self):
        """RSI下限境界テスト"""
        rsi_lower = self.strategy.config["rsi_lower"]
        boundary_df = self.test_df.copy()

        # ぎりぎり下限未満 → BUY
        boundary_df["rsi_14"] = rsi_lower - 0.1
        result = self.strategy._determine_reversal_direction(boundary_df)
        self.assertEqual(result["action"], EntryAction.BUY)

        # ぎりぎり下限超え → HOLD
        boundary_df["rsi_14"] = rsi_lower + 0.1
        result = self.strategy._determine_reversal_direction(boundary_df)
        self.assertEqual(result["action"], EntryAction.HOLD)

    # ===== 従来モード（bb_as_main_condition=False）のテスト =====
    def test_analyze_legacy_mode_with_bb_bonus_match(self):
        """従来モードテスト - BB帯端一致ボーナス"""
        legacy_strategy = ATRBasedStrategy(
            {"bb_as_main_condition": False, "bb_position_enabled": True}
        )

        buy_df = self.test_df.copy()
        buy_df["close"] = 9850000  # BB下端
        buy_df["rsi_14"] = 30  # RSI低い → BUY方向
        buy_df["high"] = 10225000  # 消尽率 90%
        buy_df["low"] = 9775000

        signal = legacy_strategy.analyze(buy_df)

        self.assertEqual(signal.action, EntryAction.BUY)
        # BB帯端一致で信頼度上昇

    def test_analyze_legacy_mode_with_bb_bonus_no_match(self):
        """従来モードテスト - BB帯端不一致ボーナス"""
        legacy_strategy = ATRBasedStrategy(
            {"bb_as_main_condition": False, "bb_position_enabled": True}
        )

        # RSIはBUY方向だがBBは上端（不一致）
        mixed_df = self.test_df.copy()
        mixed_df["close"] = 10150000  # BB上端
        mixed_df["rsi_14"] = 30  # RSI低い → BUY方向
        mixed_df["high"] = 10225000  # 消尽率 90%
        mixed_df["low"] = 9775000

        signal = legacy_strategy.analyze(mixed_df)

        self.assertEqual(signal.action, EntryAction.BUY)

    def test_analyze_legacy_mode_rsi_hold(self):
        """従来モードテスト - RSI中立でHOLD"""
        legacy_strategy = ATRBasedStrategy({"bb_as_main_condition": False})

        hold_df = self.test_df.copy()
        hold_df["rsi_14"] = 50  # RSI中立
        hold_df["high"] = 10225000  # 消尽率 90%
        hold_df["low"] = 9775000

        signal = legacy_strategy.analyze(hold_df)

        self.assertEqual(signal.action, EntryAction.HOLD)

    # ===== エラーハンドリングテスト =====
    def test_check_range_market_error_handling(self):
        """レンジ判定エラーハンドリングテスト"""
        error_df = self.test_df.copy()
        error_df["adx_14"] = None

        result = self.strategy._check_range_market(error_df)

        self.assertTrue(result["is_range"])  # エラー時はレンジと仮定
        self.assertIn("判定エラー", result["reason"])

    def test_analyze_exception_handling(self):
        """分析メソッドの例外ハンドリングテスト"""
        from src.core.exceptions import StrategyError

        # 必須カラムがない場合
        invalid_df = pd.DataFrame({"invalid_column": [1, 2, 3]})

        with self.assertRaises(StrategyError):
            self.strategy.analyze(invalid_df)

    def test_calculate_exhaustion_ratio_zero_atr(self):
        """消尽率計算テスト - ATRゼロ"""
        zero_atr_df = self.test_df.copy()
        zero_atr_df["atr_14"] = 0

        result = self.strategy._calculate_exhaustion_ratio(zero_atr_df)

        self.assertEqual(result["ratio"], 0.0)
        self.assertFalse(result["is_exhausted"])

    # ===== 特殊ケーステスト =====
    def test_analyze_with_empty_multi_timeframe_data(self):
        """空のマルチタイムフレームデータでの分析テスト"""
        buy_df = self.test_df.copy()
        buy_df["close"] = 9850000  # BB下端

        signal = self.strategy.analyze(buy_df, multi_timeframe_data={})

        self.assertIsNotNone(signal)

    def test_analyze_with_none_multi_timeframe_data(self):
        """Noneのマルチタイムフレームデータでの分析テスト"""
        buy_df = self.test_df.copy()
        buy_df["close"] = 9850000  # BB下端

        signal = self.strategy.analyze(buy_df, multi_timeframe_data=None)

        self.assertIsNotNone(signal)

    def test_strategy_custom_config(self):
        """カスタム設定での戦略初期化テスト"""
        custom_config = {
            "exhaustion_threshold": 0.80,
            "high_exhaustion_threshold": 0.95,
            "adx_range_threshold": 30,
            "rsi_upper": 65,
            "rsi_lower": 35,
            "min_confidence": 0.40,
        }

        custom_strategy = ATRBasedStrategy(custom_config)

        self.assertEqual(custom_strategy.config["exhaustion_threshold"], 0.80)
        self.assertEqual(custom_strategy.config["high_exhaustion_threshold"], 0.95)
        self.assertEqual(custom_strategy.config["adx_range_threshold"], 30)

    def test_bb_position_threshold_custom(self):
        """カスタムBB位置閾値テスト"""
        custom_strategy = ATRBasedStrategy({"bb_position_threshold": 0.15})

        # 15%閾値で中間判定になるケース
        # BB幅 = 400000 (10200000 - 9800000)
        # 25%位置 = 9800000 + 400000 * 0.25 = 9900000
        # 15%閾値では、0.15未満が下端、0.85超が上端
        middle_df = self.test_df.copy()
        middle_df["close"] = 9920000  # 30%位置 (0.15 < 0.30 < 0.85で中間)

        result = custom_strategy._check_bb_position(middle_df)

        self.assertFalse(result["at_band_edge"])

    def test_create_decision_min_confidence_floor(self):
        """判定結果の最小信頼度テスト"""
        exhaustion = {
            "ratio": 0.71,  # ぎりぎり消尽
            "is_exhausted": True,
            "is_high_exhaustion": False,
        }
        direction = {
            "action": EntryAction.BUY,
            "rsi": 39,  # ぎりぎりBUY
            "strength": 0.05,  # 非常に弱い
        }
        range_check = {"is_range": True, "adx": 24}

        decision = self.strategy._create_decision(exhaustion, direction, range_check)

        self.assertGreaterEqual(decision["confidence"], self.strategy.config["min_confidence"])

    # ===== 残りエッジケーステスト（カバレッジ向上用）=====
    def test_analyze_bb_main_mode_normal_exhaustion(self):
        """BB主導モード - 通常消尽での信頼度（base_confidence使用）"""
        # 通常消尽（high_exhaustionでない）
        normal_df = self.test_df.copy()
        normal_df["close"] = 9850000  # BB下端
        normal_df["high"] = 10175000  # 消尽率 70%（閾値ぎりぎり）
        normal_df["low"] = 9825000

        signal = self.strategy.analyze(normal_df)

        self.assertEqual(signal.action, EntryAction.BUY)
        # base_confidence使用（high_confidenceより低い）
        self.assertLess(signal.confidence, 0.60)

    def test_legacy_mode_min_confidence_floor(self):
        """従来モード - 最小信頼度フロア適用"""
        # strengthが0で信頼度が低くなるケース
        legacy_strategy = ATRBasedStrategy({
            "bb_as_main_condition": False,
            "base_confidence": 0.30,  # 低い基本信頼度
            "min_confidence": 0.35,   # 最小信頼度
        })

        exhaustion = {
            "ratio": 0.72,
            "is_exhausted": True,
            "is_high_exhaustion": False,
        }
        direction = {
            "action": EntryAction.BUY,
            "rsi": 39.9,  # ぎりぎりBUY（strength極小）
            "strength": 0.005,  # 非常に小さいstrength
        }
        range_check = {"is_range": True, "adx": 24}

        decision = legacy_strategy._create_decision(exhaustion, direction, range_check)

        # min_confidenceが適用されることを確認
        self.assertGreaterEqual(decision["confidence"], legacy_strategy.config["min_confidence"])


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
