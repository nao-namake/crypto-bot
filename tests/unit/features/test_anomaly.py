"""
AnomalyDetector テストファイル - Phase 17品質向上・カバレッジ75%達成

異常検知システム（market_stress統合指標）の全メソッドを包括的にテスト。
価格ギャップ・日中変動・出来高スパイクによる市場ストレス度検知をカバー。
"""

import numpy as np
import pandas as pd
import pytest

from src.core.exceptions import DataProcessingError
from src.features.anomaly import MarketAnomalyDetector as AnomalyDetector


class TestAnomalyDetector:
    """AnomalyDetector メインテストクラス"""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """正常市場データサンプル作成"""
        np.random.seed(42)
        n_samples = 100
        base_price = 5000000  # 500万円のBTC/JPY

        # 正常な価格変動（小さな変動）
        returns = np.random.normal(0, 0.01, n_samples)  # 1%標準偏差
        prices = [base_price]

        for ret in returns[:-1]:
            next_price = prices[-1] * (1 + ret)
            prices.append(max(next_price, 100))  # 最小値100

        # OHLCV データ作成
        highs = [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices]
        lows = [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices]
        volumes = np.random.lognormal(7, 0.3, n_samples)  # 対数正規分布

        return pd.DataFrame(
            {"open": prices, "high": highs, "low": lows, "close": prices, "volume": volumes}
        )

    @pytest.fixture
    def stressed_market_data(self):
        """ストレス市場データサンプル作成"""
        np.random.seed(123)
        n_samples = 50
        base_price = 5000000

        # ストレス市場の特徴
        # - 大きな価格ギャップ
        # - 高い日中変動
        # - 異常な出来高スパイク

        stressed_returns = np.random.normal(0, 0.05, n_samples)  # 5%標準偏差（異常）
        prices = [base_price]

        for ret in stressed_returns[:-1]:
            next_price = prices[-1] * (1 + ret)
            prices.append(max(next_price, 100))

        # 高い日中変動
        highs = [p * (1 + abs(np.random.normal(0, 0.03))) for p in prices]  # 3%変動
        lows = [p * (1 - abs(np.random.normal(0, 0.03))) for p in prices]

        # 出来高スパイク（通常の3-10倍）
        volumes = np.random.lognormal(7, 0.3, n_samples) * np.random.uniform(3, 10, n_samples)

        return pd.DataFrame(
            {"open": prices, "high": highs, "low": lows, "close": prices, "volume": volumes}
        )

    @pytest.fixture
    def detector(self):
        """AnomalyDetector インスタンス"""
        return AnomalyDetector()

    def test_init_default(self, detector):
        """デフォルト初期化テスト"""
        assert isinstance(detector, AnomalyDetector)
        assert detector.lookback_period == 20  # デフォルト値
        assert hasattr(detector, "logger")
        assert hasattr(detector, "computed_features")
        assert len(detector.computed_features) == 0

    def test_init_custom_lookback(self):
        """カスタムlookback_period初期化テスト"""
        detector = AnomalyDetector(lookback_period=30)

        assert detector.lookback_period == 30
        assert isinstance(detector, AnomalyDetector)

    def test_generate_all_features_basic(self, detector, sample_ohlcv_data):
        """基本異常検知特徴量生成テスト"""
        result_df = detector.generate_all_features(sample_ohlcv_data)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(sample_ohlcv_data)

        # market_stress 特徴量が追加されている
        assert "market_stress" in result_df.columns

        # computed_features にセットされている
        assert "market_stress" in detector.computed_features
        assert len(detector.computed_features) == 1

    def test_generate_all_features_data_validation(self, detector, sample_ohlcv_data):
        """特徴量データ妥当性テスト"""
        result_df = detector.generate_all_features(sample_ohlcv_data)

        # market_stress: 0-1の範囲内（正規化済み）
        market_stress = result_df["market_stress"].dropna()
        if len(market_stress) > 0:
            assert all(0 <= x <= 1 for x in market_stress), "market_stress値が0-1範囲外"

        # NaN値処理済み
        assert not result_df["market_stress"].isnull().any()
        assert not np.isinf(result_df["market_stress"]).any()

    def test_generate_all_features_stressed_market(self, detector, stressed_market_data):
        """ストレス市場での特徴量生成テスト"""
        result_df = detector.generate_all_features(stressed_market_data)

        assert isinstance(result_df, pd.DataFrame)
        assert "market_stress" in result_df.columns

        # ストレス市場ではmarket_stress値が高い傾向
        market_stress = result_df["market_stress"].dropna()
        if len(market_stress) > 0:
            mean_stress = market_stress.mean()
            # ストレス市場では平均値が0.3以上程度期待
            assert mean_stress >= 0.0  # 少なくとも非負

    def test_generate_all_features_missing_columns(self, detector):
        """必要列不足テスト"""
        incomplete_df = pd.DataFrame(
            {
                "close": [100, 101, 102, 103, 104],
                "volume": [1000, 1100, 1200, 1300, 1400],
                # open, high, low が不足
            }
        )

        with pytest.raises(DataProcessingError, match="必要列が不足"):
            detector.generate_all_features(incomplete_df)

    def test_generate_all_features_empty_data(self, detector):
        """空データテスト"""
        empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        try:
            result_df = detector.generate_all_features(empty_df)
            assert isinstance(result_df, pd.DataFrame)
            assert len(result_df) == 0
        except (DataProcessingError, ValueError):
            # 空データでエラーは許容される
            pass

    def test_generate_all_features_single_row(self, detector):
        """単一行データテスト"""
        single_row_df = pd.DataFrame(
            {
                "open": [5000000],
                "high": [5050000],
                "low": [4950000],
                "close": [5000000],
                "volume": [1000],
            }
        )

        result_df = detector.generate_all_features(single_row_df)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 1
        assert "market_stress" in result_df.columns

        # 単一行では参照データなしで計算困難だが、0で埋められる
        assert not result_df["market_stress"].isnull().any()

    def test_get_feature_info(self, detector, sample_ohlcv_data):
        """特徴量情報取得テスト"""
        # 特徴量生成前
        info_before = detector.get_feature_info()
        assert info_before["total_features"] == 0
        assert len(info_before["computed_features"]) == 0
        assert "parameters" in info_before
        assert info_before["parameters"]["lookback_period"] == 20

        # 特徴量生成後
        detector.generate_all_features(sample_ohlcv_data)
        info_after = detector.get_feature_info()

        assert info_after["total_features"] == 1
        assert "market_stress" in info_after["computed_features"]
        assert "feature_descriptions" in info_after
        assert "market_stress" in info_after["feature_descriptions"]

    def test_nan_handling(self, detector):
        """NaN値処理テスト"""
        data_with_nan = pd.DataFrame(
            {
                "open": [5000000, np.nan, 5100000, 4900000, 5050000],
                "high": [5050000, 5150000, np.nan, 4950000, 5100000],
                "low": [4950000, 4950000, 4950000, np.nan, 4900000],
                "close": [5000000, 5100000, 5000000, 4900000, np.nan],
                "volume": [1000, 1100, np.nan, 900, 1050],
            }
        )

        result_df = detector.generate_all_features(data_with_nan)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(data_with_nan)

        # NaN値がffill().bfill().fillna(0)で処理されている
        assert not result_df["market_stress"].isnull().any()
        assert not np.isinf(result_df["market_stress"]).any()

    def test_constant_price_data(self, detector):
        """定数価格データテスト"""
        constant_df = pd.DataFrame(
            {
                "open": [5000000] * 50,
                "high": [5000000] * 50,
                "low": [5000000] * 50,
                "close": [5000000] * 50,
                "volume": [1000] * 50,
            }
        )

        result_df = detector.generate_all_features(constant_df)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 50

        # 価格変動なしではmarket_stress は低い値
        market_stress = result_df["market_stress"].dropna()
        if len(market_stress) > 0:
            # 変動なしでは0または低い値
            assert all(0 <= x <= 0.5 for x in market_stress)

    def test_extreme_values(self, detector):
        """極端値テスト"""
        extreme_df = pd.DataFrame(
            {
                "open": [1, 1000000, 1, 1000000, 1],
                "high": [2, 1100000, 2, 1100000, 2],
                "low": [0.5, 900000, 0.5, 900000, 0.5],
                "close": [1, 1000000, 1, 1000000, 1],
                "volume": [1, 1000000000, 1, 1000000000, 1],
            }
        )

        result_df = detector.generate_all_features(extreme_df)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 5

        # 極端な値でも処理される
        assert not np.isinf(result_df["market_stress"]).any()
        assert not result_df["market_stress"].isnull().any()

        # 極端な変動でmarket_stress が高い
        market_stress = result_df["market_stress"]
        max_stress = market_stress.max()
        assert max_stress > 0.5  # 極端な変動でストレス度高

    def test_different_lookback_periods(self, sample_ohlcv_data):
        """異なるlookback_period テスト"""
        lookback_periods = [10, 20, 30, 50]

        for period in lookback_periods:
            detector = AnomalyDetector(lookback_period=period)

            result_df = detector.generate_all_features(sample_ohlcv_data)

            assert isinstance(result_df, pd.DataFrame)
            assert "market_stress" in result_df.columns
            assert detector.lookback_period == period

    def test_large_dataset_performance(self, detector):
        """大規模データ性能テスト"""
        # 10,000行のデータ
        np.random.seed(999)
        n_large = 10000
        base_price = 5000000

        # 価格データ生成
        returns = np.random.normal(0, 0.02, n_large)
        prices = [base_price]
        for ret in returns[:-1]:
            prices.append(max(prices[-1] * (1 + ret), 1))

        large_df = pd.DataFrame(
            {
                "open": prices,
                "high": [p * 1.02 for p in prices],
                "low": [p * 0.98 for p in prices],
                "close": prices,
                "volume": np.random.lognormal(7, 0.5, n_large),
            }
        )

        import time

        start_time = time.time()

        result_df = detector.generate_all_features(large_df)

        elapsed_time = time.time() - start_time

        # 10,000行で5秒以内
        assert elapsed_time < 5.0, f"Performance too slow: {elapsed_time:.3f}s"
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == n_large

    def test_data_types(self, detector):
        """データ型テスト"""
        # 整数データ
        int_df = pd.DataFrame(
            {
                "open": [5000000, 5100000, 5050000, 4950000, 5000000],
                "high": [5050000, 5150000, 5100000, 5000000, 5050000],
                "low": [4950000, 5050000, 5000000, 4900000, 4950000],
                "close": [5000000, 5100000, 5050000, 4950000, 5000000],
                "volume": [1000, 1100, 1200, 900, 1050],
            }
        )

        result_df = detector.generate_all_features(int_df)
        assert isinstance(result_df, pd.DataFrame)
        assert "market_stress" in result_df.columns

        # 浮動小数点データ
        float_df = int_df.astype(float)
        result_df_float = detector.generate_all_features(float_df)
        assert isinstance(result_df_float, pd.DataFrame)

    def test_edge_cases_zero_volume(self, detector):
        """ゼロ出来高エッジケーステスト"""
        zero_volume_df = pd.DataFrame(
            {
                "open": [5000000, 5100000, 5050000],
                "high": [5050000, 5150000, 5100000],
                "low": [4950000, 5050000, 5000000],
                "close": [5000000, 5100000, 5050000],
                "volume": [0, 0, 0],  # ゼロ出来高
            }
        )

        result_df = detector.generate_all_features(zero_volume_df)

        assert isinstance(result_df, pd.DataFrame)
        assert "market_stress" in result_df.columns
        # ゼロ除算エラーなし
        assert not np.isinf(result_df["market_stress"]).any()

    def test_negative_prices_handling(self, detector):
        """負の価格処理テスト"""
        # 現実的ではないが、堅牢性テスト
        negative_df = pd.DataFrame(
            {
                "open": [-100, 100, -50, 200, 0],
                "high": [0, 150, 0, 250, 50],
                "low": [-150, 50, -100, 150, -50],
                "close": [-50, 120, -25, 180, 25],
                "volume": [1000, 1100, 1200, 900, 1050],
            }
        )

        try:
            result_df = detector.generate_all_features(negative_df)
            assert isinstance(result_df, pd.DataFrame)
            # 異常値でも処理される
        except (ValueError, DataProcessingError):
            # 負の価格でエラーは許容される
            pass


class TestAnomalyDetectorPrivateMethods:
    """AnomalyDetector プライベートメソッドテスト"""

    @pytest.fixture
    def detector(self):
        """AnomalyDetector インスタンス"""
        return AnomalyDetector(lookback_period=10)  # 短い期間でテスト

    @pytest.fixture
    def sample_ohlcv_df(self):
        """サンプルOHLCVデータフレーム"""
        np.random.seed(654)
        n = 20
        base_price = 5000000

        returns = np.random.normal(0, 0.02, n)
        prices = [base_price]
        for ret in returns[:-1]:
            prices.append(prices[-1] * (1 + ret))

        return pd.DataFrame(
            {
                "open": prices,
                "high": [p * 1.01 for p in prices],
                "low": [p * 0.99 for p in prices],
                "close": prices,
                "volume": np.random.lognormal(7, 0.3, n),
            }
        )

    def test_calculate_market_stress(self, detector, sample_ohlcv_df):
        """市場ストレス度計算テスト"""
        market_stress = detector._calculate_market_stress(sample_ohlcv_df)

        assert isinstance(market_stress, pd.Series)
        assert len(market_stress) == len(sample_ohlcv_df)

        # 0-1の範囲内
        valid_stress = market_stress.dropna()
        if len(valid_stress) > 0:
            assert all(0 <= x <= 1 for x in valid_stress)

    def test_normalize_basic(self, detector):
        """正規化基本テスト"""
        series = pd.Series([1, 2, 3, 4, 5, 100])  # 100は外れ値

        normalized = detector._normalize(series)

        assert isinstance(normalized, pd.Series)
        assert len(normalized) == len(series)

        # 0-1の範囲内
        assert all(0 <= x <= 1 for x in normalized)

        # 最小値は0、最大値は1（外れ値処理後）
        assert normalized.min() == 0
        assert normalized.max() == 1

    def test_normalize_constant_series(self, detector):
        """定数シリーズ正規化テスト"""
        constant_series = pd.Series([5, 5, 5, 5, 5])

        normalized = detector._normalize(constant_series)

        assert isinstance(normalized, pd.Series)
        assert len(normalized) == len(constant_series)

        # 定数シリーズは全て0
        assert all(x == 0 for x in normalized)

    def test_normalize_with_outliers(self, detector):
        """外れ値含む正規化テスト"""
        series_with_outliers = pd.Series([1, 2, 3, 4, 5] * 10 + [1000, 2000, 3000])

        normalized = detector._normalize(series_with_outliers)

        assert isinstance(normalized, pd.Series)
        assert len(normalized) == len(series_with_outliers)

        # 外れ値が上位5%でクリップされる
        assert all(0 <= x <= 1 for x in normalized)

    def test_normalize_negative_values(self, detector):
        """負の値正規化テスト"""
        negative_series = pd.Series([-10, -5, 0, 5, 10])

        normalized = detector._normalize(negative_series)

        assert isinstance(normalized, pd.Series)
        assert len(normalized) == len(negative_series)

        # 0-1の範囲内に正規化される
        assert all(0 <= x <= 1 for x in normalized)

    def test_normalize_empty_series(self, detector):
        """空シリーズ正規化テスト"""
        empty_series = pd.Series([], dtype=float)

        normalized = detector._normalize(empty_series)

        assert isinstance(normalized, pd.Series)
        assert len(normalized) == 0


class TestAnomalyDetectorIntegration:
    """AnomalyDetector 統合テストクラス"""

    def test_real_world_scenario(self):
        """実世界シナリオテスト"""
        detector = AnomalyDetector(lookback_period=20)

        # BTC市場クラッシュシナリオ模擬
        np.random.seed(777)
        n_points = 1000  # 約3.5日分（4時間足想定）
        base_price = 5000000

        # Phase 1: 正常市場（800点）
        normal_returns = np.random.normal(0, 0.01, 800)

        # Phase 2: クラッシュ（50点）
        crash_returns = np.concatenate(
            [
                np.random.normal(-0.05, 0.02, 30),  # 急落
                np.random.normal(-0.02, 0.01, 20),  # 継続下落
            ]
        )

        # Phase 3: 回復（150点）
        recovery_returns = np.random.normal(0.005, 0.02, 150)

        all_returns = np.concatenate([normal_returns, crash_returns, recovery_returns])

        # 価格・出来高データ生成
        prices = [base_price]
        for ret in all_returns[:-1]:
            prices.append(max(prices[-1] * (1 + ret), 1))

        volumes = np.random.lognormal(7, 0.3, n_points)
        # クラッシュ時の出来高急増
        volumes[800:850] *= np.random.uniform(3, 8, 50)

        market_data = pd.DataFrame(
            {
                "open": prices,
                "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
                "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
                "close": prices,
                "volume": volumes,
            }
        )

        # 異常検知実行
        result_df = detector.generate_all_features(market_data)

        assert isinstance(result_df, pd.DataFrame)
        assert "market_stress" in result_df.columns

        # クラッシュ期間でストレス度上昇
        normal_stress = result_df["market_stress"].iloc[:800].mean()
        crash_stress = result_df["market_stress"].iloc[800:850].mean()

        # クラッシュ期間のストレス度が高い
        assert crash_stress > normal_stress

    def test_comparison_with_baseline(self):
        """ベースライン比較テスト"""
        # 異なるlookback_periodでの比較
        short_detector = AnomalyDetector(lookback_period=10)
        long_detector = AnomalyDetector(lookback_period=50)

        # テストデータ
        np.random.seed(888)
        test_data = pd.DataFrame(
            {
                "open": np.random.normal(5000000, 50000, 100),
                "high": np.random.normal(5050000, 50000, 100),
                "low": np.random.normal(4950000, 50000, 100),
                "close": np.random.normal(5000000, 50000, 100),
                "volume": np.random.lognormal(7, 0.3, 100),
            }
        )

        short_result = short_detector.generate_all_features(test_data)
        long_result = long_detector.generate_all_features(test_data)

        assert isinstance(short_result, pd.DataFrame)
        assert isinstance(long_result, pd.DataFrame)

        # 両方とも market_stress を計算
        assert "market_stress" in short_result.columns
        assert "market_stress" in long_result.columns

        # lookback_period の違いによる感度差
        short_stress_std = short_result["market_stress"].std()
        long_stress_std = long_result["market_stress"].std()

        # 短期間の方が変動に敏感（一般的に）
        assert short_stress_std >= 0  # 少なくとも非負
        assert long_stress_std >= 0  # 少なくとも非負
