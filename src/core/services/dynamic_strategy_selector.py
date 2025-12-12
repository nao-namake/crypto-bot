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
            # Phase 51.8-J4-G: バックテストモードで可視化するためWARNINGレベルに変更
            self.logger.warning(f"⚠️ 高ボラティリティ検出: 全戦略無効化（待機モード）")
            return {}

        # 重み検証
        if weights and not self.validate_weights(weights):
            self.logger.warning(
                f"⚠️ レジーム {regime.value} の重み合計が1.0ではありません: "
                f"{sum(weights.values()):.3f} - デフォルト重みを使用"
            )
            weights = default_weights

        # Phase 51.8-J4-G: バックテストモードで可視化するためWARNINGレベルに変更
        self.logger.warning(
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
        Phase 51.7 Day 7: レジーム別デフォルト重み取得（設定駆動型・6戦略対応）

        strategies.yamlから戦略を動的読み込みし、regime_affinityに基づいて
        レジーム別の重み付けを自動計算。戦略追加時の修正箇所を削減。

        重要: StrategyManager.update_strategy_weights()は部分的な更新のみを行うため、
              レジームに含まれない戦略を明示的に0.0にする必要がある。

        Args:
            regime: 市場レジーム

        Returns:
            Dict[str, float]: デフォルト戦略重み（全戦略・動的・合計1.0）
        """
        from ...strategies.strategy_loader import StrategyLoader

        # 全戦略を動的取得
        loader = StrategyLoader()
        strategies_data = loader.load_strategies()

        # 全戦略を0.0で初期化
        weights = {s["metadata"]["name"]: 0.0 for s in strategies_data}

        # レジーム別重み付けロジック
        if regime == RegimeType.TIGHT_RANGE:
            # レンジ型戦略のみ（70:30比率）
            range_strategies = [s for s in strategies_data if s.get("regime_affinity") == "range"]
            if len(range_strategies) >= 2:
                # 優先度順でトップ2に重み配分
                sorted_strategies = sorted(range_strategies, key=lambda x: x.get("priority", 999))
                weights[sorted_strategies[0]["metadata"]["name"]] = 0.70
                weights[sorted_strategies[1]["metadata"]["name"]] = 0.30
            elif len(range_strategies) == 1:
                weights[range_strategies[0]["metadata"]["name"]] = 1.0

        elif regime == RegimeType.NORMAL_RANGE:
            # レンジ型80% + トレンド型20%
            range_strategies = [s for s in strategies_data if s.get("regime_affinity") == "range"]
            trend_strategies = [s for s in strategies_data if s.get("regime_affinity") == "trend"]
            if range_strategies:
                sorted_range = sorted(range_strategies, key=lambda x: x.get("priority", 999))
                weights[sorted_range[0]["metadata"]["name"]] = 0.50
                if len(sorted_range) >= 2:
                    weights[sorted_range[1]["metadata"]["name"]] = 0.30
            if trend_strategies:
                weights[trend_strategies[0]["metadata"]["name"]] = 0.20

        elif regime == RegimeType.TRENDING:
            # トレンド型60% + レンジ型40%
            trend_strategies = [s for s in strategies_data if s.get("regime_affinity") == "trend"]
            range_strategies = [s for s in strategies_data if s.get("regime_affinity") == "range"]
            if trend_strategies:
                weights[trend_strategies[0]["metadata"]["name"]] = 0.60
            if range_strategies:
                sorted_range = sorted(range_strategies, key=lambda x: x.get("priority", 999))
                weights[sorted_range[0]["metadata"]["name"]] = 0.30
                if len(sorted_range) >= 2:
                    weights[sorted_range[1]["metadata"]["name"]] = 0.10

        elif regime == RegimeType.HIGH_VOLATILITY:
            # 高ボラティリティは全戦略0.0（全戦略無効化）
            pass  # 既に0.0で初期化済み

        else:
            # 未知のレジーム: 均等重み
            self.logger.warning(f"⚠️ 未知のレジーム: {regime.value} - 均等重みを使用")
            num_strategies = len(weights)
            if num_strategies > 0:
                equal_weight = 1.0 / num_strategies
                for strategy_name in weights.keys():
                    weights[strategy_name] = equal_weight

        return weights

    def is_enabled(self) -> bool:
        """
        動的戦略選択機能が有効かどうかを確認

        Returns:
            bool: 有効な場合True
        """
        enabled = get_threshold("dynamic_strategy_selection.enabled", True)
        return enabled

    def get_regime_position_limit(self, regime: RegimeType) -> int:
        """
        Phase 51.8: レジーム別最大ポジション数を取得

        市場レジームに応じた最大同時保有ポジション数を取得する。
        動的戦略選択が無効の場合はグローバル設定値を使用。

        Args:
            regime: 市場レジーム

        Returns:
            int: 最大ポジション数
                - tight_range: 5件（レンジ相場は分散投資重視）
                - normal_range: 4件（バランス型）
                - trending: 3件（トレンド相場は中程度の集中）
                - high_volatility: 0件（完全待機）

        Example:
            >>> selector = DynamicStrategySelector()
            >>> selector.get_regime_position_limit(RegimeType.TIGHT_RANGE)
            5
            >>> selector.get_regime_position_limit(RegimeType.HIGH_VOLATILITY)
            0
        """
        # 動的戦略選択が無効の場合はグローバル設定使用
        if not self.is_enabled():
            fallback = get_threshold("position_management.max_open_positions", 2)  # デフォルト2件
            self.logger.debug(f"📊 Phase 51.8: 動的戦略選択無効 - グローバル設定使用: {fallback}件")
            return fallback

        # thresholds.yaml から取得
        config_key = f"position_limits.{regime.value}.max_positions"

        # デフォルト値: レジーム別制限
        default_limits = {
            RegimeType.TIGHT_RANGE: 5,
            RegimeType.NORMAL_RANGE: 4,
            RegimeType.TRENDING: 3,
            RegimeType.HIGH_VOLATILITY: 0,
        }

        # フォールバック: 設定ファイル不足時
        fallback_limit = get_threshold("position_limits.fallback_max_positions", 2)

        limit = get_threshold(config_key, default_limits.get(regime, fallback_limit))

        # Phase 51.8-J4-G: バックテストモードで可視化するためWARNINGレベルに変更
        self.logger.warning(
            f"📊 Phase 51.8: レジーム別ポジション制限 - " f"regime={regime.value}, 上限={limit}件"
        )

        return limit
