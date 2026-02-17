"""
特徴量生成統合システム - 55特徴量固定（49基本 + 6戦略シグナル）

TechnicalIndicators、MarketAnomalyDetector、FeatureServiceAdapterを
1つのクラスに統合。6戦略対応・設定駆動型特徴量生成。
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..core.config import get_anomaly_config

# Phase 38.4: 特徴量定義一元化（feature_managerから取得）
from ..core.config.feature_manager import get_feature_categories, get_feature_names
from ..core.exceptions import DataProcessingError
from ..core.logger import CryptoBotLogger, get_logger

# 特徴量リスト（一元化対応）
OPTIMIZED_FEATURES = get_feature_names()

# 特徴量カテゴリ（一元化対応）
FEATURE_CATEGORIES = get_feature_categories()


class FeatureGenerator:
    """
    統合特徴量生成クラス - 55特徴量固定（49基本 + 6戦略シグナル）

    特徴量構成:
    - 基本（2個）: close, volume
    - テクニカル指標（17個）: RSI, MACD拡張, ATR, BB拡張, EMA, Donchian, ADX, Stochastic, volume_ema, atr_ratio
    - 異常検知（1個）: volume_ratio
    - ラグ（9個）: Close/Volume/RSI/MACD lag
    - 移動統計量（5個）: MA, Std
    - 交互作用（5個）: RSI×ATR, MACD×Volume等
    - 時間（7個）: hour, day_of_week, is_market_open_hour, is_europe_session, hour_cos, day_sin, day_cos
    - 戦略シグナル（6個）: 6戦略の判断エンコード（設定駆動型・strategies.yamlから動的取得）
    - NaN時は0埋め、strategy_signals=None時も6個を0.0で生成
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

    def _run_feature_pipeline(
        self,
        result_df: pd.DataFrame,
        strategy_signals: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> pd.DataFrame:
        """共通特徴量生成パイプライン（49基本 + 6戦略シグナル = 55特徴量）"""
        self._validate_required_columns(result_df)
        result_df = self._generate_basic_features(result_df)
        result_df = self._generate_technical_indicators(result_df)
        result_df = self._generate_anomaly_indicators(result_df)
        result_df = self._generate_lag_features(result_df)
        result_df = self._generate_rolling_statistics(result_df)
        result_df = self._generate_interaction_features(result_df)
        result_df = self._generate_time_features(result_df)
        result_df = self._add_strategy_signal_features(result_df, strategy_signals)
        result_df = self._handle_nan_values(result_df)
        return result_df

    async def generate_features(
        self,
        market_data: Dict[str, Any],
        strategy_signals: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> pd.DataFrame:
        """
        統合特徴量生成処理（55特徴量固定: 49基本 + 6戦略シグナル）

        Args:
            market_data: 市場データ（DataFrame または dict）
            strategy_signals: 戦略シグナル辞書（オプション、None時は0埋め）

        Returns:
            特徴量を含むDataFrame（55特徴量固定）

        Raises:
            DataProcessingError: 特徴量生成エラー
        """
        try:
            result_df = self._convert_to_dataframe(market_data)
            self.computed_features.clear()
            result_df = self._run_feature_pipeline(result_df, strategy_signals)
            self._validate_feature_generation(result_df, expected_count=55)
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
        同期版特徴量生成（55特徴量固定・バックテスト事前計算用）

        Args:
            df: OHLCVデータを含むDataFrame
            strategy_signals: 戦略シグナル辞書（オプション、None時は0埋め）

        Returns:
            特徴量を含むDataFrame（55特徴量固定）
        """
        try:
            result_df = df.copy()
            result_df = self._run_feature_pipeline(result_df, strategy_signals)
            return result_df

        except Exception as e:
            self.logger.error(f"同期版特徴量生成エラー: {e}")
            raise DataProcessingError(f"同期版特徴量生成失敗: {e}")

    def _convert_to_dataframe(self, market_data: Dict[str, Any]) -> pd.DataFrame:
        """市場データをDataFrameに変換（タイムフレーム辞書対応）"""
        if isinstance(market_data, pd.DataFrame):
            return market_data.copy()
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
        """テクニカル指標生成（21個）"""
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

        # EMA 2本（20/50期間）- Phase 51.7 Day 7: ema_20復活（MACDEMACrossover必須）
        result_df["ema_20"] = result_df["close"].ewm(span=20, adjust=False).mean()
        result_df["ema_50"] = result_df["close"].ewm(span=50, adjust=False).mean()
        self.computed_features.update(["ema_20", "ema_50"])

        # Donchian Channel指標（3個）- Phase 51.7 Day 7: donchian_high_20復活（DonchianChannel必須）
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

        self.logger.debug("異常検知指標生成完了: 2個")
        return result_df

    def _generate_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ラグ特徴量生成（過去N期間の値・7個・Phase 51.7 Day 2削減）"""
        result_df = df.copy()

        # Close lag features (4個・close_lag_5削除: Importance=1.0と低い)
        for lag in [1, 2, 3, 10]:
            result_df[f"close_lag_{lag}"] = result_df["close"].shift(lag)
            self.computed_features.add(f"close_lag_{lag}")

        # Volume lag features (3個・全保持: volume_lag_2が最重要!)
        for lag in [1, 2, 3]:
            result_df[f"volume_lag_{lag}"] = result_df["volume"].shift(lag)
            self.computed_features.add(f"volume_lag_{lag}")

        # RSI lag feature (1個)
        if "rsi_14" in result_df.columns:
            result_df["rsi_lag_1"] = result_df["rsi_14"].shift(1)
            self.computed_features.add("rsi_lag_1")

        # MACD lag feature (1個)
        if "macd" in result_df.columns:
            result_df["macd_lag_1"] = result_df["macd"].shift(1)
            self.computed_features.add("macd_lag_1")

        self.logger.debug("ラグ特徴量生成完了: 9個（Phase 51.7 Day 2削減）")
        return result_df

    def _generate_rolling_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """移動統計量生成（Rolling Statistics・5個・Phase 51.7 Day 2削減）"""
        result_df = df.copy()

        # Moving Average (2個・close_ma_5削除: Importance=0)
        for window in [10, 20]:
            result_df[f"close_ma_{window}"] = (
                result_df["close"].rolling(window=window, min_periods=1).mean()
            )
            self.computed_features.add(f"close_ma_{window}")

        # Standard Deviation (3個・全保持: Importance=16/12/5と非常に高い！)
        for window in [5, 10, 20]:
            result_df[f"close_std_{window}"] = (
                result_df["close"].rolling(window=window, min_periods=1).std()
            )
            self.computed_features.add(f"close_std_{window}")

        self.logger.debug("移動統計量生成完了: 5個")
        return result_df

    def _generate_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """交互作用特徴量生成（Feature Interactions・5個・Phase 51.7 Day 2削減）"""
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

        self.logger.debug("交互作用特徴量生成完了: 5個（Phase 51.7 Day 2削減）")
        return result_df

    def _generate_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """時間ベース特徴量生成（Time-based Features・8個・Phase 51.7 Day 2削減）"""
        result_df = df.copy()

        # indexまたはtimestamp列から日時情報を抽出
        if isinstance(result_df.index, pd.DatetimeIndex):
            dt_index = result_df.index
        elif "timestamp" in result_df.columns:
            # SeriesをDatetimeIndexに変換（.hour等のアクセスを可能にする）
            dt_index = pd.DatetimeIndex(pd.to_datetime(result_df["timestamp"]))
        else:
            # 日時情報がない場合はゼロ埋め（削減後の8特徴量のみ）
            self.logger.warning("日時情報が見つかりません。時間特徴量をデフォルト値で生成します")
            result_df["hour"] = 0
            result_df["day_of_week"] = 0
            result_df["is_market_open_hour"] = 0
            # Phase 51.7: 欧州セッションのみ保持（is_asia/us削除: Importance=0）
            result_df["is_europe_session"] = 0
            result_df["hour_cos"] = 1.0
            result_df["day_sin"] = 0.0
            result_df["day_cos"] = 1.0
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

        # Is market open hour (9-15時JST: 1, それ以外: 0)
        result_df["is_market_open_hour"] = ((dt_index.hour >= 9) & (dt_index.hour <= 15)).astype(
            int
        )
        self.computed_features.add("is_market_open_hour")

        # 欧州市場セッション（JST 16:00-01:00）- 日をまたぐ処理
        result_df["is_europe_session"] = (
            ((dt_index.hour >= 16) & (dt_index.hour <= 23)) | (dt_index.hour < 1)
        ).astype(int)
        self.computed_features.add("is_europe_session")

        # 周期性エンコーディング
        result_df["hour_cos"] = np.cos(2 * np.pi * dt_index.hour / 24)
        self.computed_features.add("hour_cos")

        # 曜日の周期性エンコーディング（7日サイクル・全保持: day_sin=7と高い）
        result_df["day_sin"] = np.sin(2 * np.pi * dt_index.dayofweek / 7)
        result_df["day_cos"] = np.cos(2 * np.pi * dt_index.dayofweek / 7)
        self.computed_features.add("day_sin")
        self.computed_features.add("day_cos")

        self.logger.debug("時間ベース特徴量生成完了: 7個（Phase 51.7 Day 2削減）")
        return result_df

    def _get_strategy_signal_feature_names(self) -> Dict[str, str]:
        """
        Phase 51.7 Day 7: 戦略シグナル特徴量名を動的取得（設定駆動型）

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
        Phase 51.7 Day 7: 戦略シグナル特徴量追加（Strategy Signals・設定駆動型・必ず追加）

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
            - Phase 51.7 Day 7: 6戦略統合・設定駆動型（strategies.yamlから動的読み込み）
            - Phase 50.1: 確実な特徴量生成（strategy_signals=None時も0.0で追加）
            - Phase 41: Strategy-Aware ML実装
            - MLが戦略の専門知識を学習可能に
            - 信頼性向上: 戦略数分必ず追加（後から追加しない）
            - ⚠️ Phase 51.7 Day 1発見: 既存戦略信号はImportance=0（Phase 51.8以降で改善検討）
        """
        result_df = df.copy()

        # 各戦略のシグナルを特徴量として追加（Phase 51.7 Day 7: 6戦略・設定駆動型）
        strategy_internal_names = self._get_strategy_signal_feature_names()
        num_strategies = len(strategy_internal_names)

        added_count = 0

        # Phase 50.1: strategy_signals=Noneの場合も処理を継続（0埋め）
        if not strategy_signals:
            self.logger.debug(
                f"戦略シグナル特徴量: strategy_signals未提供 → {num_strategies}個を0.0で生成（確実）"
            )
            # 全戦略を0.0で追加
            for internal_name, feature_name in strategy_internal_names.items():
                result_df[feature_name] = 0.0
                self.computed_features.add(feature_name)
            self.logger.debug(f"戦略シグナル特徴量生成完了: {num_strategies}個（0埋め）")
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

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """RSI計算"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        rs = gain / (loss + 1e-8)
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, close: pd.Series) -> tuple:
        """MACD計算（MACDラインとシグナルラインを返す）"""
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        return macd_line, macd_signal

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR計算"""
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=period, min_periods=1).mean()

    def _calculate_bb_bands(self, close: pd.Series, period: int = 20) -> tuple:
        """ボリンジャーバンド拡張（上限・下限・位置を返す）"""
        bb_middle = close.rolling(window=period, min_periods=1).mean()
        bb_std_dev = close.rolling(window=period, min_periods=1).std()
        bb_upper = bb_middle + (bb_std_dev * 2)
        bb_lower = bb_middle - (bb_std_dev * 2)
        bb_position = (close - bb_lower) / (bb_upper - bb_lower + 1e-8)
        return bb_upper, bb_lower, bb_position

    def _calculate_stochastic(self, df: pd.DataFrame, period: int = 14, smooth_k: int = 3) -> tuple:
        """Stochastic Oscillator計算 (%K, %D)"""
        low_min = df["low"].rolling(window=period, min_periods=1).min()
        high_max = df["high"].rolling(window=period, min_periods=1).max()

        # %K計算（Fast %K）
        stoch_k_fast = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-8)

        # %K smoothing（Slow %K）
        stoch_k = stoch_k_fast.rolling(window=smooth_k, min_periods=1).mean()

        # %D計算（%Kの3期間SMA）
        stoch_d = stoch_k.rolling(window=3, min_periods=1).mean()

        return stoch_k, stoch_d

    def _calculate_volume_ema(self, volume: pd.Series, period: int = 20) -> pd.Series:
        """出来高EMA計算"""
        return volume.ewm(span=period, adjust=False).mean()

    def _calculate_atr_ratio(self, df: pd.DataFrame) -> pd.Series:
        """ATR/Close比率計算（ボラティリティ正規化）"""
        return df["atr_14"] / (df["close"] + 1e-8)

    def _calculate_volume_ratio(self, volume: pd.Series, period: Optional[int] = None) -> pd.Series:
        """出来高比率計算"""
        try:
            if period is None:
                period = get_anomaly_config("volume_ratio.calculation_period", 20)
            volume_avg = volume.rolling(window=period, min_periods=1).mean()
            return volume / (volume_avg + 1e-8)
        except Exception as e:
            self.logger.error(f"出来高比率計算エラー: {e}")
            return pd.Series(np.zeros(len(volume)), index=volume.index)

    def _calculate_donchian_channel(self, df: pd.DataFrame, period: int = 20) -> tuple:
        """
        Donchian Channel計算

        Args:
            df: OHLCV DataFrame
            period: 計算期間（デフォルト: 20）

        Returns:
            (donchian_high, donchian_low, channel_position)
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            # 20期間の最高値・最安値
            donchian_high = high.rolling(window=period, min_periods=1).max()
            donchian_low = low.rolling(window=period, min_periods=1).min()

            # チャネル内位置計算（0-1）
            channel_width = donchian_high - donchian_low
            channel_position = (close - donchian_low) / (channel_width + 1e-8)

            # NaN値を適切な値で補完
            donchian_high = donchian_high.bfill().fillna(high.iloc[0])
            donchian_low = donchian_low.bfill().fillna(low.iloc[0])
            channel_position = channel_position.fillna(0.5)  # 中央値で補完

            return donchian_high, donchian_low, channel_position

        except Exception as e:
            self.logger.error(f"Donchian Channel計算エラー: {e}")
            # エラー時のフォールバック
            zeros = pd.Series(np.zeros(len(df)), index=df.index)
            half_ones = pd.Series(np.full(len(df), 0.5), index=df.index)
            return zeros, zeros, half_ones

    def _calculate_adx_indicators(self, df: pd.DataFrame, period: int = 14) -> tuple:
        """
        ADX指標計算（ADX、+DI、-DI）

        Args:
            df: OHLCV DataFrame
            period: 計算期間（デフォルト: 14）

        Returns:
            (adx, plus_di, minus_di)
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            # True Range計算
            tr1 = high - low
            tr2 = np.abs(high - close.shift(1))
            tr3 = np.abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Directional Movement計算
            plus_dm = (high - high.shift(1)).where((high - high.shift(1)) > (low.shift(1) - low), 0)
            minus_dm = (low.shift(1) - low).where((low.shift(1) - low) > (high - high.shift(1)), 0)
            plus_dm = plus_dm.where(plus_dm > 0, 0)
            minus_dm = minus_dm.where(minus_dm > 0, 0)

            # Smoothed True Range と Directional Movement
            atr = tr.rolling(window=period, min_periods=1).mean()
            plus_dm_smooth = plus_dm.rolling(window=period, min_periods=1).mean()
            minus_dm_smooth = minus_dm.rolling(window=period, min_periods=1).mean()

            # Directional Indicators
            plus_di = 100 * plus_dm_smooth / (atr + 1e-8)
            minus_di = 100 * minus_dm_smooth / (atr + 1e-8)

            # Directional Index
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)

            # ADX (Average Directional Index)
            adx = dx.rolling(window=period, min_periods=1).mean()

            # NaN値補完
            adx = adx.bfill().fillna(0)
            plus_di = plus_di.bfill().fillna(0)
            minus_di = minus_di.bfill().fillna(0)

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
                # pandas 2.x互換性: チェーン代入を2行に分割
                df[feature] = df[feature].ffill().bfill()
                df[feature] = df[feature].fillna(0)
        return df

    def _validate_feature_generation(self, df: pd.DataFrame, expected_count: int = 55) -> None:
        """
        特徴量完全確認・検証 - Phase 51.7 Day 7: 55特徴量固定

        Args:
            df: 検証対象DataFrame
            expected_count: 期待特徴量数（55固定）
        """
        generated_features = [col for col in OPTIMIZED_FEATURES if col in df.columns]
        missing_features = [col for col in OPTIMIZED_FEATURES if col not in df.columns]

        total_generated = len(generated_features)
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

        if missing_features:
            self.logger.warning(
                f"特徴量不足検出: {missing_features} ({len(missing_features)}個不足)"
            )

        if total_generated == expected_count:
            self.logger.info(f"55特徴量完全生成成功")

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
