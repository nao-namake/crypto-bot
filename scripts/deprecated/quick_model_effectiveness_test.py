#!/usr/bin/env python3
"""
改善モデル効果確認クイックテスト
Phase 3改善項目の効果を迅速に検証
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def quick_model_test():
    """改善モデルの迅速効果確認"""

    print("🚀 Phase 3改善モデル効果確認テスト")
    print("=" * 60)

    # 設定読み込み
    config_path = str(project_root / "config/production/production.yml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # 1. モデルメタデータ確認
    print("📋 1. モデル状態確認")
    metadata_path = project_root / "models/production/model_metadata.yaml"
    with open(metadata_path, "r") as f:
        metadata = yaml.safe_load(f)

    print(f"   - Phase: {metadata['phase']}")
    print(f"   - 特徴量数: {metadata['features_count']}")
    print(f"   - 学習精度: {metadata['validation_results']['train_accuracy']:.1%}")
    print(
        f"   - 予測多様性: {metadata['validation_results']['prediction_diversity']}種類"
    )
    print(f"   - 予測範囲: {metadata['validation_results']['prediction_range']:.4f}")

    # 2. 小規模データでの特徴量生成テスト
    print(f"\n🔧 2. 小規模データ特徴量生成テスト（RSIフォールバック機能確認）")

    # 5レコードでテスト
    test_data = {
        "open": [10000.0, 10050.0, 10100.0, 10080.0, 10120.0],
        "high": [10100.0, 10150.0, 10200.0, 10180.0, 10220.0],
        "low": [9950.0, 10000.0, 10050.0, 10030.0, 10070.0],
        "close": [10050.0, 10100.0, 10080.0, 10120.0, 10150.0],
        "volume": [1000.0, 1200.0, 800.0, 1500.0, 1100.0],
    }

    df_small = pd.DataFrame(test_data)
    df_small.index = pd.date_range("2025-01-01", periods=5, freq="H")

    feature_engineer = FeatureEngineer(config)
    features_small = feature_engineer.transform(df_small)

    print(f"   - 小規模データ特徴量数: {len(features_small.columns)}/125")

    # RSI特徴量確認
    rsi_features = [col for col in features_small.columns if "rsi" in col.lower()]
    print(f"   - RSI特徴量: {len(rsi_features)}個 {rsi_features}")

    if len(features_small.columns) == 125:
        print(f"   ✅ 小規模データ125特徴量生成成功")
    else:
        print(f"   ⚠️ 特徴量数不一致: {len(features_small.columns)} != 125")

    # 3. モデル予測テスト（多様性確認）
    print(f"\n🤖 3. モデル予測多様性テスト")

    model_path = project_root / "models/production/model.pkl"
    model = joblib.load(model_path)

    # より大きなテストデータ作成
    test_size = 50
    np.random.seed(42)  # 再現性確保

    # 多様な価格パターン生成
    base_price = 10000000  # 1000万円（BTC/JPY）
    price_changes = np.random.normal(0, 0.02, test_size)  # 2%の標準偏差
    prices = [base_price]

    for change in price_changes:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)

    test_data_large = {
        "open": prices[:-1],
        "high": [p * 1.01 for p in prices[:-1]],
        "low": [p * 0.99 for p in prices[:-1]],
        "close": prices[1:],
        "volume": np.random.uniform(1000, 5000, test_size).tolist(),
    }

    df_large = pd.DataFrame(test_data_large)
    df_large.index = pd.date_range("2025-01-01", periods=test_size, freq="H")

    # 特徴量生成
    features_large = feature_engineer.transform(df_large)

    # 予測実行
    predictions = model.predict_proba(features_large)[:, 1]

    print(f"   - テストデータサイズ: {len(predictions)}")
    print(f"   - 予測値統計:")
    print(f"     * 最小値: {predictions.min():.4f}")
    print(f"     * 最大値: {predictions.max():.4f}")
    print(f"     * 平均値: {predictions.mean():.4f}")
    print(f"     * 標準偏差: {predictions.std():.4f}")
    print(f"     * ユニーク数: {len(np.unique(predictions.round(4)))}")

    # 4. BUY/SELLシグナル分布確認
    print(f"\n📊 4. BUY/SELLシグナル分布確認")

    threshold = 0.45  # Phase 2で最適化された閾値

    # シグナル生成
    buy_signals = predictions > (0.5 + threshold / 2)  # 上側閾値
    sell_signals = predictions < (0.5 - threshold / 2)  # 下側閾値
    neutral_signals = ~(buy_signals | sell_signals)

    buy_count = buy_signals.sum()
    sell_count = sell_signals.sum()
    neutral_count = neutral_signals.sum()
    total_signals = buy_count + sell_count + neutral_count

    print(f"   - BUY信号: {buy_count}回 ({buy_count/total_signals*100:.1f}%)")
    print(f"   - SELL信号: {sell_count}回 ({sell_count/total_signals*100:.1f}%)")
    print(f"   - NEUTRAL: {neutral_count}回 ({neutral_count/total_signals*100:.1f}%)")

    # 方向性バイアス判定
    if buy_count + sell_count > 0:
        buy_ratio = buy_count / (buy_count + sell_count)
        print(f"   - 取引信号中のBUY比率: {buy_ratio:.1%}")

        if 0.4 <= buy_ratio <= 0.6:
            print(f"   ✅ バランス良好: 40-60%範囲内")
        elif buy_ratio < 0.3:
            print(f"   ⚠️ SELL偏向: BUY比率30%未満")
        elif buy_ratio > 0.7:
            print(f"   ⚠️ BUY偏向: BUY比率70%超過")
        else:
            print(f"   🔄 軽微な偏向: 許容範囲内")
    else:
        print(f"   ⚠️ 取引信号なし: 閾値調整が必要")

    # 5. Phase 3改善効果まとめ
    print(f"\n" + "=" * 60)
    print("🎊 Phase 3改善効果サマリー")
    print("=" * 60)

    # 改善項目チェック
    improvements = []

    # 1. 固定予測問題修正
    prediction_range = metadata["validation_results"]["prediction_range"]
    if prediction_range > 0.3:
        improvements.append("✅ 固定予測問題修正: 予測範囲拡大")
    else:
        improvements.append("⚠️ 固定予測問題: まだ改善の余地あり")

    # 2. 特徴量統一
    if len(features_small.columns) == 125:
        improvements.append("✅ 125特徴量システム統一完了")
    else:
        improvements.append("⚠️ 特徴量統一: 不完全")

    # 3. RSIフォールバック機能
    if len(rsi_features) >= 5:
        improvements.append("✅ RSIフォールバック機能動作確認")
    else:
        improvements.append("⚠️ RSIフォールバック: 機能不足")

    # 4. 方向性バイアス改善
    if buy_count + sell_count > 0:
        buy_ratio = buy_count / (buy_count + sell_count)
        if 0.35 <= buy_ratio <= 0.65:
            improvements.append("✅ 方向性バイアス改善: バランス向上")
        else:
            improvements.append("🔄 方向性バイアス: さらなる改善必要")
    else:
        improvements.append("⚠️ 方向性バイアス: 評価不可（信号なし）")

    # 5. 予測多様性
    prediction_diversity = metadata["validation_results"]["prediction_diversity"]
    if prediction_diversity > 100:
        improvements.append("✅ 予測多様性確保: 豊富な予測値")
    else:
        improvements.append("⚠️ 予測多様性: 不足")

    # 改善結果表示
    for improvement in improvements:
        print(f"   {improvement}")

    # 総合評価
    success_count = len([i for i in improvements if i.startswith("✅")])
    total_count = len(improvements)
    success_rate = success_count / total_count

    print(f"\n📈 総合改善率: {success_count}/{total_count} ({success_rate:.1%})")

    if success_rate >= 0.8:
        print(f"🎉 Phase 3大成功！次のステップ準備完了")
    elif success_rate >= 0.6:
        print(f"✅ Phase 3成功！軽微な調整で完了")
    else:
        print(f"🔄 Phase 3部分成功！追加改善が必要")

    return {
        "success_rate": success_rate,
        "improvements": improvements,
        "buy_ratio": buy_ratio if buy_count + sell_count > 0 else None,
        "prediction_diversity": prediction_diversity,
        "prediction_range": prediction_range,
    }


if __name__ == "__main__":
    try:
        results = quick_model_test()

        print(f"\n" + "=" * 60)
        print("✅ Phase 3改善モデル効果確認完了")
        print("=" * 60)
        print("🚀 次のステップ: Kelly基準・リスク管理最適化")
        print("=" * 60)

    except Exception as e:
        logger.error(f"❌ テスト実行エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
