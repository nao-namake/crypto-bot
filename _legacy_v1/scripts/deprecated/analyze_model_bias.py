#!/usr/bin/env python3
"""
Phase 2方向性偏り診断スクリプト

目的:
- TradingEnsembleClassifierの予測方向性偏りを詳細分析
- SELL偏重問題の根本原因特定
- バランス改善方法の提案

問題:
- 0.5固定問題は解決したが、全てSELL予測になっている
- LONGシグナルが生成されない
- 方向性の偏りによる勝率悪化
"""

import logging
import os
import pickle
import sys

import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
sys.path.append("/Users/nao/Desktop/bot")

from crypto_bot.ml.ensemble import TradingEnsembleClassifier

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def analyze_model_predictions():
    """モデル予測偏り分析"""
    logger.info("🔍 TradingEnsembleClassifier方向性偏り分析開始")

    try:
        # 1. モデル読み込み
        model_path = "/Users/nao/Desktop/bot/models/production/model.pkl"
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        logger.info(f"✅ モデル読み込み完了: {type(model)}")

        # 2. テストデータ作成（多様な市場環境を模擬）
        logger.info("📊 テストデータ作成（多様な市場環境）")

        # 様々な市場状況を表すダミーデータ
        test_scenarios = []
        scenario_names = []

        # 上昇トレンド
        for i in range(50):
            # 上昇トレンド的な特徴量設定
            features = np.random.normal(0, 1, 125)
            features[0] = np.random.normal(1.0, 0.5)  # close上昇傾向
            features[1] = np.random.normal(1.0, 0.3)  # 上昇モメンタム
            test_scenarios.append(features)
            scenario_names.append("bull_trend")

        # 下降トレンド
        for i in range(50):
            # 下降トレンド的な特徴量設定
            features = np.random.normal(0, 1, 125)
            features[0] = np.random.normal(-1.0, 0.5)  # close下降傾向
            features[1] = np.random.normal(-1.0, 0.3)  # 下降モメンタム
            test_scenarios.append(features)
            scenario_names.append("bear_trend")

        # レンジ相場
        for i in range(50):
            # レンジ相場的な特徴量設定
            features = np.random.normal(0, 0.5, 125)  # 小さな変動
            test_scenarios.append(features)
            scenario_names.append("range_market")

        X_test = np.array(test_scenarios)
        logger.info(f"   テストデータ: {X_test.shape}")

        # 3. 予測実行・分析
        logger.info("🤖 予測実行・偏り分析")

        # 分類予測（0=下降, 1=上昇）
        predictions = model.predict(X_test)
        pred_proba = model.predict_proba(X_test)

        # 全体統計
        total_long = np.sum(predictions == 1)
        total_short = np.sum(predictions == 0)
        long_ratio = total_long / len(predictions)

        logger.info("📊 全体予測統計:")
        logger.info(f"   LONG予測: {total_long}/{len(predictions)} ({long_ratio:.1%})")
        logger.info(
            f"   SHORT予測: {total_short}/{len(predictions)} ({100-long_ratio*100:.1%})"
        )

        # 確率分布分析
        prob_up = pred_proba[:, 1]  # 上昇確率
        logger.info("📊 上昇確率分布:")
        logger.info(f"   平均: {prob_up.mean():.3f}")
        logger.info(f"   中央値: {np.median(prob_up):.3f}")
        logger.info(f"   最小値: {prob_up.min():.3f}")
        logger.info(f"   最大値: {prob_up.max():.3f}")
        logger.info(f"   標準偏差: {prob_up.std():.3f}")

        # シナリオ別分析
        logger.info("📊 シナリオ別予測分析:")
        scenarios = ["bull_trend", "bear_trend", "range_market"]

        for scenario in scenarios:
            mask = np.array(scenario_names) == scenario
            scenario_predictions = predictions[mask]
            scenario_proba = prob_up[mask]

            long_count = np.sum(scenario_predictions == 1)
            short_count = np.sum(scenario_predictions == 0)
            scenario_long_ratio = long_count / len(scenario_predictions)

            logger.info(f"   {scenario}:")
            logger.info(
                f"     LONG: {long_count}/{len(scenario_predictions)} ({scenario_long_ratio:.1%})"
            )
            logger.info(
                f"     SHORT: {short_count}/{len(scenario_predictions)} ({100-scenario_long_ratio*100:.1%})"
            )
            logger.info(f"     平均上昇確率: {scenario_proba.mean():.3f}")

        # 4. 閾値感度分析
        logger.info("📊 閾値感度分析:")
        thresholds = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70]

        for threshold in thresholds:
            # 閾値を適用した取引シグナル
            confident_mask = (prob_up >= threshold) | (prob_up <= (1 - threshold))
            confident_predictions = predictions[confident_mask]

            if len(confident_predictions) > 0:
                conf_long = np.sum(confident_predictions == 1)
                conf_short = np.sum(confident_predictions == 0)
                conf_long_ratio = conf_long / len(confident_predictions)

                logger.info(f"   閾値{threshold}: {len(confident_predictions)}シグナル")
                logger.info(f"     LONG: {conf_long} ({conf_long_ratio:.1%})")
                logger.info(f"     SHORT: {conf_short} ({100-conf_long_ratio*100:.1%})")
            else:
                logger.info(f"   閾値{threshold}: シグナルなし")

        # 5. 問題診断・推奨事項
        logger.info("🔍 問題診断・推奨事項:")

        if long_ratio < 0.1:
            logger.error("❌ 重大な偏り: LONG予測が極端に少ない（<10%）")
            logger.info("🔧 推奨対策:")
            logger.info("   1. 学習データの上昇・下降バランス確認")
            logger.info("   2. 特徴量の方向性バイアス調査")
            logger.info("   3. ターゲット作成ロジックの見直し")
            logger.info("   4. モデル再学習（バランス調整）")
        elif long_ratio < 0.3:
            logger.warning("⚠️ 中程度の偏り: LONG予測が少ない（<30%）")
            logger.info("🔧 推奨対策:")
            logger.info("   1. 閾値調整でバランス改善")
            logger.info("   2. 特徴量重要度分析")
        elif long_ratio > 0.7:
            logger.warning("⚠️ 中程度の偏り: SHORT予測が少ない（<30%）")
        else:
            logger.info("✅ バランス良好: LONG/SHORT比率適切")

        # 6. 詳細分析結果保存
        analysis_results = {
            "total_predictions": len(predictions),
            "long_count": int(total_long),
            "short_count": int(total_short),
            "long_ratio": float(long_ratio),
            "prob_stats": {
                "mean": float(prob_up.mean()),
                "median": float(np.median(prob_up)),
                "min": float(prob_up.min()),
                "max": float(prob_up.max()),
                "std": float(prob_up.std()),
            },
            "threshold_analysis": {},
        }

        for threshold in thresholds:
            confident_mask = (prob_up >= threshold) | (prob_up <= (1 - threshold))
            confident_predictions = predictions[confident_mask]

            if len(confident_predictions) > 0:
                analysis_results["threshold_analysis"][threshold] = {
                    "signal_count": int(len(confident_predictions)),
                    "long_count": int(np.sum(confident_predictions == 1)),
                    "short_count": int(np.sum(confident_predictions == 0)),
                    "long_ratio": float(
                        np.sum(confident_predictions == 1) / len(confident_predictions)
                    ),
                }

        # 結果保存
        import json

        with open("/Users/nao/Desktop/bot/results/model_bias_analysis.json", "w") as f:
            json.dump(analysis_results, f, indent=2)

        logger.info("✅ 分析完了: results/model_bias_analysis.json に保存")

        return analysis_results

    except Exception as e:
        logger.error(f"❌ 分析失敗: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """メイン実行"""
    logger.info("=" * 60)
    logger.info("Phase 2: TradingEnsembleClassifier方向性偏り分析")
    logger.info("=" * 60)

    results = analyze_model_predictions()

    if results:
        print("\n🎯 分析結果サマリ:")
        print(f"✅ 予測分析完了")
        print(f"📊 LONG比率: {results['long_ratio']:.1%}")
        print(f"📊 SHORT比率: {1-results['long_ratio']:.1%}")
        print(f"📊 上昇確率平均: {results['prob_stats']['mean']:.3f}")
        print(f"💾 詳細結果: results/model_bias_analysis.json")

        if results["long_ratio"] < 0.1:
            print("❌ 重大な偏り検出：LONG予測不足")
            print("🔧 モデル再学習・バランス調整が必要")
        elif results["long_ratio"] < 0.3 or results["long_ratio"] > 0.7:
            print("⚠️ 中程度の偏り検出")
            print("🔧 閾値調整・特徴量分析を推奨")
        else:
            print("✅ バランス良好")
            print("🚀 Phase 2閾値最適化に進行可能")
    else:
        print("\n❌ 分析失敗")
        print("🔧 エラーログを確認してください")

    return 0 if results else 1


if __name__ == "__main__":
    exit(main())
