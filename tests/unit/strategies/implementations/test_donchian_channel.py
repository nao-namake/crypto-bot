"""
Donchian Channel戦略のテストモジュール - Phase 62.2 RSIボーナス制度対応

DonchianChannelStrategyクラスの単体テスト。
直列評価方式（ADX→極端位置→RSIボーナス）を検証。

テスト項目:
- 初期化・設定テスト
- 直列評価方式テスト
- データ検証テスト
- シグナル生成テスト

Phase 62.2:
- RSIフィルタをボーナス制度に変更（HOLD→信頼度調整）
- test_rsi_filter_buy_rejected, test_rsi_filter_sell_rejectedをRSIボーナステストに変更

Phase 56.8:
- ブレイクアウトテスト削除（ブレイクアウトロジック削除）
- 弱シグナル・中央域複雑計算テスト削除
- 直列評価方式テスト追加
"""

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.strategies.implementations.donchian_channel import DonchianChannelStrategy


class TestDonchianChannelStrategy(unittest.TestCase):
    """DonchianChannelStrategyクラスのテスト"""

    def setUp(self):
        """テスト前処理"""
        self.config = {}
        self.strategy = DonchianChannelStrategy(config=self.config)

    def _create_test_data(self, length: int = 50) -> pd.DataFrame:
        """テスト用データ生成"""
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=length, freq="1h")

        # 基本価格データ
        prices = 4500000 + np.cumsum(np.random.randn(length) * 1000)
        highs = prices + np.random.rand(length) * 2000
        lows = prices - np.random.rand(length) * 2000

        # Donchian Channel特徴量
        donchian_high_20 = pd.Series(highs).rolling(20).max()
        donchian_low_20 = pd.Series(lows).rolling(20).min()
        channel_position = (prices - donchian_low_20) / (donchian_high_20 - donchian_low_20)

        # 追加特徴量
        atr_14 = pd.Series(highs - lows).rolling(14).mean()
        adx_14 = pd.Series([20.0] * length)  # デフォルトでレンジ相場
        rsi_14 = pd.Series([50.0] * length)  # デフォルトで中立

        return pd.DataFrame(
            {
                "timestamp": dates,
                "close": prices,
                "high": highs,
                "low": lows,
                "donchian_high_20": donchian_high_20,
                "donchian_low_20": donchian_low_20,
                "channel_position": channel_position,
                "atr_14": atr_14,
                "adx_14": adx_14,
                "rsi_14": rsi_14,
            }
        )

    def test_strategy_initialization(self):
        """戦略初期化テスト"""
        strategy = DonchianChannelStrategy()
        self.assertEqual(strategy.name, "DonchianChannel")
        self.assertIsNotNone(strategy.adx_max_threshold)
        self.assertIsNotNone(strategy.extreme_zone_threshold)

    def test_required_features(self):
        """必要特徴量テスト"""
        required = self.strategy.get_required_features()
        expected = [
            "close",
            "high",
            "low",
            "donchian_high_20",
            "donchian_low_20",
            "channel_position",
            "atr_14",
            "adx_14",
            "rsi_14",
        ]

        for feature in expected:
            self.assertIn(feature, required)

    def test_data_validation_success(self):
        """データ検証成功テスト"""
        df = self._create_test_data(50)
        self.assertTrue(self.strategy._validate_data(df))

    def test_data_validation_insufficient_length(self):
        """データ不足テスト"""
        df = self._create_test_data(10)  # 20期間未満
        self.assertFalse(self.strategy._validate_data(df))

    def test_data_validation_missing_columns(self):
        """必要列不足テスト"""
        df = self._create_test_data(50)
        df = df.drop(columns=["donchian_high_20"])
        self.assertFalse(self.strategy._validate_data(df))

    def test_data_validation_nan_values(self):
        """NaN値テスト"""
        df = self._create_test_data(50)
        df.loc[df.index[-1], "channel_position"] = np.nan
        self.assertFalse(self.strategy._validate_data(df))

    # ========================================
    # 直列評価: Step 1 - ADXフィルタテスト
    # ========================================

    def test_adx_filter_trending_market(self):
        """トレンド相場でHOLD（ADX > 閾値）"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # トレンド相場設定（ADX > 28）
        df.loc[latest_idx, "adx_14"] = 35.0
        df.loc[latest_idx, "channel_position"] = 0.05  # 極端位置でもHOLD

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "hold")
        self.assertIn("トレンド相場除外", signal.reason)

    def test_adx_filter_range_market(self):
        """レンジ相場で通過（ADX < 閾値）"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # レンジ相場設定（ADX < 28）
        df.loc[latest_idx, "adx_14"] = 20.0
        df.loc[latest_idx, "channel_position"] = 0.05  # 下限付近
        df.loc[latest_idx, "rsi_14"] = 30.0  # RSI低い（買い条件OK）

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "buy")
        self.assertIn("下限平均回帰", signal.reason)

    # ========================================
    # 直列評価: Step 2 - 極端位置テスト
    # ========================================

    def test_extreme_lower_zone_buy(self):
        """下限極端位置で買いシグナル"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # 下限極端位置（< 0.12）
        df.loc[latest_idx, "channel_position"] = 0.05
        df.loc[latest_idx, "adx_14"] = 20.0  # レンジ
        df.loc[latest_idx, "rsi_14"] = 25.0  # 低RSI（買い条件OK）

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "buy")
        self.assertIn("下限平均回帰", signal.reason)

    def test_extreme_upper_zone_sell(self):
        """上限極端位置で売りシグナル"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # 上限極端位置（> 0.88）
        df.loc[latest_idx, "channel_position"] = 0.95
        df.loc[latest_idx, "adx_14"] = 20.0  # レンジ
        df.loc[latest_idx, "rsi_14"] = 75.0  # 高RSI（売り条件OK）

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "sell")
        self.assertIn("上限平均回帰", signal.reason)

    def test_middle_zone_hold(self):
        """中央域でHOLD"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # 中央域（0.12-0.88）
        df.loc[latest_idx, "channel_position"] = 0.5
        df.loc[latest_idx, "adx_14"] = 20.0  # レンジ
        df.loc[latest_idx, "rsi_14"] = 50.0

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "hold")
        self.assertIn("中央域HOLD", signal.reason)

    # ========================================
    # 直列評価: Step 3 - RSIボーナステスト（Phase 62.2）
    # ========================================

    def test_rsi_filter_buy_rejected(self):
        """Phase 62.2: RSI不一致でも買いシグナル発生（ペナルティ適用）"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # 下限極端位置だがRSI高い → Phase 62.2ではHOLDではなく買い（ペナルティ適用）
        df.loc[latest_idx, "channel_position"] = 0.05
        df.loc[latest_idx, "adx_14"] = 20.0  # レンジ
        df.loc[latest_idx, "rsi_14"] = 55.0  # RSI > 48（不一致）

        signal = self.strategy.generate_signal(df)

        # Phase 62.2: RSIボーナス制度ではHOLDではなくシグナル発生
        self.assertEqual(signal.action, "buy")
        self.assertIn("下限平均回帰", signal.reason)

    def test_rsi_filter_sell_rejected(self):
        """Phase 62.2: RSI不一致でも売りシグナル発生（ペナルティ適用）"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # 上限極端位置だがRSI低い → Phase 62.2ではHOLDではなく売り（ペナルティ適用）
        df.loc[latest_idx, "channel_position"] = 0.95
        df.loc[latest_idx, "adx_14"] = 20.0  # レンジ
        df.loc[latest_idx, "rsi_14"] = 45.0  # RSI < 52（不一致）

        signal = self.strategy.generate_signal(df)

        # Phase 62.2: RSIボーナス制度ではHOLDではなくシグナル発生
        self.assertEqual(signal.action, "sell")
        self.assertIn("上限平均回帰", signal.reason)

    def test_rsi_match_bonus_confidence(self):
        """Phase 62.2: RSI一致時は信頼度にボーナスが適用される"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # RSI一致ケース
        df.loc[latest_idx, "channel_position"] = 0.05
        df.loc[latest_idx, "adx_14"] = 20.0
        df.loc[latest_idx, "rsi_14"] = 30.0  # RSI <= 48（一致）

        signal_match = self.strategy.generate_signal(df)

        # RSI不一致ケース
        df.loc[latest_idx, "rsi_14"] = 55.0  # RSI > 48（不一致）

        signal_mismatch = self.strategy.generate_signal(df)

        # RSI一致時の方が信頼度が高い
        self.assertGreater(signal_match.confidence, signal_mismatch.confidence)

    # ========================================
    # 信頼度計算テスト
    # ========================================

    def test_confidence_calculation_basic(self):
        """基本信頼度計算テスト"""
        # Phase 62.2: rsi_matches引数追加
        confidence = self.strategy._calculate_confidence(0.05, 30.0, "buy", rsi_matches=True)

        self.assertGreaterEqual(confidence, self.strategy.min_confidence)
        self.assertLessEqual(confidence, self.strategy.max_confidence)

    def test_confidence_extreme_position_bonus(self):
        """極端位置ボーナステスト"""
        # 極端位置（< 0.05）
        conf_extreme = self.strategy._calculate_confidence(0.03, 30.0, "buy", rsi_matches=True)
        # 通常位置（0.05-0.12）
        conf_normal = self.strategy._calculate_confidence(0.10, 30.0, "buy", rsi_matches=True)

        self.assertGreater(conf_extreme, conf_normal)

    def test_confidence_rsi_bonus(self):
        """RSI確認ボーナステスト"""
        # 極端RSI（< 30）+ RSI一致
        conf_extreme_rsi = self.strategy._calculate_confidence(0.05, 25.0, "buy", rsi_matches=True)
        # 通常RSI（30-42）+ RSI一致
        conf_normal_rsi = self.strategy._calculate_confidence(0.05, 35.0, "buy", rsi_matches=True)

        self.assertGreater(conf_extreme_rsi, conf_normal_rsi)

    # ========================================
    # シグナル生成テスト
    # ========================================

    def test_hold_signal_creation(self):
        """HOLDシグナル生成テスト"""
        df = self._create_test_data(50)

        signal = self.strategy._create_hold_signal(df, "テスト理由")

        self.assertEqual(signal.action, "hold")
        self.assertGreater(signal.confidence, 0.0)
        self.assertIn("テスト理由", signal.reason)

    def test_buy_signal_creation(self):
        """BUYシグナル生成テスト"""
        df = self._create_test_data(50)

        signal = self.strategy._create_signal(
            action="buy",
            confidence=0.5,
            reason="テストBUY",
            current_price=4500000,
            df=df,
            channel_position=0.05,
        )

        self.assertEqual(signal.action, "buy")
        self.assertEqual(signal.confidence, 0.5)
        self.assertIsNotNone(signal.stop_loss)
        self.assertIsNotNone(signal.take_profit)

    def test_sell_signal_creation(self):
        """SELLシグナル生成テスト"""
        df = self._create_test_data(50)

        signal = self.strategy._create_signal(
            action="sell",
            confidence=0.5,
            reason="テストSELL",
            current_price=4500000,
            df=df,
            channel_position=0.95,
        )

        self.assertEqual(signal.action, "sell")
        self.assertEqual(signal.confidence, 0.5)
        self.assertIsNotNone(signal.stop_loss)
        self.assertIsNotNone(signal.take_profit)

    # ========================================
    # エラーハンドリングテスト
    # ========================================

    def test_signal_generation_error_handling(self):
        """シグナル生成エラーハンドリングテスト"""
        df = pd.DataFrame()  # 空DataFrame

        from src.core.exceptions import StrategyError

        with self.assertRaises(StrategyError):
            self.strategy.generate_signal(df)

    def test_analyze_with_multi_timeframe_data(self):
        """マルチタイムフレームデータを使用した分析テスト"""
        df = self._create_test_data(50)

        # 15分足データ作成
        multi_tf_data = {
            "15m": pd.DataFrame(
                {
                    "close": [4500000],
                    "atr_14": [1500],
                }
            )
        }

        signal = self.strategy.analyze(df, multi_timeframe_data=multi_tf_data)

        self.assertIsNotNone(signal)
        self.assertIn(signal.action, ["buy", "sell", "hold"])

    # ========================================
    # 統合シナリオテスト
    # ========================================

    def test_complete_buy_scenario(self):
        """完全な買いシナリオテスト"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # 全条件満たす買いシナリオ
        df.loc[latest_idx, "channel_position"] = 0.03  # 極端下限
        df.loc[latest_idx, "adx_14"] = 15.0  # 強いレンジ
        df.loc[latest_idx, "rsi_14"] = 25.0  # 極端低RSI

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "buy")
        self.assertGreater(signal.confidence, 0.4)

    def test_complete_sell_scenario(self):
        """完全な売りシナリオテスト"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]

        # 全条件満たす売りシナリオ
        df.loc[latest_idx, "channel_position"] = 0.97  # 極端上限
        df.loc[latest_idx, "adx_14"] = 15.0  # 強いレンジ
        df.loc[latest_idx, "rsi_14"] = 75.0  # 極端高RSI

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "sell")
        self.assertGreater(signal.confidence, 0.4)

    @patch("src.strategies.implementations.donchian_channel.get_threshold")
    def test_configuration_override(self, mock_get_threshold):
        """設定オーバーライドテスト"""
        mock_get_threshold.return_value = 30  # ADX閾値を30に

        strategy = DonchianChannelStrategy(config={})

        # get_thresholdが呼ばれたことを確認
        self.assertTrue(mock_get_threshold.called)


if __name__ == "__main__":
    unittest.main()
