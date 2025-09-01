"""
統一市場データクラス - データ型統一とパフォーマンス最適化

DataFrameと辞書形式の両方をサポートする統一的な
市場データ構造を提供し、型安全性を向上させる。

Phase 16-A実装: データ型統一
実装日: 2025年8月29日
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from .exceptions import DataProcessingError
from .logger import get_logger


@dataclass
class OHLCVRecord:
    """
    単一時点のOHLCVデータ

    高速なアクセスが必要な場合やAPIレスポンスで使用。
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OHLCVRecord":
        """辞書から作成."""
        return cls(
            timestamp=(
                data["timestamp"]
                if isinstance(data["timestamp"], datetime)
                else pd.to_datetime(data["timestamp"])
            ),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=float(data["volume"]),
        )


class MarketDataBase(ABC):
    """
    市場データベースクラス

    DataFrame形式と辞書形式の両方のインターフェースを
    提供する抽象基底クラス。
    """

    def __init__(self, symbol: str = "BTC/JPY"):
        """
        初期化

        Args:
            symbol: 通貨ペア
        """
        self.symbol = symbol
        self.logger = get_logger()
        self._df_cache: Optional[pd.DataFrame] = None
        self._records_cache: Optional[List[OHLCVRecord]] = None

    @abstractmethod
    def to_dataframe(self) -> pd.DataFrame:
        """DataFrameとして取得."""
        pass

    @abstractmethod
    def to_records(self) -> List[OHLCVRecord]:
        """レコードリストとして取得."""
        pass

    @abstractmethod
    def get_latest(self) -> OHLCVRecord:
        """最新データを取得."""
        pass

    def __len__(self) -> int:
        """データ長を取得."""
        return len(self.to_dataframe())

    def is_empty(self) -> bool:
        """空データかどうか."""
        return len(self) == 0


class BasicMarketData(MarketDataBase):
    """
    基本市場データクラス

    OHLCV基本情報のみを含むシンプルな市場データ。
    高速アクセスが必要な場面で使用。
    """

    def __init__(
        self,
        symbol: str = "BTC/JPY",
        data: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]] = None,
    ):
        """
        初期化

        Args:
            symbol: 通貨ペア
            data: 初期データ（DataFrame or dict list）
        """
        super().__init__(symbol)
        self._raw_data: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]] = data
        self._validated = False

    def to_dataframe(self) -> pd.DataFrame:
        """DataFrameとして取得."""
        if self._df_cache is not None:
            return self._df_cache.copy()

        if self._raw_data is None:
            return pd.DataFrame()

        try:
            if isinstance(self._raw_data, pd.DataFrame):
                df = self._raw_data.copy()
            else:
                # List[Dict]からDataFrameを作成
                df = pd.DataFrame(self._raw_data)
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df.set_index("timestamp", inplace=True)

            # 必要列の検証
            required_cols = ["open", "high", "low", "close", "volume"]
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise DataProcessingError(f"必要な列が不足: {missing}")

            # データ型変換
            for col in required_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # キャッシュ
            self._df_cache = df.copy()
            self._validated = True

            return df

        except Exception as e:
            self.logger.error(f"DataFrameへの変換に失敗: {e}")
            return pd.DataFrame()

    def to_records(self) -> List[OHLCVRecord]:
        """レコードリストとして取得."""
        if self._records_cache is not None:
            return self._records_cache.copy()

        try:
            df = self.to_dataframe()
            if df.empty:
                return []

            records = []
            for idx, row in df.iterrows():
                record = OHLCVRecord(
                    timestamp=idx if isinstance(idx, datetime) else pd.to_datetime(idx),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
                records.append(record)

            # キャッシュ
            self._records_cache = records.copy()
            return records

        except Exception as e:
            self.logger.error(f"レコードリストへの変換に失敗: {e}")
            return []

    def get_latest(self) -> OHLCVRecord:
        """最新データを取得."""
        records = self.to_records()
        if not records:
            raise DataProcessingError("データが存在しません")

        return records[-1]

    def get_price_range(self) -> Dict[str, float]:
        """価格レンジ情報を取得."""
        try:
            df = self.to_dataframe()
            if df.empty:
                return {}

            return {
                "min_price": float(df["low"].min()),
                "max_price": float(df["high"].max()),
                "avg_price": float(df["close"].mean()),
                "current_price": float(df["close"].iloc[-1]),
                "price_change": float(df["close"].iloc[-1] - df["close"].iloc[0]),
                "price_change_pct": float((df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100),
            }

        except Exception as e:
            self.logger.error(f"価格レンジ計算に失敗: {e}")
            return {}


class EnrichedMarketData(BasicMarketData):
    """
    拡張市場データクラス

    OHLCV + テクニカル指標を含む完全な市場データ。
    戦略分析で使用される主要クラス。
    """

    def __init__(
        self,
        symbol: str = "BTC/JPY",
        data: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]] = None,
        features: Optional[List[str]] = None,
    ):
        """
        初期化

        Args:
            symbol: 通貨ペア
            data: 基本データ
            features: 利用可能な特徴量リスト
        """
        super().__init__(symbol, data)
        self.available_features = features or []
        self._feature_values: Dict[str, np.ndarray] = {}

    def add_features(self, features: Dict[str, Union[np.ndarray, pd.Series, List[float]]]) -> None:
        """
        特徴量を追加

        Args:
            features: 特徴量辞書 {feature_name: values}
        """
        try:
            df = self.to_dataframe()
            if df.empty:
                self.logger.warning("基本データが空のため特徴量を追加できません")
                return

            for name, values in features.items():
                # 値の型を統一
                if isinstance(values, pd.Series):
                    values_array = values.values
                elif isinstance(values, list):
                    values_array = np.array(values)
                else:
                    values_array = np.array(values)

                # 長さチェック
                if len(values_array) != len(df):
                    self.logger.warning(
                        f"特徴量 {name} の長さが不一致: {len(values_array)} vs {len(df)}"
                    )
                    continue

                self._feature_values[name] = values_array
                if name not in self.available_features:
                    self.available_features.append(name)

            # キャッシュクリア（特徴量追加により無効化）
            self._df_cache = None

            self.logger.debug(f"特徴量追加完了: {list(features.keys())}")

        except Exception as e:
            self.logger.error(f"特徴量追加に失敗: {e}")
            raise DataProcessingError(f"特徴量追加エラー: {e}")

    def to_dataframe(self) -> pd.DataFrame:
        """特徴量付きDataFrameとして取得."""
        if self._df_cache is not None:
            return self._df_cache.copy()

        # 基本データを取得
        df = super().to_dataframe()
        if df.empty:
            return df

        try:
            # 特徴量を追加
            for name, values in self._feature_values.items():
                if len(values) == len(df):
                    df[name] = values
                else:
                    self.logger.warning(f"特徴量 {name} をスキップ（長さ不一致）")

            # キャッシュ
            self._df_cache = df.copy()
            return df

        except Exception as e:
            self.logger.error(f"拡張DataFrameの作成に失敗: {e}")
            return super().to_dataframe()  # 基本データのみ返す

    def get_feature_vector(self, feature_names: Optional[List[str]] = None) -> np.ndarray:
        """
        特徴量ベクトルを取得

        Args:
            feature_names: 取得する特徴量名リスト（None=全て）

        Returns:
            特徴量ベクトル（最新データポイント）
        """
        try:
            df = self.to_dataframe()
            if df.empty:
                return np.array([])

            # 使用する特徴量を決定
            if feature_names is None:
                feature_names = self.available_features

            # 存在する特徴量のみ使用
            valid_features = [f for f in feature_names if f in df.columns]
            if not valid_features:
                self.logger.warning("有効な特徴量が見つかりません")
                return np.array([])

            # 最新行の特徴量ベクトル
            feature_vector = df[valid_features].iloc[-1].values

            # NaN値のチェック
            if np.any(np.isnan(feature_vector)):
                self.logger.warning("特徴量ベクトルにNaN値が含まれています")
                feature_vector = np.nan_to_num(feature_vector, nan=0.0)

            return feature_vector

        except Exception as e:
            self.logger.error(f"特徴量ベクトルの取得に失敗: {e}")
            return np.array([])

    def get_feature_summary(self) -> Dict[str, Dict[str, float]]:
        """特徴量の統計サマリーを取得."""
        try:
            df = self.to_dataframe()
            if df.empty or not self.available_features:
                return {}

            summary = {}
            for feature in self.available_features:
                if feature in df.columns:
                    series = df[feature]
                    summary[feature] = {
                        "mean": float(series.mean()),
                        "std": float(series.std()),
                        "min": float(series.min()),
                        "max": float(series.max()),
                        "latest": float(series.iloc[-1]),
                        "null_ratio": float(series.isnull().sum() / len(series)),
                    }

            return summary

        except Exception as e:
            self.logger.error(f"特徴量サマリー取得に失敗: {e}")
            return {}


def create_market_data(
    data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]],
    symbol: str = "BTC/JPY",
    with_features: bool = False,
) -> MarketDataBase:
    """
    ファクトリー関数：適切なMarketDataクラスを作成

    Args:
        data: 市場データ
        symbol: 通貨ペア
        with_features: 特徴量付きクラスを使用するか

    Returns:
        適切なMarketDataインスタンス
    """
    try:
        # データ形式の統一
        if isinstance(data, dict):
            data = [data]  # 単一レコードをリスト化

        # クラス選択
        if with_features:
            return EnrichedMarketData(symbol=symbol, data=data)
        else:
            return BasicMarketData(symbol=symbol, data=data)

    except Exception as e:
        logger = get_logger()
        logger.error(f"MarketData作成に失敗: {e}")
        # 空のデータで安全なインスタンスを返す
        return BasicMarketData(symbol=symbol, data=None)
