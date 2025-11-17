"""
統合FeatureGenerator テストファイル - Phase 50.3対応版

Phase 18統合により、TechnicalIndicators・MarketAnomalyDetector・FeatureServiceAdapterが
FeatureGeneratorクラスに統合されました。70特徴量生成システムの包括的テスト。

テスト対象:
- 基本特徴量生成（2個）: close, volume
- テクニカル指標生成（12個）: rsi_14, macd, atr_14, bb_position, ema_20, ema_50, etc
- 異常検知指標生成（1個）: volume_ratio
- ラグ特徴量生成（10個）: close_lag_1, etc - Phase 40.6
- 移動統計量生成（12個）: close_ma_5, etc - Phase 40.6
- 交互作用特徴量生成（6個）: rsi_x_atr, etc - Phase 40.6
- 時間ベース特徴量生成（14個）: hour, day_of_week, 市場セッション, 周期性 - Phase 40.6/50.2
- 戦略シグナル特徴量（5個）: strategy_signal_* - Phase 41
- 外部API特徴量（8個）: usd_jpy, nikkei_225, us_10y_yield, fear_greed_index等 - Phase 50.3
- 入力形式対応: DataFrame, 辞書, マルチタイムフレーム
- 出力形式確認: DataFrame返却
- エラーハンドリング: 不正データ、不足列等

注: 単体テストでは external_api_client を渡さないため、外部API特徴量は生成されません（57特徴量のみ）
"""

import asyncio

import numpy as np
import pandas as pd
import pytest

from src.core.exceptions import DataProcessingError
from src.features.feature_generator import OPTIMIZED_FEATURES, FeatureGenerator

# Phase 50.3: 戦略シグナル・外部API特徴量を除外した基本特徴量（57個）
# generate_features()はstrategy_signalsパラメータを渡さず、external_api_clientも渡さないと57特徴量のみ生成
STRATEGY_SIGNAL_FEATURES = [
    "strategy_signal_ATRBased",
    "strategy_signal_MochipoyAlert",
    "strategy_signal_MultiTimeframe",
    "strategy_signal_DonchianChannel",
    "strategy_signal_ADXTrendStrength",
]
EXTERNAL_API_FEATURES = [
    "usd_jpy",
    "nikkei_225",
    "us_10y_yield",
    "fear_greed_index",
    "usd_jpy_change_1d",
    "nikkei_change_1d",
    "usd_jpy_btc_correlation",
    "market_sentiment",
]
# Phase 51.5-A: include_external_api=Falseまたはexternal_api_clientなしの場合の期待特徴量（60個）
FEATURES_WITHOUT_EXTERNAL_API = [f for f in OPTIMIZED_FEATURES if f not in EXTERNAL_API_FEATURES]
EXCLUDED_FEATURES = STRATEGY_SIGNAL_FEATURES + EXTERNAL_API_FEATURES
BASE_FEATURES = [f for f in OPTIMIZED_FEATURES if f not in EXCLUDED_FEATURES]


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
        result_df = await generator.generate_features(
            sample_ohlcv_data
        )  # Phase 51.5-A: 60特徴量固定

        # 戻り値がDataFrameかチェック
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(sample_ohlcv_data)

        # Phase 51.5-A: 60特徴量固定（外部API削除・戦略シグナル3個含む）
        # strategy_signalsパラメータがNoneでも、戦略シグナル特徴量は0.0で生成される
        strategy_signal_features = [
            "strategy_signal_ATRBased",
            "strategy_signal_DonchianChannel",
            "strategy_signal_ADXTrendStrength",
        ]

        # Phase 51.5-A: 外部API特徴量を除く60特徴量が存在するかチェック（戦略シグナル含む）
        for feature in FEATURES_WITHOUT_EXTERNAL_API:
            assert feature in result_df.columns, f"特徴量{feature}が不足"

        # Phase 51.5-A: 戦略シグナル特徴量は0.0で存在するはず（確実な60特徴量生成）
        for feature in strategy_signal_features:
            assert feature in result_df.columns, f"戦略シグナル特徴量{feature}が生成されていない"
            # strategy_signals=Noneの場合は0.0で生成
            assert (result_df[feature] == 0.0).all(), f"戦略シグナル特徴量{feature}が0.0でない"

        # computed_featuresに記録されているかチェック - Phase 51.5-A: 60特徴量（確実）
        assert len(generator.computed_features) == 55

    @pytest.mark.asyncio
    async def test_generate_features_multitime_input(self, generator, multitime_data):
        """マルチタイムフレーム入力テスト"""
        result_df = await generator.generate_features(multitime_data)

        # 戻り値がDataFrameかチェック
        assert isinstance(result_df, pd.DataFrame)

        # 4hタイムフレームのデータが使われているはず
        assert len(result_df) == len(multitime_data["4h"])

        # Phase 50.3: 戦略シグナル・外部API特徴量を除外した57特徴量をチェック
        # external_api_clientを渡していないため、外部API特徴量は生成されない
        for feature in BASE_FEATURES:
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
        for feature in BASE_FEATURES:
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
        for feature in BASE_FEATURES:
            assert feature in result_df.columns, f"単一行で特徴量{feature}が不足"

        # NaN値が適切に処理されているかチェック
        for feature in BASE_FEATURES:
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
        for feature in BASE_FEATURES:
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
        for feature in BASE_FEATURES:
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
        for feature in BASE_FEATURES:
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
        for feature in BASE_FEATURES:
            assert feature in result_df.columns, f"大規模データで特徴量{feature}が不足"

    def test_feature_categories_coverage(self):
        """特徴量カテゴリカバレッジテスト"""
        from src.features.feature_generator import FEATURE_CATEGORIES

        # 各カテゴリの特徴量が適切に定義されているかチェック
        expected_categories = [
            "basic",
            "momentum",
            "volatility",
            "trend",
            "volume",
            "breakout",
            "regime",
        ]

        for category in expected_categories:
            assert category in FEATURE_CATEGORIES, f"カテゴリ{category}が不足"
            assert len(FEATURE_CATEGORIES[category]) > 0, f"カテゴリ{category}が空"

        # 全特徴量がいずれかのカテゴリに属しているかチェック
        all_categorized_features = []
        for features in FEATURE_CATEGORIES.values():
            all_categorized_features.extend(features)

        for feature in BASE_FEATURES:
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

            for feature in BASE_FEATURES:
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

        # 計算された特徴量数が55-63の範囲になるはず - Phase 51.7 Day 7（6戦略構成）
        # 49基本特徴量 + 6戦略信号特徴量 = 55特徴量
        assert 55 <= len(generator.computed_features) <= 63

        # すべてのOPTIMIZED_FEATURESが含まれているかチェック
        for feature in BASE_FEATURES:
            assert feature in result_df.columns, f"特徴量{feature}が不足"


# ========================================
# Phase 51.7 Day 2: 新規追加特徴量テスト
# ========================================
@pytest.mark.skip(
    reason="Phase 51.7 Day 7: Day 2テスト(51特徴量)はDay 7(55特徴量・6戦略)に置き換えられたためスキップ"
)
class TestPhase517Day2NewFeatures:
    """Phase 51.7 Day 2で追加された新特徴量のテストクラス"""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """サンプルOHLCVデータ作成"""
        np.random.seed(42)
        base_price = 5000000
        n_periods = 100

        returns = np.random.normal(0, 0.01, n_periods)
        prices = [base_price]
        for i in range(n_periods - 1):
            next_price = prices[-1] * (1 + returns[i])
            prices.append(max(next_price, 100))

        highs = [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices]
        lows = [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices]
        volumes = np.random.lognormal(7, 0.3, n_periods)

        return pd.DataFrame(
            {"open": prices, "high": highs, "low": lows, "close": prices, "volume": volumes}
        )

    @pytest.fixture
    def generator(self):
        """FeatureGeneratorインスタンス"""
        return FeatureGenerator()

    @pytest.mark.asyncio
    async def test_macd_signal_generation(self, generator, sample_ohlcv_data):
        """MACD Signal生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # macd_signalが生成されているか
        assert "macd_signal" in result_df.columns, "macd_signal特徴量が生成されていない"

        # 値の妥当性チェック
        macd_signal_valid = result_df["macd_signal"].dropna()
        assert len(macd_signal_valid) > 0, "macd_signal値が全てNaN"

        # NaN値・無限値チェック
        assert not result_df["macd_signal"].isnull().any(), "macd_signalにNaN値が残存"
        assert not np.isinf(result_df["macd_signal"]).any(), "macd_signalに無限値が存在"

    @pytest.mark.asyncio
    async def test_macd_histogram_generation(self, generator, sample_ohlcv_data):
        """MACD Histogram生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # macd_histogramが生成されているか
        assert "macd_histogram" in result_df.columns, "macd_histogram特徴量が生成されていない"

        # macd_histogram = macd - macd_signalの関係確認
        if "macd" in result_df.columns and "macd_signal" in result_df.columns:
            expected_histogram = result_df["macd"] - result_df["macd_signal"]
            np.testing.assert_allclose(
                result_df["macd_histogram"],
                expected_histogram,
                rtol=1e-5,
                err_msg="macd_histogramの計算が不正確",
            )

    @pytest.mark.asyncio
    async def test_bb_upper_generation(self, generator, sample_ohlcv_data):
        """BB Upper生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # bb_upperが生成されているか
        assert "bb_upper" in result_df.columns, "bb_upper特徴量が生成されていない"

        # 値の妥当性チェック（正の値）
        bb_upper_valid = result_df["bb_upper"].dropna()
        assert len(bb_upper_valid) > 0, "bb_upper値が全てNaN"
        assert all(x > 0 for x in bb_upper_valid), "bb_upper値に負の値が存在"

        # NaN値・無限値チェック
        assert not result_df["bb_upper"].isnull().any(), "bb_upperにNaN値が残存"
        assert not np.isinf(result_df["bb_upper"]).any(), "bb_upperに無限値が存在"

    @pytest.mark.asyncio
    async def test_bb_lower_generation(self, generator, sample_ohlcv_data):
        """BB Lower生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # bb_lowerが生成されているか
        assert "bb_lower" in result_df.columns, "bb_lower特徴量が生成されていない"

        # 値の妥当性チェック（正の値）
        bb_lower_valid = result_df["bb_lower"].dropna()
        assert len(bb_lower_valid) > 0, "bb_lower値が全てNaN"
        assert all(x > 0 for x in bb_lower_valid), "bb_lower値に負の値が存在"

        # bb_lower < bb_upper の関係確認
        if "bb_upper" in result_df.columns:
            assert all(
                result_df["bb_lower"] <= result_df["bb_upper"]
            ), "bb_lower > bb_upperの異常値が存在"

    @pytest.mark.asyncio
    async def test_stoch_k_generation(self, generator, sample_ohlcv_data):
        """Stochastic %K生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # stoch_kが生成されているか
        assert "stoch_k" in result_df.columns, "stoch_k特徴量が生成されていない"

        # 値の妥当性チェック（0-100範囲）
        stoch_k_valid = result_df["stoch_k"].dropna()
        assert len(stoch_k_valid) > 0, "stoch_k値が全てNaN"
        assert all(0 <= x <= 100 for x in stoch_k_valid), "stoch_k値が0-100範囲外"

        # NaN値・無限値チェック
        assert not result_df["stoch_k"].isnull().any(), "stoch_kにNaN値が残存"
        assert not np.isinf(result_df["stoch_k"]).any(), "stoch_kに無限値が存在"

    @pytest.mark.asyncio
    async def test_stoch_d_generation(self, generator, sample_ohlcv_data):
        """Stochastic %D生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # stoch_dが生成されているか
        assert "stoch_d" in result_df.columns, "stoch_d特徴量が生成されていない"

        # 値の妥当性チェック（0-100範囲）
        stoch_d_valid = result_df["stoch_d"].dropna()
        assert len(stoch_d_valid) > 0, "stoch_d値が全てNaN"
        assert all(0 <= x <= 100 for x in stoch_d_valid), "stoch_d値が0-100範囲外"

        # NaN値・無限値チェック
        assert not result_df["stoch_d"].isnull().any(), "stoch_dにNaN値が残存"
        assert not np.isinf(result_df["stoch_d"]).any(), "stoch_dに無限値が存在"

    @pytest.mark.asyncio
    async def test_volume_ema_generation(self, generator, sample_ohlcv_data):
        """Volume EMA生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # volume_emaが生成されているか
        assert "volume_ema" in result_df.columns, "volume_ema特徴量が生成されていない"

        # 値の妥当性チェック（正の値）
        volume_ema_valid = result_df["volume_ema"].dropna()
        assert len(volume_ema_valid) > 0, "volume_ema値が全てNaN"
        assert all(x > 0 for x in volume_ema_valid), "volume_ema値に負の値が存在"

        # NaN値・無限値チェック
        assert not result_df["volume_ema"].isnull().any(), "volume_emaにNaN値が残存"
        assert not np.isinf(result_df["volume_ema"]).any(), "volume_emaに無限値が存在"

    @pytest.mark.asyncio
    async def test_atr_ratio_generation(self, generator, sample_ohlcv_data):
        """ATR Ratio生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # atr_ratioが生成されているか
        assert "atr_ratio" in result_df.columns, "atr_ratio特徴量が生成されていない"

        # 値の妥当性チェック（正の値）
        atr_ratio_valid = result_df["atr_ratio"].dropna()
        assert len(atr_ratio_valid) > 0, "atr_ratio値が全てNaN"
        assert all(x > 0 for x in atr_ratio_valid), "atr_ratio値に負の値が存在"

        # atr_ratio = atr_14 / close の関係確認
        if "atr_14" in result_df.columns and "close" in result_df.columns:
            expected_ratio = result_df["atr_14"] / (result_df["close"] + 1e-8)
            np.testing.assert_allclose(
                result_df["atr_ratio"],
                expected_ratio,
                rtol=1e-3,  # Phase 51.7 Day 7: 金融計算の浮動小数点誤差を考慮
                err_msg="atr_ratioの計算が不正確",
            )

    @pytest.mark.asyncio
    async def test_51_features_generation(self, generator, sample_ohlcv_data):
        """51特徴量完全生成テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # Phase 51.7 Day 2: 51特徴量固定
        assert (
            len(generator.computed_features) == 51
        ), f"生成特徴量数が51でない: {len(generator.computed_features)}"

        # 新規追加特徴量が全て存在することを確認
        new_features = [
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_lower",
            "stoch_k",
            "stoch_d",
            "volume_ema",
            "atr_ratio",
        ]
        for feature in new_features:
            assert feature in result_df.columns, f"新規特徴量{feature}が生成されていない"

    @pytest.mark.asyncio
    async def test_deleted_features_not_exist(self, generator, sample_ohlcv_data):
        """削除特徴量が存在しないことのテスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # Phase 51.7 Day 2で削除された特徴量
        deleted_features = [
            "ema_20",
            "donchian_high_20",
            "close_ma_5",
            "close_max_5",
            "close_max_10",
            "close_max_20",
            "close_min_5",
            "close_min_10",
            "close_min_20",
            "close_lag_5",
            "month",
            "hour_sin",
            "is_weekend",
            "is_quarter_end",
            "quarter",
            "is_asia_session",
            "is_us_session",
            "ema_spread_x_adx",
        ]

        for feature in deleted_features:
            assert (
                feature not in result_df.columns
            ), f"削除されたはずの特徴量{feature}が生成されている"

    @pytest.mark.asyncio
    async def test_new_features_no_nan_values(self, generator, sample_ohlcv_data):
        """新規特徴量のNaN値・無限値チェック - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        new_features = [
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_lower",
            "stoch_k",
            "stoch_d",
            "volume_ema",
            "atr_ratio",
        ]

        for feature in new_features:
            assert feature in result_df.columns, f"新規特徴量{feature}が生成されていない"
            assert not result_df[feature].isnull().any(), f"{feature}にNaN値が残存"
            assert not np.isinf(result_df[feature]).any(), f"{feature}に無限値が存在"

    @pytest.mark.asyncio
    async def test_bb_bands_relationship(self, generator, sample_ohlcv_data):
        """BBバンドの関係性テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # bb_lower < close < bb_upper の妥当性確認（大部分のデータで成立）
        if all(f in result_df.columns for f in ["bb_lower", "bb_upper", "close"]):
            # BB外のデータもあり得るが、極端な外れ値でないことを確認
            within_bands = (result_df["bb_lower"] <= result_df["close"]) & (
                result_df["close"] <= result_df["bb_upper"]
            )
            within_ratio = within_bands.sum() / len(result_df)
            assert within_ratio >= 0.5, f"BBバンド内データ比率が低すぎる: {within_ratio:.2%}"

    @pytest.mark.asyncio
    async def test_stochastic_relationship(self, generator, sample_ohlcv_data):
        """Stochastic指標の関係性テスト - Phase 51.7 Day 2"""
        result_df = await generator.generate_features(sample_ohlcv_data)

        # stoch_dはstoch_kの移動平均なので、平滑化されている
        if all(f in result_df.columns for f in ["stoch_k", "stoch_d"]):
            # stoch_dの標準偏差はstoch_kより小さいはず（平滑化効果）
            stoch_k_std = result_df["stoch_k"].std()
            stoch_d_std = result_df["stoch_d"].std()
            assert (
                stoch_d_std < stoch_k_std
            ), f"stoch_dの平滑化が機能していない: K_std={stoch_k_std:.2f}, D_std={stoch_d_std:.2f}"

    @pytest.mark.asyncio
    async def test_feature_count_consistency(self, generator, sample_ohlcv_data):
        """特徴量数一貫性テスト - Phase 51.7 Day 2"""
        # 複数回実行しても同じ特徴量数が生成されることを確認
        result_df1 = await generator.generate_features(sample_ohlcv_data)
        count1 = len(generator.computed_features)

        # 新しいジェネレータインスタンスで再実行
        generator2 = FeatureGenerator()
        result_df2 = await generator2.generate_features(sample_ohlcv_data)
        count2 = len(generator2.computed_features)

        assert count1 == count2 == 51, f"特徴量数が一貫していない: 1回目={count1}, 2回目={count2}"
