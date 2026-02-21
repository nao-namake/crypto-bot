"""
市場レジーム分類定義

市場状況を4段階に分類するEnum定義。
レンジ型bot最適化のための市場状況分類システム。
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
    """トレンド相場（ADX > 25）- ADXTrendStrength重視"""

    HIGH_VOLATILITY = "high_volatility"
    """高ボラティリティ（ATR比 > 1.8%・4時間足）- 全戦略ディスエーブル（待機）"""

    def __str__(self) -> str:
        """文字列表現を返す"""
        return self.value
