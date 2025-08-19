#!/usr/bin/env python3
"""
97特徴量バックテスト結果に基づく最適化提案生成スクリプト
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class OptimizationRecommender:
    """最適化提案生成クラス"""

    def __init__(self):
        self.backtest_results = None
        self.trade_log = None
        self.recommendations = []

    def load_backtest_results(self):
        """バックテスト結果の読み込み"""
        print("📊 バックテスト結果を分析中...")

        # CSVファイル読み込み
        results_path = Path("results/backtest_results.csv")
        if results_path.exists():
            self.backtest_results = pd.read_csv(results_path)
            print(
                f"✅ {len(self.backtest_results)}件のバックテスト結果を読み込みました"
            )

        # 取引ログ読み込み
        trade_log_path = Path("results/trade_log.csv")
        if trade_log_path.exists():
            try:
                self.trade_log = pd.read_csv(trade_log_path)
                print(f"✅ {len(self.trade_log)}件の取引ログを読み込みました")
            except pd.errors.EmptyDataError:
                print("⚠️ 取引ログが空です（取引が実行されませんでした）")
                self.trade_log = pd.DataFrame(
                    columns=["timestamp", "side", "price", "amount", "profit"]
                )

    def analyze_performance(self):
        """パフォーマンス分析"""
        print("\n🔍 パフォーマンス分析...")

        if self.backtest_results is None:
            return

        # 基本統計
        latest_result = self.backtest_results.iloc[-1]

        analysis = {
            "total_profit": latest_result["total_profit"],
            "final_balance": latest_result["final_balance"],
            "max_drawdown": latest_result["max_drawdown"],
            "sharpe_ratio": latest_result["sharpe"],
        }

        # 勝率計算（取引ログから）
        if self.trade_log is not None and len(self.trade_log) > 0:
            winning_trades = self.trade_log[self.trade_log["profit"] > 0]
            analysis["win_rate"] = len(winning_trades) / len(self.trade_log) * 100
            analysis["total_trades"] = len(self.trade_log)
            analysis["avg_profit"] = self.trade_log["profit"].mean()
            analysis["profit_factor"] = (
                self.trade_log[self.trade_log["profit"] > 0]["profit"].sum()
                / abs(self.trade_log[self.trade_log["profit"] < 0]["profit"].sum())
                if len(self.trade_log[self.trade_log["profit"] < 0]) > 0
                else 0
            )

        return analysis

    def generate_recommendations(self, analysis):
        """最適化提案の生成"""
        print("\n💡 最適化提案を生成中...")

        recommendations = []

        # 0. 取引が実行されていない場合（最優先）
        if analysis.get("total_trades", 0) == 0:
            recommendations.append(
                {
                    "priority": "CRITICAL",
                    "category": "エントリー条件・戦略設定",
                    "issue": "取引が一切実行されていない",
                    "recommendation": "エントリー条件の大幅緩和が必要",
                    "expected_impact": "取引機会の創出",
                    "implementation": {
                        "immediate_actions": [
                            "confidence_threshold を0.65→0.50に下げる",
                            "strategy.params.threshold を0.02→0.01に下げる",
                            "アンサンブル戦略の重み調整（より積極的なモデルに重みを増やす）",
                            "volatility_adjustment の感度を上げる",
                        ],
                        "test_settings": {
                            "confidence_threshold": 0.50,
                            "threshold": 0.01,
                            "threshold_bounds": [0.005, 0.03],
                            "atr_multiplier": 0.5,
                        },
                    },
                }
            )

            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "戦略の見直し",
                    "issue": "multi_timeframe_ensemble戦略が保守的すぎる",
                    "recommendation": "シンプルな戦略から段階的に複雑化",
                    "expected_impact": "取引シグナルの生成",
                    "implementation": {
                        "phase1": "まずsingle ML戦略でテスト",
                        "phase2": "取引が発生したらアンサンブル化",
                        "phase3": "マルチタイムフレーム統合",
                    },
                }
            )

        # 1. 損失が継続している場合
        elif analysis.get("total_profit", 0) < 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "エントリー条件",
                    "issue": "継続的な損失が発生",
                    "recommendation": "エントリー閾値の引き上げ（0.02→0.03）",
                    "expected_impact": "取引頻度を減らし、質の高いシグナルのみ採用",
                    "implementation": {
                        "file": "config/production/production.yml",
                        "parameter": "strategy.params.threshold",
                        "current_value": 0.02,
                        "suggested_value": 0.03,
                    },
                }
            )

        # 2. 勝率が低い場合
        if analysis.get("win_rate", 0) < 50:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "機械学習モデル",
                    "issue": f"勝率が低い（{analysis.get('win_rate', 0):.1f}%）",
                    "recommendation": "特徴量の見直しとモデル再学習",
                    "expected_impact": "予測精度の向上",
                    "implementation": {
                        "actions": [
                            "重要度の低い特徴量をさらに削除",
                            "ハイパーパラメータの最適化",
                            "学習データ期間の延長",
                        ]
                    },
                }
            )

        # 3. ドローダウンが大きい場合
        if abs(analysis.get("max_drawdown", 0)) > 0.15:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "リスク管理",
                    "issue": f"最大ドローダウンが大きい（{abs(analysis.get('max_drawdown', 0)):.1%}）",
                    "recommendation": "ポジションサイズの縮小とストップロス強化",
                    "expected_impact": "リスク低減",
                    "implementation": {
                        "file": "config/production/production.yml",
                        "parameters": {
                            "position_sizing.max_position_size": {
                                "current": 0.95,
                                "suggested": 0.5,
                            },
                            "risk_management.stop_loss": {
                                "current": 0.03,
                                "suggested": 0.02,
                            },
                        },
                    },
                }
            )

        # 4. 取引頻度の最適化
        total_trades = analysis.get("total_trades", 0)
        if total_trades < 10:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "category": "エントリー条件",
                    "issue": f"取引頻度が低い（{total_trades}回）",
                    "recommendation": "エントリー条件の緩和",
                    "expected_impact": "適切な取引機会の増加",
                    "implementation": {
                        "suggestions": [
                            "threshold_bounds を[0.005, 0.05]に調整",
                            "volatility_adjustment の感度を上げる",
                            "confidence_threshold を0.65→0.60に下げる",
                        ]
                    },
                }
            )

        # 5. 特徴量の追加調整
        recommendations.append(
            {
                "priority": "MEDIUM",
                "category": "特徴量最適化",
                "issue": "97特徴量の効果検証が必要",
                "recommendation": "段階的な特徴量調整",
                "expected_impact": "さらなる効率化と精度向上",
                "implementation": {
                    "phase1": "現在の97特徴量で1週間運用",
                    "phase2": "重要度下位10特徴量を削除して87特徴量で検証",
                    "phase3": "市場環境に応じた動的特徴量選択の実装",
                },
            }
        )

        # 6. 外部データの活用検討
        recommendations.append(
            {
                "priority": "LOW",
                "category": "外部データ統合",
                "issue": "外部データが無効化されている",
                "recommendation": "市場センチメント指標の段階的導入",
                "expected_impact": "マクロ環境を考慮した予測",
                "implementation": {
                    "phase1": "VIX指数のみ有効化して効果測定",
                    "phase2": "Fear&Greed指数を追加",
                    "phase3": "効果があれば他の指標も検討",
                },
            }
        )

        return recommendations

    def save_recommendations(self, analysis, recommendations):
        """提案の保存"""
        output_dir = Path("results/optimization_recommendations")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"recommendations_97features_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "current_performance": analysis,
            "recommendations": recommendations,
            "summary": {
                "high_priority_count": len(
                    [r for r in recommendations if r["priority"] == "HIGH"]
                ),
                "medium_priority_count": len(
                    [r for r in recommendations if r["priority"] == "MEDIUM"]
                ),
                "low_priority_count": len(
                    [r for r in recommendations if r["priority"] == "LOW"]
                ),
            },
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📁 最適化提案を保存しました: {output_file}")

        return report

    def print_recommendations(self, recommendations):
        """提案の表示"""
        print("\n" + "=" * 60)
        print("📋 97特徴量システム最適化提案")
        print("=" * 60)

        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. [{rec['priority']}] {rec['category']}")
            print(f"   問題: {rec['issue']}")
            print(f"   提案: {rec['recommendation']}")
            print(f"   期待効果: {rec['expected_impact']}")
            if "implementation" in rec:
                print("   実装方法:")
                self._print_implementation(rec["implementation"], indent=6)

    def _print_implementation(self, impl, indent=0):
        """実装方法の表示"""
        prefix = " " * indent
        if isinstance(impl, dict):
            for key, value in impl.items():
                if isinstance(value, (list, dict)):
                    print(f"{prefix}{key}:")
                    self._print_implementation(value, indent + 2)
                else:
                    print(f"{prefix}{key}: {value}")
        elif isinstance(impl, list):
            for item in impl:
                print(f"{prefix}- {item}")

    def run(self):
        """最適化提案の実行"""
        # データ読み込み
        self.load_backtest_results()

        # パフォーマンス分析
        analysis = self.analyze_performance()

        if analysis:
            print("\n現在のパフォーマンス:")
            for key, value in analysis.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")

        # 提案生成
        recommendations = self.generate_recommendations(analysis)

        # 提案表示
        self.print_recommendations(recommendations)

        # 提案保存
        report = self.save_recommendations(analysis, recommendations)

        print("\n" + "=" * 60)
        print("✅ 最適化提案の生成が完了しました")
        print(f"   HIGH優先度: {report['summary']['high_priority_count']}件")
        print(f"   MEDIUM優先度: {report['summary']['medium_priority_count']}件")
        print(f"   LOW優先度: {report['summary']['low_priority_count']}件")
        print("=" * 60)


def main():
    """メイン実行"""
    recommender = OptimizationRecommender()
    recommender.run()


if __name__ == "__main__":
    main()
