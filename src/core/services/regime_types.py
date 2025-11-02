"""
市場レジーム分類定義 - Phase 51.2-New

市場状況を4段階に分類するEnum定義。
レンジ型bot最適化のための市場状況分類システム。

Phase 51.2-New: 市場状況分類器実装
"""

from enum import Enum


class RegimeType(Enum):
    """
    市場レジーム分類

    市場状況を4つのタイプに分類し、各タイプに応じた
    戦略選択・ML統合を実現する。

    Attributes:
        TIGHT_RANGE: 狭いレンジ相場（< 2%変動）
        NORMAL_RANGE: 通常レンジ相場（2-5%変動）
        TRENDING: トレンド相場（ADX > 25）
        HIGH_VOLATILITY: 高ボラティリティ（ATR比 > 3%）
    """

    TIGHT_RANGE = "tight_range"
    """狭いレンジ相場（< 2%変動）- ATRBased戦略最重視（70%）"""

    NORMAL_RANGE = "normal_range"
    """通常レンジ相場（2-5%変動）- ATRBased+Donchian+ADXバランス型"""

    TRENDING = "trending"
    """トレンド相場（ADX > 25）- MultiTimeframe+Mochipoy重視"""

    HIGH_VOLATILITY = "high_volatility"
    """高ボラティリティ（ATR比 > 1.8%・4時間足）- 全戦略ディスエーブル（待機）"""

    def __str__(self) -> str:
        """文字列表現を返す"""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "RegimeType":
        """
        文字列からRegimeTypeを生成

        Args:
            value: レジーム名（"tight_range"等）

        Returns:
            RegimeType: 対応するRegimeType

        Raises:
            ValueError: 不正な文字列の場合
        """
        for regime in cls:
            if regime.value == value:
                return regime
        raise ValueError(f"不正なレジームタイプ: {value}")

    def get_description(self) -> str:
        """
        レジームの説明を取得

        Returns:
            str: レジームの説明
        """
        descriptions = {
            RegimeType.TIGHT_RANGE: "狭いレンジ相場（< 2%変動）- 戦略重視",
            RegimeType.NORMAL_RANGE: "通常レンジ相場（2-5%変動）- バランス型",
            RegimeType.TRENDING: "トレンド相場（ADX > 25）- ML補完重視",
            RegimeType.HIGH_VOLATILITY: "高ボラティリティ（ATR比 > 1.8%・4時間足）- 待機",
        }
        return descriptions.get(self, "Unknown")

    def is_range(self) -> bool:
        """
        レンジ相場かどうかを判定

        Returns:
            bool: レンジ相場の場合True
        """
        return self in (RegimeType.TIGHT_RANGE, RegimeType.NORMAL_RANGE)

    def is_high_risk(self) -> bool:
        """
        高リスク状況かどうかを判定

        Returns:
            bool: 高リスク（高ボラ）の場合True
        """
        return self == RegimeType.HIGH_VOLATILITY
