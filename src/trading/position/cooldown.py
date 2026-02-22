"""
クールダウン管理サービス - Phase 64
Phase 31.1: 柔軟なクールダウン機能

強いトレンド発生時はクールダウンをスキップし、機会損失を防ぐ。
"""

from typing import Any, Dict

import pandas as pd

from ...core.config import get_features_config
from ...core.logger import get_logger
from ..core import TradeEvaluation


class CooldownManager:
    """
    クールダウン管理サービス

    トレンド強度に基づいて柔軟なクールダウン判定を行う。
    """

    def __init__(self):
        """CooldownManager初期化"""
        self.logger = get_logger()

    async def should_apply_cooldown(self, evaluation: TradeEvaluation) -> bool:
        """
        Phase 31.1: 柔軟なクールダウン判定

        強いトレンド発生時はクールダウンをスキップし、
        機会損失を防ぐ。

        Args:
            evaluation: 取引評価結果（market_conditionsを含む）

        Returns:
            bool: クールダウンを適用するか
        """
        try:
            # 機能トグル設定を取得
            features = get_features_config()
            features_config = features.get("trading", {}).get("cooldown", {})

            # クールダウン無効の場合は適用しない
            if not features_config.get("enabled", True):
                return False

            # 柔軟モード無効の場合は常に適用
            if not features_config.get("flexible_mode", False):
                return True

            # 柔軟モード: トレンド強度を判定
            market_data = evaluation.market_conditions.get("market_data")
            if market_data is None:
                # 市場データがない場合はデフォルトで適用
                return True

            trend_strength = self.calculate_trend_strength(market_data)
            threshold = features_config.get("trend_strength_threshold", 0.7)

            # 強いトレンド時はクールダウンをスキップ
            if trend_strength >= threshold:
                self.logger.info(
                    f"🔥 強トレンド検出 (強度: {trend_strength:.2f}) - クールダウンスキップ"
                )
                return False

            return True

        except Exception as e:
            self.logger.warning(f"⚠️ クールダウン判定エラー: {e} - デフォルトで適用")
            return True

    def calculate_trend_strength(self, market_data: Dict) -> float:
        """
        Phase 31.1: トレンド強度計算（ADX・DI・EMA総合判定）

        Args:
            market_data: 市場データ（特徴量含む）

        Returns:
            float: トレンド強度 (0.0-1.0)
        """
        try:
            # 4h足データを使用してトレンド強度を判定
            df = market_data.get("4h", pd.DataFrame())
            if df.empty or len(df) < 3:
                return 0.0

            # ADX（トレンド強度指標）
            adx = float(df["adx_14"].iloc[-1]) if "adx_14" in df.columns else 0.0

            # DI差分（方向性）
            plus_di = float(df["plus_di_14"].iloc[-1]) if "plus_di_14" in df.columns else 0.0
            minus_di = float(df["minus_di_14"].iloc[-1]) if "minus_di_14" in df.columns else 0.0
            di_diff = abs(plus_di - minus_di)

            # EMAトレンド（方向の一貫性）
            ema_20 = float(df["ema_20"].iloc[-1]) if "ema_20" in df.columns else 0.0
            ema_50 = float(df["ema_50"].iloc[-1]) if "ema_50" in df.columns else 0.0
            ema_trend = abs(ema_20 - ema_50) / ema_50 if ema_50 > 0 else 0.0

            # トレンド強度スコア算出
            # ADX: 25以上で強いトレンド（正規化: 0-50 → 0-1）
            adx_score = min(1.0, adx / 50.0)

            # DI差分: 20以上で明確な方向性（正規化: 0-40 → 0-1）
            di_score = min(1.0, di_diff / 40.0)

            # EMAトレンド: 2%以上で明確なトレンド（正規化: 0-5% → 0-1）
            ema_score = min(1.0, ema_trend / 0.05)

            # 加重平均（ADX重視: 50%、DI: 30%、EMA: 20%）
            trend_strength = adx_score * 0.5 + di_score * 0.3 + ema_score * 0.2

            self.logger.debug(
                f"トレンド強度計算: ADX={adx:.1f}({adx_score:.2f}), "
                f"DI差={di_diff:.1f}({di_score:.2f}), "
                f"EMAトレンド={ema_trend:.3f}({ema_score:.2f}) → 総合={trend_strength:.2f}"
            )

            return trend_strength

        except Exception as e:
            self.logger.error(f"❌ トレンド強度計算エラー: {e}")
            return 0.0

    def get_cooldown_status(self, trend_strength: float) -> Dict[str, Any]:
        """
        クールダウンステータスを取得

        Args:
            trend_strength: トレンド強度

        Returns:
            クールダウン状態情報
        """
        try:
            features = get_features_config()
            features_config = features.get("trading", {}).get("cooldown", {})

            enabled = features_config.get("enabled", True)
            flexible_mode = features_config.get("flexible_mode", False)
            threshold = features_config.get("trend_strength_threshold", 0.7)

            status = {
                "enabled": enabled,
                "flexible_mode": flexible_mode,
                "trend_strength": trend_strength,
                "threshold": threshold,
                "skip_cooldown": False,
                "reason": "",
            }

            if not enabled:
                status["reason"] = "クールダウン無効"
            elif not flexible_mode:
                status["reason"] = "通常モード（常に適用）"
            elif trend_strength >= threshold:
                status["skip_cooldown"] = True
                status["reason"] = f"強トレンド検出（{trend_strength:.2f} >= {threshold}）"
            else:
                status["reason"] = f"トレンド弱（{trend_strength:.2f} < {threshold}）"

            return status

        except Exception as e:
            self.logger.error(f"❌ クールダウンステータス取得エラー: {e}")
            return {
                "enabled": True,
                "flexible_mode": False,
                "trend_strength": 0.0,
                "threshold": 0.7,
                "skip_cooldown": False,
                "reason": f"エラー: {e}",
            }
