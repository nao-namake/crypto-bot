"""
ランタイムフラグのテスト - Phase 64.13

runtime_flags.pyの全関数をカバーするテスト。
"""

import pytest

from src.core.config.runtime_flags import (
    get_backtest_log_level,
    is_backtest_mode,
    set_backtest_log_level,
    set_backtest_mode,
)


class TestRuntimeFlags:
    """ランタイムフラグのテストクラス"""

    def setup_method(self):
        """各テスト前にフラグをリセット"""
        set_backtest_mode(False)
        set_backtest_log_level("WARNING")

    def teardown_method(self):
        """各テスト後にフラグをリセット"""
        set_backtest_mode(False)
        set_backtest_log_level("WARNING")

    def test_set_backtest_mode_true(self):
        """バックテストモード有効化テスト"""
        set_backtest_mode(True)
        assert is_backtest_mode() is True

    def test_set_backtest_mode_false(self):
        """バックテストモード無効化テスト"""
        set_backtest_mode(True)
        set_backtest_mode(False)
        assert is_backtest_mode() is False

    def test_is_backtest_mode_default(self):
        """バックテストモードのデフォルト値テスト"""
        assert is_backtest_mode() is False

    def test_set_backtest_log_level(self):
        """バックテストログレベル設定テスト"""
        set_backtest_log_level("DEBUG")
        assert get_backtest_log_level() == "DEBUG"

    def test_set_backtest_log_level_lowercase(self):
        """バックテストログレベル小文字入力テスト"""
        set_backtest_log_level("info")
        assert get_backtest_log_level() == "INFO"

    def test_get_backtest_log_level_default(self):
        """バックテストログレベルのデフォルト値テスト"""
        assert get_backtest_log_level() == "WARNING"
