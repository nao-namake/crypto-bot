"""
戦略動的ローダー - Phase 51.5-B実装

Facade Patternによる戦略動的ロードシステム。
strategies.yamlから戦略を読み込み、動的にインスタンス化。

主要機能:
- strategies.yaml読み込み
- 戦略動的インスタンス化
- thresholds.yaml連携
- 優先度順ソート

Phase 51.5-B: 動的戦略管理基盤実装
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..core.config.threshold_manager import get_all_thresholds
from ..core.exceptions import StrategyError
from ..core.logger import get_logger
from .base.strategy_base import StrategyBase
from .strategy_registry import StrategyRegistry


class StrategyLoader:
    """
    戦略動的ローダー（Facade Pattern）

    strategies.yamlから戦略定義を読み込み、動的にインスタンス化。
    Registry Patternと連携して、設定ファイル主導の戦略管理を実現。

    使用例:
        loader = StrategyLoader("config/strategies.yaml")
        strategies = loader.load_strategies()

        for strategy_data in strategies:
            instance = strategy_data['instance']
            weight = strategy_data['weight']
            # ... 戦略使用

    Phase 51.5-B完了
    """

    def __init__(self, config_path: str = "config/strategies.yaml"):
        """
        戦略ローダー初期化

        Args:
            config_path: strategies.yamlのパス
        """
        self.config_path = Path(config_path)
        self.logger = get_logger()
        self.config: Optional[Dict[str, Any]] = None

    def load_strategies(self) -> List[Dict[str, Any]]:
        """
        strategies.yamlから戦略を動的ロード

        Returns:
            戦略データのリスト（instance, weight, priority, metadataを含む）

        Raises:
            StrategyError: 設定ファイル読み込みエラー、戦略ロードエラー
        """
        # 設定ファイル読み込み
        self.config = self._load_config()

        # 戦略リスト
        strategies = []

        # 各戦略をロード
        for strategy_id, strategy_config in self.config["strategies"].items():
            # 無効な戦略はスキップ
            if not strategy_config.get("enabled", False):
                self.logger.info(f"⏸️ Phase 51.5-B: 戦略スキップ（無効） - id={strategy_id}")
                continue

            try:
                # 戦略ロード
                strategy_data = self._load_strategy(strategy_id, strategy_config)
                strategies.append(strategy_data)

                self.logger.info(
                    f"✅ Phase 51.5-B: 戦略ロード完了 - "
                    f"id={strategy_id}, "
                    f"name={strategy_data['metadata']['name']}, "
                    f"weight={strategy_data['weight']}, "
                    f"priority={strategy_data['priority']}"
                )

            except Exception as e:
                self.logger.error(f"❌ Phase 51.5-B: 戦略ロード失敗 - id={strategy_id}, error={e}")
                raise StrategyError(f"戦略'{strategy_id}'のロードに失敗しました: {e}") from e

        # 優先度順にソート
        strategies.sort(key=lambda x: x["priority"])

        self.logger.info(
            f"✅ Phase 51.5-B: {len(strategies)}戦略をロードしました - "
            f"ids={[s['metadata']['strategy_id'] for s in strategies]}"
        )

        return strategies

    def _load_config(self) -> Dict[str, Any]:
        """
        strategies.yaml読み込み

        Returns:
            設定辞書

        Raises:
            StrategyError: ファイル読み込みエラー
        """
        if not self.config_path.exists():
            raise StrategyError(f"strategies.yaml が見つかりません: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            # 必須フィールド確認
            if "strategies" not in config:
                raise StrategyError("strategies.yaml に 'strategies' セクションがありません")

            self.logger.info(
                f"✅ Phase 51.5-B: strategies.yaml読み込み完了 - "
                f"path={self.config_path}, "
                f"version={config.get('strategy_system_version', 'unknown')}, "
                f"total_strategies={len(config['strategies'])}"
            )

            return config

        except yaml.YAMLError as e:
            raise StrategyError(f"strategies.yaml のYAML解析エラー: {e}") from e
        except Exception as e:
            raise StrategyError(f"strategies.yaml 読み込みエラー: {e}") from e

    def _load_strategy(self, strategy_id: str, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一戦略のロード

        Args:
            strategy_id: 戦略ID（strategies.yamlのキー）
            strategy_config: 戦略設定

        Returns:
            戦略データ（instance, weight, priority, metadata）

        Raises:
            StrategyError: 戦略ロードエラー
        """
        # 必須フィールド確認
        required_fields = ["class_name", "strategy_type"]
        for field in required_fields:
            if field not in strategy_config:
                raise StrategyError(f"戦略'{strategy_id}'の設定に '{field}' がありません")

        # Registry から戦略クラス取得
        class_name = strategy_config["class_name"]
        try:
            strategy_class = StrategyRegistry.get_strategy(class_name)
        except StrategyError as e:
            raise StrategyError(
                f"戦略'{strategy_id}'のクラス'{class_name}'が"
                f"Registryに登録されていません。"
                f"戦略クラスに@StrategyRegistry.register()が"
                f"適用されているか確認してください。"
            ) from e

        # thresholds.yamlから戦略設定を取得
        strategy_thresholds_config = self._get_strategy_thresholds(strategy_id)

        # 戦略インスタンス化
        try:
            strategy_instance = strategy_class(config=strategy_thresholds_config)
        except Exception as e:
            raise StrategyError(f"戦略'{strategy_id}'のインスタンス化に失敗しました: {e}") from e

        # 戦略データ作成
        return {
            "instance": strategy_instance,
            "weight": strategy_config.get("weight", 1.0),
            "priority": strategy_config.get("priority", 99),
            "metadata": {
                "strategy_id": strategy_id,
                "name": class_name,
                "strategy_type": strategy_config["strategy_type"],
                "description": strategy_config.get("description", ""),
                "module_path": strategy_config.get("module_path", ""),
                "config_section": strategy_config.get("config_section", ""),
            },
        }

    def _get_strategy_thresholds(self, strategy_id: str) -> Dict[str, Any]:
        """
        thresholds.yamlから戦略設定を取得

        Args:
            strategy_id: 戦略ID（strategies.yamlのキー）

        Returns:
            戦略設定辞書（thresholds.yaml の strategies.{strategy_id} セクション）
        """
        try:
            all_thresholds = get_all_thresholds()
            strategies_section = all_thresholds.get("strategies", {})

            # 戦略IDに対応する設定を取得
            strategy_config = strategies_section.get(strategy_id, {})

            if not strategy_config:
                self.logger.warning(
                    f"⚠️ Phase 51.5-B: thresholds.yamlに戦略設定がありません - "
                    f"strategy_id={strategy_id}, デフォルト設定を使用"
                )

            return strategy_config

        except Exception as e:
            self.logger.warning(
                f"⚠️ Phase 51.5-B: thresholds.yaml読み込みエラー - "
                f"strategy_id={strategy_id}, error={e}, デフォルト設定を使用"
            )
            return {}

    def get_enabled_strategy_ids(self) -> List[str]:
        """
        有効な戦略IDのリスト取得

        Returns:
            有効な戦略IDのリスト

        Raises:
            StrategyError: 設定が読み込まれていない場合
        """
        if self.config is None:
            self.config = self._load_config()

        enabled_ids = [
            strategy_id
            for strategy_id, strategy_config in self.config["strategies"].items()
            if strategy_config.get("enabled", False)
        ]

        return enabled_ids

    def get_strategy_config(self, strategy_id: str) -> Dict[str, Any]:
        """
        特定戦略の設定取得

        Args:
            strategy_id: 戦略ID

        Returns:
            戦略設定辞書

        Raises:
            StrategyError: 設定が読み込まれていない、または戦略が存在しない場合
        """
        if self.config is None:
            self.config = self._load_config()

        if strategy_id not in self.config["strategies"]:
            available = ", ".join(self.config["strategies"].keys())
            raise StrategyError(
                f"戦略'{strategy_id}'が見つかりません。" f"利用可能な戦略ID: {available}"
            )

        return self.config["strategies"][strategy_id].copy()
