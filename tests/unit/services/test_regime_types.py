"""
市場レジームタイプのテスト - Phase 51.2-New

RegimeTypeの基本機能・ユーティリティメソッドをテスト。
"""

import pytest

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

    def test_from_string_valid(self):
        """from_string()が正しい文字列で動作することを確認"""
        assert RegimeType.from_string("tight_range") == RegimeType.TIGHT_RANGE
        assert RegimeType.from_string("normal_range") == RegimeType.NORMAL_RANGE
        assert RegimeType.from_string("trending") == RegimeType.TRENDING
        assert RegimeType.from_string("high_volatility") == RegimeType.HIGH_VOLATILITY

    def test_from_string_invalid(self):
        """from_string()が不正な文字列でValueErrorを発生させることを確認"""
        with pytest.raises(ValueError, match="不正なレジームタイプ"):
            RegimeType.from_string("invalid_regime")

    def test_get_description(self):
        """get_description()が説明文を返すことを確認"""
        assert "狭いレンジ相場" in RegimeType.TIGHT_RANGE.get_description()
        assert "通常レンジ相場" in RegimeType.NORMAL_RANGE.get_description()
        assert "トレンド相場" in RegimeType.TRENDING.get_description()
        assert "高ボラティリティ" in RegimeType.HIGH_VOLATILITY.get_description()

    def test_is_range(self):
        """is_range()が正しくレンジ相場を判定することを確認"""
        # レンジ相場
        assert RegimeType.TIGHT_RANGE.is_range() is True
        assert RegimeType.NORMAL_RANGE.is_range() is True

        # レンジ相場以外
        assert RegimeType.TRENDING.is_range() is False
        assert RegimeType.HIGH_VOLATILITY.is_range() is False

    def test_is_high_risk(self):
        """is_high_risk()が正しく高リスクを判定することを確認"""
        # 高リスク
        assert RegimeType.HIGH_VOLATILITY.is_high_risk() is True

        # 高リスク以外
        assert RegimeType.TIGHT_RANGE.is_high_risk() is False
        assert RegimeType.NORMAL_RANGE.is_high_risk() is False
        assert RegimeType.TRENDING.is_high_risk() is False

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
