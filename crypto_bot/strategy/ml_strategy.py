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
        mp_long = int(last_X["mochipoyo_long_signal"].iloc[0]) if has_mochipoyo_long else 0
        mp_short = int(last_X["mochipoyo_short_signal"].iloc[0]) if has_mochipoyo_short else 0

        # --- MLモデルの確率予測 ---
        prob = self.model.predict_proba(last_X)[0, 1]
        logger.info("Predicted ↑ prob = %.4f", prob)

        # ポジション有無で判定
        if position.exist:
            # Exit
            if prob < 0.5 - dynamic_th:
                logger.info("Exit signal: SELL (prob=%.4f < %.4f)", prob, 0.5 - dynamic_th)
                return Signal(side="SELL", price=price)
            return Signal()
        else:
            # Entry: どちらか1つでもシグナルが出れば即返却（もちぽよ優先）
            if mp_long == 1:
                logger.info("Entry signal: BUY by mochipoyo_long_signal")
                return Signal(side="BUY", price=price)
            if mp_short == 1:
                logger.info("Entry signal: SELL by mochipoyo_short_signal")
                return Signal(side="SELL", price=price)
            # MLシグナル
            if prob > 0.5 + dynamic_th:
                logger.info("Entry signal: BUY (prob=%.4f > %.4f)", prob, 0.5 + dynamic_th)
                return Signal(side="BUY", price=price)
            if prob < 0.5 - dynamic_th:
                logger.info("Entry signal: SELL (prob=%.4f < %.4f)", prob, 0.5 - dynamic_th)
                return Signal(side="SELL", price=price)
            return Signal()
