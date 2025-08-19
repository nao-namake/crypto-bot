#!/usr/bin/env python3
"""
Phase 3.4: エントリー閾値最終最適化
現在のモデルの予測範囲に最適な閾値を設定
"""

import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def optimize_threshold_for_current_model():
    """現在のモデルに最適な閾値を計算"""

    print("🎯 Phase 3.4: エントリー閾値最終最適化")
    print("=" * 60)

    # 設定読み込み
    config_path = str(project_root / "config/production/production.yml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # モデル読み込み
    model_path = project_root / "models/production/model.pkl"
    model = joblib.load(model_path)

    # モデルメタデータ確認
    metadata_path = project_root / "models/production/model_metadata.yaml"
    with open(metadata_path, "r") as f:
        metadata = yaml.safe_load(f)

    print(f"📊 現在のモデル情報:")
    print(f"   - 予測範囲: {metadata['validation_results']['prediction_range']:.4f}")
    print(
        f"   - 最小値: {metadata['validation_results']['prediction_stats']['min']:.4f}"
    )
    print(
        f"   - 最大値: {metadata['validation_results']['prediction_stats']['max']:.4f}"
    )
    print(
        f"   - 平均値: {metadata['validation_results']['prediction_stats']['mean']:.4f}"
    )
    print(
        f"   - 標準偏差: {metadata['validation_results']['prediction_stats']['std']:.4f}"
    )

    # 大規模テストデータ生成
    print(f"\n🔧 大規模テストデータでの予測分布分析:")

    test_size = 200
    np.random.seed(42)

    # より現実的な価格データ生成
    base_price = 10000000  # 1000万円
    price_changes = np.random.normal(0, 0.01, test_size)  # 1%の標準偏差
    prices = [base_price]

    for change in price_changes:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, base_price * 0.5))  # 最低50%まで

    # 出来高とボラティリティの相関
    volatility = np.abs(price_changes)
    base_volume = 2000
    volumes = [base_volume * (1 + v * 10) for v in volatility]

    test_data = {
        "open": prices[:-1],
        "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices[:-1]],
        "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices[:-1]],
        "close": prices[1:],
        "volume": volumes,
    }

    df = pd.DataFrame(test_data)
    df.index = pd.date_range("2025-01-01", periods=test_size, freq="H")

    # 特徴量生成・予測
    feature_engineer = FeatureEngineer(config)
    features_df = feature_engineer.transform(df)
    predictions = model.predict_proba(features_df)[:, 1]

    print(f"   - テストサイズ: {len(predictions)}")
    print(f"   - 予測値統計:")
    print(f"     * 最小値: {predictions.min():.4f}")
    print(f"     * 最大値: {predictions.max():.4f}")
    print(f"     * 平均値: {predictions.mean():.4f}")
    print(f"     * 中央値: {np.median(predictions):.4f}")
    print(f"     * 標準偏差: {predictions.std():.4f}")
    print(f"     * 25%ile: {np.percentile(predictions, 25):.4f}")
    print(f"     * 75%ile: {np.percentile(predictions, 75):.4f}")

    # 最適閾値計算
    print(f"\n📊 最適閾値計算:")

    # 戦略1: パーセンタイル基準
    percentile_thresholds = {
        "90%信頼度": np.percentile(predictions, [10, 90]),
        "80%信頼度": np.percentile(predictions, [20, 80]),
        "70%信頼度": np.percentile(predictions, [30, 70]),
        "60%信頼度": np.percentile(predictions, [40, 60]),
    }

    print(f"   💡 パーセンタイル基準閾値:")
    for conf, (low, high) in percentile_thresholds.items():
        print(f"     {conf}: SELL<{low:.4f}, BUY>{high:.4f}")

    # 戦略2: 標準偏差基準
    mean_pred = predictions.mean()
    std_pred = predictions.std()

    std_thresholds = {
        "2σ": (mean_pred - 2 * std_pred, mean_pred + 2 * std_pred),
        "1.5σ": (mean_pred - 1.5 * std_pred, mean_pred + 1.5 * std_pred),
        "1σ": (mean_pred - std_pred, mean_pred + std_pred),
        "0.5σ": (mean_pred - 0.5 * std_pred, mean_pred + 0.5 * std_pred),
    }

    print(f"   📈 標準偏差基準閾値:")
    for sigma, (low, high) in std_thresholds.items():
        print(f"     {sigma}: SELL<{low:.4f}, BUY>{high:.4f}")

    # 戦略3: 絶対距離基準（0.5からの距離）
    abs_thresholds = {
        "0.15": (0.5 - 0.15, 0.5 + 0.15),
        "0.10": (0.5 - 0.10, 0.5 + 0.10),
        "0.05": (0.5 - 0.05, 0.5 + 0.05),
        "0.03": (0.5 - 0.03, 0.5 + 0.03),
        "0.02": (0.5 - 0.02, 0.5 + 0.02),
    }

    print(f"   ⚖️ 絶対距離基準閾値:")
    for dist, (low, high) in abs_thresholds.items():
        print(f"     ±{dist}: SELL<{low:.4f}, BUY>{high:.4f}")

    # 各閾値でのシグナル分布確認
    print(f"\n📊 推奨閾値での信号分布テスト:")

    recommended_thresholds = [
        ("70%信頼度", percentile_thresholds["70%信頼度"]),
        ("1σ", std_thresholds["1σ"]),
        ("±0.05", abs_thresholds["0.05"]),
        ("±0.03", abs_thresholds["0.03"]),
    ]

    best_threshold = None
    best_balance_score = float("inf")

    for name, (sell_thresh, buy_thresh) in recommended_thresholds:
        buy_signals = predictions > buy_thresh
        sell_signals = predictions < sell_thresh
        neutral_signals = ~(buy_signals | sell_signals)

        buy_count = buy_signals.sum()
        sell_count = sell_signals.sum()
        neutral_count = neutral_signals.sum()

        # バランススコア計算（理想は50:50）
        if buy_count + sell_count > 0:
            buy_ratio = buy_count / (buy_count + sell_count)
            balance_score = abs(buy_ratio - 0.5)  # 0.5からの距離

            print(f"   {name}:")
            print(f"     BUY: {buy_count}回 ({buy_count/len(predictions)*100:.1f}%)")
            print(f"     SELL: {sell_count}回 ({sell_count/len(predictions)*100:.1f}%)")
            print(
                f"     NEUTRAL: {neutral_count}回 ({neutral_count/len(predictions)*100:.1f}%)"
            )
            print(f"     BUY比率: {buy_ratio:.1%}")
            print(f"     バランススコア: {balance_score:.3f}")

            # 最適閾値判定（取引頻度とバランスを両方考慮）
            total_signals = buy_count + sell_count
            signal_ratio = total_signals / len(predictions)

            # 理想的な条件: 取引頻度10-30%、バランススコア<0.2
            if 0.1 <= signal_ratio <= 0.3 and balance_score < best_balance_score:
                best_threshold = (
                    name,
                    sell_thresh,
                    buy_thresh,
                    buy_ratio,
                    signal_ratio,
                )
                best_balance_score = balance_score
        else:
            print(f"   {name}: 信号なし")

    # 推奨閾値決定
    print(f"\n" + "=" * 60)
    print("🎯 最適閾値推奨結果")
    print("=" * 60)

    if best_threshold:
        name, sell_thresh, buy_thresh, buy_ratio, signal_ratio = best_threshold
        print(f"✅ 推奨閾値: {name}")
        print(f"   - SELL閾値: {sell_thresh:.4f}")
        print(f"   - BUY閾値: {buy_thresh:.4f}")
        print(f"   - 取引頻度: {signal_ratio:.1%}")
        print(f"   - BUY/SELL比率: {buy_ratio:.1%} / {1-buy_ratio:.1%}")
        print(f"   - バランススコア: {best_balance_score:.3f}")

        # confidence_threshold形式に変換
        threshold_range = buy_thresh - sell_thresh
        confidence_threshold = threshold_range

        print(f"\n🔧 設定ファイル用パラメータ:")
        print(f"   confidence_threshold: {confidence_threshold:.4f}")
        print(f"   # BUY条件: prediction > {0.5 + confidence_threshold/2:.4f}")
        print(f"   # SELL条件: prediction < {0.5 - confidence_threshold/2:.4f}")

        return confidence_threshold, sell_thresh, buy_thresh

    else:
        print("⚠️ 最適閾値が見つかりませんでした")
        print("💡 フォールバック推奨:")

        # より緩い条件で再検索
        fallback_threshold = abs_thresholds["0.05"]
        sell_thresh, buy_thresh = fallback_threshold
        confidence_threshold = buy_thresh - sell_thresh

        print(f"   confidence_threshold: {confidence_threshold:.4f}")
        print(f"   # BUY条件: prediction > {buy_thresh:.4f}")
        print(f"   # SELL条件: prediction < {sell_thresh:.4f}")

        return confidence_threshold, sell_thresh, buy_thresh


def update_production_config(confidence_threshold):
    """本番設定ファイルを更新"""

    print(f"\n🔧 設定ファイル更新:")

    config_path = project_root / "config/production/production.yml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # 既存の confidence_threshold を更新
    if "strategy" not in config:
        config["strategy"] = {}

    config["strategy"]["confidence_threshold"] = float(confidence_threshold)

    # 更新を複数箇所に適用
    if "ml" in config:
        config["ml"]["confidence_threshold"] = float(confidence_threshold)

    # バックアップ作成
    backup_path = config_path.with_suffix(".yml.backup")
    with open(backup_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # 設定ファイル更新
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"   ✅ {config_path} 更新完了")
    print(f"   💾 バックアップ: {backup_path}")
    print(f"   📊 新しい閾値: {confidence_threshold:.4f}")


if __name__ == "__main__":
    try:
        confidence_threshold, sell_thresh, buy_thresh = (
            optimize_threshold_for_current_model()
        )

        # 設定ファイル更新
        update_production_config(confidence_threshold)

        print(f"\n" + "=" * 60)
        print("✅ Phase 3.4完了：エントリー閾値最適化完了")
        print("=" * 60)
        print(f"🎯 新しい閾値: {confidence_threshold:.4f}")
        print(f"📈 BUY条件: prediction > {buy_thresh:.4f}")
        print(f"📉 SELL条件: prediction < {sell_thresh:.4f}")
        print("🚀 これでBUY/SELLバランスが大幅改善される予定です！")
        print("=" * 60)

    except Exception as e:
        logger.error(f"❌ 最適化エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
