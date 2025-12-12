"""
ポジションサイジング統合システム - Phase 49完了

Phase 28完了・Kelly基準と既存RiskManagerの統合クラス
動的ポジションサイジング対応・ML信頼度連動

設計思想:
- Kelly基準と既存RiskManagerの統合
- ML信頼度に基づく動的ポジションサイジング
- 3つの値（Dynamic, Kelly, RiskManager）から最も保守的な値を採用
"""

from typing import Dict, Optional

from ...core.config import get_threshold
from ...core.logger import get_logger
from .kelly import KellyCriterion


class PositionSizeIntegrator:
    """
    Kelly基準と既存RiskManagerの統合クラス
    """

    def __init__(self, kelly_criterion: KellyCriterion):
        """
        統合ポジションサイジング初期化

        Args:
            kelly_criterion: Kelly基準計算器
        """
        self.kelly = kelly_criterion
        self.logger = get_logger()

    def calculate_integrated_position_size(
        self,
        ml_confidence: float,
        risk_manager_confidence: float,
        strategy_name: str,
        config: Dict,
        current_balance: float = None,
        btc_price: float = None,
    ) -> float:
        """
        Kelly基準と既存RiskManagerの統合ポジションサイズ計算（動的サイジング対応）

        Args:
            ml_confidence: ML予測信頼度
            risk_manager_confidence: RiskManager用信頼度
            strategy_name: 戦略名
            config: 戦略設定
            current_balance: 現在残高（動的サイジング用）
            btc_price: BTC価格（動的サイジング用）

        Returns:
            統合ポジションサイズ（動的調整済み）
        """
        try:
            from ...core.config import get_threshold

            # 動的ポジションサイジングが有効かチェック
            dynamic_enabled = get_threshold(
                "position_management.dynamic_position_sizing.enabled", False
            )

            if dynamic_enabled and current_balance and btc_price:
                # 動的ポジションサイジングを使用
                dynamic_size = self._calculate_dynamic_position_size(
                    ml_confidence, current_balance, btc_price
                )

                # 従来のKelly+RiskManagerと比較して最小値を採用
                kelly_size = self.kelly.calculate_optimal_size(
                    ml_confidence=ml_confidence, strategy_name=strategy_name
                )

                from ...strategies.utils import RiskManager

                risk_manager_size = RiskManager.calculate_position_size(
                    confidence=risk_manager_confidence, config=config
                )

                # 3つの値のうち最も保守的な値を採用
                integrated_size = min(dynamic_size, kelly_size, risk_manager_size)

                self.logger.info(
                    f"動的統合ポジションサイズ計算: Dynamic={dynamic_size:.6f}, "
                    f"Kelly={kelly_size:.6f}, RiskManager={risk_manager_size:.6f}, "
                    f"採用={integrated_size:.6f} BTC (信頼度={ml_confidence:.1%})"
                )

                return integrated_size

            else:
                # 従来の方法を使用
                kelly_size = self.kelly.calculate_optimal_size(
                    ml_confidence=ml_confidence, strategy_name=strategy_name
                )

                from ...strategies.utils import RiskManager

                risk_manager_size = RiskManager.calculate_position_size(
                    confidence=risk_manager_confidence, config=config
                )

                integrated_size = min(kelly_size, risk_manager_size)

                self.logger.info(
                    f"統合ポジションサイズ計算: Kelly={kelly_size:.6f}, "
                    f"RiskManager={risk_manager_size:.6f}, 採用={integrated_size:.6f} BTC"
                )

                return integrated_size

        except Exception as e:
            self.logger.error(f"統合ポジションサイズ計算エラー: {e}")
            return 0.01  # フォールバック値

    def _calculate_dynamic_position_size(
        self, ml_confidence: float, current_balance: float, btc_price: float
    ) -> float:
        """
        ML信頼度に基づく動的ポジションサイジング

        Args:
            ml_confidence: ML予測信頼度 (0.0-1.0)
            current_balance: 現在の口座残高（円）
            btc_price: 現在のBTC価格（円）

        Returns:
            ポジションサイズ（BTC）
        """
        try:
            from ...core.config import get_threshold

            # ML信頼度によるカテゴリー決定と比率範囲取得
            if ml_confidence < 0.6:
                # 低信頼度
                min_ratio = get_threshold(
                    "position_management.dynamic_position_sizing.low_confidence.min_ratio", 0.01
                )
                max_ratio = get_threshold(
                    "position_management.dynamic_position_sizing.low_confidence.max_ratio", 0.03
                )
                confidence_category = "low"
            elif ml_confidence < 0.75:
                # 中信頼度
                min_ratio = get_threshold(
                    "position_management.dynamic_position_sizing.medium_confidence.min_ratio", 0.03
                )
                max_ratio = get_threshold(
                    "position_management.dynamic_position_sizing.medium_confidence.max_ratio", 0.05
                )
                confidence_category = "medium"
            else:
                # 高信頼度
                min_ratio = get_threshold(
                    "position_management.dynamic_position_sizing.high_confidence.min_ratio", 0.05
                )
                max_ratio = get_threshold(
                    "position_management.dynamic_position_sizing.high_confidence.max_ratio", 0.10
                )
                confidence_category = "high"

            # 信頼度に応じた線形補間で比率を計算
            if ml_confidence < 0.6:
                normalized_confidence = (ml_confidence - 0.5) / 0.1  # 0.5-0.6 -> 0-1
            elif ml_confidence < 0.75:
                normalized_confidence = (ml_confidence - 0.6) / 0.15  # 0.6-0.75 -> 0-1
            else:
                normalized_confidence = min((ml_confidence - 0.75) / 0.25, 1.0)  # 0.75-1.0 -> 0-1

            normalized_confidence = max(0.0, min(1.0, normalized_confidence))
            position_ratio = min_ratio + (max_ratio - min_ratio) * normalized_confidence

            # 資金による計算
            calculated_size = (current_balance * position_ratio) / btc_price

            # 最小ロット保証
            min_trade_size = get_threshold("position_management.min_trade_size", 0.0001)
            final_size = max(calculated_size, min_trade_size)

            # 資金規模別調整
            if current_balance < get_threshold(
                "position_management.account_size_adjustments.small.threshold", 50000
            ):
                # 少額資金：最小ロット優先
                override_enabled = get_threshold(
                    "position_management.account_size_adjustments.small.min_trade_override", True
                )
                if override_enabled:
                    final_size = max(final_size, min_trade_size)

            self.logger.info(
                f"動的ポジションサイズ: {confidence_category}信頼度({ml_confidence:.1%}) -> "
                f"比率={position_ratio:.1%}, サイズ={final_size:.6f} BTC, "
                f"残高={current_balance:.0f}円"
            )

            return final_size

        except Exception as e:
            self.logger.error(f"動的ポジションサイズ計算エラー: {e}")
            # フォールバック：最小ロットを返す
            return get_threshold("position_management.min_trade_size", 0.0001)
