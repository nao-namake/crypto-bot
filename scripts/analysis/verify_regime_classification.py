"""
市場レジーム分類精度検証スクリプト - Phase 52.4

MarketRegimeClassifierの分類精度を履歴データで検証。
レンジ/トレンド/高ボラティリティの検出精度を確認する。

設定管理: thresholds.yamlに検証パラメータ定義
期待結果: thresholds.yaml:analysis.regime_verification.target_rangesに定義
"""

import asyncio
import random
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config.threshold_manager import get_threshold
from src.core.logger import get_logger
from src.core.services.market_regime_classifier import MarketRegimeClassifier
from src.core.services.regime_types import RegimeType
from src.features.feature_generator import FeatureGenerator

logger = get_logger()


def load_historical_data(csv_path: str) -> pd.DataFrame:
    """
    履歴データを読み込み

    Args:
        csv_path: CSVファイルパス

    Returns:
        pd.DataFrame: 履歴データ
    """
    logger.info(f"📂 履歴データ読み込み: {csv_path}")
    df = pd.read_csv(csv_path)

    # タイムスタンプ列の処理
    if "datetime" in df.columns:
        # CSVに既にdatetimeカラムがある場合はそれを使用
        df["timestamp"] = pd.to_datetime(df["datetime"], errors="coerce")
    elif "timestamp_ms" in df.columns:
        # timestamp_msがある場合はミリ秒として変換
        df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", errors="coerce")
    elif "timestamp" in df.columns:
        # timestampカラムがある場合はそのまま変換を試みる
        # まず数値（ミリ秒）として試す
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
        except (ValueError, TypeError):
            # 文字列の可能性もあるので再試行
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # ソートとインデックス設定（FeatureGenerator用）
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)
        # インデックスをDatetimeIndexに設定（FeatureGeneratorが期待する形式）
        df = df.set_index("timestamp")

    logger.info(f"✅ データ読み込み完了: {len(df)}行")
    if isinstance(df.index, pd.DatetimeIndex):
        logger.info(f"   タイムスタンプ範囲: {df.index.min()} ~ {df.index.max()}")
    return df


async def generate_features_for_all_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    全行に対して特徴量を生成（非同期）

    Args:
        df: 履歴データ

    Returns:
        pd.DataFrame: 特徴量付きデータ
    """
    logger.info("📊 特徴量生成開始")
    generator = FeatureGenerator()

    all_features = []
    for i in range(len(df)):
        try:
            # i行目までのデータで特徴量生成
            partial_df = df.iloc[: i + 1].copy()
            features = await generator.generate_features(partial_df)

            # 最新行の特徴量を保存
            all_features.append(features.iloc[-1])
        except Exception as e:
            logger.warning(f"⚠️ 行{i}の特徴量生成失敗: {e}")
            # NaN行を追加（後でスキップ）
            all_features.append(pd.Series(dtype=float))

    # DataFrameに変換
    features_df = pd.DataFrame(all_features).reset_index(drop=True)
    logger.info(f"✅ 特徴量生成完了: {len(features_df)}行")
    return features_df


def classify_all_regimes(features_df: pd.DataFrame) -> list:
    """
    全行に対して市場レジーム分類を実行

    Args:
        features_df: 特徴量データ

    Returns:
        list[RegimeType]: 分類結果リスト
    """
    logger.info("🎯 市場レジーム分類開始")
    classifier = MarketRegimeClassifier()

    regimes = []
    for i in range(len(features_df)):
        try:
            # i行目までのデータで分類
            partial_df = features_df.iloc[: i + 1].copy()

            # 必須カラム確認
            required_columns = ["close", "high", "low", "atr_14", "adx_14"]
            if all(col in partial_df.columns for col in required_columns):
                regime = classifier.classify(partial_df)
                regimes.append(regime)
            else:
                # 必須カラムがない場合はNoneを追加
                regimes.append(None)
        except Exception as e:
            logger.warning(f"⚠️ 行{i}の分類失敗: {e}")
            regimes.append(None)

    logger.info(f"✅ 分類完了: {len(regimes)}行")
    return regimes


def calculate_regime_statistics(regimes: list) -> dict:
    """
    レジーム分類統計を計算

    Args:
        regimes: 分類結果リスト

    Returns:
        dict: 統計情報
    """
    # Noneを除外
    valid_regimes = [r for r in regimes if r is not None]
    total = len(valid_regimes)

    if total == 0:
        return {}

    stats = {
        "total": total,
        "tight_range": sum(1 for r in valid_regimes if r == RegimeType.TIGHT_RANGE),
        "normal_range": sum(1 for r in valid_regimes if r == RegimeType.NORMAL_RANGE),
        "trending": sum(1 for r in valid_regimes if r == RegimeType.TRENDING),
        "high_volatility": sum(1 for r in valid_regimes if r == RegimeType.HIGH_VOLATILITY),
    }

    # パーセンテージ計算
    stats["tight_range_pct"] = (stats["tight_range"] / total) * 100
    stats["normal_range_pct"] = (stats["normal_range"] / total) * 100
    stats["trending_pct"] = (stats["trending"] / total) * 100
    stats["high_volatility_pct"] = (stats["high_volatility"] / total) * 100

    # レンジ相場合計
    stats["range_total"] = stats["tight_range"] + stats["normal_range"]
    stats["range_total_pct"] = (stats["range_total"] / total) * 100

    return stats


def print_regime_statistics(stats: dict):
    """
    レジーム分類統計を表示

    Args:
        stats: 統計情報
    """
    logger.info("=" * 80)
    logger.info("📊 市場レジーム分類統計（Phase 51.2-New）")
    logger.info("=" * 80)

    # 空の辞書の場合（全行失敗）
    if not stats or "total" not in stats:
        logger.error("⚠️ 統計データがありません。全ての行で分類が失敗しました。")
        logger.error("   原因: 特徴量生成の失敗、または必須カラムの不足")
        logger.info("=" * 80)
        return

    logger.info(f"\n📈 総データ数: {stats['total']}行")

    logger.info("\n【レンジ相場】")
    logger.info(f"  📊 狭いレンジ: {stats['tight_range']}行 ({stats['tight_range_pct']:.2f}%)")
    logger.info(f"  📊 通常レンジ: {stats['normal_range']}行 ({stats['normal_range_pct']:.2f}%)")
    logger.info(f"  📊 レンジ合計: {stats['range_total']}行 ({stats['range_total_pct']:.2f}%)")

    logger.info("\n【トレンド相場】")
    logger.info(f"  📈 トレンド: {stats['trending']}行 ({stats['trending_pct']:.2f}%)")

    logger.info("\n【高ボラティリティ】")
    logger.info(f"  ⚠️ 高ボラ: {stats['high_volatility']}行 ({stats['high_volatility_pct']:.2f}%)")

    logger.info("\n" + "=" * 80)
    logger.info("🎯 目標達成確認")
    logger.info("=" * 80)

    # thresholds.yamlから目標値を取得
    range_min = get_threshold("analysis.regime_verification.target_ranges.range_market.min", 70)
    range_max = get_threshold("analysis.regime_verification.target_ranges.range_market.max", 80)
    trending_min = get_threshold(
        "analysis.regime_verification.target_ranges.trending_market.min", 15
    )
    trending_max = get_threshold(
        "analysis.regime_verification.target_ranges.trending_market.max", 20
    )
    volatility_min = get_threshold(
        "analysis.regime_verification.target_ranges.high_volatility.min", 5
    )
    volatility_max = get_threshold(
        "analysis.regime_verification.target_ranges.high_volatility.max", 10
    )

    # 目標値との比較
    range_target = range_min <= stats["range_total_pct"] <= range_max
    trending_target = trending_min <= stats["trending_pct"] <= trending_max
    volatility_target = volatility_min <= stats["high_volatility_pct"] <= volatility_max

    logger.info(
        f"  レンジ相場 {range_min}-{range_max}%: {'✅' if range_target else '⚠️'} ({stats['range_total_pct']:.2f}%)"
    )
    logger.info(
        f"  トレンド相場 {trending_min}-{trending_max}%: {'✅' if trending_target else '⚠️'} ({stats['trending_pct']:.2f}%)"
    )
    logger.info(
        f"  高ボラティリティ {volatility_min}-{volatility_max}%: {'✅' if volatility_target else '⚠️'} ({stats['high_volatility_pct']:.2f}%)"
    )

    # 総合判定
    all_targets = range_target and trending_target and volatility_target
    logger.info(f"\n  総合判定: {'✅ 目標達成' if all_targets else '⚠️ 要調整'}")
    logger.info("=" * 80)


def print_random_samples(
    df: pd.DataFrame, features_df: pd.DataFrame, regimes: list, sample_size: Optional[int] = None
):
    """
    ランダムサンプルを表示（手動検証用）

    Args:
        df: 履歴データ
        features_df: 特徴量データ
        regimes: 分類結果リスト
        sample_size: サンプル数（Noneの場合はthresholds.yamlから取得）
    """
    if sample_size is None:
        sample_size = get_threshold("analysis.regime_verification.sample_size", 50)

    logger.info("\n" + "=" * 80)
    logger.info(f"🔍 ランダムサンプル表示（{sample_size}件）")
    logger.info("=" * 80)

    # Noneでないインデックスを取得
    valid_indices = [i for i, r in enumerate(regimes) if r is not None]

    # ランダムサンプリング
    sample_indices = random.sample(valid_indices, min(sample_size, len(valid_indices)))
    sample_indices.sort()

    for idx in sample_indices:
        regime = regimes[idx]
        row = features_df.iloc[idx]

        # タイムスタンプ取得（indexから）
        if isinstance(df.index, pd.DatetimeIndex):
            timestamp = df.index[idx]
        else:
            timestamp = "N/A"

        # 主要指標取得
        close = row.get("close", 0)
        atr_14 = row.get("atr_14", 0)
        adx_14 = row.get("adx_14", 0)
        ema_20 = row.get("ema_20", 0)

        # ATR比計算
        atr_ratio = (atr_14 / close) if close > 0 else 0

        logger.info(f"\n行{idx} | {timestamp} | {regime.value}")
        logger.info(f"  価格: ¥{close:,.0f} | ATR: {atr_14:.2f} (比: {atr_ratio:.4f})")
        logger.info(f"  ADX: {adx_14:.2f} | EMA20: ¥{ema_20:,.0f}")

    logger.info("\n" + "=" * 80)


async def main(limit_rows: int = None):
    """
    メイン処理（非同期）

    Args:
        limit_rows: テスト用行数制限（Noneの場合は全行処理）
    """
    logger.info("🚀 Phase 52.4: 市場レジーム分類精度検証開始")

    # 1. 履歴データ読み込み（thresholds.yamlからデフォルトパス取得）
    csv_path = get_threshold(
        "analysis.regime_verification.default_data_path",
        "src/backtest/data/historical/BTC_JPY_4h.csv",
    )
    df = load_historical_data(csv_path)

    # テスト用: 行数制限
    if limit_rows is not None:
        logger.info(f"⚠️ テストモード: 最初の{limit_rows}行のみ処理")
        df = df.iloc[:limit_rows].copy()

    # 2. 特徴量生成
    features_df = await generate_features_for_all_rows(df)

    # 3. 市場レジーム分類
    regimes = classify_all_regimes(features_df)

    # 4. 統計計算
    stats = calculate_regime_statistics(regimes)

    # 5. 統計表示
    print_regime_statistics(stats)

    # 6. ランダムサンプル表示
    sample_size = min(50, len([r for r in regimes if r is not None]))
    print_random_samples(df, features_df, regimes, sample_size=sample_size)

    logger.info("\n✅ Phase 51.2-New: 市場レジーム分類精度検証完了")


if __name__ == "__main__":
    # 全データ処理（Phase 51.2-New 最終検証）
    # テストモードの場合は: asyncio.run(main(limit_rows=100))
    asyncio.run(main())
