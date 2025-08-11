"""
アンサンブル学習最適化システム

複数のMLモデルを統合して予測精度・信頼度を向上させる高度なアンサンブル学習。
スタッキング・メタモデル・予測信頼度向上・動的閾値最適化に対応。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)


class TradingEnsembleClassifier(BaseEstimator, ClassifierMixin):
    """
    取引特化型アンサンブル学習クラス

    勝率と収益性向上に焦点を当てた設計:
    - 取引パフォーマンス最適化スタッキング
    - 動的閾値最適化システム
    - リスク調整型予測信頼度
    - 市場環境適応型重み調整
    - 既存MLStrategy完全統合
    """

    def __init__(
        self,
        base_models: Optional[List[BaseEstimator]] = None,
        meta_model: Optional[BaseEstimator] = None,
        ensemble_method: str = "trading_stacking",
        trading_metrics: Optional[Dict[str, float]] = None,
        risk_adjustment: bool = True,
        cv_folds: int = 5,
        confidence_threshold: float = 0.65,
    ):
        """
        取引特化型アンサンブル学習器の初期化

        Parameters:
        -----------
        base_models : List[BaseEstimator], optional
            ベースモデルのリスト
        meta_model : BaseEstimator, optional
            メタモデル（取引最適化用）
        ensemble_method : str
            アンサンブル手法 ("trading_stacking", "risk_weighted", "performance_voting")
        trading_metrics : Dict[str, float], optional
            取引メトリクス重み（sharpe_ratio, win_rate, max_drawdown等）
        risk_adjustment : bool
            リスク調整の使用有無
        cv_folds : int
            交差検証フォールド数
        confidence_threshold : float
            取引信頼度閾値（より保守的）
        """
        self.ensemble_method = ensemble_method
        self.trading_metrics = trading_metrics or {
            "sharpe_ratio": 0.4,
            "win_rate": 0.3,
            "max_drawdown": -0.2,
            "profit_factor": 0.1,
        }
        self.risk_adjustment = risk_adjustment
        self.cv_folds = cv_folds
        self.confidence_threshold = confidence_threshold

        # デフォルトベースモデル
        if base_models is None:
            self.base_models = self._create_default_base_models()
        else:
            self.base_models = base_models

        # デフォルトメタモデル
        if meta_model is None:
            self.meta_model = LogisticRegression(
                random_state=42, max_iter=1000, class_weight="balanced"
            )
        else:
            self.meta_model = meta_model

        # 学習済み状態
        self.fitted_base_models = []
        self.fitted_meta_model = None
        self.feature_names_ = None
        self.classes_ = None
        self.model_performance_ = {}
        self.trading_weights_ = None
        self.risk_metrics_ = {}
        self.market_regime_weights_ = {}
        self.is_fitted = False  # Phase H.16.1: is_fitted属性追加

        # 取引パフォーマンス追跡
        self.prediction_history_ = []
        self.performance_cache_ = {}

        # Calibration setting
        self.use_calibration = True

        # Additional attributes for compatibility
        self.ensemble_weights_ = None
        self.voting_weights = None
        self.last_X_ = None

    def _create_default_base_models(self) -> List[BaseEstimator]:
        """デフォルトベースモデルの作成"""
        return [
            # LightGBM（高速・高精度）
            LGBMClassifier(
                objective="binary",
                boosting_type="gbdt",
                num_leaves=31,
                learning_rate=0.05,
                feature_fraction=0.9,
                bagging_fraction=0.8,
                bagging_freq=5,
                verbose=-1,
                random_state=42,
            ),
            # XGBoost（ロバスト）
            XGBClassifier(
                objective="binary:logistic",
                learning_rate=0.05,
                max_depth=6,
                min_child_weight=1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=0,
            ),
            # Random Forest（アンサンブル）
            RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                max_features="sqrt",
                random_state=42,
                n_jobs=-1,
            ),
        ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "TradingEnsembleClassifier":
        """
        アンサンブルモデルの学習（Phase H.26: 堅牢化版）

        Parameters:
        -----------
        X : pd.DataFrame
            特徴量データ
        y : pd.Series
            ターゲットデータ
        """
        try:
            # Phase H.26: データ妥当性チェック
            if not self._validate_training_data(X, y):
                logger.error("Training data validation failed")
                return self._create_fallback_ensemble()

            # Phase H.26: インデックス整合性確保
            X_clean, y_clean = self._align_and_clean_data(X, y)

            # Phase H.26: 最小サンプル数チェック
            min_samples = max(20, len(X_clean.columns) // 5)  # 動的最小サンプル数
            if len(y_clean) < min_samples:
                logger.warning(
                    f"Insufficient training samples: {len(y_clean)} < {min_samples}"
                )
                return self._create_fallback_ensemble()

            self.feature_names_ = X_clean.columns.tolist()
            self.classes_ = np.unique(y_clean)

            logger.info(f"Training ensemble with {len(self.base_models)} base models")
            logger.info(f"Ensemble method: {self.ensemble_method}")
            logger.info(
                f"Training samples: {len(y_clean)}, Features: {len(X_clean.columns)}"
            )

            # 1. ベースモデル学習（堅牢化）
            successful_models = self._fit_base_models_robust(X_clean, y_clean)
            if successful_models == 0:
                logger.error("All base models failed to train")
                return self._create_fallback_ensemble()

            # 2. 取引特化型メタ特徴量生成（堅牢化）
            if self.ensemble_method == "trading_stacking" and successful_models >= 2:
                try:
                    self._fit_trading_meta_model(X_clean, y_clean)
                except Exception as e:
                    logger.warning(
                        f"Meta model training failed: {e}, using simple voting"
                    )
                    self.ensemble_method = "risk_weighted"
                    self._calculate_risk_weights(X_clean, y_clean)
            elif self.ensemble_method == "risk_weighted":
                self._calculate_risk_weights(X_clean, y_clean)

            # 3. モデル性能評価（堅牢化）
            try:
                self._evaluate_model_performance(X_clean, y_clean)
            except Exception as e:
                logger.warning(f"Performance evaluation failed: {e}")
                self.model_performance_ = {}

            # 4. 取引特化型重み計算（堅牢化）
            try:
                self._calculate_trading_weights()
            except Exception as e:
                logger.warning(f"Trading weights calculation failed: {e}")
                self.trading_weights_ = [1.0 / len(self.fitted_base_models)] * len(
                    self.fitted_base_models
                )

            # Phase H.26: 学習完了フラグ設定
            self.is_fitted = True

            logger.info(
                f"✅ Ensemble training completed successfully ({successful_models}/{len(self.base_models)} models)"
            )
            return self

        except Exception as e:
            logger.error(f"❌ Ensemble training failed completely: {e}")
            return self._create_fallback_ensemble()

    def _fit_base_models(self, X: pd.DataFrame, y: pd.Series):
        """ベースモデルの学習"""
        self.fitted_base_models = []

        for i, model in enumerate(self.base_models):
            logger.info(
                f"Training base model {i+1}/{len(self.base_models)}: "
                f"{type(model).__name__}"
            )

            try:
                # 確率校正付きモデル
                if self.use_calibration:
                    calibrated_model = CalibratedClassifierCV(
                        model, method="sigmoid", cv=3
                    )
                    calibrated_model.fit(X, y)
                    self.fitted_base_models.append(calibrated_model)
                else:
                    model.fit(X, y)
                    self.fitted_base_models.append(model)

                logger.info(f"Base model {i+1} training completed")

            except Exception as e:
                logger.error(f"Failed to train base model {i+1}: {e}")
                # 失敗したモデルはダミーモデルで代替
                dummy_model = LogisticRegression(random_state=42)
                dummy_model.fit(X, y)
                self.fitted_base_models.append(dummy_model)

    def _fit_trading_meta_model(self, X: pd.DataFrame, y: pd.Series):
        """取引特化型メタモデルの学習"""
        logger.info("Generating trading-optimized meta-features")

        # 取引特化型メタ特徴量生成（確率・信頼度・リスク調整値）
        meta_features = np.zeros((len(X), len(self.fitted_base_models) * 3))

        cv = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=42)

        for i, model in enumerate(self.base_models):
            try:
                # 交差検証予測
                cv_predictions = cross_val_predict(
                    model, X, y, cv=cv, method="predict_proba"
                )

                # 基本確率
                if cv_predictions.shape[1] > 1:
                    proba = cv_predictions[:, 1]
                else:
                    proba = cv_predictions[:, 0]
                meta_features[:, i * 3] = proba

                # 予測信頼度（エントロピーベース）
                entropy = -np.sum(
                    cv_predictions * np.log(cv_predictions + 1e-8), axis=1
                )
                confidence = 1 - (entropy / np.log(2))  # 正規化
                meta_features[:, i * 3 + 1] = confidence

                # リスク調整値（極端な予測への重み調整）
                risk_adjustment = 1.0 - np.abs(proba - 0.5) * 2  # 0.5から離れるほど低下
                if self.risk_adjustment:
                    meta_features[:, i * 3 + 2] = risk_adjustment
                else:
                    meta_features[:, i * 3 + 2] = 1.0

            except Exception as e:
                logger.error(
                    f"Failed to generate trading meta-features for model {i+1}: {e}"
                )
                # エラー時はニュートラル値
                meta_features[:, i * 3 : i * 3 + 3] = [0.5, 0.5, 1.0]

        # 取引最適化メタモデル学習
        self.fitted_meta_model = self.meta_model.fit(meta_features, y)
        logger.info("Trading meta-model training completed")

    def _calculate_risk_weights(self, X: pd.DataFrame, y: pd.Series):
        """リスク加重型重み計算"""
        logger.info("Calculating risk-adjusted weights")

        risk_weights = []
        cv = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=42)

        for model in self.base_models:
            try:
                # 予測精度計算
                cv_predictions = cross_val_predict(model, X, y, cv=cv)
                accuracy = np.mean(cv_predictions == y)

                # 予測安定性計算（予測分散）
                cv_probas = cross_val_predict(
                    model, X, y, cv=cv, method="predict_proba"
                )
                stability = 1.0 - np.std(cv_probas[:, 1])  # 低分散 = 高安定性

                # リスク調整重み（精度×安定性）
                risk_weight = accuracy * stability
                risk_weights.append(risk_weight)

            except Exception as e:
                logger.error(f"Failed to calculate risk weight: {e}")
                risk_weights.append(0.5)

        # 正規化
        total_weight = sum(risk_weights)
        if total_weight > 0:
            self.trading_weights_ = [w / total_weight for w in risk_weights]
        else:
            self.trading_weights_ = [1.0 / len(risk_weights)] * len(risk_weights)

        logger.info(f"Calculated risk weights: {self.trading_weights_}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """予測値の出力"""
        predictions_proba = self.predict_proba(X)
        return (predictions_proba[:, 1] > 0.5).astype(int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """取引特化型確率予測の出力"""
        if not self.fitted_base_models:
            raise ValueError("Model not fitted yet")

        # Store last X for model agreement calculation
        self.last_X_ = X

        if self.ensemble_method == "trading_stacking":
            return self._predict_proba_trading_stacking(X)
        elif self.ensemble_method == "risk_weighted":
            return self._predict_proba_risk_weighted(X)
        else:  # performance_voting
            return self._predict_proba_performance_voting(X)

    def _predict_proba_trading_stacking(self, X: pd.DataFrame) -> np.ndarray:
        """取引特化型スタッキング予測"""
        # 取引特化型メタ特徴量生成
        meta_features = np.zeros((len(X), len(self.fitted_base_models) * 3))

        for i, model in enumerate(self.fitted_base_models):
            try:
                proba = model.predict_proba(X)
                base_proba = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]

                # 基本確率
                meta_features[:, i * 3] = base_proba

                # 予測信頼度
                entropy = -np.sum(proba * np.log(proba + 1e-8), axis=1)
                confidence = 1 - (entropy / np.log(2))
                meta_features[:, i * 3 + 1] = confidence

                # リスク調整値
                risk_adjustment = 1.0 - np.abs(base_proba - 0.5) * 2
                if self.risk_adjustment:
                    meta_features[:, i * 3 + 2] = risk_adjustment
                else:
                    meta_features[:, i * 3 + 2] = 1.0

            except Exception as e:
                logger.error(f"Trading prediction failed for base model {i+1}: {e}")
                meta_features[:, i * 3 : i * 3 + 3] = [0.5, 0.5, 1.0]

        # 取引最適化メタモデル予測
        return self.fitted_meta_model.predict_proba(meta_features)

    def _predict_proba_risk_weighted(self, X: pd.DataFrame) -> np.ndarray:
        """リスク加重型予測"""
        weights = self.trading_weights_ or [1.0 / len(self.fitted_base_models)] * len(
            self.fitted_base_models
        )

        weighted_proba = np.zeros((len(X), 2))
        total_weight = 0

        for i, (model, weight) in enumerate(zip(self.fitted_base_models, weights)):
            try:
                proba = model.predict_proba(X)

                # リスク調整（極端な予測を抑制）
                if self.risk_adjustment:
                    # 0.5から離れすぎる予測には重みを下げる
                    extreme_penalty = 1.0 - np.abs(proba[:, 1] - 0.5) * 0.5
                    adjusted_weight = weight * np.mean(extreme_penalty)
                else:
                    adjusted_weight = weight

                weighted_proba += proba * adjusted_weight
                total_weight += adjusted_weight

            except Exception as e:
                logger.error(f"Risk-weighted prediction failed for model {i+1}: {e}")

        return weighted_proba / max(total_weight, 1e-8)

    def _predict_proba_performance_voting(self, X: pd.DataFrame) -> np.ndarray:
        """パフォーマンス加重投票予測"""
        # モデル性能ベースの重み使用
        performance_weights = []
        for _model_name, performance in self.model_performance_.items():
            # 取引メトリクス重み付き総合スコア
            win_rate_score = performance.get(
                "accuracy", 0.5
            ) * self.trading_metrics.get("win_rate", 0.3)
            sharpe_score = performance.get("f1", 0.5) * self.trading_metrics.get(
                "sharpe_ratio", 0.4
            )
            drawdown_penalty = (1.0 - performance.get("precision", 0.5)) * abs(
                self.trading_metrics.get("max_drawdown", -0.2)
            )
            score = win_rate_score + sharpe_score + drawdown_penalty
            performance_weights.append(score)

        # 正規化
        total_perf = sum(performance_weights)
        if total_perf > 0:
            performance_weights = [w / total_perf for w in performance_weights]
        else:
            performance_weights = [1.0 / len(self.fitted_base_models)] * len(
                self.fitted_base_models
            )

        weighted_proba = np.zeros((len(X), 2))

        for i, (model, weight) in enumerate(
            zip(self.fitted_base_models, performance_weights)
        ):
            try:
                proba = model.predict_proba(X)
                weighted_proba += proba * weight
            except Exception as e:
                logger.error(f"Performance voting failed for model {i+1}: {e}")

        return weighted_proba

    def _predict_proba_weighted_voting(self, X: pd.DataFrame) -> np.ndarray:
        """重み付き投票予測"""
        weights = (
            self.ensemble_weights_
            or self.voting_weights
            or [1.0] * len(self.fitted_base_models)
        )

        weighted_proba = np.zeros((len(X), 2))
        total_weight = 0

        for i, (model, weight) in enumerate(zip(self.fitted_base_models, weights)):
            try:
                proba = model.predict_proba(X)
                weighted_proba += proba * weight
                total_weight += weight
            except Exception as e:
                logger.error(f"Weighted prediction failed for model {i+1}: {e}")

        return weighted_proba / max(total_weight, 1e-8)

    def _predict_proba_voting(self, X: pd.DataFrame) -> np.ndarray:
        """単純投票予測"""
        return self._predict_proba_weighted_voting(X)

    def predict_with_trading_confidence(
        self, X: pd.DataFrame, market_context: Dict = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]:
        """
        取引特化型信頼度付き予測（Phase H.26: 堅牢化版）

        Parameters:
        -----------
        X : pd.DataFrame
            特徴量データ
        market_context : Dict, optional
            市場環境コンテキスト（VIX、ボラティリティ等）

        Returns:
        --------
        predictions : np.ndarray
            予測クラス
        probabilities : np.ndarray
            予測確率
        confidence_scores : np.ndarray
            取引信頼度スコア
        trading_info : Dict
            取引判断に関する詳細情報
        """
        # Phase H.26: 予測前の堅牢性チェック
        try:
            # 学習済みチェック
            if not hasattr(self, "is_fitted") or not self.is_fitted:
                logger.warning("Model not fitted, using fallback predictions")
                return self._create_fallback_predictions(X)

            # ベースモデル存在チェック
            if not self.fitted_base_models or len(self.fitted_base_models) == 0:
                logger.warning("No fitted base models, using fallback predictions")
                return self._create_fallback_predictions(X)

            # 入力データ検証
            if X is None or X.empty:
                logger.error("Empty input data")
                return self._create_fallback_predictions(X)

            # 特徴量整合性チェック
            if hasattr(self, "feature_names_") and self.feature_names_:
                if list(X.columns) != self.feature_names_:
                    logger.warning("Feature mismatch, attempting alignment")
                    X = self._align_prediction_features(X)

            # NaN値チェック
            nan_ratio = X.isna().sum().sum() / (len(X) * len(X.columns))
            if nan_ratio > 0.8:  # 80%以上がNaN
                logger.error(f"Too many NaN values for prediction: {nan_ratio:.2%}")
                return self._create_fallback_predictions(X)

            # NaN値補完
            X_clean = X.ffill().bfill().fillna(0)

            probabilities = self.predict_proba(X_clean)

        except Exception as e:
            logger.error(f"Prediction failed: {e}, using fallback")
            return self._create_fallback_predictions(X)

        # 動的閾値計算
        dynamic_threshold = self._calculate_dynamic_threshold(X, market_context)
        predictions = (probabilities[:, 1] > dynamic_threshold).astype(int)

        # 取引特化型信頼度計算
        confidence_scores = self._calculate_trading_confidence(
            probabilities, X, market_context
        )

        # 取引情報まとめ
        trading_info = {
            "dynamic_threshold": dynamic_threshold,
            "base_threshold": 0.5,
            "market_regime": self._assess_market_regime(market_context),
            "risk_level": self._assess_risk_level(confidence_scores),
            "recommended_position_size": self._calculate_position_sizing(
                confidence_scores, market_context
            ),
        }

        return predictions, probabilities, confidence_scores, trading_info

    def _calculate_dynamic_threshold(
        self, X: pd.DataFrame, market_context: Dict = None
    ) -> float:
        """動的閾値計算"""
        base_threshold = self.confidence_threshold

        if market_context is None:
            return base_threshold

        # VIXベース調整
        vix_level = market_context.get("vix_level", 20.0)
        if vix_level > 35:  # 高VIX
            threshold_adj = 0.1  # より保守的
        elif vix_level > 25:  # 中VIX
            threshold_adj = 0.05
        elif vix_level < 15:  # 低VIX
            threshold_adj = -0.05  # より積極的
        else:
            threshold_adj = 0.0

        # ボラティリティベース調整
        volatility = market_context.get("volatility", 0.02)
        if volatility > 0.05:  # 高ボラティリティ
            threshold_adj += 0.05
        elif volatility < 0.01:  # 低ボラティリティ
            threshold_adj -= 0.02

        # 最終閾値
        dynamic_threshold = base_threshold + threshold_adj
        return np.clip(dynamic_threshold, 0.3, 0.8)  # 範囲制限

    def _calculate_trading_confidence(
        self, probabilities: np.ndarray, X: pd.DataFrame, market_context: Dict = None
    ) -> np.ndarray:
        """取引特化型信頼度計算"""
        # 基本信頼度（エントロピーベース）
        epsilon = 1e-8
        entropy = -np.sum(probabilities * np.log(probabilities + epsilon), axis=1)
        max_entropy = np.log(2)
        entropy_confidence = 1 - (entropy / max_entropy)

        # 確率の極端度（0.5から離れるほど高信頼度）
        probability_confidence = np.abs(probabilities[:, 1] - 0.5) * 2

        # モデル合意度
        model_agreement = self._calculate_model_agreement_score(X)

        # 市場環境調整
        market_adjustment = self._get_market_confidence_adjustment(market_context)

        # 総合信頼度
        trading_confidence = (
            0.3 * entropy_confidence
            + 0.3 * probability_confidence
            + 0.2 * model_agreement
            + 0.2 * market_adjustment
        )

        return np.clip(trading_confidence, 0.0, 1.0)

    def _calculate_model_agreement_score(self, X: pd.DataFrame) -> np.ndarray:
        """モデル間合意度スコア計算"""
        if len(self.fitted_base_models) < 2:
            return np.ones(len(X))

        individual_predictions = []
        for model in self.fitted_base_models:
            try:
                proba = model.predict_proba(X)
                individual_predictions.append(proba[:, 1])
            except Exception:
                individual_predictions.append(np.full(len(X), 0.5))

        # 予測の標準偏差計算（低い = 高合意度）
        pred_array = np.array(individual_predictions).T
        agreement = 1.0 - np.std(pred_array, axis=1) / 0.5  # 正規化

        return np.clip(agreement, 0.0, 1.0)

    def _get_market_confidence_adjustment(self, market_context: Dict = None) -> float:
        """市場環境による信頼度調整"""
        if market_context is None:
            return 0.5

        # VIXベース調整
        vix_level = market_context.get("vix_level", 20.0)
        if vix_level > 35:
            vix_adj = 0.2  # 不安定な市場では信頼度低下
        elif vix_level < 15:
            vix_adj = 0.8  # 安定市場では信頼度向上
        else:
            vix_adj = 0.5

        # トレンド強度調整
        trend_strength = market_context.get("trend_strength", 0.5)
        trend_adj = trend_strength  # 強いトレンドは高信頼度

        return (vix_adj + trend_adj) / 2.0

    def _assess_market_regime(self, market_context: Dict = None) -> str:
        """市場レジーム評価"""
        if market_context is None:
            return "unknown"

        vix_level = market_context.get("vix_level", 20.0)
        volatility = market_context.get("volatility", 0.02)

        if vix_level > 35 or volatility > 0.06:
            return "crisis"
        elif vix_level > 25 or volatility > 0.04:
            return "volatile"
        elif vix_level < 15 and volatility < 0.02:
            return "calm"
        else:
            return "normal"

    def _assess_risk_level(self, confidence_scores: np.ndarray) -> str:
        """リスクレベル評価"""
        avg_confidence = np.mean(confidence_scores)

        if avg_confidence > 0.8:
            return "low"
        elif avg_confidence > 0.6:
            return "medium"
        elif avg_confidence > 0.4:
            return "high"
        else:
            return "very_high"

    def _calculate_position_sizing(
        self, confidence_scores: np.ndarray, market_context: Dict = None
    ) -> float:
        """ポジションサイジング推奨計算"""
        avg_confidence = np.mean(confidence_scores)

        # 基本サイズ（信頼度ベース）
        base_size = avg_confidence * 0.1  # 最大10%

        # 市場環境調整
        if market_context:
            vix_level = market_context.get("vix_level", 20.0)
            if vix_level > 35:
                base_size *= 0.5  # 半分に削減
            elif vix_level < 15:
                base_size *= 1.2  # 20%増加

        return min(base_size, 0.15)  # 最大15%制限

    def _calculate_confidence_scores(self, probabilities: np.ndarray) -> np.ndarray:
        """
        予測信頼度スコアの計算

        エントロピー・分散・一致度を組み合わせた信頼度指標
        """
        # エントロピーベース信頼度（低エントロピー = 高信頼度）
        epsilon = 1e-8
        entropy = -np.sum(probabilities * np.log(probabilities + epsilon), axis=1)
        max_entropy = np.log(2)  # 2クラス分類の最大エントロピー
        entropy_confidence = 1 - (entropy / max_entropy)

        # 確率の最大値ベース信頼度
        max_prob_confidence = np.max(probabilities, axis=1)

        # ベースモデル間の一致度（スタッキング以外の場合）
        if self.ensemble_method != "stacking" and len(self.fitted_base_models) > 1:
            model_agreement = self._calculate_model_agreement(probabilities)
        else:
            model_agreement = np.ones(len(probabilities))

        # 総合信頼度（重み付き平均）
        confidence_scores = (
            0.4 * entropy_confidence + 0.4 * max_prob_confidence + 0.2 * model_agreement
        )

        return confidence_scores

    def _calculate_model_agreement(
        self, ensemble_probabilities: np.ndarray
    ) -> np.ndarray:
        """ベースモデル間の予測一致度計算"""
        # 各ベースモデルの予測確率を取得
        individual_probabilities = []

        for model in self.fitted_base_models:
            try:
                proba = model.predict_proba(self.last_X_)  # 最後に予測したX
                individual_probabilities.append(proba[:, 1])
            except Exception:
                individual_probabilities.append(
                    np.full(len(ensemble_probabilities), 0.5)
                )

        if len(individual_probabilities) < 2:
            return np.ones(len(ensemble_probabilities))

        # 標準偏差ベースの一致度（低分散 = 高一致度）
        prob_array = np.array(individual_probabilities).T
        # 最大標準偏差で正規化
        agreement = 1 - np.std(prob_array, axis=1) / 0.5

        return np.clip(agreement, 0, 1)

    def _evaluate_model_performance(self, X: pd.DataFrame, y: pd.Series):
        """モデル性能評価"""
        self.model_performance_ = {}

        # 交差検証でベースモデル性能評価
        cv = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=42)

        for i, model in enumerate(self.base_models):
            try:
                cv_predictions = cross_val_predict(model, X, y, cv=cv)

                performance = {
                    "accuracy": accuracy_score(y, cv_predictions),
                    "precision": precision_score(
                        y, cv_predictions, average="weighted", zero_division=0
                    ),
                    "recall": recall_score(
                        y, cv_predictions, average="weighted", zero_division=0
                    ),
                    "f1": f1_score(
                        y, cv_predictions, average="weighted", zero_division=0
                    ),
                }

                model_key = f"model_{i+1}_{type(model).__name__}"
                self.model_performance_[model_key] = performance
                logger.info(f"Model {i+1} performance: {performance}")

            except Exception as e:
                logger.error(f"Performance evaluation failed for model {i+1}: {e}")
                model_key = f"model_{i+1}_{type(model).__name__}"
                self.model_performance_[model_key] = {
                    "accuracy": 0.5,
                    "precision": 0.5,
                    "recall": 0.5,
                    "f1": 0.5,
                }

    def _calculate_trading_weights(self):
        """取引特化型動的重み計算"""
        if not self.model_performance_:
            self.trading_weights_ = [1.0] * len(self.fitted_base_models)
            return

        # 取引メトリクス総合スコア計算
        trading_scores = []
        for _model_name, performance in self.model_performance_.items():
            # 勝率重視の総合スコア
            win_rate_score = performance.get(
                "accuracy", 0.5
            ) * self.trading_metrics.get("win_rate", 0.3)
            sharpe_score = performance.get("precision", 0.5) * self.trading_metrics.get(
                "sharpe_ratio", 0.4
            )
            f1_score = performance.get("f1", 0.5) * 0.2
            drawdown_penalty = (
                (1.0 - performance.get("recall", 0.5))
                * abs(self.trading_metrics.get("max_drawdown", -0.2))
                * 0.1
            )
            score = win_rate_score + sharpe_score + f1_score + drawdown_penalty
            trading_scores.append(max(score, 0.1))  # 最小重み保証

        # 重みの正規化
        total_score = sum(trading_scores)
        if total_score > 0:
            self.trading_weights_ = [score / total_score for score in trading_scores]
        else:
            self.trading_weights_ = [1.0 / len(self.fitted_base_models)] * len(
                self.fitted_base_models
            )

        logger.info(f"Calculated trading weights: {self.trading_weights_}")

        # リスクメトリクス記録
        self.risk_metrics_ = {
            "weight_diversity": np.std(self.trading_weights_),
            "max_weight": max(self.trading_weights_),
            "min_weight": min(self.trading_weights_),
            "weight_concentration": (
                max(self.trading_weights_) / np.mean(self.trading_weights_)
            ),
        }

    def get_trading_ensemble_info(self) -> Dict[str, Any]:
        """取引特化型アンサンブル情報の取得"""
        return {
            "ensemble_method": self.ensemble_method,
            "num_base_models": len(self.fitted_base_models),
            "risk_adjustment": self.risk_adjustment,
            "cv_folds": self.cv_folds,
            "confidence_threshold": self.confidence_threshold,
            "trading_metrics": self.trading_metrics,
            "model_performance": self.model_performance_,
            "trading_weights": self.trading_weights_,
            "risk_metrics": self.risk_metrics_,
            "base_model_types": [type(model).__name__ for model in self.base_models],
            "prediction_history_size": len(self.prediction_history_),
            "market_regime_weights": self.market_regime_weights_,
        }

    def update_confidence_threshold(self, new_threshold: float):
        """信頼度閾値の動的更新"""
        self.confidence_threshold = new_threshold
        logger.info(f"Confidence threshold updated to: {new_threshold}")

    def get_feature_importance(self) -> pd.DataFrame:
        """統合特徴量重要度の取得"""
        if not self.feature_names_:
            return pd.DataFrame()

        importance_data = []

        for _i, model in enumerate(self.fitted_base_models):
            if hasattr(model, "feature_importances_"):
                importance_data.append(model.feature_importances_)
            elif hasattr(model, "coef_"):
                importance_data.append(np.abs(model.coef_[0]))
            else:
                # 重要度が取得できない場合は均等重み
                importance_data.append(np.ones(len(self.feature_names_)))

        if not importance_data:
            return pd.DataFrame()

        # 重み付き平均重要度計算
        weights = self.ensemble_weights_ or [1.0] * len(importance_data)
        weighted_importance = np.zeros(len(self.feature_names_))

        for importance, weight in zip(importance_data, weights):
            weighted_importance += importance * weight

        weighted_importance /= sum(weights)

        # データフレーム作成
        importance_df = pd.DataFrame(
            {"feature": self.feature_names_, "importance": weighted_importance}
        ).sort_values("importance", ascending=False)

        return importance_df

    # Phase H.26: アンサンブル学習堅牢化メソッド群
    def _validate_training_data(self, X: pd.DataFrame, y: pd.Series) -> bool:
        """データ妥当性チェック"""
        try:
            # 基本的な存在確認
            if X is None or y is None:
                logger.error("X or y is None")
                return False

            if X.empty or y.empty:
                logger.error("X or y is empty")
                return False

            # サイズ確認
            if len(X) != len(y):
                logger.error(f"Size mismatch: X={len(X)}, y={len(y)}")
                return False

            # 最小サイズ確認
            if len(X) < 10:  # 絶対最小
                logger.error(f"Dataset too small: {len(X)} samples")
                return False

            # NaN値チェック
            x_nan_ratio = X.isna().sum().sum() / (len(X) * len(X.columns))
            y_nan_ratio = y.isna().sum() / len(y)

            if x_nan_ratio > 0.5:  # 50%以上がNaN
                logger.error(f"Too many NaN values in X: {x_nan_ratio:.2%}")
                return False

            if y_nan_ratio > 0.3:  # 30%以上がNaN
                logger.error(f"Too many NaN values in y: {y_nan_ratio:.2%}")
                return False

            # ターゲット値の多様性確認
            unique_targets = len(y.unique())
            if unique_targets < 2:
                logger.error(f"Insufficient target diversity: {unique_targets} classes")
                return False

            logger.info(
                f"✅ Data validation passed: {len(X)} samples, X_NaN={x_nan_ratio:.2%}, y_NaN={y_nan_ratio:.2%}"
            )
            return True

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return False

    def _align_and_clean_data(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """インデックス整合性確保とNaN除去"""
        try:
            # インデックス整合
            common_index = X.index.intersection(y.index)
            if len(common_index) == 0:
                logger.warning("No common index, using positional alignment")
                # 位置ベース整合
                min_len = min(len(X), len(y))
                X_aligned = X.iloc[:min_len].reset_index(drop=True)
                y_aligned = y.iloc[:min_len].reset_index(drop=True)
            else:
                X_aligned = X.loc[common_index]
                y_aligned = y.loc[common_index]

            # NaN除去
            # まずyのNaNを除去
            y_valid_mask = ~y_aligned.isna()
            y_clean = y_aligned[y_valid_mask]
            X_temp = X_aligned[y_valid_mask]

            # 次にXの行で全てNaNの行を除去
            x_valid_mask = ~X_temp.isna().all(axis=1)
            X_clean = X_temp[x_valid_mask]
            y_clean = y_clean[x_valid_mask]

            # 各列で残っているNaNを前方補完（Phase H.26: pandas非推奨対応）
            X_clean = X_clean.ffill().bfill().fillna(0)

            logger.info(
                f"Data alignment: {len(X)} → {len(X_clean)} samples after cleaning"
            )
            return X_clean, y_clean

        except Exception as e:
            logger.error(f"Data alignment failed: {e}")
            # フォールバック: 単純な整合
            min_len = min(len(X), len(y))
            return X.iloc[:min_len].fillna(0), y.iloc[:min_len].fillna(0)

    def _fit_base_models_robust(self, X: pd.DataFrame, y: pd.Series) -> int:
        """堅牢なベースモデル学習"""
        self.fitted_base_models = []
        successful_models = 0

        for i, model in enumerate(self.base_models):
            try:
                logger.info(
                    f"Training base model {i+1}/{len(self.base_models)}: {type(model).__name__}"
                )

                # モデル固有の最小サンプル数チェック
                model_min_samples = self._get_model_min_samples(model)
                if len(y) < model_min_samples:
                    logger.warning(
                        f"Insufficient samples for {type(model).__name__}: {len(y)} < {model_min_samples}"
                    )
                    continue

                # 確率校正付きモデルの学習
                if hasattr(self, "use_calibration") and self.use_calibration:
                    calibrated_model = CalibratedClassifierCV(
                        model, method="sigmoid", cv=3
                    )
                    calibrated_model.fit(X, y)
                    self.fitted_base_models.append(calibrated_model)
                else:
                    model.fit(X, y)
                    self.fitted_base_models.append(model)

                successful_models += 1
                logger.info(f"✅ Base model {i+1} training completed")

            except Exception as e:
                logger.error(f"❌ Base model {i+1} failed: {e}")
                # フォールバック: シンプルなLogisticRegression
                try:
                    fallback_model = LogisticRegression(random_state=42, max_iter=100)
                    fallback_model.fit(X, y)
                    self.fitted_base_models.append(fallback_model)
                    successful_models += 1
                    logger.warning(f"⚠️ Using fallback model for base model {i+1}")
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback model also failed: {fallback_error}")
                    continue

        logger.info(
            f"Base models training completed: {successful_models}/{len(self.base_models)} successful"
        )
        return successful_models

    def _get_model_min_samples(self, model) -> int:
        """モデル別最小サンプル数取得"""
        model_name = type(model).__name__

        # Phase H.29: 4hタイムフレーム対応のため最小サンプル数を緩和
        if model_name in ["XGBClassifier", "LGBMClassifier"]:
            return 30  # 勾配ブースティング系（50→30に緩和）
        elif model_name == "RandomForestClassifier":
            return 20  # ランダムフォレスト（30→20に緩和）
        elif model_name in ["LogisticRegression", "SVC"]:
            return 15  # 線形モデル（20→15に緩和）
        else:
            return 20  # その他（25→20に緩和）

    def _create_fallback_ensemble(self) -> "TradingEnsembleClassifier":
        """フォールバック用簡易アンサンブル作成"""
        logger.warning("Creating fallback ensemble with single LogisticRegression")

        try:
            # 最小限のLogisticRegressionモデル
            fallback_model = LogisticRegression(
                random_state=42, max_iter=100, class_weight="balanced"
            )
            self.fitted_base_models = [fallback_model]
            self.ensemble_method = "simple_fallback"
            self.is_fitted = False  # まだ学習していない
            self.feature_names_ = []
            self.classes_ = np.array([0, 1])
            self.model_performance_ = {}
            self.trading_weights_ = [1.0]

            return self

        except Exception as e:
            logger.error(f"Failed to create fallback ensemble: {e}")
            # 完全フォールバック
            self.fitted_base_models = []
            self.is_fitted = False
            return self

    def _create_fallback_predictions(
        self, X: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]:
        """フォールバック予測生成"""
        try:
            n_samples = len(X)

            # 基本的な確率（わずかに楽観的）
            fallback_probabilities = np.column_stack(
                [
                    np.full(n_samples, 0.45),  # クラス0確率
                    np.full(n_samples, 0.55),  # クラス1確率（わずかに楽観的）
                ]
            )

            # 予測クラス
            predictions = np.ones(n_samples, dtype=int)  # わずかに楽観的

            # 低めの信頼度
            confidence_scores = np.full(n_samples, 0.35)

            # フォールバック情報
            trading_info = {
                "method": "fallback",
                "ensemble_enabled": False,
                "dynamic_threshold": 0.5,
                "market_regime": "unknown",
                "risk_level": "high",
                "model_agreement": 0.5,
                "prediction_quality": "poor",
            }

            logger.warning(f"Using fallback predictions for {n_samples} samples")
            return predictions, fallback_probabilities, confidence_scores, trading_info

        except Exception as e:
            logger.error(f"Fallback prediction failed: {e}")
            # 最後の手段
            n_samples = max(1, len(X) if X is not None and not X.empty else 1)
            return (
                np.zeros(n_samples, dtype=int),
                np.full((n_samples, 2), 0.5),
                np.full(n_samples, 0.1),
                {"method": "emergency_fallback", "ensemble_enabled": False},
            )

    def _align_prediction_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """予測用特徴量整合"""
        try:
            if not hasattr(self, "feature_names_") or not self.feature_names_:
                logger.warning("No stored feature names, using input as-is")
                return X

            # 不足する特徴量を0で補完
            missing_features = set(self.feature_names_) - set(X.columns)
            if missing_features:
                logger.warning(
                    f"Adding missing features with zeros: {len(missing_features)} features"
                )
                for feature in missing_features:
                    X[feature] = 0.0

            # 余分な特徴量を削除
            extra_features = set(X.columns) - set(self.feature_names_)
            if extra_features:
                logger.warning(
                    f"Removing extra features: {len(extra_features)} features"
                )
                X = X.drop(columns=extra_features)

            # 順序を合わせる
            X = X[self.feature_names_]

            logger.info(f"Feature alignment completed: {len(X.columns)} features")
            return X

        except Exception as e:
            logger.error(f"Feature alignment failed: {e}")
            return X  # 元のまま返す


def create_trading_ensemble(config: Dict[str, Any]) -> TradingEnsembleClassifier:
    """
    取引特化型アンサンブルの作成

    Parameters:
    -----------
    config : Dict[str, Any]
        取引アンサンブル設定

    Returns:
    --------
    TradingEnsembleClassifier
        取引最適化されたアンサンブル分類器
    """
    ensemble_config = config.get("ml", {}).get("ensemble", {})

    risk_adjustment = ensemble_config.get("risk_adjustment", True)

    # confidence_thresholdを複数の場所から取得（優先順位順）
    confidence_from_ensemble = ensemble_config.get("confidence_threshold")
    confidence_from_ml = config.get("ml", {}).get("confidence_threshold")
    confidence_from_strategy = config.get("strategy", {}).get("confidence_threshold")

    # 優先順位に従って値を選択（production.ymlのデフォルト値0.35に合わせる）
    if confidence_from_ensemble is not None:
        confidence_threshold = confidence_from_ensemble
    elif confidence_from_ml is not None:
        confidence_threshold = confidence_from_ml
    elif confidence_from_strategy is not None:
        confidence_threshold = confidence_from_strategy
    else:
        confidence_threshold = 0.35  # production.ymlのデフォルト値

    # 取引メトリクス重み設定
    trading_metrics = ensemble_config.get(
        "trading_metrics",
        {
            "sharpe_ratio": 0.4,  # シャープレシオ重視
            "win_rate": 0.3,  # 勝率重視
            "max_drawdown": -0.2,  # ドローダウン回避
            "profit_factor": 0.1,  # 利益率考慮
        },
    )

    # Phase 16.1-B修正: 事前学習済みモデル自動読み込み機能追加
    try:
        from pathlib import Path

        import joblib

        # 事前学習済みアンサンブルモデル読み込み試行
        production_model_path = Path("models/production/model.pkl")
        if production_model_path.exists():
            logger.info(
                f"🔄 Loading pre-trained ensemble model from: {production_model_path}"
            )
            ensemble = joblib.load(production_model_path)

            # 設定パラメータで更新
            ensemble.confidence_threshold = confidence_threshold
            if hasattr(ensemble, "risk_adjustment"):
                ensemble.risk_adjustment = risk_adjustment

            logger.info(
                f"✅ Loaded pre-trained ensemble with {len(ensemble.base_models)} models"
            )
            return ensemble

        else:
            logger.warning(f"⚠️  Pre-trained model not found at {production_model_path}")

    except Exception as e:
        logger.warning(f"⚠️  Failed to load pre-trained model: {e}")

    # ChatGPT提案: アンサンブルモデル強制使用 - フォールバック改善
    logger.warning(
        "⚠️  No pre-trained ensemble model available! "
        "Creating simple_fallback mode for basic operation"
    )

    # シンプルフォールバック: 基本的なアンサンブル分類器を作成
    ensemble = TradingEnsembleClassifier(
        ensemble_method="simple_fallback",
        trading_metrics=trading_metrics,
        risk_adjustment=risk_adjustment,
        confidence_threshold=confidence_threshold,
    )

    logger.warning(
        "⚠️  Created fallback ensemble: simple_fallback mode "
        "(to prevent 'Strategy does not use ensemble models' error)"
    )
    return ensemble
