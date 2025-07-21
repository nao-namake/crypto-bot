"""
マクロ経済データフェッチャー
Yahoo Financeから米ドル指数(DXY)・金利データを取得し、101特徴量システムに統合
Phase A3: 外部データキャッシュ最適化・グローバルキャッシュ統合
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd
import yfinance as yf

from ..utils.api_retry import api_retry
from .multi_source_fetcher import MultiSourceDataFetcher

logger = logging.getLogger(__name__)


class MacroDataFetcher(MultiSourceDataFetcher):
    """マクロ経済データ取得クラス（MultiSourceDataFetcher継承・Phase B1対応）"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 親クラス初期化
        super().__init__(config, data_type="macro")

        self.symbols = {
            "dxy": "DX-Y.NYB",  # ドル指数
            "us10y": "^TNX",  # 米10年債利回り
            "us2y": "^IRX",  # 米2年債利回り
            "usdjpy": "USDJPY=X",  # USD/JPY為替レート
        }

        logger.info("🔧 MacroDataFetcher initialized with MultiSourceDataFetcher base")

    def _validate_data_quality(self, data: pd.DataFrame) -> float:
        """データ品質検証（MultiSourceDataFetcher抽象メソッド実装）"""
        if data is None or data.empty:
            return 0.0

        # 品質評価指標
        total_points = len(data)
        valid_points = len(data.dropna())

        if total_points == 0:
            return 0.0

        # マクロ経済データ特有の品質検証
        range_quality_score = 0.0
        numeric_cols = data.select_dtypes(include=["number"]).columns

        if len(numeric_cols) > 0:
            # 妥当な数値範囲かチェック（極端な値を除外）
            valid_ranges = 0
            for col in numeric_cols:
                # 各指標の妥当性をチェック
                if "dxy" in col.lower():
                    # DXYは90-120の範囲が妥当
                    valid_ranges += ((data[col] >= 80) & (data[col] <= 130)).sum()
                elif (
                    "treasury" in col.lower()
                    or "us10y" in col.lower()
                    or "us2y" in col.lower()
                ):
                    # 金利は0-15%の範囲が妥当
                    valid_ranges += ((data[col] >= 0) & (data[col] <= 15)).sum()
                elif "usdjpy" in col.lower():
                    # USD/JPYは100-180の範囲が妥当
                    valid_ranges += ((data[col] >= 80) & (data[col] <= 200)).sum()
                else:
                    # その他は無限大値のみをチェック
                    valid_ranges += (~(data[col].isinf() | data[col].isna())).sum()

            range_quality_score = valid_ranges / (len(numeric_cols) * total_points)

        # 総合品質スコア
        quality_score = (valid_points / total_points) * 0.6 + range_quality_score * 0.4
        logger.debug(
            f"📊 Macro data quality: {quality_score:.3f} "
            f"(valid: {valid_points}/{total_points}, range: {range_quality_score:.3f})"
        )

        return quality_score

    def _fetch_data_from_source(
        self, source_name: str, **kwargs
    ) -> Optional[pd.DataFrame]:
        """特定データソースからデータ取得（MultiSourceDataFetcher抽象メソッド実装）"""
        start_date = kwargs.get(
            "start_date", (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        )
        end_date = kwargs.get("end_date", datetime.now().strftime("%Y-%m-%d"))

        if source_name == "yahoo":
            return self._fetch_yahoo_macro_data(start_date, end_date)
        elif source_name == "alpha_vantage":
            return self._fetch_alpha_vantage_macro_data(start_date, end_date)
        elif source_name == "fred":
            return self._fetch_fred_macro_data(start_date, end_date)
        else:
            logger.warning(f"Unknown macro data source: {source_name}")
            return None

    def _generate_fallback_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """フォールバックデータ生成（MultiSourceDataFetcher抽象メソッド実装）"""
        try:
            # デフォルト期間設定
            start_date = kwargs.get(
                "start_date", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            )
            end_date = kwargs.get("end_date", datetime.now().strftime("%Y-%m-%d"))

            # 過去30日分のデフォルトマクロデータを生成
            try:
                dates = pd.date_range(start=start_date, end=end_date, freq="D")
            except ValueError:
                # 日付範囲指定に問題がある場合は30日間で生成
                dates = pd.date_range(end=datetime.now(), periods=30, freq="D")

            # デフォルト値（現在の概算値）
            fallback_data = pd.DataFrame(index=dates)
            fallback_data["dxy_close"] = 103.0  # DXY通常レベル
            fallback_data["us10y_close"] = 4.5  # 10年債利回り
            fallback_data["us2y_close"] = 4.8  # 2年債利回り
            fallback_data["usdjpy_close"] = 150.0  # USD/JPY

            logger.info("📈 Generated macro fallback data: %d days", len(fallback_data))
            return fallback_data

        except Exception as e:
            logger.error(f"❌ Failed to generate macro fallback data: {e}")
            return None

    @api_retry(max_retries=3, base_delay=2.0, circuit_breaker=True)
    def _fetch_yahoo_macro_data(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """Yahoo Financeからマクロデータをまとめて取得"""
        try:
            combined_data = pd.DataFrame()

            for name, symbol in self.symbols.items():
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(start=start_date, end=end_date)

                    if data.empty:
                        logger.warning(f"⚠️ No data for {name} ({symbol})")
                        continue

                    # カラム名を統一（シンボル名をプレフィックスに追加）
                    data.columns = [f"{name}_{col.lower()}" for col in data.columns]

                    if combined_data.empty:
                        combined_data = data.copy()
                    else:
                        # インデックス（日付）で結合
                        combined_data = combined_data.join(data, how="outer")

                    logger.info(f"✅ {name} data: {len(data)} records")

                except Exception as e:
                    logger.warning(f"⚠️ Failed to fetch {name} data: {e}")
                    continue

            if combined_data.empty:
                raise ValueError("All macro symbols failed to fetch")

            # 前方埋めで欠損値を補完
            combined_data = combined_data.fillna(method="ffill")

            return combined_data

        except Exception as e:
            logger.error(f"Yahoo Finance macro fetch failed: {e}")
            raise

    @api_retry(max_retries=3, base_delay=2.0, circuit_breaker=True)
    def _fetch_alpha_vantage_macro_data(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """Alpha Vantageからマクロデータ取得（代替実装）"""
        try:
            # Alpha Vantage API実装（簡略版）
            # 実際の実装では、Alpha Vantage APIキーが必要
            # 現在は Yahoo Finance のフォールバックとして実装
            logger.info("📡 Using Yahoo Finance as Alpha Vantage macro alternative")

            return self._fetch_yahoo_macro_data(start_date, end_date)

        except Exception as e:
            logger.error(f"Alpha Vantage macro fetch failed: {e}")
            raise

    @api_retry(max_retries=3, base_delay=2.0, circuit_breaker=True)
    def _fetch_fred_macro_data(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """FRED（Federal Reserve Economic Data）からマクロデータ取得（将来実装）"""
        try:
            # FRED API実装（将来の拡張用）
            # 現在はYahoo Financeフォールバックとして実装
            logger.info("📡 Using Yahoo Finance as FRED macro alternative")

            return self._fetch_yahoo_macro_data(start_date, end_date)

        except Exception as e:
            logger.error(f"FRED macro fetch failed: {e}")
            raise

    def get_macro_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        マクロ経済データ取得（MultiSourceDataFetcher統合版）

        Args:
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）

        Returns:
            マクロデータの辞書
        """
        # 親クラスのget_dataメソッドを呼び出し
        unified_data = self.get_data(
            start_date=start_date, end_date=end_date, limit=limit
        )

        if unified_data is None or unified_data.empty:
            logger.warning("❌ No macro data retrieved from MultiSourceDataFetcher")
            return {}

        # 統合データを個別データ辞書形式に変換（後方互換性のため）
        macro_data = {}
        for symbol_name in self.symbols.keys():
            # 統合データから各シンボルのデータを抽出
            symbol_columns = [
                col for col in unified_data.columns if symbol_name in col.lower()
            ]
            if symbol_columns:
                macro_data[symbol_name] = unified_data[symbol_columns].copy()
                # 'close'列があることを確認（特徴量計算で使用）
                if "close" not in macro_data[symbol_name].columns and symbol_columns:
                    # 最初の数値列をcloseとして使用
                    numeric_cols = (
                        macro_data[symbol_name]
                        .select_dtypes(include=["number"])
                        .columns
                    )
                    if len(numeric_cols) > 0:
                        macro_data[symbol_name]["close"] = macro_data[symbol_name][
                            numeric_cols[0]
                        ]

        return macro_data

    def calculate_macro_features(
        self, macro_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        マクロ経済特徴量計算（10特徴量）

        Args:
            macro_data: マクロデータ辞書

        Returns:
            マクロ特徴量DataFrame
        """
        try:
            if not macro_data or all(df.empty for df in macro_data.values()):
                # データがない場合はデフォルト値でDataFrameを作成
                default_features = self._get_default_macro_features()
                return pd.DataFrame(
                    [default_features], index=[pd.Timestamp.now(tz="UTC")]
                )

            # 共通のインデックスを決定（最も長いデータセットを基準）
            max_data = max(macro_data.values(), key=len, default=pd.DataFrame())
            if max_data.empty:
                default_features = self._get_default_macro_features()
                return pd.DataFrame(
                    [default_features], index=[pd.Timestamp.now(tz="UTC")]
                )

            features_df = pd.DataFrame(index=max_data.index)

            # DXY（ドル指数）特徴量（preprocessor期待形式）
            if "dxy" in macro_data and not macro_data["dxy"].empty:
                dxy_data = macro_data["dxy"]
                dxy_aligned = dxy_data.reindex(features_df.index, method="ffill")

                dxy_ma20 = dxy_aligned["close"].rolling(20).mean()
                dxy_std = dxy_aligned["close"].rolling(20).std()

                features_df["dxy_level"] = dxy_aligned["close"]
                features_df["dxy_change"] = dxy_aligned["close"].pct_change()
                features_df["dxy_zscore"] = (dxy_aligned["close"] - dxy_ma20) / dxy_std
                features_df["dxy_strength"] = (dxy_aligned["close"] > dxy_ma20).astype(
                    int
                )
            else:
                defaults = self._get_default_dxy_features()
                for key, value in defaults.items():
                    features_df[key] = value

            # 米10年債利回り特徴量（preprocessor期待形式）
            if "us10y" in macro_data and not macro_data["us10y"].empty:
                us10y_data = macro_data["us10y"]
                us10y_aligned = us10y_data.reindex(features_df.index, method="ffill")

                us10y_ma20 = us10y_aligned["close"].rolling(20).mean()
                us10y_std = us10y_aligned["close"].rolling(20).std()

                features_df["treasury_10y_level"] = us10y_aligned["close"]
                features_df["treasury_10y_change"] = us10y_aligned["close"].diff()
                features_df["treasury_10y_zscore"] = (
                    us10y_aligned["close"] - us10y_ma20
                ) / us10y_std
                features_df["treasury_regime"] = (
                    us10y_aligned["close"] > us10y_ma20
                ).astype(int)
            else:
                defaults = self._get_default_10y_features()
                for key, value in defaults.items():
                    features_df[key] = value

            # 米2年債利回り特徴量とイールドカーブ
            if "us2y" in macro_data and not macro_data["us2y"].empty:
                us2y_data = macro_data["us2y"]
                us2y_aligned = us2y_data.reindex(features_df.index, method="ffill")

                # イールドカーブとリスクセンチメント
                treasury_10y = features_df.get("treasury_10y_level", 4.0)
                if isinstance(treasury_10y, pd.Series):
                    yield_spread = treasury_10y - us2y_aligned["close"]
                    features_df["yield_curve_spread"] = yield_spread
                    features_df["risk_sentiment"] = (yield_spread > 0).astype(int)
                else:
                    features_df["yield_curve_spread"] = (
                        treasury_10y - us2y_aligned["close"]
                    )
                    features_df["risk_sentiment"] = (
                        features_df["yield_curve_spread"] > 0
                    ).astype(int)
            else:
                defaults = self._get_default_2y_features()
                for key, value in defaults.items():
                    features_df[key] = value

            # USD/JPY為替レート特徴量（BTC/JPY予測精度向上）
            if "usdjpy" in macro_data and not macro_data["usdjpy"].empty:
                usdjpy_data = macro_data["usdjpy"]
                usdjpy_aligned = usdjpy_data.reindex(features_df.index, method="ffill")

                usdjpy_ma20 = usdjpy_aligned["close"].rolling(20).mean()
                usdjpy_std = usdjpy_aligned["close"].rolling(20).std()

                features_df["usdjpy_level"] = usdjpy_aligned["close"]
                features_df["usdjpy_change"] = usdjpy_aligned["close"].pct_change()
                features_df["usdjpy_volatility"] = (
                    usdjpy_aligned["close"].rolling(24).std()
                )
                features_df["usdjpy_zscore"] = (
                    usdjpy_aligned["close"] - usdjpy_ma20
                ) / usdjpy_std
                features_df["usdjpy_trend"] = (
                    usdjpy_aligned["close"] > usdjpy_ma20
                ).astype(int)
                features_df["usdjpy_strength"] = (
                    usdjpy_aligned["close"].pct_change() > 0
                ).astype(int)
            else:
                defaults = self._get_default_usdjpy_features()
                for key, value in defaults.items():
                    features_df[key] = value

            # NaN値を適切にデフォルト値で補完
            default_values = self._get_default_macro_features()
            for col in features_df.columns:
                features_df[col] = features_df[col].fillna(default_values.get(col, 0))
                # 無限大値も補完
                features_df[col] = features_df[col].replace(
                    [float("inf"), float("-inf")], default_values.get(col, 0)
                )

            logger.info(
                f"Macro features calculated: {len(features_df)} rows, "
                f"{len(features_df.columns)} columns"
            )
            return features_df

        except Exception as e:
            logger.error(f"Failed to calculate macro features: {e}")
            # エラー時はデフォルト値でDataFrameを返す
            default_features = self._get_default_macro_features()
            return pd.DataFrame([default_features], index=[pd.Timestamp.now(tz="UTC")])

    def _get_default_dxy_features(self) -> Dict[str, Any]:
        """DXY特徴量デフォルト値"""
        return {
            "dxy_level": 103.0,  # 典型的なDXYレベル
            "dxy_change": 0.0,
            "dxy_zscore": 0.0,
            "dxy_strength": 0,
        }

    def _get_default_10y_features(self) -> Dict[str, Any]:
        """10年債特徴量デフォルト値"""
        return {
            "treasury_10y_level": 4.0,  # 典型的な10年債利回り
            "treasury_10y_change": 0.0,
            "treasury_10y_zscore": 0.0,
            "treasury_regime": 0,
        }

    def _get_default_2y_features(self) -> Dict[str, Any]:
        """2年債特徴量デフォルト値"""
        return {
            "yield_curve_spread": -0.5,  # 逆イールド状態
            "risk_sentiment": 0,
        }

    def _get_default_usdjpy_features(self) -> Dict[str, Any]:
        """USD/JPY為替特徴量デフォルト値"""
        return {
            "usdjpy_level": 150.0,  # 典型的なUSD/JPYレベル
            "usdjpy_change": 0.0,  # 変動率
            "usdjpy_volatility": 0.005,  # 為替ボラティリティ
            "usdjpy_zscore": 0.0,  # Z-score
            "usdjpy_trend": 0,  # トレンド方向
            "usdjpy_strength": 0,  # 強度
        }

    def _get_default_macro_features(self) -> Dict[str, Any]:
        """マクロ特徴量デフォルト値（16特徴量）"""
        features = {}
        features.update(self._get_default_dxy_features())
        features.update(self._get_default_10y_features())
        features.update(self._get_default_2y_features())
        features.update(self._get_default_usdjpy_features())
        return features

    def _count_default_values(self, data: pd.DataFrame) -> int:
        """マクロデータ特有のデフォルト値カウント（品質監視用）"""
        try:
            default_count = 0

            # DXY特有のデフォルト値チェック
            for col in data.columns:
                if "dxy" in col.lower() and "close" in col.lower():
                    # DXY=103.0がデフォルト値
                    default_count += (data[col] == 103.0).sum()
                elif (
                    "treasury" in col.lower() or "us10y" in col.lower()
                ) and "close" in col.lower():
                    # 10年債=4.5がデフォルト値
                    default_count += (data[col] == 4.5).sum()
                elif "us2y" in col.lower() and "close" in col.lower():
                    # 2年債=4.8がデフォルト値
                    default_count += (data[col] == 4.8).sum()
                elif "usdjpy" in col.lower() and "close" in col.lower():
                    # USD/JPY=150.0がデフォルト値
                    default_count += (data[col] == 150.0).sum()

            return default_count

        except Exception as e:
            logger.error(f"❌ Failed to count macro default values: {e}")
            return 0
