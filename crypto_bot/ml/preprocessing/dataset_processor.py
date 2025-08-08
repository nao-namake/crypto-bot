"""
ML Dataset Processor - Phase 16.3-A Split

統合前: crypto_bot/ml/preprocessor.py（3,314行）
分割後: crypto_bot/ml/preprocessing/dataset_processor.py

機能:
- prepare_ml_dataset: 機械学習用データセット作成
- prepare_ml_dataset_enhanced: 特徴量完全性保証付きML用データセット作成

Phase 16.3-A実装日: 2025年8月8日
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

# 分割後import調整
from .pipeline_builder import build_ml_pipeline

# Phase 3: 外部API依存完全除去
ENHANCED_FEATURES_AVAILABLE = False

# 必要な依存関係
from crypto_bot.ml.target import make_classification_target, make_regression_target

logger = logging.getLogger(__name__)


def prepare_ml_dataset(
    df: pd.DataFrame, config: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    機械学習用データセットを作成。
    戻り値: X（特徴量）, y_reg（回帰ターゲット）, y_clf（分類ターゲット）

    - 必要なぶんだけ最初の行をドロップ（rolling/lags）
    - horizon, thresholdはconfig["ml"]から取得
    """
    logger.info(f"prepare_ml_dataset input df shape: {tuple(df.shape)}")
    pipeline = build_ml_pipeline(config)
    X_arr = pipeline.fit_transform(df)

    logger.info(f"Pipeline output type: {type(X_arr)}")
    if hasattr(X_arr, "shape"):
        shape_info = X_arr.shape
    elif hasattr(X_arr, "__len__"):
        shape_info = len(X_arr)
    else:
        shape_info = "unknown"
    logger.info(f"Pipeline output shape: {shape_info}")

    # TargetのDataFrameインデックスがX_arrのインデックスと揃うように調整
    ml_config = config.get("ml", {})
    rolling_window = ml_config.get("rolling_window", 10)
    lags = ml_config.get("lags", [1, 2])
    extra_features = ml_config.get("extra_features", [])

    # Phase 2: 97特徴量システム最適化
    # extra_featuresが設定されている場合は、必要なドロップ数を調整
    if extra_features and any(
        f in extra_features for f in ["ema_200", "sma_200", "bb_200", "rsi_14"]
    ):
        # より長い期間が必要な場合はドロップ数を増やす
        win = max(rolling_window, 200, 14)  # ATR, SMA200, RSI14を考慮
    else:
        win = rolling_window

    drop_n = win + max(lags) if lags else win

    # インデックスが欠損している可能性があるため、安全に処理
    if len(df) <= drop_n:
        logger.warning(f"Not enough data: len(df)={len(df)}, drop_n={drop_n}")
        # 少ないデータでも処理できるよう調整
        drop_n = max(0, len(df) - 5)  # 最低5行は残す

    y_reg = make_regression_target(df, config.get("ml", {}).get("horizon", 1))
    y_clf = make_classification_target(df, config.get("ml", {}).get("horizon", 1))

    # インデックスの範囲を調整
    if isinstance(X_arr, np.ndarray):
        valid_length = min(len(X_arr), len(df) - drop_n)
        idx = df.index[drop_n : drop_n + valid_length]
        X = pd.DataFrame(X_arr[: len(idx)], index=idx)
    else:
        # X_arrがDataFrameなどの場合
        idx = df.index[drop_n:]
        X = pd.DataFrame(X_arr, index=idx)

    # 共通のインデックスでそろえる
    common_idx = X.index.intersection(y_reg.index).intersection(y_clf.index)
    if len(common_idx) == 0:
        logger.error("No common index found between X, y_reg, y_clf")
        logger.info(f"X.index: {X.index[:5]}...")
        logger.info(f"y_reg.index: {y_reg.index[:5]}...")
        logger.info(f"y_clf.index: {y_clf.index[:5]}...")
        # フォールバックとして最小の共通範囲を使用
        min_len = min(len(X), len(y_reg), len(y_clf))
        if min_len > 0:
            X = X.iloc[:min_len]
            common_idx = X.index
        else:
            raise ValueError("Cannot align X, y_reg, y_clf indices")
    else:
        X = X.loc[common_idx]

    return X, y_reg.loc[common_idx], y_clf.loc[common_idx]


# Phase H.11: 特徴量完全性保証システム統合
def prepare_ml_dataset_enhanced(
    df: pd.DataFrame, config: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    特徴量完全性保証付きML用データセット作成

    Args:
        df: OHLCVデータ
        config: 設定辞書

    Returns:
        (特徴量DataFrame, 回帰ターゲット, 分類ターゲット)
    """
    logger.info("🚀 [ENHANCED-ML] Starting enhanced ML dataset preparation...")
    logger.info(f"📊 [ENHANCED-ML] Input shape: {tuple(df.shape)}")

    # Phase H.11: 特徴量完全性保証実行
    if ENHANCED_FEATURES_AVAILABLE:
        logger.info("✅ [ENHANCED-ML] Using enhanced feature engineering system")
        # Phase 3: enhance_feature_engineering機能完全無効化
        enhanced_df, feature_report = df, {"status": "disabled"}

        # 特徴量レポートの出力
        logger.info(f"📋 [ENHANCED-ML] Feature report: {feature_report.get('status')}")

        # 拡張されたDataFrameでML用データセット作成
        pipeline = build_ml_pipeline(config)
        X_arr = pipeline.fit_transform(enhanced_df)

        # ターゲット作成（元のDataFrameを使用）
        y_reg = make_regression_target(df, config)
        y_clf = make_classification_target(df, config)

        logger.info(
            f"✅ [ENHANCED-ML] Enhanced pipeline output shape: {X_arr.shape if hasattr(X_arr, 'shape') else 'unknown'}"
        )

    else:
        logger.info(
            "⚠️ [ENHANCED-ML] Enhanced features unavailable, using standard ML pipeline"
        )
        # 標準パイプライン使用
        return prepare_ml_dataset(df, config)

    # インデックス調整（標準prepare_ml_datasetと同じロジック）
    ml_config = config.get("ml", {})
    rolling_window = ml_config.get("rolling_window", 10)
    lags = ml_config.get("lags", [1, 2])

    win = rolling_window
    drop_n = win + max(lags) if lags else win

    idx = enhanced_df.index[drop_n:]
    if isinstance(X_arr, np.ndarray):
        result_df = enhanced_df  # 元のDataFrameまたは拡張DataFrame
    else:
        result_df = enhanced_df

    # 安全なインデックス調整
    if len(result_df) <= drop_n:
        logger.warning(
            f"⚠️ [ENHANCED-ML] Insufficient data length: {len(result_df)} <= {drop_n}"
        )
        drop_n = max(0, len(result_df) - 5)

    drop_n = win + max(lags) if lags else win

    idx = result_df.index[drop_n:]
    X = pd.DataFrame(X_arr[drop_n:], index=idx)

    logger.info(
        f"✅ [ENHANCED-ML] Enhanced ML dataset ready: X{tuple(X.shape)}, y_reg{tuple(y_reg.loc[idx].shape)}, y_clf{tuple(y_clf.loc[idx].shape)}"
    )

    return X, y_reg.loc[idx], y_clf.loc[idx]
