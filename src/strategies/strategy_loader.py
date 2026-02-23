"""
戦略動的ローダー - Phase 65.11

Facade Patternによる戦略動的ロードシステム。
thresholds.yamlから戦略定義+パラメータを読み込み、動的にインスタンス化。

主要機能:
- thresholds.yaml読み込み（get_all_thresholds経由）
- 戦略動的インスタンス化
- 優先度順ソート

Phase 65.11: strategies.yaml廃止・thresholds.yaml統合
"""

from typing import Any, Dict, List, Optional

from ..core.config.threshold_manager import get_all_thresholds
from ..core.exceptions import StrategyError
from ..core.logger import get_logger
from .base.strategy_base import StrategyBase
from .strategy_registry import StrategyRegistry


class StrategyLoader:
    """
    戦略動的ローダー（Facade Pattern）

    thresholds.yamlから戦略定義+パラメータを読み込み、動的にインスタンス化。
    Registry Patternと連携して、設定ファイル主導の戦略管理を実現。

    使用例:
        loader = StrategyLoader()
        strategies = loader.load_strategies()

        for strategy_data in strategies:
            instance = strategy_data['instance']
            weight = strategy_data['weight']
            # ... 戦略使用

    Phase 65.11: thresholds.yaml統合
    """

    def __init__(self):
        """戦略ローダー初期化"""
        self.logger = get_logger()
        self.config: Optional[Dict[str, Any]] = None

    def load_strategies(self) -> List[Dict[str, Any]]:
        """
        thresholds.yamlから戦略を動的ロード

        Returns:
            戦略データのリスト（instance, weight, priority, metadataを含む）

        Raises:
            StrategyError: 設定読み込みエラー、戦略ロードエラー
        """
        # 設定読み込み
        self.config = self._load_config()

        # 戦略リスト
        strategies = []

        # 各戦略をロード
        for strategy_id, strategy_config in self.config["strategies"].items():
            # 無効な戦略はスキップ
            if not strategy_config.get("enabled", False):
                self.logger.info(f"⏸️ 戦略スキップ（無効） - id={strategy_id}")
                continue

            try:
                # 戦略ロード
                strategy_data = self._load_strategy(strategy_id, strategy_config)
                strategies.append(strategy_data)

                self.logger.info(
                    f"✅ 戦略ロード完了 - "
                    f"id={strategy_id}, "
                    f"name={strategy_data['metadata']['name']}, "
                    f"weight={strategy_data['weight']}, "
                    f"priority={strategy_data['priority']}"
                )

            except Exception as e:
                self.logger.error(f"❌ 戦略ロード失敗 - id={strategy_id}, error={e}")
                raise StrategyError(f"戦略'{strategy_id}'のロードに失敗しました: {e}") from e

        # 優先度順にソート
        strategies.sort(key=lambda x: x["priority"])

        self.logger.info(
            f"✅ {len(strategies)}戦略をロードしました - "
            f"ids={[s['metadata']['strategy_id'] for s in strategies]}"
        )

        return strategies

    def _load_config(self) -> Dict[str, Any]:
        """
        thresholds.yaml読み込み（get_all_thresholds経由）

        Returns:
            設定辞書

        Raises:
            StrategyError: 読み込みエラー
        """
        try:
            config = get_all_thresholds()

            if not config:
                raise StrategyError("thresholds.yaml の読み込み結果が空です")

            # 必須フィールド確認
            if "strategies" not in config:
                raise StrategyError("thresholds.yaml に 'strategies' セクションがありません")

            self.logger.info(
                f"✅ thresholds.yaml戦略設定読み込み完了 - "
                f"version={config.get('strategy_system_version', 'unknown')}, "
                f"total_strategies={len(config['strategies'])}"
            )

            return config

        except StrategyError:
            raise
        except Exception as e:
            raise StrategyError(f"thresholds.yaml 読み込みエラー: {e}") from e

    def _load_strategy(self, strategy_id: str, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一戦略のロード

        Args:
            strategy_id: 戦略ID（thresholds.yamlのキー）
            strategy_config: 戦略設定（定義+パラメータ統合済み）

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

        class_name = strategy_config["class_name"]

        # 戦略クラスが未登録の場合のみモジュールをimport
        if not StrategyRegistry.is_registered(class_name):
            # module_pathが必須（本番環境）
            if "module_path" not in strategy_config:
                raise StrategyError(
                    f"戦略'{strategy_id}'のクラス'{class_name}'がRegistryに未登録で、"
                    f"'module_path'が設定されていません。thresholds.yamlに'module_path'を追加してください。"
                )

            module_path = strategy_config["module_path"]
            try:
                import importlib

                importlib.import_module(module_path)
                self.logger.info(f"✅ 戦略モジュールimport成功 - module={module_path}")
            except ImportError as e:
                raise StrategyError(
                    f"戦略'{strategy_id}'のモジュール'{module_path}'のimportに失敗しました: {e}"
                ) from e
        else:
            self.logger.debug(f"ℹ️ 戦略'{class_name}'は既に登録済み - importスキップ")

        # Registry から戦略クラス取得
        try:
            strategy_class = StrategyRegistry.get_strategy(class_name)
        except StrategyError as e:
            raise StrategyError(
                f"戦略'{strategy_id}'のクラス'{class_name}'が"
                f"Registryに登録されていません。"
                f"戦略クラスに@StrategyRegistry.register()が"
                f"適用されているか確認してください。"
            ) from e

        # 戦略インスタンス化（strategy_configをそのまま渡す）
        try:
            strategy_instance = strategy_class(config=strategy_config)
        except Exception as e:
            raise StrategyError(f"戦略'{strategy_id}'のインスタンス化に失敗しました: {e}") from e

        # 戦略データ作成
        return {
            "instance": strategy_instance,
            "weight": strategy_config.get("weight", 1.0),
            "priority": strategy_config.get("priority", 99),
            "regime_affinity": strategy_config.get("regime_affinity", "both"),
            "metadata": {
                "strategy_id": strategy_id,
                "name": class_name,
                "strategy_type": strategy_config["strategy_type"],
                "module_path": strategy_config.get("module_path", ""),
            },
        }

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
