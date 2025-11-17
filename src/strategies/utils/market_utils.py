"""
市場データ分析ユーティリティ - Phase 52.4-B完了

全戦略で共通する市場データ分析機能を統合管理：
- 市場不確実性計算：ATR・ボリューム・価格変動率の統合分析
- 設定ベース統一ロジック：thresholds.yaml設定値の一元管理

Phase 52.4-B完了: 重複コード250-300行削減・保守性向上
"""

import pandas as pd

from ...core.logger import get_logger


class MarketUncertaintyCalculator:
    """
    市場不確実性計算統合クラス

    全戦略で使用する市場不確実性（market uncertainty）計算を一元化。
    ATRベースのボラティリティ・ボリューム異常度・価格変動率を統合し、
    市場状況を反映した動的信頼度調整係数を提供する。

    Phase 52.4-B完了: 全戦略から重複コード削除・統一ロジック実装
    """

    _logger = None

    @classmethod
    def _get_logger(cls):
        """ロガーの遅延初期化（循環インポート回避）"""
        if cls._logger is None:
            cls._logger = get_logger()
        return cls._logger

    @classmethod
    def calculate(cls, df: pd.DataFrame) -> float:
        """
        市場データ基づく不確実性計算（設定ベース統一ロジック）

        全戦略共通の市場不確実性計算を実行。
        thresholds.yamlの設定値を使用し、市場状況を0-0.1の範囲で数値化する。

        Args:
            df: 市場データ（close, atr_14, volume列必須）

        Returns:
            float: 市場不確実性係数（0-0.1の範囲、設定値で制限）

        Raises:
            なし（エラー時はデフォルト値0.02を返す）

        Example:
            >>> uncertainty = MarketUncertaintyCalculator.calculate(df)
            >>> adjusted_confidence = base_confidence * (1 + uncertainty)
        """
        logger = cls._get_logger()

        try:
            # 循環インポート回避のため遅延インポート
            from ...core.config.threshold_manager import get_threshold

            # 設定値取得（thresholds.yaml: dynamic_confidence.market_uncertainty）
            volatility_max = get_threshold(
                "dynamic_confidence.market_uncertainty.volatility_factor_max", 0.05
            )
            volume_max = get_threshold(
                "dynamic_confidence.market_uncertainty.volume_factor_max", 0.03
            )
            volume_multiplier = get_threshold(
                "dynamic_confidence.market_uncertainty.volume_multiplier", 0.1
            )
            price_max = get_threshold(
                "dynamic_confidence.market_uncertainty.price_factor_max", 0.02
            )
            uncertainty_max = get_threshold(
                "dynamic_confidence.market_uncertainty.uncertainty_max", 0.10
            )

            # 1. ATRベースのボラティリティ要因
            current_price = float(df["close"].iloc[-1])
            atr_value = float(df["atr_14"].iloc[-1])
            volatility_factor = min(volatility_max, atr_value / current_price)

            # 2. ボリューム異常度（平均からの乖離）
            current_volume = float(df["volume"].iloc[-1])
            avg_volume = float(df["volume"].rolling(20).mean().iloc[-1])
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_factor = min(volume_max, abs(volume_ratio - 1.0) * volume_multiplier)

            # 3. 価格変動率（短期動向）
            price_change = abs(float(df["close"].pct_change().iloc[-1]))
            price_factor = min(price_max, price_change)

            # 統合不確実性（設定値の範囲で市場状況を反映）
            market_uncertainty = volatility_factor + volume_factor + price_factor

            # 設定値で調整範囲を制限
            result = min(uncertainty_max, market_uncertainty)

            logger.debug(
                f"[MarketUncertainty] 計算完了: {result:.4f} "
                f"(volatility={volatility_factor:.4f}, volume={volume_factor:.4f}, price={price_factor:.4f})"
            )

            return result

        except Exception as e:
            logger.warning(f"[MarketUncertainty] 計算エラー: {e}")
            return 0.02  # デフォルト値（2%の軽微な調整）

    @classmethod
    def calculate_with_breakdown(cls, df: pd.DataFrame) -> dict:
        """
        市場不確実性計算（内訳付き）

        デバッグ・分析用に、各要因の内訳を返す拡張版。

        Args:
            df: 市場データ

        Returns:
            dict: {
                "total": 総合不確実性,
                "volatility": ボラティリティ要因,
                "volume": ボリューム要因,
                "price": 価格変動要因
            }
        """
        logger = cls._get_logger()

        try:
            from ...core.config.threshold_manager import get_threshold

            volatility_max = get_threshold(
                "dynamic_confidence.market_uncertainty.volatility_factor_max", 0.05
            )
            volume_max = get_threshold(
                "dynamic_confidence.market_uncertainty.volume_factor_max", 0.03
            )
            volume_multiplier = get_threshold(
                "dynamic_confidence.market_uncertainty.volume_multiplier", 0.1
            )
            price_max = get_threshold(
                "dynamic_confidence.market_uncertainty.price_factor_max", 0.02
            )
            uncertainty_max = get_threshold(
                "dynamic_confidence.market_uncertainty.uncertainty_max", 0.10
            )

            # 各要因計算
            current_price = float(df["close"].iloc[-1])
            atr_value = float(df["atr_14"].iloc[-1])
            volatility_factor = min(volatility_max, atr_value / current_price)

            current_volume = float(df["volume"].iloc[-1])
            avg_volume = float(df["volume"].rolling(20).mean().iloc[-1])
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_factor = min(volume_max, abs(volume_ratio - 1.0) * volume_multiplier)

            price_change = abs(float(df["close"].pct_change().iloc[-1]))
            price_factor = min(price_max, price_change)

            total = min(uncertainty_max, volatility_factor + volume_factor + price_factor)

            return {
                "total": total,
                "volatility": volatility_factor,
                "volume": volume_factor,
                "price": price_factor,
            }

        except Exception as e:
            logger.warning(f"[MarketUncertainty] 内訳計算エラー: {e}")
            return {
                "total": 0.02,
                "volatility": 0.01,
                "volume": 0.005,
                "price": 0.005,
            }
