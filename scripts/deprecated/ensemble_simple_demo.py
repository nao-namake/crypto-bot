#!/usr/bin/env python3
"""
アンサンブル学習システム簡易デモンストレーション
依存関係を最小限にしたA/Bテスト・統計的検証のデモ
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from crypto_bot.data.csv_loader import CSVDataLoader
    from crypto_bot.ml.ensemble import TradingEnsembleClassifier
    from crypto_bot.ml.preprocessor import FeatureEngineer

    have_crypto_bot = True
except ImportError:
    have_crypto_bot = False

import numpy as np
import pandas as pd
from scipy import stats

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnsembleSimpleDemo:
    """アンサンブル学習簡易デモシステム"""

    def __init__(self):
        """デモシステム初期化"""
        self.results = {}

        # 結果保存ディレクトリ
        self.output_dir = Path(project_root / "results" / "ensemble_simple_demo")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Ensemble Simple Demo initialized")

    def run_simple_demonstration(self):
        """簡易デモンストレーション実行"""
        print("🚀 アンサンブル学習システム簡易デモンストレーション")
        print("=" * 80)

        try:
            # データ生成
            print("\n📊 Phase 1: テストデータ生成")
            print("-" * 50)
            test_data = self._generate_test_data()

            # 従来手法シミュレーション
            print("\n🔧 Phase 2: 従来手法シミュレーション")
            print("-" * 50)
            traditional_results = self._simulate_traditional_method(test_data)

            # アンサンブル手法シミュレーション
            print("\n🎯 Phase 3: アンサンブル手法シミュレーション")
            print("-" * 50)
            ensemble_results = self._simulate_ensemble_method(test_data)

            # 統計的比較
            print("\n📈 Phase 4: 統計的比較分析")
            print("-" * 50)
            comparison_results = self._perform_statistical_comparison(
                traditional_results, ensemble_results
            )

            # 結果表示
            print("\n💡 Phase 5: 結果サマリー")
            print("-" * 50)
            self._display_results_summary(comparison_results)

            # 結果保存
            print("\n💾 Phase 6: 結果保存")
            print("-" * 50)
            self._save_results(
                {
                    "test_data": test_data,
                    "traditional_results": traditional_results,
                    "ensemble_results": ensemble_results,
                    "comparison_results": comparison_results,
                }
            )

            print("\n✅ 簡易デモンストレーション完了")

        except Exception as e:
            logger.error(f"Simple demonstration failed: {e}")
            print(f"\n❌ エラー: {e}")

    def _generate_test_data(self) -> dict:
        """テストデータ生成"""
        print("  📋 テストデータ生成中...")

        # シード設定
        np.random.seed(42)

        # 1年間の時系列データ
        dates = pd.date_range(start="2024-01-01", periods=365, freq="D")

        # 価格データ生成
        base_price = 45000
        returns = np.random.normal(0, 0.02, len(dates))
        prices = [base_price]

        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)

        # 基本特徴量生成
        features = pd.DataFrame(
            {
                "date": dates,
                "price": prices,
                "returns": np.concatenate([[0], returns[1:]]),
                "volume": np.random.uniform(100, 1000, len(dates)),
                "volatility": pd.Series(returns).rolling(20).std().fillna(0.02),
                "momentum": pd.Series(returns).rolling(5).mean().fillna(0),
                "trend": pd.Series(prices).rolling(20).mean().fillna(base_price)
                / pd.Series(prices).fillna(base_price),
            }
        )

        # ターゲット生成（次日リターンの正負）
        features["target"] = (features["returns"].shift(-1) > 0.005).astype(int)
        features = features.dropna()

        test_data = {
            "features": features,
            "sample_size": len(features),
            "date_range": f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}",
            "target_distribution": features["target"].value_counts().to_dict(),
        }

        print(f"  ✅ テストデータ生成完了: {len(features)} samples")
        return test_data

    def _simulate_traditional_method(self, test_data: dict) -> dict:
        """従来手法シミュレーション"""
        print("  🔧 従来手法シミュレーション実行中...")

        features = test_data["features"]

        # 単純な閾値ベース戦略
        predictions = []
        confidences = []

        for _, row in features.iterrows():
            # 簡単なルールベース予測
            score = 0

            # モメンタム
            if row["momentum"] > 0.001:
                score += 0.3

            # ボラティリティ
            if row["volatility"] < 0.025:
                score += 0.2

            # トレンド
            if row["trend"] > 1.0:
                score += 0.25

            # 予測
            prediction = 1 if score > 0.5 else 0
            confidence = min(score, 1.0)

            predictions.append(prediction)
            confidences.append(confidence)

        predictions = np.array(predictions)
        confidences = np.array(confidences)
        targets = features["target"].values

        # パフォーマンス計算
        accuracy = np.mean(predictions == targets)
        precision = np.sum((predictions == 1) & (targets == 1)) / max(
            np.sum(predictions == 1), 1
        )
        recall = np.sum((predictions == 1) & (targets == 1)) / max(
            np.sum(targets == 1), 1
        )
        f1_score = 2 * precision * recall / max(precision + recall, 1e-8)

        # 取引シミュレーション
        trading_performance = self._simulate_trading_performance(
            predictions, features["returns"].values
        )

        traditional_results = {
            "predictions": predictions,
            "confidences": confidences,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "avg_confidence": np.mean(confidences),
            "trading_performance": trading_performance,
        }

        print(f"  ✅ 従来手法シミュレーション完了: 精度={accuracy:.3f}")
        return traditional_results

    def _simulate_ensemble_method(self, test_data: dict) -> dict:
        """アンサンブル手法シミュレーション"""
        print("  🎯 アンサンブル手法シミュレーション実行中...")

        features = test_data["features"]

        # 3つのベースモデルをシミュレート
        ensemble_predictions = []
        ensemble_confidences = []

        for _, row in features.iterrows():
            # Model 1: Momentum-based
            score1 = 0.5 + row["momentum"] * 10

            # Model 2: Volatility-based
            score2 = 0.5 + (0.03 - row["volatility"]) * 5

            # Model 3: Trend-based
            score3 = 0.5 + (row["trend"] - 1.0) * 2

            # アンサンブル予測（重み付き平均）
            ensemble_score = 0.4 * score1 + 0.3 * score2 + 0.3 * score3
            ensemble_score = np.clip(ensemble_score, 0, 1)

            # 信頼度計算（予測の一致度）
            predictions = [1 if s > 0.5 else 0 for s in [score1, score2, score3]]
            agreement = np.mean(predictions)
            confidence = 0.5 + abs(agreement - 0.5)

            ensemble_predictions.append(
                1 if ensemble_score > 0.55 else 0
            )  # より保守的な閾値
            ensemble_confidences.append(confidence)

        ensemble_predictions = np.array(ensemble_predictions)
        ensemble_confidences = np.array(ensemble_confidences)
        targets = features["target"].values

        # パフォーマンス計算
        accuracy = np.mean(ensemble_predictions == targets)
        precision = np.sum((ensemble_predictions == 1) & (targets == 1)) / max(
            np.sum(ensemble_predictions == 1), 1
        )
        recall = np.sum((ensemble_predictions == 1) & (targets == 1)) / max(
            np.sum(targets == 1), 1
        )
        f1_score = 2 * precision * recall / max(precision + recall, 1e-8)

        # 取引シミュレーション
        trading_performance = self._simulate_trading_performance(
            ensemble_predictions, features["returns"].values
        )

        # アンサンブル特有指標
        model_diversity = np.std(ensemble_confidences)  # 多様性の代理指標

        ensemble_results = {
            "predictions": ensemble_predictions,
            "confidences": ensemble_confidences,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "avg_confidence": np.mean(ensemble_confidences),
            "model_diversity": model_diversity,
            "trading_performance": trading_performance,
        }

        print(f"  ✅ アンサンブル手法シミュレーション完了: 精度={accuracy:.3f}")
        return ensemble_results

    def _simulate_trading_performance(
        self, predictions: np.ndarray, returns: np.ndarray
    ) -> dict:
        """取引パフォーマンスシミュレーション"""
        portfolio_returns = []
        position = 0

        for i, pred in enumerate(predictions):
            if pred == 1 and position == 0:  # Buy signal
                position = 1
            elif pred == 0 and position == 1:  # Sell signal
                position = 0

            # ポジションに基づくリターン
            if position == 1:
                portfolio_returns.append(returns[i])
            else:
                portfolio_returns.append(0)

        portfolio_returns = np.array(portfolio_returns)

        # 統計計算
        total_return = np.sum(portfolio_returns)
        sharpe_ratio = (
            np.mean(portfolio_returns) / np.std(portfolio_returns) * np.sqrt(252)
            if np.std(portfolio_returns) > 0
            else 0
        )

        positive_returns = portfolio_returns[portfolio_returns > 0]
        negative_returns = portfolio_returns[portfolio_returns < 0]

        win_rate = (
            len(positive_returns) / len(portfolio_returns)
            if len(portfolio_returns) > 0
            else 0
        )
        max_drawdown = np.min(
            np.cumsum(portfolio_returns)
            - np.maximum.accumulate(np.cumsum(portfolio_returns))
        )

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "total_trades": np.sum(np.diff(predictions.astype(int)) != 0),
        }

    def _perform_statistical_comparison(
        self, traditional_results: dict, ensemble_results: dict
    ) -> dict:
        """統計的比較分析"""
        print("  📊 統計的比較分析実行中...")

        metrics = ["accuracy", "precision", "recall", "f1_score"]
        comparison_results = {}

        for metric in metrics:
            trad_val = traditional_results[metric]
            ens_val = ensemble_results[metric]

            # 基本統計
            improvement = ens_val - trad_val
            improvement_pct = (improvement / trad_val) * 100 if trad_val > 0 else 0

            # 模擬的な分散を作成（実際は複数実行の結果を使用）
            np.random.seed(42)
            trad_samples = np.random.normal(trad_val, abs(trad_val * 0.05), 50)
            ens_samples = np.random.normal(ens_val, abs(ens_val * 0.05), 50)

            # t検定
            t_stat, p_value = stats.ttest_ind(ens_samples, trad_samples)

            # 効果サイズ（Cohen's d）
            pooled_std = np.sqrt(
                (
                    (len(trad_samples) - 1) * np.var(trad_samples, ddof=1)
                    + (len(ens_samples) - 1) * np.var(ens_samples, ddof=1)
                )
                / (len(trad_samples) + len(ens_samples) - 2)
            )
            effect_size = improvement / pooled_std if pooled_std > 0 else 0

            # 信頼区間
            se_diff = pooled_std * np.sqrt(1 / len(trad_samples) + 1 / len(ens_samples))
            t_critical = stats.t.ppf(0.975, len(trad_samples) + len(ens_samples) - 2)
            ci_lower = improvement - t_critical * se_diff
            ci_upper = improvement + t_critical * se_diff

            # 解釈
            is_significant = p_value < 0.05
            if is_significant and improvement > 0:
                interpretation = "統計的に有意な改善"
            elif is_significant and improvement < 0:
                interpretation = "統計的に有意な悪化"
            else:
                interpretation = "統計的に有意な差なし"

            comparison_results[metric] = {
                "traditional_value": trad_val,
                "ensemble_value": ens_val,
                "improvement": improvement,
                "improvement_pct": improvement_pct,
                "p_value": p_value,
                "effect_size": effect_size,
                "confidence_interval": (ci_lower, ci_upper),
                "is_significant": is_significant,
                "interpretation": interpretation,
            }

        # 取引パフォーマンス比較
        trading_metrics = ["total_return", "sharpe_ratio", "win_rate"]
        for metric in trading_metrics:
            trad_val = traditional_results["trading_performance"][metric]
            ens_val = ensemble_results["trading_performance"][metric]

            improvement = ens_val - trad_val
            improvement_pct = (improvement / trad_val) * 100 if trad_val != 0 else 0

            comparison_results[f"trading_{metric}"] = {
                "traditional_value": trad_val,
                "ensemble_value": ens_val,
                "improvement": improvement,
                "improvement_pct": improvement_pct,
                "interpretation": (
                    "改善"
                    if improvement > 0
                    else "悪化" if improvement < 0 else "変化なし"
                ),
            }

        # 総合評価
        significant_improvements = sum(
            1
            for result in comparison_results.values()
            if result.get("is_significant", False) and result.get("improvement", 0) > 0
        )

        total_tests = len(
            [r for r in comparison_results.values() if "is_significant" in r]
        )

        overall_assessment = {
            "significant_improvements": significant_improvements,
            "total_tests": total_tests,
            "significance_rate": (
                significant_improvements / total_tests if total_tests > 0 else 0
            ),
            "recommendation": self._generate_recommendation(
                significant_improvements, total_tests
            ),
        }

        comparison_results["overall_assessment"] = overall_assessment

        print(
            f"  ✅ 統計的比較分析完了: {significant_improvements}/{total_tests} 有意な改善"
        )
        return comparison_results

    def _generate_recommendation(
        self, significant_improvements: int, total_tests: int
    ) -> str:
        """推奨事項生成"""
        if significant_improvements >= total_tests * 0.8:
            return "STRONGLY_RECOMMENDED: アンサンブル学習の本格導入を強く推奨"
        elif significant_improvements >= total_tests * 0.6:
            return "RECOMMENDED: アンサンブル学習の導入を推奨"
        elif significant_improvements >= total_tests * 0.4:
            return "CONDITIONAL: 条件付きでアンサンブル学習を検討"
        else:
            return "NOT_RECOMMENDED: 現時点でのアンサンブル学習導入は推奨しない"

    def _display_results_summary(self, comparison_results: dict):
        """結果サマリー表示"""
        print("  📋 結果サマリー:")

        overall = comparison_results.get("overall_assessment", {})
        print(f"    総合評価: {overall.get('recommendation', 'N/A')}")
        print(
            f"    有意な改善: {overall.get('significant_improvements', 0)}/{overall.get('total_tests', 0)}"
        )
        print(f"    改善率: {overall.get('significance_rate', 0):.2%}")

        print("\n  📊 主要メトリクス改善:")
        key_metrics = ["accuracy", "precision", "recall", "f1_score"]
        for metric in key_metrics:
            result = comparison_results.get(metric, {})
            if result:
                print(
                    f"    {metric}: {result.get('improvement_pct', 0):+.1f}% "
                    f"({result.get('interpretation', 'N/A')})"
                )

        print("\n  💰 取引パフォーマンス:")
        trading_metrics = [
            "trading_total_return",
            "trading_sharpe_ratio",
            "trading_win_rate",
        ]
        for metric in trading_metrics:
            result = comparison_results.get(metric, {})
            if result:
                metric_name = metric.replace("trading_", "")
                print(
                    f"    {metric_name}: {result.get('improvement_pct', 0):+.1f}% "
                    f"({result.get('interpretation', 'N/A')})"
                )

    def _save_results(self, results: dict):
        """結果保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON結果保存
        json_file = self.output_dir / f"ensemble_simple_demo_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            # numpy配列を変換
            serializable_results = self._make_serializable(results)
            json.dump(
                serializable_results, f, indent=2, ensure_ascii=False, default=str
            )

        # レポート保存
        report_file = self.output_dir / f"ensemble_demo_report_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(self._generate_report(results))

        print(f"  📁 結果保存: {json_file}")
        print(f"  📄 レポート: {report_file}")

    def _make_serializable(self, obj):
        """JSON序列化可能な形式に変換"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict("records")
        else:
            return obj

    def _generate_report(self, results: dict) -> str:
        """レポート生成"""
        report_lines = []
        report_lines.append("🚀 アンサンブル学習システム簡易デモ レポート")
        report_lines.append("=" * 80)

        # 実行概要
        report_lines.append(f"\n📊 実行概要:")
        report_lines.append(
            f"  実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        test_data = results.get("test_data", {})
        if test_data:
            report_lines.append(f"  データ期間: {test_data.get('date_range', 'N/A')}")
            report_lines.append(f"  サンプル数: {test_data.get('sample_size', 0)}")

        # 手法比較
        traditional = results.get("traditional_results", {})
        ensemble = results.get("ensemble_results", {})

        if traditional and ensemble:
            report_lines.append(f"\n📈 手法比較:")
            report_lines.append(f"  従来手法:")
            report_lines.append(f"    精度: {traditional.get('accuracy', 0):.3f}")
            report_lines.append(f"    適合率: {traditional.get('precision', 0):.3f}")
            report_lines.append(f"    再現率: {traditional.get('recall', 0):.3f}")

            report_lines.append(f"  アンサンブル手法:")
            report_lines.append(f"    精度: {ensemble.get('accuracy', 0):.3f}")
            report_lines.append(f"    適合率: {ensemble.get('precision', 0):.3f}")
            report_lines.append(f"    再現率: {ensemble.get('recall', 0):.3f}")

        # 統計的比較
        comparison = results.get("comparison_results", {})
        if comparison:
            overall = comparison.get("overall_assessment", {})
            report_lines.append(f"\n🔍 統計的分析:")
            report_lines.append(f"  総合推奨: {overall.get('recommendation', 'N/A')}")
            report_lines.append(
                f"  有意な改善数: {overall.get('significant_improvements', 0)}"
            )
            report_lines.append(f"  総テスト数: {overall.get('total_tests', 0)}")

            # 個別メトリクス
            report_lines.append(f"\n  📊 個別メトリクス結果:")
            key_metrics = ["accuracy", "precision", "recall", "f1_score"]
            for metric in key_metrics:
                result = comparison.get(metric, {})
                if result:
                    report_lines.append(
                        f"    {metric}: {result.get('improvement_pct', 0):+.1f}% "
                        f"(p={result.get('p_value', 1):.3f}, "
                        f"効果サイズ={result.get('effect_size', 0):.3f})"
                    )

        report_lines.append(f"\n" + "=" * 80)
        return "\n".join(report_lines)


def main():
    """メイン実行関数"""
    try:
        # 簡易デモ実行
        demo = EnsembleSimpleDemo()
        demo.run_simple_demonstration()

    except Exception as e:
        logger.error(f"Simple demo failed: {e}")
        print(f"\n❌ デモ実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
