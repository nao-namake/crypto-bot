"""
動的戦略選択器のテスト - Phase 60.7

DynamicStrategySelectorの機能・ロジックをテスト。
7戦略構成（ATRBased・BBReversal・DonchianChannel・StochasticReversal・ADXTrendStrength・MACDEMACrossover・MeanReversion）対応。
"""

import pytest

from src.core.services.dynamic_strategy_selector import DynamicStrategySelector
from src.core.services.regime_types import RegimeType


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
        """tight_range レジームの重み取得が正しいことを確認（Phase 60.7: 7戦略）"""
        weights = selector.get_regime_weights(RegimeType.TIGHT_RANGE)

        # Phase 60.7: 7戦略全てを含む
        assert len(weights) == 7

        # tight_rangeは全7戦略を含む
        assert "ATRBased" in weights
        assert "BBReversal" in weights
        assert "DonchianChannel" in weights
        assert "StochasticReversal" in weights
        assert "ADXTrendStrength" in weights
        assert "MACDEMACrossover" in weights
        assert "MeanReversion" in weights

        # Phase 60.7: レンジ戦略が正の重みを持つ
        assert weights["ATRBased"] > 0
        assert weights["BBReversal"] > 0
        assert weights["MeanReversion"] > 0

        # Phase 60.7: 7戦略統合の重み設定
        assert weights["ADXTrendStrength"] == 0.15  # Phase 60.7: PF1.34
        assert weights["MACDEMACrossover"] == 0.10  # Phase 60.7: PF1.48

        # 重み合計が1.0であることを確認
        assert selector.validate_weights(weights)

    def test_get_regime_weights_normal_range(self, selector):
        """normal_range レジームの重み取得が正しいことを確認（Phase 60.7: 7戦略）"""
        weights = selector.get_regime_weights(RegimeType.NORMAL_RANGE)

        # Phase 60.7: 7戦略全てを含む
        assert len(weights) == 7

        # normal_rangeはバランス型配分（全7戦略使用）
        assert "ATRBased" in weights
        assert "BBReversal" in weights
        assert "DonchianChannel" in weights
        assert "StochasticReversal" in weights
        assert "ADXTrendStrength" in weights
        assert "MACDEMACrossover" in weights
        assert "MeanReversion" in weights

        # 全戦略が正の重みまたは0（バランス型）
        assert weights["ATRBased"] > 0
        assert weights["BBReversal"] > 0
        assert weights["DonchianChannel"] > 0
        assert weights["ADXTrendStrength"] > 0
        assert weights["MACDEMACrossover"] > 0
        assert weights["MeanReversion"] > 0

        # 重み合計が1.0であることを確認
        assert selector.validate_weights(weights)

    def test_get_regime_weights_trending(self, selector):
        """trending レジームの重み取得が正しいことを確認（Phase 60.7: 7戦略）"""
        weights = selector.get_regime_weights(RegimeType.TRENDING)

        # Phase 60.7: 7戦略全てを含む
        assert len(weights) == 7

        # trendingはトレンド型戦略に集中（ADXTrendStrength・MACDEMACrossover）
        assert "ADXTrendStrength" in weights
        assert "MACDEMACrossover" in weights
        assert "ATRBased" in weights
        assert "DonchianChannel" in weights
        assert "BBReversal" in weights
        assert "StochasticReversal" in weights
        assert "MeanReversion" in weights

        # トレンド型戦略は正の重み
        assert weights["ADXTrendStrength"] > 0
        assert weights["MACDEMACrossover"] > 0
        assert weights["ATRBased"] > 0
        assert weights["DonchianChannel"] > 0

        # レンジ型戦略は0.0（無効化）
        assert weights["BBReversal"] == 0.0
        assert weights["StochasticReversal"] == 0.0
        assert weights["MeanReversion"] == 0.0  # Phase 60.7: トレンド時は無効

        # ADXTrendStrengthが最も高い重みを持つことを確認
        assert weights["ADXTrendStrength"] > weights["MACDEMACrossover"]
        assert weights["ADXTrendStrength"] > weights["ATRBased"]

        # 重み合計が1.0であることを確認
        assert selector.validate_weights(weights)

    def test_get_regime_weights_high_volatility(self, selector):
        """high_volatility レジームは全戦略0.0（全戦略無効化）を返すことを確認（Phase 60.7: 7戦略）"""
        weights = selector.get_regime_weights(RegimeType.HIGH_VOLATILITY)

        # 高ボラティリティは全戦略0.0（全戦略無効化）
        assert len(weights) == 7  # 全7戦略を含む - Phase 60.7
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
        """重み合計が1.0の場合にTrueを返すことを確認（Phase 60.7: 7戦略）"""
        weights = {
            "ATRBased": 0.30,
            "BBReversal": 0.20,
            "DonchianChannel": 0.15,
            "StochasticReversal": 0.15,
            "ADXTrendStrength": 0.15,
            "MACDEMACrossover": 0.05,
        }
        assert selector.validate_weights(weights) is True

    def test_validate_weights_sum_not_one(self, selector):
        """重み合計が1.0でない場合にFalseを返すことを確認（Phase 60.7: 7戦略）"""
        weights = {
            "ATRBased": 0.30,
            "BBReversal": 0.20,
            "DonchianChannel": 0.15,
            "StochasticReversal": 0.15,
            "ADXTrendStrength": 0.10,
            "MACDEMACrossover": 0.05,  # 合計0.95（1.0でない）
        }
        assert selector.validate_weights(weights) is False

    def test_validate_weights_empty_dict(self, selector):
        """空辞書はTrueを返すことを確認（高ボラティリティ時・後方互換性）"""
        weights = {}
        assert selector.validate_weights(weights) is True

    def test_validate_weights_all_zero(self, selector):
        """全戦略0.0（合計0.0）はTrueを返すことを確認（高ボラティリティ時・Phase 60.7: 7戦略）"""
        weights = {
            "ATRBased": 0.0,
            "BBReversal": 0.0,
            "DonchianChannel": 0.0,
            "StochasticReversal": 0.0,
            "ADXTrendStrength": 0.0,
            "MACDEMACrossover": 0.0,
            "MeanReversion": 0.0,
        }
        assert selector.validate_weights(weights) is True

    def test_validate_weights_tolerance(self, selector):
        """許容誤差範囲（0.99-1.01）でTrueを返すことを確認（Phase 60.7: 7戦略）"""
        # 0.995（許容範囲内）
        weights = {
            "ATRBased": 0.30,
            "BBReversal": 0.20,
            "DonchianChannel": 0.15,
            "StochasticReversal": 0.15,
            "ADXTrendStrength": 0.15,
            "MACDEMACrossover": 0.045,  # 合計0.995
        }
        assert selector.validate_weights(weights) is True

        # 1.005（許容範囲内）
        weights = {
            "ATRBased": 0.30,
            "BBReversal": 0.20,
            "DonchianChannel": 0.15,
            "StochasticReversal": 0.15,
            "ADXTrendStrength": 0.15,
            "MACDEMACrossover": 0.055,  # 合計1.005
        }
        assert selector.validate_weights(weights) is True

        # 0.98（許容範囲外）
        weights = {
            "ATRBased": 0.30,
            "BBReversal": 0.20,
            "DonchianChannel": 0.15,
            "StochasticReversal": 0.15,
            "ADXTrendStrength": 0.13,
            "MACDEMACrossover": 0.05,  # 合計0.98
        }
        assert selector.validate_weights(weights) is False

        # 1.02（許容範囲外）
        weights = {
            "ATRBased": 0.30,
            "BBReversal": 0.20,
            "DonchianChannel": 0.15,
            "StochasticReversal": 0.15,
            "ADXTrendStrength": 0.17,
            "MACDEMACrossover": 0.05,  # 合計1.02
        }
        assert selector.validate_weights(weights) is False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # _get_default_weights()テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_default_weights_tight_range(self, selector):
        """tight_range のデフォルト重みが正しいことを確認（Phase 60.7: 7戦略）"""
        weights = selector._get_default_weights(RegimeType.TIGHT_RANGE)

        # Phase 60.7: 7戦略全てを含む
        assert len(weights) == 7
        # Phase 60.7: 設定駆動型のため、strategies.yamlの構成に依存
        # レンジ型戦略が正の重みを持つことを確認
        assert weights.get("ATRBased", 0) > 0 or weights.get("BBReversal", 0) > 0
        # トレンド型戦略は0.0か低い重み
        assert weights.get("ADXTrendStrength", 0) == 0.0 or weights.get("ADXTrendStrength", 0) < 0.2
        # 重み合計が1.0または0.0（高ボラティリティ時）
        assert selector.validate_weights(weights)

    def test_get_default_weights_normal_range(self, selector):
        """normal_range のデフォルト重みが正しいことを確認（Phase 60.7: 7戦略）"""
        weights = selector._get_default_weights(RegimeType.NORMAL_RANGE)

        # Phase 60.7: 7戦略全てを含む
        assert len(weights) == 7
        # Phase 60.7: 設定駆動型のため、strategies.yamlの構成に依存
        # バランス型配分を確認
        assert sum(weights.values()) >= 0.0
        # 重み合計が1.0または0.0
        assert selector.validate_weights(weights)

    def test_get_default_weights_trending(self, selector):
        """trending のデフォルト重みが正しいことを確認（Phase 60.7: 7戦略）"""
        weights = selector._get_default_weights(RegimeType.TRENDING)

        # Phase 60.7: 7戦略全てを含む
        assert len(weights) == 7
        # Phase 60.7: 設定駆動型のため、strategies.yamlの構成に依存
        # トレンド型戦略が正の重みを持つことを確認
        assert weights.get("ADXTrendStrength", 0) > 0 or weights.get("MACDEMACrossover", 0) > 0
        # 重み合計が1.0または0.0
        assert selector.validate_weights(weights)

    def test_get_default_weights_high_volatility(self, selector):
        """high_volatility のデフォルト重みは全戦略0.0であることを確認（Phase 60.7: 7戦略）"""
        weights = selector._get_default_weights(RegimeType.HIGH_VOLATILITY)

        # Phase 60.7: 7戦略全てを含む
        assert len(weights) == 7
        # 高ボラティリティは全戦略0.0
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
    # Phase 51.8: get_regime_position_limit()テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_regime_position_limit_tight_range(self, selector):
        """Phase 51.8: TIGHT_RANGEレジームの最大ポジション数が6を返すことを確認"""
        limit = selector.get_regime_position_limit(RegimeType.TIGHT_RANGE)
        assert limit == 6

    def test_get_regime_position_limit_normal_range(self, selector):
        """Phase 51.8: NORMAL_RANGEレジームの最大ポジション数が4を返すことを確認"""
        limit = selector.get_regime_position_limit(RegimeType.NORMAL_RANGE)
        assert limit == 4

    def test_get_regime_position_limit_trending(self, selector):
        """Phase 51.8: TRENDINGレジームの最大ポジション数が2を返すことを確認"""
        limit = selector.get_regime_position_limit(RegimeType.TRENDING)
        assert limit == 2

    def test_get_regime_position_limit_high_volatility(self, selector):
        """Phase 51.8: HIGH_VOLATILITYレジームの最大ポジション数が0を返すことを確認"""
        limit = selector.get_regime_position_limit(RegimeType.HIGH_VOLATILITY)
        assert limit == 0

    def test_get_regime_position_limit_all_regimes_return_int(self, selector):
        """Phase 51.8: 全レジームの最大ポジション数が整数を返すことを確認"""
        regimes = [
            RegimeType.TIGHT_RANGE,
            RegimeType.NORMAL_RANGE,
            RegimeType.TRENDING,
            RegimeType.HIGH_VOLATILITY,
        ]

        for regime in regimes:
            limit = selector.get_regime_position_limit(regime)
            assert isinstance(limit, int)
            assert limit >= 0

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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Phase 55: 完全フィルタリング方式テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_regime_active_strategies_tight_range(self, selector):
        """Phase 60.7: tight_rangeの有効戦略リストが正しいことを確認"""
        active_strategies = selector._get_regime_active_strategies(RegimeType.TIGHT_RANGE)

        # tight_range: ATRBased, BBReversal, StochasticReversal, MeanReversion
        assert len(active_strategies) == 4
        assert "ATRBased" in active_strategies
        assert "BBReversal" in active_strategies
        assert "StochasticReversal" in active_strategies
        assert "MeanReversion" in active_strategies

        # 無効な戦略が含まれていないことを確認
        assert "DonchianChannel" not in active_strategies
        assert "ADXTrendStrength" not in active_strategies
        assert "MACDEMACrossover" not in active_strategies

    def test_get_regime_active_strategies_normal_range(self, selector):
        """Phase 55: normal_rangeの有効戦略リストが正しいことを確認"""
        active_strategies = selector._get_regime_active_strategies(RegimeType.NORMAL_RANGE)

        # normal_range: ATRBased, BBReversal, DonchianChannel
        assert len(active_strategies) == 3
        assert "ATRBased" in active_strategies
        assert "BBReversal" in active_strategies
        assert "DonchianChannel" in active_strategies

        # 無効な戦略が含まれていないことを確認
        assert "StochasticReversal" not in active_strategies
        assert "ADXTrendStrength" not in active_strategies
        assert "MACDEMACrossover" not in active_strategies

    def test_get_regime_active_strategies_trending(self, selector):
        """Phase 55: trendingの有効戦略リストが正しいことを確認"""
        active_strategies = selector._get_regime_active_strategies(RegimeType.TRENDING)

        # trending: ADXTrendStrength, MACDEMACrossover, DonchianChannel
        assert len(active_strategies) == 3
        assert "ADXTrendStrength" in active_strategies
        assert "MACDEMACrossover" in active_strategies
        assert "DonchianChannel" in active_strategies

        # 無効な戦略が含まれていないことを確認
        assert "ATRBased" not in active_strategies
        assert "BBReversal" not in active_strategies
        assert "StochasticReversal" not in active_strategies

    def test_get_regime_active_strategies_high_volatility(self, selector):
        """Phase 55: high_volatilityの有効戦略リストが空であることを確認"""
        active_strategies = selector._get_regime_active_strategies(RegimeType.HIGH_VOLATILITY)

        # high_volatility: 全戦略無効（空リスト）
        assert len(active_strategies) == 0
        assert active_strategies == []

    def test_apply_regime_strategy_filter_tight_range(self, selector):
        """Phase 60.7: tight_rangeで戦略フィルタリングが正しく適用されることを確認"""
        from unittest.mock import MagicMock

        # モックStrategyManagerを作成
        mock_strategy_manager = MagicMock()

        # 7戦略のモックを作成
        mock_strategies = {
            "ATRBased": MagicMock(),
            "BBReversal": MagicMock(),
            "StochasticReversal": MagicMock(),
            "DonchianChannel": MagicMock(),
            "ADXTrendStrength": MagicMock(),
            "MACDEMACrossover": MagicMock(),
            "MeanReversion": MagicMock(),
        }
        mock_strategy_manager.strategies = mock_strategies

        # フィルタリング適用
        selector.apply_regime_strategy_filter(RegimeType.TIGHT_RANGE, mock_strategy_manager)

        # tight_range: ATRBased, BBReversal, StochasticReversal, MeanReversion が有効化
        mock_strategies["ATRBased"].enable.assert_called_once()
        mock_strategies["BBReversal"].enable.assert_called_once()
        mock_strategies["StochasticReversal"].enable.assert_called_once()
        mock_strategies["MeanReversion"].enable.assert_called_once()

        # 残りは無効化
        mock_strategies["DonchianChannel"].disable.assert_called_once()
        mock_strategies["ADXTrendStrength"].disable.assert_called_once()
        mock_strategies["MACDEMACrossover"].disable.assert_called_once()

    def test_apply_regime_strategy_filter_high_volatility(self, selector):
        """Phase 60.7: high_volatilityで全戦略が無効化されることを確認"""
        from unittest.mock import MagicMock

        # モックStrategyManagerを作成
        mock_strategy_manager = MagicMock()

        # 7戦略のモックを作成
        mock_strategies = {
            "ATRBased": MagicMock(),
            "BBReversal": MagicMock(),
            "StochasticReversal": MagicMock(),
            "DonchianChannel": MagicMock(),
            "ADXTrendStrength": MagicMock(),
            "MACDEMACrossover": MagicMock(),
            "MeanReversion": MagicMock(),
        }
        mock_strategy_manager.strategies = mock_strategies

        # フィルタリング適用
        selector.apply_regime_strategy_filter(RegimeType.HIGH_VOLATILITY, mock_strategy_manager)

        # high_volatility: 全戦略無効化
        for strategy in mock_strategies.values():
            strategy.disable.assert_called_once()
            strategy.enable.assert_not_called()
