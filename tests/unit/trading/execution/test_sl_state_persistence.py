"""Phase 68.4: SLStatePersistence テスト"""

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.trading.execution.sl_state_persistence import SLStatePersistence


@pytest.fixture
def tmp_state_path(tmp_path):
    return str(tmp_path / "sl_state.json")


@pytest.fixture
def persistence(tmp_state_path):
    return SLStatePersistence(state_path=tmp_state_path)


class TestSLStatePersistence:
    """SLStatePersistence基本テスト"""

    def test_save_and_load(self, persistence, tmp_state_path):
        """save→loadで正しく復元される"""
        persistence.save("buy", "12345", 10000000.0, 0.001)

        state = persistence.load()
        assert "buy" in state
        assert state["buy"]["sl_order_id"] == "12345"
        assert state["buy"]["sl_price"] == 10000000.0
        assert state["buy"]["amount"] == 0.001
        assert "saved_at" in state["buy"]

    def test_save_both_sides(self, persistence):
        """buy/sell両方保存可能"""
        persistence.save("buy", "111", 10000000.0, 0.001)
        persistence.save("sell", "222", 11000000.0, 0.002)

        state = persistence.load()
        assert state["buy"]["sl_order_id"] == "111"
        assert state["sell"]["sl_order_id"] == "222"

    def test_save_overwrites_same_side(self, persistence):
        """同じサイドの保存は上書き"""
        persistence.save("buy", "111", 10000000.0, 0.001)
        persistence.save("buy", "222", 10500000.0, 0.002)

        state = persistence.load()
        assert state["buy"]["sl_order_id"] == "222"
        assert state["buy"]["sl_price"] == 10500000.0

    def test_clear(self, persistence):
        """clearで指定サイドのみ削除"""
        persistence.save("buy", "111", 10000000.0, 0.001)
        persistence.save("sell", "222", 11000000.0, 0.002)

        persistence.clear("buy")

        state = persistence.load()
        assert "buy" not in state
        assert "sell" in state

    def test_clear_nonexistent(self, persistence):
        """存在しないサイドのclearはエラーなし"""
        persistence.clear("buy")  # Should not raise

    def test_load_empty(self, persistence):
        """ファイル未存在時は空dict"""
        state = persistence.load()
        assert state == {}

    def test_load_corrupted_file(self, persistence, tmp_state_path):
        """壊れたJSONファイルは空dict"""
        os.makedirs(os.path.dirname(tmp_state_path), exist_ok=True)
        with open(tmp_state_path, "w") as f:
            f.write("not json")

        state = persistence.load()
        assert state == {}

    def test_save_error_handling(self, tmp_path):
        """保存時のエラーハンドリング"""
        # 書き込み不可能なパスを指定
        persistence = SLStatePersistence(state_path="/nonexistent/deep/path/sl_state.json")
        # Should not raise, just log error
        persistence.save("buy", "123", 10000000.0, 0.001)

    def test_clear_error_handling(self, persistence):
        """クリア時のエラーハンドリング（write失敗）"""
        persistence.save("buy", "123", 10000000.0, 0.001)
        # Make state_path read-only dir to cause write error
        original_write = persistence._write
        persistence._write = MagicMock(side_effect=PermissionError("read-only"))
        # Should not raise, just log error
        persistence.clear("buy")
        persistence._write = original_write

    def test_verify_with_no_order_id_in_state(self, persistence):
        """sl_order_idがない状態データ"""
        # Write state without sl_order_id
        persistence._write({"buy": {"sl_price": 10000000.0}})
        mock_client = MagicMock()
        result = persistence.verify_with_api("buy", mock_client)
        assert result is None
        mock_client.fetch_order.assert_not_called()


class TestSLStatePersistenceVerifyWithAPI:
    """verify_with_api テスト"""

    def test_verify_valid_inactive_sl(self, persistence):
        """INACTIVE状態のSLはvalidと判定"""
        persistence.save("buy", "12345", 10000000.0, 0.001)

        mock_client = MagicMock()
        mock_client.fetch_order.return_value = {
            "id": "12345",
            "status": "INACTIVE",
            "type": "stop_limit",
        }

        result = persistence.verify_with_api("buy", mock_client)
        assert result == "12345"
        mock_client.fetch_order.assert_called_once_with("12345", "BTC/JPY")

    def test_verify_valid_open_sl(self, persistence):
        """open状態のSLもvalidと判定"""
        persistence.save("buy", "12345", 10000000.0, 0.001)

        mock_client = MagicMock()
        mock_client.fetch_order.return_value = {
            "id": "12345",
            "status": "open",
        }

        result = persistence.verify_with_api("buy", mock_client)
        assert result == "12345"

    def test_verify_canceled_sl(self, persistence):
        """canceled状態のSLは無効→クリア"""
        persistence.save("buy", "12345", 10000000.0, 0.001)

        mock_client = MagicMock()
        mock_client.fetch_order.return_value = {
            "id": "12345",
            "status": "canceled",
        }

        result = persistence.verify_with_api("buy", mock_client)
        assert result is None
        # クリアされたか確認
        state = persistence.load()
        assert "buy" not in state

    def test_verify_closed_sl(self, persistence):
        """closed状態のSL（約定済み）は無効→クリア"""
        persistence.save("buy", "12345", 10000000.0, 0.001)

        mock_client = MagicMock()
        mock_client.fetch_order.return_value = {
            "id": "12345",
            "status": "closed",
        }

        result = persistence.verify_with_api("buy", mock_client)
        assert result is None

    def test_verify_order_not_found(self, persistence):
        """注文が見つからない場合→クリア"""
        persistence.save("buy", "12345", 10000000.0, 0.001)

        mock_client = MagicMock()
        mock_client.fetch_order.side_effect = Exception("OrderNotFound")

        result = persistence.verify_with_api("buy", mock_client)
        assert result is None
        state = persistence.load()
        assert "buy" not in state

    def test_verify_no_saved_state(self, persistence):
        """保存データなしの場合→None"""
        mock_client = MagicMock()
        result = persistence.verify_with_api("buy", mock_client)
        assert result is None
        mock_client.fetch_order.assert_not_called()

    def test_verify_api_returns_none(self, persistence):
        """API がNoneを返した場合→クリア"""
        persistence.save("buy", "12345", 10000000.0, 0.001)

        mock_client = MagicMock()
        mock_client.fetch_order.return_value = None

        result = persistence.verify_with_api("buy", mock_client)
        assert result is None

    def test_verify_api_error_non_not_found(self, persistence):
        """OrderNotFound以外のAPIエラー→Noneだがクリアしない"""
        persistence.save("buy", "12345", 10000000.0, 0.001)

        mock_client = MagicMock()
        mock_client.fetch_order.side_effect = Exception("Network timeout")

        result = persistence.verify_with_api("buy", mock_client)
        assert result is None
        # クリアされない（一時エラーの可能性）
        state = persistence.load()
        assert "buy" in state

    def test_verify_unfilled_status(self, persistence):
        """unfilled状態のSLはvalidと判定"""
        persistence.save("sell", "99999", 11000000.0, 0.002)

        mock_client = MagicMock()
        mock_client.fetch_order.return_value = {
            "id": "99999",
            "status": "unfilled",
        }

        result = persistence.verify_with_api("sell", mock_client)
        assert result == "99999"
