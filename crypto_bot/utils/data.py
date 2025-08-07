"""
Data preparation utilities
"""

import logging
from typing import Any, Dict, Tuple

import pandas as pd

from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.ml.preprocessor import FeatureEngineer

logger = logging.getLogger(__name__)


def prepare_data(
    cfg: Dict[str, Any],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    設定に基づいてデータを準備する

    Returns:
        Tuple[train_df, val_df, test_df]
    """
    dd = cfg.get("data", {})

    # データ取得
    if dd.get("exchange") == "csv" or dd.get("csv_path"):
        fetcher = MarketDataFetcher(csv_path=dd.get("csv_path"))
        df = fetcher.get_price_df(
            since=dd.get("since"),
            limit=dd.get("limit"),
        )
    else:
        fetcher = MarketDataFetcher(
            exchange_id=dd.get("exchange"),
            symbol=dd.get("symbol"),
            ccxt_options=dd.get("ccxt_options"),
        )
        # ベースタイムフレーム決定
        base_timeframe = "1h"  # デフォルト
        if (
            "multi_timeframe_data" in dd
            and "base_timeframe" in dd["multi_timeframe_data"]
        ):
            base_timeframe = dd["multi_timeframe_data"]["base_timeframe"]
        else:
            timeframe_raw = dd.get("timeframe", "1h")
            if timeframe_raw == "4h":
                base_timeframe = "1h"  # 4h要求を強制的に1hに変換
            else:
                base_timeframe = timeframe_raw

        df = fetcher.get_price_df(
            timeframe=base_timeframe,
            since=dd.get("since"),
            limit=dd.get("limit"),
            paginate=dd.get("paginate", True),
            per_page=dd.get("per_page", 100),
        )

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # データクリーニング
    window = cfg["ml"].get("feat_period", 14)
    df = DataPreprocessor.clean(df, timeframe=dd.get("timeframe", "1h"), window=window)

    # 分割比率
    train_ratio = dd.get("train_ratio", 0.6)
    val_ratio = dd.get("val_ratio", 0.2)

    # データ分割
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]

    # Phase 2.4: 97特徴量検証
    fe = FeatureEngineer(cfg["ml"])

    # 特徴量生成テスト
    if len(train_df) > 100:
        sample_df = train_df.tail(100).copy()
        features_df = fe.fit_transform(sample_df)
        logger.info(f"Generated features shape: {features_df.shape}")
        logger.info(
            f"Feature columns: {features_df.columns.tolist()[:10]}..."
        )  # 最初の10個表示

    logger.info(
        f"Data split - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}"
    )

    return train_df, val_df, test_df
