#!/usr/bin/env python3
"""
Phase 3: 予測分布診断スクリプト
方向性バイアス（全SELL問題）の根本原因を特定する

このスクリプトは以下を分析します：
1. モデル予測値の分布（個別モデル・アンサンブル）
2. 予測値が0.475未満（SELLシグナル）に偏っているか
3. 各モデルの予測傾向
4. クラス不均衡の影響
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import joblib
import yaml

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.ml.target import make_classification_target

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PredictionBiasDiagnoser:
    """予測バイアス診断クラス"""

    def __init__(self, config_path: str):
        """初期化"""
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.feature_engineer = FeatureEngineer(self.config)
        self.feature_order_manager = FeatureOrderManager()

        # 結果保存用
        self.results = {
            "individual_predictions": {},
            "ensemble_predictions": None,
            "statistics": {},
            "signal_distribution": {},
        }

    def load_model(self, model_path: str) -> TradingEnsembleClassifier:
        """モデルロード"""
        try:
            # TradingEnsembleClassifierを直接ロード
            model = joblib.load(model_path)
            logger.info(f"✅ モデルロード成功: {model_path}")
            logger.info(f"  - モデルタイプ: {type(model).__name__}")
            return model
        except Exception as e:
            logger.error(f"❌ モデルロード失敗: {e}")
            raise

    def prepare_test_data(self, days: int = 30) -> pd.DataFrame:
        """テストデータ準備"""
        try:
            # データ取得
            fetcher = MarketDataFetcher(
                exchange_id="bitbank",
                symbol="BTC/JPY",
                api_key=self.config.get("data", {}).get("api_key"),
                api_secret=self.config.get("data", {}).get("api_secret"),
                testnet=False,
            )
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)

            df = fetcher.get_price_df(
                timeframe="1h",
                since=int(start_time.timestamp() * 1000),
                limit=days * 24,
            )

            logger.info(f"📊 テストデータ取得: {len(df)}レコード")
            return df

        except Exception as e:
            logger.error(f"❌ データ取得失敗: {e}")
            raise

    def extract_individual_predictions(
        self, model: TradingEnsembleClassifier, X: pd.DataFrame
    ):
        """個別モデルの予測値を抽出"""
        predictions = {}

        if hasattr(model, "fitted_base_models"):
            for i, base_model in enumerate(model.fitted_base_models):
                try:
                    # 個別モデルの予測確率
                    proba = base_model.predict_proba(X)
                    predictions[f"model_{i}_{type(base_model).__name__}"] = proba[:, 1]
                    logger.info(f"✅ モデル{i}予測抽出成功")
                except Exception as e:
                    logger.error(f"❌ モデル{i}予測失敗: {e}")

        self.results["individual_predictions"] = predictions

    def analyze_predictions(
        self, model: TradingEnsembleClassifier, price_df: pd.DataFrame
    ):
        """予測分析実行"""
        # 特徴量生成
        features_df = self.feature_engineer.transform(price_df)

        # 特徴量順序保証
        X = self.feature_order_manager.ensure_column_order(features_df)
        logger.info(f"📊 特徴量生成完了: {X.shape}")

        # アンサンブル予測
        ensemble_proba = model.predict_proba(X)
        self.results["ensemble_predictions"] = ensemble_proba[:, 1]

        # 個別モデル予測抽出
        self.extract_individual_predictions(model, X)

        # 統計分析
        self._calculate_statistics()

        # シグナル分布分析
        self._analyze_signal_distribution()

    def _calculate_statistics(self):
        """予測値の統計情報計算"""
        stats = {}

        # アンサンブル予測統計
        ensemble_pred = self.results["ensemble_predictions"]
        stats["ensemble"] = {
            "mean": np.mean(ensemble_pred),
            "std": np.std(ensemble_pred),
            "min": np.min(ensemble_pred),
            "max": np.max(ensemble_pred),
            "median": np.median(ensemble_pred),
            "q25": np.percentile(ensemble_pred, 25),
            "q75": np.percentile(ensemble_pred, 75),
        }

        # 個別モデル統計
        for model_name, predictions in self.results["individual_predictions"].items():
            stats[model_name] = {
                "mean": np.mean(predictions),
                "std": np.std(predictions),
                "min": np.min(predictions),
                "max": np.max(predictions),
                "median": np.median(predictions),
            }

        self.results["statistics"] = stats

    def _analyze_signal_distribution(self):
        """シグナル分布分析"""
        ensemble_pred = self.results["ensemble_predictions"]

        # 閾値設定（Phase 2の設定）
        threshold = 0.025

        # シグナル分類
        buy_signals = np.sum(ensemble_pred > (0.5 + threshold))
        sell_signals = np.sum(ensemble_pred < (0.5 - threshold))
        neutral_signals = len(ensemble_pred) - buy_signals - sell_signals

        self.results["signal_distribution"] = {
            "buy_count": buy_signals,
            "sell_count": sell_signals,
            "neutral_count": neutral_signals,
            "buy_ratio": buy_signals / len(ensemble_pred),
            "sell_ratio": sell_signals / len(ensemble_pred),
            "neutral_ratio": neutral_signals / len(ensemble_pred),
        }

    def visualize_results(self, save_path: str = None):
        """結果の可視化"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # 1. アンサンブル予測分布
        ax1 = axes[0, 0]
        ensemble_pred = self.results["ensemble_predictions"]
        ax1.hist(ensemble_pred, bins=50, alpha=0.7, color="blue", edgecolor="black")
        ax1.axvline(x=0.5, color="red", linestyle="--", label="中立線")
        ax1.axvline(x=0.475, color="orange", linestyle="--", label="SELL閾値")
        ax1.axvline(x=0.525, color="green", linestyle="--", label="BUY閾値")
        ax1.set_title("アンサンブル予測分布")
        ax1.set_xlabel("予測確率")
        ax1.set_ylabel("頻度")
        ax1.legend()

        # 2. 個別モデル予測分布比較
        ax2 = axes[0, 1]
        for model_name, predictions in self.results["individual_predictions"].items():
            ax2.hist(predictions, bins=30, alpha=0.5, label=model_name.split("_")[-1])
        ax2.axvline(x=0.5, color="red", linestyle="--")
        ax2.set_title("個別モデル予測分布")
        ax2.set_xlabel("予測確率")
        ax2.set_ylabel("頻度")
        ax2.legend()

        # 3. 予測値の時系列推移
        ax3 = axes[1, 0]
        ax3.plot(ensemble_pred, alpha=0.7, label="アンサンブル予測")
        ax3.axhline(y=0.5, color="red", linestyle="--", alpha=0.5)
        ax3.axhline(y=0.475, color="orange", linestyle="--", alpha=0.5)
        ax3.axhline(y=0.525, color="green", linestyle="--", alpha=0.5)
        ax3.set_title("予測値の時系列推移")
        ax3.set_xlabel("サンプル")
        ax3.set_ylabel("予測確率")
        ax3.legend()

        # 4. シグナル分布円グラフ
        ax4 = axes[1, 1]
        signal_dist = self.results["signal_distribution"]
        labels = ["BUY", "SELL", "NEUTRAL"]
        sizes = [
            signal_dist["buy_count"],
            signal_dist["sell_count"],
            signal_dist["neutral_count"],
        ]
        colors = ["green", "red", "gray"]
        ax4.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
        ax4.set_title("シグナル分布")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path)
            logger.info(f"📊 グラフ保存: {save_path}")
        else:
            plt.show()

    def print_diagnosis(self):
        """診断結果の出力"""
        print("\n" + "=" * 60)
        print("🔍 予測バイアス診断結果")
        print("=" * 60)

        # アンサンブル統計
        stats = self.results["statistics"]["ensemble"]
        print("\n📊 アンサンブル予測統計:")
        print(f"  - 平均値: {stats['mean']:.4f}")
        print(f"  - 標準偏差: {stats['std']:.4f}")
        print(f"  - 最小値: {stats['min']:.4f}")
        print(f"  - 最大値: {stats['max']:.4f}")
        print(f"  - 中央値: {stats['median']:.4f}")
        print(f"  - 第1四分位: {stats['q25']:.4f}")
        print(f"  - 第3四分位: {stats['q75']:.4f}")

        # 個別モデル統計
        print("\n📊 個別モデル予測統計:")
        for model_name, model_stats in self.results["statistics"].items():
            if model_name != "ensemble":
                print(f"\n  {model_name}:")
                print(f"    - 平均値: {model_stats['mean']:.4f}")
                print(f"    - 標準偏差: {model_stats['std']:.4f}")
                print(
                    f"    - 範囲: [{model_stats['min']:.4f}, {model_stats['max']:.4f}]"
                )

        # シグナル分布
        signal_dist = self.results["signal_distribution"]
        print("\n📊 シグナル分布:")
        print(
            f"  - BUY シグナル: {signal_dist['buy_count']} ({signal_dist['buy_ratio']:.1%})"
        )
        print(
            f"  - SELL シグナル: {signal_dist['sell_count']} ({signal_dist['sell_ratio']:.1%})"
        )
        print(
            f"  - NEUTRAL: {signal_dist['neutral_count']} ({signal_dist['neutral_ratio']:.1%})"
        )

        # 診断結果
        print("\n🔍 診断結果:")
        if stats["mean"] < 0.45:
            print("  ⚠️ 重大な負のバイアス検出: 予測が過度に悲観的")
        elif stats["mean"] > 0.55:
            print("  ⚠️ 重大な正のバイアス検出: 予測が過度に楽観的")
        else:
            print("  ✅ 予測の平均値は正常範囲内")

        if signal_dist["sell_ratio"] > 0.8:
            print("  ❌ 極度のSELLバイアス: 80%以上がSELLシグナル")
        elif signal_dist["buy_ratio"] > 0.8:
            print("  ❌ 極度のBUYバイアス: 80%以上がBUYシグナル")
        elif abs(signal_dist["buy_ratio"] - signal_dist["sell_ratio"]) > 0.4:
            print("  ⚠️ 方向性バイアス検出: BUY/SELLの不均衡が大きい")
        else:
            print("  ✅ シグナル分布は比較的バランスが取れている")

        print("\n" + "=" * 60)


def main():
    """メイン実行"""
    # 設定ファイルパス
    config_path = str(project_root / "config/production/production.yml")

    # モデルパス（最新のモデルを使用）
    model_path = str(project_root / "models/production/model.pkl")

    # 診断実行
    diagnoser = PredictionBiasDiagnoser(config_path)

    try:
        # モデルロード
        model = diagnoser.load_model(model_path)

        # テストデータ準備
        price_df = diagnoser.prepare_test_data(days=30)

        # 予測分析
        logger.info("🔍 予測分析開始...")
        diagnoser.analyze_predictions(model, price_df)

        # 結果出力
        diagnoser.print_diagnosis()

        # 可視化
        output_path = str(project_root / "results/prediction_bias_analysis.png")
        diagnoser.visualize_results(save_path=output_path)

        logger.info("✅ 診断完了")

    except Exception as e:
        logger.error(f"❌ 診断失敗: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
