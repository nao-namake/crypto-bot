"""
戦略理論的分析 - Phase 58更新

6戦略構成（Phase 57）の理論的特性に基づく分析。

分析軸:
1. 戦略の設計思想（レンジ型 vs トレンド型）
2. 動的戦略選択結果（レジーム別重み）
3. 戦略の役割重複度
4. 冗長戦略の特定
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config.threshold_manager import get_threshold
from src.core.logger import get_logger
from src.core.services.regime_types import RegimeType


class StrategyTheoreticalAnalyzer:
    """戦略理論的分析クラス"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Phase 51.7 Day 7: strategies.yamlから動的取得（設定駆動型）
        from src.strategies.strategy_loader import StrategyLoader

        loader = StrategyLoader()
        strategies_data = loader.load_strategies()

        # 戦略リスト
        self.strategies = [s["metadata"]["name"] for s in strategies_data]

        # 戦略の設計思想（regime_affinityから取得）- Phase 58修正
        self.strategy_types = {
            s["metadata"]["name"]: s.get("regime_affinity", "both") for s in strategies_data
        }

        # 戦略の主要指標（現在は未使用のため空リスト）
        self.strategy_indicators = {s["metadata"]["name"]: [] for s in strategies_data}

        self.logger.info("✅ StrategyTheoreticalAnalyzer初期化完了")

    def get_regime_weights(self) -> dict:
        """Phase 51.3のレジーム別戦略重みを取得"""
        regime_weights = {}

        for regime in [
            RegimeType.TIGHT_RANGE,
            RegimeType.NORMAL_RANGE,
            RegimeType.TRENDING,
            RegimeType.HIGH_VOLATILITY,
        ]:
            weights = get_threshold(
                f"dynamic_strategy_selection.regime_strategy_mapping.{regime.value}",
                {},
            )
            regime_weights[regime.value] = weights

        return regime_weights

    def analyze_regime_coverage(self, regime_weights: dict) -> dict:
        """レジーム別の戦略カバレッジ分析"""
        coverage = {}

        for regime, weights in regime_weights.items():
            active_strategies = [s for s, w in weights.items() if w > 0]
            coverage[regime] = {
                "active_count": len(active_strategies),
                "active_strategies": active_strategies,
                "weights": weights,
            }

        return coverage

    def identify_redundant_strategies(self, coverage: dict) -> list:
        """冗長な戦略を特定"""
        redundant = []

        # 基準1: 全レジームで重みが0の戦略
        never_used = []
        for strategy in self.strategies:
            used_count = sum(
                1
                for regime_data in coverage.values()
                if strategy in regime_data["active_strategies"]
            )
            if used_count == 0:
                never_used.append(strategy)

        if never_used:
            redundant.extend(
                [
                    {
                        "strategy": s,
                        "reason": "全レジームで重み0（未使用）",
                        "severity": "high",
                    }
                    for s in never_used
                ]
            )

        # 基準2: 使用頻度が極めて低い戦略（1レジームのみ）
        low_usage = []
        for strategy in self.strategies:
            used_count = sum(
                1
                for regime_data in coverage.values()
                if strategy in regime_data["active_strategies"]
            )
            if 0 < used_count <= 1:
                low_usage.append(strategy)

        if low_usage:
            redundant.extend(
                [
                    {
                        "strategy": s,
                        "reason": f"使用レジーム数が少ない（{sum(1 for r in coverage.values() if s in r['active_strategies'])}/4レジーム）",
                        "severity": "medium",
                    }
                    for s in low_usage
                ]
            )

        # 基準3: 同じタイプの戦略が複数存在（トレンド型3つ）
        trend_strategies = [s for s, t in self.strategy_types.items() if t == "trend"]
        if len(trend_strategies) >= 3:
            # トレンド型の中で最も使用頻度が低い戦略を特定
            trend_usage = {}
            for strategy in trend_strategies:
                total_weight = sum(data["weights"].get(strategy, 0) for data in coverage.values())
                trend_usage[strategy] = total_weight

            # 最小重みの戦略
            min_weight_strategy = min(trend_usage, key=trend_usage.get)
            if trend_usage[min_weight_strategy] < 0.5:  # 合計重みが0.5未満
                redundant.append(
                    {
                        "strategy": min_weight_strategy,
                        "reason": f"トレンド型戦略の中で最も使用頻度が低い（合計重み: {trend_usage[min_weight_strategy]:.2f}）",
                        "severity": "medium",
                    }
                )

        return redundant

    def generate_deletion_recommendation(self, redundant: list) -> dict:
        """削除推奨リストを生成"""
        # 重要度でソート（high > medium）
        sorted_redundant = sorted(redundant, key=lambda x: 0 if x["severity"] == "high" else 1)

        # 上位3-4戦略を削除候補に
        deletion_candidates = (
            sorted_redundant[:4] if len(sorted_redundant) >= 4 else sorted_redundant
        )

        return {
            "deletion_candidates": deletion_candidates,
            "total_candidates": len(deletion_candidates),
            "remaining_strategies": [
                s for s in self.strategies if s not in [c["strategy"] for c in deletion_candidates]
            ],
        }

    def generate_report(
        self, regime_weights: dict, coverage: dict, redundant: list, recommendation: dict
    ) -> str:
        """包括的レポート生成"""
        lines = []
        lines.append("=" * 80)
        lines.append("📊 Phase 58: 戦略理論的分析レポート（6戦略構成）")
        lines.append("=" * 80)
        lines.append("")

        # 1. 戦略一覧
        lines.append("【現行6戦略】")
        for strategy in self.strategies:
            strategy_type = self.strategy_types[strategy]
            lines.append(f"  - {strategy}: {strategy_type}型")
        lines.append("")

        # 2. レジーム別カバレッジ
        lines.append("【レジーム別戦略カバレッジ】")
        for regime, data in coverage.items():
            lines.append(f"  {regime}:")
            lines.append(f"    有効戦略数: {data['active_count']}戦略")
            if data["active_strategies"]:
                for strategy in data["active_strategies"]:
                    weight = data["weights"].get(strategy, 0)
                    lines.append(f"      - {strategy}: {weight:.0%}")
            else:
                lines.append("      - なし（全戦略無効化）")
        lines.append("")

        # 3. 冗長性分析
        lines.append("【冗長性分析】")
        if redundant:
            for item in redundant:
                severity_mark = "⚠️" if item["severity"] == "high" else "📋"
                lines.append(f"  {severity_mark} {item['strategy']}: {item['reason']}")
        else:
            lines.append("  ✅ 冗長な戦略なし")
        lines.append("")

        # 4. 削除推奨
        lines.append("【削除推奨】")
        if recommendation["deletion_candidates"]:
            lines.append(f"  推奨削除戦略数: {recommendation['total_candidates']}戦略")
            lines.append("")
            for i, candidate in enumerate(recommendation["deletion_candidates"], 1):
                lines.append(f"  {i}. {candidate['strategy']}")
                lines.append(f"     理由: {candidate['reason']}")
                lines.append(f"     重要度: {candidate['severity']}")
                lines.append("")
        else:
            lines.append("  ✅ 削除推奨戦略なし")
            lines.append("")

        # 5. 残存戦略
        lines.append("【削除後の残存戦略】")
        if recommendation["remaining_strategies"]:
            lines.append(f"  残存戦略数: {len(recommendation['remaining_strategies'])}戦略")
            for strategy in recommendation["remaining_strategies"]:
                strategy_type = self.strategy_types[strategy]
                lines.append(f"    - {strategy} ({strategy_type}型)")
        else:
            lines.append("  （全戦略削除候補）")
        lines.append("")

        # 6. 次のアクション
        lines.append("【次のアクション】")
        lines.append("  - 削除候補戦略の実パフォーマンス測定")
        lines.append("  - 削除前後のアンサンブル性能比較")
        lines.append("  - 最終削除判断")
        lines.append("")

        lines.append("=" * 80)
        lines.append("✅ 戦略理論的分析完了")
        lines.append("=" * 80)

        return "\n".join(lines)

    def save_report(self, report: str, output_dir: Path = None):
        """レポート保存"""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "src/backtest/logs"

        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = "20251102_phase51_4_day3"

        txt_file = output_dir / f"strategy_theoretical_analysis_{timestamp}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(report)

        self.logger.info(f"💾 レポート保存完了: {txt_file}")
        return txt_file


def main():
    """メイン実行関数"""
    analyzer = StrategyTheoreticalAnalyzer()

    print("=" * 80)
    print("📊 Phase 58: 戦略理論的分析")
    print("=" * 80)
    print()

    # 1. レジーム別重み取得
    print("📂 レジーム別戦略重みを取得中...")
    regime_weights = analyzer.get_regime_weights()
    print("✅ レジーム別重み取得完了")
    print()

    # 2. レジームカバレッジ分析
    print("🎯 レジーム別カバレッジ分析中...")
    coverage = analyzer.analyze_regime_coverage(regime_weights)
    print("✅ カバレッジ分析完了")
    print()

    # 3. 冗長性分析
    print("🔍 冗長性分析中...")
    redundant = analyzer.identify_redundant_strategies(coverage)
    print(f"✅ 冗長性分析完了: {len(redundant)}件検出")
    print()

    # 4. 削除推奨生成
    print("📋 削除推奨リスト生成中...")
    recommendation = analyzer.generate_deletion_recommendation(redundant)
    print(f"✅ 削除推奨完了: {recommendation['total_candidates']}戦略")
    print()

    # 5. レポート生成
    print("📝 包括的レポート生成中...")
    report = analyzer.generate_report(regime_weights, coverage, redundant, recommendation)
    print()
    print(report)
    print()

    # 6. レポート保存
    print("💾 レポート保存中...")
    report_file = analyzer.save_report(report)
    print(f"✅ 保存完了: {report_file}")
    print()

    print("=" * 80)
    print("✅ 戦略理論的分析完了")
    print("   理論的分析に基づく削除候補特定完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
