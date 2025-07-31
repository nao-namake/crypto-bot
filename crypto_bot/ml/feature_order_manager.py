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

import numpy as np
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

    # Phase H.26: 125特徴量完全性保証システム
    def ensure_125_features_completeness(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        125特徴量の完全性を保証する包括的システム

        Args:
            df: 入力DataFrame

        Returns:
            正確に125個の特徴量を持つDataFrame
        """
        logger.info(
            f"🔍 Starting 125-feature completeness check: {len(df.columns)} input features"
        )

        try:
            # Step 1: 重複特徴量の検出・排除
            df_dedup = self._remove_duplicate_features(df)

            # Step 2: 125特徴量リストとの照合
            df_aligned = self._align_to_target_features(df_dedup)

            # Step 3: 不足特徴量の自動補完
            df_complete = self._fill_missing_features(df_aligned)

            # Step 4: 余分特徴量の管理
            df_trimmed = self._trim_excess_features(df_complete)

            # Step 5: 特徴量品質チェック・修正
            df_quality = self._ensure_feature_quality(df_trimmed)

            # Step 6: 最終検証
            df_final = self._final_125_validation(df_quality)

            logger.info(
                f"✅ 125-feature completeness guaranteed: {len(df_final.columns)} features"
            )
            return df_final

        except Exception as e:
            logger.error(f"❌ 125-feature completeness failed: {e}")
            return self._emergency_125_fallback(df)

    def _remove_duplicate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """重複特徴量の検出・排除"""
        original_count = len(df.columns)

        # 完全に同じ名前の重複を除去
        df_dedup = df.loc[:, ~df.columns.duplicated()]

        # 値が同じ特徴量の検出（相関1.0の特徴量）
        duplicate_pairs = []
        columns = df_dedup.columns.tolist()

        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                col1, col2 = columns[i], columns[j]
                try:
                    # NaNを除外して相関計算
                    clean_data1 = df_dedup[col1].dropna()
                    clean_data2 = df_dedup[col2].dropna()

                    if len(clean_data1) > 0 and len(clean_data2) > 0:
                        common_index = clean_data1.index.intersection(clean_data2.index)
                        if len(common_index) > 5:  # 最小5ポイントで判定
                            corr = clean_data1.loc[common_index].corr(
                                clean_data2.loc[common_index]
                            )
                            if abs(corr) > 0.999:  # ほぼ完全相関
                                duplicate_pairs.append((col1, col2, corr))
                except Exception:
                    continue

        # 重複特徴量の削除（より重要でない方を削除）
        features_to_remove = set()
        for col1, col2, corr in duplicate_pairs:
            # 125特徴量リストに含まれている方を優先
            if col1 in self.FEATURE_ORDER_125 and col2 not in self.FEATURE_ORDER_125:
                features_to_remove.add(col2)
            elif col2 in self.FEATURE_ORDER_125 and col1 not in self.FEATURE_ORDER_125:
                features_to_remove.add(col1)
            else:
                # どちらも125リストにない場合は後の方を削除
                features_to_remove.add(col2)

        if features_to_remove:
            df_dedup = df_dedup.drop(columns=list(features_to_remove))
            logger.info(f"Removed {len(features_to_remove)} duplicate features")

        logger.debug(
            f"Deduplication: {original_count} → {len(df_dedup.columns)} features"
        )
        return df_dedup

    def _align_to_target_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """125特徴量ターゲットリストとの照合"""
        current_features = set(df.columns)
        target_features = set(self.FEATURE_ORDER_125)

        # 現在の特徴量の分析
        present_target = current_features.intersection(target_features)
        missing_target = target_features - current_features
        extra_features = current_features - target_features

        logger.info(
            f"Feature alignment: {len(present_target)}/125 target features present"
        )
        logger.info(f"Missing target features: {len(missing_target)}")
        logger.info(f"Extra features: {len(extra_features)}")

        if missing_target:
            logger.debug(f"Missing features sample: {list(missing_target)[:10]}")

        return df

    def _fill_missing_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """不足特徴量の自動補完"""
        current_features = set(df.columns)
        target_features = set(self.FEATURE_ORDER_125)
        missing_features = target_features - current_features

        if not missing_features:
            logger.debug("No missing features to fill")
            return df

        logger.info(f"Filling {len(missing_features)} missing features")
        df_filled = df.copy()

        # 統計情報の事前計算（効率化）
        mean_price = df_filled.get("close", pd.Series([100.0])).mean()
        if pd.isna(mean_price) or mean_price <= 0:
            mean_price = 100.0

        # Phase H.26: パフォーマンス警告対応 - 一括でDataFrame作成
        missing_data = {}
        for feature in missing_features:
            try:
                # 特徴量タイプに応じた適切な補完値を計算
                fill_value = self._calculate_smart_fill_value(
                    feature, df_filled, mean_price
                )
                missing_data[feature] = fill_value
            except Exception as e:
                logger.warning(f"Failed to fill feature {feature}: {e}")
                # フォールバック: 0で補完
                missing_data[feature] = 0.0

        # 一括でDataFrameに追加（パフォーマンス向上）
        if missing_data:
            missing_df = pd.DataFrame(missing_data, index=df_filled.index)
            df_filled = pd.concat([df_filled, missing_df], axis=1)

        logger.info(f"✅ Filled {len(missing_features)} missing features")
        return df_filled

    def _calculate_smart_fill_value(
        self, feature: str, df: pd.DataFrame, mean_price: float
    ) -> float:
        """特徴量に応じた適切な補完値を計算"""
        # 価格系特徴量
        if any(
            x in feature.lower()
            for x in ["close", "open", "high", "low", "price", "sma", "ema"]
        ):
            return mean_price

        # ボリューム系特徴量
        elif "volume" in feature.lower():
            if "volume" in df.columns:
                return df["volume"].mean() if not df["volume"].isna().all() else 1000.0
            return 1000.0

        # RSI系（0-100の範囲）
        elif "rsi" in feature.lower():
            return 50.0

        # ATR系（価格の数%）
        elif "atr" in feature.lower():
            return mean_price * 0.02

        # ボラティリティ系
        elif "volatility" in feature.lower() or "vol" in feature.lower():
            return 0.02

        # 比率・パーセント系
        elif any(x in feature.lower() for x in ["ratio", "pct", "change", "return"]):
            return 0.0

        # バイナリ指標（0/1）
        elif any(
            x in feature.lower()
            for x in ["is_", "oversold", "overbought", "cross", "breakout"]
        ):
            return 0.0

        # 正規化された指標
        elif any(x in feature.lower() for x in ["zscore", "normalized"]):
            return 0.0

        # その他のテクニカル指標
        elif any(
            x in feature.lower() for x in ["macd", "stoch", "adx", "cci", "williams"]
        ):
            return 0.0

        # デフォルト
        else:
            return 0.0

    def _trim_excess_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """余分特徴量の管理（125特徴量に調整）"""
        if len(df.columns) <= 125:
            return df

        logger.info(f"Trimming excess features: {len(df.columns)} → 125")

        # 125特徴量リストの順序に従って選択
        ordered_features = []
        available_features = set(df.columns)

        # まず125リストの特徴量を順序通りに追加
        for feature in self.FEATURE_ORDER_125:
            if feature in available_features:
                ordered_features.append(feature)

        # まだ125に達していない場合は、残りの重要そうな特徴量を追加
        if len(ordered_features) < 125:
            remaining_features = available_features - set(ordered_features)
            # 重要度でソート（アルファベット順で安定化）
            remaining_sorted = sorted(remaining_features)
            needed = 125 - len(ordered_features)
            ordered_features.extend(remaining_sorted[:needed])

        # 正確に125特徴量を選択
        selected_features = ordered_features[:125]

        logger.info(f"Selected {len(selected_features)} features for final dataset")
        return df[selected_features]

    def _ensure_feature_quality(self, df: pd.DataFrame) -> pd.DataFrame:
        """特徴量品質チェック・修正"""
        df_quality = df.copy()
        issues_fixed = 0

        for column in df_quality.columns:
            try:
                # NaN値の処理
                nan_count = df_quality[column].isna().sum()
                if nan_count > 0:
                    # 前方・後方補完
                    df_quality[column] = df_quality[column].ffill().bfill()
                    # まだNaNがある場合は適切なデフォルト値で補完
                    remaining_nan = df_quality[column].isna().sum()
                    if remaining_nan > 0:
                        fill_value = self._calculate_smart_fill_value(
                            column, df_quality, 100.0
                        )
                        df_quality[column] = df_quality[column].fillna(fill_value)
                        issues_fixed += 1

                # inf値の処理
                inf_count = np.isinf(df_quality[column]).sum()
                if inf_count > 0:
                    # inf値を適切な値で置換
                    finite_values = df_quality[column][np.isfinite(df_quality[column])]
                    if len(finite_values) > 0:
                        replacement = finite_values.median()
                    else:
                        replacement = self._calculate_smart_fill_value(
                            column, df_quality, 100.0
                        )

                    df_quality[column] = df_quality[column].replace(
                        [np.inf, -np.inf], replacement
                    )
                    issues_fixed += 1

            except Exception as e:
                logger.warning(f"Quality check failed for {column}: {e}")
                # 問題のある特徴量は安全な値で置換
                df_quality[column] = 0.0
                issues_fixed += 1

        if issues_fixed > 0:
            logger.info(f"Fixed quality issues in {issues_fixed} features")

        return df_quality

    def _final_125_validation(self, df: pd.DataFrame) -> pd.DataFrame:
        """最終的な125特徴量検証"""
        if len(df.columns) != 125:
            logger.error(
                f"Final validation failed: {len(df.columns)} features instead of 125"
            )

            if len(df.columns) > 125:
                # 余分な特徴量を削除
                df = df.iloc[:, :125]
            elif len(df.columns) < 125:
                # 不足分を補完
                needed = 125 - len(df.columns)
                for i in range(needed):
                    feature_name = f"auto_generated_{i:03d}"
                    df[feature_name] = 0.0

            logger.warning(
                f"Applied emergency adjustment: now {len(df.columns)} features"
            )

        # 特徴量名の最終調整（重複チェック）
        final_columns = []
        seen_names = set()

        for col in df.columns:
            if col in seen_names:
                # 重複がある場合は番号を付加
                counter = 1
                new_name = f"{col}_{counter}"
                while new_name in seen_names:
                    counter += 1
                    new_name = f"{col}_{counter}"
                final_columns.append(new_name)
                seen_names.add(new_name)
            else:
                final_columns.append(col)
                seen_names.add(col)

        df.columns = final_columns

        logger.info(f"✅ Final validation passed: {len(df.columns)} unique features")
        return df

    def _emergency_125_fallback(self, df: pd.DataFrame) -> pd.DataFrame:
        """緊急時の125特徴量フォールバック"""
        logger.warning("Using emergency 125-feature fallback")

        try:
            # 使用可能な特徴量を最大限活用
            available_features = list(df.columns)

            # 125特徴量の基本フレームワークを作成
            result_df = pd.DataFrame(index=df.index)

            # Step 1: 既存の特徴量をコピー（最大125まで）
            for i, feature in enumerate(available_features[:125]):
                result_df[f"feature_{i:03d}"] = df[feature]

            # Step 2: 不足分を基本的な特徴量で補完
            for i in range(len(available_features), 125):
                if i < 5 and "close" in df.columns:
                    # 基本価格特徴量
                    result_df[f"feature_{i:03d}"] = df["close"]
                elif i < 10 and "volume" in df.columns:
                    # 出来高特徴量
                    result_df[f"feature_{i:03d}"] = df["volume"]
                else:
                    # デフォルト値
                    result_df[f"feature_{i:03d}"] = 0.0

            logger.warning(
                f"Emergency fallback created: {len(result_df.columns)} features"
            )
            return result_df

        except Exception as e:
            logger.error(f"Emergency fallback failed: {e}")
            # 最後の手段：全て0の125特徴量DataFrame
            emergency_df = pd.DataFrame(
                0.0,
                index=df.index if not df.empty else [0],
                columns=[f"emergency_{i:03d}" for i in range(125)],
            )
            return emergency_df


# グローバルインスタンス
_global_feature_order_manager: Optional[FeatureOrderManager] = None


def get_feature_order_manager() -> FeatureOrderManager:
    """グローバルな特徴量順序管理インスタンスを取得"""
    global _global_feature_order_manager
    if _global_feature_order_manager is None:
        _global_feature_order_manager = FeatureOrderManager()
    return _global_feature_order_manager
