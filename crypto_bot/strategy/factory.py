"""
戦略ファクトリー

設定から戦略インスタンスを生成するファクトリークラス。
複数戦略の組み合わせやパラメータ設定を統一的に管理します。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .base import StrategyBase

logger = logging.getLogger(__name__)


class StrategyFactory:
    """戦略インスタンスの生成を管理するファクトリー"""

    @staticmethod
    def create_strategy(
        config: Dict[str, Any], full_config: Dict[str, Any] = None
    ) -> StrategyBase:
        """
        設定から単一の戦略インスタンスを生成

        Args:
            config: 戦略設定辞書
                必須キー:
                - name: 戦略名
                オプションキー:
                - params: 戦略固有のパラメータ

        Returns:
            戦略インスタンス

        Example:
            config = {
                "name": "ml_strategy",
                "params": {
                    "model_path": "model/calibrated_model.pkl",
                    "threshold": 0.1
                }
            }
        """
        strategy_name = config.get("name")
        if not strategy_name:
            raise ValueError("Strategy name is required in config")

        from .registry import strategy_registry

        strategy_class = strategy_registry.get_strategy(strategy_name)
        params = config.get("params", {})

        logger.info(f"Creating strategy: {strategy_name} with params: {params}")

        try:
            # 戦略クラスのコンストラクタシグネチャを調べて適切にパラメータを渡す
            import inspect

            sig = inspect.signature(strategy_class.__init__)

            # configを全体として渡すパラメータがあるかチェック
            init_params = {}
            if "config" in sig.parameters:
                # MLStrategyなど、全体設定が必要な戦略の場合はfull_configを使用
                if strategy_name in ["ml", "ml_strategy"] and full_config is not None:
                    init_params["config"] = full_config
                else:
                    init_params["config"] = params

            # 個別パラメータを展開
            for param_name, param_value in params.items():
                if param_name in sig.parameters:
                    init_params[param_name] = param_value

            return strategy_class(**init_params)

        except Exception as e:
            logger.error(f"Failed to create strategy {strategy_name}: {e}")
            raise

    @staticmethod
    def create_multi_strategy(
        configs: List[Dict[str, Any]], combination_mode: str = "weighted_average"
    ) -> StrategyBase:
        """
        複数の戦略を組み合わせたコンポジット戦略を生成

        Args:
            configs: 戦略設定のリスト
            combination_mode: 組み合わせ方法
                - weighted_average: 重み付き平均
                - majority_vote: 多数決
                - unanimous: 全戦略一致

        Returns:
            コンポジット戦略インスタンス
        """
        strategies = []
        for config in configs:
            strategy = StrategyFactory.create_strategy(config)
            weight = config.get("weight", 1.0)
            strategies.append((strategy, weight))

        from .composite import CompositeStrategy

        return CompositeStrategy(strategies, combination_mode)

    @staticmethod
    def list_available_strategies() -> List[str]:
        """利用可能な戦略名のリストを取得"""
        from .registry import strategy_registry

        return strategy_registry.list_strategies()

    @staticmethod
    def get_strategy_info(strategy_name: str) -> Dict[str, Any]:
        """
        戦略の詳細情報を取得

        Args:
            strategy_name: 戦略名

        Returns:
            戦略情報辞書
        """
        from .registry import strategy_registry

        strategy_class = strategy_registry.get_strategy(strategy_name)

        import inspect

        sig = inspect.signature(strategy_class.__init__)
        params = []
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            params.append(
                {
                    "name": param_name,
                    "default": (
                        param.default
                        if param.default != inspect.Parameter.empty
                        else None
                    ),
                    "annotation": (
                        param.annotation
                        if param.annotation != inspect.Parameter.empty
                        else None
                    ),
                }
            )

        return {
            "name": strategy_name,
            "class_name": strategy_class.__name__,
            "module": strategy_class.__module__,
            "docstring": strategy_class.__doc__,
            "parameters": params,
        }

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """
        戦略設定の検証

        Args:
            config: 戦略設定辞書

        Returns:
            エラーメッセージのリスト（空の場合は検証成功）
        """
        errors = []

        if not config.get("name"):
            errors.append("Strategy name is required")
            return errors

        strategy_name = config["name"]

        try:
            from .registry import strategy_registry

            strategy_class = strategy_registry.get_strategy(strategy_name)
        except KeyError:
            errors.append(f"Unknown strategy: {strategy_name}")
            return errors

        # パラメータの検証
        params = config.get("params", {})
        import inspect

        sig = inspect.signature(strategy_class.__init__)

        # 必須パラメータのチェック
        for param_name, param in sig.parameters.items():
            if (
                param_name != "self"
                and param.default == inspect.Parameter.empty
                and param_name not in params
                and param_name != "config"
            ):
                errors.append(
                    f"Required parameter '{param_name}' is missing for "
                    f"strategy '{strategy_name}'"
                )

        return errors
