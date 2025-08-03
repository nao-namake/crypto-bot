#!/usr/bin/env python3
"""
シンプルなゼロ値特徴量確認テスト
実際に何個の特徴量がゼロ値になっているかを確認
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートの追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# ログ設定
logging.basicConfig(level=logging.WARNING)  # ログを最小限に


def quick_zero_check():
    """クイックゼロ値特徴量確認"""
    print("🔍 実際のゼロ値特徴量数確認テスト")
    print("-" * 50)

    try:
        # 設定読み込み
        from crypto_bot.config.strategy_factory import StrategyFactory

        config = StrategyFactory.create_config("config/production/production.yml")

        # preprocessor使用での特徴量生成テスト
        from crypto_bot.ml.preprocessor import Preprocessor

        preprocessor = Preprocessor(config)

        # 小さなテストデータ生成
        np.random.seed(42)
        size = 100
        dates = pd.date_range("2024-01-01", periods=size, freq="1H")

        base_price = 5000000
        price_changes = np.random.normal(0, 0.02, size)
        cumulative_changes = np.cumsum(price_changes)

        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": base_price * (1 + cumulative_changes),
                "high": base_price
                * (1 + cumulative_changes + np.abs(np.random.normal(0, 0.01, size))),
                "low": base_price
                * (1 + cumulative_changes - np.abs(np.random.normal(0, 0.01, size))),
                "close": base_price
                * (1 + cumulative_changes + np.random.normal(0, 0.005, size)),
                "volume": np.random.lognormal(10, 1, size),
            }
        )

        test_data.set_index("timestamp", inplace=True)

        print(f"📊 テストデータ: {len(test_data)}行")

        # 特徴量生成
        features_df = preprocessor.engineer_features(test_data)

        print(f"📈 生成された特徴量: {len(features_df.columns)}個")

        # ゼロ値の多い特徴量を特定
        zero_heavy_features = []
        for col in features_df.columns:
            if col in ["target", "signal"]:  # ターゲット系は除外
                continue

            series = features_df[col]
            zero_count = (series == 0).sum()
            total_count = len(series)
            zero_ratio = zero_count / total_count if total_count > 0 else 0

            # 50%以上がゼロの特徴量をリストアップ
            if zero_ratio > 0.5:
                zero_heavy_features.append(
                    {
                        "feature": col,
                        "zero_count": zero_count,
                        "total_count": total_count,
                        "zero_ratio": zero_ratio,
                    }
                )

        # 結果表示
        print(f"\n📋 ゼロ値が50%以上の特徴量: {len(zero_heavy_features)}個")
        print("-" * 50)

        if zero_heavy_features:
            for i, feat in enumerate(zero_heavy_features[:10], 1):  # 上位10個表示
                print(
                    f"{i:2d}. {feat['feature']}: {feat['zero_ratio']:.1%} ({feat['zero_count']}/{feat['total_count']})"
                )

            if len(zero_heavy_features) > 10:
                print(f"    ... あと{len(zero_heavy_features) - 10}個")
        else:
            print("✅ ゼロ値が50%以上の特徴量はありませんでした")

        # 80%以上の特徴量も確認
        very_zero_heavy = [f for f in zero_heavy_features if f["zero_ratio"] > 0.8]
        print(f"\n📋 ゼロ値が80%以上の特徴量: {len(very_zero_heavy)}個")

        if very_zero_heavy:
            for i, feat in enumerate(very_zero_heavy, 1):
                print(f"{i:2d}. {feat['feature']}: {feat['zero_ratio']:.1%}")

        print(f"\n🎯 結論:")
        print(f"   50%以上ゼロ: {len(zero_heavy_features)}個")
        print(f"   80%以上ゼロ: {len(very_zero_heavy)}個")

        return len(zero_heavy_features), len(very_zero_heavy)

    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback

        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    quick_zero_check()
