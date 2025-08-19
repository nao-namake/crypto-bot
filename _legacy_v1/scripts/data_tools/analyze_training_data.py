#!/usr/bin/env python3
"""
Phase 3: 学習データ分析スクリプト
モデルの学習データを分析し、クラス不均衡やバイアスの原因を特定する

このスクリプトは以下を分析します：
1. 学習データのクラス分布（上昇/下落の比率）
2. 期間別のクラス分布（ベアマーケットの影響）
3. 特徴量の相関と重要度
4. モデルの学習メタデータ
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.ml.feature_engines import BatchFeatureCalculator, TechnicalFeatureEngine
from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.ml.target import make_classification_target

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TrainingDataAnalyzer:
    """学習データ分析クラス"""

    def __init__(self, config_path: str):
        """初期化"""
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.feature_engineer = FeatureEngineer(self.config)
        self.batch_calc = BatchFeatureCalculator(self.config)
        self.tech_engine = TechnicalFeatureEngine(self.config, self.batch_calc)

        # 結果保存用
        self.results = {
            "class_distribution": {},
            "period_analysis": {},
            "feature_analysis": {},
            "metadata": {},
        }

    def load_training_data(self, days: int = 365) -> pd.DataFrame:
        """学習データのロード（過去1年分）"""
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

            # ページネーションで大量データ取得
            df = fetcher.get_price_df(
                timeframe="1h",
                since=int(start_time.timestamp() * 1000),
                limit=days * 24,
                paginate=True,
            )

            logger.info(f"📊 学習データ取得: {len(df)}レコード")
            return df

        except Exception as e:
            logger.error(f"❌ データ取得失敗: {e}")
            raise

    def analyze_class_distribution(self, df: pd.DataFrame):
        """クラス分布の分析"""
        # ターゲット生成（5期間後の上昇/下落）
        target = make_classification_target(df, horizon=5, threshold=0.0)

        # クラス分布
        class_counts = target.value_counts()
        class_ratio = target.value_counts(normalize=True)

        self.results["class_distribution"] = {
            "up_count": int(class_counts.get(1, 0)),
            "down_count": int(class_counts.get(0, 0)),
            "up_ratio": float(class_ratio.get(1, 0)),
            "down_ratio": float(class_ratio.get(0, 0)),
            "total_samples": len(target),
            "imbalance_ratio": (
                float(class_counts.get(0, 0) / class_counts.get(1, 1))
                if class_counts.get(1, 0) > 0
                else np.inf
            ),
        }

        logger.info(
            f"📊 クラス分布: UP={class_counts.get(1, 0)} ({class_ratio.get(1, 0):.1%}), DOWN={class_counts.get(0, 0)} ({class_ratio.get(0, 0):.1%})"
        )

        return target

    def analyze_by_period(self, df: pd.DataFrame, target: pd.Series):
        """期間別分析"""
        # 月別集計
        df_with_target = df.copy()
        df_with_target["target"] = target
        df_with_target["month"] = pd.to_datetime(df_with_target.index).to_period("M")

        monthly_stats = []
        for month, group in df_with_target.groupby("month"):
            if "target" in group.columns and len(group) > 0:
                month_target = group["target"]
                up_ratio = (
                    (month_target == 1).sum() / len(month_target)
                    if len(month_target) > 0
                    else 0
                )
                monthly_stats.append(
                    {
                        "month": str(month),
                        "samples": len(group),
                        "up_ratio": float(up_ratio),
                        "down_ratio": float(1 - up_ratio),
                        "avg_price": float(group["close"].mean()),
                        "price_change": float(
                            (group["close"].iloc[-1] - group["close"].iloc[0])
                            / group["close"].iloc[0]
                            * 100
                        ),
                    }
                )

        self.results["period_analysis"] = {
            "monthly_stats": monthly_stats,
            "bear_market_months": sum(
                1 for stat in monthly_stats if stat["up_ratio"] < 0.4
            ),
            "bull_market_months": sum(
                1 for stat in monthly_stats if stat["up_ratio"] > 0.6
            ),
        }

    def analyze_features(self, df: pd.DataFrame):
        """特徴量分析"""
        # 特徴量生成
        features_df = self.tech_engine.generate_features(df)

        # 欠落特徴量の確認
        expected_features = self.config["ml"]["extra_features"]
        actual_features = list(features_df.columns)

        missing_features = set(expected_features) - set(actual_features)
        extra_features = (
            set(actual_features)
            - set(expected_features)
            - {"open", "high", "low", "close", "volume"}
        )

        # 特徴量の統計
        feature_stats = {}
        for col in features_df.columns:
            if col not in ["open", "high", "low", "close", "volume"]:
                feature_stats[col] = {
                    "mean": (
                        float(features_df[col].mean())
                        if not features_df[col].isna().all()
                        else None
                    ),
                    "std": (
                        float(features_df[col].std())
                        if not features_df[col].isna().all()
                        else None
                    ),
                    "null_ratio": float(
                        features_df[col].isna().sum() / len(features_df)
                    ),
                }

        self.results["feature_analysis"] = {
            "expected_count": len(expected_features) + 5,  # +5 for OHLCV
            "actual_count": len(actual_features),
            "missing_features": list(missing_features),
            "extra_features": list(extra_features),
            "feature_stats": feature_stats,
        }

    def load_model_metadata(self):
        """モデルメタデータの読み込み"""
        metadata_path = project_root / "models/production/model_metadata.yaml"

        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = yaml.safe_load(f)

            self.results["metadata"] = {
                "phase": metadata.get("phase"),
                "features_count": metadata.get("features_count"),
                "training_timestamp": metadata.get("training_timestamp"),
                "validation_results": metadata.get("validation_results", {}),
                "training_data_period": metadata.get("training_data_period", {}),
            }
        else:
            logger.warning("⚠️ モデルメタデータファイルが見つかりません")

    def visualize_results(self, save_path: str = None):
        """結果の可視化"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # 1. クラス分布
        ax1 = axes[0, 0]
        class_dist = self.results["class_distribution"]
        labels = ["DOWN (0)", "UP (1)"]
        sizes = [class_dist["down_count"], class_dist["up_count"]]
        colors = ["red", "green"]
        ax1.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
        ax1.set_title("学習データのクラス分布")

        # 2. 月別UP比率の推移
        ax2 = axes[0, 1]
        monthly_stats = self.results["period_analysis"]["monthly_stats"]
        months = [stat["month"] for stat in monthly_stats]
        up_ratios = [stat["up_ratio"] for stat in monthly_stats]

        ax2.plot(range(len(months)), up_ratios, marker="o")
        ax2.axhline(y=0.5, color="gray", linestyle="--", alpha=0.5)
        ax2.set_ylim(0, 1)
        ax2.set_title("月別UP比率の推移")
        ax2.set_xlabel("月")
        ax2.set_ylabel("UP比率")
        ax2.tick_params(axis="x", rotation=45)

        # 3. 価格推移と相場環境
        ax3 = axes[1, 0]
        prices = [stat["avg_price"] for stat in monthly_stats]
        ax3.plot(range(len(months)), prices, marker="o", color="blue")
        ax3.set_title("月別平均価格推移")
        ax3.set_xlabel("月")
        ax3.set_ylabel("価格 (JPY)")
        ax3.tick_params(axis="x", rotation=45)

        # 4. 特徴量欠落状況
        ax4 = axes[1, 1]
        feature_info = self.results["feature_analysis"]
        missing_count = len(feature_info["missing_features"])
        extra_count = len(feature_info["extra_features"])
        expected_count = feature_info["expected_count"]
        actual_count = feature_info["actual_count"]

        categories = ["期待", "実際", "欠落", "追加"]
        values = [expected_count, actual_count, missing_count, extra_count]
        colors_bar = ["blue", "green", "red", "orange"]

        ax4.bar(categories, values, color=colors_bar)
        ax4.set_title("特徴量カウント比較")
        ax4.set_ylabel("特徴量数")

        # テキストラベル追加
        for i, v in enumerate(values):
            ax4.text(i, v + 1, str(v), ha="center")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path)
            logger.info(f"📊 グラフ保存: {save_path}")
        else:
            plt.show()

    def print_analysis(self):
        """分析結果の出力"""
        print("\n" + "=" * 60)
        print("🔍 学習データ分析結果")
        print("=" * 60)

        # クラス分布
        class_dist = self.results["class_distribution"]
        print("\n📊 クラス分布:")
        print(f"  - UP (1): {class_dist['up_count']} ({class_dist['up_ratio']:.1%})")
        print(
            f"  - DOWN (0): {class_dist['down_count']} ({class_dist['down_ratio']:.1%})"
        )
        print(f"  - 不均衡比率: {class_dist['imbalance_ratio']:.2f}")

        # 期間分析
        period_info = self.results["period_analysis"]
        print("\n📊 期間別分析:")
        print(f"  - ベア相場月数: {period_info['bear_market_months']}")
        print(f"  - ブル相場月数: {period_info['bull_market_months']}")
        print(f"  - 分析期間: {len(period_info['monthly_stats'])}ヶ月")

        # 特徴量分析
        feature_info = self.results["feature_analysis"]
        print("\n📊 特徴量分析:")
        print(f"  - 期待特徴量数: {feature_info['expected_count']}")
        print(f"  - 実際特徴量数: {feature_info['actual_count']}")
        print(
            f"  - 欠落特徴量: {', '.join(feature_info['missing_features']) if feature_info['missing_features'] else 'なし'}"
        )

        # モデルメタデータ
        metadata = self.results.get("metadata", {})
        if metadata:
            print("\n📊 モデルメタデータ:")
            print(f"  - Phase: {metadata.get('phase', 'N/A')}")
            print(f"  - 学習時特徴量数: {metadata.get('features_count', 'N/A')}")
            print(f"  - 学習日時: {metadata.get('training_timestamp', 'N/A')}")

        # 診断結果
        print("\n🔍 診断結果:")
        if class_dist["down_ratio"] > 0.6:
            print("  ⚠️ 重大なDOWNバイアス: 学習データが下落相場に偏っている")
        elif class_dist["up_ratio"] > 0.6:
            print("  ⚠️ UPバイアス: 学習データが上昇相場に偏っている")
        else:
            print("  ✅ クラス分布は比較的バランスが取れている")

        if feature_info["missing_features"]:
            print(
                f"  ❌ 特徴量不一致: {len(feature_info['missing_features'])}個の特徴量が欠落"
            )
        else:
            print("  ✅ 特徴量は完全に一致")

        print("\n" + "=" * 60)

    def save_results(self):
        """結果の保存"""
        output_path = project_root / "results/training_data_analysis.json"
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"📊 分析結果保存: {output_path}")


def main():
    """メイン実行"""
    # 設定ファイルパス
    config_path = str(project_root / "config/production/production.yml")

    # 分析実行
    analyzer = TrainingDataAnalyzer(config_path)

    try:
        # 学習データ取得（簡易版：30日分）
        logger.info("📊 学習データ取得中...")
        df = analyzer.load_training_data(days=30)  # デモ用に30日分

        # クラス分布分析
        logger.info("🔍 クラス分布分析中...")
        target = analyzer.analyze_class_distribution(df)

        # 期間別分析
        logger.info("🔍 期間別分析中...")
        analyzer.analyze_by_period(df, target)

        # 特徴量分析
        logger.info("🔍 特徴量分析中...")
        analyzer.analyze_features(df)

        # モデルメタデータ読み込み
        logger.info("🔍 モデルメタデータ読み込み中...")
        analyzer.load_model_metadata()

        # 結果出力
        analyzer.print_analysis()

        # 結果保存
        analyzer.save_results()

        # 可視化
        output_path = str(project_root / "results/training_data_analysis.png")
        analyzer.visualize_results(save_path=output_path)

        logger.info("✅ 分析完了")

    except Exception as e:
        logger.error(f"❌ 分析失敗: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
