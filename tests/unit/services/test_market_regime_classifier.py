"""
市場レジーム分類器のテスト - Phase 51.2-New

MarketRegimeClassifierの分類精度・計算ロジックをテスト。
"""

import pandas as pd
import pytest

from src.core.services.market_regime_classifier import MarketRegimeClassifier
from src.core.services.regime_types import RegimeType


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

    def test_classify_tight_range(self, classifier, base_df):
        """狭いレンジ相場を正しく検出することを確認"""
        # BB幅 < 0.03, 価格変動 < 0.02になるように設定
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.01 for i in range(50)]  # 微小な変動
        df["high"] = df["close"] + 0.5
        df["low"] = df["close"] - 0.5
        df["atr_14"] = [0.5] * 50  # 低ボラティリティ
        df["adx_14"] = [10.0] * 50  # 低ADX

        regime = classifier.classify(df)
        assert regime == RegimeType.TIGHT_RANGE

    def test_classify_normal_range(self, classifier, base_df):
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

    def test_classify_trending(self, classifier, base_df):
        """トレンド相場を正しく検出することを確認"""
        # ADX > 25, EMA傾き > 0.01になるように設定
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.5 for i in range(50)]  # 上昇トレンド
        df["high"] = df["close"] + 1.0
        df["low"] = df["close"] - 1.0
        df["atr_14"] = [2.0] * 50
        df["adx_14"] = [30.0] * 50  # ADX > 25
        df["ema_20"] = [100.0 + i * 0.5 for i in range(50)]  # EMA上昇

        regime = classifier.classify(df)
        assert regime == RegimeType.TRENDING

    def test_classify_high_volatility(self, classifier, base_df):
        """高ボラティリティを正しく検出することを確認"""
        # ATR比 > 0.03になるように設定
        df = base_df.copy()
        df["close"] = [100.0] * 50
        df["atr_14"] = [3.5] * 50  # ATR / close = 3.5 / 100 = 0.035 > 0.03

        regime = classifier.classify(df)
        assert regime == RegimeType.HIGH_VOLATILITY

    def test_classify_priority_high_volatility(self, classifier, base_df):
        """高ボラティリティが最優先で検出されることを確認"""
        # 複数条件を満たすがhigh_volatilityが優先
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.01 for i in range(50)]
        df["atr_14"] = [3.5] * 50  # 高ボラ条件満たす
        df["adx_14"] = [10.0] * 50  # レンジ条件も満たす

        regime = classifier.classify(df)
        assert regime == RegimeType.HIGH_VOLATILITY  # 高ボラが優先

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 境界値テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_boundary_tight_range_bb_width(self, classifier, base_df):
        """tight_range境界値テスト: BB幅が0.03より大きい場合"""
        df = base_df.copy()
        # BB幅が0.03より大きくなるように大きな変動を設定
        df["close"] = [100.0 + i * 2.0 for i in range(50)]  # 大きな変動
        df["atr_14"] = [0.5] * 50
        df["adx_14"] = [10.0] * 50

        regime = classifier.classify(df)
        # BB幅 >= 0.03なのでtight_rangeではない
        assert regime != RegimeType.TIGHT_RANGE

    def test_boundary_normal_range_adx(self, classifier, base_df):
        """normal_range境界値テスト: ADX = 19.9（ギリギリ範囲内）"""
        df = base_df.copy()
        df["close"] = [100.0 + (i % 10) * 0.3 for i in range(50)]
        df["atr_14"] = [1.0] * 50
        df["adx_14"] = [19.9] * 50  # ADX < 20（ギリギリ範囲内）

        regime = classifier.classify(df)
        # ADX < 20かつBB幅 < 0.05なのでnormal_range
        # ただし実際のBB幅次第でtight_rangeになる可能性もある
        assert regime in (RegimeType.NORMAL_RANGE, RegimeType.TIGHT_RANGE)

    def test_boundary_trending_adx(self, classifier, base_df):
        """trending境界値テスト: ADX = 25（境界）"""
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.5 for i in range(50)]
        df["atr_14"] = [2.0] * 50
        df["adx_14"] = [25.0] * 50  # ADX = 25（境界・ギリギリOK）
        df["ema_20"] = [100.0 + i * 0.5 for i in range(50)]

        # ADX > 25条件は「25.0は不含」だが、実装では「25以上」なので要確認
        # 実装コードを見ると adx > 25 なので 25.0は含まれない
        regime = classifier.classify(df)
        assert regime != RegimeType.TRENDING  # ADX=25はtrendingにならない

    def test_boundary_high_volatility_atr_ratio(self, classifier, base_df):
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

    def test_classify_missing_required_columns(self, classifier):
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

    def test_classify_empty_dataframe(self, classifier):
        """空のDataFrameでエラーハンドリングが動作することを確認"""
        df = pd.DataFrame()

        regime = classifier.classify(df)
        assert regime == RegimeType.NORMAL_RANGE  # デフォルト

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ユーティリティメソッドテスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_regime_stats(self, classifier, base_df):
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

    def test_is_tight_range(self, classifier):
        """_is_tight_range()判定ロジックが正しいことを確認"""
        assert classifier._is_tight_range(0.02, 0.01) is True  # 両方満たす
        assert classifier._is_tight_range(0.04, 0.01) is False  # BB幅が大きい
        assert classifier._is_tight_range(0.02, 0.03) is False  # 価格変動が大きい
        assert classifier._is_tight_range(0.04, 0.03) is False  # 両方満たさない

    def test_is_normal_range(self, classifier):
        """_is_normal_range()判定ロジックが正しいことを確認"""
        assert classifier._is_normal_range(0.04, 15.0) is True  # 両方満たす
        assert classifier._is_normal_range(0.06, 15.0) is False  # BB幅が大きい
        assert classifier._is_normal_range(0.04, 25.0) is False  # ADXが高い
        assert classifier._is_normal_range(0.06, 25.0) is False  # 両方満たさない

    def test_is_trending(self, classifier):
        """_is_trending()判定ロジックが正しいことを確認"""
        assert classifier._is_trending(30.0, 0.02) is True  # 両方満たす
        assert classifier._is_trending(20.0, 0.02) is False  # ADXが低い
        assert classifier._is_trending(30.0, 0.005) is False  # EMA傾きが小さい
        assert classifier._is_trending(20.0, 0.005) is False  # 両方満たさない

        # 下降トレンドもOK（abs(ema_slope) > 0.01）
        assert classifier._is_trending(30.0, -0.02) is True

    def test_is_high_volatility(self, classifier):
        """_is_high_volatility()判定ロジックが正しいことを確認"""
        assert classifier._is_high_volatility(0.02) is True  # 高ボラ
        assert classifier._is_high_volatility(0.01) is False  # 低ボラ
        assert classifier._is_high_volatility(0.018) is False  # 境界値（含まない）
        assert classifier._is_high_volatility(0.019) is True  # 境界値超え
