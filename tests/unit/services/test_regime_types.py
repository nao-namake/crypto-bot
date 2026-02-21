"""
市場レジームタイプのテスト - Phase 51.2-New

RegimeTypeの基本機能・ユーティリティメソッドをテスト。
"""

from src.core.services.regime_types import RegimeType


class TestRegimeType:
    """RegimeTypeのテストクラス"""

    def test_regime_type_values(self):
        """Enum値が正しいことを確認"""
        assert RegimeType.TIGHT_RANGE.value == "tight_range"
        assert RegimeType.NORMAL_RANGE.value == "normal_range"
        assert RegimeType.TRENDING.value == "trending"
        assert RegimeType.HIGH_VOLATILITY.value == "high_volatility"

    def test_regime_type_count(self):
        """Enum要素数が4つであることを確認"""
        assert len(RegimeType) == 4

    def test_str_representation(self):
        """__str__メソッドが正しく動作することを確認"""
        assert str(RegimeType.TIGHT_RANGE) == "tight_range"
        assert str(RegimeType.NORMAL_RANGE) == "normal_range"
        assert str(RegimeType.TRENDING) == "trending"
        assert str(RegimeType.HIGH_VOLATILITY) == "high_volatility"

    def test_enum_iteration(self):
        """Enumを反復処理できることを確認"""
        regimes = list(RegimeType)
        assert len(regimes) == 4
        assert RegimeType.TIGHT_RANGE in regimes
        assert RegimeType.NORMAL_RANGE in regimes
        assert RegimeType.TRENDING in regimes
        assert RegimeType.HIGH_VOLATILITY in regimes

    def test_enum_equality(self):
        """Enum要素が正しく比較できることを確認"""
        regime1 = RegimeType.TIGHT_RANGE
        regime2 = RegimeType.TIGHT_RANGE
        regime3 = RegimeType.NORMAL_RANGE

        assert regime1 == regime2
        assert regime1 != regime3
