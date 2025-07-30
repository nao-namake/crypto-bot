"""
特徴量順序管理システム
Phase H.17: 学習時と予測時の特徴量順序を完全一致させる

目的:
- XGBoost/RandomForestのfeature_names mismatchエラー解決
- 155特徴量の決定論的順序管理
- 学習・予測間の一貫性保証
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class FeatureOrderManager:
    """
    特徴量順序の決定論的管理クラス

    機能:
    - 155特徴量の固定順序定義
    - 学習時の特徴量順序記録
    - 予測時の特徴量順序整合
    - 特徴量順序の検証・ログ出力
    """

    # Phase H.25: 125特徴量の決定論的順序（外部API特徴量を除外）
    FEATURE_ORDER_125 = [
        # 基本OHLCV特徴量
        "open",
        "high",
        "low",
        "close",
        "volume",
        # ラグ特徴量
        "close_lag_1",
        "close_lag_2",
        "close_lag_3",
        "close_lag_4",
        "close_lag_5",
        "volume_lag_1",
        "volume_lag_2",
        "volume_lag_3",
        "volume_lag_4",
        "volume_lag_5",
        # リターン特徴量
        "returns_1",
        "returns_2",
        "returns_3",
        "returns_5",
        "returns_10",
        "log_returns_1",
        "log_returns_2",
        "log_returns_3",
        "log_returns_5",
        "log_returns_10",
        # 移動平均
        "sma_5",
        "sma_10",
        "sma_20",
        "sma_50",
        "sma_100",
        "sma_200",
        "ema_5",
        "ema_10",
        "ema_20",
        "ema_50",
        "ema_100",
        "ema_200",
        # 価格位置
        "price_position_20",
        "price_position_50",
        "price_vs_sma20",
        "bb_position",
        "intraday_position",
        # ボリンジャーバンド
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "bb_width",
        "bb_squeeze",
        # モメンタム指標
        "rsi_14",
        "rsi_7",
        "rsi_21",
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
        # ボラティリティ
        "atr_14",
        "atr_7",
        "atr_21",
        "volatility_20",
        "volatility_50",
        "high_low_ratio",
        "true_range",
        "volatility_ratio",
        # 出来高指標
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
        # トレンド指標
        "adx_14",
        "plus_di",
        "minus_di",
        "trend_strength",
        "trend_direction",
        "cci_20",
        "williams_r",
        "ultimate_oscillator",
        # マーケット構造
        "support_distance",
        "resistance_distance",
        "support_strength",
        "volume_breakout",
        "price_breakout_up",
        "price_breakout_down",
        # ローソク足パターン
        "doji",
        "hammer",
        "engulfing",
        "pinbar",
        # 統計的特徴量
        "skewness_20",
        "kurtosis_20",
        "zscore",
        "mean_reversion_20",
        "mean_reversion_50",
        # 時系列特徴量
        "hour",
        "day_of_week",
        "is_weekend",
        "is_asian_session",
        "is_european_session",
        "is_us_session",
        # Phase H.25: 外部データ特徴量を削除（VIX, Fear&Greed, マクロ, Funding, 相関）
        # 追加の技術指標
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
        # その他の派生特徴量
        "price_efficiency",
        "trend_consistency",
        "volume_price_correlation",
        "volatility_regime",
        "momentum_quality",
        "market_phase",
        "momentum_14",  # Phase H.23.7: momentum_14追加で155特徴量に統一
    ]

    def __init__(self, feature_order_file: Optional[str] = None):
        """
        初期化

        Args:
            feature_order_file: 特徴量順序を保存/読込するファイルパス
        """
        self.feature_order_file = feature_order_file or "feature_order.json"
        self.stored_order: Optional[List[str]] = None

        # 保存された順序があれば読み込む
        self._load_stored_order()

        logger.info("🔧 FeatureOrderManager initialized")
        logger.info(f"  - Default order: {len(self.FEATURE_ORDER_125)} features")
        logger.info(f"  - Storage file: {self.feature_order_file}")

    def _load_stored_order(self):
        """保存された特徴量順序を読み込む"""
        try:
            path = Path(self.feature_order_file)
            if path.exists():
                with open(path, "r") as f:
                    data = json.load(f)
                    self.stored_order = data.get("feature_order", [])
                    logger.info(
                        f"✅ Loaded stored feature order: "
                        f"{len(self.stored_order)} features"
                    )
            else:
                logger.info("📝 No stored feature order found, using default")
        except Exception as e:
            logger.error(f"❌ Failed to load feature order: {e}")
            self.stored_order = None

    def save_feature_order(self, features: List[str]):
        """
        特徴量順序を保存（学習時に使用）

        Args:
            features: 学習時の特徴量リスト
        """
        try:
            data = {
                "feature_order": features,
                "num_features": len(features),
                "timestamp": pd.Timestamp.now().isoformat(),
            }

            with open(self.feature_order_file, "w") as f:
                json.dump(data, f, indent=2)

            self.stored_order = features
            logger.info(f"✅ Saved feature order: {len(features)} features")

            # 順序の最初と最後を表示
            if len(features) > 10:
                logger.info(f"  First 5: {features[:5]}")
                logger.info(f"  Last 5: {features[-5:]}")
            else:
                logger.info(f"  Features: {features}")

        except Exception as e:
            logger.error(f"❌ Failed to save feature order: {e}")

    def get_consistent_order(self, current_features: List[str]) -> List[str]:
        """
        一貫性のある特徴量順序を取得

        Args:
            current_features: 現在の特徴量リスト

        Returns:
            順序調整された特徴量リスト
        """
        # 保存された順序があればそれを使用
        if self.stored_order:
            logger.info(
                f"📋 Using stored feature order ({len(self.stored_order)} features)"
            )
            return self._align_to_stored_order(current_features)

        # なければデフォルト順序を使用
        logger.info("📋 Using default feature order")
        return self._align_to_default_order(current_features)

    def _align_to_stored_order(self, current_features: List[str]) -> List[str]:
        """保存された順序に合わせて整列"""
        current_set = set(current_features)
        stored_set = set(self.stored_order)

        # 共通の特徴量を保存された順序で並べる
        aligned = [f for f in self.stored_order if f in current_set]

        # 新しい特徴量があれば最後に追加
        new_features = current_set - stored_set
        if new_features:
            logger.warning(f"⚠️ New features not in stored order: {new_features}")
            aligned.extend(sorted(new_features))

        # 不足している特徴量を警告
        missing_features = stored_set - current_set
        if missing_features:
            logger.warning(
                f"⚠️ Features in stored order but missing now: {missing_features}"
            )

        logger.info(
            f"✅ Aligned features: {len(aligned)} (was {len(current_features)})"
        )
        return aligned

    def _align_to_default_order(self, current_features: List[str]) -> List[str]:
        """デフォルト順序に合わせて整列"""
        current_set = set(current_features)

        # デフォルト順序に存在する特徴量を抽出
        aligned = [f for f in self.FEATURE_ORDER_125 if f in current_set]

        # デフォルトにない特徴量を追加
        extra_features = current_set - set(self.FEATURE_ORDER_125)
        if extra_features:
            logger.info(
                f"📝 Extra features not in default order: {len(extra_features)}"
            )
            aligned.extend(sorted(extra_features))

        logger.info(f"✅ Aligned to default order: {len(aligned)} features")
        return aligned

    def ensure_column_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrameの列順序を保証

        Args:
            df: 順序調整するDataFrame

        Returns:
            列順序が調整されたDataFrame
        """
        if df.empty:
            return df

        original_columns = list(df.columns)
        ordered_columns = self.get_consistent_order(original_columns)

        # 順序が変わった場合のみ並び替え
        if original_columns != ordered_columns:
            logger.info(
                f"🔄 Reordering columns: "
                f"{len(original_columns)} -> {len(ordered_columns)}"
            )
            df = df[ordered_columns]

            # 変更内容を表示
            if len(ordered_columns) <= 20:
                logger.debug(f"  Original: {original_columns[:10]}...")
                logger.debug(f"  Ordered: {ordered_columns[:10]}...")
        else:
            logger.debug("✅ Column order already consistent")

        return df

    def validate_features(
        self, train_features: List[str], predict_features: List[str]
    ) -> bool:
        """
        学習時と予測時の特徴量を検証

        Args:
            train_features: 学習時の特徴量
            predict_features: 予測時の特徴量

        Returns:
            一致していればTrue
        """
        train_set = set(train_features)
        predict_set = set(predict_features)

        # 完全一致チェック
        if train_set == predict_set and train_features == predict_features:
            logger.info("✅ Feature validation passed: perfect match")
            return True

        # 差分分析
        missing_in_predict = train_set - predict_set
        extra_in_predict = predict_set - train_set

        if missing_in_predict:
            logger.error(f"❌ Features missing in prediction: {missing_in_predict}")
        if extra_in_predict:
            logger.error(f"❌ Extra features in prediction: {extra_in_predict}")

        # 順序の違いをチェック
        common_features = train_set & predict_set
        if common_features:
            train_order = [f for f in train_features if f in common_features]
            predict_order = [f for f in predict_features if f in common_features]

            if train_order != predict_order:
                logger.error("❌ Feature order mismatch detected")
                # 最初の不一致を表示
                for i, (t, p) in enumerate(zip(train_order, predict_order)):
                    if t != p:
                        logger.error(f"  Position {i}: '{t}' vs '{p}'")
                        break

        return False


# グローバルインスタンス
_global_feature_order_manager: Optional[FeatureOrderManager] = None


def get_feature_order_manager() -> FeatureOrderManager:
    """グローバルな特徴量順序管理インスタンスを取得"""
    global _global_feature_order_manager
    if _global_feature_order_manager is None:
        _global_feature_order_manager = FeatureOrderManager()
    return _global_feature_order_manager
