"""
特徴量管理システム - Phase 19

特徴量定義の一元化により、ハードコーディング排除と保守性向上を実現。
config/core/feature_order.jsonを真の情報源として全システムが統一的に参照。

Phase 19完了: 2025年9月4日
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from ..exceptions import DataProcessingError
from ..logger import get_logger


class FeatureManager:
    """
    特徴量管理システム

    特徴量定義をconfig/core/feature_order.jsonから一元的に管理し、
    システム全体の特徴量設定を統一。
    """

    def __init__(self):
        self.logger = get_logger()
        self._feature_config: Optional[Dict] = None
        self._feature_order_path = Path("config/core/feature_order.json")

    def _load_feature_config(self) -> Dict:
        """特徴量設定をキャッシュ付きで読み込み"""
        # 手動キャッシュ
        if self._feature_config is not None:
            return self._feature_config

        try:
            if not self._feature_order_path.exists():
                self.logger.warning(f"特徴量設定ファイル未発見: {self._feature_order_path}")
                config = self._get_default_feature_config()
            else:
                with open(self._feature_order_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.logger.debug(f"✅ 特徴量設定読み込み: {config.get('total_features', 0)}特徴量")

            self._feature_config = config  # キャッシュに保存
            return config

        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            self.logger.error(f"特徴量設定読み込みエラー: {e}")
            config = self._get_default_feature_config()
            self._feature_config = config
            return config

    def _get_default_feature_config(self) -> Dict:
        """デフォルト特徴量設定（フォールバック）"""
        return {
            "total_features": 12,
            "feature_categories": {
                "basic": {"features": ["close", "volume", "returns_1"]},
                "momentum": {"features": ["rsi_14", "macd", "macd_signal"]},
                "volatility": {"features": ["atr_14", "bb_position"]},
                "trend": {"features": ["ema_20", "ema_50"]},
                "volume": {"features": ["volume_ratio"]},
                "anomaly": {"features": ["zscore"]},
            },
        }

    def get_feature_names(self) -> List[str]:
        """
        特徴量名リストを取得

        Returns:
            特徴量名のリスト（順序保証）
        """
        config = self._load_feature_config()

        if "feature_categories" in config:
            # カテゴリから特徴量を抽出
            features = []
            categories = config["feature_categories"]

            # 順序保証のためのカテゴリ順序
            category_order = [
                "basic",
                "momentum",
                "volatility",
                "trend",
                "volume",
                "anomaly",
            ]

            for category in category_order:
                if category in categories and "features" in categories[category]:
                    features.extend(categories[category]["features"])

            return features

        # フォールバック
        return [
            "close",
            "volume",
            "returns_1",
            "rsi_14",
            "macd",
            "macd_signal",
            "atr_14",
            "bb_position",
            "ema_20",
            "ema_50",
            "volume_ratio",
            "zscore",
        ]

    def get_feature_count(self) -> int:
        """
        特徴量数を取得

        Returns:
            特徴量の総数
        """
        config = self._load_feature_config()

        if "total_features" in config:
            return int(config["total_features"])

        # 実際の特徴量数をカウント
        return len(self.get_feature_names())

    def get_feature_categories(self) -> Dict[str, List[str]]:
        """
        特徴量カテゴリを取得

        Returns:
            カテゴリ名をキーとした特徴量リスト辞書
        """
        config = self._load_feature_config()

        if "feature_categories" in config:
            categories = {}
            for category, data in config["feature_categories"].items():
                if "features" in data:
                    categories[category] = data["features"]
            return categories

        # デフォルトカテゴリ
        return {
            "basic": ["close", "volume", "returns_1"],
            "momentum": ["rsi_14", "macd", "macd_signal"],
            "volatility": ["atr_14", "bb_position"],
            "trend": ["ema_20", "ema_50"],
            "volume": ["volume_ratio"],
            "anomaly": ["zscore"],
        }

    def validate_features(self, features: List[str]) -> bool:
        """
        特徴量の妥当性をチェック

        Args:
            features: チェック対象の特徴量リスト

        Returns:
            妥当性チェック結果
        """
        expected_features = set(self.get_feature_names())
        provided_features = set(features)

        # 不足特徴量
        missing = expected_features - provided_features
        # 余分な特徴量
        extra = provided_features - expected_features

        if missing:
            self.logger.error(f"不足特徴量: {sorted(missing)}")
            return False

        if extra:
            self.logger.warning(f"余分な特徴量（無視されます）: {sorted(extra)}")

        if len(features) != self.get_feature_count():
            self.logger.error(
                f"特徴量数不一致: 期待={self.get_feature_count()}, 実際={len(features)}"
            )
            return False

        return True

    def get_feature_info(self) -> Dict:
        """特徴量設定の詳細情報を取得"""
        config = self._load_feature_config()

        return {
            "total_features": self.get_feature_count(),
            "feature_names": self.get_feature_names(),
            "feature_categories": self.get_feature_categories(),
            "config_source": str(self._feature_order_path),
            "config_exists": self._feature_order_path.exists(),
            "version": config.get("feature_order_version", "unknown"),
        }

    def clear_cache(self):
        """キャッシュをクリア"""
        self._feature_config = None
        self.logger.debug("特徴量設定キャッシュをクリア")


# グローバルインスタンス
_feature_manager = FeatureManager()


# 便利関数（後方互換性とシンプルなアクセスのため）
def get_feature_names() -> List[str]:
    """特徴量名リストを取得"""
    return _feature_manager.get_feature_names()


def get_feature_count() -> int:
    """特徴量数を取得"""
    return _feature_manager.get_feature_count()


def get_feature_categories() -> Dict[str, List[str]]:
    """特徴量カテゴリを取得"""
    return _feature_manager.get_feature_categories()


def validate_features(features: List[str]) -> bool:
    """特徴量の妥当性をチェック"""
    return _feature_manager.validate_features(features)


def get_feature_info() -> Dict:
    """特徴量設定の詳細情報を取得"""
    return _feature_manager.get_feature_info()


def reload_feature_config():
    """特徴量設定を再読み込み"""
    _feature_manager.clear_cache()
    return _feature_manager._load_feature_config()
