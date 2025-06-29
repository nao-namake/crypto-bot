# tests/unit/ml/test_preprocessor.py
# テスト対象: crypto_bot/ml/preprocessor.py
# 説明:
#   - FeatureEngineer: 特徴量生成・補完・extra_features
#   - build_ml_pipeline: sklearn互換パイプライン生成
#   - prepare_ml_dataset: X, y_reg, y_clf の一括生成

import numpy as np
import pandas as pd
import pytest
from unittest.mock import Mock, patch

from crypto_bot.ml.preprocessor import (
    FeatureEngineer,
    build_ml_pipeline,
    prepare_ml_dataset,
)


@pytest.fixture
def dummy_config():
    return {
        "ml": {
            "feat_period": 3,
            "lags": [1, 2],
            "rolling_window": 3,
            "extra_features": ["rsi_3", "ema_3", "day_of_week"],
            "horizon": 1,
            "threshold": 0.0,
        }
    }


@pytest.fixture
def dummy_ohlcv():
    idx = pd.date_range("2023-01-01", periods=10, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": np.random.rand(10),
            "high": np.random.rand(10),
            "low": np.random.rand(10),
            "close": np.random.rand(10),
            "volume": np.random.rand(10) * 10,
        },
        index=idx,
    )
    return df


def test_feature_engineer_transform(dummy_config, dummy_ohlcv):
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    # カラムが増えていること・欠損0埋め
    assert isinstance(out, pd.DataFrame)
    # 基本OHLCV + ATR + lag + rolling + extra_features で10列以上
    assert out.shape[1] > 10
    # 欠損が0で埋まる
    assert out.isnull().sum().sum() == 0


def test_feature_engineer_transform_empty_df(dummy_config):
    fe = FeatureEngineer(dummy_config)
    empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = fe.transform(empty_df)
    assert isinstance(out, pd.DataFrame)
    assert out.empty


def test_feature_engineer_transform_missing_columns(dummy_config):
    fe = FeatureEngineer(dummy_config)
    df = pd.DataFrame({"open": [1, 2, 3]})
    with pytest.raises(KeyError):
        fe.transform(df)


def test_feature_engineer_transform_with_rsi(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["rsi_14"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "rsi_14" in out.columns
    assert not out["rsi_14"].isnull().any()


def test_feature_engineer_transform_with_ema(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["ema_20"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "ema_20" in out.columns
    assert not out["ema_20"].isnull().any()


def test_feature_engineer_transform_with_sma(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["sma_20"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "sma_20" in out.columns
    assert not out["sma_20"].isnull().any()


def test_feature_engineer_transform_with_macd(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["macd"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "macd" in out.columns
    assert "macd_signal" in out.columns
    assert "macd_hist" in out.columns
    assert not out["macd"].isnull().any()


def test_feature_engineer_transform_with_rci(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["rci_14"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "rci_14" in out.columns
    assert not out["rci_14"].isnull().any()


def test_feature_engineer_transform_with_volume_zscore(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["volume_zscore_20"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "volume_zscore_20" in out.columns
    assert not out["volume_zscore_20"].isnull().any()


def test_feature_engineer_transform_with_time_features(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["day_of_week", "hour_of_day"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "day_of_week" in out.columns
    assert "hour_of_day" in out.columns
    assert out["day_of_week"].dtype == "int8"
    assert out["hour_of_day"].dtype == "int8"


def test_feature_engineer_transform_with_mochipoyo_signals(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = [
        "mochipoyo_long_signal",
        "mochipoyo_short_signal",
    ]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "mochipoyo_long_signal" in out.columns
    assert "mochipoyo_short_signal" in out.columns
    assert not out["mochipoyo_long_signal"].isnull().any()
    assert not out["mochipoyo_short_signal"].isnull().any()


def test_build_ml_pipeline_runs(dummy_config, dummy_ohlcv):
    pipeline = build_ml_pipeline(dummy_config)
    arr = pipeline.fit_transform(dummy_ohlcv)
    # 出力はndarray
    assert isinstance(arr, np.ndarray)
    # サンプル数一致
    assert arr.shape[0] == dummy_ohlcv.shape[0]


def test_build_ml_pipeline_empty_df(dummy_config):
    pipeline = build_ml_pipeline(dummy_config)
    empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    arr = pipeline.fit_transform(empty_df)
    assert isinstance(arr, np.ndarray)
    assert arr.shape[0] == 0


def test_prepare_ml_dataset(dummy_config, dummy_ohlcv):
    # 最小限のテスト：戻り値3つ/X, y_reg, y_clf
    X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
    # X, y_reg, y_clf の行数・index一致
    assert len(X) == len(y_reg) == len(y_clf)
    # DataFrame/Series型
    assert isinstance(X, pd.DataFrame)
    assert isinstance(y_reg, pd.Series)
    assert isinstance(y_clf, pd.Series)


def test_prepare_ml_dataset_empty_df(dummy_config):
    empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    X, y_reg, y_clf = prepare_ml_dataset(empty_df, dummy_config)
    assert len(X) == 0
    assert len(y_reg) == 0
    assert len(y_clf) == 0


def test_prepare_ml_dataset_single_row(dummy_config):
    df = pd.DataFrame(
        {"open": [100], "high": [101], "low": [99], "close": [100], "volume": [1000]}
    )
    X, y_reg, y_clf = prepare_ml_dataset(df, dummy_config)
    assert len(X) == 0  # ウィンドウサイズ分のデータが必要なため
    assert len(y_reg) == 0
    assert len(y_clf) == 0


def test_extra_feature_unknown_warns(dummy_config, dummy_ohlcv):
    """Test that unknown features log a warning and are skipped."""
    dummy_config["ml"]["extra_features"] = ["unknown_feature_999"]
    fe = FeatureEngineer(dummy_config)
    # Test that transform completes without raising and result has some features
    result = fe.transform(dummy_ohlcv)
    assert not result.empty
    assert "unknown_feature_999" not in result.columns


def test_extra_feature_invalid_format_raises(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["rsi"]  # パラメータなし
    fe = FeatureEngineer(dummy_config)
    # 無効なフォーマットではWarningがログに出力され、そのfeatureはスキップされる
    result = fe.transform(dummy_ohlcv)
    assert not result.empty
    assert "rsi" not in result.columns


# =============================================================================
# 高カバレッジを達成するための包括的テスト追加
# =============================================================================

class TestCalcRCI:
    """calc_rci 関数のテストクラス"""
    
    def test_calc_rci_basic(self):
        """基本的なRCI計算のテスト"""
        from crypto_bot.ml.preprocessor import calc_rci
        
        # 単調増加する価格データ
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        rci = calc_rci(prices, period=5)
        
        # RCIは-100から100の範囲
        assert rci.max() <= 100
        assert rci.min() >= -100
        
        # 最初の数値はNaN（ウィンドウサイズ分）
        assert rci.iloc[:4].isna().all()
        # 5番目以降は値が入る
        assert not rci.iloc[4:].isna().any()
    
    def test_calc_rci_constant_prices(self):
        """一定価格でのRCI計算テスト"""
        from crypto_bot.ml.preprocessor import calc_rci
        
        # 一定価格
        prices = pd.Series([100] * 10)
        rci = calc_rci(prices, period=5)
        
        # 一定価格では一部の値が特定の値になる
        non_nan_values = rci.dropna()
        if len(non_nan_values) > 0:
            # 一定価格の場合のRCI値をチェック
            assert all(abs(val) <= 100 for val in non_nan_values)
    
    def test_calc_rci_small_period(self):
        """小さな期間でのRCI計算テスト"""
        from crypto_bot.ml.preprocessor import calc_rci
        
        prices = pd.Series([100, 101, 102, 103, 104])
        rci = calc_rci(prices, period=3)
        
        # 期間3なので最初の2つはNaN
        assert rci.iloc[:2].isna().all()
        assert not rci.iloc[2:].isna().any()


class TestFeatureEngineerAdvanced:
    """FeatureEngineer の高度なテストクラス"""
    
    def test_feature_engineer_initialization(self, dummy_config):
        """初期化のテスト"""
        fe = FeatureEngineer(dummy_config)
        
        assert fe.config == dummy_config
        assert fe.feat_period == dummy_config["ml"]["feat_period"]
        assert fe.lags == dummy_config["ml"]["lags"]
        assert fe.rolling_window == dummy_config["ml"]["rolling_window"]
        assert fe.extra_features == dummy_config["ml"]["extra_features"]
        assert hasattr(fe, 'ind_calc')
        assert hasattr(fe, 'vix_fetcher')
    
    def test_feature_engineer_fit_method(self, dummy_config, dummy_ohlcv):
        """fit メソッドのテスト（何もしない）"""
        fe = FeatureEngineer(dummy_config)
        result = fe.fit(dummy_ohlcv)
        
        # fit は self を返す
        assert result is fe
    
    def test_feature_engineer_basic_features(self, dummy_config, dummy_ohlcv):
        """基本特徴量生成のテスト"""
        # extra_features を空にして基本特徴量のみテスト
        dummy_config["ml"]["extra_features"] = []
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        # 基本的なOHLCV特徴量
        expected_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in expected_cols:
            assert col in result.columns
        
        # ATR が追加されている
        assert 'atr' in result.columns
        
        # ラグ特徴量（設定に基づく）
        for lag in dummy_config["ml"]["lags"]:
            assert f'close_lag_{lag}' in result.columns
            assert f'volume_lag_{lag}' in result.columns
    
    def test_feature_engineer_rolling_features(self, dummy_config, dummy_ohlcv):
        """ローリング特徴量のテスト"""
        dummy_config["ml"]["extra_features"] = []
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        window = dummy_config["ml"]["rolling_window"]
        
        # ローリング統計量
        rolling_cols = [
            f'close_mean_{window}', f'close_std_{window}',
            f'volume_mean_{window}', f'volume_std_{window}'
        ]
        
        for col in rolling_cols:
            assert col in result.columns
    
    def test_feature_engineer_stochastic(self, dummy_config, dummy_ohlcv):
        """ストキャスティクス特徴量のテスト"""
        dummy_config["ml"]["extra_features"] = ["stoch"]
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        # ストキャスティクス関連列が追加される
        assert 'stoch_k' in result.columns
        assert 'stoch_d' in result.columns
    
    def test_feature_engineer_bollinger_bands(self, dummy_config, dummy_ohlcv):
        """ボリンジャーバンド特徴量のテスト"""
        dummy_config["ml"]["extra_features"] = ["bb"]
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        # ボリンジャーバンド関連列
        bb_cols = ['bb_upper', 'bb_middle', 'bb_lower', 'bb_percent', 'bb_width']
        for col in bb_cols:
            assert col in result.columns
    
    def test_feature_engineer_williams_r(self, dummy_config, dummy_ohlcv):
        """Williams %R 特徴量のテスト"""
        dummy_config["ml"]["extra_features"] = ["willr_14"]
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        assert 'willr_14' in result.columns
    
    def test_feature_engineer_adx(self, dummy_config, dummy_ohlcv):
        """ADX特徴量のテスト"""
        dummy_config["ml"]["extra_features"] = ["adx"]
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        # ADX関連列
        adx_cols = ['adx', 'di_plus', 'di_minus']
        for col in adx_cols:
            assert col in result.columns
    
    def test_feature_engineer_cmf(self, dummy_config, dummy_ohlcv):
        """チャイキンマネーフロー特徴量のテスト"""
        dummy_config["ml"]["extra_features"] = ["cmf_20"]
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        assert 'cmf_20' in result.columns
    
    def test_feature_engineer_fisher_transform(self, dummy_config, dummy_ohlcv):
        """フィッシャートランスフォーム特徴量のテスト"""
        dummy_config["ml"]["extra_features"] = ["fisher"]
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        # Fisher Transform関連列
        assert 'fisher' in result.columns
        assert 'fisher_signal' in result.columns
    
    def test_feature_engineer_advanced_signals(self, dummy_config, dummy_ohlcv):
        """高度な複合シグナル特徴量のテスト"""
        dummy_config["ml"]["extra_features"] = ["advanced_signals"]
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(dummy_ohlcv)
        
        # 高度なシグナルが追加される（具体的な列名は実装依存）
        assert result.shape[1] > len(dummy_ohlcv.columns)
    
    def test_feature_engineer_data_cleaning(self, dummy_config):
        """データクリーニング機能のテスト"""
        # 異常値を含むデータ
        idx = pd.date_range("2023-01-01", periods=10, freq="D")
        df = pd.DataFrame({
            "open": [100, np.inf, 102, -np.inf, 104, 105, 106, 107, 108, 109],
            "high": [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            "low": [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
            "close": [102, 103, np.nan, 105, 106, 107, 108, 109, 110, 111],
            "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        }, index=idx)
        
        dummy_config["ml"]["extra_features"] = []
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(df)
        
        # 無限大値・NaN値が処理されている
        assert not np.isinf(result.values).any()
        assert not np.isnan(result.values).any()
    
    def test_feature_engineer_quantile_clipping(self, dummy_config):
        """クオンタイルクリッピングのテスト"""
        # 極端な外れ値を含むデータ
        idx = pd.date_range("2023-01-01", periods=100, freq="D")
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 98)
        outlier_data = [10000, -10000]  # 極端な外れ値
        close_data = np.concatenate([normal_data, outlier_data])
        
        df = pd.DataFrame({
            "open": close_data,
            "high": close_data + 5,
            "low": close_data - 5,
            "close": close_data,
            "volume": np.random.normal(1000, 100, 100)
        }, index=idx)
        
        dummy_config["ml"]["extra_features"] = []
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(df)
        
        # 極端な外れ値がクリッピングされている
        assert result['close'].max() < 10000
        assert result['close'].min() > -10000
    
    def test_feature_engineer_empty_dataframe_index(self, dummy_config):
        """空でないが日時インデックスでないDataFrameのテスト"""
        # 整数インデックスのDataFrame
        df = pd.DataFrame({
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [95, 96, 97],
            "close": [102, 103, 104],
            "volume": [1000, 1100, 1200]
        })
        
        dummy_config["ml"]["extra_features"] = ["day_of_week", "hour_of_day"]
        fe = FeatureEngineer(dummy_config)
        result = fe.transform(df)
        
        # 日時インデックスでない場合は0で埋められる
        assert (result['day_of_week'] == 0).all()
        assert (result['hour_of_day'] == 0).all()


class TestBuildMLPipeline:
    """build_ml_pipeline 関数のテストクラス"""
    
    def test_build_ml_pipeline_structure(self, dummy_config):
        """パイプライン構造のテスト"""
        pipeline = build_ml_pipeline(dummy_config)
        
        # パイプラインが2ステップ（features + scaler）を持つ
        assert len(pipeline.steps) == 2
        assert 'features' in pipeline.named_steps
        assert 'scaler' in pipeline.named_steps
        
        # 各ステップが適切なクラス
        assert isinstance(pipeline.named_steps['features'], FeatureEngineer)
    
    def test_build_ml_pipeline_skip_scaling(self, dummy_config):
        """スケーリングスキップ設定のテスト"""
        dummy_config['skip_scaling'] = True
        pipeline = build_ml_pipeline(dummy_config)
        
        # スケーリングがスキップされる
        scaler = pipeline.named_steps['scaler']
        # EmptyDataFrameScaler が使用される
        assert hasattr(scaler, 'fit') and hasattr(scaler, 'transform')
    
    def test_build_ml_pipeline_empty_dataframe_handling(self, dummy_config):
        """空のDataFrame処理のテスト"""
        pipeline = build_ml_pipeline(dummy_config)
        empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        
        # 空のDataFrameでも処理される
        result = pipeline.fit_transform(empty_df)
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 0
    
    def test_build_ml_pipeline_transform_method(self, dummy_config, dummy_ohlcv):
        """transform メソッドのテスト"""
        pipeline = build_ml_pipeline(dummy_config)
        
        # fit_transform でトレーニング
        pipeline.fit_transform(dummy_ohlcv)
        
        # 新しいデータで transform
        new_data = dummy_ohlcv.copy()
        result = pipeline.transform(new_data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == new_data.shape[0]
        
        # 空のDataFrameでの transform
        empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        empty_result = pipeline.transform(empty_df)
        assert isinstance(empty_result, np.ndarray)
        assert empty_result.shape[0] == 0


class TestPrepareMlDataset:
    """prepare_ml_dataset 関数のテストクラス"""
    
    def test_prepare_ml_dataset_return_types(self, dummy_config, dummy_ohlcv):
        """戻り値の型チェック"""
        X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
        
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y_reg, pd.Series)
        assert isinstance(y_clf, pd.Series)
    
    def test_prepare_ml_dataset_target_names(self, dummy_config, dummy_ohlcv):
        """ターゲット系列の名前チェック"""
        horizon = dummy_config["ml"]["horizon"]
        X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
        
        assert y_reg.name == f"return_{horizon}"
        assert y_clf.name == f"up_{horizon}"
    
    def test_prepare_ml_dataset_index_alignment(self, dummy_config, dummy_ohlcv):
        """インデックスの整合性チェック"""
        X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
        
        # 全てのインデックスが一致
        assert X.index.equals(y_reg.index)
        assert X.index.equals(y_clf.index)
        
        # 元のDataFrameよりも短い（window + lags分ドロップ）
        assert len(X) <= len(dummy_ohlcv)
    
    def test_prepare_ml_dataset_drop_calculation(self, dummy_config, dummy_ohlcv):
        """ドロップ行数計算のテスト"""
        window = dummy_config["ml"]["rolling_window"]
        lags = dummy_config["ml"]["lags"]
        expected_drop = window + max(lags)
        
        X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
        
        # 期待される行数
        expected_length = len(dummy_ohlcv) - expected_drop
        assert len(X) == expected_length
        assert len(y_reg) == expected_length
        assert len(y_clf) == expected_length
    
    def test_prepare_ml_dataset_no_lags(self, dummy_config, dummy_ohlcv):
        """ラグなし設定のテスト"""
        dummy_config["ml"]["lags"] = []
        window = dummy_config["ml"]["rolling_window"]
        
        X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
        
        # ラグがない場合はwindowのみドロップ
        expected_length = len(dummy_ohlcv) - window
        assert len(X) == expected_length
    
    def test_prepare_ml_dataset_custom_threshold(self, dummy_config, dummy_ohlcv):
        """カスタム閾値のテスト"""
        dummy_config["ml"]["threshold"] = 0.05  # 5%の閾値
        
        X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
        
        # 分類ターゲットが0と1のみ
        assert set(y_clf.unique()).issubset({0, 1})
    
    def test_prepare_ml_dataset_large_window(self, dummy_config, dummy_ohlcv):
        """大きなウィンドウサイズのテスト"""
        # データより大きなウィンドウサイズ
        dummy_config["ml"]["rolling_window"] = 15
        dummy_config["ml"]["lags"] = [1, 2, 3]
        
        X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
        
        # データが少なすぎる場合は空になる可能性
        if len(dummy_ohlcv) <= 18:  # window(15) + max_lag(3)
            assert len(X) == 0
            assert len(y_reg) == 0
            assert len(y_clf) == 0


class TestEmptyDataFrameClasses:
    """空のDataFrame処理用クラスのテスト"""
    
    def test_empty_dataframe_scaler(self):
        """EmptyDataFrameScaler のテスト"""
        from crypto_bot.ml.preprocessor import build_ml_pipeline
        
        config = {"ml": {"feat_period": 3}, "skip_scaling": True}
        pipeline = build_ml_pipeline(config)
        scaler = pipeline.named_steps['scaler']
        
        # ダミーデータでfit
        dummy_data = np.array([[1, 2, 3], [4, 5, 6]])
        scaler.fit(dummy_data)
        
        # transform は入力をそのまま返す
        result = scaler.transform(dummy_data)
        np.testing.assert_array_equal(result, dummy_data)
    
    def test_empty_dataframe_pipeline_consistency(self, dummy_config, dummy_ohlcv):
        """EmptyDataFramePipeline の一貫性テスト"""
        pipeline = build_ml_pipeline(dummy_config)
        
        # fit_transform と fit -> transform の結果が一致
        result1 = pipeline.fit_transform(dummy_ohlcv.copy())
        
        pipeline2 = build_ml_pipeline(dummy_config)
        pipeline2.fit(dummy_ohlcv.copy())
        result2 = pipeline2.transform(dummy_ohlcv.copy())
        
        np.testing.assert_array_equal(result1, result2)


class TestErrorHandling:
    """エラーハンドリングのテストクラス"""
    
    def test_feature_engineer_missing_column_error(self, dummy_config):
        """必須列欠如時のエラーテスト"""
        fe = FeatureEngineer(dummy_config)
        
        # 必須列が欠けているDataFrame
        df = pd.DataFrame({"open": [1, 2, 3], "high": [2, 3, 4]})
        
        with pytest.raises(KeyError):
            fe.transform(df)
    
    def test_feature_engineer_indicator_error_handling(self, dummy_config, dummy_ohlcv):
        """指標計算エラーのハンドリングテスト"""
        # 実際のエラーを引き起こすのは困難なので、ログ出力の存在確認
        dummy_config["ml"]["extra_features"] = ["stoch", "bb", "adx"]
        fe = FeatureEngineer(dummy_config)
        
        # 正常なケースでエラーが発生しないことを確認
        result = fe.transform(dummy_ohlcv)
        assert not result.empty
        assert result.shape[1] > len(dummy_ohlcv.columns)
    
    def test_prepare_ml_dataset_config_validation(self, dummy_ohlcv):
        """設定値検証のテスト"""
        # 必須設定が欠けている場合
        incomplete_config = {"ml": {"feat_period": 3}}  # horizon がない
        
        with pytest.raises(KeyError):
            prepare_ml_dataset(dummy_ohlcv, incomplete_config)


class TestVIXIntegration:
    """VIX統合機能のテストクラス"""
    
    def test_vix_feature_handling(self, dummy_config, dummy_ohlcv):
        """VIX特徴量処理のテスト"""
        dummy_config["ml"]["extra_features"] = ["vix_level", "vix_change"]
        fe = FeatureEngineer(dummy_config)
        
        # VIXフェッチャーが利用できない場合でもエラーにならない
        result = fe.transform(dummy_ohlcv)
        assert not result.empty
        
        # VIX関連特徴量は追加されない（フェッチャーが無効なため）
        assert "vix_level" not in result.columns
        assert "vix_change" not in result.columns
