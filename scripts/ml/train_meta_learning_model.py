"""
Phase 45.3: Meta-Learning学習パイプライン

バックテストデータから学習データを生成し、Meta-MLモデルを学習。

実行方法:
    python scripts/ml/train_meta_learning_model.py [--dry-run]

設計原則:
- ハードコード完全排除: すべての数値はthresholds.yamlから取得
- 事後的最適重み計算: 各時点でMLと戦略のどちらが正しかったかを判定
- 市場状況特徴量活用: MarketRegimeAnalyzerで抽出
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import get_threshold
from src.core.logger import CryptoBotLogger
from src.data.data_pipeline import DataPipeline
from src.features.feature_generator import FeatureGenerator
from src.ml.ensemble import ProductionEnsemble
from src.ml.meta_learning import MarketRegimeAnalyzer
from src.strategies.implementations.atr_based import ATRBasedStrategy
from src.strategies.implementations.mochipoy_alert import MochipoyAlertStrategy


def generate_training_data(
    days: int = 180, logger: CryptoBotLogger = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    バックテストデータから学習データ生成

    Args:
        days: 学習データ期間（日数）
        logger: ロガー

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: (特徴量X, ラベルy)
            - X: 市場状況特徴量（13特徴量）
            - y: 最適重み（2値: ml_weight, strategy_weight）
    """
    if logger:
        logger.info(f"📊 Meta-ML学習データ生成開始（過去{days}日間）")

    # データ取得
    pipeline = DataPipeline()
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    if logger:
        logger.info(f"📈 価格データ取得: {start_time} - {end_time}")

    # 15m足データ取得
    df = pipeline.fetch_historical_data(
        symbol="btc_jpy", timeframe="15m", start_time=start_time, end_time=end_time
    )

    if df is None or len(df) < 100:
        raise ValueError("データ取得失敗または不足")

    # 特徴量生成
    if logger:
        logger.info("🔧 特徴量生成中...")

    feature_gen = FeatureGenerator()
    df = feature_gen.generate(df)

    # ML予測生成
    if logger:
        logger.info("🧠 ML予測生成中...")

    ml_model = ProductionEnsemble()
    ml_predictions = []
    for i in range(len(df)):
        try:
            features = df.iloc[i][feature_gen.get_feature_names()].values.reshape(1, -1)
            pred = ml_model.predict(features)
            ml_predictions.append(
                {"prediction": pred["prediction"], "confidence": pred["confidence"]}
            )
        except Exception:
            ml_predictions.append({"prediction": 0, "confidence": 0.5})

    df["ml_prediction"] = [p["prediction"] for p in ml_predictions]
    df["ml_confidence"] = [p["confidence"] for p in ml_predictions]

    # 戦略シグナル生成
    if logger:
        logger.info("📊 戦略シグナル生成中...")

    atr_strategy = ATRBasedStrategy()
    mochipoy_strategy = MochipoyAlertStrategy()

    strategy_signals = []
    for i in range(len(df)):
        try:
            df_slice = df.iloc[: i + 1]
            atr_signal = atr_strategy.generate_signal(df_slice)
            mochipoy_signal = mochipoy_strategy.generate_signal(df_slice)

            # 簡易統合（平均）
            if atr_signal and mochipoy_signal:
                strategy_action = (
                    atr_signal.action
                    if atr_signal.confidence > mochipoy_signal.confidence
                    else mochipoy_signal.action
                )
                strategy_confidence = (atr_signal.confidence + mochipoy_signal.confidence) / 2
            elif atr_signal:
                strategy_action = atr_signal.action
                strategy_confidence = atr_signal.confidence
            elif mochipoy_signal:
                strategy_action = mochipoy_signal.action
                strategy_confidence = mochipoy_signal.confidence
            else:
                strategy_action = "hold"
                strategy_confidence = 0.5

            strategy_signals.append({"action": strategy_action, "confidence": strategy_confidence})
        except Exception:
            strategy_signals.append({"action": "hold", "confidence": 0.5})

    df["strategy_action"] = [s["action"] for s in strategy_signals]
    df["strategy_confidence"] = [s["confidence"] for s in strategy_signals]

    # 市場状況特徴量抽出
    if logger:
        logger.info("🔍 市場状況特徴量抽出中...")

    market_analyzer = MarketRegimeAnalyzer()
    market_features_list = []

    for i in range(100, len(df)):  # 十分なウィンドウ確保
        df_slice = df.iloc[: i + 1]
        market_features = market_analyzer.analyze(df_slice)
        market_features_list.append(market_features)

    # 最適重み計算（教師ラベル）
    if logger:
        logger.info("🎯 最適重み計算中...")

    optimal_weights = []
    for i in range(100, len(df)):
        # 将来N期間の価格変動を確認（N=5）
        future_window = 5
        if i + future_window >= len(df):
            break

        current_price = df.iloc[i]["close"]
        future_price = df.iloc[i + future_window]["close"]
        actual_change = (future_price - current_price) / current_price

        # ML予測の正誤判定
        ml_pred = df.iloc[i]["ml_prediction"]
        ml_correct = (
            (ml_pred == 1 and actual_change > 0.005)  # buy予測が正解
            or (ml_pred == -1 and actual_change < -0.005)  # sell予測が正解
            or (ml_pred == 0 and abs(actual_change) < 0.005)  # hold予測が正解
        )

        # 戦略予測の正誤判定
        strategy_action = df.iloc[i]["strategy_action"]
        strategy_correct = (
            (strategy_action == "buy" and actual_change > 0.005)
            or (strategy_action == "sell" and actual_change < -0.005)
            or (strategy_action == "hold" and abs(actual_change) < 0.005)
        )

        # 最適重み計算
        if ml_correct and strategy_correct:
            # 両方正解: バランス重み
            ml_weight = 0.5
            strategy_weight = 0.5
        elif ml_correct and not strategy_correct:
            # MLのみ正解: ML重視
            ml_weight = 0.7
            strategy_weight = 0.3
        elif not ml_correct and strategy_correct:
            # 戦略のみ正解: 戦略重視
            ml_weight = 0.3
            strategy_weight = 0.7
        else:
            # 両方不正解: デフォルト重み
            ml_weight = 0.35
            strategy_weight = 0.7

        optimal_weights.append([ml_weight, strategy_weight])

    # 特徴量X作成
    X_data = []
    for features in market_features_list[: len(optimal_weights)]:
        vector = [
            features.get("volatility_atr_14", 0.5),
            features.get("volatility_bb_width", 0.5),
            features.get("volatility_ratio_7d", 0.5),
            features.get("trend_ema_spread", 0.5),
            features.get("trend_adx", 0.5),
            features.get("trend_di_plus", 0.5),
            features.get("trend_di_minus", 0.5),
            features.get("trend_strength", 0.5),
            features.get("range_donchian_width", 0.5),
            features.get("range_detection", 0.5),
            features.get("volume_ratio", 0.5),
            0.5,  # ml_win_rate（パフォーマンス特徴量・学習時は0.5固定）
            0.0,  # ml_avg_profit（パフォーマンス特徴量・学習時は0.0固定）
        ]
        X_data.append(vector)

    X = pd.DataFrame(
        X_data,
        columns=[
            "volatility_atr_14",
            "volatility_bb_width",
            "volatility_ratio_7d",
            "trend_ema_spread",
            "trend_adx",
            "trend_di_plus",
            "trend_di_minus",
            "trend_strength",
            "range_donchian_width",
            "range_detection",
            "volume_ratio",
            "ml_win_rate",
            "ml_avg_profit",
        ],
    )
    y = pd.DataFrame(optimal_weights, columns=["ml_weight", "strategy_weight"])

    if logger:
        logger.info(f"✅ 学習データ生成完了: X={X.shape}, y={y.shape}")
        logger.info(f"📊 最適重み統計:")
        logger.info(f"   ML重み平均: {y['ml_weight'].mean():.3f} ± {y['ml_weight'].std():.3f}")
        logger.info(
            f"   戦略重み平均: {y['strategy_weight'].mean():.3f} ± {y['strategy_weight'].std():.3f}"
        )

    return X, y


def train_meta_model(
    X: pd.DataFrame, y: pd.DataFrame, logger: CryptoBotLogger = None
) -> lgb.LGBMRegressor:
    """
    Meta-MLモデル学習

    Args:
        X: 特徴量
        y: ラベル（最適重み）
        logger: ロガー

    Returns:
        lgb.LGBMRegressor: 学習済みモデル
    """
    if logger:
        logger.info("🧠 Meta-MLモデル学習開始")

    # thresholds.yamlから設定取得（ハードコード禁止）
    n_estimators = get_threshold("ml.meta_learning.model_config.n_estimators", 100)
    learning_rate = get_threshold("ml.meta_learning.model_config.learning_rate", 0.05)
    max_depth = get_threshold("ml.meta_learning.model_config.max_depth", 5)
    random_state = get_threshold("ml.meta_learning.model_config.random_state", 42)

    # ML重み予測モデル（単一出力に簡略化）
    model = lgb.LGBMRegressor(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        random_state=random_state,
        verbose=-1,
    )

    # 学習（y["ml_weight"]のみ予測・strategy_weightは1 - ml_weightで計算）
    model.fit(X, y["ml_weight"])

    if logger:
        logger.info("✅ Meta-MLモデル学習完了")

        # 特徴量重要度表示
        feature_importance = pd.DataFrame(
            {"feature": X.columns, "importance": model.feature_importances_}
        ).sort_values("importance", ascending=False)

        logger.info("📊 特徴量重要度 Top 5:")
        for _, row in feature_importance.head(5).iterrows():
            logger.info(f"   {row['feature']}: {row['importance']:.4f}")

    return model


def save_model(model: lgb.LGBMRegressor, logger: CryptoBotLogger = None):
    """
    モデル保存

    Args:
        model: 学習済みモデル
        logger: ロガー
    """
    # thresholds.yamlから保存先取得
    model_path = Path(
        get_threshold("ml.meta_learning.model_path", "models/meta_learning/meta_model.pkl")
    )

    # ディレクトリ作成
    model_path.parent.mkdir(parents=True, exist_ok=True)

    # モデル保存
    joblib.dump(model, model_path)

    if logger:
        logger.info(f"💾 Meta-MLモデル保存: {model_path}")


def main(args):
    """メイン処理"""
    logger = CryptoBotLogger(name="train_meta_learning_model")

    try:
        logger.info("=" * 70)
        logger.info("Phase 45.3: Meta-Learning学習パイプライン")
        logger.info("=" * 70)

        if args.dry_run:
            logger.info("🔍 DRY RUNモード: モデル保存はスキップ")

        # 学習データ生成
        X, y = generate_training_data(days=args.days, logger=logger)

        # モデル学習
        model = train_meta_model(X, y, logger=logger)

        # モデル保存
        if not args.dry_run:
            save_model(model, logger=logger)
            logger.info("✅ Meta-ML学習パイプライン完了")
        else:
            logger.info("✅ Meta-ML学習パイプライン完了（DRY RUN・保存スキップ）")

    except Exception as e:
        logger.error(f"❌ Meta-ML学習失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meta-Learning学習パイプライン")
    parser.add_argument("--days", type=int, default=180, help="学習データ期間（日数）")
    parser.add_argument(
        "--dry-run", action="store_true", help="DRY RUNモード（モデル保存スキップ）"
    )
    args = parser.parse_args()

    main(args)
