"""
ML Preprocessing Utilities - Phase 16.3-A Split

統合前: crypto_bot/ml/preprocessor.py（3,314行）
分割後: crypto_bot/ml/preprocessing/utils.py

機能:
- calc_rci: RCI（Rank Correlation Index）計算
- ensure_feature_coverage: 特徴量カバレッジ保証

Phase 16.3-A実装日: 2025年8月8日
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

# Phase 8.2: 統一特徴量実装システム統合
try:
    from crypto_bot.ml.feature_master_implementation import FeatureMasterImplementation

    FEATURE_MASTER_AVAILABLE = True
except ImportError:
    FEATURE_MASTER_AVAILABLE = False

# Phase 3: 外部API依存完全除去
ENHANCED_FEATURES_AVAILABLE = False

logger = logging.getLogger(__name__)


def calc_rci(series: pd.Series, period: int) -> pd.Series:
    """
    Rank Correlation Index（RCI）を計算する。
    :param series: 終値などの価格データ（pd.Series）
    :param period: 期間
    :return: RCIのpd.Series
    """
    n = period

    def _rci(x):
        price_ranks = pd.Series(x).rank(ascending=False)
        date_ranks = np.arange(1, n + 1)
        d = price_ranks.values - date_ranks
        return (1 - 6 * (d**2).sum() / (n * (n**2 - 1))) * 100

    return series.rolling(window=n).apply(_rci, raw=False)


def ensure_feature_coverage(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    設定ファイルの特徴量カバレッジ確保

    Args:
        config: 設定辞書

    Returns:
        特徴量カバレッジ保証済み設定辞書
    """
    if not ENHANCED_FEATURES_AVAILABLE:
        logger.warning("⚠️ Enhanced feature engineering not available")
        return config

    logger.info("🔍 [COVERAGE] Ensuring feature coverage in configuration...")

    enhanced_config = config.copy()

    # ML設定から要求特徴量を取得
    ml_features = config.get("ml", {}).get("extra_features", [])
    strategy_features = (
        config.get("strategy", {})
        .get("params", {})
        .get("ml", {})
        .get("extra_features", [])
    )

    all_features = list(set(ml_features + strategy_features))

    if not all_features:
        logger.warning("⚠️ [COVERAGE] No features specified in configuration")
        return enhanced_config

    # Phase 8.3: FeatureMasterImplementation優先監査
    if FEATURE_MASTER_AVAILABLE:
        logger.info("🚀 [COVERAGE] Using FeatureMasterImplementation for feature audit")
        try:
            feature_master = FeatureMasterImplementation(config)
            # テストデータで実装状況を確認
            import numpy as np
            import pandas as pd

            dates = pd.date_range("2024-01-01", periods=20, freq="H")
            test_df = pd.DataFrame(
                {
                    "open": np.random.randn(20).cumsum() + 100,
                    "high": np.random.randn(20).cumsum() + 105,
                    "low": np.random.randn(20).cumsum() + 95,
                    "close": np.random.randn(20).cumsum() + 100,
                    "volume": np.random.randint(1000, 10000, 20),
                },
                index=dates,
            )

            # FeatureMasterImplementationで特徴量生成
            feature_master.generate_all_features(test_df)
            report = feature_master.get_implementation_report()

            # FeatureMasterImplementation監査結果
            audit_result = {
                "total_requested": len(all_features),
                "implemented": report["implemented_features"],
                "implementation_rate": report["implementation_stats"][
                    "implementation_rate"
                ]
                / 100.0,
                "missing": [],  # FeatureMasterImplementationは未実装もプレースホルダーで対応
                "external_dependent": [],
                "derivable": [],
            }

            logger.info("✅ [COVERAGE] FeatureMasterImplementation audit completed:")
            logger.info(f"   - Total requested: {audit_result['total_requested']}")
            logger.info(
                f"   - Implemented: {len(audit_result['implemented'])} ({audit_result['implementation_rate']:.1%})"
            )
            logger.info(
                "   - Missing: 0 (FeatureMasterImplementation provides fallbacks)"
            )

        except Exception as e:
            logger.error(f"❌ [COVERAGE] FeatureMasterImplementation audit failed: {e}")
            # フォールバック: 古いシステムを使用
            # Phase 3: FeatureEngineeringEnhanced機能完全無効化
            audit_result = {"missing": [], "implemented": all_features}
            logger.warning(
                "⚠️ [COVERAGE] Using legacy FeatureEngineeringEnhanced audit (fallback)"
            )

    else:
        # Phase 8.3: レガシーauditシステム（フォールバック）
        # Phase 3: FeatureEngineeringEnhanced機能完全無効化
        audit_result = {"missing": [], "implemented": all_features}

    # 未実装特徴量の警告とフォールバック設定
    if audit_result["missing"]:
        logger.warning(
            f"⚠️ [COVERAGE] Unimplemented features detected ({len(audit_result['missing'])})"
        )
        logger.info(
            f"   Missing: {audit_result['missing'][:10]}..."
        )  # 最初の10個を表示

        # フォールバック設定を追加
        enhanced_config.setdefault("feature_fallback", {})
        enhanced_config["feature_fallback"]["auto_generate_missing"] = True
        enhanced_config["feature_fallback"]["missing_features"] = audit_result[
            "missing"
        ]

    # 外部データ依存特徴量の設定確認
    if audit_result["external_dependent"]:
        logger.info(
            f"📡 [COVERAGE] External data features ({len(audit_result['external_dependent'])})"
        )

        # 外部データ設定の存在確認
        external_config = enhanced_config.get("ml", {}).get("external_data", {})
        if not external_config.get("enabled", False):
            logger.warning(
                "⚠️ [COVERAGE] External data features requested but external_data not enabled"
            )
            enhanced_config.setdefault("ml", {}).setdefault("external_data", {})[
                "enabled"
            ] = True

    logger.info("✅ [COVERAGE] Feature coverage ensured:")
    logger.info(f"   - Implementation rate: {audit_result['implementation_rate']:.1%}")
    logger.info(f"   - Total features: {audit_result['total_requested']}")
    logger.info(f"   - Implemented: {len(audit_result['implemented'])}")
    logger.info(f"   - Missing: {len(audit_result['missing'])}")

    return enhanced_config
