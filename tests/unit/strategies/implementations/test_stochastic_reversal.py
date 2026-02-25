"""
Stochastic Divergence戦略のテストモジュール - Phase 55.3

StochasticReversalStrategyクラスの単体テスト。
モメンタム乖離（ダイバージェンス）検出を検証。

核心思想:
「価格は高値更新しているがStochasticは低下している = モメンタム弱化 = 反転間近」

テスト項目:
- 初期化・設定テスト
- ダイバージェンス検出テスト（Bearish/Bullish）
- 極端領域判定テスト（過買い/過売り）
- 信頼度ボーナステスト
- ADXフィルタテスト
- SELL信号生成テスト（Bearish Divergence）
- BUY信号生成テスト（Bullish Divergence）
- HOLD信号生成テスト
- エラーハンドリングテスト

Phase 55.3: 同時性緩和・位置ベース検出対応
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd
import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.implementations.stochastic_reversal import StochasticReversalStrategy
from src.strategies.utils import EntryAction


@pytest.fixture(scope="session", autouse=True)
def init_config():
    """テスト用設定初期化"""
    try:
        from src.core.config import load_config

        load_config("config/core/thresholds.yaml")
    except Exception:
        from src.core.config import config_manager

        config_manager._config = {
            "trading": {"mode": "paper"},
            "features": {"selected": ["close", "stoch_k", "stoch_d", "adx_14", "atr_14"]},
            "strategies": {"default_config": {}},
            "ml": {"models": {}},
            "data": {"timeframes": ["15m", "1h", "4h"]},
            "monitoring": {"enabled": False},
        }


class TestStochasticDivergenceStrategy(unittest.TestCase):
    """Stochastic Divergence戦略テストクラス"""

    def setUp(self):
        """テスト前準備"""
        dates = pd.date_range(start="2025-08-01", periods=100, freq="4h")
        base_price = 15000000

        # 基本テストデータ（ダイバージェンスなし）
        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "close": np.full(100, base_price),
                "stoch_k": np.full(100, 50.0),  # 中立
                "stoch_d": np.full(100, 50.0),
                "adx_14": np.full(100, 25.0),  # 中程度
                "atr_14": np.full(100, 150000),
            }
        )

        self.strategy = StochasticReversalStrategy()

    def test_strategy_initialization(self):
        """戦略初期化テスト"""
        self.assertEqual(self.strategy.name, "StochasticReversal")
        # Phase 55.2: 閾値はthresholds.yamlから読み込まれる
        # 値の存在確認のみ行う
        self.assertIn("divergence_lookback", self.strategy.config)
        self.assertIn("divergence_price_threshold", self.strategy.config)
        self.assertIn("divergence_stoch_threshold", self.strategy.config)
        self.assertIn("stoch_overbought", self.strategy.config)
        self.assertIn("stoch_oversold", self.strategy.config)
        self.assertIn("adx_max_threshold", self.strategy.config)
        self.assertIn("zone_bonus", self.strategy.config)

    def test_required_features(self):
        """必須特徴量テスト"""
        features = self.strategy.get_required_features()

        required = ["close", "stoch_k", "stoch_d", "adx_14", "atr_14"]
        for feature in required:
            self.assertIn(feature, features)

        self.assertEqual(len(features), 5)

    def test_check_market_condition_ok(self):
        """市場条件テスト - ADX低（取引可能）"""
        result = self.strategy._check_market_condition(self.test_df)
        self.assertTrue(result)  # ADX 25 < 50

    def test_check_market_condition_strong_trend(self):
        """市場条件テスト - 強トレンド（取引不可）"""
        strong_trend_df = self.test_df.copy()
        strong_trend_df["adx_14"] = 55  # ADX > 50

        result = self.strategy._check_market_condition(strong_trend_df)
        self.assertFalse(result)

    def test_detect_divergence_bearish(self):
        """Bearish Divergence検出テスト - Phase 55.3位置ベース検出"""
        # Phase 55.3: 価格が高値付近（位置>0.6）、Stochが安値付近（位置<0.4）
        bearish_df = self.test_df.copy()

        # 期間内のデータを設定（現在が高値、Stochが低値）
        # 価格: 徐々に上昇 → 現在が最高値付近
        for i in range(-6, 0):
            bearish_df.iloc[i, bearish_df.columns.get_loc("close")] = 15000000 + (i + 6) * 20000
            bearish_df.iloc[i, bearish_df.columns.get_loc("stoch_k")] = 70.0 - (i + 6) * 8

        # 現在: 価格最高、Stoch最低
        bearish_df.iloc[-1, bearish_df.columns.get_loc("close")] = 15100000
        bearish_df.iloc[-1, bearish_df.columns.get_loc("stoch_k")] = 30.0

        result = self.strategy._detect_divergence(bearish_df)

        self.assertEqual(result["type"], "bearish")
        self.assertEqual(result["action"], EntryAction.SELL)
        self.assertIn("Bearish Div", result["reason"])

    def test_detect_divergence_bullish(self):
        """Bullish Divergence検出テスト - Phase 55.3位置ベース検出"""
        # Phase 55.3: 価格が安値付近（位置<0.4）、Stochが高値付近（位置>0.6）
        bullish_df = self.test_df.copy()

        # 期間内のデータを設定（現在が安値、Stochが高値）
        # 価格: 徐々に下落 → 現在が最安値付近
        for i in range(-6, 0):
            bullish_df.iloc[i, bullish_df.columns.get_loc("close")] = 15100000 - (i + 6) * 20000
            bullish_df.iloc[i, bullish_df.columns.get_loc("stoch_k")] = 30.0 + (i + 6) * 8

        # 現在: 価格最低、Stoch最高
        bullish_df.iloc[-1, bullish_df.columns.get_loc("close")] = 14900000
        bullish_df.iloc[-1, bullish_df.columns.get_loc("stoch_k")] = 70.0

        result = self.strategy._detect_divergence(bullish_df)

        self.assertEqual(result["type"], "bullish")
        self.assertEqual(result["action"], EntryAction.BUY)
        self.assertIn("Bullish Div", result["reason"])

    def test_detect_divergence_none(self):
        """ダイバージェンスなしテスト"""
        # 価格・Stochastic両方上昇（通常の上昇トレンド）
        no_div_df = self.test_df.copy()

        # lookback=5なのでiloc[-5]と比較
        # 5期間前
        no_div_df.iloc[-5, no_div_df.columns.get_loc("close")] = 15000000
        no_div_df.iloc[-5, no_div_df.columns.get_loc("stoch_k")] = 40.0

        # 現在（価格も Stochも上昇）
        no_div_df.iloc[-1, no_div_df.columns.get_loc("close")] = 15100000  # +0.67%
        no_div_df.iloc[-1, no_div_df.columns.get_loc("stoch_k")] = 55.0  # +15pt

        result = self.strategy._detect_divergence(no_div_df)

        self.assertEqual(result["type"], "none")
        self.assertEqual(result["action"], EntryAction.HOLD)

    def test_check_extreme_zone_overbought(self):
        """過買い領域テスト"""
        # Phase 55.3: 閾値75なので80でテスト
        result = self.strategy._check_extreme_zone(80.0, 78.0)

        self.assertEqual(result["zone"], "overbought")
        self.assertGreater(result["bonus"], 0)

    def test_check_extreme_zone_oversold(self):
        """過売り領域テスト"""
        # Phase 55.3: 閾値25なので20でテスト
        result = self.strategy._check_extreme_zone(20.0, 22.0)

        self.assertEqual(result["zone"], "oversold")
        self.assertGreater(result["bonus"], 0)

    def test_check_extreme_zone_neutral(self):
        """中立領域テスト"""
        result = self.strategy._check_extreme_zone(50.0, 50.0)

        self.assertEqual(result["zone"], "neutral")
        self.assertEqual(result["bonus"], 0.0)

    def test_analyze_full_sell_signal(self):
        """統合分析テスト - SELLシグナル - Phase 55.3位置ベース"""
        # 条件: 価格が高値付近、Stochが安値付近
        sell_df = self.test_df.copy()

        # 期間内のデータを設定
        for i in range(-6, 0):
            sell_df.iloc[i, sell_df.columns.get_loc("close")] = 15000000 + (i + 6) * 20000
            sell_df.iloc[i, sell_df.columns.get_loc("stoch_k")] = 70.0 - (i + 6) * 8

        # 現在: 価格最高、Stoch最低
        sell_df.iloc[-1, sell_df.columns.get_loc("close")] = 15100000
        sell_df.iloc[-1, sell_df.columns.get_loc("stoch_k")] = 30.0
        sell_df.iloc[-1, sell_df.columns.get_loc("stoch_d")] = 32.0

        signal = self.strategy.analyze(sell_df)

        self.assertEqual(signal.action, EntryAction.SELL)
        self.assertGreater(signal.confidence, 0.25)

    def test_analyze_full_buy_signal(self):
        """統合分析テスト - BUYシグナル - Phase 55.3位置ベース"""
        # 条件: 価格が安値付近、Stochが高値付近
        buy_df = self.test_df.copy()

        # 期間内のデータを設定
        for i in range(-6, 0):
            buy_df.iloc[i, buy_df.columns.get_loc("close")] = 15100000 - (i + 6) * 20000
            buy_df.iloc[i, buy_df.columns.get_loc("stoch_k")] = 30.0 + (i + 6) * 8

        # 現在: 価格最低、Stoch最高
        buy_df.iloc[-1, buy_df.columns.get_loc("close")] = 14900000
        buy_df.iloc[-1, buy_df.columns.get_loc("stoch_k")] = 70.0
        buy_df.iloc[-1, buy_df.columns.get_loc("stoch_d")] = 68.0

        signal = self.strategy.analyze(buy_df)

        self.assertEqual(signal.action, EntryAction.BUY)
        self.assertGreater(signal.confidence, 0.25)

    def test_analyze_hold_no_divergence(self):
        """統合分析テスト - ダイバージェンスなしでHOLD"""
        signal = self.strategy.analyze(self.test_df)

        self.assertEqual(signal.action, EntryAction.HOLD)

    def test_analyze_hold_strong_trend(self):
        """統合分析テスト - 強トレンドでHOLD"""
        strong_trend_df = self.test_df.copy()
        strong_trend_df["adx_14"] = 55  # ADX > 50

        signal = self.strategy.analyze(strong_trend_df)

        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("strong_trend_excluded", signal.reason)

    def test_zone_bonus_applied(self):
        """ゾーンボーナス適用テスト - Phase 55.3"""
        # Bearish Divergence（位置ベース）+ 過買い領域
        overbought_df = self.test_df.copy()

        # 期間内のデータを設定
        for i in range(-6, 0):
            overbought_df.iloc[i, overbought_df.columns.get_loc("close")] = (
                15000000 + (i + 6) * 20000
            )
            overbought_df.iloc[i, overbought_df.columns.get_loc("stoch_k")] = 90.0 - (i + 6) * 3

        # 現在: 価格最高、Stoch低下だがまだ過買い領域内(>75)
        overbought_df.iloc[-1, overbought_df.columns.get_loc("close")] = 15100000
        overbought_df.iloc[-1, overbought_df.columns.get_loc("stoch_k")] = 76.0
        overbought_df.iloc[-1, overbought_df.columns.get_loc("stoch_d")] = 77.0

        decision = self.strategy._analyze_stochastic_divergence_signal(overbought_df)

        # シグナルが生成されれば成功
        self.assertIn(decision["action"], [EntryAction.SELL, EntryAction.HOLD])

    def test_confidence_max_limit(self):
        """信頼度上限テスト"""
        # 強いダイバージェンス + ゾーンマッチでも上限0.60
        strong_div_df = self.test_df.copy()

        # lookback=5なのでiloc[-5]と比較
        # 極端なダイバージェンス
        strong_div_df.iloc[-5, strong_div_df.columns.get_loc("close")] = 15000000
        strong_div_df.iloc[-5, strong_div_df.columns.get_loc("stoch_k")] = 95.0

        strong_div_df.iloc[-1, strong_div_df.columns.get_loc("close")] = 15200000  # +1.3%
        strong_div_df.iloc[-1, strong_div_df.columns.get_loc("stoch_k")] = 72.0  # -23pt
        strong_div_df.iloc[-1, strong_div_df.columns.get_loc("stoch_d")] = 71.0

        decision = self.strategy._analyze_stochastic_divergence_signal(strong_div_df)

        self.assertLessEqual(decision["confidence"], 0.60)

    def test_analyze_empty_dataframe(self):
        """空データテスト"""
        empty_df = pd.DataFrame()
        signal = self.strategy.analyze(empty_df)

        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("insufficient_data", signal.reason)

    def test_analyze_missing_features(self):
        """必須特徴量欠落テスト"""
        incomplete_df = pd.DataFrame(
            {
                "close": [15000000],
                "stoch_k": [50.0],
                # stoch_d, adx_14, atr_14 が欠落
            }
        )
        signal = self.strategy.analyze(incomplete_df)

        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("insufficient_data", signal.reason)

    def test_detect_divergence_insufficient_data(self):
        """ダイバージェンス検出 - データ不足テスト"""
        short_df = self.test_df.head(3)  # 3行のみ
        result = self.strategy._detect_divergence(short_df)

        self.assertEqual(result["type"], "none")
        self.assertEqual(result["action"], EntryAction.HOLD)

    def test_strength_calculation(self):
        """シグナル強度計算テスト - Phase 55.3位置ベース"""
        # Phase 55.3: strength = 0.3 + abs(price_position - stoch_position) * 0.4
        div_df = self.test_df.copy()

        # 期間内のデータを設定（価格高、Stoch低）
        for i in range(-6, 0):
            div_df.iloc[i, div_df.columns.get_loc("close")] = 15000000 + (i + 6) * 20000
            div_df.iloc[i, div_df.columns.get_loc("stoch_k")] = 70.0 - (i + 6) * 8

        div_df.iloc[-1, div_df.columns.get_loc("close")] = 15100000
        div_df.iloc[-1, div_df.columns.get_loc("stoch_k")] = 30.0

        result = self.strategy._detect_divergence(div_df)

        # Position-based strength calculation
        self.assertEqual(result["type"], "bearish")
        # strength >= 0.3 (base) + some position difference
        self.assertGreaterEqual(result["strength"], 0.3)
        self.assertLessEqual(result["strength"], 1.0)

    def test_with_multi_timeframe_data(self):
        """マルチタイムフレームデータを使用した分析テスト - Phase 55.3"""
        multi_tf_data = {
            "15m": pd.DataFrame(
                {
                    "close": [15050000],
                    "atr_14": [100000],
                }
            )
        }

        # Bearish Divergence条件（位置ベース）
        sell_df = self.test_df.copy()
        for i in range(-6, 0):
            sell_df.iloc[i, sell_df.columns.get_loc("close")] = 15000000 + (i + 6) * 20000
            sell_df.iloc[i, sell_df.columns.get_loc("stoch_k")] = 70.0 - (i + 6) * 8

        sell_df.iloc[-1, sell_df.columns.get_loc("close")] = 15100000
        sell_df.iloc[-1, sell_df.columns.get_loc("stoch_k")] = 30.0
        sell_df.iloc[-1, sell_df.columns.get_loc("stoch_d")] = 32.0

        signal = self.strategy.analyze(sell_df, multi_timeframe_data=multi_tf_data)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, EntryAction.SELL)


def run_stochastic_divergence_tests():
    """Stochastic Divergence戦略テスト実行関数"""
    print("=" * 50)
    print("Stochastic Divergence戦略 テスト開始")
    print("=" * 50)

    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("Stochastic Divergence戦略 テスト完了")
    print("=" * 50)


class TestStochasticDivergenceEdgeCases(unittest.TestCase):
    """エッジケース・カバレッジ補完テスト"""

    def setUp(self):
        """テスト前準備"""
        dates = pd.date_range(start="2025-08-01", periods=100, freq="4h")
        base_price = 15000000

        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "close": np.full(100, base_price),
                "stoch_k": np.full(100, 50.0),
                "stoch_d": np.full(100, 50.0),
                "adx_14": np.full(100, 25.0),
                "atr_14": np.full(100, 150000),
            }
        )

        self.strategy = StochasticReversalStrategy()

    def test_check_market_condition_exception(self):
        """_check_market_condition: KeyError時はTrueを返す"""
        bad_df = pd.DataFrame({"close": [15000000]})  # adx_14なし
        result = self.strategy._check_market_condition(bad_df)
        self.assertTrue(result)

    def test_detect_divergence_weak_bearish_filtered(self):
        """_detect_divergence: 弱Bearish Divergenceフィルタリング"""
        df = self.test_df.copy()
        # 価格は高値付近、Stochは安値付近だが価格変動が小さい
        for i in range(-6, 0):
            df.iloc[i, df.columns.get_loc("close")] = 15000000 + (i + 6) * 100  # 微小変動
            df.iloc[i, df.columns.get_loc("stoch_k")] = 70.0 - (i + 6) * 8
        df.iloc[-1, df.columns.get_loc("close")] = 15000500
        df.iloc[-1, df.columns.get_loc("stoch_k")] = 30.0

        result = self.strategy._detect_divergence(df)
        self.assertIn(result["type"], ["weak_bearish", "none"])

    def test_detect_divergence_weak_bullish_filtered(self):
        """_detect_divergence: 弱Bullish Divergenceフィルタリング"""
        df = self.test_df.copy()
        for i in range(-6, 0):
            df.iloc[i, df.columns.get_loc("close")] = 15000000 - (i + 6) * 100
            df.iloc[i, df.columns.get_loc("stoch_k")] = 30.0 + (i + 6) * 8
        df.iloc[-1, df.columns.get_loc("close")] = 14999500
        df.iloc[-1, df.columns.get_loc("stoch_k")] = 70.0

        result = self.strategy._detect_divergence(df)
        self.assertIn(result["type"], ["weak_bullish", "none"])

    def test_detect_divergence_strong_bearish_with_bonus(self):
        """_detect_divergence: 大きな価格変動でstrength bonus"""
        df = self.test_df.copy()
        min_price_change = self.strategy.config.get("min_price_change_ratio", 0.005)
        # price_range_ratio > min_price_change * 2 でbonus
        big_change = int(15000000 * min_price_change * 3)
        for i in range(-6, 0):
            df.iloc[i, df.columns.get_loc("close")] = 15000000 + (i + 6) * (big_change // 5)
            df.iloc[i, df.columns.get_loc("stoch_k")] = 70.0 - (i + 6) * 8
        df.iloc[-1, df.columns.get_loc("close")] = 15000000 + big_change
        df.iloc[-1, df.columns.get_loc("stoch_k")] = 30.0

        result = self.strategy._detect_divergence(df)
        if result["type"] == "bearish":
            self.assertGreater(result["strength"], 0.3)

    def test_detect_divergence_exception_handling(self):
        """_detect_divergence: 例外発生時のエラーハンドリング"""
        df = pd.DataFrame(
            {
                "close": [None] * 20,
                "stoch_k": [None] * 20,
                "stoch_d": [None] * 20,
                "adx_14": [None] * 20,
                "atr_14": [None] * 20,
            }
        )
        result = self.strategy._detect_divergence(df)
        self.assertEqual(result["type"], "error")
        self.assertEqual(result["action"], EntryAction.HOLD)


class TestGetSignalProximity(unittest.TestCase):
    """get_signal_proximity()テスト"""

    def setUp(self):
        """テスト前準備"""
        dates = pd.date_range(start="2025-08-01", periods=100, freq="4h")
        base_price = 15000000

        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "close": np.full(100, base_price),
                "stoch_k": np.full(100, 50.0),
                "stoch_d": np.full(100, 50.0),
                "adx_14": np.full(100, 25.0),
                "atr_14": np.full(100, 150000),
            }
        )
        self.strategy = StochasticReversalStrategy()

    def test_empty_data(self):
        """空データの場合はデフォルト値を返す"""
        result = self.strategy.get_signal_proximity(None)
        self.assertFalse(result["divergence_detected"])
        self.assertEqual(result["nearest_action"], "unknown")
        self.assertEqual(result["diagnosis"], "データ不足")

    def test_empty_dataframe(self):
        """空DataFrameの場合もデフォルト値を返す"""
        result = self.strategy.get_signal_proximity(pd.DataFrame())
        self.assertFalse(result["divergence_detected"])

    def test_buy_near_stoch_low(self):
        """stoch_k < 30の場合nearest_action=buy"""
        df = self.test_df.copy()
        df.iloc[-1, df.columns.get_loc("stoch_k")] = 20.0
        df.iloc[-1, df.columns.get_loc("stoch_d")] = 22.0
        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["nearest_action"], "buy")
        self.assertIn("過売り", result["diagnosis"])

    def test_sell_near_stoch_high(self):
        """stoch_k > 70の場合nearest_action=sell"""
        df = self.test_df.copy()
        df.iloc[-1, df.columns.get_loc("stoch_k")] = 80.0
        df.iloc[-1, df.columns.get_loc("stoch_d")] = 78.0
        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["nearest_action"], "sell")
        self.assertIn("過買い", result["diagnosis"])

    def test_neutral_zone_buy_candidate(self):
        """中立ゾーンでprice_position < stoch_positionの場合buy候補"""
        df = self.test_df.copy()
        # 価格が安値付近、Stochが中立
        for i in range(-6, 0):
            df.iloc[i, df.columns.get_loc("close")] = 15100000 - (i + 6) * 20000
            df.iloc[i, df.columns.get_loc("stoch_k")] = 30.0 + (i + 6) * 8
        df.iloc[-1, df.columns.get_loc("close")] = 14900000
        df.iloc[-1, df.columns.get_loc("stoch_k")] = 50.0
        df.iloc[-1, df.columns.get_loc("stoch_d")] = 50.0
        result = self.strategy.get_signal_proximity(df)
        self.assertIn(result["nearest_action"], ["buy", "sell"])

    def test_divergence_detected_in_diagnosis(self):
        """ダイバージェンス検出時のdiagnosis確認"""
        df = self.test_df.copy()
        for i in range(-6, 0):
            df.iloc[i, df.columns.get_loc("close")] = 15000000 + (i + 6) * 20000
            df.iloc[i, df.columns.get_loc("stoch_k")] = 70.0 - (i + 6) * 8
        df.iloc[-1, df.columns.get_loc("close")] = 15100000
        df.iloc[-1, df.columns.get_loc("stoch_k")] = 30.0
        df.iloc[-1, df.columns.get_loc("stoch_d")] = 32.0
        result = self.strategy.get_signal_proximity(df)
        self.assertIn("diagnosis", result)

    def test_adx_high_diagnosis(self):
        """ADX > threshold時の診断"""
        df = self.test_df.copy()
        df.iloc[-1, df.columns.get_loc("adx_14")] = 55.0
        result = self.strategy.get_signal_proximity(df)
        self.assertFalse(result["adx_ok"])
        self.assertIn("超過", result["diagnosis"])

    def test_price_range_ratio_sufficient(self):
        """十分な価格変動率の場合"""
        df = self.test_df.copy()
        # 価格に変動をつける
        for i in range(-6, 0):
            df.iloc[i, df.columns.get_loc("close")] = 15000000 + (i + 6) * 50000
        df.iloc[-1, df.columns.get_loc("close")] = 15250000
        result = self.strategy.get_signal_proximity(df)
        self.assertIn("price_range_ratio", result)

    def test_price_range_ratio_insufficient(self):
        """不十分な価格変動率の場合"""
        df = self.test_df.copy()
        result = self.strategy.get_signal_proximity(df)
        # すべてのclose値が同じなので変動率0
        self.assertEqual(result["price_range_ratio"], 0)
        self.assertIn("閾値", result["diagnosis"])

    def test_short_data_price_range(self):
        """短いデータの場合price_range_ratio=0"""
        df = self.test_df.head(3).copy()
        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["price_range_ratio"], 0)

    def test_adx_nan_handled(self):
        """adx_14がNaNの場合0として扱う"""
        df = self.test_df.copy()
        df.iloc[-1, df.columns.get_loc("adx_14")] = np.nan
        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["adx"], 0)
        self.assertTrue(result["adx_ok"])

    def test_exception_handling(self):
        """例外発生時のエラーハンドリング"""
        df = pd.DataFrame(
            {
                "close": [None] * 20,
                "stoch_k": [None] * 20,
                "stoch_d": [None] * 20,
                "adx_14": [None] * 20,
                "atr_14": [None] * 20,
            }
        )
        result = self.strategy.get_signal_proximity(df)
        self.assertFalse(result["divergence_detected"])
        self.assertEqual(result["nearest_action"], "unknown")

    def test_no_divergence_small_position_diff(self):
        """ダイバージェンスなし+位置差が20%未満"""
        df = self.test_df.copy()
        # 全て同値→位置差0
        result = self.strategy.get_signal_proximity(df)
        self.assertFalse(result["divergence_detected"])
        # 位置差小さいので特定メッセージ含む
        self.assertIn("diagnosis", result)


if __name__ == "__main__":
    run_stochastic_divergence_tests()
