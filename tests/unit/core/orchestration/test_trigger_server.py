"""
Phase 90γ-⑨: trigger_server._verify_firestore_io のテスト

Phase 88 I3 で Cloud Scheduler 駆動 FastAPI アプリを導入したが、Firestore I/O
検証関数 `_verify_firestore_io` には直接テストが無かった。Phase 90γ-⑦ で
`pragma: no cover` を解除して WARNING ログ追加したのを機にテストカバレッジを整備する。
"""

from unittest.mock import MagicMock

import pytest

from src.core.orchestration.trigger_server import _verify_firestore_io


@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.warning = MagicMock()
    logger.info = MagicMock()
    return logger


@pytest.fixture
def mock_fs_enabled():
    fs = MagicMock()
    fs.enabled = True
    return fs


class TestPhase90GammaTriggerServer:
    """Phase 90γ-⑨: _verify_firestore_io の正常系・異常系・後始末ログ"""

    def test_returns_false_when_client_disabled(self, mock_logger):
        """fs_client.enabled=False のとき (False, 'firestore_client_disabled') を返す"""
        fs = MagicMock()
        fs.enabled = False

        ok, reason = _verify_firestore_io(fs, mock_logger)

        assert ok is False
        assert reason == "firestore_client_disabled"
        # 早期 return なので save/load/delete は呼ばれない
        fs.save.assert_not_called()

    def test_returns_false_when_save_fails(self, mock_fs_enabled, mock_logger):
        """fs_client.save が False を返したとき (False, 'firestore_save_failed')"""
        mock_fs_enabled.save.return_value = False

        ok, reason = _verify_firestore_io(mock_fs_enabled, mock_logger)

        assert ok is False
        assert reason == "firestore_save_failed"
        # save 失敗で load も delete も呼ばれない
        mock_fs_enabled.load.assert_not_called()
        mock_fs_enabled.delete.assert_not_called()

    def test_returns_false_when_load_mismatch(self, mock_fs_enabled, mock_logger):
        """fs_client.load が不正な形式を返したとき (False, 'firestore_load_mismatch')"""
        mock_fs_enabled.save.return_value = True
        mock_fs_enabled.load.return_value = None  # dict でない・"ts" なし

        ok, reason = _verify_firestore_io(mock_fs_enabled, mock_logger)

        assert ok is False
        assert reason == "firestore_load_mismatch"

    def test_returns_true_on_full_roundtrip_success(self, mock_fs_enabled, mock_logger):
        """save/load/delete 全成功で (True, None) を返す"""
        mock_fs_enabled.save.return_value = True
        mock_fs_enabled.load.return_value = {"ts": 1234567.0, "src": "test"}
        # delete も成功するパス
        mock_fs_enabled.delete.return_value = True

        ok, reason = _verify_firestore_io(mock_fs_enabled, mock_logger)

        assert ok is True
        assert reason is None
        # 後始末の WARNING は出ない
        mock_logger.warning.assert_not_called()

    def test_delete_exception_emits_warning_but_returns_true(self, mock_fs_enabled, mock_logger):
        """Phase 90γ-⑦: delete 例外時に WARNING ログを出すが (True, None) を返す（無害扱い）"""
        mock_fs_enabled.save.return_value = True
        mock_fs_enabled.load.return_value = {"ts": 1234.0}
        mock_fs_enabled.delete.side_effect = ConnectionError("network glitch")

        ok, reason = _verify_firestore_io(mock_fs_enabled, mock_logger)

        # delete 失敗は無害なので True を返す
        assert ok is True
        assert reason is None
        # Phase 90γ-⑦ で追加した WARNING が出ている
        mock_logger.warning.assert_called_once()
        warning_msg = str(mock_logger.warning.call_args.args[0])
        assert "Phase 90γ-⑦" in warning_msg
        assert "Firestore health_check ping 削除失敗" in warning_msg
        assert "ConnectionError" in warning_msg

    def test_save_raises_exception_returns_io_exception_reason(self, mock_fs_enabled, mock_logger):
        """save 自体が例外を投げると外側 except に到達して 'firestore_io_exception:*'"""
        mock_fs_enabled.save.side_effect = RuntimeError("transport error")

        ok, reason = _verify_firestore_io(mock_fs_enabled, mock_logger)

        assert ok is False
        assert reason is not None
        assert reason.startswith("firestore_io_exception:")
        assert "RuntimeError" in reason
        # Phase R-Mb 既存 WARNING が出ている
        warning_msgs = [str(c.args[0]) for c in mock_logger.warning.call_args_list]
        assert any("Phase R-Mb" in m for m in warning_msgs)
