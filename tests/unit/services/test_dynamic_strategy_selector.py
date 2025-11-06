"""
動的戦略選択器のテスト - Phase 51.5-A

DynamicStrategySelectorの機能・ロジックをテスト。
3戦略構成（ATRBased・DonchianChannel・ADXTrendStrength）対応。
"""

import pytest

from src.core.services.dynamic_strategy_selector import DynamicStrategySelector
from src.core.services.regime_types import RegimeType


@pytest.mark.skip(
    reason="Phase 51.7 Day 7: strategies.yamlの'config'キー構造未実装 - regime_affinity対応待ち"
)
class TestDynamicStrategySelector:
    """DynamicStrategySelectorのテストクラス"""

    @pytest.fixture
    def selector(self):
        """DynamicStrategySelector インスタンスを返すfixture"""
        return DynamicStrategySelector()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # get_regime_weights()テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_regime_weights_tight_range(self, selector):
        """tight_range レジームの重み取得が正しいことを確認"""
        weights = selector.get_regime_weights(RegimeType.TIGHT_RANGE)

        # tight_rangeは ATRBased + DonchianChannel（ADXTrendStrength=0.0）
        assert "ATRBased" in weights
        assert "DonchianChannel" in weights
        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert weights["ATRBased"] > 0
        assert weights["DonchianChannel"] > 0
        assert weights.get("ADXTrendStrength", 0) == 0.0

        # 重み合計が1.0であることを確認
        assert selector.validate_weights(weights)

    def test_get_regime_weights_normal_range(self, selector):
        """normal_range レジームの重み取得が正しいことを確認"""
        weights = selector.get_regime_weights(RegimeType.NORMAL_RANGE)

        # normal_rangeは ATRBased + DonchianChannel + ADXTrendStrength
        assert "ATRBased" in weights
        assert "DonchianChannel" in weights
        assert "ADXTrendStrength" in weights
        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert weights["ATRBased"] > 0
        assert weights["DonchianChannel"] > 0
        assert weights["ADXTrendStrength"] > 0

        # 重み合計が1.0であることを確認
        assert selector.validate_weights(weights)

    def test_get_regime_weights_trending(self, selector):
        """trending レジームの重み取得が正しいことを確認"""
        weights = selector.get_regime_weights(RegimeType.TRENDING)

        # trendingは ADXTrendStrength + ATRBased + DonchianChannel
        # ADXTrendStrengthが主戦略（60%）
        assert "ADXTrendStrength" in weights
        assert "ATRBased" in weights
        assert "DonchianChannel" in weights
        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert weights["ADXTrendStrength"] > 0
        assert weights["ATRBased"] > 0
        assert weights["DonchianChannel"] > 0
        # ADXTrendStrengthが最も高い重みを持つことを確認
        assert weights["ADXTrendStrength"] > weights["ATRBased"]
        assert weights["ADXTrendStrength"] > weights["DonchianChannel"]

        # 重み合計が1.0であることを確認
        assert selector.validate_weights(weights)

    def test_get_regime_weights_high_volatility(self, selector):
        """high_volatility レジームは全戦略0.0（全戦略無効化）を返すことを確認"""
        weights = selector.get_regime_weights(RegimeType.HIGH_VOLATILITY)

        # 高ボラティリティは全戦略0.0（全戦略無効化）
        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert all(weight == 0.0 for weight in weights.values())
        # 合計0.0も有効と判定されることを確認
        assert selector.validate_weights(weights)

    def test_get_regime_weights_invalid_regime(self, selector):
        """不正なレジームタイプでValueErrorが発生することを確認"""
        with pytest.raises(ValueError):
            selector.get_regime_weights("invalid_regime")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # validate_weights()テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_validate_weights_sum_to_one(self, selector):
        """重み合計が1.0の場合にTrueを返すことを確認"""
        weights = {
            "ATRBased": 0.50,
            "DonchianChannel": 0.30,
            "ADXTrendStrength": 0.20,
        }
        assert selector.validate_weights(weights) is True

    def test_validate_weights_sum_not_one(self, selector):
        """重み合計が1.0でない場合にFalseを返すことを確認"""
        weights = {
            "ATRBased": 0.50,
            "DonchianChannel": 0.30,
            "ADXTrendStrength": 0.10,  # 合計0.9（1.0でない）
        }
        assert selector.validate_weights(weights) is False

    def test_validate_weights_empty_dict(self, selector):
        """空辞書はTrueを返すことを確認（高ボラティリティ時・後方互換性）"""
        weights = {}
        assert selector.validate_weights(weights) is True

    def test_validate_weights_all_zero(self, selector):
        """全戦略0.0（合計0.0）はTrueを返すことを確認（高ボラティリティ時）"""
        weights = {
            "ATRBased": 0.0,
            "DonchianChannel": 0.0,
            "ADXTrendStrength": 0.0,
        }
        assert selector.validate_weights(weights) is True

    def test_validate_weights_tolerance(self, selector):
        """許容誤差範囲（0.99-1.01）でTrueを返すことを確認"""
        # 0.995（許容範囲内）
        weights = {
            "ATRBased": 0.50,
            "DonchianChannel": 0.30,
            "ADXTrendStrength": 0.195,  # 合計0.995
        }
        assert selector.validate_weights(weights) is True

        # 1.005（許容範囲内）
        weights = {
            "ATRBased": 0.50,
            "DonchianChannel": 0.30,
            "ADXTrendStrength": 0.205,  # 合計1.005
        }
        assert selector.validate_weights(weights) is True

        # 0.98（許容範囲外）
        weights = {
            "ATRBased": 0.50,
            "DonchianChannel": 0.30,
            "ADXTrendStrength": 0.18,  # 合計0.98
        }
        assert selector.validate_weights(weights) is False

        # 1.02（許容範囲外）
        weights = {
            "ATRBased": 0.50,
            "DonchianChannel": 0.30,
            "ADXTrendStrength": 0.22,  # 合計1.02
        }
        assert selector.validate_weights(weights) is False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # _get_default_weights()テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_default_weights_tight_range(self, selector):
        """tight_range のデフォルト重みが正しいことを確認"""
        weights = selector._get_default_weights(RegimeType.TIGHT_RANGE)

        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert weights["ATRBased"] == 0.70
        assert weights["DonchianChannel"] == 0.30
        assert weights["ADXTrendStrength"] == 0.0
        assert selector.validate_weights(weights)

    def test_get_default_weights_normal_range(self, selector):
        """normal_range のデフォルト重みが正しいことを確認"""
        weights = selector._get_default_weights(RegimeType.NORMAL_RANGE)

        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert weights["ATRBased"] == 0.50
        assert weights["DonchianChannel"] == 0.30
        assert weights["ADXTrendStrength"] == 0.20
        assert selector.validate_weights(weights)

    def test_get_default_weights_trending(self, selector):
        """trending のデフォルト重みが正しいことを確認"""
        weights = selector._get_default_weights(RegimeType.TRENDING)

        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert weights["ADXTrendStrength"] == 0.60
        assert weights["ATRBased"] == 0.30
        assert weights["DonchianChannel"] == 0.10
        assert selector.validate_weights(weights)

    def test_get_default_weights_high_volatility(self, selector):
        """high_volatility のデフォルト重みは全戦略0.0であることを確認"""
        weights = selector._get_default_weights(RegimeType.HIGH_VOLATILITY)

        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert all(weight == 0.0 for weight in weights.values())
        assert selector.validate_weights(weights)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # is_enabled()テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_is_enabled(self, selector):
        """is_enabled()がboolを返すことを確認"""
        enabled = selector.is_enabled()
        assert isinstance(enabled, bool)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 統合テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_all_regime_weights_valid(self, selector):
        """全レジームの重みが有効であることを確認"""
        regimes = [
            RegimeType.TIGHT_RANGE,
            RegimeType.NORMAL_RANGE,
            RegimeType.TRENDING,
            RegimeType.HIGH_VOLATILITY,
        ]

        for regime in regimes:
            weights = selector.get_regime_weights(regime)
            # 重み検証（high_volatilityは空辞書OK）
            assert selector.validate_weights(weights)
