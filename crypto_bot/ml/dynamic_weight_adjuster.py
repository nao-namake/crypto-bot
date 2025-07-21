# =============================================================================
# ファイル名: crypto_bot/ml/dynamic_weight_adjuster.py
# 説明:
# Phase C2: 動的重み調整アルゴリズム
# リアルタイム性能評価・予測精度フィードバック・オンライン学習・強化学習
# CrossTimeframeIntegratorの高度な重み調整システム
# =============================================================================

import logging
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler

from crypto_bot.analysis.market_environment_analyzer import MarketEnvironmentAnalyzer

logger = logging.getLogger(__name__)


class DynamicWeightAdjuster:
    """
    Phase C2: 動的重み調整アルゴリズム

    機能:
    - リアルタイム予測精度評価・追跡
    - 性能フィードバックによる重み動的調整
    - オンライン学習・適応的重み最適化
    - 市場環境連動重み調整
    - 多目的最適化（精度・収益性・リスク）
    - 強化学習ベース重み調整（Q-learning風）
    """

    def __init__(self, config: Dict[str, Any]):
        """
        動的重み調整システム初期化

        Parameters:
        -----------
        config : Dict[str, Any]
            動的重み調整設定
        """
        self.config = config

        # 基本設定
        adjustment_config = config.get("dynamic_weight_adjustment", {})
        self.timeframes = adjustment_config.get("timeframes", ["15m", "1h", "4h"])
        self.base_weights = adjustment_config.get("base_weights", [0.3, 0.5, 0.2])
        self.learning_rate = adjustment_config.get("learning_rate", 0.01)
        self.adaptation_speed = adjustment_config.get("adaptation_speed", 0.1)
        self.memory_window = adjustment_config.get("memory_window", 100)

        # 性能評価設定
        performance_config = adjustment_config.get("performance_tracking", {})
        self.accuracy_weight = performance_config.get("accuracy_weight", 0.4)
        self.profitability_weight = performance_config.get("profitability_weight", 0.4)
        self.risk_weight = performance_config.get("risk_weight", 0.2)
        self.min_samples_for_adjustment = performance_config.get("min_samples", 20)

        # オンライン学習設定
        online_config = adjustment_config.get("online_learning", {})
        self.enable_online_learning = online_config.get("enabled", True)
        self.online_learning_method = online_config.get("method", "sgd_regressor")
        self.feature_window = online_config.get("feature_window", 50)
        self.retraining_frequency = online_config.get("retraining_frequency", 20)

        # 強化学習設定
        rl_config = adjustment_config.get("reinforcement_learning", {})
        self.enable_reinforcement_learning = rl_config.get("enabled", True)
        self.epsilon = rl_config.get("epsilon", 0.1)  # 探索率
        self.epsilon_decay = rl_config.get("epsilon_decay", 0.995)
        self.discount_factor = rl_config.get("discount_factor", 0.95)

        # 市場環境解析システム
        self.market_analyzer: Optional[MarketEnvironmentAnalyzer] = None
        if "market_analysis" in config:
            self.market_analyzer = MarketEnvironmentAnalyzer(config)

        # 性能履歴管理
        self.performance_history = defaultdict(deque)  # タイムフレーム別性能履歴
        self.prediction_outcomes = deque(maxlen=self.memory_window)  # 予測結果履歴
        self.weight_history = deque(maxlen=200)  # 重み履歴
        self.market_context_history = deque(maxlen=100)  # 市場環境履歴

        # オンライン学習モデル
        self.online_models = {}
        self.scalers = {}
        self.model_update_count = 0

        if self.enable_online_learning:
            self._initialize_online_models()

        # 強化学習のQ-table（簡易版）
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.action_space = self._generate_weight_actions()
        self.state_space_size = 0

        # 現在の動的重み
        self.current_weights = dict(zip(self.timeframes, self.base_weights))
        self.weight_confidence = {tf: 0.5 for tf in self.timeframes}

        # 統計追跡
        self.adjustment_stats = {
            "total_adjustments": 0,
            "online_learning_updates": 0,
            "reinforcement_learning_updates": 0,
            "market_adaptation_adjustments": 0,
            "performance_feedback_adjustments": 0,
            "weight_change_magnitude": 0.0,
            "improvement_rate": 0.0,
            "successful_adjustments": 0,
        }

        logger.info("🎛️ DynamicWeightAdjuster initialized")
        logger.info(f"   Timeframes: {self.timeframes}")
        logger.info(f"   Learning rate: {self.learning_rate}")
        logger.info(f"   Online learning: {self.enable_online_learning}")
        logger.info(f"   Reinforcement learning: {self.enable_reinforcement_learning}")

    def _initialize_online_models(self):
        """オンライン学習モデル初期化"""
        try:
            for timeframe in self.timeframes:
                if self.online_learning_method == "sgd_regressor":
                    # 確率的勾配降下法回帰器
                    model = SGDRegressor(
                        learning_rate="adaptive",
                        eta0=self.learning_rate,
                        alpha=0.01,
                        random_state=42,
                    )
                    self.online_models[timeframe] = model
                    self.scalers[timeframe] = StandardScaler()

            logger.info("✅ Online learning models initialized")

        except Exception as e:
            logger.error(f"Failed to initialize online models: {e}")
            self.enable_online_learning = False

    def _generate_weight_actions(self) -> List[Dict[str, float]]:
        """重み調整アクション空間生成"""
        actions = []

        # 基本アクション: 各タイムフレームの重み±10%調整
        for i, timeframe in enumerate(self.timeframes):
            # 重み増加アクション
            action_increase = {tf: 1.0 for tf in self.timeframes}
            action_increase[timeframe] = 1.1
            actions.append(action_increase)

            # 重み減少アクション
            action_decrease = {tf: 1.0 for tf in self.timeframes}
            action_decrease[timeframe] = 0.9
            actions.append(action_decrease)

        # 組み合わせアクション
        actions.extend(
            [
                {"15m": 1.2, "1h": 0.9, "4h": 0.9},  # 短期重視
                {"15m": 0.9, "1h": 1.2, "4h": 0.9},  # 中期重視
                {"15m": 0.9, "1h": 0.9, "4h": 1.2},  # 長期重視
                {"15m": 1.0, "1h": 1.0, "4h": 1.0},  # 維持
            ]
        )

        return actions

    def adjust_weights_dynamic(
        self,
        timeframe_predictions: Dict[str, Dict[str, Any]],
        market_context: Optional[Dict[str, Any]] = None,
        recent_performance: Optional[Dict[str, float]] = None,
    ) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """
        動的重み調整（Phase C2コア機能）

        Parameters:
        -----------
        timeframe_predictions : Dict[str, Dict[str, Any]]
            各タイムフレームの予測結果
        market_context : Dict[str, Any], optional
            市場環境コンテキスト
        recent_performance : Dict[str, float], optional
            最近の性能指標

        Returns:
        --------
        Tuple[Dict[str, float], Dict[str, Any]]
            (調整済み重み辞書, 調整情報)
        """
        self.adjustment_stats["total_adjustments"] += 1

        try:
            adjustment_info = {
                "adjustment_method": "multi_objective_dynamic",
                "timestamp": datetime.now(),
                "original_weights": self.current_weights.copy(),
            }

            # 1. 基本重みコピー
            adjusted_weights = self.current_weights.copy()

            # 2. 性能フィードバック調整
            if recent_performance:
                performance_adjustment = self._calculate_performance_adjustment(
                    recent_performance, timeframe_predictions
                )
                adjusted_weights = self._apply_weight_adjustment(
                    adjusted_weights, performance_adjustment, 0.3
                )
                adjustment_info["performance_adjustment"] = performance_adjustment
                self.adjustment_stats["performance_feedback_adjustments"] += 1

            # 3. 市場環境適応調整
            if market_context and self.market_analyzer:
                market_adjustment = self._calculate_market_adaptation_adjustment(
                    market_context, timeframe_predictions
                )
                adjusted_weights = self._apply_weight_adjustment(
                    adjusted_weights, market_adjustment, 0.4
                )
                adjustment_info["market_adjustment"] = market_adjustment
                self.adjustment_stats["market_adaptation_adjustments"] += 1

            # 4. オンライン学習調整
            if self.enable_online_learning:
                online_adjustment = self._calculate_online_learning_adjustment(
                    timeframe_predictions, market_context, recent_performance
                )
                if online_adjustment:
                    adjusted_weights = self._apply_weight_adjustment(
                        adjusted_weights, online_adjustment, 0.2
                    )
                    adjustment_info["online_learning_adjustment"] = online_adjustment
                    self.adjustment_stats["online_learning_updates"] += 1

            # 5. 強化学習調整
            if self.enable_reinforcement_learning:
                rl_adjustment = self._calculate_reinforcement_learning_adjustment(
                    timeframe_predictions, market_context, recent_performance
                )
                if rl_adjustment:
                    adjusted_weights = self._apply_weight_adjustment(
                        adjusted_weights, rl_adjustment, 0.1
                    )
                    adjustment_info["reinforcement_learning_adjustment"] = rl_adjustment
                    self.adjustment_stats["reinforcement_learning_updates"] += 1

            # 6. 重み正規化・制約適用
            final_weights = self._normalize_and_constrain_weights(adjusted_weights)

            # 7. 調整効果評価
            weight_change_magnitude = self._calculate_weight_change_magnitude(
                self.current_weights, final_weights
            )
            adjustment_info["weight_change_magnitude"] = weight_change_magnitude
            adjustment_info["final_weights"] = final_weights
            self.adjustment_stats["weight_change_magnitude"] = weight_change_magnitude

            # 8. 重み更新・履歴記録
            self._update_weights(final_weights, adjustment_info)

            logger.debug(
                f"🎛️ Dynamic weight adjustment: magnitude={weight_change_magnitude:.3f}, "
                f"methods={len([k for k in adjustment_info.keys() if 'adjustment' in k])}"
            )

            return final_weights, adjustment_info

        except Exception as e:
            logger.error(f"❌ Dynamic weight adjustment failed: {e}")
            return self.current_weights.copy(), {"error": True}

    def _calculate_performance_adjustment(
        self,
        recent_performance: Dict[str, float],
        timeframe_predictions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, float]:
        """性能フィードバックベース調整計算"""
        try:
            adjustments = {}

            for timeframe in self.timeframes:
                if timeframe not in timeframe_predictions:
                    adjustments[timeframe] = 1.0
                    continue

                # タイムフレーム別性能履歴取得
                tf_performance_history = self.performance_history[timeframe]

                if len(tf_performance_history) < self.min_samples_for_adjustment:
                    adjustments[timeframe] = 1.0
                    continue

                # 最近の性能スコア計算
                recent_scores = list(tf_performance_history)[-10:]  # 最近10件
                avg_recent_score = np.mean(recent_scores)

                # 全体平均との比較
                overall_avg = np.mean(list(tf_performance_history))

                # 性能向上率計算
                if overall_avg > 0:
                    performance_ratio = avg_recent_score / overall_avg
                else:
                    performance_ratio = 1.0

                # 調整係数計算
                if performance_ratio > 1.1:  # 10%以上の改善
                    adjustments[timeframe] = min(1.2, 1.0 + (performance_ratio - 1.0))
                elif performance_ratio < 0.9:  # 10%以上の悪化
                    adjustments[timeframe] = max(0.8, performance_ratio)
                else:
                    adjustments[timeframe] = 1.0

            return adjustments

        except Exception as e:
            logger.error(f"Performance adjustment calculation failed: {e}")
            return {tf: 1.0 for tf in self.timeframes}

    def _calculate_market_adaptation_adjustment(
        self,
        market_context: Dict[str, Any],
        timeframe_predictions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, float]:
        """市場環境適応調整計算"""
        try:
            if not self.market_analyzer:
                return {tf: 1.0 for tf in self.timeframes}

            # 市場環境解析実行（価格データが必要だが、ここではコンテキストから推定）
            market_regime = market_context.get("market_regime", "normal")
            volatility_score = market_context.get("volatility", 0.02)

            # レジーム別重み調整戦略
            if market_regime in ["crisis", "extreme_volatile"]:
                # 危機時：長期安定性重視
                adjustments = {
                    "15m": 0.7,
                    "1h": 1.0,
                    "4h": 1.3,
                }
            elif market_regime in ["volatile", "high_volatile"]:
                # 高ボラ時：中期バランス重視
                adjustments = {
                    "15m": 0.8,
                    "1h": 1.2,
                    "4h": 1.0,
                }
            elif market_regime in ["calm", "extreme_calm"]:
                # 安定時：短期機敏性重視
                adjustments = {
                    "15m": 1.2,
                    "1h": 1.0,
                    "4h": 0.9,
                }
            elif "bullish" in market_regime or "bearish" in market_regime:
                # トレンド時：中長期重視
                adjustments = {
                    "15m": 0.9,
                    "1h": 1.1,
                    "4h": 1.1,
                }
            else:
                # 通常時：バランス維持
                adjustments = {
                    "15m": 1.0,
                    "1h": 1.0,
                    "4h": 1.0,
                }

            # ボラティリティによる微調整
            if volatility_score > 0.05:  # 高ボラティリティ
                for tf in adjustments:
                    if tf == "4h":  # 長期をより重視
                        adjustments[tf] *= 1.1
                    elif tf == "15m":  # 短期を抑制
                        adjustments[tf] *= 0.95

            return adjustments

        except Exception as e:
            logger.error(f"Market adaptation adjustment failed: {e}")
            return {tf: 1.0 for tf in self.timeframes}

    def _calculate_online_learning_adjustment(
        self,
        timeframe_predictions: Dict[str, Dict[str, Any]],
        market_context: Optional[Dict[str, Any]],
        recent_performance: Optional[Dict[str, float]],
    ) -> Optional[Dict[str, float]]:
        """オンライン学習ベース調整計算"""
        try:
            if not self.enable_online_learning or not self.online_models:
                return None

            # 十分なデータが蓄積されるまで待機
            if len(self.prediction_outcomes) < self.min_samples_for_adjustment:
                return None

            # 定期的な再学習チェック
            if self.model_update_count % self.retraining_frequency != 0:
                self.model_update_count += 1
                return None

            adjustments = {}

            for timeframe in self.timeframes:
                if timeframe not in self.online_models:
                    adjustments[timeframe] = 1.0
                    continue

                # 特徴量準備
                features = self._prepare_online_features(
                    timeframe, timeframe_predictions, market_context
                )

                if features is None or len(features) == 0:
                    adjustments[timeframe] = 1.0
                    continue

                # モデル予測
                model = self.online_models[timeframe]
                scaler = self.scalers[timeframe]

                try:
                    # 特徴量スケーリング
                    if hasattr(scaler, "mean_"):  # 既に学習済み
                        features_scaled = scaler.transform([features])
                    else:
                        # 初回学習
                        features_scaled = scaler.fit_transform([features])

                    # 重み調整予測
                    if hasattr(model, "predict"):
                        predicted_adjustment = model.predict(features_scaled)[0]
                        # 調整係数を安全な範囲に制限
                        adjustment = max(0.8, min(1.2, predicted_adjustment))
                        adjustments[timeframe] = adjustment
                    else:
                        adjustments[timeframe] = 1.0

                except Exception as model_error:
                    logger.warning(
                        f"Online model prediction failed for {timeframe}: {model_error}"
                    )
                    adjustments[timeframe] = 1.0

            self.model_update_count += 1

            # 有効な調整が存在する場合のみ返す
            if any(adj != 1.0 for adj in adjustments.values()):
                return adjustments
            else:
                return None

        except Exception as e:
            logger.error(f"Online learning adjustment failed: {e}")
            return None

    def _calculate_reinforcement_learning_adjustment(
        self,
        timeframe_predictions: Dict[str, Dict[str, Any]],
        market_context: Optional[Dict[str, Any]],
        recent_performance: Optional[Dict[str, float]],
    ) -> Optional[Dict[str, float]]:
        """強化学習ベース調整計算（簡易Q-learning）"""
        try:
            if not self.enable_reinforcement_learning:
                return None

            # 十分な履歴が必要
            if len(self.weight_history) < 10:
                return None

            # 現在の状態定義
            current_state = self._encode_state(market_context, recent_performance)

            # ε-greedy行動選択
            if np.random.random() < self.epsilon:
                # 探索：ランダム行動
                action_idx = np.random.randint(len(self.action_space))
            else:
                # 活用：最良行動
                q_values = [
                    self.q_table[current_state][i]
                    for i in range(len(self.action_space))
                ]
                action_idx = np.argmax(q_values)

            # 選択された行動（重み調整）
            selected_action = self.action_space[action_idx]

            # ε減衰
            self.epsilon = max(0.01, self.epsilon * self.epsilon_decay)

            # Q値更新（前回の行動に対する報酬が利用可能な場合）
            if (
                recent_performance
                and len(self.weight_history) > 0
                and hasattr(self, "_last_rl_state")
                and hasattr(self, "_last_rl_action")
            ):

                reward = self._calculate_reward(recent_performance)
                last_state = self._last_rl_state
                last_action_idx = self._last_rl_action

                # Q(s,a) = Q(s,a) + α[r + γmax(Q(s',a')) - Q(s,a)]
                current_q = self.q_table[last_state][last_action_idx]
                max_future_q = max(
                    [
                        self.q_table[current_state][i]
                        for i in range(len(self.action_space))
                    ]
                )

                new_q = current_q + self.learning_rate * (
                    reward + self.discount_factor * max_future_q - current_q
                )
                self.q_table[last_state][last_action_idx] = new_q

            # 現在の状態・行動を記録
            self._last_rl_state = current_state
            self._last_rl_action = action_idx

            return selected_action

        except Exception as e:
            logger.error(f"Reinforcement learning adjustment failed: {e}")
            return None

    def _prepare_online_features(
        self,
        timeframe: str,
        timeframe_predictions: Dict[str, Dict[str, Any]],
        market_context: Optional[Dict[str, Any]],
    ) -> Optional[List[float]]:
        """オンライン学習用特徴量準備"""
        try:
            features = []

            # 1. タイムフレーム別予測特徴量
            if timeframe in timeframe_predictions:
                pred_data = timeframe_predictions[timeframe]
                features.extend(
                    [
                        pred_data.get("confidence", 0.5),
                        pred_data.get("unified_confidence", 0.5),
                        pred_data.get("model_agreement", 1.0),
                    ]
                )

                # 予測確率特徴量
                probability = pred_data.get("probability", np.array([[0.5, 0.5]]))
                if isinstance(probability, np.ndarray) and probability.shape[1] >= 2:
                    features.extend(
                        [
                            probability[0, 0],  # クラス0確率
                            probability[0, 1],  # クラス1確率
                            abs(probability[0, 1] - 0.5),  # 中立からの距離
                        ]
                    )
                else:
                    features.extend([0.5, 0.5, 0.0])

            else:
                features.extend([0.5, 0.5, 1.0, 0.5, 0.5, 0.0])

            # 2. 市場環境特徴量
            if market_context:
                features.extend(
                    [
                        market_context.get("vix_level", 20.0) / 100,  # 正規化
                        market_context.get("volatility", 0.02) * 50,  # 正規化
                        market_context.get("trend_strength", 0.5),
                        market_context.get("fear_greed", 50) / 100,  # 正規化
                    ]
                )
            else:
                features.extend([0.2, 1.0, 0.5, 0.5])

            # 3. 履歴特徴量
            if len(self.performance_history[timeframe]) > 0:
                recent_performance = list(self.performance_history[timeframe])[-5:]
                features.extend(
                    [
                        np.mean(recent_performance),
                        (
                            np.std(recent_performance)
                            if len(recent_performance) > 1
                            else 0.0
                        ),
                        max(recent_performance) if recent_performance else 0.5,
                        min(recent_performance) if recent_performance else 0.5,
                    ]
                )
            else:
                features.extend([0.5, 0.0, 0.5, 0.5])

            # 4. 重み履歴特徴量
            if len(self.weight_history) > 0:
                recent_weights = [
                    w["final_weights"].get(timeframe, 0.33)
                    for w in list(self.weight_history)[-5:]
                ]
                features.extend(
                    [
                        np.mean(recent_weights),
                        np.std(recent_weights) if len(recent_weights) > 1 else 0.0,
                    ]
                )
            else:
                features.extend([0.33, 0.0])

            return features if len(features) > 0 else None

        except Exception as e:
            logger.error(f"Online feature preparation failed for {timeframe}: {e}")
            return None

    def _encode_state(
        self,
        market_context: Optional[Dict[str, Any]],
        recent_performance: Optional[Dict[str, float]],
    ) -> str:
        """強化学習用状態エンコーディング"""
        try:
            state_components = []

            # 市場環境状態
            if market_context:
                regime = market_context.get("market_regime", "normal")
                vol_level = (
                    "high" if market_context.get("volatility", 0.02) > 0.04 else "low"
                )
                vix_level = (
                    "high" if market_context.get("vix_level", 20) > 25 else "low"
                )
                state_components.extend([regime, vol_level, vix_level])
            else:
                state_components.extend(["unknown", "unknown", "unknown"])

            # 性能状態
            if recent_performance:
                avg_performance = np.mean(list(recent_performance.values()))
                perf_level = (
                    "high"
                    if avg_performance > 0.7
                    else ("low" if avg_performance < 0.4 else "medium")
                )
                state_components.append(perf_level)
            else:
                state_components.append("unknown")

            return "_".join(state_components)

        except Exception as e:
            logger.error(f"State encoding failed: {e}")
            return "default_state"

    def _calculate_reward(self, recent_performance: Dict[str, float]) -> float:
        """強化学習報酬計算"""
        try:
            if not recent_performance:
                return 0.0

            # 多目的報酬設計
            accuracy_reward = (
                recent_performance.get("accuracy", 0.5) - 0.5
            )  # -0.5 to 0.5
            profitability_reward = recent_performance.get("profitability", 0.5) - 0.5
            risk_reward = 0.5 - recent_performance.get(
                "risk", 0.5
            )  # リスク低減で正報酬

            # 重み付き総合報酬
            total_reward = (
                accuracy_reward * self.accuracy_weight
                + profitability_reward * self.profitability_weight
                + risk_reward * self.risk_weight
            )

            return total_reward

        except Exception as e:
            logger.error(f"Reward calculation failed: {e}")
            return 0.0

    def _apply_weight_adjustment(
        self,
        current_weights: Dict[str, float],
        adjustment_factors: Dict[str, float],
        influence_strength: float,
    ) -> Dict[str, float]:
        """重み調整適用"""
        try:
            adjusted_weights = {}

            for timeframe in self.timeframes:
                current = current_weights.get(timeframe, 0.33)
                factor = adjustment_factors.get(timeframe, 1.0)

                # 影響強度を考慮した調整
                adjustment = current * (1.0 + (factor - 1.0) * influence_strength)
                adjusted_weights[timeframe] = adjustment

            return adjusted_weights

        except Exception as e:
            logger.error(f"Weight adjustment application failed: {e}")
            return current_weights.copy()

    def _normalize_and_constrain_weights(
        self, weights: Dict[str, float]
    ) -> Dict[str, float]:
        """重み正規化・制約適用"""
        try:
            # 制約適用（各重みを0.1-0.8の範囲に制限）
            constrained_weights = {}
            for timeframe, weight in weights.items():
                constrained_weights[timeframe] = max(0.1, min(0.8, weight))

            # 正規化（合計を1にする）
            total = sum(constrained_weights.values())
            if total > 0:
                normalized_weights = {
                    tf: weight / total for tf, weight in constrained_weights.items()
                }
            else:
                # フォールバック
                normalized_weights = dict(zip(self.timeframes, self.base_weights))

            return normalized_weights

        except Exception as e:
            logger.error(f"Weight normalization failed: {e}")
            return dict(zip(self.timeframes, self.base_weights))

    def _calculate_weight_change_magnitude(
        self, old_weights: Dict[str, float], new_weights: Dict[str, float]
    ) -> float:
        """重み変化の大きさ計算"""
        try:
            changes = []
            for timeframe in self.timeframes:
                old = old_weights.get(timeframe, 0.33)
                new = new_weights.get(timeframe, 0.33)
                changes.append(abs(new - old))

            return np.mean(changes)

        except Exception as e:
            logger.error(f"Weight change magnitude calculation failed: {e}")
            return 0.0

    def _update_weights(
        self, new_weights: Dict[str, float], adjustment_info: Dict[str, Any]
    ):
        """重み更新・履歴記録"""
        try:
            self.current_weights = new_weights.copy()

            # 重み履歴記録
            weight_record = {
                "timestamp": datetime.now(),
                "final_weights": new_weights.copy(),
                "adjustment_info": adjustment_info,
            }
            self.weight_history.append(weight_record)

            # 統計更新
            if adjustment_info.get("weight_change_magnitude", 0) > 0.02:  # 2%以上の変化
                self.adjustment_stats["successful_adjustments"] += 1

        except Exception as e:
            logger.error(f"Weight update failed: {e}")

    def record_prediction_outcome(
        self,
        timeframe_predictions: Dict[str, Dict[str, Any]],
        actual_outcome: Dict[str, Any],
        performance_metrics: Dict[str, float],
    ):
        """予測結果記録・オンライン学習データ更新"""
        try:
            # 予測結果履歴記録
            outcome_record = {
                "timestamp": datetime.now(),
                "predictions": timeframe_predictions.copy(),
                "actual_outcome": actual_outcome.copy(),
                "performance": performance_metrics.copy(),
            }
            self.prediction_outcomes.append(outcome_record)

            # タイムフレーム別性能履歴更新
            for timeframe in self.timeframes:
                if timeframe in performance_metrics:
                    self.performance_history[timeframe].append(
                        performance_metrics[timeframe]
                    )

            # オンライン学習モデル更新
            if self.enable_online_learning:
                self._update_online_models(
                    timeframe_predictions, actual_outcome, performance_metrics
                )

        except Exception as e:
            logger.error(f"Prediction outcome recording failed: {e}")

    def _update_online_models(
        self,
        timeframe_predictions: Dict[str, Dict[str, Any]],
        actual_outcome: Dict[str, Any],
        performance_metrics: Dict[str, float],
    ):
        """オンライン学習モデル更新"""
        try:
            for timeframe in self.timeframes:
                if timeframe not in self.online_models:
                    continue

                # 特徴量・ターゲット準備
                features = self._prepare_online_features(
                    timeframe, timeframe_predictions, actual_outcome
                )
                target = performance_metrics.get(timeframe, 0.5)

                if features is None or len(features) == 0:
                    continue

                # モデル更新
                model = self.online_models[timeframe]
                scaler = self.scalers[timeframe]

                try:
                    features_scaled = scaler.partial_fit([features]).transform(
                        [features]
                    )

                    if hasattr(model, "partial_fit"):
                        model.partial_fit(features_scaled, [target])
                    else:
                        # 一時的なデータセット作成
                        model.fit(features_scaled, [target])

                except Exception as model_error:
                    logger.warning(
                        f"Model update failed for {timeframe}: {model_error}"
                    )

        except Exception as e:
            logger.error(f"Online models update failed: {e}")

    def get_adjustment_statistics(self) -> Dict[str, Any]:
        """調整統計情報取得"""
        stats = self.adjustment_stats.copy()

        # 成功率計算
        if stats["total_adjustments"] > 0:
            stats["success_rate"] = (
                stats["successful_adjustments"] / stats["total_adjustments"]
            )
        else:
            stats["success_rate"] = 0.0

        # 学習状況
        stats["online_models_available"] = len(self.online_models)
        stats["q_table_size"] = len(self.q_table)
        stats["current_epsilon"] = self.epsilon
        stats["prediction_outcomes_count"] = len(self.prediction_outcomes)
        stats["weight_history_count"] = len(self.weight_history)

        # 現在の重み
        stats["current_weights"] = self.current_weights.copy()
        stats["weight_confidence"] = self.weight_confidence.copy()

        return stats

    def get_current_weights(self) -> Dict[str, float]:
        """現在の動的重み取得"""
        return self.current_weights.copy()

    def reset_statistics(self):
        """統計・履歴リセット"""
        for key in self.adjustment_stats:
            if isinstance(self.adjustment_stats[key], (int, float)):
                self.adjustment_stats[key] = (
                    0 if isinstance(self.adjustment_stats[key], int) else 0.0
                )

        for timeframe in self.timeframes:
            self.performance_history[timeframe].clear()

        self.prediction_outcomes.clear()
        self.weight_history.clear()
        self.market_context_history.clear()

        # Q-table リセット
        self.q_table.clear()
        self.epsilon = self.config.get("reinforcement_learning", {}).get("epsilon", 0.1)

        # オンライン学習モデル再初期化
        if self.enable_online_learning:
            self._initialize_online_models()

        logger.info("📊 Dynamic weight adjuster statistics reset")


# ファクトリー関数


def create_dynamic_weight_adjuster(config: Dict[str, Any]) -> DynamicWeightAdjuster:
    """
    動的重み調整システム作成

    Parameters:
    -----------
    config : Dict[str, Any]
        設定辞書

    Returns:
    --------
    DynamicWeightAdjuster
        初期化済み動的重み調整システム
    """
    return DynamicWeightAdjuster(config)
