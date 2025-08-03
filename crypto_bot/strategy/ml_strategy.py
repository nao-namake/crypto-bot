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

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

try:
    from crypto_bot.data.vix_fetcher import VIXDataFetcher

    VIX_AVAILABLE = True
except ImportError:
    VIXDataFetcher = None
    VIX_AVAILABLE = False
from crypto_bot.execution.engine import Position, Signal
from crypto_bot.indicator.calculator import IndicatorCalculator
from crypto_bot.ml.model import EnsembleModel, MLModel
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
            self.base_threshold = threshold
        else:
            self.base_threshold = self.config.get("threshold", 0.0)
        logger.debug(
            "MLStrategy initialised with base threshold = %.4f", self.base_threshold
        )

        # モデルの読み込み（TradingEnsembleClassifier, MLModel or EnsembleModel）
        try:
            # まずTradingEnsembleClassifierとして直接読み込みを試行（Phase2.2: is_fitted修正）
            import joblib

            logger.info(
                f"Attempting to load TradingEnsembleClassifier from: {model_path}"
            )
            self.model = joblib.load(model_path)
            # Phase2.2: is_fittedフラグが設定されていない場合の修正
            if (
                hasattr(self.model, "fitted_base_models")
                and self.model.fitted_base_models
            ):
                if not hasattr(self.model, "is_fitted") or not self.model.is_fitted:
                    self.model.is_fitted = True
                    logger.info(
                        "✅ Set is_fitted=True for loaded TradingEnsembleClassifier"
                    )
            self.is_ensemble = True
            logger.info("Loaded TradingEnsembleClassifier successfully")
        except Exception as e:
            # フォールバック: EnsembleModelとして読み込みを試行
            logger.warning(f"Failed to load as TradingEnsembleClassifier: {e}")
            try:
                logger.info(f"Attempting to load ensemble model from: {model_path}")
                self.model = EnsembleModel.load(model_path)
                self.is_ensemble = True
                logger.info("Loaded ensemble model successfully")
            except Exception as e:
                # 失敗した場合は通常のMLModelとして読み込み
                logger.warning(f"Failed to load as ensemble model: {e}")
                logger.info(f"Attempting to load as single model from: {model_path}")
                try:
                    self.model = MLModel.load(model_path)
                    self.is_ensemble = False
                    logger.info("Loaded single model successfully")
                except Exception as e2:
                    logger.error(f"Failed to load model: {e2}")
                    raise RuntimeError(f"Could not load model from {model_path}: {e2}")

        self.feature_engineer = FeatureEngineer(self.config)
        self.scaler = StandardScaler()
        self.indicator_calc = IndicatorCalculator()

        # VIX恐怖指数データ取得
        self.vix_fetcher = VIXDataFetcher() if VIX_AVAILABLE else None

        # Dynamic threshold parameters（strategy.paramsからも取得可能）
        strategy_params = self.config.get("strategy", {}).get("params", {})
        self.atr_multiplier = strategy_params.get("atr_multiplier", 0.5)
        self.volatility_adjustment = strategy_params.get("volatility_adjustment", True)
        self.threshold_bounds = strategy_params.get("threshold_bounds", [0.01, 0.25])
        # Phase H.15: 新規パラメータ追加
        self.max_volatility_adj = strategy_params.get("max_volatility_adj", 0.1)
        self.performance_adj_range = strategy_params.get(
            "performance_adj_range", [-0.01, 0.01]
        )

        # VIX integration parameters
        vix_config = self.config.get("ml", {}).get("vix_integration", {})
        self.vix_enabled = vix_config.get("enabled", True)
        self.vix_risk_off_threshold = vix_config.get("risk_off_threshold", 25)
        self.vix_panic_threshold = vix_config.get("panic_threshold", 35)
        self.vix_spike_multiplier = vix_config.get("spike_multiplier", 2.0)
        self.vix_extreme_adj = vix_config.get(
            "vix_extreme_adj", 0.05
        )  # Phase H.15: 極端な調整を抑制

        # Performance improvement parameters
        perf_config = self.config.get("ml", {}).get("performance_enhancements", {})
        self.confidence_filter = perf_config.get(
            "confidence_filter", 0.60
        )  # Phase H.15: 0.65→0.60
        self.partial_profit_levels = perf_config.get(
            "partial_profit_levels", [0.3, 0.5]
        )
        self.trailing_stop_enabled = perf_config.get("trailing_stop", True)

        # Historical performance tracking for adaptive adjustment
        self.recent_signals = []
        self.max_signal_history = 50
        self.vix_data_cache = None
        self.vix_cache_time = None

    def calculate_atr_threshold(
        self, price_df: pd.DataFrame, window: int = 14
    ) -> float:
        """Calculate ATR-based threshold adjustment"""
        try:
            atr = self.indicator_calc.atr(price_df, window=window)
            if atr is None or atr.isna().all():
                return 0.0

            # Get current price and ATR
            current_price = float(price_df["close"].iloc[-1])
            current_atr = float(atr.iloc[-1])

            # Calculate ATR as percentage of price
            atr_percentage = (current_atr / current_price) if current_price > 0 else 0

            # Scale ATR to threshold adjustment
            atr_adjustment = atr_percentage * self.atr_multiplier

            return min(atr_adjustment, 0.15)  # Cap at 15%

        except Exception as e:
            logger.warning("Failed to calculate ATR threshold: %s", e)
            return 0.0

    def calculate_volatility_adjustment(
        self, price_df: pd.DataFrame, window: int = 20
    ) -> float:
        """Calculate volatility-based threshold adjustment"""
        try:
            if not self.volatility_adjustment:
                return 0.0

            # Calculate rolling volatility (standard deviation of returns)
            returns = price_df["close"].pct_change().dropna()
            if len(returns) < window:
                return 0.0

            rolling_vol = returns.rolling(window=window).std()
            current_vol = float(rolling_vol.iloc[-1])

            # Calculate long-term average volatility for comparison
            long_term_vol = float(returns.rolling(window=window * 3).std().iloc[-1])

            # Volatility regime detection
            vol_ratio = current_vol / long_term_vol if long_term_vol > 0 else 1.0

            # Adjust threshold based on volatility regime
            if vol_ratio > 1.5:  # High volatility - increase threshold
                vol_adjustment = 0.02
            elif vol_ratio < 0.7:  # Low volatility - decrease threshold
                vol_adjustment = -0.01
            else:  # Normal volatility
                vol_adjustment = 0.0

            # Phase H.15: ボラティリティ調整の上限制御
            vol_adjustment = np.clip(
                vol_adjustment, -self.max_volatility_adj, self.max_volatility_adj
            )

            return vol_adjustment

        except Exception as e:
            logger.warning("Failed to calculate volatility adjustment: %s", e)
            return 0.0

    def calculate_performance_adjustment(self) -> float:
        """Calculate threshold adjustment based on recent signal performance"""
        if len(self.recent_signals) < 10:
            return 0.0

        # Calculate win rate of recent signals
        wins = sum(
            1 for signal in self.recent_signals[-20:] if signal.get("success", False)
        )
        total = len(self.recent_signals[-20:])
        win_rate = wins / total if total > 0 else 0.5

        # Adjust threshold based on performance
        if win_rate > 0.65:  # Good performance - slightly more aggressive
            perf_adj = -0.005
        elif win_rate < 0.35:  # Poor performance - more conservative
            perf_adj = 0.01
        else:
            perf_adj = 0.0

        # Phase H.15: パフォーマンス調整の範囲制限
        min_adj, max_adj = self.performance_adj_range
        return np.clip(perf_adj, min_adj, max_adj)

    def get_vix_adjustment(self) -> tuple[float, dict]:
        """
        VIX恐怖指数に基づく閾値調整とリスク判定

        Returns:
        --------
        tuple[float, dict]
            (threshold_adjustment, vix_info)
        """
        if not self.vix_enabled or not VIX_AVAILABLE or self.vix_fetcher is None:
            return 0.0, {}

        try:
            # VIXデータ取得（キャッシュ活用）
            from datetime import datetime, timedelta

            current_time = datetime.now()
            if (
                self.vix_data_cache is None
                or self.vix_cache_time is None
                or current_time - self.vix_cache_time > timedelta(hours=1)
            ):

                vix_data = self.vix_fetcher.get_vix_data(timeframe="1d", limit=30)
                if not vix_data.empty:
                    vix_features = self.vix_fetcher.calculate_vix_features(vix_data)
                    self.vix_data_cache = vix_features
                    self.vix_cache_time = current_time
                else:
                    return 0.0, {"error": "VIX data unavailable"}

            vix_features = self.vix_data_cache
            if vix_features is None or vix_features.empty:
                return 0.0, {"error": "No VIX cache"}

            # 最新のVIX指標
            latest = vix_features.iloc[-1]
            current_vix = latest["vix_level"]
            vix_change = latest["vix_change"]
            vix_spike = latest["vix_spike"]
            fear_level = latest["fear_level"]

            # 市場環境判定
            market_regime = self.vix_fetcher.get_market_regime(current_vix)

            # VIXに基づく閾値調整
            threshold_adj = 0.0
            risk_signal = "normal"

            if current_vix < 15:
                # 低恐怖：積極的取引
                threshold_adj = -0.01
                risk_signal = "risk_on"
            elif current_vix > self.vix_panic_threshold:
                # パニック状態：取引停止レベル
                # Phase H.15: 極端な調整を抑制（0.15→vix_extreme_adj）
                threshold_adj = self.vix_extreme_adj  # デフォルト0.05
                risk_signal = "panic"
            elif current_vix > self.vix_risk_off_threshold:
                # リスクオフ：保守的
                threshold_adj = 0.03  # Phase H.15: 0.05→0.03（影響を抑制）
                risk_signal = "risk_off"

            # VIXスパイク（急上昇）の場合はさらに保守的に
            if vix_spike and vix_change > 0.1:  # 10%以上上昇
                threshold_adj += 0.03
                risk_signal = "spike"

            # VIX急低下（恐怖緩和）の場合は積極的に
            if vix_change < -0.05:  # 5%以上低下
                threshold_adj -= 0.005
                risk_signal = "fear_relief"

            vix_info = {
                "current_vix": current_vix,
                "vix_change": vix_change,
                "fear_level": fear_level,
                "market_regime": market_regime["regime"],
                "risk_signal": risk_signal,
                "spike_detected": bool(vix_spike),
                "threshold_adjustment": threshold_adj,
            }

            logger.info(
                f"VIX Analysis: Level={current_vix:.1f}, Change={vix_change:.3f}, "
                f"Regime={market_regime['regime']}, Adj={threshold_adj:.3f}"
            )

            return threshold_adj, vix_info

        except Exception as e:
            logger.warning(f"VIX adjustment failed: {e}")
            return 0.0, {"error": str(e)}

    def calculate_dynamic_threshold(self, price_df: pd.DataFrame) -> float:
        """Calculate final dynamic threshold combining all factors including VIX"""
        # Start with base threshold
        dynamic_threshold = self.base_threshold

        # Add ATR-based adjustment
        atr_adj = self.calculate_atr_threshold(price_df)
        dynamic_threshold += atr_adj

        # Add volatility adjustment
        vol_adj = self.calculate_volatility_adjustment(price_df)
        dynamic_threshold += vol_adj

        # Add performance-based adjustment
        perf_adj = self.calculate_performance_adjustment()
        dynamic_threshold += perf_adj

        # Add VIX-based adjustment (新機能)
        vix_adj, vix_info = self.get_vix_adjustment()
        dynamic_threshold += vix_adj

        # VIX情報をログ出力
        if vix_info and "risk_signal" in vix_info:
            logger.info(
                f"VIX Risk Signal: {vix_info['risk_signal']}, "
                f"VIX Level: {vix_info.get('current_vix', 'N/A')}"
            )

        # Apply bounds to prevent extreme values
        min_threshold, max_threshold = self.threshold_bounds
        dynamic_threshold = np.clip(dynamic_threshold, min_threshold, max_threshold)

        logger.debug(
            "Dynamic threshold calculation: base=%.4f, atr_adj=%.4f, vol_adj=%.4f, "
            "perf_adj=%.4f, final=%.4f",
            self.base_threshold,
            atr_adj,
            vol_adj,
            perf_adj,
            dynamic_threshold,
        )

        return dynamic_threshold

    def update_signal_history(self, signal_info: dict):
        """Update signal history for performance tracking"""
        self.recent_signals.append(signal_info)
        if len(self.recent_signals) > self.max_signal_history:
            self.recent_signals.pop(0)

    def logic_signal(self, price_df: pd.DataFrame, position: Position) -> Signal:
        logger.debug("Input DataFrame columns: %s", price_df.columns.tolist())
        logger.debug("Input DataFrame head (3 rows):\n%s", price_df.head(3).to_string())

        # Calculate dynamic threshold based on market conditions
        dynamic_th = self.calculate_dynamic_threshold(price_df)
        logger.debug("Using dynamic threshold = %.4f", dynamic_th)

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
        if self.is_ensemble:
            # アンサンブルモデルの場合
            prob = self.model.predict_proba(last_X)[0, 1]
            logger.info("Ensemble predicted ↑ prob = %.4f", prob)
        else:
            # 単一モデルの場合
            prob = self.model.predict_proba(last_X)[0, 1]
            logger.info("Single model predicted ↑ prob = %.4f", prob)

        # ポジション有無で判定
        position_exists = position is not None and position.exist
        if position_exists:
            # ポジション有りの場合はexit条件を動的に調整
            # 高ボラティリティ時は早めの利確、低ボラティリティ時は粘る
            exit_multiplier = 0.8 if dynamic_th > self.base_threshold else 0.6
            exit_threshold = 0.5 - (dynamic_th * exit_multiplier)

            if prob < exit_threshold:  # exitしきい値を動的調整
                logger.info(
                    "Position EXIT signal: prob=%.4f < %.4f (dynamic)",
                    prob,
                    exit_threshold,
                )
                signal = Signal(side="SELL", price=price)
                # Track exit signal
                self.update_signal_history(
                    {
                        "type": "EXIT",
                        "probability": prob,
                        "threshold": exit_threshold,
                        "price": price,
                        "timestamp": pd.Timestamp.now(),
                    }
                )
                return signal
            return None

        # シグナル統合ロジック（OR条件でより積極的に）
        ml_long_signal = prob > 0.5 + dynamic_th
        ml_short_signal = prob < 0.5 - dynamic_th
        # もちぽよシグナル OR MLシグナル（どちらかが条件満たせばエントリー）
        if mp_long or ml_long_signal:
            confidence = max(prob - 0.5, mp_long * 0.1)  # 信頼度計算
            logger.info(
                "LONG signal: mochipoyo=%d, ml_prob=%.4f, confidence=%.4f, dyn_th=%.4f",
                mp_long,
                prob,
                confidence,
                dynamic_th,
            )
            signal = Signal(side="BUY", price=price)
            # Track entry signal
            self.update_signal_history(
                {
                    "type": "ENTRY_LONG",
                    "probability": prob,
                    "threshold": dynamic_th,
                    "mochipoyo": mp_long,
                    "ml_signal": ml_long_signal,
                    "confidence": confidence,
                    "price": price,
                    "timestamp": pd.Timestamp.now(),
                }
            )
            return signal

        if mp_short or ml_short_signal:
            confidence = max(0.5 - prob, mp_short * 0.1)  # 信頼度計算
            logger.info(
                "SHORT signal: mochipoyo=%d, ml_prob=%.4f, confidence=%.4f, "
                "dyn_th=%.4f",
                mp_short,
                prob,
                confidence,
                dynamic_th,
            )
            signal = Signal(side="SELL", price=price)
            # Track entry signal
            self.update_signal_history(
                {
                    "type": "ENTRY_SHORT",
                    "probability": prob,
                    "threshold": dynamic_th,
                    "mochipoyo": mp_short,
                    "ml_signal": ml_short_signal,
                    "confidence": confidence,
                    "price": price,
                    "timestamp": pd.Timestamp.now(),
                }
            )
            return signal

        # 中間的なシグナル（動的閾値ベース）
        # 低ボラティリティ時により積極的、高ボラティリティ時により慎重
        # Phase H.15: より積極的な弱シグナル（0.4→0.2、範囲も調整）
        weak_threshold = 0.51 - (dynamic_th * 0.2)  # 動的調整（係数を0.4→0.2）
        weak_threshold = max(
            0.505, min(0.53, weak_threshold)
        )  # 範囲制限（0.51-0.55→0.505-0.53）

        if prob > weak_threshold:  # 弱いBUYシグナル
            logger.info(
                "Weak LONG signal: prob=%.4f > %.4f (dynamic)", prob, weak_threshold
            )
            signal = Signal(side="BUY", price=price)
            self.update_signal_history(
                {
                    "type": "WEAK_LONG",
                    "probability": prob,
                    "threshold": weak_threshold,
                    "price": price,
                    "timestamp": pd.Timestamp.now(),
                }
            )
            return signal

        elif prob < (1.0 - weak_threshold):  # 弱いSELLシグナル
            weak_short_threshold = 1.0 - weak_threshold
            logger.info(
                "Weak SHORT signal: prob=%.4f < %.4f (dynamic)",
                prob,
                weak_short_threshold,
            )
            signal = Signal(side="SELL", price=price)
            self.update_signal_history(
                {
                    "type": "WEAK_SHORT",
                    "probability": prob,
                    "threshold": weak_short_threshold,
                    "price": price,
                    "timestamp": pd.Timestamp.now(),
                }
            )
            return signal

        return None
