"""
Fear&Greed指数データフェッチャー
複数データソース・キャッシュ機能・フォールバック機能対応
ChatGPTアドバイス反映版：段階的・品質重視アプローチ
MultiSourceDataFetcher継承版 - Phase2統合実装
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
import requests

from ..utils.api_retry import api_retry
from .multi_source_fetcher import MultiSourceDataFetcher

logger = logging.getLogger(__name__)


class FearGreedDataFetcher(MultiSourceDataFetcher):
    """Fear&Greed指数データ取得クラス（複数データソース・キャッシュ対応）"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 親クラス初期化
        super().__init__(config, data_type="fear_greed")

        # Fear&Greed特有設定
        self.api_url = self.data_config.get("url", "https://api.alternative.me/fng/")
        self.backup_url = self.data_config.get(
            "backup_url", "https://api.alternative.me/fng/?limit=365"
        )
        self.fallback_days = self.data_config.get("fallback_days", 7)

        logger.info(
            "🔧 Fear&Greed Fetcher initialized with MultiSourceDataFetcher base"
        )

    def _validate_data_quality(self, data: pd.DataFrame) -> float:
        """データ品質検証（MultiSourceDataFetcher抽象メソッド実装）"""
        if data is None or data.empty:
            return 0.0

        # 品質評価指標
        total_points = len(data)
        valid_points = len(data.dropna())

        if total_points == 0:
            return 0.0

        # Fear&Greed特有の検証
        range_score = 0.0
        if "value" in data.columns:
            # 値が0-100の範囲内かチェック
            valid_range = ((data["value"] >= 0) & (data["value"] <= 100)).sum()
            range_score = valid_range / total_points

        # 総合品質スコア
        quality_score = (valid_points / total_points) * 0.7 + range_score * 0.3
        logger.debug(
            f"📊 Fear&Greed data quality: {quality_score:.3f} "
            f"(valid: {valid_points}/{total_points}, range: {range_score:.3f})"
        )

        return quality_score

    def _generate_trend_fallback(
        self, last_value: float, days: int = 7
    ) -> pd.DataFrame:
        """前日値トレンド推定フォールバック"""
        try:
            # 簡単なトレンド推定（市場が不安定な場合は恐怖指数が上昇傾向）
            base_value = last_value if last_value > 0 else 50.0

            # 過去7日分のデータを生成
            dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

            # 軽微な変動を加えた推定値
            import numpy as np

            values = []
            for _i in range(days):
                # 前日比±5%程度の変動
                variation = base_value * 0.05 * (0.5 - np.random.random())
                estimated_value = base_value + variation
                # 0-100の範囲に制限
                estimated_value = max(0, min(100, estimated_value))
                values.append(estimated_value)
                base_value = estimated_value

            fallback_data = pd.DataFrame(
                {
                    "timestamp": dates,
                    "value": values,
                    "value_classification": ["Neutral"] * days,
                }
            )

            logger.info(
                f"📈 Generated Fear&Greed trend fallback: {days} days, "
                f"base_value={last_value}"
            )
            return fallback_data

        except Exception as e:
            logger.error(f"❌ Failed to generate trend fallback: {e}")
            return pd.DataFrame()

    def get_fear_greed_data(
        self, limit: int = 30, days_back: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fear&Greedデータ取得（MultiSourceDataFetcher統合版）

        Args:
            limit: 取得するデータ数
            days_back: 過去何日分のデータを取得するか（limitと同等）

        Returns:
            Fear&GreedデータのDataFrame
        """
        # days_backが指定されている場合はlimitとして使用
        if days_back is not None:
            limit = days_back

        # 親クラスのget_dataメソッドを呼び出し
        return self.get_data(limit=limit)

    def _fetch_data_from_source(
        self, source_name: str, **kwargs
    ) -> Optional[pd.DataFrame]:
        """特定データソースからデータ取得（MultiSourceDataFetcher抽象メソッド実装）"""
        limit = kwargs.get("limit", 30)

        if source_name == "alternative_me":
            return self._fetch_alternative_me(limit)
        elif source_name == "cnn_fear_greed":
            return self._fetch_cnn_fear_greed(limit)
        else:
            logger.warning(f"Unknown Fear&Greed data source: {source_name}")
            return None

    def _generate_fallback_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """フォールバックデータ生成（MultiSourceDataFetcher抽象メソッド実装）"""
        # 最後の既知の値を使用してトレンド推定
        last_value = 50.0  # デフォルト値（中立）

        # グローバルキャッシュから最新データを試行取得
        try:
            cache_key = self._get_cache_key(limit=1)
            cached_data = self.global_cache.get(cache_key)
            if (
                cached_data is not None
                and not cached_data.empty
                and "value" in cached_data.columns
            ):
                last_value = cached_data["value"].iloc[-1]
                logger.debug(
                    f"📋 Using cached Fear&Greed value for fallback: {last_value}"
                )
        except Exception:
            logger.debug("⚠️ No cached Fear&Greed data for fallback, using default")

        fallback_data = self._generate_trend_fallback(last_value, self.fallback_days)

        if not fallback_data.empty:
            logger.info(
                f"✅ Generated Fear&Greed fallback data: {len(fallback_data)} records"
            )
            return fallback_data

        return None

    @api_retry(max_retries=3, base_delay=2.0, circuit_breaker=True)
    def _fetch_alternative_me(self, limit: int) -> Optional[pd.DataFrame]:
        """Alternative.me APIからFear&Greedデータ取得（Cloud Run対応）"""
        try:
            # Phase H.17: Cloud Run環境でのリクエスト最適化
            import os

            is_cloud_run = os.getenv("K_SERVICE") is not None

            # ヘッダー設定（User-Agent追加）
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; CryptoBot/1.0; +https://github.com/crypto-bot)",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            }

            params = {"limit": limit}

            # Cloud Run環境では長めのタイムアウト
            timeout = 30 if is_cloud_run else 10

            if is_cloud_run:
                logger.info(f"🌐 Cloud Run environment: using timeout={timeout}s")

            response = requests.get(
                self.api_url, params=params, headers=headers, timeout=timeout
            )

            logger.info(f"📡 Alternative.me response status: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            if "data" not in data:
                raise ValueError("No Fear&Greed data in response")

            # DataFrameに変換
            fg_data = pd.DataFrame(data["data"])
            fg_data["timestamp"] = pd.to_datetime(fg_data["timestamp"], unit="s")
            fg_data["value"] = pd.to_numeric(fg_data["value"])
            fg_data = fg_data.sort_values("timestamp").set_index("timestamp")

            return fg_data

        except Exception as e:
            logger.error(f"Alternative.me Fear&Greed fetch failed: {e}")
            raise

    @api_retry(max_retries=3, base_delay=2.0, circuit_breaker=True)
    def _fetch_cnn_fear_greed(self, limit: int) -> Optional[pd.DataFrame]:
        """CNN Fear&Greedデータ取得（代替実装）"""
        try:
            # CNN Fear&Greed API実装（簡略版）
            # 実際の実装では、CNN Business APIまたはスクレイピングが必要
            # 現在は Alternative.me のバックアップURLを使用
            logger.info(
                "📡 Using Alternative.me backup URL as CNN Fear&Greed alternative"
            )

            # Phase H.17: Cloud Run対応ヘッダー
            import os

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; CryptoBot/1.0; +https://github.com/crypto-bot)",
                "Accept": "application/json",
            }

            timeout = 30 if os.getenv("K_SERVICE") else 10

            response = requests.get(self.backup_url, headers=headers, timeout=timeout)
            response.raise_for_status()

            data = response.json()
            if "data" not in data:
                raise ValueError("No Fear&Greed data in backup response")

            # DataFrameに変換
            fg_data = pd.DataFrame(data["data"])
            fg_data["timestamp"] = pd.to_datetime(fg_data["timestamp"], unit="s")
            fg_data["value"] = pd.to_numeric(fg_data["value"])
            fg_data = fg_data.sort_values("timestamp").set_index("timestamp")

            # 最新のlimit件に制限
            fg_data = fg_data.head(limit)

            return fg_data

        except Exception as e:
            logger.error(f"CNN Fear&Greed fetch failed: {e}")
            raise

    def calculate_fear_greed_features(self, fg_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fear&Greed特徴量計算（13特徴量）

        Args:
            fg_data: Fear&Greedデータ

        Returns:
            Fear&Greed特徴量DataFrame
        """
        try:
            if fg_data is None or fg_data.empty:
                # デフォルト値でDataFrameを作成
                default_features = self._get_default_fear_greed_features()
                return pd.DataFrame(
                    [default_features], index=[pd.Timestamp.now(tz="UTC")]
                )

            # 各行に対してFear&Greed特徴量を計算
            features_df = pd.DataFrame(index=fg_data.index)

            # 基本指標
            features_df["fg_index"] = fg_data["value"]
            features_df["fg_change_1d"] = fg_data["value"].pct_change()
            features_df["fg_change_7d"] = fg_data["value"].pct_change(7)
            features_df["fg_ma_7"] = fg_data["value"].rolling(7).mean()
            features_df["fg_ma_30"] = fg_data["value"].rolling(30).mean()

            # 感情状態分類
            features_df["fg_extreme_fear"] = (fg_data["value"] < 25).astype(int)
            features_df["fg_fear"] = (
                (fg_data["value"] >= 25) & (fg_data["value"] < 45)
            ).astype(int)
            features_df["fg_neutral"] = (
                (fg_data["value"] >= 45) & (fg_data["value"] < 55)
            ).astype(int)
            features_df["fg_greed"] = (
                (fg_data["value"] >= 55) & (fg_data["value"] < 75)
            ).astype(int)
            features_df["fg_extreme_greed"] = (fg_data["value"] >= 75).astype(int)

            # 統計指標
            features_df["fg_volatility"] = fg_data["value"].rolling(7).std()
            features_df["fg_momentum"] = (
                fg_data["value"] - fg_data["value"].rolling(7).mean()
            )
            features_df["fg_reversal_signal"] = (
                (fg_data["value"] < 25) | (fg_data["value"] > 75)
            ).astype(int)

            # NaN値をデフォルト値で補完
            default_values = self._get_default_fear_greed_features()
            for col in features_df.columns:
                features_df[col] = features_df[col].fillna(default_values.get(col, 0))

            logger.info(
                f"Fear&Greed features calculated: {len(features_df)} rows, "
                f"{len(features_df.columns)} columns"
            )
            return features_df

        except Exception as e:
            logger.error(f"Failed to calculate Fear&Greed features: {e}")
            # エラー時はデフォルト値でDataFrameを返す
            default_features = self._get_default_fear_greed_features()
            return pd.DataFrame([default_features], index=[pd.Timestamp.now(tz="UTC")])

    def _get_default_fear_greed_features(self) -> Dict[str, Any]:
        """Fear&Greed特徴量デフォルト値"""
        return {
            "fg_index": 50.0,  # 中立
            "fg_change_1d": 0.0,
            "fg_change_7d": 0.0,
            "fg_ma_7": 50.0,
            "fg_ma_30": 50.0,
            "fg_extreme_fear": 0,
            "fg_fear": 0,
            "fg_neutral": 1,
            "fg_greed": 0,
            "fg_extreme_greed": 0,
            "fg_volatility": 10.0,
            "fg_momentum": 0.0,
            "fg_reversal_signal": 0,
        }

    def get_vix_correlation_features(
        self, fg_data: pd.DataFrame, vix_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        VIXとFear&Greedの相関特徴量計算

        Args:
            fg_data: Fear&Greedデータ
            vix_data: VIXデータ

        Returns:
            VIX-FG相関特徴量DataFrame
        """
        try:
            if fg_data.empty or vix_data.empty:
                logger.warning("⚠️ Empty data for VIX-FG correlation")
                return pd.DataFrame()

            # データを共通の時間軸に合わせる
            common_index = fg_data.index.intersection(vix_data.index)
            if len(common_index) == 0:
                # インデックスが全く合わない場合、最新データで補完
                logger.warning("⚠️ No common index for VIX-FG correlation")
                return pd.DataFrame()

            # 共通期間のデータを抽出
            fg_common = fg_data.loc[common_index]
            vix_common = vix_data.loc[common_index]

            # 相関特徴量を計算
            correlation_features = pd.DataFrame(index=common_index)

            # 基本相関
            if "value" in fg_common.columns and "vix_level" in vix_common.columns:
                # 30日間の相関係数
                correlation_features["vix_fg_correlation_30d"] = (
                    fg_common["value"].rolling(30).corr(vix_common["vix_level"])
                )

                # 差分の相関
                fg_change = fg_common["value"].pct_change()
                vix_change = vix_common["vix_level"].pct_change()
                correlation_features["vix_fg_change_correlation"] = fg_change.rolling(
                    30
                ).corr(vix_change)

                # 逆相関シグナル（VIX上昇時のFG下降）
                correlation_features["vix_fg_divergence"] = (
                    (vix_change > 0) & (fg_change < 0)
                ).astype(int)

            # 欠損値を0で埋める
            correlation_features = correlation_features.fillna(0)

            logger.info(
                f"✅ VIX-FG correlation features: "
                f"{len(correlation_features.columns)} columns"
            )
            return correlation_features

        except Exception as e:
            logger.error(f"❌ VIX-FG correlation calculation failed: {e}")
            return pd.DataFrame()


def get_available_fear_greed_features():
    """利用可能なFear&Greed特徴量の名前リストを取得"""
    return [
        "fg_index",
        "fg_change_1d",
        "fg_change_7d",
        "fg_ma_7",
        "fg_ma_30",
        "fg_extreme_fear",
        "fg_fear",
        "fg_neutral",
        "fg_greed",
        "fg_extreme_greed",
        "fg_volatility",
        "fg_momentum",
        "fg_reversal_signal",
    ]
