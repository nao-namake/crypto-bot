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


class TestDonchianChannelEdgeCases(unittest.TestCase):
    """エッジケース・カバレッジ補完テスト"""

    def setUp(self):
        """テスト前処理"""
        self.strategy = DonchianChannelStrategy(config={})

    def _create_test_data(self, length: int = 50) -> pd.DataFrame:
        """テスト用データ生成"""
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=length, freq="1h")
        prices = 4500000 + np.cumsum(np.random.randn(length) * 1000)
        highs = prices + np.random.rand(length) * 2000
        lows = prices - np.random.rand(length) * 2000
        donchian_high_20 = pd.Series(highs).rolling(20).max()
        donchian_low_20 = pd.Series(lows).rolling(20).min()
        channel_position = (prices - donchian_low_20) / (donchian_high_20 - donchian_low_20)
        atr_14 = pd.Series(highs - lows).rolling(14).mean()

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
                "adx_14": pd.Series([20.0] * length),
                "rsi_14": pd.Series([50.0] * length),
            }
        )

    def test_analyze_data_validation_hold(self):
        """analyze: データ検証失敗時はHOLDシグナル"""
        df = self._create_test_data(50)
        df = df.drop(columns=["donchian_high_20"])
        signal = self.strategy.analyze(df)
        self.assertEqual(signal.action, "hold")
        self.assertIn("データ不足", signal.reason)

    def test_analyze_confidence_below_threshold(self):
        """analyze: 信頼度が閾値未満の場合HOLD"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]
        # 極端位置ギリギリだが信頼度不足
        df.loc[latest_idx, "channel_position"] = self.strategy.extreme_zone_threshold - 0.001
        df.loc[latest_idx, "adx_14"] = 20.0
        df.loc[latest_idx, "rsi_14"] = 55.0  # RSI不一致（ペナルティ）
        signal = self.strategy.analyze(df)
        # 信頼度不足でHOLDの可能性
        self.assertIn(signal.action, ["buy", "hold"])

    def test_analyze_exception_handling(self):
        """analyze: 例外発生時のエラーハンドリング"""
        df = self._create_test_data(50)
        # channel_positionをNoneにして例外を誘発
        df["channel_position"] = None
        signal = self.strategy.analyze(df)
        self.assertEqual(signal.action, "hold")

    def test_validate_data_missing_columns_warning(self):
        """_validate_data: 不足特徴量でFalseを返す"""
        df = pd.DataFrame(
            {
                "close": [4500000] * 25,
                "high": [4501000] * 25,
                "low": [4499000] * 25,
                # donchian_high_20, donchian_low_20, channel_position が不足
                "atr_14": [1500] * 25,
                "adx_14": [20.0] * 25,
                "rsi_14": [50.0] * 25,
            }
        )
        result = self.strategy._validate_data(df)
        self.assertFalse(result)

    def test_calculate_confidence_rsi_bonus_false(self):
        """_calculate_confidence: rsi_as_bonus=False時の従来方式"""
        original = self.strategy.rsi_as_bonus
        self.strategy.rsi_as_bonus = False
        try:
            # buy + RSI < 30 → bonus
            conf_low_rsi = self.strategy._calculate_confidence(0.05, 25.0, "buy")
            # buy + RSI > 30 → no bonus
            conf_normal_rsi = self.strategy._calculate_confidence(0.05, 50.0, "buy")
            self.assertGreaterEqual(conf_low_rsi, conf_normal_rsi)

            # sell + RSI > 70 → bonus
            conf_high_rsi = self.strategy._calculate_confidence(0.95, 75.0, "sell")
            conf_mid_rsi = self.strategy._calculate_confidence(0.95, 50.0, "sell")
            self.assertGreaterEqual(conf_high_rsi, conf_mid_rsi)
        finally:
            self.strategy.rsi_as_bonus = original


class TestDonchianGetSignalProximity(unittest.TestCase):
    """get_signal_proximity()テスト"""

    def setUp(self):
        """テスト前処理"""
        self.strategy = DonchianChannelStrategy(config={})

    def _create_valid_df(self, length: int = 50) -> pd.DataFrame:
        """有効なテストデータ生成"""
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=length, freq="1h")
        prices = 4500000 + np.cumsum(np.random.randn(length) * 1000)
        highs = prices + np.random.rand(length) * 2000
        lows = prices - np.random.rand(length) * 2000
        donchian_high_20 = pd.Series(highs).rolling(20).max()
        donchian_low_20 = pd.Series(lows).rolling(20).min()
        channel_position = (prices - donchian_low_20) / (donchian_high_20 - donchian_low_20)

        return pd.DataFrame(
            {
                "timestamp": dates,
                "close": prices,
                "high": highs,
                "low": lows,
                "donchian_high_20": donchian_high_20,
                "donchian_low_20": donchian_low_20,
                "channel_position": channel_position,
                "atr_14": pd.Series(highs - lows).rolling(14).mean(),
                "adx_14": pd.Series([20.0] * length),
                "rsi_14": pd.Series([50.0] * length),
            }
        )

    def test_invalid_data_returns_default(self):
        """無効データではデフォルト値を返す"""
        df = pd.DataFrame({"close": [4500000] * 10})  # 不十分なデータ
        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["nearest_action"], "unknown")
        self.assertEqual(result["diagnosis"], "データ不足")

    def test_buy_zone_near(self):
        """チャネル下端でBUYシグナル近い"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "channel_position"] = 0.05  # 下端
        df.loc[latest_idx, "adx_14"] = 20.0
        df.loc[latest_idx, "rsi_14"] = 25.0  # 過売り

        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["nearest_action"], "buy")
        self.assertIn("BUY端", result["diagnosis"])
        self.assertLess(result["gap_to_buy"], result["gap_to_sell"])

    def test_sell_zone_near(self):
        """チャネル上端でSELLシグナル近い"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "channel_position"] = 0.95  # 上端
        df.loc[latest_idx, "adx_14"] = 20.0
        df.loc[latest_idx, "rsi_14"] = 75.0  # 過買い

        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["nearest_action"], "sell")
        self.assertIn("SELL端", result["diagnosis"])

    def test_middle_zone(self):
        """中央域では距離情報を返す"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "channel_position"] = 0.5
        df.loc[latest_idx, "adx_14"] = 20.0
        df.loc[latest_idx, "rsi_14"] = 50.0

        result = self.strategy.get_signal_proximity(df)
        self.assertGreater(result["gap_to_buy"], 0)
        self.assertGreater(result["gap_to_sell"], 0)
        self.assertIn("端まで", result["diagnosis"])

    def test_adx_high_not_ok(self):
        """ADXが閾値超過の場合"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "channel_position"] = 0.5
        df.loc[latest_idx, "adx_14"] = 35.0  # 高ADX

        result = self.strategy.get_signal_proximity(df)
        self.assertFalse(result["adx_ok"])
        self.assertIn("超過", result["diagnosis"])

    def test_adx_ok(self):
        """ADXが閾値以下の場合"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "adx_14"] = 15.0

        result = self.strategy.get_signal_proximity(df)
        self.assertTrue(result["adx_ok"])

    def test_rsi_oversold(self):
        """RSI過売り診断"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "rsi_14"] = 20.0

        result = self.strategy.get_signal_proximity(df)
        self.assertIn("過売り", result["diagnosis"])

    def test_rsi_overbought(self):
        """RSI過買い診断"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "rsi_14"] = 80.0

        result = self.strategy.get_signal_proximity(df)
        self.assertIn("過買い", result["diagnosis"])

    def test_rsi_neutral(self):
        """RSI中立診断"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "rsi_14"] = 50.0

        result = self.strategy.get_signal_proximity(df)
        self.assertIn("中立", result["diagnosis"])

    def test_adx_nan_handled(self):
        """adx_14がNaNの場合0として扱う"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "adx_14"] = np.nan

        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["adx"], 0)

    def test_rsi_nan_handled(self):
        """rsi_14がNaNの場合50として扱う"""
        df = self._create_valid_df()
        latest_idx = df.index[-1]
        df.loc[latest_idx, "rsi_14"] = np.nan

        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["rsi"], 50)

    def test_exception_handling(self):
        """例外発生時のエラーハンドリング"""
        # _validate_dataを通過するが、float変換で失敗するデータ
        df = self._create_valid_df()
        # channel_positionを文字列にして例外を誘発
        df["channel_position"] = "not_a_number"
        result = self.strategy.get_signal_proximity(df)
        self.assertEqual(result["nearest_action"], "unknown")
        self.assertIn("診断エラー", result["diagnosis"])

    def test_return_fields_complete(self):
        """全フィールドが返される"""
        df = self._create_valid_df()
        result = self.strategy.get_signal_proximity(df)
        expected_keys = [
            "channel_position",
            "extreme_threshold",
            "gap_to_buy",
            "gap_to_sell",
            "adx",
            "adx_threshold",
            "adx_ok",
            "rsi",
            "nearest_action",
            "diagnosis",
        ]
        for key in expected_keys:
            self.assertIn(key, result, f"Missing key: {key}")


if __name__ == "__main__":
    unittest.main()
