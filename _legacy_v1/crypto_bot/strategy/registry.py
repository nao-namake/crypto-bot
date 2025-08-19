"""
戦略レジストリシステム

戦略の動的発見、登録、管理を行うレジストリクラス。
新しい戦略クラスを追加する際の中央管理ポイントとして機能します。
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Type

from .base import StrategyBase

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """戦略クラスの登録と管理を行うレジストリ"""

    _instance = None
    _strategies: Dict[str, Type[StrategyBase]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._auto_discover_strategies()

    def register(self, name: str, strategy_class: Type[StrategyBase]) -> None:
        """
        戦略クラスを手動で登録

        Args:
            name: 戦略名（一意識別子）
            strategy_class: StrategyBaseを継承した戦略クラス
        """
        if not issubclass(strategy_class, StrategyBase):
            raise ValueError(
                f"Strategy class {strategy_class} must inherit from StrategyBase"
            )

        self._strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name} -> {strategy_class.__name__}")

    def get_strategy(self, name: str) -> Type[StrategyBase]:
        """
        登録された戦略クラスを取得

        Args:
            name: 戦略名

        Returns:
            戦略クラス

        Raises:
            KeyError: 指定された戦略が見つからない場合
        """
        if name not in self._strategies:
            raise KeyError(
                f"Strategy '{name}' not found. Available strategies: "
                f"{list(self._strategies.keys())}"
            )

        return self._strategies[name]

    def list_strategies(self) -> List[str]:
        """登録されている戦略名のリストを取得"""
        return list(self._strategies.keys())

    def _auto_discover_strategies(self) -> None:
        """crypto_bot.strategy パッケージ内の戦略クラスを自動発見"""
        try:
            # 現在のパッケージディレクトリを取得
            strategy_dir = Path(__file__).parent

            # .pyファイルを走査
            for py_file in strategy_dir.glob("*.py"):
                if py_file.name.startswith("_") or py_file.name in [
                    "base.py",
                    "registry.py",
                ]:
                    continue

                module_name = f"crypto_bot.strategy.{py_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    self._discover_strategies_in_module(module)
                except Exception as e:
                    logger.warning(
                        f"Failed to import strategy module {module_name}: {e}"
                    )

        except Exception as e:
            logger.error(f"Failed to auto-discover strategies: {e}")

    def _discover_strategies_in_module(self, module) -> None:
        """モジュール内のStrategyBaseサブクラスを発見して登録"""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                obj != StrategyBase
                and issubclass(obj, StrategyBase)
                and obj.__module__ == module.__name__
            ):

                # クラス名から戦略名を生成（例: MLStrategy -> ml_strategy）
                strategy_name = self._class_name_to_strategy_name(name)
                self.register(strategy_name, obj)

    def _class_name_to_strategy_name(self, class_name: str) -> str:
        """
        クラス名を戦略名に変換
        例: MLStrategy -> ml_strategy, BollingerBandsStrategy -> bollinger_bands_strategy
        """
        # CamelCaseをsnake_caseに変換
        import re

        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", class_name)
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

        # "Strategy"サフィックスを削除
        if name.endswith("_strategy"):
            name = name[:-9]

        return name

    def load_external_strategy(self, file_path: str, strategy_name: str = None) -> None:
        """
        外部ファイルから戦略クラスを動的に読み込み

        Args:
            file_path: 戦略クラスが定義されたPythonファイルのパス
            strategy_name: 戦略名（指定されない場合は自動生成）
        """
        try:
            spec = importlib.util.spec_from_file_location(
                "external_strategy", file_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # モジュール内の戦略クラスを発見
            strategies_found = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj != StrategyBase and issubclass(obj, StrategyBase):
                    if strategy_name:
                        self.register(strategy_name, obj)
                    else:
                        auto_name = self._class_name_to_strategy_name(name)
                        self.register(auto_name, obj)
                    strategies_found.append(name)

            if not strategies_found:
                logger.warning(f"No strategy classes found in {file_path}")
            else:
                logger.info(
                    f"Loaded external strategies from {file_path}: {strategies_found}"
                )

        except Exception as e:
            logger.error(f"Failed to load external strategy from {file_path}: {e}")
            raise


# シングルトンインスタンス
strategy_registry = StrategyRegistry()
