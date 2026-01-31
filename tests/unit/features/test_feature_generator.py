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


class TestFeatureGeneratorSyncMethod:
    """generate_features_sync メソッドのテスト（同期版特徴量生成）"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

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

    def test_generate_features_sync_basic(self, generator, sample_ohlcv_data):
        """同期版特徴量生成基本テスト"""
        result_df = generator.generate_features_sync(sample_ohlcv_data)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(sample_ohlcv_data)

        # 基本特徴量が生成されているかチェック
        for feature in BASE_FEATURES:
            assert feature in result_df.columns, f"特徴量{feature}が不足"

    def test_generate_features_sync_with_strategy_signals(self, generator, sample_ohlcv_data):
        """同期版特徴量生成 - 戦略シグナル付きテスト"""
        strategy_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.7, "encoded": 0.7},
            "DonchianChannel": {"action": "sell", "confidence": 0.6, "encoded": -0.6},
            "BBReversal": {"action": "hold", "confidence": 0.5, "encoded": 0.0},
        }

        result_df = generator.generate_features_sync(sample_ohlcv_data, strategy_signals)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(sample_ohlcv_data)

        # 戦略シグナル特徴量が生成されているかチェック
        assert "strategy_signal_ATRBased" in result_df.columns
        assert "strategy_signal_DonchianChannel" in result_df.columns

    def test_generate_features_sync_error_handling(self, generator):
        """同期版特徴量生成エラーハンドリングテスト"""
        incomplete_df = pd.DataFrame(
            {
                "close": [100, 101],
                "volume": [1000, 1100],
                # open, high, low が不足
            }
        )

        with pytest.raises(DataProcessingError, match="必要列が不足"):
            generator.generate_features_sync(incomplete_df)

    def test_generate_features_sync_nan_handling(self, generator):
        """同期版特徴量生成NaN処理テスト"""
        data_with_nan = pd.DataFrame(
            {
                "open": [5000000, np.nan, 5100000, 4900000, 5050000],
                "high": [5050000, 5150000, np.nan, 4950000, 5100000],
                "low": [4950000, 4950000, 4950000, np.nan, 4900000],
                "close": [5000000, 5100000, 5000000, 4900000, np.nan],
                "volume": [1000, 1100, np.nan, 900, 1050],
            }
        )

        result_df = generator.generate_features_sync(data_with_nan)

        assert isinstance(result_df, pd.DataFrame)
        # NaN値が処理されているかチェック
        for feature in BASE_FEATURES:
            if feature in result_df.columns:
                assert not result_df[feature].isnull().any(), f"{feature}にNaN残存"


class TestTimeFeatures:
    """時間ベース特徴量生成テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_time_features_with_datetime_index(self, generator):
        """DatetimeIndexを持つデータでの時間特徴量生成テスト"""
        # DatetimeIndexを持つDataFrame作成
        dates = pd.date_range("2025-01-01 09:00", periods=50, freq="h")
        df = pd.DataFrame(
            {
                "open": np.random.uniform(5000000, 5100000, 50),
                "high": np.random.uniform(5050000, 5150000, 50),
                "low": np.random.uniform(4950000, 5000000, 50),
                "close": np.random.uniform(5000000, 5100000, 50),
                "volume": np.random.uniform(1000, 2000, 50),
            },
            index=dates,
        )

        result_df = generator._generate_time_features(df)

        # 時間特徴量が生成されているかチェック
        assert "hour" in result_df.columns
        assert "day_of_week" in result_df.columns
        assert "is_market_open_hour" in result_df.columns
        assert "is_europe_session" in result_df.columns
        assert "hour_cos" in result_df.columns
        assert "day_sin" in result_df.columns
        assert "day_cos" in result_df.columns

        # 時間値が正しいかチェック
        assert result_df["hour"].iloc[0] == 9  # 最初の時間は9時
        assert all(0 <= h <= 23 for h in result_df["hour"])
        assert all(0 <= d <= 6 for d in result_df["day_of_week"])

    def test_time_features_with_timestamp_column(self, generator):
        """timestamp列を持つデータでの時間特徴量生成テスト"""
        dates = pd.date_range("2025-01-01 09:00", periods=50, freq="h")
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": np.random.uniform(5000000, 5100000, 50),
                "high": np.random.uniform(5050000, 5150000, 50),
                "low": np.random.uniform(4950000, 5000000, 50),
                "close": np.random.uniform(5000000, 5100000, 50),
                "volume": np.random.uniform(1000, 2000, 50),
            }
        )

        result_df = generator._generate_time_features(df)

        # 時間特徴量が生成されているかチェック
        assert "hour" in result_df.columns
        assert "day_of_week" in result_df.columns
        assert "is_market_open_hour" in result_df.columns
        assert "is_europe_session" in result_df.columns

    def test_time_features_europe_session(self, generator):
        """欧州セッション判定テスト（日をまたぐ処理）"""
        # 欧州セッション時間帯を含むデータ作成
        hours = [15, 16, 17, 22, 23, 0, 1, 2, 6, 12]
        dates = [pd.Timestamp(f"2025-01-01 {h:02d}:00") for h in hours]
        df = pd.DataFrame(
            {
                "open": [100] * 10,
                "high": [105] * 10,
                "low": [95] * 10,
                "close": [103] * 10,
                "volume": [1000] * 10,
            },
            index=pd.DatetimeIndex(dates),
        )

        result_df = generator._generate_time_features(df)

        # 欧州セッション判定チェック（16:00-01:00がTrue）
        expected_europe = [0, 1, 1, 1, 1, 1, 0, 0, 0, 0]
        assert list(result_df["is_europe_session"]) == expected_europe

    def test_time_features_market_open_hour(self, generator):
        """市場オープン時間判定テスト（9-15時）"""
        hours = [8, 9, 10, 14, 15, 16, 20]
        dates = [pd.Timestamp(f"2025-01-01 {h:02d}:00") for h in hours]
        df = pd.DataFrame(
            {
                "open": [100] * 7,
                "high": [105] * 7,
                "low": [95] * 7,
                "close": [103] * 7,
                "volume": [1000] * 7,
            },
            index=pd.DatetimeIndex(dates),
        )

        result_df = generator._generate_time_features(df)

        # 市場オープン時間判定チェック（9-15時がTrue）
        expected_market_open = [0, 1, 1, 1, 1, 0, 0]
        assert list(result_df["is_market_open_hour"]) == expected_market_open

    def test_time_features_cyclic_encoding(self, generator):
        """周期性エンコーディングテスト"""
        dates = pd.date_range("2025-01-01", periods=24, freq="h")
        df = pd.DataFrame(
            {
                "open": [100] * 24,
                "high": [105] * 24,
                "low": [95] * 24,
                "close": [103] * 24,
                "volume": [1000] * 24,
            },
            index=dates,
        )

        result_df = generator._generate_time_features(df)

        # 周期性エンコーディング値の範囲チェック
        assert all(-1 <= v <= 1 for v in result_df["hour_cos"])
        assert all(-1 <= v <= 1 for v in result_df["day_sin"])
        assert all(-1 <= v <= 1 for v in result_df["day_cos"])


class TestStrategySignalFeatures:
    """戦略シグナル特徴量テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    @pytest.fixture
    def sample_df(self):
        """サンプルDataFrame"""
        return pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [103, 104, 105],
                "volume": [1000, 1100, 1200],
            }
        )

    def test_add_strategy_signal_features_with_full_signals(self, generator, sample_df):
        """完全な戦略シグナルでの特徴量追加テスト"""
        strategy_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.8, "encoded": 0.8},
            "DonchianChannel": {"action": "sell", "confidence": 0.7, "encoded": -0.7},
            "BBReversal": {"action": "hold", "confidence": 0.5, "encoded": 0.0},
            "StochasticReversal": {"action": "buy", "confidence": 0.65, "encoded": 0.65},
            "ADXTrendStrength": {"action": "sell", "confidence": 0.55, "encoded": -0.55},
            "MACDEMACrossover": {"action": "buy", "confidence": 0.72, "encoded": 0.72},
        }

        result_df = generator._add_strategy_signal_features(sample_df, strategy_signals)

        # 戦略シグナル特徴量がエンコード値で設定されているかチェック
        assert "strategy_signal_ATRBased" in result_df.columns
        assert result_df["strategy_signal_ATRBased"].iloc[0] == 0.8

        assert "strategy_signal_DonchianChannel" in result_df.columns
        assert result_df["strategy_signal_DonchianChannel"].iloc[0] == -0.7

    def test_add_strategy_signal_features_partial_signals(self, generator, sample_df):
        """一部戦略シグナルのみの場合のテスト"""
        strategy_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.8, "encoded": 0.8},
            # 他の戦略シグナルがない
        }

        result_df = generator._add_strategy_signal_features(sample_df, strategy_signals)

        # ATRBasedは設定された値、他は0.0で補完
        assert "strategy_signal_ATRBased" in result_df.columns
        assert result_df["strategy_signal_ATRBased"].iloc[0] == 0.8

    def test_add_strategy_signal_features_none_signals(self, generator, sample_df):
        """戦略シグナルがNoneの場合のテスト"""
        result_df = generator._add_strategy_signal_features(sample_df, None)

        # 全戦略シグナルが0.0で生成されているかチェック
        assert "strategy_signal_ATRBased" in result_df.columns
        assert (result_df["strategy_signal_ATRBased"] == 0.0).all()

    def test_add_strategy_signal_features_empty_signals(self, generator, sample_df):
        """戦略シグナルが空辞書の場合のテスト"""
        result_df = generator._add_strategy_signal_features(sample_df, {})

        # 全戦略シグナルが0.0で生成されているかチェック
        assert "strategy_signal_ATRBased" in result_df.columns
        assert (result_df["strategy_signal_ATRBased"] == 0.0).all()


class TestConvertToDataFrameEdgeCases:
    """_convert_to_dataframe エッジケーステスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_convert_to_dataframe_unsupported_type(self, generator):
        """サポートされていない型でのエラーテスト"""
        with pytest.raises(ValueError, match="Unsupported market_data type"):
            generator._convert_to_dataframe([1, 2, 3])  # リスト型は非サポート

    def test_convert_to_dataframe_complex_dict_structure(self, generator):
        """複雑な辞書構造での変換テスト"""
        # DataFrameを含まない辞書
        complex_dict = {
            "some_key": {"nested": "value"},
            "another_key": [1, 2, 3],
        }

        # DataProcessingErrorが発生するはず
        with pytest.raises(DataProcessingError):
            generator._convert_to_dataframe(complex_dict)


class TestNormalizeMethod:
    """_normalize メソッドテスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_normalize_basic(self, generator):
        """基本正規化テスト"""
        series = pd.Series([0, 50, 100, 150, 200])
        result = generator._normalize(series)

        # 0-1の範囲になるかチェック
        assert all(0 <= v <= 1 for v in result)

    def test_normalize_constant_values(self, generator):
        """定数値の正規化テスト（分母がゼロになるケース）"""
        series = pd.Series([100, 100, 100, 100, 100])
        result = generator._normalize(series)

        # 定数の場合は全てゼロになる
        assert all(v == 0 for v in result)

    def test_normalize_with_outliers(self, generator):
        """外れ値を含むデータの正規化テスト"""
        series = pd.Series([1, 2, 3, 4, 5, 1000])  # 1000は外れ値
        result = generator._normalize(series)

        # 外れ値がクリップされて0-1範囲になる
        assert all(0 <= v <= 1 for v in result)


class TestVolumeRatioEdgeCases:
    """_calculate_volume_ratio エッジケーステスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_volume_ratio_custom_period(self, generator):
        """カスタム期間での出来高比率計算テスト"""
        volume = pd.Series([1000, 1100, 1200, 1300, 1400, 1500])
        result = generator._calculate_volume_ratio(volume, period=3)

        assert len(result) == len(volume)
        assert all(v > 0 for v in result)


class TestDonchianChannelEdgeCases:
    """_calculate_donchian_channel エッジケーステスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_donchian_channel_error_handling(self, generator):
        """Donchian Channel計算エラーハンドリングテスト"""
        # 不正なデータでエラーをトリガー
        # 注: 実際にはpandasがエラーを適切にハンドルするため、
        # このテストは正常動作を確認
        df = pd.DataFrame(
            {
                "high": [100, 101, 102],
                "low": [95, 96, 97],
                "close": [98, 99, 100],
            }
        )

        high, low, position = generator._calculate_donchian_channel(df, period=2)

        assert len(high) == 3
        assert len(low) == 3
        assert len(position) == 3


class TestGetFeatureInfo:
    """get_feature_info メソッドテスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator(lookback_period=15)

    @pytest.mark.asyncio
    async def test_get_feature_info_after_generation(self, generator):
        """特徴量生成後の情報取得テスト"""
        # 先に特徴量を生成
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [103, 104, 105, 106, 107],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )
        await generator.generate_features(df)

        info = generator.get_feature_info()

        assert "total_features" in info
        assert "computed_features" in info
        assert "feature_categories" in info
        assert "optimized_features" in info
        assert "parameters" in info
        assert "feature_descriptions" in info

        assert info["parameters"]["lookback_period"] == 15
        assert isinstance(info["computed_features"], list)
        assert len(info["computed_features"]) > 0

    def test_get_feature_info_before_generation(self, generator):
        """特徴量生成前の情報取得テスト"""
        info = generator.get_feature_info()

        assert info["total_features"] == 0
        assert info["computed_features"] == []
        assert info["parameters"]["lookback_period"] == 15


class TestADXIndicatorsEdgeCases:
    """_calculate_adx_indicators エッジケーステスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_adx_calculation_basic(self, generator):
        """ADX計算基本テスト"""
        np.random.seed(42)
        df = pd.DataFrame(
            {
                "high": np.random.uniform(105, 110, 30),
                "low": np.random.uniform(95, 100, 30),
                "close": np.random.uniform(100, 105, 30),
            }
        )

        adx, plus_di, minus_di = generator._calculate_adx_indicators(df)

        assert len(adx) == 30
        assert len(plus_di) == 30
        assert len(minus_di) == 30

        # 全ての値が有限（NaNや無限値でない）
        assert not adx.isnull().any()
        assert not plus_di.isnull().any()
        assert not minus_di.isnull().any()

    def test_adx_calculation_short_period(self, generator):
        """短期間データでのADX計算テスト"""
        df = pd.DataFrame(
            {
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [100, 101, 102],
            }
        )

        adx, plus_di, minus_di = generator._calculate_adx_indicators(df, period=2)

        # 短いデータでも計算が完了すること
        assert len(adx) == 3
        assert len(plus_di) == 3
        assert len(minus_di) == 3


class TestValidateFeatureGenerationWarning:
    """_validate_feature_generation 不足特徴量警告テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_validate_with_missing_features(self, generator, caplog):
        """不足特徴量がある場合の警告テスト"""
        import logging

        # 一部の特徴量のみ持つDataFrame
        df = pd.DataFrame(
            {
                "close": [100, 101, 102],
                "volume": [1000, 1100, 1200],
                "rsi_14": [50, 55, 60],
                # 他の必要特徴量が不足
            }
        )

        # computed_featuresにいくつかの特徴量を追加
        generator.computed_features = {"close", "volume", "rsi_14"}

        with caplog.at_level(logging.WARNING):
            generator._validate_feature_generation(df, expected_count=55)

        # 警告メッセージが出力されているかチェック
        assert any("特徴量不足検出" in record.message for record in caplog.records)


class TestExceptionHandlingEdgeCases:
    """例外処理のエッジケーステスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_normalize_exception_handling(self, generator):
        """_normalizeの例外処理テスト"""
        from unittest.mock import patch

        # quantileメソッドで例外を発生させる
        with patch.object(pd.Series, 'quantile', side_effect=Exception("Quantile error")):
            series = pd.Series([1, 2, 3, 4, 5])
            result = generator._normalize(series)

            # 例外発生時はゼロ系列が返される
            assert len(result) == 5
            assert all(v == 0 for v in result)

    def test_volume_ratio_exception_handling(self, generator):
        """_calculate_volume_ratioの例外処理テスト"""
        from unittest.mock import patch

        # rollingメソッドで例外を発生させる
        with patch.object(pd.Series, 'rolling', side_effect=Exception("Rolling error")):
            volume = pd.Series([1000, 1100, 1200], index=[0, 1, 2])
            result = generator._calculate_volume_ratio(volume)

            # 例外発生時はゼロ系列が返される
            assert len(result) == 3
            assert all(v == 0 for v in result)

    def test_adx_exception_handling(self, generator):
        """_calculate_adx_indicatorsの例外処理テスト"""
        from unittest.mock import patch

        df = pd.DataFrame(
            {
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [100, 101, 102],
            }
        )

        # rolling計算で例外を発生させる
        with patch.object(pd.Series, 'rolling', side_effect=Exception("Rolling error")):
            adx, plus_di, minus_di = generator._calculate_adx_indicators(df)

            # 例外発生時はゼロ系列が返される
            assert len(adx) == 3
            assert len(plus_di) == 3
            assert len(minus_di) == 3
            assert all(v == 0 for v in adx)
            assert all(v == 0 for v in plus_di)
            assert all(v == 0 for v in minus_di)


class TestStochasticCalculation:
    """Stochastic Oscillator計算テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_stochastic_basic(self, generator):
        """Stochastic基本計算テスト"""
        df = pd.DataFrame(
            {
                "high": [110, 112, 115, 113, 118, 120],
                "low": [100, 102, 105, 103, 108, 110],
                "close": [105, 108, 112, 108, 115, 118],
            }
        )

        stoch_k, stoch_d = generator._calculate_stochastic(df, period=3)

        assert len(stoch_k) == 6
        assert len(stoch_d) == 6

        # Stochasticは0-100の範囲
        assert all(0 <= v <= 100 for v in stoch_k.dropna())
        assert all(0 <= v <= 100 for v in stoch_d.dropna())


class TestBollingerBandsCalculation:
    """Bollinger Bands計算テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_bollinger_bands_basic(self, generator):
        """Bollinger Bands基本計算テスト"""
        close = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])

        bb_upper, bb_lower, bb_position = generator._calculate_bb_bands(close, period=5)

        assert len(bb_upper) == 10
        assert len(bb_lower) == 10
        assert len(bb_position) == 10

        # 上限は下限より大きい（NaN値を除く）
        valid_indices = (~bb_upper.isna()) & (~bb_lower.isna())
        assert all(bb_upper[valid_indices].iloc[i] >= bb_lower[valid_indices].iloc[i]
                   for i in range(sum(valid_indices)))

        # 位置は0-1の範囲（概ね）
        assert all(-0.5 <= v <= 1.5 for v in bb_position.dropna())


class TestMACDCalculation:
    """MACD計算テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_macd_basic(self, generator):
        """MACD基本計算テスト"""
        close = pd.Series([100 + i for i in range(50)])

        macd_line, macd_signal = generator._calculate_macd(close)

        assert len(macd_line) == 50
        assert len(macd_signal) == 50

        # トレンドが上昇の場合、MACDはプラスになるはず
        assert macd_line.iloc[-1] > 0


class TestRSICalculation:
    """RSI計算テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_rsi_basic(self, generator):
        """RSI基本計算テスト"""
        # 上昇トレンドのデータ
        close = pd.Series([100 + i for i in range(20)])
        rsi = generator._calculate_rsi(close, period=14)

        assert len(rsi) == 20
        # 上昇トレンドなのでRSIは高い値になるはず
        assert rsi.iloc[-1] > 50

    def test_rsi_downtrend(self, generator):
        """RSI下降トレンド計算テスト"""
        # 下降トレンドのデータ
        close = pd.Series([100 - i for i in range(20)])
        rsi = generator._calculate_rsi(close, period=14)

        assert len(rsi) == 20
        # 下降トレンドなのでRSIは低い値になるはず
        assert rsi.iloc[-1] < 50


class TestATRCalculation:
    """ATR計算テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_atr_basic(self, generator):
        """ATR基本計算テスト"""
        df = pd.DataFrame(
            {
                "high": [110, 112, 115, 113, 118],
                "low": [100, 102, 105, 103, 108],
                "close": [105, 108, 112, 108, 115],
            }
        )

        atr = generator._calculate_atr(df, period=3)

        assert len(atr) == 5
        # ATRは常に正の値
        assert all(v > 0 for v in atr.dropna())


class TestVolumeEMACalculation:
    """Volume EMA計算テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_volume_ema_basic(self, generator):
        """Volume EMA基本計算テスト"""
        volume = pd.Series([1000, 1100, 1200, 1300, 1400])
        volume_ema = generator._calculate_volume_ema(volume, period=3)

        assert len(volume_ema) == 5
        # EMAは常に正の値
        assert all(v > 0 for v in volume_ema)


class TestATRRatioCalculation:
    """ATR Ratio計算テスト"""

    @pytest.fixture
    def generator(self):
        """FeatureGenerator インスタンス"""
        return FeatureGenerator()

    def test_atr_ratio_basic(self, generator):
        """ATR Ratio基本計算テスト"""
        df = pd.DataFrame(
            {
                "close": [5000000, 5100000, 5200000],
                "atr_14": [50000, 51000, 52000],
            }
        )

        atr_ratio = generator._calculate_atr_ratio(df)

        assert len(atr_ratio) == 3
        # ATR比率は正の値
        assert all(v > 0 for v in atr_ratio)
        # ATR比率は小さい値（1%程度）
        assert all(v < 0.02 for v in atr_ratio)
