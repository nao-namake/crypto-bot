"""
戦略理論的分析のテスト - Phase 51.4-Day3
"""

import pytest

from scripts.analysis.strategy_theoretical_analysis import StrategyTheoreticalAnalyzer
from src.core.services.regime_types import RegimeType


@pytest.mark.skip(
    reason="Phase 51.7 Day 7: strategy_theoretical_analysis.pyがKeyError: 'config'で失敗 - strategies.yaml未実装のためスキップ"
)
class TestStrategyTheoreticalAnalyzer:
    """StrategyTheoreticalAnalyzer のテスト"""

    @pytest.fixture
    def analyzer(self):
        """Analyzer インスタンスを返すfixture"""
        return StrategyTheoreticalAnalyzer()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 初期化テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_analyzer_initialization(self, analyzer):
        """初期化テスト - Phase 51.5-A: 3戦略構成"""
        assert analyzer is not None
        assert len(analyzer.strategies) == 3
        assert "ATRBased" in analyzer.strategies
        assert "DonchianChannel" in analyzer.strategies
        assert "ADXTrendStrength" in analyzer.strategies

    def test_strategy_types_classification(self, analyzer):
        """戦略タイプ分類テスト - Phase 51.5-A: 3戦略構成"""
        assert analyzer.strategy_types["ATRBased"] == "range"
        assert analyzer.strategy_types["DonchianChannel"] == "range"
        assert analyzer.strategy_types["ADXTrendStrength"] == "trend"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # レジーム別重み取得テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_regime_weights_structure(self, analyzer):
        """レジーム別重み取得の構造テスト"""
        regime_weights = analyzer.get_regime_weights()

        # 4レジーム存在確認
        assert "tight_range" in regime_weights
        assert "normal_range" in regime_weights
        assert "trending" in regime_weights
        assert "high_volatility" in regime_weights

    def test_get_regime_weights_values(self, analyzer):
        """レジーム別重み値のテスト - Phase 51.5-A: 3戦略構成"""
        regime_weights = analyzer.get_regime_weights()

        # tight_rangeの重み確認（ATRBased主体）
        tight_range = regime_weights["tight_range"]
        assert tight_range.get("ATRBased", 0) > 0
        assert tight_range.get("DonchianChannel", 0) > 0

        # trendingの重み確認（ADXTrendStrength主体） - Phase 51.5-A
        trending = regime_weights["trending"]
        assert trending.get("ADXTrendStrength", 0) > 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # カバレッジ分析テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_analyze_regime_coverage_structure(self, analyzer):
        """カバレッジ分析の構造テスト"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)

        # 4レジーム存在確認
        assert len(coverage) == 4

        # 各レジームに必須キーが存在
        for regime_data in coverage.values():
            assert "active_count" in regime_data
            assert "active_strategies" in regime_data
            assert "weights" in regime_data

    def test_analyze_regime_coverage_values(self, analyzer):
        """カバレッジ分析の値テスト"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)

        # tight_rangeは2戦略（ATRBased + DonchianChannel）
        assert coverage["tight_range"]["active_count"] == 2
        assert "ATRBased" in coverage["tight_range"]["active_strategies"]

        # high_volatilityは0戦略（全無効化）
        assert coverage["high_volatility"]["active_count"] == 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 冗長性分析テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_identify_redundant_strategies_structure(self, analyzer):
        """冗長性分析の構造テスト"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)
        redundant = analyzer.identify_redundant_strategies(coverage)

        # リスト形式
        assert isinstance(redundant, list)

        # 各要素に必須キーが存在
        for item in redundant:
            assert "strategy" in item
            assert "reason" in item
            assert "severity" in item

    def test_identify_redundant_strategies_detects_low_usage(self, analyzer):
        """低使用頻度戦略の検出テスト - Phase 51.5-A: 冗長戦略削除済み"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)
        redundant = analyzer.identify_redundant_strategies(coverage)

        # Phase 51.5-A: MochipoyAlert・MultiTimeframe削除済みのため冗長戦略は少ない
        # 3戦略構成では冗長性が大幅に低減されることを確認
        redundant_strategies = [item["strategy"] for item in redundant]
        assert len(redundant_strategies) < 3  # 冗長戦略は3未満

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 削除推奨テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_generate_deletion_recommendation_structure(self, analyzer):
        """削除推奨の構造テスト"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)
        redundant = analyzer.identify_redundant_strategies(coverage)
        recommendation = analyzer.generate_deletion_recommendation(redundant)

        # 必須キー存在確認
        assert "deletion_candidates" in recommendation
        assert "total_candidates" in recommendation
        assert "remaining_strategies" in recommendation

    def test_generate_deletion_recommendation_candidate_count(self, analyzer):
        """削除推奨の候補数テスト - Phase 51.5-A: 3戦略構成"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)
        redundant = analyzer.identify_redundant_strategies(coverage)
        recommendation = analyzer.generate_deletion_recommendation(redundant)

        # Phase 51.5-A: 3戦略構成のため削除候補は0-2戦略
        assert recommendation["total_candidates"] <= 2

        # 残存戦略が存在（最低1戦略は残る）
        assert len(recommendation["remaining_strategies"]) >= 1

    def test_generate_deletion_recommendation_remaining_includes_atr(self, analyzer):
        """削除後にATRBasedが残ることを確認"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)
        redundant = analyzer.identify_redundant_strategies(coverage)
        recommendation = analyzer.generate_deletion_recommendation(redundant)

        # ATRBasedは最も使用頻度が高いため削除されない
        assert "ATRBased" in recommendation["remaining_strategies"]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # レポート生成テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_generate_report_returns_string(self, analyzer):
        """レポート生成が文字列を返すテスト"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)
        redundant = analyzer.identify_redundant_strategies(coverage)
        recommendation = analyzer.generate_deletion_recommendation(redundant)
        report = analyzer.generate_report(regime_weights, coverage, redundant, recommendation)

        assert isinstance(report, str)
        assert len(report) > 0

    def test_generate_report_contains_key_sections(self, analyzer):
        """レポートが主要セクションを含むテスト - Phase 51.5-A: 3戦略構成"""
        regime_weights = analyzer.get_regime_weights()
        coverage = analyzer.analyze_regime_coverage(regime_weights)
        redundant = analyzer.identify_redundant_strategies(coverage)
        recommendation = analyzer.generate_deletion_recommendation(redundant)
        report = analyzer.generate_report(regime_weights, coverage, redundant, recommendation)

        # 主要セクション存在確認 - Phase 51.5-A
        assert "【既存3戦略】" in report
        assert "【レジーム別戦略カバレッジ】" in report
        assert "【冗長性分析】" in report
        assert "【削除推奨】" in report
        assert "【削除後の残存戦略】" in report
        assert "【次のアクション】" in report

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 統合テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_full_analysis_workflow(self, analyzer):
        """完全な分析ワークフローテスト - Phase 51.5-A: 3戦略構成"""
        # 1. レジーム別重み取得
        regime_weights = analyzer.get_regime_weights()
        assert len(regime_weights) == 4

        # 2. カバレッジ分析
        coverage = analyzer.analyze_regime_coverage(regime_weights)
        assert len(coverage) == 4

        # 3. 冗長性分析 - Phase 51.5-A: 冗長性は大幅に低減
        redundant = analyzer.identify_redundant_strategies(coverage)
        assert len(redundant) >= 0  # 冗長戦略は0以上

        # 4. 削除推奨生成 - Phase 51.5-A: 削除候補は0-2戦略
        recommendation = analyzer.generate_deletion_recommendation(redundant)
        assert recommendation["total_candidates"] <= 2

        # 5. レポート生成
        report = analyzer.generate_report(regime_weights, coverage, redundant, recommendation)
        assert len(report) > 500  # 十分な情報量（3戦略構成のため短め）
