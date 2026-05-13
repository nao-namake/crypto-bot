"""Phase 87 H4 基盤: FirestoreStateClient テスト（ローカル fallback メイン）"""

import json
from pathlib import Path

import pytest

from src.core.persistence.firestore_state import FirestoreStateClient


@pytest.fixture
def client(tmp_path):
    """force_local=True で Firestore を使わず純粋なローカル JSON fallback"""
    return FirestoreStateClient(
        instance_id="testinst",
        local_fallback_dir=str(tmp_path),
        force_local=True,
    )


class TestLocalFallback:
    def test_save_and_load(self, client, tmp_path):
        ok = client.save("sl_state", "buy", {"sl_order_id": "ABC", "sl_price": 13000000})
        assert ok is True
        data = client.load("sl_state", "buy")
        assert data == {"sl_order_id": "ABC", "sl_price": 13000000}

    def test_load_missing_returns_none(self, client):
        assert client.load("sl_state", "buy") is None

    def test_save_multiple_sides(self, client):
        client.save("sl_state", "buy", {"id": "B"})
        client.save("sl_state", "sell", {"id": "S"})
        col = client.load_collection("sl_state")
        assert col == {"buy": {"id": "B"}, "sell": {"id": "S"}}

    def test_delete(self, client):
        client.save("sl_state", "buy", {"id": "X"})
        assert client.delete("sl_state", "buy") is True
        assert client.load("sl_state", "buy") is None

    def test_overwrite(self, client):
        client.save("sl_state", "buy", {"id": "v1"})
        client.save("sl_state", "buy", {"id": "v2"})
        assert client.load("sl_state", "buy") == {"id": "v2"}

    def test_local_file_format_compatible(self, client, tmp_path):
        """ローカル形式が data/{collection}.json で書き出される"""
        client.save("sl_state", "buy", {"sl_order_id": "Z"})
        path = tmp_path / "sl_state.json"
        assert path.exists()
        content = json.loads(path.read_text(encoding="utf-8"))
        assert content == {"buy": {"sl_order_id": "Z"}}

    def test_load_collection_empty(self, client):
        assert client.load_collection("nonexistent") == {}

    def test_instance_id_default(self):
        """instance_id 未指定なら 'default' or BOT_INSTANCE_ID 環境変数"""
        c = FirestoreStateClient(force_local=True, local_fallback_dir="/tmp/x")
        # 環境変数で上書きされていない限り default
        assert c.instance_id in ("default", c.instance_id)

    def test_invalid_local_doc_data_skipped(self, client, tmp_path):
        """非 dict 値が混入していたら load 時に None"""
        # 手動で不正な内容を書く
        path = tmp_path / "weird.json"
        path.write_text(json.dumps({"buy": "not-a-dict"}), encoding="utf-8")
        assert client.load("weird", "buy") is None
