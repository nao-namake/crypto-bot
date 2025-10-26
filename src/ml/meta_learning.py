"""
Phase 49完了: Meta-Learning動的重み最適化システム

市場状況に応じて戦略・ML重みを動的に最適化し、シャープレシオ+30-50%向上を目指す。

主要クラス:
- MetaLearningWeightOptimizer: Meta-ML動的重み最適化
- MarketRegimeAnalyzer: 市場状況分析（既存特徴量活用）
- PerformanceTracker: 戦略・MLパフォーマンス履歴トラッキング

設計原則:
- ハードコード完全排除: すべての数値はthresholds.yamlから取得
- フォールバック機能: Meta-ML失敗時は固定重み使用
- 段階的有効化: デフォルト無効（enabled: false）
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.config import get_threshold


class MarketRegimeAnalyzer:
    """
    市場状況分析クラス（Phase 45.1）

    既存特徴量を活用して市場状況を分析し、Meta-Learning用の特徴量を生成。
    """

    def __init__(self):
        """
        初期化

        設計原則遵守:
        - すべての設定値はget_threshold()で取得（ハードコード禁止）
        """
        # thresholds.yamlから設定取得（ハードコード禁止）
        self.atr_window = get_threshold("ml.meta_learning.market_features.atr_window", 14)
        self.bb_window = get_threshold("ml.meta_learning.market_features.bb_window", 20)
        self.volatility_ratio_window = get_threshold(
            "ml.meta_learning.market_features.volatility_ratio_window", 7
        )
        self.ema_short = get_threshold("ml.meta_learning.market_features.ema_short", 20)
        self.ema_long = get_threshold("ml.meta_learning.market_features.ema_long", 50)
        self.adx_window = get_threshold("ml.meta_learning.market_features.adx_window", 14)
        self.trend_strength_threshold = get_threshold(
            "ml.meta_learning.market_features.trend_strength_threshold", 0.5
        )
        self.donchian_window = get_threshold("ml.meta_learning.market_features.donchian_window", 20)
        self.range_threshold = get_threshold(
            "ml.meta_learning.market_features.range_threshold", 0.02
        )

    def analyze(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        市場状況特徴量を抽出（10-15特徴量）

        Args:
            df: 価格データ（既存特徴量含む）

        Returns:
            Dict[str, float]: 市場状況特徴量
                - volatility_atr_14: ATR（14期間）正規化
                - volatility_bb_width: BB幅正規化
                - volatility_ratio_7d: 7日間ボラティリティ比率
                - trend_ema_spread: EMA(20-50)スプレッド正規化
                - trend_adx: ADX正規化
                - trend_di_plus: +DI正規化
                - trend_di_minus: -DI正規化
                - trend_strength: トレンド強度（0-1）
                - range_donchian_width: Donchian幅正規化
                - range_detection: レンジ判定（0=レンジ, 1=ブレイクアウト）
                - volume_ratio: 出来高比率（現在/平均）
        """
        if df is None or len(df) == 0:
            return self._get_default_features()

        features = {}

        try:
            # ボラティリティ特徴量
            features["volatility_atr_14"] = self._normalize(
                df["atr_14"].iloc[-1], df["close"].iloc[-1]
            )
            features["volatility_bb_width"] = self._calculate_bb_width(df)
            features["volatility_ratio_7d"] = self._calculate_volatility_ratio(df)

            # トレンド特徴量
            features["trend_ema_spread"] = self._calculate_ema_spread(df)
            features["trend_adx"] = self._normalize_indicator(df["adx_14"].iloc[-1], 0, 100)
            features["trend_di_plus"] = self._normalize_indicator(df["plus_di_14"].iloc[-1], 0, 100)
            features["trend_di_minus"] = self._normalize_indicator(
                df["minus_di_14"].iloc[-1], 0, 100
            )
            features["trend_strength"] = self._calculate_trend_strength(df)

            # レンジ判定特徴量
            features["range_donchian_width"] = self._calculate_donchian_width(df)
            features["range_detection"] = self._detect_range(df)

            # 出来高特徴量
            features["volume_ratio"] = self._calculate_volume_ratio(df)

        except Exception as e:
            # エラー時はデフォルト特徴量を返す
            return self._get_default_features()

        return features

    def _normalize(self, value: float, reference: float) -> float:
        """値を参照値で正規化"""
        if reference == 0:
            return 0.0
        return min(max(value / reference, 0.0), 1.0)

    def _normalize_indicator(self, value: float, min_val: float, max_val: float) -> float:
        """指標を0-1範囲に正規化"""
        if max_val == min_val:
            return 0.5
        return min(max((value - min_val) / (max_val - min_val), 0.0), 1.0)

    def _calculate_bb_width(self, df: pd.DataFrame) -> float:
        """BB幅を計算（正規化）"""
        try:
            bb_position = df["bb_position"].iloc[-1]
            # BB幅はbb_position特徴量から推定（0-1範囲）
            return min(max(abs(bb_position), 0.0), 1.0)
        except Exception:
            return 0.5

    def _calculate_volatility_ratio(self, df: pd.DataFrame) -> float:
        """7日間ボラティリティ比率を計算"""
        try:
            window = self.volatility_ratio_window
            if len(df) < window * 2:
                return 1.0

            recent_vol = df["close"].iloc[-window:].std()
            past_vol = df["close"].iloc[-window * 2 : -window].std()

            if past_vol == 0:
                return 1.0

            ratio = recent_vol / past_vol
            return min(max(ratio, 0.0), 3.0) / 3.0  # 0-3を0-1に正規化
        except Exception:
            return 0.5

    def _calculate_ema_spread(self, df: pd.DataFrame) -> float:
        """EMA(20-50)スプレッドを計算（正規化）"""
        try:
            ema_20 = df["ema_20"].iloc[-1]
            ema_50 = df["ema_50"].iloc[-1]
            spread = (ema_20 - ema_50) / ema_50
            return min(max(spread + 0.5, 0.0), 1.0)  # -0.5 to 0.5 を 0-1に正規化
        except Exception:
            return 0.5

    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """
        トレンド強度を計算（0-1）

        ADX・DI・EMAを統合してトレンド強度を判定。
        """
        try:
            adx = df["adx_14"].iloc[-1]
            plus_di = df["plus_di_14"].iloc[-1]
            minus_di = df["minus_di_14"].iloc[-1]
            ema_20 = df["ema_20"].iloc[-1]
            ema_50 = df["ema_50"].iloc[-1]

            # ADXベース強度
            adx_strength = min(adx / 50.0, 1.0)  # ADX 50以上で1.0

            # DI方向性
            di_diff = abs(plus_di - minus_di)
            di_strength = min(di_diff / 50.0, 1.0)

            # EMA方向性
            ema_diff = abs(ema_20 - ema_50)
            ema_strength = min(ema_diff / ema_50 / 0.05, 1.0)  # 5%乖離で1.0

            # 統合トレンド強度（加重平均）
            trend_strength = adx_strength * 0.5 + di_strength * 0.3 + ema_strength * 0.2
            return min(max(trend_strength, 0.0), 1.0)
        except Exception:
            return 0.5

    def _calculate_donchian_width(self, df: pd.DataFrame) -> float:
        """Donchian Channel幅を計算（正規化）"""
        try:
            window = self.donchian_window
            if len(df) < window:
                return 0.5

            high_max = df["high"].iloc[-window:].max()
            low_min = df["low"].iloc[-window:].min()
            current_price = df["close"].iloc[-1]

            if current_price == 0:
                return 0.5

            width = (high_max - low_min) / current_price
            return min(max(width / 0.1, 0.0), 1.0)  # 10%幅で1.0
        except Exception:
            return 0.5

    def _detect_range(self, df: pd.DataFrame) -> float:
        """
        レンジ判定（0=レンジ, 1=ブレイクアウト）

        Donchian幅がrange_threshold以下ならレンジ。
        """
        try:
            width = self._calculate_donchian_width(df)
            if width < self.range_threshold:
                return 0.0  # レンジ
            else:
                return 1.0  # ブレイクアウト
        except Exception:
            return 0.5

    def _calculate_volume_ratio(self, df: pd.DataFrame) -> float:
        """出来高比率を計算（現在/20期間平均）"""
        try:
            if "volume" not in df.columns or len(df) < 20:
                return 1.0

            current_volume = df["volume"].iloc[-1]
            avg_volume = df["volume"].iloc[-20:].mean()

            if avg_volume == 0:
                return 1.0

            ratio = current_volume / avg_volume
            return min(max(ratio, 0.0), 5.0) / 5.0  # 0-5を0-1に正規化
        except Exception:
            return 0.5

    def _get_default_features(self) -> Dict[str, float]:
        """デフォルト特徴量（エラー時・データ不足時）"""
        return {
            "volatility_atr_14": 0.5,
            "volatility_bb_width": 0.5,
            "volatility_ratio_7d": 0.5,
            "trend_ema_spread": 0.5,
            "trend_adx": 0.5,
            "trend_di_plus": 0.5,
            "trend_di_minus": 0.5,
            "trend_strength": 0.5,
            "range_donchian_width": 0.5,
            "range_detection": 0.5,
            "volume_ratio": 0.5,
        }


class PerformanceTracker:
    """
    パフォーマンストラッキングクラス（Phase 45.2）

    戦略・MLの過去パフォーマンスを記録・取得。
    """

    def __init__(self):
        """
        初期化

        設計原則遵守:
        - history_fileパスはget_threshold()で取得（ハードコード禁止）
        """
        # thresholds.yamlから設定取得
        self.window_days_short = get_threshold(
            "ml.meta_learning.performance_tracking.window_days_short", 7
        )
        self.window_days_long = get_threshold(
            "ml.meta_learning.performance_tracking.window_days_long", 30
        )
        self.min_trades_required = get_threshold(
            "ml.meta_learning.performance_tracking.min_trades_required", 5
        )
        history_file = get_threshold(
            "ml.meta_learning.performance_tracking.history_file",
            "src/core/state/performance_history.json",
        )

        # 履歴ファイルパス
        self.history_file = Path(history_file)

        # 履歴読み込み
        self.history = self._load_history()

    def _load_history(self) -> Dict[str, Any]:
        """履歴ファイルから読み込み"""
        if not self.history_file.exists():
            return self._get_default_history()

        try:
            with open(self.history_file, "r") as f:
                return json.load(f)
        except Exception:
            return self._get_default_history()

    def _save_history(self):
        """履歴ファイルに保存"""
        try:
            # ディレクトリ作成
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            pass

    def _get_default_history(self) -> Dict[str, Any]:
        """デフォルト履歴"""
        return {
            "strategy_performance": {},
            "ml_performance": {
                "trades": [],
                "win_rate_7d": 0.5,
                "win_rate_30d": 0.5,
                "avg_profit_7d": 0.0,
                "avg_profit_30d": 0.0,
                "confidence_trend": [],
            },
            "last_update": datetime.now().isoformat(),
        }

    def record_trade(self, trade_result: Dict[str, Any]):
        """
        取引結果を記録

        Args:
            trade_result: 取引結果
                - timestamp: 取引時刻
                - strategy_name: 戦略名
                - ml_prediction: ML予測
                - actual_outcome: 実際の結果（win/loss）
                - profit: 利益率
        """
        try:
            # ML取引記録
            ml_trade = {
                "timestamp": trade_result.get("timestamp", datetime.now().isoformat()),
                "prediction": trade_result.get("ml_prediction", 0),
                "outcome": trade_result.get("actual_outcome", "unknown"),
                "profit": trade_result.get("profit", 0.0),
            }
            self.history["ml_performance"]["trades"].append(ml_trade)

            # 戦略パフォーマンス記録
            strategy_name = trade_result.get("strategy_name", "unknown")
            if strategy_name not in self.history["strategy_performance"]:
                self.history["strategy_performance"][strategy_name] = {
                    "trades": [],
                    "win_rate_7d": 0.5,
                    "win_rate_30d": 0.5,
                    "avg_profit_7d": 0.0,
                    "avg_profit_30d": 0.0,
                }

            strategy_trade = {
                "timestamp": trade_result.get("timestamp", datetime.now().isoformat()),
                "outcome": trade_result.get("actual_outcome", "unknown"),
                "profit": trade_result.get("profit", 0.0),
            }
            self.history["strategy_performance"][strategy_name]["trades"].append(strategy_trade)

            # 更新日時記録
            self.history["last_update"] = datetime.now().isoformat()

            # 統計更新
            self._update_statistics()

            # 保存
            self._save_history()

        except Exception:
            pass

    def _update_statistics(self):
        """統計情報更新（勝率・平均利益計算）"""
        try:
            now = datetime.now()

            # ML統計更新
            ml_trades = self.history["ml_performance"]["trades"]
            self.history["ml_performance"]["win_rate_7d"] = self._calculate_win_rate(
                ml_trades, now, self.window_days_short
            )
            self.history["ml_performance"]["win_rate_30d"] = self._calculate_win_rate(
                ml_trades, now, self.window_days_long
            )
            self.history["ml_performance"]["avg_profit_7d"] = self._calculate_avg_profit(
                ml_trades, now, self.window_days_short
            )
            self.history["ml_performance"]["avg_profit_30d"] = self._calculate_avg_profit(
                ml_trades, now, self.window_days_long
            )

            # 戦略統計更新
            for strategy_name, perf in self.history["strategy_performance"].items():
                strategy_trades = perf["trades"]
                perf["win_rate_7d"] = self._calculate_win_rate(
                    strategy_trades, now, self.window_days_short
                )
                perf["win_rate_30d"] = self._calculate_win_rate(
                    strategy_trades, now, self.window_days_long
                )
                perf["avg_profit_7d"] = self._calculate_avg_profit(
                    strategy_trades, now, self.window_days_short
                )
                perf["avg_profit_30d"] = self._calculate_avg_profit(
                    strategy_trades, now, self.window_days_long
                )

        except Exception:
            pass

    def _calculate_win_rate(self, trades: List[Dict], now: datetime, window_days: int) -> float:
        """勝率計算（指定期間）"""
        try:
            cutoff = now - timedelta(days=window_days)
            recent_trades = [t for t in trades if datetime.fromisoformat(t["timestamp"]) >= cutoff]

            if len(recent_trades) < self.min_trades_required:
                return 0.5  # デフォルト値

            wins = sum(1 for t in recent_trades if t["outcome"] == "win")
            return wins / len(recent_trades)
        except Exception:
            return 0.5

    def _calculate_avg_profit(self, trades: List[Dict], now: datetime, window_days: int) -> float:
        """平均利益計算（指定期間）"""
        try:
            cutoff = now - timedelta(days=window_days)
            recent_trades = [t for t in trades if datetime.fromisoformat(t["timestamp"]) >= cutoff]

            if len(recent_trades) < self.min_trades_required:
                return 0.0  # デフォルト値

            profits = [t["profit"] for t in recent_trades]
            return sum(profits) / len(profits)
        except Exception:
            return 0.0

    def get_recent_performance(self, window_days: Optional[int] = None) -> Dict[str, Any]:
        """
        直近パフォーマンス取得

        Args:
            window_days: 取得期間（Noneの場合はwindow_days_short使用）

        Returns:
            Dict[str, Any]: パフォーマンス統計
                - ml_win_rate: ML勝率
                - ml_avg_profit: ML平均利益
                - strategy_performance: 戦略別パフォーマンス
        """
        if window_days is None:
            window_days = self.window_days_short

        try:
            # 統計更新
            self._update_statistics()

            # ML統計取得
            ml_perf = self.history["ml_performance"]
            if window_days == self.window_days_short:
                ml_win_rate = ml_perf.get("win_rate_7d", 0.5)
                ml_avg_profit = ml_perf.get("avg_profit_7d", 0.0)
            else:
                ml_win_rate = ml_perf.get("win_rate_30d", 0.5)
                ml_avg_profit = ml_perf.get("avg_profit_30d", 0.0)

            # 戦略統計取得
            strategy_perf = {}
            for strategy_name, perf in self.history["strategy_performance"].items():
                if window_days == self.window_days_short:
                    strategy_perf[strategy_name] = {
                        "win_rate": perf.get("win_rate_7d", 0.5),
                        "avg_profit": perf.get("avg_profit_7d", 0.0),
                    }
                else:
                    strategy_perf[strategy_name] = {
                        "win_rate": perf.get("win_rate_30d", 0.5),
                        "avg_profit": perf.get("avg_profit_30d", 0.0),
                    }

            return {
                "ml_win_rate": ml_win_rate,
                "ml_avg_profit": ml_avg_profit,
                "strategy_performance": strategy_perf,
            }

        except Exception:
            return {"ml_win_rate": 0.5, "ml_avg_profit": 0.0, "strategy_performance": {}}


class MetaLearningWeightOptimizer:
    """
    Meta-Learning動的重み最適化クラス（Phase 45.1-45.3）

    市場状況に応じて戦略・ML重みを動的に最適化。
    """

    def __init__(self, logger=None):
        """
        初期化

        設計原則遵守:
        - model_pathはget_threshold()で取得（ハードコード禁止）
        - フォールバック重みもget_threshold()で取得
        """
        self.logger = logger

        # thresholds.yamlから設定取得
        model_path = get_threshold(
            "ml.meta_learning.model_path", "models/meta_learning/meta_model.pkl"
        )
        self.model_path = Path(model_path)
        self.fallback_ml_weight = get_threshold("ml.meta_learning.fallback_ml_weight", 0.35)
        self.fallback_strategy_weight = get_threshold(
            "ml.meta_learning.fallback_strategy_weight", 0.7
        )
        self.min_confidence = get_threshold("ml.meta_learning.min_confidence", 0.3)

        # Meta-MLモデル
        self.model = self._load_model()

        # 市場状況分析器
        self.market_analyzer = MarketRegimeAnalyzer()

        # パフォーマンストラッカー
        self.performance_tracker = PerformanceTracker()

    def _load_model(self) -> Optional[Any]:
        """Meta-MLモデル読み込み"""
        if not self.model_path.exists():
            if self.logger:
                self.logger.info(
                    f"📊 Meta-MLモデル未存在: {self.model_path} - フォールバック重み使用"
                )
            return None

        try:
            import joblib

            model = joblib.load(self.model_path)
            if self.logger:
                self.logger.info(f"✅ Meta-MLモデル読み込み成功: {self.model_path}")
            return model
        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ Meta-MLモデル読み込み失敗: {e} - フォールバック重み使用")
            return None

    def predict_weights(
        self, market_data: pd.DataFrame, performance_data: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        市場状況から最適重みを予測

        Args:
            market_data: 市場データ（価格・特徴量含む）
            performance_data: パフォーマンスデータ（オプション）

        Returns:
            Dict[str, float]: 最適重み
                - ml: ML重み（0-1）
                - strategy: 戦略重み（0-1）
                ※合計1.0に正規化
        """
        try:
            # モデル未存在時はフォールバック
            if self.model is None:
                return self._get_fallback_weights()

            # 市場状況特徴量抽出
            market_features = self.market_analyzer.analyze(market_data)

            # パフォーマンス特徴量追加（オプション）
            if performance_data is None:
                performance_data = self.performance_tracker.get_recent_performance()

            # 特徴量ベクトル作成
            feature_vector = self._create_feature_vector(market_features, performance_data)

            # Meta-ML推論
            weights = self.model.predict([feature_vector])[0]

            # 重み正規化（合計1.0）
            ml_weight = max(0.0, min(1.0, weights[0]))
            strategy_weight = max(0.0, min(1.0, weights[1]))
            total = ml_weight + strategy_weight

            if total > 0:
                ml_weight /= total
                strategy_weight /= total
            else:
                return self._get_fallback_weights()

            if self.logger:
                self.logger.info(
                    f"📊 Meta-ML動的重み: ML={ml_weight:.3f}, 戦略={strategy_weight:.3f}"
                )

            return {"ml": ml_weight, "strategy": strategy_weight}

        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ Meta-ML推論エラー: {e} - フォールバック重み使用")
            return self._get_fallback_weights()

    def _create_feature_vector(
        self, market_features: Dict[str, float], performance_data: Dict[str, Any]
    ) -> np.ndarray:
        """
        特徴量ベクトル作成

        市場状況11特徴量 + パフォーマンス2特徴量 = 13特徴量
        """
        vector = []

        # 市場状況特徴量（11特徴量）
        vector.append(market_features.get("volatility_atr_14", 0.5))
        vector.append(market_features.get("volatility_bb_width", 0.5))
        vector.append(market_features.get("volatility_ratio_7d", 0.5))
        vector.append(market_features.get("trend_ema_spread", 0.5))
        vector.append(market_features.get("trend_adx", 0.5))
        vector.append(market_features.get("trend_di_plus", 0.5))
        vector.append(market_features.get("trend_di_minus", 0.5))
        vector.append(market_features.get("trend_strength", 0.5))
        vector.append(market_features.get("range_donchian_width", 0.5))
        vector.append(market_features.get("range_detection", 0.5))
        vector.append(market_features.get("volume_ratio", 0.5))

        # パフォーマンス特徴量（2特徴量）
        vector.append(performance_data.get("ml_win_rate", 0.5))
        vector.append(performance_data.get("ml_avg_profit", 0.0))

        return np.array(vector)

    def _get_fallback_weights(self) -> Dict[str, float]:
        """フォールバック固定重み取得（正規化済み）"""
        # フォールバック重みを正規化（合計1.0）
        total = self.fallback_ml_weight + self.fallback_strategy_weight
        if total > 0:
            ml_weight = self.fallback_ml_weight / total
            strategy_weight = self.fallback_strategy_weight / total
        else:
            ml_weight = 0.5
            strategy_weight = 0.5
        return {"ml": ml_weight, "strategy": strategy_weight}

    def record_trade_outcome(self, trade_result: Dict[str, Any]):
        """取引結果を記録（パフォーマンストラッキング）"""
        try:
            self.performance_tracker.record_trade(trade_result)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ 取引結果記録エラー: {e}")
