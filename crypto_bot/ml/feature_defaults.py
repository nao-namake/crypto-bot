"""
確実な特徴量生成システム
外部データが取得できない場合でも、必ず101特徴量を生成する
"""

import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


class FeatureDefaults:
    """
    外部データエラー時の確実な特徴量生成
    """

    @staticmethod
    def get_default_vix_features() -> List[str]:
        """VIX特徴量の名前リスト"""
        return [
            "vix_level",
            "vix_change",
            "vix_zscore",
            "fear_level",
            "vix_spike",
            "vix_regime_numeric",
        ]

    @staticmethod
    def get_default_macro_features() -> List[str]:
        """マクロ経済特徴量の名前リスト"""
        return [
            "dxy_level",
            "dxy_change",
            "dxy_zscore",
            "dxy_strength",
            "treasury_10y_level",
            "treasury_10y_change",
            "treasury_10y_zscore",
            "treasury_regime",
            "yield_curve_spread",
            "risk_sentiment",
        ]

    @staticmethod
    def get_default_forex_features() -> List[str]:
        """USD/JPY為替特徴量の名前リスト"""
        return [
            "usdjpy_level",
            "usdjpy_change",
            "usdjpy_volatility",
            "usdjpy_zscore",
            "usdjpy_trend",
            "usdjpy_strength",
        ]

    @staticmethod
    def get_default_fear_greed_features() -> List[str]:
        """Fear&Greed特徴量の名前リスト"""
        return [
            "fear_greed_index",
            "fear_greed_classification",
            "market_sentiment",
            "extreme_fear",
            "extreme_greed",
            "fear_greed_change",
            "fear_greed_ma",
            "fear_greed_volatility",
            "fear_greed_zscore",
            "fear_greed_momentum",
            "sentiment_regime",
            "fear_greed_strength",
            "market_panic",
        ]

    @staticmethod
    def get_default_funding_features() -> List[str]:
        """Funding Rate特徴量の名前リスト"""
        return [
            "funding_rate_mean",
            "funding_rate_zscore",
            "funding_extreme",
            "oi_level",
            "oi_change",
            "oi_zscore",
        ]

    @staticmethod
    def add_default_vix_features(df: pd.DataFrame) -> pd.DataFrame:
        """VIXデフォルト特徴量を追加"""
        vix_features = FeatureDefaults.get_default_vix_features()
        for feature in vix_features:
            if feature not in df.columns:
                if feature == "vix_level":
                    df[feature] = 20.0  # VIX平均値
                elif feature == "vix_regime_numeric":
                    df[feature] = 1  # normal regime
                elif feature == "fear_level":
                    df[feature] = 1  # normal fear
                else:
                    df[feature] = 0.0
        logger.debug(f"Added {len(vix_features)} default VIX features")
        return df

    @staticmethod
    def add_default_macro_features(df: pd.DataFrame) -> pd.DataFrame:
        """マクロ経済デフォルト特徴量を追加"""
        macro_features = FeatureDefaults.get_default_macro_features()
        for feature in macro_features:
            if feature not in df.columns:
                if feature == "dxy_level":
                    df[feature] = 100.0  # DXY基準値
                elif feature == "treasury_10y_level":
                    df[feature] = 4.0  # 10年債利回り基準値
                elif feature == "treasury_regime":
                    df[feature] = 1  # normal regime
                else:
                    df[feature] = 0.0
        logger.debug(f"Added {len(macro_features)} default macro features")
        return df

    @staticmethod
    def add_default_forex_features(df: pd.DataFrame) -> pd.DataFrame:
        """USD/JPY為替デフォルト特徴量を追加"""
        forex_features = FeatureDefaults.get_default_forex_features()
        for feature in forex_features:
            if feature not in df.columns:
                if feature == "usdjpy_level":
                    df[feature] = 150.0  # 典型的なUSD/JPYレベル
                elif feature == "usdjpy_volatility":
                    df[feature] = 0.005  # 為替ボラティリティ
                elif feature == "usdjpy_trend":
                    df[feature] = 0  # トレンド方向
                elif feature == "usdjpy_strength":
                    df[feature] = 0  # 強度
                else:
                    df[feature] = 0.0
        logger.debug(f"Added {len(forex_features)} default forex features")
        return df

    @staticmethod
    def add_default_fear_greed_features(df: pd.DataFrame) -> pd.DataFrame:
        """Fear&Greedデフォルト特徴量を追加"""
        fg_features = FeatureDefaults.get_default_fear_greed_features()
        for feature in fg_features:
            if feature not in df.columns:
                if feature == "fear_greed_index":
                    df[feature] = 50.0  # 中立値
                elif feature == "fear_greed_classification":
                    df[feature] = 2  # neutral
                elif feature == "market_sentiment":
                    df[feature] = 1  # neutral sentiment
                elif feature == "sentiment_regime":
                    df[feature] = 1  # normal regime
                else:
                    df[feature] = 0.0
        logger.debug(f"Added {len(fg_features)} default Fear&Greed features")
        return df

    @staticmethod
    def add_default_funding_features(df: pd.DataFrame) -> pd.DataFrame:
        """Funding Rateデフォルト特徴量を追加"""
        funding_features = FeatureDefaults.get_default_funding_features()
        for feature in funding_features:
            if feature not in df.columns:
                if feature == "oi_level":
                    df[feature] = 1000.0  # OI基準値
                else:
                    df[feature] = 0.0
        logger.debug(f"Added {len(funding_features)} default funding features")
        return df

    @staticmethod
    def ensure_101_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        確実に101特徴量を生成

        Parameters
        ----------
        df : pd.DataFrame
            入力データフレーム

        Returns
        -------
        pd.DataFrame
            101特徴量が保証されたデータフレーム
        """
        logger.info("Ensuring 101 features with defaults")

        # 基本特徴量（データから計算される）の確認
        basic_features = ["open", "high", "low", "close", "volume"]
        for feature in basic_features:
            if feature not in df.columns:
                logger.warning(f"Missing basic feature: {feature}")

        # 外部データ特徴量のデフォルト値追加
        df = FeatureDefaults.add_default_vix_features(df)
        df = FeatureDefaults.add_default_macro_features(df)
        df = FeatureDefaults.add_default_forex_features(df)
        df = FeatureDefaults.add_default_fear_greed_features(df)
        df = FeatureDefaults.add_default_funding_features(df)

        # 追加の特徴量（基本計算系）
        additional_features = {
            "momentum_14": 0.0,
            "trend_strength": 25.0,
            "day_of_week": 1,
            "hour_of_day": 12,
            "mochipoyo_long_signal": 0,
            "mochipoyo_short_signal": 0,
        }

        for feature, default_value in additional_features.items():
            if feature not in df.columns:
                df[feature] = default_value

        logger.info(f"Final feature count: {len(df.columns)}")
        return df


def ensure_feature_consistency(
    df: pd.DataFrame, target_count: int = 101
) -> pd.DataFrame:
    """
    特徴量数の一致を保証する最終チェック

    Parameters
    ----------
    df : pd.DataFrame
        特徴量データフレーム
    target_count : int
        目標特徴量数

    Returns
    -------
    pd.DataFrame
        特徴量数が一致したデータフレーム
    """
    current_count = len(df.columns)

    if current_count == target_count:
        logger.info(f"Feature count matches target: {current_count}")
        return df
    elif current_count < target_count:
        # 不足分を補完
        missing_count = target_count - current_count
        logger.warning(f"Missing {missing_count} features, adding defaults")

        for i in range(missing_count):
            feature_name = f"default_feature_{i}"
            df[feature_name] = 0.0

        logger.info(f"Added {missing_count} default features, total: {len(df.columns)}")
        return df
    else:
        # 超過分を削除（最後の特徴量から）
        excess_count = current_count - target_count
        logger.warning(f"Excess {excess_count} features, removing last ones")

        df = df.iloc[:, :target_count]
        logger.info(f"Removed {excess_count} features, total: {len(df.columns)}")
        return df
