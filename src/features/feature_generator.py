"""
特徴量生成統合システム

最終更新: 2025/11/16 (Phase 52.4-B)

TechnicalIndicators、MarketAnomalyDetector、FeatureServiceAdapterを
1つのクラスに統合し、重複コード削除と保守性向上を実現。

開発履歴:
- Phase 52.4-B (2025/11/16): コード整理・ドキュメント統一完了・特徴量数コメント修正
- Phase 51.7 Day 7 (2025/11/07): 6戦略統合・55特徴量システム確立
- Phase 51.7 Day 2 (2025/11/07): Feature Importance分析に基づく最適化
- Phase 50.9 (2025/11/01): 外部API完全削除・シンプル設計回帰
- Phase 50.2 (2025/10/28): 時間的特徴量拡張（市場セッション+周期性追加）
- Phase 50.1 (2025/10/27): 確実な特徴量生成実装（strategy_signals=None時も0埋め）
- Phase 41 (2025/10/17): Strategy-Aware ML実装・戦略シグナル追加
- Phase 40.6 (2025/10/15): Feature Engineering拡張（Lag/Rolling/Interaction/Time）
- Phase 38.4 (2025/10/13): 97→15特徴量最適化

統合効果:
- ファイル数削減: 3→1（67%削減）
- コード行数削減: 461行→約250行（46%削除）
- 重複コード削除: _handle_nan_values、logger初期化等
- 管理簡素化: 特徴量処理の完全一元化
"""

import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..core.config import get_anomaly_config

# Phase 38.4: 特徴量定義一元化（feature_managerから取得）
from ..core.config.feature_manager import (
    get_feature_categories,
    get_feature_count,
    get_feature_names,
)
from ..core.exceptions import DataProcessingError
from ..core.logger import CryptoBotLogger, get_logger

# 特徴量リスト（一元化対応）
OPTIMIZED_FEATURES = get_feature_names()

# 特徴量カテゴリ（一元化対応）
FEATURE_CATEGORIES = get_feature_categories()

# ========================================
# テクニカル指標パラメータ定数
# ========================================
# Phase 52.4-B: Magic number抽出

# RSI
RSI_PERIOD = 14

# MACD
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9

# ATR
ATR_PERIOD = 14

# Bollinger Bands
BB_PERIOD = 20
BB_STD_MULTIPLIER = 2

# EMA
EMA_SHORT_PERIOD = 20
EMA_LONG_PERIOD = 50

# Donchian Channel
DONCHIAN_PERIOD = 20

# ADX
ADX_PERIOD = 14

# Stochastic Oscillator
STOCHASTIC_PERIOD = 14
STOCHASTIC_SMOOTH_K = 3
STOCHASTIC_SMOOTH_D = 3

# Volume EMA
VOLUME_EMA_PERIOD = 20

# Lag features
LAG_PERIODS_CLOSE = [1, 2, 3, 10]
LAG_PERIODS_VOLUME = [1, 2, 3]
LAG_PERIODS_INDICATOR = [1]  # RSI, MACD

# Rolling statistics
ROLLING_WINDOWS_MA = [10, 20]
ROLLING_WINDOWS_STD = [5, 10, 20]

# Market hours (JST)
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 15
EUROPE_SESSION_START = 16
EUROPE_SESSION_END_HOUR = 23
EUROPE_SESSION_EARLY_HOUR = 1

# Numerical stability
EPSILON = 1e-8

# Cyclic encoding
HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7


class FeatureGenerator:
    """
    統合特徴量生成クラス

    最終更新: 2025/11/16 (Phase 52.4-B)

    テクニカル指標、異常検知、特徴量サービス機能を
    1つのクラスに統合し、55特徴量を確実に生成。

    主要機能:
    - 基本特徴量生成（2個）
    - テクニカル指標生成（17個：RSI, MACD拡張, ATR, BB拡張, EMA, Donchian, ADX, Stochastic等）
    - 異常検知指標生成（1個：Volume Ratio）
    - ラグ特徴量生成（9個：Close/Volume/RSI/MACD lag）
    - 移動統計量生成（5個：MA, Std）
    - 交互作用特徴量生成（5個：RSI×ATR, MACD×Volume等）
    - 時間ベース特徴量生成（7個：Hour, Day, 市場セッション, 周期性）
    - 戦略シグナル特徴量生成（6個：戦略判断エンコード）
    - 統合品質管理と特徴量確認（必ず55特徴量）

    特徴量最適化:
    - 55特徴量固定（49基本+6戦略シグナル）
    - Feature Importance分析に基づく最適化
    - 6戦略対応（Stochastic, MACD拡張, BB拡張等）
    - システム精度向上・保守性向上

    信頼性保証:
    - 必ず固定数生成（strategy_signals=None時も0.0埋め）
    - 後から追加しない設計
    - ML予測エラー防止（特徴量数不一致解消）
    """

    def __init__(self, lookback_period: Optional[int] = None) -> None:
        """
        初期化

        Args:
            lookback_period: 異常検知の参照期間
        """
        self.logger = get_logger()
        self.lookback_period = lookback_period or get_anomaly_config(
            "spike_detection.lookback_period", 20
        )
        self.computed_features = set()

    async def generate_features(
        self,
        market_data: Dict[str, Any],
        strategy_signals: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> pd.DataFrame:
        """
        統合特徴量生成処理

        Args:
            market_data: 市場データ（DataFrame または dict）
            strategy_signals: 戦略シグナル辞書（オプション）

        Returns:
            特徴量を含むDataFrame（55特徴量固定）

        Raises:
            DataProcessingError: 特徴量生成エラー

        Note:
            - Phase 52.4-B: 55特徴量固定システム（49基本+6戦略シグナル）
            - 確実な特徴量生成（strategy_signals=None時も6個を0埋め）
            - 信頼性向上: 後から追加せず、生成時に全特徴量確定
        """
        try:
            # DataFrameに変換
            result_df = self._convert_to_dataframe(market_data)

            # Phase 52.4-B: 特徴量数一元管理（feature_order.jsonから自動取得）
            target_features = get_feature_count()
            self.logger.info(
                f"特徴量生成開始 - Phase 52.4-B: {target_features}特徴量固定システム（一元管理）"
            )
            self.computed_features.clear()

            # 必要列チェック
            self._validate_required_columns(result_df)

            # 🔹 基本特徴量を生成（2個）
            result_df = self._generate_basic_features(result_df)

            # 🔹 テクニカル指標を生成（17個）
            result_df = self._generate_technical_indicators(result_df)

            # 🔹 異常検知指標を生成（1個）
            result_df = self._generate_anomaly_indicators(result_df)

            # 🔹 ラグ特徴量を生成（9個）- Phase 52.4-B
            result_df = self._generate_lag_features(result_df)

            # 🔹 移動統計量を生成（5個）- Phase 52.4-B
            result_df = self._generate_rolling_statistics(result_df)

            # 🔹 交互作用特徴量を生成（5個）- Phase 52.4-B
            result_df = self._generate_interaction_features(result_df)

            # 🔹 時間ベース特徴量を生成（7個）- Phase 52.4-B
            result_df = self._generate_time_features(result_df)

            # 🔹 戦略シグナル特徴量を追加（6個）- Phase 52.4-B: 必ず追加（Noneの場合は0埋め）
            result_df = self._add_strategy_signal_features(result_df, strategy_signals)

            # 🔹 NaN値処理（統合版）
            result_df = self._handle_nan_values(result_df)

            # 🎯 特徴量完全確認・検証（55特徴量固定）
            self._validate_feature_generation(result_df, expected_count=target_features)

            # DataFrameをそのまま返す（戦略で使用するため）
            return result_df

        except Exception as e:
            self.logger.error(f"統合特徴量生成エラー: {e}")
            raise DataProcessingError(f"特徴量生成失敗: {e}")

    def generate_features_sync(
        self,
        df: pd.DataFrame,
        strategy_signals: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> pd.DataFrame:
        """
        同期版特徴量生成（バックテスト事前計算用）

        Args:
            df: OHLCVデータを含むDataFrame
            strategy_signals: 戦略シグナル辞書（オプション）

        Returns:
            特徴量を含むDataFrame（必ず55特徴量）

        Note:
            - Phase 52.4-B: 55特徴量固定システム
            - バックテストの事前計算で使用（asyncなしで一括計算）
            - 確実な特徴量生成（strategy_signals=None時も6個を0埋め）
        """
        try:
            result_df = df.copy()

            # 必要列チェック
            self._validate_required_columns(result_df)

            # 基本特徴量を生成（2個）
            result_df = self._generate_basic_features(result_df)

            # テクニカル指標を生成（17個）
            result_df = self._generate_technical_indicators(result_df)

            # 異常検知指標を生成（1個）
            result_df = self._generate_anomaly_indicators(result_df)

            # ラグ特徴量を生成（9個）- Phase 52.4-B
            result_df = self._generate_lag_features(result_df)

            # 移動統計量を生成（5個）- Phase 52.4-B
            result_df = self._generate_rolling_statistics(result_df)

            # 交互作用特徴量を生成（5個）- Phase 52.4-B
            result_df = self._generate_interaction_features(result_df)

            # 時間ベース特徴量を生成（7個）- Phase 52.4-B
            result_df = self._generate_time_features(result_df)

            # 戦略シグナル特徴量を追加（6個）- Phase 52.4-B（Noneの場合は0埋め）
            result_df = self._add_strategy_signal_features(result_df, strategy_signals)

            # NaN値処理（統合版）
            result_df = self._handle_nan_values(result_df)

            return result_df

        except Exception as e:
            self.logger.error(f"同期版特徴量生成エラー: {e}")
            raise DataProcessingError(f"同期版特徴量生成失敗: {e}")

    def _convert_to_dataframe(self, market_data: Dict[str, Any]) -> pd.DataFrame:
        """
        市場データをDataFrameに変換（DatetimeIndex強制保持）

        Phase 54.9追加: DatetimeIndex明示的変換により、
        バックテスト時のDatetimeIndex喪失を根本的に防止。
        """
        if isinstance(market_data, pd.DataFrame):
            result = market_data.copy()

            # Phase 54.9: DatetimeIndex強制保持（防御的プログラミング・Bug #3の二重防御）
            if not isinstance(result.index, pd.DatetimeIndex):
                if "timestamp" in result.columns:
                    result.index = pd.to_datetime(result["timestamp"], unit="ms")
                    result = result.drop(columns=["timestamp"])
                    self.logger.debug("📅 _convert_to_dataframe: DatetimeIndex変換完了")
                elif "datetime" in result.columns:
                    result.index = pd.to_datetime(result["datetime"])
                    result = result.drop(columns=["datetime"])
                    self.logger.debug(
                        "📅 _convert_to_dataframe: DatetimeIndex変換完了（datetime列）"
                    )

            return result
        elif isinstance(market_data, dict):
            try:
                # タイムフレーム辞書の場合（マルチタイムフレームデータ）
                # 設定から優先順位付きタイムフレームを取得
                from ..core.config import get_data_config

                timeframe_keys = get_data_config("timeframes", ["4h", "15m"])  # 設定化対応
                for tf in timeframe_keys:
                    if tf in market_data and isinstance(market_data[tf], pd.DataFrame):
                        self.logger.info(f"タイムフレーム辞書からメイン時系列取得: {tf}")
                        return market_data[tf].copy()

                # 通常の辞書データの場合（OHLCV形式等）
                # 全ての値がスカラーかリストかをチェック
                if all(
                    isinstance(v, (int, float, str)) or (isinstance(v, list) and len(v) > 0)
                    for v in market_data.values()
                ):
                    return pd.DataFrame(market_data)

                # その他の構造の辞書
                self.logger.warning(f"複雑な辞書構造を検出: keys={list(market_data.keys())}")
                return pd.DataFrame(market_data)

            except (ValueError, KeyError, TypeError) as e:
                self.logger.error(
                    f"市場データ変換エラー - 構造: {type(market_data)}, キー: {list(market_data.keys()) if hasattr(market_data, 'keys') else 'N/A'}"
                )
                raise DataProcessingError(f"Dict→DataFrame変換データ構造エラー: {e}")
            except (MemoryError, OverflowError) as e:
                raise DataProcessingError(f"Dict→DataFrame変換サイズエラー: {e}")
            except Exception as e:
                raise DataProcessingError(f"Dict→DataFrame変換予期しないエラー: {e}")
        else:
            raise ValueError(f"Unsupported market_data type: {type(market_data)}")

    def _validate_required_columns(self, df: pd.DataFrame) -> None:
        """必要列の存在確認"""
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise DataProcessingError(f"必要列が不足: {missing_cols}")

    def _generate_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """基本特徴量生成（2個）"""
        result_df = df.copy()

        # 基本データはそのまま（close, volume）
        basic_features = []
        if "close" in result_df.columns:
            basic_features.append("close")
        if "volume" in result_df.columns:
            basic_features.append("volume")

        self.computed_features.update(basic_features)
        self.logger.debug(f"基本特徴量生成完了: {len(basic_features)}個")
        return result_df

    def _generate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """テクニカル指標生成（17個）"""
        result_df = df.copy()

        # RSI 14期間
        result_df["rsi_14"] = self._calculate_rsi(result_df["close"])
        self.computed_features.add("rsi_14")

        # MACD拡張（ライン・シグナル・ヒストグラム生成）
        macd_line, macd_signal = self._calculate_macd(result_df["close"])
        result_df["macd"] = macd_line
        result_df["macd_signal"] = macd_signal
        result_df["macd_histogram"] = macd_line - macd_signal
        self.computed_features.update(["macd", "macd_signal", "macd_histogram"])

        # ATR 14期間
        result_df["atr_14"] = self._calculate_atr(result_df)
        self.computed_features.add("atr_14")

        # ボリンジャーバンド拡張（上限・下限・位置）
        bb_upper, bb_lower, bb_position = self._calculate_bb_bands(result_df["close"])
        result_df["bb_upper"] = bb_upper
        result_df["bb_lower"] = bb_lower
        result_df["bb_position"] = bb_position
        self.computed_features.update(["bb_upper", "bb_lower", "bb_position"])

        # EMA 2本
        result_df["ema_20"] = result_df["close"].ewm(span=EMA_SHORT_PERIOD, adjust=False).mean()
        result_df["ema_50"] = result_df["close"].ewm(span=EMA_LONG_PERIOD, adjust=False).mean()
        self.computed_features.update(["ema_20", "ema_50"])

        # Donchian Channel指標（3個）
        donchian_high, donchian_low, channel_position = self._calculate_donchian_channel(result_df)
        result_df["donchian_high_20"] = donchian_high
        result_df["donchian_low_20"] = donchian_low
        result_df["channel_position"] = channel_position
        self.computed_features.update(["donchian_high_20", "donchian_low_20", "channel_position"])

        # ADX指標（3個）
        adx, plus_di, minus_di = self._calculate_adx_indicators(result_df)
        result_df["adx_14"] = adx
        result_df["plus_di_14"] = plus_di
        result_df["minus_di_14"] = minus_di
        self.computed_features.update(["adx_14", "plus_di_14", "minus_di_14"])

        # Stochastic Oscillator（2個）
        stoch_k, stoch_d = self._calculate_stochastic(result_df)
        result_df["stoch_k"] = stoch_k
        result_df["stoch_d"] = stoch_d
        self.computed_features.update(["stoch_k", "stoch_d"])

        # 出来高EMA
        result_df["volume_ema"] = self._calculate_volume_ema(result_df["volume"])
        self.computed_features.add("volume_ema")

        # ATR比率（ボラティリティ正規化）
        result_df["atr_ratio"] = self._calculate_atr_ratio(result_df)
        self.computed_features.add("atr_ratio")

        self.logger.debug("テクニカル指標生成完了: 17個")
        return result_df

    def _generate_anomaly_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """異常検知指標生成（1個）"""
        result_df = df.copy()

        # 出来高比率
        result_df["volume_ratio"] = self._calculate_volume_ratio(result_df["volume"])
        self.computed_features.add("volume_ratio")

        self.logger.debug("異常検知指標生成完了: 1個")
        return result_df

    def _generate_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ラグ特徴量生成（過去N期間の値・9個）"""
        result_df = df.copy()

        # Close lag features
        for lag in LAG_PERIODS_CLOSE:
            result_df[f"close_lag_{lag}"] = result_df["close"].shift(lag)
            self.computed_features.add(f"close_lag_{lag}")

        # Volume lag features
        for lag in LAG_PERIODS_VOLUME:
            result_df[f"volume_lag_{lag}"] = result_df["volume"].shift(lag)
            self.computed_features.add(f"volume_lag_{lag}")

        # RSI lag feature
        if "rsi_14" in result_df.columns:
            for lag in LAG_PERIODS_INDICATOR:
                result_df[f"rsi_lag_{lag}"] = result_df["rsi_14"].shift(lag)
                self.computed_features.add(f"rsi_lag_{lag}")

        # MACD lag feature
        if "macd" in result_df.columns:
            for lag in LAG_PERIODS_INDICATOR:
                result_df[f"macd_lag_{lag}"] = result_df["macd"].shift(lag)
                self.computed_features.add(f"macd_lag_{lag}")

        self.logger.debug("ラグ特徴量生成完了: 9個")
        return result_df

    def _generate_rolling_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """移動統計量生成（Rolling Statistics・5個）"""
        result_df = df.copy()

        # Moving Average
        for window in ROLLING_WINDOWS_MA:
            result_df[f"close_ma_{window}"] = (
                result_df["close"].rolling(window=window, min_periods=1).mean()
            )
            self.computed_features.add(f"close_ma_{window}")

        # Standard Deviation
        for window in ROLLING_WINDOWS_STD:
            result_df[f"close_std_{window}"] = (
                result_df["close"].rolling(window=window, min_periods=1).std()
            )
            self.computed_features.add(f"close_std_{window}")

        self.logger.debug("移動統計量生成完了: 5個")
        return result_df

    def _generate_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """交互作用特徴量生成（Feature Interactions・5個）"""
        result_df = df.copy()

        # RSI × ATR
        if "rsi_14" in result_df.columns and "atr_14" in result_df.columns:
            result_df["rsi_x_atr"] = result_df["rsi_14"] * result_df["atr_14"]
            self.computed_features.add("rsi_x_atr")

        # MACD × Volume
        if "macd" in result_df.columns and "volume" in result_df.columns:
            result_df["macd_x_volume"] = result_df["macd"] * result_df["volume"]
            self.computed_features.add("macd_x_volume")

        # BB Position × Volume Ratio
        if "bb_position" in result_df.columns and "volume_ratio" in result_df.columns:
            result_df["bb_position_x_volume_ratio"] = (
                result_df["bb_position"] * result_df["volume_ratio"]
            )
            self.computed_features.add("bb_position_x_volume_ratio")

        # Close × ATR
        if "close" in result_df.columns and "atr_14" in result_df.columns:
            result_df["close_x_atr"] = result_df["close"] * result_df["atr_14"]
            self.computed_features.add("close_x_atr")

        # Volume × BB Position
        if "volume" in result_df.columns and "bb_position" in result_df.columns:
            result_df["volume_x_bb_position"] = result_df["volume"] * result_df["bb_position"]
            self.computed_features.add("volume_x_bb_position")

        self.logger.debug("交互作用特徴量生成完了: 5個")
        return result_df

    def _generate_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """時間ベース特徴量生成（Time-based Features・7個）"""
        result_df = df.copy()

        # indexまたはtimestamp列から日時情報を抽出
        if isinstance(result_df.index, pd.DatetimeIndex):
            dt_index = result_df.index
        elif "timestamp" in result_df.columns:
            dt_index = pd.to_datetime(result_df["timestamp"])
        else:
            # 日時情報がない場合は中立値で埋める（Phase 54.9: Bug #1修正）
            self.logger.warning(
                "日時情報が見つかりません。時間特徴量を中立デフォルト値で生成します"
            )
            result_df["hour"] = 12  # 1日の中間（0→12）
            result_df["day_of_week"] = 3  # 週の中間・水曜日（0→3）
            result_df["is_market_open_hour"] = 0  # 変更なし
            result_df["is_europe_session"] = 0  # 変更なし
            result_df["hour_cos"] = 0.0  # 中立化（1.0→0.0）
            result_df["day_sin"] = 0.0  # 変更なし
            result_df["day_cos"] = 0.0  # 中立化（1.0→0.0）
            self.computed_features.update(
                [
                    "hour",
                    "day_of_week",
                    "is_market_open_hour",
                    "is_europe_session",
                    "hour_cos",
                    "day_sin",
                    "day_cos",
                ]
            )
            return result_df

        # Hour (0-23)
        result_df["hour"] = dt_index.hour
        self.computed_features.add("hour")

        # Day of week (0-6)
        result_df["day_of_week"] = dt_index.dayofweek
        self.computed_features.add("day_of_week")

        # Is market open hour (JST market hours)
        result_df["is_market_open_hour"] = (
            (dt_index.hour >= MARKET_OPEN_HOUR) & (dt_index.hour <= MARKET_CLOSE_HOUR)
        ).astype(int)
        self.computed_features.add("is_market_open_hour")

        # 欧州市場セッション（日をまたぐ処理）
        result_df["is_europe_session"] = (
            ((dt_index.hour >= EUROPE_SESSION_START) & (dt_index.hour <= EUROPE_SESSION_END_HOUR))
            | (dt_index.hour < EUROPE_SESSION_EARLY_HOUR)
        ).astype(int)
        self.computed_features.add("is_europe_session")

        # 時刻の周期性エンコーディング
        result_df["hour_cos"] = np.cos(2 * np.pi * dt_index.hour / HOURS_PER_DAY)
        self.computed_features.add("hour_cos")

        # 曜日の周期性エンコーディング
        result_df["day_sin"] = np.sin(2 * np.pi * dt_index.dayofweek / DAYS_PER_WEEK)
        result_df["day_cos"] = np.cos(2 * np.pi * dt_index.dayofweek / DAYS_PER_WEEK)
        self.computed_features.add("day_sin")
        self.computed_features.add("day_cos")

        self.logger.debug("時間ベース特徴量生成完了: 7個")
        return result_df

    def _get_strategy_signal_feature_names(self) -> Dict[str, str]:
        """
        戦略シグナル特徴量名を動的取得（設定駆動型）

        strategies.yamlから戦略リストを読み込み、特徴量名辞書を生成。
        これにより、戦略追加時に修正が不要になる。

        Returns:
            戦略名をキーとした特徴量名辞書
            例: {"ATRBased": "strategy_signal_ATRBased", ...}
        """
        from ..strategies.strategy_loader import StrategyLoader

        loader = StrategyLoader()
        strategies_data = loader.load_strategies()
        return {
            s["metadata"]["name"]: f"strategy_signal_{s['metadata']['name']}"
            for s in strategies_data
        }

    def _add_strategy_signal_features(
        self, df: pd.DataFrame, strategy_signals: Optional[Dict[str, Dict[str, float]]] = None
    ) -> pd.DataFrame:
        """
        戦略シグナル特徴量追加（Strategy Signals・設定駆動型・必ず追加）

        Args:
            df: 特徴量DataFrame
            strategy_signals: 戦略シグナル辞書（StrategyManager.get_individual_strategy_signals()の戻り値）
                例: {
                    "ATRBased": {"action": "buy", "confidence": 0.678, "encoded": 0.678},
                    "DonchianChannel": {"action": "sell", "confidence": 0.729, "encoded": -0.729},
                    ...
                }

        Returns:
            戦略シグナル特徴量が追加されたDataFrame（strategies.yamlから動的取得）

        Note:
            - Phase 52.4-B: 6戦略統合・設定駆動型（strategies.yamlから動的読み込み）
            - 確実な特徴量生成（strategy_signals=None時も0.0で追加）
            - MLが戦略の専門知識を学習可能に
            - 信頼性向上: 戦略数分必ず追加（後から追加しない）
        """
        result_df = df.copy()

        # 各戦略のシグナルを特徴量として追加（6戦略・設定駆動型）
        strategy_internal_names = self._get_strategy_signal_feature_names()
        num_strategies = len(strategy_internal_names)

        added_count = 0

        # strategy_signals=Noneの場合も処理を継続（0埋め）
        if not strategy_signals:
            self.logger.debug(
                f"戦略シグナル特徴量: strategy_signals未提供 → {num_strategies}個を0.5（中立HOLD）で生成（Phase 54.9: Bug #2修正）"
            )
            # 全戦略を0.5（中立HOLD）で追加（0.0→0.5: 極端SELL偏重バイアス排除）
            for internal_name, feature_name in strategy_internal_names.items():
                result_df[feature_name] = 0.5  # Phase 54.9: Bug #2修正（0.0→0.5）
                self.computed_features.add(feature_name)
            self.logger.debug(f"戦略シグナル特徴量生成完了: {num_strategies}個（0.5中立値）")
            return result_df

        # strategy_signalsが提供されている場合
        for internal_name, feature_name in strategy_internal_names.items():
            if internal_name in strategy_signals:
                # エンコード済み値を使用（buy=+1, hold=0, sell=-1 × confidence）
                encoded_value = strategy_signals[internal_name].get("encoded", 0.0)

                # DataFrameの最後の行に値を追加
                result_df[feature_name] = encoded_value
                self.computed_features.add(feature_name)
                added_count += 1
            else:
                # 戦略シグナルがない場合は0で補完
                result_df[feature_name] = 0.0
                self.computed_features.add(feature_name)
                self.logger.debug(f"戦略シグナル不足: {internal_name} → 0.0で補完")

        self.logger.debug(f"戦略シグナル特徴量生成完了: {added_count}/{num_strategies}個")
        return result_df

    def _calculate_rsi(self, close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
        """
        RSI計算

        Phase 55: GCPメモリ最適化
        - Series.where() → np.where() に置換（メモリ効率改善）
        - gVisor環境でのメモリフラグメンテーション回避
        """
        delta = close.diff()
        # Phase 55: メモリ効率化（pd.Series.where → np.where）
        delta_values = delta.values
        gain_values = np.where(delta_values > 0, delta_values, 0)
        loss_values = np.where(delta_values < 0, -delta_values, 0)

        gain = pd.Series(gain_values, index=delta.index).rolling(window=period, min_periods=1).mean()
        loss = pd.Series(loss_values, index=delta.index).rolling(window=period, min_periods=1).mean()
        rs = gain / (loss + EPSILON)
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, close: pd.Series) -> tuple:
        """MACD計算（MACDラインとシグナルラインを返す）"""
        ema_fast = close.ewm(span=MACD_FAST_PERIOD, adjust=False).mean()
        ema_slow = close.ewm(span=MACD_SLOW_PERIOD, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=MACD_SIGNAL_PERIOD, adjust=False).mean()
        return macd_line, macd_signal

    def _calculate_atr(self, df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
        """ATR計算"""
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=period, min_periods=1).mean()

    def _calculate_bb_bands(self, close: pd.Series, period: int = BB_PERIOD) -> tuple:
        """ボリンジャーバンド拡張（上限・下限・位置を返す）"""
        bb_middle = close.rolling(window=period, min_periods=1).mean()
        bb_std_dev = close.rolling(window=period, min_periods=1).std()
        bb_upper = bb_middle + (bb_std_dev * BB_STD_MULTIPLIER)
        bb_lower = bb_middle - (bb_std_dev * BB_STD_MULTIPLIER)
        bb_position = (close - bb_lower) / (bb_upper - bb_lower + EPSILON)
        return bb_upper, bb_lower, bb_position

    def _calculate_stochastic(
        self, df: pd.DataFrame, period: int = STOCHASTIC_PERIOD, smooth_k: int = STOCHASTIC_SMOOTH_K
    ) -> tuple:
        """Stochastic Oscillator計算 (%K, %D)"""
        low_min = df["low"].rolling(window=period, min_periods=1).min()
        high_max = df["high"].rolling(window=period, min_periods=1).max()

        # %K計算（Fast %K）
        stoch_k_fast = 100 * (df["close"] - low_min) / (high_max - low_min + EPSILON)

        # %K smoothing（Slow %K）
        stoch_k = stoch_k_fast.rolling(window=smooth_k, min_periods=1).mean()

        # %D計算（%Kの3期間SMA）
        stoch_d = stoch_k.rolling(window=STOCHASTIC_SMOOTH_D, min_periods=1).mean()

        return stoch_k, stoch_d

    def _calculate_volume_ema(
        self, volume: pd.Series, period: int = VOLUME_EMA_PERIOD
    ) -> pd.Series:
        """出来高EMA計算"""
        return volume.ewm(span=period, adjust=False).mean()

    def _calculate_atr_ratio(self, df: pd.DataFrame) -> pd.Series:
        """ATR/Close比率計算（ボラティリティ正規化）"""
        return df["atr_14"] / (df["close"] + EPSILON)

    def _calculate_volume_ratio(self, volume: pd.Series, period: Optional[int] = None) -> pd.Series:
        """出来高比率計算"""
        try:
            if period is None:
                period = get_anomaly_config("volume_ratio.calculation_period", VOLUME_EMA_PERIOD)
            volume_avg = volume.rolling(window=period, min_periods=1).mean()
            return volume / (volume_avg + EPSILON)
        except Exception as e:
            self.logger.error(f"出来高比率計算エラー: {e}")
            return pd.Series(np.zeros(len(volume)), index=volume.index)

    def _normalize(self, series: pd.Series) -> pd.Series:
        """0-1範囲に正規化"""
        try:
            # 外れ値処理（設定ファイルから取得）
            outlier_clip_quantile = get_anomaly_config("normalization.outlier_clip_quantile", 0.95)
            upper_bound = series.quantile(outlier_clip_quantile)
            clipped_series = np.clip(series, 0, upper_bound)

            # 0-1正規化
            min_val = clipped_series.min()
            max_val = clipped_series.max()

            if max_val - min_val == 0:
                return pd.Series(np.zeros(len(series)), index=series.index)

            return (clipped_series - min_val) / (max_val - min_val)

        except Exception:
            return pd.Series(np.zeros(len(series)), index=series.index)

    def _calculate_donchian_channel(self, df: pd.DataFrame, period: int = DONCHIAN_PERIOD) -> tuple:
        """
        Donchian Channel計算

        Args:
            df: OHLCV DataFrame
            period: 計算期間（デフォルト: DONCHIAN_PERIOD）

        Returns:
            (donchian_high, donchian_low, channel_position)
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            # 期間の最高値・最安値
            donchian_high = high.rolling(window=period, min_periods=1).max()
            donchian_low = low.rolling(window=period, min_periods=1).min()

            # チャネル内位置計算（0-1）
            channel_width = donchian_high - donchian_low
            channel_position = (close - donchian_low) / (channel_width + EPSILON)

            # Phase 53.6: GCP環境安定性向上（.copy()追加）
            donchian_high = donchian_high.bfill().fillna(high.iloc[0]).copy()
            donchian_low = donchian_low.bfill().fillna(low.iloc[0]).copy()
            channel_position = channel_position.fillna(0.5).copy()  # 中央値で補完

            return donchian_high, donchian_low, channel_position

        except Exception as e:
            self.logger.error(f"Donchian Channel計算エラー: {e}")
            # エラー時のフォールバック
            zeros = pd.Series(np.zeros(len(df)), index=df.index)
            half_ones = pd.Series(np.full(len(df), 0.5), index=df.index)
            return zeros, zeros, half_ones

    def _calculate_adx_indicators(self, df: pd.DataFrame, period: int = ADX_PERIOD) -> tuple:
        """
        ADX指標計算（ADX、+DI、-DI）

        Args:
            df: OHLCV DataFrame
            period: 計算期間（デフォルト: ADX_PERIOD）

        Returns:
            (adx, plus_di, minus_di)

        Phase 55: GCPメモリ最適化
        - pd.concat().max() → np.maximum() に置換（メモリ効率改善）
        - Series.where() → np.where() に置換
        - gVisor環境でのメモリフラグメンテーション回避
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            # True Range計算 - Phase 55: メモリ効率化（pd.concat().max → np.maximum）
            tr1 = (high - low).values
            tr2 = np.abs(high.values - close.shift(1).values)
            tr3 = np.abs(low.values - close.shift(1).values)
            # np.maximumはin-place的に動作し、中間DataFrameを作らない
            tr_values = np.maximum(np.maximum(tr1, tr2), tr3)
            tr = pd.Series(tr_values, index=df.index)

            # Directional Movement計算 - Phase 55: メモリ効率化（Series.where → np.where）
            high_diff = (high - high.shift(1)).values
            low_diff = (low.shift(1) - low).values

            # +DM計算（np.where使用）
            plus_dm_values = np.where(
                (high_diff > low_diff) & (high_diff > 0),
                high_diff,
                0
            )
            plus_dm = pd.Series(plus_dm_values, index=df.index)

            # -DM計算（np.where使用）
            minus_dm_values = np.where(
                (low_diff > high_diff) & (low_diff > 0),
                low_diff,
                0
            )
            minus_dm = pd.Series(minus_dm_values, index=df.index)

            # Smoothed True Range と Directional Movement
            atr = tr.rolling(window=period, min_periods=1).mean()
            plus_dm_smooth = plus_dm.rolling(window=period, min_periods=1).mean()
            minus_dm_smooth = minus_dm.rolling(window=period, min_periods=1).mean()

            # Directional Indicators
            plus_di = 100 * plus_dm_smooth / (atr + EPSILON)
            minus_di = 100 * minus_dm_smooth / (atr + EPSILON)

            # Directional Index
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + EPSILON)

            # ADX (Average Directional Index)
            adx = dx.rolling(window=period, min_periods=1).mean()

            # Phase 53.6: GCP環境安定性向上（.copy()追加）
            adx = adx.bfill().fillna(0).copy()
            plus_di = plus_di.bfill().fillna(0).copy()
            minus_di = minus_di.bfill().fillna(0).copy()

            return adx, plus_di, minus_di

        except Exception as e:
            self.logger.error(f"ADX指標計算エラー: {e}")
            # エラー時のフォールバック
            zeros = pd.Series(np.zeros(len(df)), index=df.index)
            return zeros, zeros, zeros

    def _handle_nan_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """NaN値処理（統合版）"""
        for feature in self.computed_features:
            if feature in df.columns:
                # Phase 53.6: GCP環境安定性向上（中間変数使用）
                temp_series = df[feature].ffill().bfill().fillna(0)
                df[feature] = temp_series
        return df

    def _validate_feature_generation(
        self, df: pd.DataFrame, expected_count: Optional[int] = None
    ) -> None:
        """
        特徴量完全確認・検証

        Args:
            df: 検証対象DataFrame
            expected_count: 期待特徴量数（デフォルト: get_feature_count()から自動取得）
        """
        if expected_count is None:
            expected_count = get_feature_count()
        generated_features = [col for col in OPTIMIZED_FEATURES if col in df.columns]
        missing_features = [col for col in OPTIMIZED_FEATURES if col not in df.columns]

        total_generated = len(generated_features)

        # 統合ログ出力
        self.logger.info(
            f"特徴量生成完了 - 総数: {total_generated}/{expected_count}個",
            extra_data={
                "basic_features": len([f for f in ["close", "volume"] if f in df.columns]),
                "technical_features": len(
                    [
                        f
                        for f in [
                            "rsi_14",
                            "macd",
                            "macd_signal",
                            "macd_histogram",
                            "atr_14",
                            "bb_upper",
                            "bb_lower",
                            "bb_position",
                            "ema_50",
                            "donchian_low_20",
                            "channel_position",
                            "adx_14",
                            "plus_di_14",
                            "minus_di_14",
                            "stoch_k",
                            "stoch_d",
                            "volume_ema",
                            "atr_ratio",
                        ]
                        if f in df.columns
                    ]
                ),
                "anomaly_features": len([f for f in ["volume_ratio"] if f in df.columns]),
                "lag_features": len([f for f in df.columns if "lag" in f]),
                "rolling_features": len(
                    [f for f in df.columns if any(kw in f for kw in ["_ma_", "_std_"])]
                ),
                "interaction_features": len([f for f in df.columns if "_x_" in f]),
                "time_features": len(
                    [
                        f
                        for f in [
                            "hour",
                            "day_of_week",
                            "is_market_open_hour",
                            "is_europe_session",
                            "hour_cos",
                            "day_sin",
                            "day_cos",
                        ]
                        if f in df.columns
                    ]
                ),
                "generated_features": generated_features,
                "missing_features": missing_features,
                "total_expected": expected_count,
                "success": total_generated >= expected_count,
            },
        )

        # 不足特徴量の警告
        if missing_features:
            self.logger.warning(
                f"🚨 特徴量不足検出: {missing_features} ({len(missing_features)}個不足)"
            )

        # 特徴量完全生成確認
        if total_generated == expected_count:
            self.logger.info(f"✅ {expected_count}特徴量完全生成成功")

    def get_feature_info(self) -> Dict[str, Any]:
        """特徴量情報取得"""
        return {
            "total_features": len(self.computed_features),
            "computed_features": sorted(list(self.computed_features)),
            "feature_categories": FEATURE_CATEGORIES,
            "optimized_features": OPTIMIZED_FEATURES,
            "parameters": {"lookback_period": self.lookback_period},
            "feature_descriptions": {
                "close": "終値（基準価格）",
                "volume": "出来高（市場活動度）",
                "rsi_14": "RSI（オーバーボート・ソールド判定）",
                "macd": "MACD（トレンド転換シグナル）",
                "atr_14": "ATR（ボラティリティ測定）",
                "bb_position": "ボリンジャーバンド位置（価格位置）",
                "ema_20": "EMA短期（短期トレンド）",
                "ema_50": "EMA中期（中期トレンド）",
                "donchian_high_20": "Donchian Channel上限（20期間最高値）",
                "donchian_low_20": "Donchian Channel下限（20期間最安値）",
                "channel_position": "チャネル内位置（0-1正規化位置）",
                "adx_14": "ADX（トレンド強度指標）",
                "plus_di_14": "+DI（上昇トレンド方向性）",
                "minus_di_14": "-DI（下降トレンド方向性）",
                "volume_ratio": "出来高比率（出来高異常検知）",
            },
        }


# エクスポートリスト
__all__ = [
    "FeatureGenerator",
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
]
