"""
Feature Order Manager - Phase 2.2最適化版
97特徴量システム統一管理・順序整合性保証・バッチ処理効率最大化

Key Features:
- FEATURE_ORDER_97統一定義活用
- production.yml完全準拠
- 特徴量mismatch根絶
- バッチ処理効率最適化
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class FeatureOrderManager:
    """
    Phase 2.2最適化版特徴量順序管理

    統一特徴量順序保証・mismatch根絶・効率最大化
    """

    def __init__(self):
        self.feature_order_97: Optional[List[str]] = None
        self.categories: Optional[Dict[str, List[str]]] = None
        self.batch_opportunities: Optional[Dict[str, List[str]]] = None

        # 統一定義読み込み
        self._load_unified_definition()

        logger.info("🔧 FeatureOrderManager Phase 2.2最適化版初期化完了")

    def _load_unified_definition(self):
        """FEATURE_ORDER_97統一定義読み込み"""
        definition_path = Path(__file__).parent / "feature_order_97_unified.json"

        try:
            with open(definition_path, "r", encoding="utf-8") as f:
                definition = json.load(f)

            self.feature_order_97 = definition["FEATURE_ORDER_97"]
            self.categories = definition["categories"]
            self.batch_opportunities = definition["batch_opportunities"]

            logger.info(
                f"✅ FEATURE_ORDER_97統一定義読み込み完了: {len(self.feature_order_97)}特徴量"
            )

        except Exception as e:
            logger.error(f"❌ 統一定義読み込み失敗: {e}")
            # フォールバック: 基本定義
            self._create_fallback_definition()

    def _create_fallback_definition(self):
        """フォールバック定義生成（production.yml読み込み失敗時）"""
        logger.warning("⚠️ フォールバック定義生成中...")

        # 基本的な97特徴量定義
        base_features = ["open", "high", "low", "close", "volume"]

        # 主要特徴量（production.yml準拠の最小セット）
        essential_extra = [
            "close_lag_1",
            "close_lag_3",
            "volume_lag_1",
            "returns_1",
            "returns_2",
            "returns_3",
            "returns_5",
            "returns_10",
            "ema_5",
            "ema_10",
            "ema_20",
            "ema_50",
            "ema_100",
            "ema_200",
            "rsi_14",
            "rsi_oversold",
            "rsi_overbought",
            "atr_14",
            "volatility_20",
            "hour",
            "day_of_week",
            "is_weekend",
            "is_asian_session",
            "is_us_session",
        ]

        self.feature_order_97 = base_features + essential_extra

        # 残り特徴量数計算
        remaining_needed = 97 - len(self.feature_order_97)
        logger.warning(
            f"⚠️ フォールバック定義: {len(self.feature_order_97)}特徴量, 不足{remaining_needed}個"
        )

    def get_feature_order_97(self) -> List[str]:
        """FEATURE_ORDER_97取得"""
        if self.feature_order_97 is None:
            self._load_unified_definition()

        return self.feature_order_97 or []

    def validate_feature_order(self, features: List[str]) -> Tuple[bool, List[str]]:
        """特徴量順序検証・mismatch検出"""
        expected_order = self.get_feature_order_97()

        if len(features) != len(expected_order):
            return False, [f"Length mismatch: {len(features)} vs {len(expected_order)}"]

        mismatches = []
        for i, (actual, expected) in enumerate(zip(features, expected_order)):
            if actual != expected:
                mismatches.append(f"[{i}] {actual} != {expected}")

        return len(mismatches) == 0, mismatches

    def ensure_feature_order(
        self, df, required_features: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """特徴量順序強制統一"""

        target_order = required_features or self.get_feature_order_97()

        # 不足特徴量を0で補完
        for feature in target_order:
            if feature not in df.columns:
                df[feature] = 0.0
                logger.warning(f"⚠️ Missing feature filled with 0: {feature}")

        # 順序統一
        ordered_df = df[target_order].copy()

        logger.debug(f"✅ Feature order enforced: {len(ordered_df.columns)} features")
        return ordered_df

    def get_batch_groups(self) -> Dict[str, List[str]]:
        """バッチ処理グループ取得"""
        return self.batch_opportunities or {}

    def get_feature_categories(self) -> Dict[str, List[str]]:
        """特徴量カテゴリ取得"""
        return self.categories or {}


# グローバルインスタンス
_feature_order_manager = None


def get_feature_order_manager() -> FeatureOrderManager:
    """FeatureOrderManagerシングルトンアクセス"""
    global _feature_order_manager
    if _feature_order_manager is None:
        _feature_order_manager = FeatureOrderManager()
    return _feature_order_manager


def get_feature_order_97() -> List[str]:
    """FEATURE_ORDER_97クイックアクセス"""
    return get_feature_order_manager().get_feature_order_97()
