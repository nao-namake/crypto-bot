"""
市場レジーム分類器のテスト - Phase 61.1

MarketRegimeClassifierの分類精度・計算ロジックをテスト。
Phase 61.1: thresholds.yamlから閾値を読み込む方式に対応。
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.core.services.market_regime_classifier import MarketRegimeClassifier
from src.core.services.regime_types import RegimeType

# Phase 61.1: 新しい閾値（設定ファイルと同じ値）
TIGHT_RANGE_BB_THRESHOLD = 0.025
TIGHT_RANGE_PRICE_THRESHOLD = 0.015
TRENDING_ADX_THRESHOLD = 20
TRENDING_EMA_THRESHOLD = 0.007
NORMAL_RANGE_BB_THRESHOLD = 0.05
NORMAL_RANGE_ADX_THRESHOLD = 20
HIGH_VOLATILITY_ATR_THRESHOLD = 0.018


def mock_get_threshold(key, default=None):
    """テスト用のget_thresholdモック"""
    thresholds = {
        "market_regime.tight_range.bb_width_threshold": TIGHT_RANGE_BB_THRESHOLD,
        "market_regime.tight_range.price_range_threshold": TIGHT_RANGE_PRICE_THRESHOLD,
        "market_regime.trending.adx_threshold": TRENDING_ADX_THRESHOLD,
        "market_regime.trending.ema_slope_threshold": TRENDING_EMA_THRESHOLD,
        "market_regime.normal_range.bb_width_threshold": NORMAL_RANGE_BB_THRESHOLD,
        "market_regime.normal_range.adx_threshold": NORMAL_RANGE_ADX_THRESHOLD,
        "market_regime.high_volatility.atr_ratio_threshold": HIGH_VOLATILITY_ATR_THRESHOLD,
    }
    return thresholds.get(key, default)


class TestMarketRegimeClassifier:
    """MarketRegimeClassifierのテストクラス"""

    @pytest.fixture
    def classifier(self):
        """分類器インスタンスを返すfixture"""
        return MarketRegimeClassifier()

    @pytest.fixture
    def base_df(self):
        """基本的な市場データDataFrameを返すfixture"""
        return pd.DataFrame(
            {
                "close": [100.0] * 50,
                "high": [102.0] * 50,
                "low": [98.0] * 50,
                "volume": [1000.0] * 50,
                "atr_14": [1.5] * 50,
                "adx_14": [15.0] * 50,
                "ema_20": [100.0] * 50,
                "ema_50": [100.0] * 50,
                "donchian_high_20": [102.0] * 50,
                "donchian_low_20": [98.0] * 50,
            }
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 分類テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_classify_tight_range(self, mock_threshold, classifier, base_df):
        """狭いレンジ相場を正しく検出することを確認"""
        # BB幅 < 0.025, 価格変動 < 0.015になるように設定
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.005 for i in range(50)]  # 微小な変動
        df["high"] = df["close"] + 0.3
        df["low"] = df["close"] - 0.3
        df["atr_14"] = [0.5] * 50  # 低ボラティリティ
        df["adx_14"] = [10.0] * 50  # 低ADX

        regime = classifier.classify(df)
        assert regime == RegimeType.TIGHT_RANGE

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_classify_normal_range(self, mock_threshold, classifier, base_df):
        """通常レンジ相場を正しく検出することを確認"""
        # BB幅 < 0.05, ADX < 20になるように設定
        df = base_df.copy()
        df["close"] = [100.0 + (i % 10) * 0.5 for i in range(50)]  # レンジ変動
        df["high"] = df["close"] + 1.0
        df["low"] = df["close"] - 1.0
        df["atr_14"] = [1.0] * 50
        df["adx_14"] = [15.0] * 50  # ADX < 20

        regime = classifier.classify(df)
        assert regime == RegimeType.NORMAL_RANGE

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_classify_trending(self, mock_threshold, classifier, base_df):
        """トレンド相場を正しく検出することを確認"""
        # ADX > 20, EMA傾き > 0.007になるように設定
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.5 for i in range(50)]  # 上昇トレンド
        df["high"] = df["close"] + 1.0
        df["low"] = df["close"] - 1.0
        df["atr_14"] = [1.5] * 50
        df["adx_14"] = [25.0] * 50  # ADX > 20
        df["ema_20"] = [100.0 + i * 0.5 for i in range(50)]  # EMA上昇

        regime = classifier.classify(df)
        assert regime == RegimeType.TRENDING

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_classify_high_volatility(self, mock_threshold, classifier, base_df):
        """高ボラティリティを正しく検出することを確認"""
        # ATR比 > 0.018になるように設定
        df = base_df.copy()
        df["close"] = [100.0] * 50
        df["atr_14"] = [2.5] * 50  # ATR / close = 2.5 / 100 = 0.025 > 0.018

        regime = classifier.classify(df)
        assert regime == RegimeType.HIGH_VOLATILITY

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_classify_priority_high_volatility(self, mock_threshold, classifier, base_df):
        """高ボラティリティが最優先で検出されることを確認"""
        # 複数条件を満たすがhigh_volatilityが優先
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.005 for i in range(50)]
        df["atr_14"] = [2.5] * 50  # 高ボラ条件満たす
        df["adx_14"] = [10.0] * 50  # レンジ条件も満たす

        regime = classifier.classify(df)
        assert regime == RegimeType.HIGH_VOLATILITY  # 高ボラが優先

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 境界値テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_boundary_tight_range_bb_width(self, mock_threshold, classifier, base_df):
        """tight_range境界値テスト: BB幅が0.025より大きい場合"""
        df = base_df.copy()
        # BB幅が0.025より大きくなるように大きな変動を設定
        df["close"] = [100.0 + i * 2.0 for i in range(50)]  # 大きな変動
        df["atr_14"] = [0.5] * 50
        df["adx_14"] = [10.0] * 50

        regime = classifier.classify(df)
        # BB幅 >= 0.025なのでtight_rangeではない
        assert regime != RegimeType.TIGHT_RANGE

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_boundary_normal_range_adx(self, mock_threshold, classifier, base_df):
        """normal_range境界値テスト: ADX = 19.9（ギリギリ範囲内）"""
        df = base_df.copy()
        df["close"] = [100.0 + (i % 10) * 0.3 for i in range(50)]
        df["atr_14"] = [1.0] * 50
        df["adx_14"] = [19.9] * 50  # ADX < 20（ギリギリ範囲内）

        regime = classifier.classify(df)
        # ADX < 20かつBB幅 < 0.05なのでnormal_range
        # ただし実際のBB幅次第でtight_rangeになる可能性もある
        assert regime in (RegimeType.NORMAL_RANGE, RegimeType.TIGHT_RANGE)

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_boundary_trending_adx(self, mock_threshold, classifier, base_df):
        """trending境界値テスト: ADX = 20（境界）"""
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.5 for i in range(50)]
        df["atr_14"] = [1.5] * 50
        df["adx_14"] = [20.0] * 50  # ADX = 20（境界・ギリギリOK）
        df["ema_20"] = [100.0 + i * 0.5 for i in range(50)]

        # adx > 20条件は「20.0は不含」なのでtrendingにならない
        regime = classifier.classify(df)
        assert regime != RegimeType.TRENDING  # ADX=20はtrendingにならない

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_boundary_high_volatility_atr_ratio(self, mock_threshold, classifier, base_df):
        """high_volatility境界値テスト: ATR比 = 0.017（境界以下）"""
        df = base_df.copy()
        df["close"] = [100.0] * 50
        df["atr_14"] = [1.7] * 50  # ATR / close = 1.7 / 100 = 0.017（境界以下）

        regime = classifier.classify(df)
        # ATR比 = 0.017 < 0.018なので high_volatility ではない
        assert regime != RegimeType.HIGH_VOLATILITY

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 計算メソッドテスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_calc_bb_width(self, classifier, base_df):
        """BB幅計算が正しいことを確認"""
        df = base_df.copy()
        df["close"] = [100.0] * 50

        bb_width = classifier._calc_bb_width(df)
        assert isinstance(bb_width, float)
        assert bb_width >= 0.0

    def test_calc_donchian_width(self, classifier, base_df):
        """Donchian幅計算が正しいことを確認"""
        df = base_df.copy()

        donchian_width = classifier._calc_donchian_width(df)
        assert isinstance(donchian_width, float)
        assert donchian_width >= 0.0

    def test_calc_price_range(self, classifier, base_df):
        """価格変動率計算が正しいことを確認"""
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.5 for i in range(50)]

        price_range = classifier._calc_price_range(df, lookback=20)
        assert isinstance(price_range, float)
        assert price_range >= 0.0

    def test_calc_ema_slope(self, classifier, base_df):
        """EMA傾き計算が正しいことを確認"""
        df = base_df.copy()
        df["ema_20"] = [100.0 + i * 0.2 for i in range(50)]  # 上昇EMA

        ema_slope = classifier._calc_ema_slope(df, period=20, lookback=5)
        assert isinstance(ema_slope, float)
        assert ema_slope > 0.0  # 上昇トレンドなので正の傾き

    def test_calc_ema_slope_without_ema_column(self, classifier, base_df):
        """EMAカラムがない場合でもEMA傾き計算が動作することを確認"""
        df = base_df.copy()
        df = df.drop(columns=["ema_20", "ema_50"])  # EMAカラムを削除
        df["close"] = [100.0 + i * 0.2 for i in range(50)]

        ema_slope = classifier._calc_ema_slope(df, period=20, lookback=5)
        assert isinstance(ema_slope, float)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # エラーハンドリングテスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_classify_missing_required_columns(self, mock_threshold, classifier):
        """必須カラムが不足している場合にValueErrorが発生することを確認"""
        df = pd.DataFrame(
            {
                "close": [100.0] * 50,
                # atr_14, adx_14が不足
            }
        )

        # ValueErrorが発生するが、エラーハンドリングでNORMAL_RANGEが返却される
        regime = classifier.classify(df)
        assert regime == RegimeType.NORMAL_RANGE  # デフォルト

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_classify_empty_dataframe(self, mock_threshold, classifier):
        """空のDataFrameでエラーハンドリングが動作することを確認"""
        df = pd.DataFrame()

        regime = classifier.classify(df)
        assert regime == RegimeType.NORMAL_RANGE  # デフォルト

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ユーティリティメソッドテスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_get_regime_stats(self, mock_threshold, classifier, base_df):
        """get_regime_stats()が詳細統計を返すことを確認"""
        df = base_df.copy()

        stats = classifier.get_regime_stats(df)

        assert "regime" in stats
        assert "bb_width" in stats
        assert "donchian_width" in stats
        assert "price_range" in stats
        assert "adx" in stats
        assert "ema_slope" in stats
        assert "atr_ratio" in stats

        assert isinstance(stats["regime"], RegimeType)
        assert isinstance(stats["bb_width"], float)
        assert isinstance(stats["adx"], float)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 判定メソッドテスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_is_tight_range(self, mock_threshold, classifier):
        """_is_tight_range()判定ロジックが正しいことを確認"""
        # 閾値: bb_width < 0.025, price_range < 0.015
        assert classifier._is_tight_range(0.02, 0.01) is True  # 両方満たす
        assert classifier._is_tight_range(0.03, 0.01) is False  # BB幅が大きい
        assert classifier._is_tight_range(0.02, 0.02) is False  # 価格変動が大きい
        assert classifier._is_tight_range(0.03, 0.02) is False  # 両方満たさない

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_is_normal_range(self, mock_threshold, classifier):
        """_is_normal_range()判定ロジックが正しいことを確認"""
        # 閾値: bb_width < 0.05, adx < 20
        assert classifier._is_normal_range(0.04, 15.0) is True  # 両方満たす
        assert classifier._is_normal_range(0.06, 15.0) is False  # BB幅が大きい
        assert classifier._is_normal_range(0.04, 25.0) is False  # ADXが高い
        assert classifier._is_normal_range(0.06, 25.0) is False  # 両方満たさない

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_is_trending(self, mock_threshold, classifier):
        """_is_trending()判定ロジックが正しいことを確認"""
        # 閾値: adx > 20, abs(ema_slope) > 0.007
        assert classifier._is_trending(25.0, 0.015) is True  # 両方満たす
        assert classifier._is_trending(15.0, 0.015) is False  # ADXが低い
        assert classifier._is_trending(25.0, 0.005) is False  # EMA傾きが小さい
        assert classifier._is_trending(15.0, 0.005) is False  # 両方満たさない

        # 下降トレンドもOK（abs(ema_slope) > 0.007）
        assert classifier._is_trending(25.0, -0.015) is True

    @patch(
        "src.core.services.market_regime_classifier.get_threshold", side_effect=mock_get_threshold
    )
    def test_is_high_volatility(self, mock_threshold, classifier):
        """_is_high_volatility()判定ロジックが正しいことを確認"""
        # 閾値: atr_ratio > 0.018
        assert classifier._is_high_volatility(0.02) is True  # 高ボラ
        assert classifier._is_high_volatility(0.01) is False  # 低ボラ
        assert classifier._is_high_volatility(0.018) is False  # 境界値（含まない）
        assert classifier._is_high_volatility(0.019) is True  # 境界値超え
