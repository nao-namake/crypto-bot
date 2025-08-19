"""
Configuration state management utilities
"""

from typing import Any, Dict, Optional

# グローバル設定ストレージ
_current_config: Optional[Dict[str, Any]] = None


def set_current_config(config: Dict[str, Any]):
    """
    現在の設定を保存（Phase H.22.3: ATR期間統一用）

    Args:
        config: 保存する設定辞書
    """
    global _current_config
    _current_config = config


def get_current_config() -> Optional[Dict[str, Any]]:
    """
    現在の設定を取得（Phase H.22.3: ATR期間統一用）

    Returns:
        保存されている設定辞書、または None
    """
    return _current_config
