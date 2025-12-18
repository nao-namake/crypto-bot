"""
ランタイムフラグのテスト - Phase 54.10

runtime_flags.pyの全関数をカバーするテスト。
"""

import pytest

from src.core.config.runtime_flags import (
    get_all_flags,
    get_backtest_log_level,
    is_backtest_mode,
    is_paper_mode,
    reset_all_flags,
    set_backtest_log_level,
    set_backtest_mode,
    set_paper_mode,
)


class TestRuntimeFlags:
    """ランタイムフラグのテストクラス"""

    def setup_method(self):
        """各テスト前にフラグをリセット"""
        reset_all_flags()

    def teardown_method(self):
        """各テスト後にフラグをリセット"""
        reset_all_flags()

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

    def test_set_paper_mode_true(self):
        """ペーパーモード有効化テスト"""
        set_paper_mode(True)
        assert is_paper_mode() is True

    def test_set_paper_mode_false(self):
        """ペーパーモード無効化テスト"""
        set_paper_mode(True)
        set_paper_mode(False)
        assert is_paper_mode() is False

    def test_is_paper_mode_default(self):
        """ペーパーモードのデフォルト値テスト"""
        assert is_paper_mode() is False

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

    def test_reset_all_flags(self):
        """全フラグリセットテスト"""
        set_backtest_mode(True)
        set_paper_mode(True)
        set_backtest_log_level("DEBUG")

        reset_all_flags()

        assert is_backtest_mode() is False
        assert is_paper_mode() is False
        assert get_backtest_log_level() == "WARNING"

    def test_get_all_flags(self):
        """全フラグ取得テスト"""
        set_backtest_mode(True)
        set_paper_mode(True)
        set_backtest_log_level("ERROR")

        flags = get_all_flags()

        assert flags["backtest_mode"] is True
        assert flags["paper_mode"] is True
        assert flags["backtest_log_level"] == "ERROR"

    def test_get_all_flags_returns_copy(self):
        """get_all_flagsがコピーを返すことを確認"""
        flags = get_all_flags()
        flags["backtest_mode"] = True

        # 元のフラグは変更されていないことを確認
        assert is_backtest_mode() is False
