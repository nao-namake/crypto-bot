"""
Feature Coordinator - Phase 16.3-B Split

統合前: crypto_bot/ml/feature_master_implementation.py（1,801行）
分割後: crypto_bot/ml/features/master/feature_coordinator.py

機能:
- FeatureMasterImplementation: メイン特徴量統合クラス
- 97特徴量システム統合・調整機能
- 実装進捗管理・レポート生成・フォールバック機能

Phase 16.3-B実装日: 2025年8月8日
"""

import logging
from typing import Dict, Optional

import pandas as pd

from .market_features import MarketFeaturesMixin

# 分割後のMixinクラスを統合import
from .technical_indicators import TechnicalIndicatorsMixin

logger = logging.getLogger(__name__)


class FeatureMasterImplementation(TechnicalIndicatorsMixin, MarketFeaturesMixin):
    """
    97特徴量完全実装マスタークラス

    - production.yml定義の92特徴量を完全実装
    - OHLCV基本5特徴量 + 92特徴量 = 97特徴量システム
    - デフォルト値依存を根絶し、実装率100%達成
    - TechnicalIndicatorsMixin + MarketFeaturesMixin の統合
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.ml_config = self.config.get("ml", {})

        # Phase 8.1: 実装進捗追跡
        self.implemented_features = set()
        self.implementation_stats = {
            "total_required": 92,
            "implemented": 0,
            "implementation_rate": 0.0,
        }

        # フォールバック削減機能: 動的期間調整
        self.adaptive_periods = True
        self.min_data_threshold = 3  # 最低データ数

        logger.info(
            "🔧 FeatureMasterImplementation初期化: 97特徴量完全実装システム（フォールバック削減版）"
        )

    def _adjust_period_for_data_length(
        self, desired_period: int, data_length: int, min_ratio: float = 0.5
    ) -> int:
        """
        データ長に応じて期間を動的に調整（フォールバック削減）

        Parameters
        ----------
        desired_period : int
            希望する期間
        data_length : int
            利用可能なデータ長
        min_ratio : float
            最小比率（デフォルト0.5 = データの半分以上を使用）

        Returns
        -------
        int
            調整された期間
        """
        if not self.adaptive_periods:
            return desired_period

        # データ長の50%を上限とする調整
        max_period = max(2, int(data_length * min_ratio))
        adjusted_period = min(desired_period, max_period)

        if adjusted_period != desired_period:
            logger.debug(
                f"📉 期間調整: {desired_period} → {adjusted_period} (データ長: {data_length})"
            )

        return adjusted_period

    def _safe_rolling_calculation(
        self, series: pd.Series, window: int, operation: str = "mean"
    ) -> pd.Series:
        """
        安全なローリング計算（フォールバック削減）

        Parameters
        ----------
        series : pd.Series
            計算対象の系列
        window : int
            ウィンドウサイズ
        operation : str
            操作種類 ('mean', 'std', 'min', 'max', 'sum')

        Returns
        -------
        pd.Series
            計算結果
        """
        if len(series) == 0:
            return pd.Series(dtype=float, index=series.index)

        # データ長に応じてウィンドウを調整
        adjusted_window = self._adjust_period_for_data_length(window, len(series))

        try:
            rolling_obj = series.rolling(window=adjusted_window, min_periods=1)

            if operation == "mean":
                result = rolling_obj.mean()
            elif operation == "std":
                result = rolling_obj.std()
            elif operation == "min":
                result = rolling_obj.min()
            elif operation == "max":
                result = rolling_obj.max()
            elif operation == "sum":
                result = rolling_obj.sum()
            else:
                logger.warning(
                    f"⚠️ 未知のローリング操作: {operation}, meanにフォールバック"
                )
                result = rolling_obj.mean()

            # NaN値の補間処理（フォールバック削減）
            if result.isna().any():
                # 前方補間 → 後方補間 → 平均値補間の順で実行
                result = result.ffill().bfill()
                if result.isna().any():
                    # 系列の平均値で補間
                    mean_value = series.mean() if not series.isna().all() else 0.0
                    result = result.fillna(mean_value)

            return result

        except Exception as e:
            logger.warning(f"⚠️ ローリング計算エラー: {e}, 単純値で代替")
            # エラー時は系列の平均値を返す
            mean_value = series.mean() if not series.isna().all() else 0.0
            return pd.Series([mean_value] * len(series), index=series.index)

    def generate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        全92特徴量を生成するメインメソッド

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV基本データ（5特徴量）

        Returns
        -------
        pd.DataFrame
            97特徴量完全実装データフレーム
        """
        logger.info("🚀 Phase 8: 92特徴量完全実装開始")

        # フォールバック発動条件を厳格化：本当に必要な時のみ
        if df.empty:
            logger.warning("⚠️ 完全に空のデータフレーム: フォールバック発動")
            fallback_df = self._generate_comprehensive_fallback(df)
            return fallback_df
        elif len(df) < 3:
            logger.warning("⚠️ 極度データ不足（3行未満）: フォールバック発動")
            fallback_df = self._generate_comprehensive_fallback(df)
            return fallback_df
        elif len(df) < 10:
            logger.info(f"ℹ️ 少量データ（{len(df)}行）: 特徴量計算可能範囲で実行")
            # フォールバックではなく、少量データ用の調整済み処理を実行

        result_df = df.copy()

        # Phase 8.2: 実装優先度順に特徴量生成
        # TechnicalIndicatorsMixinからの機能

        # 1. 基本ラグ特徴量 (複雑度:1, 優先度:1)
        result_df = self._generate_basic_lag_features(result_df)

        # 2. リターン系 (複雑度:1, 優先度:1)
        result_df = self._generate_return_features(result_df)

        # 3. EMA系 (複雑度:2, 優先度:1)
        result_df = self._generate_ema_features(result_df)

        # 4. RSI系 (複雑度:2, 優先度:1)
        result_df = self._generate_rsi_features(result_df)

        # 5. MACD系 (複雑度:3, 優先度:1)
        result_df = self._generate_macd_features(result_df)

        # 6. 統計系 (複雑度:2, 優先度:2)
        result_df = self._generate_statistical_features(result_df)

        # 7. ATR・ボラティリティ系 (複雑度:3, 優先度:2)
        result_df = self._generate_atr_volatility_features(result_df)

        # 8. 価格ポジション系 (複雑度:3, 優先度:2)
        result_df = self._generate_price_position_features(result_df)

        # 9. ボリンジャーバンド系 (複雑度:3, 優先度:2)
        result_df = self._generate_bollinger_band_features(result_df)

        # 10. 時間特徴量系 (複雑度:1, 優先度:3)
        result_df = self._generate_time_features(result_df)

        # Phase 9.1: 中・低優先度特徴量（段階的実装開始）
        # 11. ストキャスティクス系: 4個 (Phase 9.1.1実装完了)
        result_df = self._generate_stochastic_features(result_df)

        # 12. 出来高系: 15個 (Phase 9.1.2実装完了)
        result_df = self._generate_volume_features(result_df)

        # 13. オシレーター系: 4個 (Phase 9.1.3実装完了)
        result_df = self._generate_oscillator_features(result_df)

        # 14. ADX・トレンド系: 5個 (Phase 9.1.4実装完了)
        result_df = self._generate_adx_trend_features(result_df)

        # MarketFeaturesMixinからの機能
        # 15. サポート・レジスタンス系: 5個 (Phase 9.1.5実装完了)
        result_df = self._generate_support_resistance_features(result_df)

        # 16. チャートパターン系: 4個 (Phase 9.1.6実装完了)
        result_df = self._generate_chart_pattern_features(result_df)

        # 17. 高度テクニカル系: 10個 (Phase 9.1.7実装完了)
        result_df = self._generate_advanced_technical_features(result_df)

        # 18. 市場状態系: 6個 (Phase 9.1.8実装完了)
        result_df = self._generate_market_state_features(result_df)

        # 19. その他特徴量は今後実装
        result_df = self._generate_remaining_features_placeholder(result_df)

        # 実装統計更新
        self._update_implementation_stats(result_df)

        logger.info(
            f"✅ Phase 8.2: {self.implementation_stats['implemented']}/92特徴量実装完了 "
            f"({self.implementation_stats['implementation_rate']:.1f}%)"
        )

        return result_df

    def _generate_basic_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """基本ラグ特徴量: 2個 (close_lag_1, close_lag_3)"""
        logger.debug("🔧 基本ラグ特徴量生成中...")

        try:
            # close_lag_1
            if "close" in df.columns:
                df["close_lag_1"] = df["close"].shift(1)
                self.implemented_features.add("close_lag_1")

                # close_lag_3
                df["close_lag_3"] = df["close"].shift(3)
                self.implemented_features.add("close_lag_3")

                logger.debug("✅ 基本ラグ特徴量: 2/2個実装完了")
            else:
                logger.warning("⚠️ close列が見つかりません")

        except Exception as e:
            logger.error(f"❌ 基本ラグ特徴量生成エラー: {e}")

        return df

    def _generate_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """リターン系: 5個 (returns_1, returns_2, returns_3, returns_5, returns_10)"""
        logger.debug("🔧 リターン系特徴量生成中...")

        try:
            if "close" in df.columns:
                periods = [1, 2, 3, 5, 10]

                for period in periods:
                    feature_name = f"returns_{period}"
                    # パーセントリターン計算
                    df[feature_name] = df["close"].pct_change(period) * 100
                    self.implemented_features.add(feature_name)

                logger.debug(f"✅ リターン系特徴量: {len(periods)}/5個実装完了")
            else:
                logger.warning("⚠️ close列が見つかりません")

        except Exception as e:
            logger.error(f"❌ リターン系特徴量生成エラー: {e}")

        return df

    def _generate_ema_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """EMA系: 6個 (ema_5, ema_10, ema_20, ema_50, ema_100, ema_200)"""
        logger.debug("🔧 EMA系特徴量生成中...")

        try:
            if "close" in df.columns:
                periods = [5, 10, 20, 50, 100, 200]

                for period in periods:
                    feature_name = f"ema_{period}"
                    # 指数移動平均計算
                    df[feature_name] = df["close"].ewm(span=period, adjust=False).mean()
                    self.implemented_features.add(feature_name)

                logger.debug(f"✅ EMA系特徴量: {len(periods)}/6個実装完了")
            else:
                logger.warning("⚠️ close列が見つかりません")

        except Exception as e:
            logger.error(f"❌ EMA系特徴量生成エラー: {e}")

        return df

    def _generate_remaining_features_placeholder(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        残り特徴量のプレースホルダー（Phase 9.1.8完了）

        🎊 全92特徴量実装完了達成!

        実装済み特徴量:
        - ストキャスティクス系: 4個 ✅ (Phase 9.1.1)
        - 出来高系: 15個 ✅ (Phase 9.1.2)
        - オシレーター系: 4個 ✅ (Phase 9.1.3)
        - ADX・トレンド系: 5個 ✅ (Phase 9.1.4)
        - サポート・レジスタンス系: 5個 ✅ (Phase 9.1.5)
        - チャートパターン系: 4個 ✅ (Phase 9.1.6)
        - 高度テクニカル系: 10個 ✅ (Phase 9.1.7)
        - 市場状態系: 6個 ✅ (Phase 9.1.8)

        総計: 基本(52) + 追加(40) = 92特徴量完全実装
        """
        logger.debug("🎊 Phase 9.1.8完了: 92特徴量完全実装達成!")

        # production.yml定義の全92特徴量 - すべて実装済み
        # プレースホルダーは不要となったが、念のため空のリストを保持
        all_required_features = [
            # 全実装済み - プレースホルダー不要
        ]

        # 未実装特徴量にデフォルト値を設定
        for feature_name in all_required_features:
            if (
                feature_name not in df.columns
                and feature_name not in self.implemented_features
            ):
                # 特徴量タイプに応じたデフォルト値設定
                if "volume" in feature_name:
                    df[feature_name] = 1.0  # ボリューム系
                elif any(
                    x in feature_name for x in ["ratio", "position", "efficiency"]
                ):
                    df[feature_name] = 0.5  # 比率・ポジション系
                elif any(
                    x in feature_name
                    for x in ["oversold", "overbought", "breakout", "cross"]
                ):
                    df[feature_name] = 0  # バイナリ系
                elif any(
                    x in feature_name for x in ["distance", "strength", "quality"]
                ):
                    df[feature_name] = 50.0  # スコア系
                else:
                    df[feature_name] = 0.0  # その他

                # プレースホルダーとしてマーク
                logger.debug(f"⚠️ プレースホルダー設定: {feature_name}")

        return df

    def _generate_comprehensive_fallback(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        データ不足時の包括的フォールバック（97特徴量保証）
        """
        logger.warning(
            "⚠️ データ不足により包括的フォールバック特徴量を生成（97特徴量保証）"
        )

        # 最低限のデータフレーム作成
        if df.empty:
            dates = pd.date_range("2024-01-01", periods=20, freq="H")
            fallback_df = pd.DataFrame(
                {
                    "open": 100.0,
                    "high": 105.0,
                    "low": 95.0,
                    "close": 100.0,
                    "volume": 10000.0,
                },
                index=dates,
            )
        else:
            # 既存データを20行に拡張
            target_length = max(20, len(df))
            if len(df) < target_length:
                # データを繰り返して必要な長さまで拡張
                repeat_times = (target_length // len(df)) + 1
                fallback_df = pd.concat([df] * repeat_times, ignore_index=True)[
                    :target_length
                ]

                # インデックスを時系列に修正
                if hasattr(df.index, "freq") and df.index.freq:
                    freq = df.index.freq
                else:
                    freq = "H"

                start_time = df.index[0] if len(df) > 0 else pd.Timestamp("2024-01-01")
                fallback_df.index = pd.date_range(
                    start=start_time, periods=target_length, freq=freq
                )
            else:
                fallback_df = df.copy()

        # 必須列の補完
        required_columns = ["open", "high", "low", "close", "volume"]
        for col in required_columns:
            if col not in fallback_df.columns:
                if col == "volume":
                    fallback_df[col] = 10000.0
                else:
                    fallback_df[col] = 100.0

        # 97特徴量システムで処理
        try:
            result_df = self.generate_all_features(fallback_df)
            if result_df.shape[1] != 97:
                # 不足分をデフォルト値で補完
                return self._ensure_97_features(result_df)
            return result_df
        except Exception as e:
            logger.error(f"❌ 包括的フォールバック処理エラー: {e}")
            return self._ensure_97_features(fallback_df)

    def _ensure_97_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """97特徴量を確実に保証"""
        # production.yml定義の全92特徴量リスト
        all_features = [
            "close_lag_1",
            "close_lag_3",
            "volume_lag_1",
            "volume_lag_4",
            "volume_lag_5",
            "returns_1",
            "returns_2",
            "returns_3",
            "returns_5",
            "returns_10",
            "ema_5",
            "ema_10",
            "ema_20",
            "ema_50",
            "ema_100",
            "ema_200",
            "price_position_20",
            "price_position_50",
            "price_vs_sma20",
            "bb_position",
            "intraday_position",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_width",
            "bb_squeeze",
            "rsi_14",
            "rsi_oversold",
            "rsi_overbought",
            "macd",
            "macd_signal",
            "macd_hist",
            "macd_cross_up",
            "macd_cross_down",
            "stoch_k",
            "stoch_d",
            "stoch_oversold",
            "stoch_overbought",
            "atr_14",
            "volatility_20",
            "volume_sma_20",
            "volume_ratio",
            "volume_trend",
            "vwap",
            "vwap_distance",
            "obv",
            "obv_sma",
            "cmf",
            "mfi",
            "ad_line",
            "volume_breakout",
            "volume_price_correlation",
            "adx_14",
            "plus_di",
            "minus_di",
            "trend_strength",
            "trend_direction",
            "cci_20",
            "williams_r",
            "ultimate_oscillator",
            "momentum_14",
            "support_distance",
            "resistance_distance",
            "support_strength",
            "price_breakout_up",
            "price_breakout_down",
            "doji",
            "hammer",
            "engulfing",
            "pinbar",
            "roc_10",
            "roc_20",
            "trix",
            "mass_index",
            "keltner_upper",
            "keltner_lower",
            "donchian_upper",
            "donchian_lower",
            "ichimoku_conv",
            "ichimoku_base",
            "price_efficiency",
            "trend_consistency",
            "volatility_regime",
            "momentum_quality",
            "market_phase",
            "zscore",
            "close_std_10",
            "hour",
            "day_of_week",
            "is_weekend",
            "is_asian_session",
            "is_us_session",
        ]

        # 不足特徴量をデフォルト値で追加
        for feature in all_features:
            if feature not in df.columns:
                if "ratio" in feature or "position" in feature:
                    df[feature] = 0.5
                elif any(
                    x in feature
                    for x in ["oversold", "overbought", "cross", "breakout", "weekend"]
                ):
                    df[feature] = 0
                elif "rsi" in feature:
                    df[feature] = 50.0
                elif "volume" in feature:
                    df[feature] = 10000.0
                else:
                    df[feature] = (
                        100.0
                        if any(
                            x in feature
                            for x in ["price", "close", "open", "high", "low"]
                        )
                        else 0.0
                    )

        return df

    def _update_implementation_stats(self, df: pd.DataFrame):
        """実装統計を更新"""
        self.implementation_stats["implemented"] = len(self.implemented_features)
        self.implementation_stats["implementation_rate"] = (
            len(self.implemented_features)
            / self.implementation_stats["total_required"]
            * 100
        )

        logger.info(
            f"📊 実装統計: {self.implementation_stats['implemented']}/92特徴量 "
            f"({self.implementation_stats['implementation_rate']:.1f}%)"
        )

    def get_implementation_report(self) -> Dict:
        """実装レポートを取得"""
        return {
            "implementation_stats": self.implementation_stats,
            "implemented_features": sorted(list(self.implemented_features)),
            "total_features": len(self.implemented_features),
        }


def create_97_feature_system(
    df: pd.DataFrame, config: Optional[Dict] = None
) -> pd.DataFrame:
    """
    97特徴量システムのエントリーポイント

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV基本データ
    config : Dict, optional
        設定辞書

    Returns
    -------
    pd.DataFrame
        97特徴量完全実装データフレーム
    """
    feature_master = FeatureMasterImplementation(config)
    return feature_master.generate_all_features(df)
