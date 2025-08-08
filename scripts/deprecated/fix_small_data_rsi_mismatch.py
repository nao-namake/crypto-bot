#!/usr/bin/env python3
"""
Phase 3.1: 小規模データでのRSI特徴量不一致問題解決スクリプト
実取引環境でのRSI計算不能時のフォールバック機能実装
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.ml.feature_engines.technical_engine import TechnicalFeatureEngine
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RSIFeatureFallbackSystem:
    """RSI特徴量フォールバックシステム"""

    def __init__(self):
        self.required_rsi_features = [
            "rsi_7",
            "rsi_14",
            "rsi_21",
            "rsi_oversold",
            "rsi_overbought",
        ]
        self.default_rsi_values = {
            "rsi_7": 50.0,  # 中性値
            "rsi_14": 50.0,  # 中性値
            "rsi_21": 50.0,  # 中性値
            "rsi_oversold": 0,  # False
            "rsi_overbought": 0,  # False
        }

    def calculate_minimal_rsi(
        self, close_series: pd.Series, period: int
    ) -> Optional[pd.Series]:
        """最小データでのRSI計算（シンプル版）"""
        try:
            if len(close_series) < 2:
                logger.warning(
                    f"データ不足でRSI_{period}計算不可: {len(close_series)}レコード"
                )
                return None

            # 価格変化率を計算
            delta = close_series.diff()

            # 上昇・下落分を分離
            gain = (delta.where(delta > 0, 0)).fillna(0)
            loss = (-delta.where(delta < 0, 0)).fillna(0)

            # 最小期間でRSI近似計算
            min_period = min(period, len(close_series) - 1)

            if min_period >= 2:
                # シンプル移動平均でRSI計算
                avg_gain = gain.rolling(window=min_period, min_periods=1).mean()
                avg_loss = loss.rolling(window=min_period, min_periods=1).mean()

                # RSI計算（ZeroDivisionError回避）
                rs = avg_gain / (avg_loss + 1e-10)  # 微小値追加
                rsi = 100 - (100 / (1 + rs))

                logger.debug(f"RSI_{period}最小計算成功: {min_period}期間使用")
                return rsi
            else:
                # 極小データの場合は価格変化率から推定
                price_change = (close_series.iloc[-1] / close_series.iloc[0] - 1) * 100

                # 価格変化率からRSI推定
                if price_change > 2:
                    estimated_rsi = pd.Series(
                        [65.0] * len(close_series), index=close_series.index
                    )
                elif price_change < -2:
                    estimated_rsi = pd.Series(
                        [35.0] * len(close_series), index=close_series.index
                    )
                else:
                    estimated_rsi = pd.Series(
                        [50.0] * len(close_series), index=close_series.index
                    )

                logger.warning(
                    f"RSI_{period}推定値使用: price_change={price_change:.2f}%"
                )
                return estimated_rsi

        except Exception as e:
            logger.error(f"最小RSI計算エラー: {e}")
            return None

    def ensure_rsi_features(
        self, features_df: pd.DataFrame, original_df: pd.DataFrame
    ) -> pd.DataFrame:
        """RSI特徴量の完全性保証"""
        logger.info("🔍 RSI特徴量完全性チェック開始")

        missing_features = []
        for feature in self.required_rsi_features:
            if feature not in features_df.columns:
                missing_features.append(feature)

        if not missing_features:
            logger.info("✅ すべてのRSI特徴量が存在")
            return features_df

        logger.warning(f"⚠️ 不足RSI特徴量: {missing_features}")

        # 不足特徴量の生成
        close_series = original_df["close"]

        for feature in missing_features:
            if feature == "rsi_7":
                rsi_values = self.calculate_minimal_rsi(close_series, 7)
                if rsi_values is not None:
                    features_df[feature] = rsi_values
                else:
                    features_df[feature] = self.default_rsi_values[feature]
                    logger.warning(
                        f"RSI_7デフォルト値使用: {self.default_rsi_values[feature]}"
                    )

            elif feature == "rsi_14":
                rsi_values = self.calculate_minimal_rsi(close_series, 14)
                if rsi_values is not None:
                    features_df[feature] = rsi_values
                else:
                    features_df[feature] = self.default_rsi_values[feature]
                    logger.warning(
                        f"RSI_14デフォルト値使用: {self.default_rsi_values[feature]}"
                    )

            elif feature == "rsi_21":
                rsi_values = self.calculate_minimal_rsi(close_series, 21)
                if rsi_values is not None:
                    features_df[feature] = rsi_values
                else:
                    features_df[feature] = self.default_rsi_values[feature]
                    logger.warning(
                        f"RSI_21デフォルト値使用: {self.default_rsi_values[feature]}"
                    )

            elif feature == "rsi_oversold":
                # RSI_14が存在する場合はそれを使用、なければデフォルト
                if "rsi_14" in features_df.columns:
                    features_df[feature] = (features_df["rsi_14"] < 30).astype(int)
                else:
                    features_df[feature] = self.default_rsi_values[feature]
                logger.debug(f"RSI_oversold生成完了")

            elif feature == "rsi_overbought":
                # RSI_14が存在する場合はそれを使用、なければデフォルト
                if "rsi_14" in features_df.columns:
                    features_df[feature] = (features_df["rsi_14"] > 70).astype(int)
                else:
                    features_df[feature] = self.default_rsi_values[feature]
                logger.debug(f"RSI_overbought生成完了")

        logger.info(f"✅ RSI特徴量完全性保証完了: {len(missing_features)}個追加")
        return features_df


def patch_technical_engine():
    """TechnicalFeatureEngineにフォールバック機能をパッチ"""

    def enhanced_calculate_rsi_batch(self, df: pd.DataFrame):
        """拡張RSI計算（フォールバック機能付き）"""
        periods = self.technical_configs["rsi"]["periods"]
        logger.info(f"🔍 Enhanced RSI batch calculation: periods={periods}")

        if not periods:
            logger.warning("⚠️ No RSI periods configured")
            return self.batch_calc.create_feature_batch("rsi_batch", {})

        try:
            rsi_features = {}
            close_series = df["close"]
            fallback_system = RSIFeatureFallbackSystem()

            logger.info(f"🔍 RSI calculation: close_series length={len(close_series)}")

            # 各期間のRSI計算
            for period in periods:
                try:
                    if len(close_series) < period + 1:
                        logger.warning(
                            f"  ⚠️ Insufficient data for RSI_{period}: {len(close_series)} < {period + 1}"
                        )
                        # フォールバック計算実行
                        rsi_values = fallback_system.calculate_minimal_rsi(
                            close_series, period
                        )
                        if rsi_values is not None:
                            rsi_features[f"rsi_{period}"] = rsi_values
                            logger.info(f"  ✅ RSI_{period} フォールバック計算成功")
                        else:
                            # デフォルト値使用
                            default_val = fallback_system.default_rsi_values.get(
                                f"rsi_{period}", 50.0
                            )
                            rsi_features[f"rsi_{period}"] = pd.Series(
                                [default_val] * len(close_series),
                                index=close_series.index,
                            )
                            logger.warning(
                                f"  ⚠️ RSI_{period} デフォルト値使用: {default_val}"
                            )
                        continue

                    # 通常のRSI計算
                    if self.indicator_available and self.ind_calc:
                        logger.debug(f"  Using IndicatorCalculator for RSI_{period}")
                        rsi_values = self.ind_calc.rsi(close_series, window=period)
                    else:
                        logger.debug(f"  Using builtin calculation for RSI_{period}")
                        rsi_values = self._calculate_rsi_builtin(close_series, period)

                    # None または 空の結果チェック
                    if rsi_values is None:
                        logger.warning(
                            f"  ⚠️ RSI_{period} returned None, using fallback"
                        )
                        rsi_values = fallback_system.calculate_minimal_rsi(
                            close_series, period
                        )
                        if rsi_values is None:
                            default_val = fallback_system.default_rsi_values.get(
                                f"rsi_{period}", 50.0
                            )
                            rsi_values = pd.Series(
                                [default_val] * len(close_series),
                                index=close_series.index,
                            )
                            logger.warning(
                                f"  ⚠️ RSI_{period} デフォルト値使用: {default_val}"
                            )

                    # Series型確認とNaN値処理
                    if rsi_values is not None and isinstance(rsi_values, pd.Series):
                        rsi_features[f"rsi_{period}"] = rsi_values
                        logger.debug(f"  ✅ RSI_{period} calculated successfully")
                    else:
                        logger.warning(
                            f"  ⚠️ RSI_{period} invalid result: {type(rsi_values)}"
                        )

                except Exception as e:
                    logger.error(f"  ❌ RSI_{period} calculation failed: {e}")
                    # エラー時もフォールバック実行
                    default_val = fallback_system.default_rsi_values.get(
                        f"rsi_{period}", 50.0
                    )
                    rsi_features[f"rsi_{period}"] = pd.Series(
                        [default_val] * len(close_series), index=close_series.index
                    )
                    logger.warning(
                        f"  ⚠️ RSI_{period} エラー時デフォルト値使用: {default_val}"
                    )

            # RSI oversold/overbought特徴量を追加
            if "rsi_14" in rsi_features and rsi_features["rsi_14"] is not None:
                rsi_14 = rsi_features["rsi_14"]
                if isinstance(rsi_14, pd.Series):
                    rsi_features["rsi_oversold"] = (rsi_14 < 30).astype(int)
                    rsi_features["rsi_overbought"] = (rsi_14 > 70).astype(int)
                    logger.debug("  ✅ RSI oversold/overbought features added")
            else:
                # RSI_14がない場合のフォールバック
                rsi_features["rsi_oversold"] = pd.Series(
                    [0] * len(close_series), index=close_series.index
                )
                rsi_features["rsi_overbought"] = pd.Series(
                    [0] * len(close_series), index=close_series.index
                )
                logger.warning("  ⚠️ RSI oversold/overbought デフォルト値使用")

            logger.info(
                f"✅ Enhanced RSI batch: {len(rsi_features)} indicators ({list(rsi_features.keys())})"
            )
            return self.batch_calc.create_feature_batch(
                "rsi_batch", rsi_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ Enhanced RSI batch calculation failed: {e}")
            import traceback

            traceback.print_exc()
            # 完全エラー時のフォールバック
            fallback_system = RSIFeatureFallbackSystem()
            fallback_features = {}
            close_series = df["close"]

            for period in periods:
                default_val = fallback_system.default_rsi_values.get(
                    f"rsi_{period}", 50.0
                )
                fallback_features[f"rsi_{period}"] = pd.Series(
                    [default_val] * len(close_series), index=close_series.index
                )

            # Oversold/Overbought
            fallback_features["rsi_oversold"] = pd.Series(
                [0] * len(close_series), index=close_series.index
            )
            fallback_features["rsi_overbought"] = pd.Series(
                [0] * len(close_series), index=close_series.index
            )

            logger.warning(
                f"⚠️ RSI完全フォールバック使用: {list(fallback_features.keys())}"
            )
            return self.batch_calc.create_feature_batch(
                "rsi_batch", fallback_features, df.index
            )

    # パッチ適用
    TechnicalFeatureEngine.calculate_rsi_batch = enhanced_calculate_rsi_batch
    logger.info("✅ TechnicalFeatureEngine RSIフォールバック機能パッチ適用完了")


def test_small_data_rsi_handling():
    """小規模データでのRSI処理テスト"""
    logger.info("🧪 小規模データRSI処理テスト開始")

    # パッチ適用
    patch_technical_engine()

    # テストデータ作成（5レコード）
    test_data = {
        "open": [10000.0, 10050.0, 10100.0, 10080.0, 10120.0],
        "high": [10100.0, 10150.0, 10200.0, 10180.0, 10220.0],
        "low": [9950.0, 10000.0, 10050.0, 10030.0, 10070.0],
        "close": [10050.0, 10100.0, 10080.0, 10120.0, 10150.0],
        "volume": [1000.0, 1200.0, 800.0, 1500.0, 1100.0],
    }

    df = pd.DataFrame(test_data)
    df.index = pd.date_range("2025-01-01", periods=5, freq="H")

    logger.info(f"📊 テストデータ: {len(df)}レコード")

    # 設定読み込み
    import yaml

    config_path = str(project_root / "config/production/production.yml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # 特徴量生成
    feature_engineer = FeatureEngineer(config)

    try:
        features_df = feature_engineer.transform(df)
        logger.info(f"✅ 特徴量生成成功: {len(features_df.columns)}個")

        # RSI特徴量の存在確認
        rsi_features = [col for col in features_df.columns if "rsi" in col.lower()]
        logger.info(f"📊 RSI特徴量: {rsi_features}")

        # 各RSI特徴量の値確認
        for feature in rsi_features:
            values = features_df[feature].dropna()
            if len(values) > 0:
                logger.info(f"  {feature}: {values.iloc[-1]:.2f} (最新値)")
            else:
                logger.warning(f"  {feature}: すべてNaN")

        # 125特徴量確認
        expected_features = 125
        actual_features = len(features_df.columns)
        logger.info(f"📊 特徴量数: {actual_features}/{expected_features}")

        if actual_features == expected_features:
            logger.info("✅ 125特徴量完全性確認成功！")
            return True
        else:
            logger.warning(
                f"⚠️ 特徴量数不一致: {actual_features} != {expected_features}"
            )
            return False

    except Exception as e:
        logger.error(f"❌ 特徴量生成エラー: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_small_data_rsi_handling()
        if success:
            print("\n" + "=" * 60)
            print("✅ Phase 3.1完了：小規模データRSI不一致問題解決！")
            print("=" * 60)
            print("🚀 実取引環境でのRSIフォールバック機能実装完了")
            print("📊 5レコードのような小規模データでも125特徴量保証")
            print("🔧 TechnicalFeatureEngineパッチ適用済み")
            print("✅ 実取引環境でのfeature mismatch問題解決")
            print("=" * 60)
        else:
            print("❌ テスト失敗")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ スクリプト実行エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
