#!/usr/bin/env python3
"""
Phase H.30修正効果確認テスト

目的:
- enhanced_default汚染防止システムの動作確認
- 124特徴量でenhanced_default_000が生成されないことを確認
- 新しい許容範囲システムの検証
"""

import logging
import os
import sys

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.append("/Users/nao/Desktop/bot")

from crypto_bot.ml.feature_defaults import ensure_feature_consistency

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_h30_fix():
    """Phase H.30修正効果テスト"""
    logger.info("🧪 Phase H.30修正効果テスト開始")

    # テストデータ作成（100行×124列）
    test_data = pd.DataFrame(
        0.5, index=range(100), columns=[f"feature_{i:03d}" for i in range(124)]
    )

    logger.info(
        f"📊 テストデータ作成: {test_data.shape} = {len(test_data.columns)}特徴量"
    )

    # Phase H.30前の期待動作（enhanced_default生成）
    logger.info("🔍 Phase H.30修正版でensure_feature_consistency実行")

    # 125特徴量目標でテスト
    result = ensure_feature_consistency(test_data, target_count=125)

    # 結果確認
    result_count = len(result.columns)
    enhanced_default_cols = [
        col for col in result.columns if "enhanced_default" in str(col)
    ]

    logger.info("📊 テスト結果:")
    logger.info(f"   入力特徴量: 124個")
    logger.info(f"   出力特徴量: {result_count}個")
    logger.info(f"   enhanced_default列: {len(enhanced_default_cols)}個")

    if enhanced_default_cols:
        logger.error(f"❌ enhanced_default検出: {enhanced_default_cols}")
        success = False
    else:
        logger.info("✅ enhanced_default汚染なし！")
        success = True

    # 許容範囲テスト
    logger.info("🧪 許容範囲境界テスト:")

    # 122特徴量テスト（125-2=123より少ない→enhanced_default生成すべき）
    test_data_122 = test_data.iloc[:, :122]
    result_122 = ensure_feature_consistency(test_data_122, target_count=125)
    enhanced_default_122 = [
        col for col in result_122.columns if "enhanced_default" in str(col)
    ]

    logger.info(
        f"   122特徴量→{len(result_122.columns)}特徴量: enhanced_default={len(enhanced_default_122)}個"
    )

    if len(enhanced_default_122) > 0:
        logger.info("✅ 122特徴量では正常にenhanced_default生成")
    else:
        logger.warning("⚠️ 122特徴量でenhanced_default未生成（予期しない動作）")

    # 123特徴量テスト（125-2=123と同じ→境界値、enhanced_default生成すべき）
    test_data_123 = test_data.iloc[:, :123]
    result_123 = ensure_feature_consistency(test_data_123, target_count=125)
    enhanced_default_123 = [
        col for col in result_123.columns if "enhanced_default" in str(col)
    ]

    logger.info(
        f"   123特徴量→{len(result_123.columns)}特徴量: enhanced_default={len(enhanced_default_123)}個"
    )

    return success and result_count == 124  # 124のまま維持されることを期待


def main():
    """メイン実行"""
    logger.info("=" * 60)
    logger.info("Phase H.30: enhanced_default汚染防止システム効果確認テスト")
    logger.info("=" * 60)

    success = test_h30_fix()

    if success:
        print("\n🎉 Phase H.30修正成功！")
        print("✅ enhanced_default汚染防止システム正常動作")
        print("✅ 124特徴量でenhanced_default_000生成されず")
        print("🚀 新しいバックテスト実行準備完了")
    else:
        print("\n❌ Phase H.30修正確認失敗")
        print("🔧 追加修正が必要")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
