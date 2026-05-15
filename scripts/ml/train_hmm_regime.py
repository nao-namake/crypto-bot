"""
Phase 89-γ C6: HMM レジーム分類器のオフライン学習スクリプト.

履歴 OHLCV から returns_1 / atr_14 / volume_ratio を計算し、3 状態 Gaussian HMM を学習。
models/regime/hmm_3state.pkl に保存する。

実行:
    python scripts/ml/train_hmm_regime.py [--days 180] [--dry-run] [--symbol BTC/JPY]

CI 統合:
    .github/workflows/model-training.yml で create_ml_models.py 学習後に呼ばれる。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートを sys.path に追加（src.* import のため）
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.logger import get_logger  # noqa: E402
from src.core.services.hmm_regime_classifier import HMMRegimeClassifier, has_hmmlearn  # noqa: E402


def compute_hmm_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """HMM 入力特徴量 (returns_1 / atr_14 / volume_ratio) を計算.

    Args:
        ohlcv: open/high/low/close/volume を含む DataFrame

    Returns:
        feature_names=["returns_1", "atr_14", "volume_ratio"] の DataFrame
    """
    df = ohlcv.copy()
    df["returns_1"] = df["close"].pct_change().fillna(0.0)

    # ATR(14)
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(window=14, min_periods=1).mean().fillna(0.0)

    # volume_ratio: 現在 volume / 20 期間移動平均
    vol_ma20 = df["volume"].rolling(window=20, min_periods=1).mean()
    df["volume_ratio"] = (df["volume"] / vol_ma20).replace([np.inf, -np.inf], 1.0).fillna(1.0)

    return df[["returns_1", "atr_14", "volume_ratio"]].copy()


async def load_ohlcv(days: int, symbol: str) -> pd.DataFrame:
    """履歴 OHLCV を読み込む（create_ml_models.py と同じ csv path）.

    Returns:
        open/high/low/close/volume を持つ DataFrame
    """
    csv_path = Path("src/backtest/data/historical/BTC_JPY_15m.csv")
    if not csv_path.exists():
        from src.backtest.data.historical_data_collector import HistoricalDataCollector

        collector = HistoricalDataCollector()
        await collector.collect_data(symbol=symbol, days=days, timeframes=["15m"])

    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df[["open", "high", "low", "close", "volume"]].copy()


async def train(days: int, symbol: str, dry_run: bool, output_path: Path) -> int:
    """HMM 学習のメインロジック."""
    logger = get_logger()

    if not has_hmmlearn():
        logger.error("❌ hmmlearn 未インストール → HMM 学習スキップ")
        return 1

    logger.info(f"📊 Phase 89-γ HMM 学習開始: days={days}, symbol={symbol}")

    ohlcv = await load_ohlcv(days, symbol)
    if len(ohlcv) < 100:
        logger.error(f"❌ サンプル数不足: {len(ohlcv)} < 100")
        return 1

    features = compute_hmm_features(ohlcv)
    logger.info(
        f"✅ HMM 入力特徴量: shape={features.shape}, "
        f"columns={list(features.columns)}, "
        f"NaN率={(features.isna().sum().sum() / features.size * 100):.2f}%"
    )

    if dry_run:
        logger.info("🧪 dry-run モード → fit + save をスキップ")
        return 0

    hmm = HMMRegimeClassifier(
        n_states=3,
        feature_names=["returns_1", "atr_14", "volume_ratio"],
        random_state=42,
        n_iter=100,
    )
    hmm.fit_offline(features, min_samples=100)
    hmm.save(str(output_path))
    logger.info(f"✅ Phase 89-γ HMM 保存完了: {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 89-γ HMM レジーム分類器学習")
    parser.add_argument("--days", type=int, default=180, help="学習に使う履歴日数")
    parser.add_argument("--symbol", default="BTC/JPY", help="対象シンボル")
    parser.add_argument("--dry-run", action="store_true", help="fit/save スキップ")
    parser.add_argument(
        "--output",
        default="models/regime/hmm_3state.pkl",
        help="保存先 pickle パス",
    )
    args = parser.parse_args()

    return asyncio.run(
        train(
            days=args.days,
            symbol=args.symbol,
            dry_run=args.dry_run,
            output_path=Path(args.output),
        )
    )


if __name__ == "__main__":
    sys.exit(main())
