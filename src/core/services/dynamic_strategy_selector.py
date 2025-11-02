"""
動的戦略選択器 - Phase 51.3

市場レジームに応じて戦略の重みを動的に選択するシステム。
MarketRegimeClassifierの分類結果に基づき、最適な戦略重みを返却する。

Phase 51.3: Dynamic Strategy Selection実装
"""

from typing import Dict

from ...core.config import get_threshold
from ...core.logger import get_logger
from .regime_types import RegimeType


class DynamicStrategySelector:
    """
    動的戦略選択器

    市場レジームに応じて戦略の重みを動的に選択し、
    StrategyManagerに適用するための重みマッピングを提供する。

    主要機能:
    - レジーム別戦略重み取得
    - 重み合計検証
    - 高ボラティリティ時の全戦略無効化

    Attributes:
        logger: ロガー
    """

    def __init__(self):
        """初期化"""
        self.logger = get_logger()

    def get_regime_weights(self, regime: RegimeType) -> Dict[str, float]:
        """
        市場レジームに応じた戦略重みを取得

        thresholds.yaml の dynamic_strategy_selection.regime_strategy_mapping から
        レジーム別の戦略重みを取得する。

        Args:
            regime: 市場レジーム分類結果

        Returns:
            Dict[str, float]: 戦略名と重みのマッピング
                例: {"ATRBased": 0.70, "DonchianChannel": 0.30}
                high_volatility時は空辞書 {}

        Raises:
            ValueError: 不正なレジームタイプの場合
        """
        if not isinstance(regime, RegimeType):
            raise ValueError(f"不正なレジームタイプ: {regime}")

        # thresholds.yaml から取得
        regime_value = regime.value  # "tight_range", "normal_range", etc.
        config_key = f"dynamic_strategy_selection.regime_strategy_mapping.{regime_value}"

        # デフォルト値: レジーム別フォールバック重み
        default_weights = self._get_default_weights(regime)

        # 設定ファイルから取得（get_threshold() パターン）
        weights = get_threshold(config_key, default_weights)

        # 高ボラティリティは空辞書（全戦略無効化）
        if regime == RegimeType.HIGH_VOLATILITY and not weights:
            self.logger.info(f"⚠️ 高ボラティリティ検出: 全戦略無効化（待機モード）")
            return {}

        # 重み検証
        if weights and not self.validate_weights(weights):
            self.logger.warning(
                f"⚠️ レジーム {regime.value} の重み合計が1.0ではありません: "
                f"{sum(weights.values()):.3f} - デフォルト重みを使用"
            )
            weights = default_weights

        self.logger.info(
            f"✅ 動的戦略選択: レジーム={regime.value}, "
            f"戦略重み={{{', '.join([f'{k}: {v:.2f}' for k, v in weights.items()])}}}"
        )

        return weights

    def validate_weights(self, weights: Dict[str, float]) -> bool:
        """
        戦略重みの合計が1.0または0.0であることを検証

        Args:
            weights: 戦略重みマッピング

        Returns:
            bool: 重み合計が1.0または0.0の場合True（許容誤差: ±0.01）
                  - 1.0: 通常レジーム（戦略有効）
                  - 0.0: 高ボラティリティレジーム（全戦略無効化）
        """
        if not weights:
            return True  # 空辞書は有効（高ボラティリティ時・後方互換性）

        total_weight = sum(weights.values())
        # 浮動小数点演算の誤差を考慮して許容範囲を設定
        # 合計1.0（通常）または0.0（全戦略無効化）を許可
        is_valid_one = 0.99 <= total_weight <= 1.01
        is_valid_zero = -0.01 <= total_weight <= 0.01
        return is_valid_one or is_valid_zero

    def _get_default_weights(self, regime: RegimeType) -> Dict[str, float]:
        """
        デフォルト戦略重みを返す（フォールバック用）

        重要: 全5戦略の重みを返す（使用しない戦略は0.0に設定）
              StrategyManager.update_strategy_weights()は部分的な更新のみを行うため、
              レジームに含まれない戦略を明示的に0.0にする必要がある。

        Args:
            regime: 市場レジーム

        Returns:
            Dict[str, float]: デフォルト戦略重み（3戦略・Phase 51.5-A・合計1.0）
        """
        if regime == RegimeType.TIGHT_RANGE:
            return {
                "ATRBased": 0.70,
                "DonchianChannel": 0.30,
                "ADXTrendStrength": 0.0,
            }
        elif regime == RegimeType.NORMAL_RANGE:
            return {
                "ATRBased": 0.50,
                "DonchianChannel": 0.30,
                "ADXTrendStrength": 0.20,
            }
        elif regime == RegimeType.TRENDING:
            return {
                "ADXTrendStrength": 0.60,
                "ATRBased": 0.30,
                "DonchianChannel": 0.10,
            }
        elif regime == RegimeType.HIGH_VOLATILITY:
            # 高ボラティリティは全戦略0.0（全戦略無効化）
            return {
                "ATRBased": 0.0,
                "DonchianChannel": 0.0,
                "ADXTrendStrength": 0.0,
            }
        else:
            # 未知のレジーム: 均等重み（3戦略・Phase 51.5-A）
            self.logger.warning(f"⚠️ 未知のレジーム: {regime.value} - 均等重みを使用")
            return {
                "ATRBased": 0.33,
                "DonchianChannel": 0.33,
                "ADXTrendStrength": 0.34,
            }

    def is_enabled(self) -> bool:
        """
        動的戦略選択機能が有効かどうかを確認

        Returns:
            bool: 有効な場合True
        """
        enabled = get_threshold("dynamic_strategy_selection.enabled", True)
        return enabled
