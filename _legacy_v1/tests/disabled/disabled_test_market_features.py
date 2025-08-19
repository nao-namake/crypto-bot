#!/usr/bin/env python3
"""
Phase 16.3-B 分割システム: MarketFeaturesMixin テスト

97特徴量システムの市場特徴量エンジンテスト
"""

import unittest

import numpy as np
import pandas as pd

from crypto_bot.ml.features.master.market_features import MarketFeaturesMixin

# from unittest.mock import MagicMock, patch  # unused


class TestMarketFeaturesMixin(unittest.TestCase):
    """MarketFeaturesMixin テスト"""

    def setUp(self):
        """テスト用データ準備"""
        self.mixin = MarketFeaturesMixin()

        # テスト用OHLCV データ
        dates = pd.date_range("2024-01-01", periods=200, freq="1H")
        np.random.seed(42)
        base_price = 5000000

        self.df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": base_price + np.random.normal(0, 50000, 200),
                "high": base_price + np.random.normal(25000, 50000, 200),
                "low": base_price - np.random.normal(25000, 50000, 200),
                "close": base_price + np.random.normal(0, 50000, 200),
                "volume": np.random.uniform(10, 100, 200),
            }
        )

        # 価格が正の値になるように調整
        self.df[["open", "high", "low", "close"]] = np.abs(
            self.df[["open", "high", "low", "close"]]
        )

    def test_calculate_lag_features(self):
        """ラグ特徴量計算テスト"""
        result = self.mixin._calculate_lag_features(self.df)

        # ラグ期間のテスト
        lag_periods = [1, 3]
        for period in lag_periods:
            self.assertIn(f"close_lag_{period}", result.columns)

        # ラグ値の妥当性確認
        for i in range(1, min(4, len(result))):
            if not pd.isna(result["close_lag_1"].iloc[i]):
                # 1期間前の値と一致するか確認
                self.assertAlmostEqual(
                    result["close_lag_1"].iloc[i],
                    result["close"].iloc[i - 1],
                    places=2,
                )

    def test_calculate_return_features(self):
        """リターン特徴量計算テスト"""
        result = self.mixin._calculate_return_features(self.df)

        # リターン期間のテスト
        return_periods = [1, 2, 3, 5, 10]
        for period in return_periods:
            self.assertIn(f"returns_{period}", result.columns)

        # リターン値の妥当性確認（-1 < return < 1 の合理的範囲）
        for period in return_periods:
            returns = result[f"returns_{period}"].dropna()
            if len(returns) > 0:
                # 極端な値でないことを確認
                self.assertTrue((returns > -2).all())
                self.assertTrue((returns < 2).all())

    def test_calculate_volume_features(self):
        """出来高特徴量計算テスト"""
        # VWAPを追加
        enhanced_df = self.df.copy()
        enhanced_df["vwap"] = enhanced_df["close"] * 1.001  # 簡易VWAP

        result = self.mixin._calculate_volume_features(enhanced_df)

        # 出来高関連特徴量
        expected_features = [
            "volume_sma_20",
            "volume_ratio",
            "vwap_distance",
            "obv",
            "cmf",
            "mfi",
        ]

        for feature in expected_features:
            self.assertIn(feature, result.columns)

        # Volume ratio は正の値
        vol_ratio = result["volume_ratio"].dropna()
        if len(vol_ratio) > 0:
            self.assertTrue((vol_ratio > 0).all())

        # MFI は 0-100 の範囲
        mfi = result["mfi"].dropna()
        if len(mfi) > 0:
            self.assertTrue((mfi >= 0).all())
            self.assertTrue((mfi <= 100).all())

    def test_calculate_volatility_features(self):
        """ボラティリティ特徴量計算テスト"""
        result = self.mixin._calculate_volatility_features(self.df)

        # ボラティリティ関連特徴量
        expected_features = ["atr", "true_range", "volatility_20"]

        for feature in expected_features:
            self.assertIn(feature, result.columns)

        # ATRは正の値
        atr = result["atr"].dropna()
        if len(atr) > 0:
            self.assertTrue((atr > 0).all())

        # True Rangeは正の値
        tr = result["true_range"].dropna()
        if len(tr) > 0:
            self.assertTrue((tr >= 0).all())

    def test_calculate_market_regime_features(self):
        """市場レジーム特徴量計算テスト"""
        result = self.mixin._calculate_market_regime_features(self.df)

        # 市場レジーム特徴量
        expected_features = [
            "volatility_regime",
            "trend_strength",
            "momentum_quality",
            "market_phase",
        ]

        for feature in expected_features:
            self.assertIn(feature, result.columns)

        # volatility_regimeは数値
        vol_regime = result["volatility_regime"].dropna()
        if len(vol_regime) > 0:
            self.assertTrue(np.isfinite(vol_regime).all())

        # trend_strengthは0-1の範囲が期待される
        trend_str = result["trend_strength"].dropna()
        if len(trend_str) > 0:
            self.assertTrue(np.isfinite(trend_str).all())

    def test_calculate_pattern_features(self):
        """パターン特徴量計算テスト"""
        result = self.mixin._calculate_pattern_features(self.df)

        # パターン特徴量
        expected_features = [
            "support_resistance",
            "breakout_signal",
            "reversal_pattern",
            "candlestick_pattern",
        ]

        for feature in expected_features:
            self.assertIn(feature, result.columns)

        # 数値の妥当性確認
        for feature in expected_features:
            values = result[feature].dropna()
            if len(values) > 0:
                self.assertTrue(np.isfinite(values).all())

    def test_full_market_features_generation(self):
        """フル市場特徴量生成テスト"""
        # 必要なカラムを追加
        enhanced_df = self.df.copy()
        enhanced_df["vwap"] = enhanced_df["close"] * 1.001  # 簡易VWAP

        result = self.mixin.generate_market_features(enhanced_df)

        # 基本的な市場特徴量が含まれていることを確認
        essential_features = [
            "close_lag_1",
            "returns_1",
            "volume_ratio",
            "atr",
            "volatility_regime",
            "support_resistance",
        ]

        for feature in essential_features:
            self.assertIn(feature, result.columns, f"{feature} が見つかりません")

        # データサイズが一致
        self.assertEqual(len(result), len(enhanced_df))

        # 数値データの妥当性
        numeric_columns = result.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            values = result[col].dropna()
            if len(values) > 0:
                self.assertTrue(
                    np.isfinite(values).all(), f"{col} に非有限値が含まれています"
                )


if __name__ == "__main__":
    unittest.main()
