"""
統合FeatureGenerator テストファイル - Phase 18対応版

Phase 18統合により、TechnicalIndicators・MarketAnomalyDetector・FeatureServiceAdapterが
FeatureGeneratorクラスに統合されました。12特徴量生成システムの包括的テスト。

テスト対象:
- 基本特徴量生成（3個）: close, volume, returns_1
- テクニカル指標生成（6個）: rsi_14, macd, atr_14, bb_position, ema_20, ema_50
- 異常検知指標生成（3個）: zscore, volume_ratio, market_stress
- 入力形式対応: DataFrame, 辞書, マルチタイムフレーム
- 出力形式確認: DataFrame返却
- エラーハンドリング: 不正データ、不足列等
"""

import asyncio

import numpy as np
import pandas as pd
import pytest

from src.core.exceptions import DataProcessingError
from src.features.feature_generator import OPTIMIZED_FEATURES, FeatureGenerator


class TestFeatureGenerator:
    """FeatureGenerator統合版メインテストクラス"""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """サンプルOHLCVデータ作成"""
        np.random.seed(42)
        base_price = 5000000  # 500万円のBTC/JPY
        n_periods = 100

        # リアルな価格変動を模擬
        returns = np.random.normal(0, 0.01, n_periods)  # 日次1%標準偏差
        prices = [base_price]

        for i in range(n_periods - 1):
            next_price = prices[-1] * (1 + returns[i])
            prices.append(max(next_price, 100))  # 最小値100

        # OHLCV データ作成
        highs = [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices]
        lows = [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices]
        volumes = np.random.lognormal(7, 0.3, n_periods)  # 対数正規分布

        return pd.DataFrame(
            {"open": prices, "high": highs, "low": lows, "close": prices, "volume": volumes}
        )

    @pytest.fixture
    def multitime_data(self, sample_ohlcv_data):
        """マルチタイムフレームデータ作成"""
        return {"4h": sample_ohlcv_data, "15m": sample_ohlcv_data[:50].copy()}  # 短いデータセット

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_init_default(self, generator):
        """デフォルト初期化テスト"""
        assert isinstance(generator, FeatureGenerator)
        assert hasattr(generator, "logger")
        assert hasattr(generator, "computed_features")
        assert hasattr(generator, "lookback_period")
        assert len(generator.computed_features) == 0

    def test_init_custom_lookback(self):
        """カスタムlookback_period初期化テスト"""
        generator = FeatureGenerator(lookback_period=30)
        assert generator.lookback_period == 30
        assert isinstance(generator, FeatureGenerator)

    @pytest.mark.asyncio
    async def test_generate_features_basic_dataframe(self, generator, sample_ohlcv_data):
        """基本特徴量生成テスト（DataFrame入力）"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # 戻り値がDataFrameかチェック
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(sample_ohlcv_data)

        # 12特徴量すべてが存在するかチェック
        for feature in OPTIMIZED_FEATURES:
            assert feature in result_df.columns, f"特徴量{feature}が不足"

        # computed_featuresに記録されているかチェック
        assert len(generator.computed_features) == 12

    @pytest.mark.asyncio
    async def test_generate_features_multitime_input(self, generator, multitime_data):
        """マルチタイムフレーム入力テスト"""
        result_df = await generator.generate_features(multitime_data)

        # 戻り値がDataFrameかチェック
        assert isinstance(result_df, pd.DataFrame)

        # 4hタイムフレームのデータが使われているはず
        assert len(result_df) == len(multitime_data["4h"])

        # 12特徴量すべてが存在するかチェック
        for feature in OPTIMIZED_FEATURES:
            assert feature in result_df.columns, f"特徴量{feature}が不足"

    @pytest.mark.asyncio
    async def test_feature_validation_values(self, generator, sample_ohlcv_data):
        """特徴量値の妥当性テスト"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # RSI: 0-100の範囲
        if "rsi_14" in result_df.columns:
            rsi_valid = result_df["rsi_14"].dropna()
            if len(rsi_valid) > 0:
                assert all(0 <= x <= 100 for x in rsi_valid), "RSI値が0-100範囲外"

        # ATR: 正の値
        if "atr_14" in result_df.columns:
            atr_valid = result_df["atr_14"].dropna()
            if len(atr_valid) > 0:
                assert all(x > 0 for x in atr_valid), "ATR値が負"

        # BB position: 実装に応じた妥当な範囲（通常-3〜3程度）
        if "bb_position" in result_df.columns:
            bb_valid = result_df["bb_position"].dropna()
            if len(bb_valid) > 0:
                assert all(-5 <= x <= 5 for x in bb_valid), "BB position値が異常範囲"

        # Phase 19: market_stress削除（12特徴量統一）
        # market_stress: 0-1の範囲
        # if "market_stress" in result_df.columns:
        #     stress_valid = result_df["market_stress"].dropna()
        #     if len(stress_valid) > 0:
        #         assert all(0 <= x <= 1 for x in stress_valid), "market_stress値が0-1範囲外"

        # volume_ratio: 正の値
        if "volume_ratio" in result_df.columns:
            volume_ratio_valid = result_df["volume_ratio"].dropna()
            if len(volume_ratio_valid) > 0:
                assert all(x > 0 for x in volume_ratio_valid), "volume_ratio値が負"

        # NaN値処理確認
        for feature in OPTIMIZED_FEATURES:
            if feature in result_df.columns:
                assert not result_df[feature].isnull().any(), f"{feature}にNaN値が残存"
                assert not np.isinf(result_df[feature]).any(), f"{feature}に無限値が存在"

    @pytest.mark.asyncio
    async def test_missing_columns_error(self, generator):
        """必要列不足エラーテスト"""
        incomplete_df = pd.DataFrame(
            {
                "close": [100, 101, 102, 103, 104],
                "volume": [1000, 1100, 1200, 1300, 1400],
                # open, high, low が不足
            }
        )

        with pytest.raises(DataProcessingError, match="必要列が不足"):
            await generator.generate_features(incomplete_df)

    @pytest.mark.asyncio
    async def test_empty_data_handling(self, generator):
        """空データ処理テスト"""
        empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        try:
            result_df = await generator.generate_features(empty_df)
            assert isinstance(result_df, pd.DataFrame)
            assert len(result_df) == 0
        except (DataProcessingError, ValueError):
            # 空データでエラーは許容される
            pass

    @pytest.mark.asyncio
    async def test_single_row_data(self, generator):
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

        result_df = await generator.generate_features(single_row_df)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 1

        # 単一行でも12特徴量が生成されるかチェック
        for feature in OPTIMIZED_FEATURES:
            assert feature in result_df.columns, f"単一行で特徴量{feature}が不足"

        # NaN値が適切に処理されているかチェック
        for feature in OPTIMIZED_FEATURES:
            assert not result_df[feature].isnull().any(), f"単一行で{feature}にNaN残存"

    @pytest.mark.asyncio
    async def test_dict_input_conversion(self, generator):
        """辞書入力変換テスト"""
        dict_data = {
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [103, 104, 105, 106, 107],
            "volume": [1000, 1100, 1200, 1300, 1400],
        }

        result_df = await generator.generate_features(dict_data)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 5

        # 12特徴量すべてが生成されているかチェック
        for feature in OPTIMIZED_FEATURES:
            assert feature in result_df.columns, f"辞書入力で特徴量{feature}が不足"

    @pytest.mark.asyncio
    async def test_nan_data_handling(self, generator):
        """NaN値含むデータ処理テスト"""
        data_with_nan = pd.DataFrame(
            {
                "open": [5000000, np.nan, 5100000, 4900000, 5050000],
                "high": [5050000, 5150000, np.nan, 4950000, 5100000],
                "low": [4950000, 4950000, 4950000, np.nan, 4900000],
                "close": [5000000, 5100000, 5000000, 4900000, np.nan],
                "volume": [1000, 1100, np.nan, 900, 1050],
            }
        )

        result_df = await generator.generate_features(data_with_nan)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(data_with_nan)

        # NaN値が適切に処理されているかチェック
        for feature in OPTIMIZED_FEATURES:
            if feature in result_df.columns:
                assert not result_df[feature].isnull().any(), f"NaN処理後に{feature}にNaN残存"
                assert not np.isinf(result_df[feature]).any(), f"NaN処理後に{feature}に無限値存在"

    @pytest.mark.asyncio
    async def test_extreme_values_handling(self, generator):
        """極端値処理テスト"""
        extreme_df = pd.DataFrame(
            {
                "open": [1, 1000000, 1, 1000000, 1],
                "high": [2, 1100000, 2, 1100000, 2],
                "low": [0.5, 900000, 0.5, 900000, 0.5],
                "close": [1, 1000000, 1, 1000000, 1],
                "volume": [1, 1000000000, 1, 1000000000, 1],
            }
        )

        result_df = await generator.generate_features(extreme_df)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 5

        # 極端な値でも処理が完了することを確認
        for feature in OPTIMIZED_FEATURES:
            if feature in result_df.columns:
                assert not np.isinf(result_df[feature]).any(), f"極端値処理で{feature}に無限値"
                assert not result_df[feature].isnull().any(), f"極端値処理で{feature}にNaN残存"

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, generator):
        """大規模データ性能テスト"""
        # 5,000行のデータ
        np.random.seed(999)
        n_large = 5000
        base_price = 5000000

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

        result_df = await generator.generate_features(large_df)

        elapsed_time = time.time() - start_time

        # 5,000行で10秒以内
        assert elapsed_time < 10.0, f"Performance too slow: {elapsed_time:.3f}s"
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == n_large

        # 12特徴量すべて生成確認
        for feature in OPTIMIZED_FEATURES:
            assert feature in result_df.columns, f"大規模データで特徴量{feature}が不足"

    def test_feature_categories_coverage(self):
        """特徴量カテゴリカバレッジテスト"""
        from src.features.feature_generator import FEATURE_CATEGORIES

        # 各カテゴリの特徴量が適切に定義されているかチェック
        expected_categories = ["basic", "momentum", "volatility", "trend", "volume", "anomaly"]

        for category in expected_categories:
            assert category in FEATURE_CATEGORIES, f"カテゴリ{category}が不足"
            assert len(FEATURE_CATEGORIES[category]) > 0, f"カテゴリ{category}が空"

        # 全特徴量がいずれかのカテゴリに属しているかチェック
        all_categorized_features = []
        for features in FEATURE_CATEGORIES.values():
            all_categorized_features.extend(features)

        for feature in OPTIMIZED_FEATURES:
            assert feature in all_categorized_features, f"特徴量{feature}がカテゴリ未分類"

    @pytest.mark.asyncio
    async def test_multitime_preference_order(self, generator):
        """マルチタイムフレーム優先順位テスト"""
        # 4hと15mの両方を含むデータ
        multitime_data = {
            "15m": pd.DataFrame(
                {
                    "open": [100] * 10,
                    "high": [105] * 10,
                    "low": [95] * 10,
                    "close": [103] * 10,
                    "volume": [1000] * 10,
                }
            ),
            "4h": pd.DataFrame(
                {
                    "open": [200] * 20,  # 異なる価格
                    "high": [205] * 20,
                    "low": [195] * 20,
                    "close": [203] * 20,
                    "volume": [2000] * 20,
                }
            ),
        }

        result_df = await generator.generate_features(multitime_data)

        # 4hタイムフレームが優先されているはず（価格=200番台）
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 20  # 4hデータの長さ
        assert result_df["close"].iloc[0] == 203  # 4hデータの価格

    @pytest.mark.asyncio
    async def test_concurrent_generation(self, generator, sample_ohlcv_data):
        """並行特徴量生成テスト"""
        # 同じデータで複数回並行実行
        tasks = [generator.generate_features(sample_ohlcv_data) for _ in range(3)]

        results = await asyncio.gather(*tasks)

        # すべての結果が正常
        for result in results:
            assert isinstance(result, pd.DataFrame)
            assert len(result) == len(sample_ohlcv_data)

            for feature in OPTIMIZED_FEATURES:
                assert feature in result.columns, f"並行実行で特徴量{feature}が不足"

        # 結果の一貫性確認（同じ入力なので同じ結果になるはず）
        for i in range(1, len(results)):
            pd.testing.assert_frame_equal(results[0], results[i])


class TestFeatureGeneratorPrivateMethods:
    """FeatureGeneratorプライベートメソッドテスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator(lookback_period=10)

    @pytest.fixture
    def sample_data(self):
        """サンプルデータ"""
        np.random.seed(123)
        return pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [103, 104, 105, 106, 107],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

    def test_convert_to_dataframe_dict_input(self, generator):
        """辞書→DataFrame変換テスト"""
        dict_input = {
            "open": [100, 101],
            "high": [105, 106],
            "low": [95, 96],
            "close": [103, 104],
            "volume": [1000, 1100],
        }

        result = generator._convert_to_dataframe(dict_input)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["open", "high", "low", "close", "volume"]

    def test_convert_to_dataframe_multitime_input(self, generator, sample_data):
        """マルチタイムフレーム→DataFrame変換テスト"""
        multitime_input = {"4h": sample_data, "15m": sample_data[:3]}

        result = generator._convert_to_dataframe(multitime_input)

        # 4hが優先されるはず
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_data)
        pd.testing.assert_frame_equal(result, sample_data)

    def test_validate_required_columns_success(self, generator, sample_data):
        """必要列存在確認成功テスト"""
        # エラーなしで完了するはず
        generator._validate_required_columns(sample_data)

    def test_validate_required_columns_failure(self, generator):
        """必要列存在確認失敗テスト"""
        incomplete_df = pd.DataFrame(
            {
                "close": [100, 101],
                "volume": [1000, 1100],
                # open, high, low が不足
            }
        )

        with pytest.raises(DataProcessingError, match="必要列が不足"):
            generator._validate_required_columns(incomplete_df)

    def test_handle_nan_values_integration(self, generator):
        """NaN値処理統合テスト（実際の特徴量生成時）"""
        # 完全なOHLCVデータでのNaN処理テスト
        data_with_complete_ohlcv = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [103, 104, 105, 106, 107],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        # _handle_nan_valuesメソッドは統合プロセス内で動作する
        result = generator._handle_nan_values(data_with_complete_ohlcv)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(data_with_complete_ohlcv)

        # 完全なデータではNaN値が残存しないことを確認
        assert not result.isnull().any().any(), "完全データでNaN値が残存"
        assert not np.isinf(result).any().any(), "完全データで無限値が存在"

    @pytest.mark.asyncio
    async def test_validate_feature_generation_integration(self, generator, sample_data):
        """特徴量生成検証統合テスト（実際の生成プロセス経由）"""
        # 実際の特徴量生成プロセスを経由
        result_df = await generator.generate_features(sample_data)

        # 特徴量生成後の検証メソッドを呼び出し
        generator._validate_feature_generation(result_df)

        # 計算された特徴量数が12になるはず
        assert len(generator.computed_features) == 12

        # すべてのOPTIMIZED_FEATURESが含まれているかチェック
        for feature in OPTIMIZED_FEATURES:
            assert feature in result_df.columns, f"特徴量{feature}が不足"
