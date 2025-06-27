# crypto_bot/strategy/ml_strategy.py
# 説明:
# 学習済みMLモデル（例: LightGBMなど）の予測結果と
# もちぽよアラート（RCI×MACD逆張りテクニカルシグナル）の両方を利用し、
# 売買シグナル（BUY/SELL/EXIT）を自動で返す戦略クラスです。
# 特徴量エンジニアリング、標準化、シグナル判定までを担当します。
#
# 使用例:
#   - バックテスト・実運用どちらでも利用
#   - config（設定）からしきい値やモデルパスを受け取り動作

from __future__ import annotations

import logging

import pandas as pd
from sklearn.preprocessing import StandardScaler

from crypto_bot.execution.engine import Position, Signal
from crypto_bot.ml.model import MLModel
from crypto_bot.ml.preprocessor import FeatureEngineer

from .base import StrategyBase

logger = logging.getLogger(__name__)


class MLStrategy(StrategyBase):
    """
    学習済みモデル＋もちぽよテクニカルシグナルのハイブリッド判定で
    売買シグナルを返す戦略。
    """

    def __init__(self, model_path: str, threshold: float = None, config: dict = None):
        self.config = config or {}
        if threshold is not None:
            self.threshold = threshold
        else:
            self.threshold = self.config.get("threshold", 0.0)
        logger.debug("MLStrategy initialised with threshold = %.4f", self.threshold)
        self.model = MLModel.load(model_path)
        self.feature_engineer = FeatureEngineer(self.config)
        self.scaler = StandardScaler()

    def logic_signal(self, price_df: pd.DataFrame, position: Position) -> Signal:
        logger.debug("Input DataFrame columns: %s", price_df.columns.tolist())
        logger.debug("Input DataFrame head (3 rows):\n%s", price_df.head(3).to_string())

        dynamic_th = self.threshold
        logger.debug("Using threshold = %.4f", dynamic_th)

        # 特徴量エンジニアリング
        feat_df = self.feature_engineer.transform(price_df)
        if feat_df.empty:
            logger.warning("Empty features DataFrame after transformation")
            return Signal()

        # スケーリング
        scaled = self.scaler.fit_transform(feat_df.values)
        X_df = pd.DataFrame(scaled, index=feat_df.index, columns=feat_df.columns)

        # 直近行
        last_X = X_df.iloc[[-1]]
        price = float(price_df["close"].iloc[-1])

        # --- もちぽよシグナルの判定 ---
        has_mochipoyo_long = "mochipoyo_long_signal" in last_X.columns
        has_mochipoyo_short = "mochipoyo_short_signal" in last_X.columns
        mp_long = (
            int(last_X["mochipoyo_long_signal"].iloc[0]) if has_mochipoyo_long else 0
        )
        mp_short = (
            int(last_X["mochipoyo_short_signal"].iloc[0]) if has_mochipoyo_short else 0
        )

        # --- MLモデルの確率予測 ---
        prob = self.model.predict_proba(last_X)[0, 1]
        logger.info("Predicted ↑ prob = %.4f", prob)

        # ポジション有無で判定
        position_exists = position is not None and position.exist
        if position_exists:
            # ポジション有りの場合はexit条件を緩和（より早めの利確・損切り）
            exit_threshold = 0.5 - (dynamic_th * 0.7)
            if prob < exit_threshold:  # exitしきい値を緩和
                logger.info(
                    "Position EXIT signal: prob=%.4f < %.4f", prob, exit_threshold
                )
                return Signal(side="SELL", price=price)
            return None

        # シグナル統合ロジック（OR条件でより積極的に）
        ml_long_signal = prob > 0.5 + dynamic_th
        ml_short_signal = prob < 0.5 - dynamic_th
        # もちぽよシグナル OR MLシグナル（どちらかが条件満たせばエントリー）
        if mp_long or ml_long_signal:
            confidence = max(prob - 0.5, mp_long * 0.1)  # 信頼度計算
            logger.info(
                "LONG signal: mochipoyo=%d, ml_prob=%.4f, " "confidence=%.4f",
                mp_long,
                prob,
                confidence,
            )
            return Signal(side="BUY", price=price)
        if mp_short or ml_short_signal:
            confidence = max(0.5 - prob, mp_short * 0.1)  # 信頼度計算
            logger.info(
                "SHORT signal: mochipoyo=%d, ml_prob=%.4f, " "confidence=%.4f",
                mp_short,
                prob,
                confidence,
            )
            return Signal(side="SELL", price=price)

        # 中間的なシグナル（確率が中央付近でも弱いシグナルとして扱う）
        if prob > 0.52:  # 52%以上で弱いBUYシグナル
            logger.info("Weak LONG signal: prob=%.4f", prob)
            return Signal(side="BUY", price=price)
        elif prob < 0.48:  # 48%以下で弱いSELLシグナル
            logger.info("Weak SHORT signal: prob=%.4f", prob)
            return Signal(side="SELL", price=price)

        return None
