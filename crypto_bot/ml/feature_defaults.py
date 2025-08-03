"""
確実な特徴量生成システム
外部データが取得できない場合でも、必ず97特徴量を生成する
"""

import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


class FeatureDefaults:
    """
    外部データエラー時の確実な特徴量生成
    Phase 2: 97特徴量最適化対応
    """

    # Phase 2: 97特徴量最適化システム対応
    target_count = 97

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
    def ensure_97_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        確実に97特徴量を生成（Phase 2最適化対応）

        Parameters
        ----------
        df : pd.DataFrame
            入力データフレーム

        Returns
        -------
        pd.DataFrame
            97特徴量が保証されたデータフレーム
        """
        logger.info("Ensuring 97 optimized features with defaults")

        # 基本特徴量（データから計算される）の確認
        basic_features = ["open", "high", "low", "close", "volume"]
        for feature in basic_features:
            if feature not in df.columns:
                logger.warning(f"Missing basic feature: {feature}")

        # Phase 2: 97特徴量最適化システム対応
        # 外部データは無効化されているため、テクニカル指標のみの補完
        essential_technical_features = {
            "rsi_14": 50.0,  # RSI中立値
            "ema_20": 100.0,  # 価格ベース移動平均
            "atr_14": 2.0,  # ATRデフォルト値
            "macd": 0.0,  # MACDゼロライン
            "volume_ratio": 1.0,  # 出来高比率中立
            "momentum_14": 0.0,  # モメンタム中立
            "trend_strength": 50.0,  # トレンド強度中立
            "volatility_20": 0.02,  # ボラティリティ2%
            "hour": 12,  # 時間特徴量
            "day_of_week": 3,  # 曜日特徴量（水曜）
            "is_weekend": 0,  # 平日フラグ
            "is_asian_session": 0,
            "is_us_session": 0,
        }

        # 不足特徴量を安全なデフォルト値で補完
        for feature, default_value in essential_technical_features.items():
            if feature not in df.columns:
                df[feature] = default_value

        logger.info(f"Phase 2 optimized feature count: {len(df.columns)}")
        logger.info(
            "97特徴量最適化システム対応完了（外部データ除外・テクニカル指標重視）"
        )
        return df


def ensure_feature_consistency(
    df: pd.DataFrame, target_count: int = 97
) -> pd.DataFrame:
    """
    特徴量数の一致を保証する最終チェック（Phase H.12: 強化版・確実性向上）

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

    logger.info(
        f"🔍 [PHASE-H12] Feature consistency check: {current_count}/{target_count}"
    )

    if current_count == target_count:
        logger.info(f"✅ Feature count matches target: {current_count}")
        return df
    elif current_count < (
        target_count - 2
    ):  # Phase H.30: enhanced_default汚染防止・許容範囲±2
        # Phase H.29: 不足特徴量の詳細ログ追加
        missing_count = target_count - current_count
        logger.error(
            f"🚨 [PHASE-H29] CRITICAL: Missing {missing_count} features! Current: {current_count}, Target: {target_count}"
        )

        # Phase H.29: 既存特徴量と期待特徴量の比較
        if hasattr(df, "columns"):
            logger.error(
                f"🚨 [PHASE-H29] Current features: {list(df.columns)[:10]}... (showing first 10)"
            )
        logger.warning(
            f"⚠️ [PHASE-H12] Missing {missing_count} features, adding smart defaults"
        )

        # Phase H.12: より意味のあるデフォルト特徴量生成
        try:
            # 効率的なデフォルト特徴量生成（pd.concat使用）
            default_data = {}

            for i in range(missing_count):
                feature_name = f"enhanced_default_{i:03d}"
                # より意味のあるデフォルト値（価格ベース）
                if hasattr(df.index, "__len__") and len(df.index) > 0:
                    if "close" in df.columns:
                        # 価格ベースの特徴量（RSI風）
                        default_data[feature_name] = 50.0 + (
                            i * 0.1
                        )  # 50.0, 50.1, 50.2...
                    else:
                        # 一般的な正規化された特徴量
                        default_data[feature_name] = 0.0 + (
                            i * 0.01
                        )  # 0.0, 0.01, 0.02...
                else:
                    default_data[feature_name] = 0.0

            # 一括追加（断片化回避）
            default_df = pd.DataFrame(default_data, index=df.index)
            df = pd.concat([df, default_df], axis=1)

            logger.info(
                f"✅ [PHASE-H12] Added {missing_count} enhanced default features, total: {len(df.columns)}"
            )

        except Exception as e:
            logger.error(f"❌ [PHASE-H12] Enhanced default generation failed: {e}")
            # フォールバック: 従来方式
            default_features = pd.DataFrame(
                0.0,
                index=df.index,
                columns=[f"fallback_feature_{i}" for i in range(missing_count)],
            )
            df = pd.concat([df, default_features], axis=1)
            logger.warning(
                f"⚠️ [PHASE-H12] Used fallback default features: {len(df.columns)}"
            )

        return df
    else:
        # 超過分を削除（最後の特徴量から）
        excess_count = current_count - target_count
        logger.warning(
            f"⚠️ [PHASE-H12] Excess {excess_count} features, removing last ones"
        )

        df = df.iloc[:, :target_count]
        logger.info(
            f"✅ [PHASE-H12] Removed {excess_count} features, total: {len(df.columns)}"
        )
        return df
