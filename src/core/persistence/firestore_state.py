"""Firestore-backed key-value state store - Phase 87 Stage 2 / H4-5 基盤

Cloud Run ephemeral FS 問題（Container 再起動で `data/*.json` が消失）を解決する。

Firestore パス: `bot_state/{instance_id}/{collection}/{doc_id}`
- `instance_id`: 環境変数 `BOT_INSTANCE_ID`（デフォルト "default"）
- 例: `bot_state/default/sl_state/buy` / `bot_state/default/drawdown_state/main` /
       `bot_state/default/ml_health/main`

フォールバック設計:
- `google-cloud-firestore` 未インストール / Firestore 不通 → ローカル JSON へ自動切替
- ローカル形式は `data/{collection}.json` で既存 `sl_state.json` と互換
- テスト / オフライン開発 / GCP 設定ミス時の安全策

無料枠（2026 年現在）:
- 1 GiB ストレージ / 20K write/day / 50K read/day（10件ポジションなら余裕で 576 write/day）
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from ..logger import get_logger


class FirestoreStateClient:
    """Firestore（Native モード）への CRUD ラッパー。

    使い方:
        client = FirestoreStateClient()
        client.save("sl_state", "buy", {"sl_order_id": "123", "sl_price": 13900000})
        state = client.load("sl_state", "buy")  # -> {...} or None
        client.delete("sl_state", "buy")
    """

    DEFAULT_INSTANCE_ID = "default"
    LOCAL_FALLBACK_DIR = "data"

    def __init__(
        self,
        instance_id: Optional[str] = None,
        local_fallback_dir: Optional[str] = None,
        force_local: bool = False,
    ) -> None:
        """
        Args:
            instance_id: Firestore のドキュメントスコープ。複数インスタンス分離用。
            local_fallback_dir: Firestore 不通時のローカル JSON 保存先。
            force_local: True なら Firestore を試さずローカル JSON のみ使用（テスト用）。
        """
        self.logger = get_logger()
        self.instance_id = instance_id or os.getenv("BOT_INSTANCE_ID", self.DEFAULT_INSTANCE_ID)
        self.local_dir = Path(local_fallback_dir or self.LOCAL_FALLBACK_DIR)
        self._lock = threading.Lock()  # ローカル JSON 並列書き込み保護
        self.db: Any = None
        self.enabled = False

        if force_local:
            self.logger.debug("Phase 87 H4: FirestoreStateClient (force_local=True)")
            return

        try:
            from google.cloud import firestore

            self.db = firestore.Client()
            self.enabled = True
            self.logger.info(
                f"✅ Phase 87 H4: FirestoreStateClient 初期化成功 "
                f"(instance_id={self.instance_id})"
            )
        except Exception as e:
            # ImportError / DefaultCredentialsError / Firestore 不通 全て吸収
            self.logger.warning(
                f"⚠️ Phase 87 H4: Firestore unavailable → ローカル JSON フォールバック: {e}"
            )

    # ========================================
    # Public API
    # ========================================

    def save(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """state を永続化する。

        Returns:
            bool: Firestore 書込成功 True / ローカル JSON 書込のみ False / 完全失敗 None。
                  実用上は「成功:True / 失敗または fallback:False」の扱いで十分。
        """
        if self.enabled:
            try:
                self._firestore_doc(collection, doc_id).set(data)
                return True
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Phase 87 H4: Firestore save failed ({collection}/{doc_id}): {e}"
                    " → ローカルへフォールバック"
                )
        # フォールバック / 無効時
        return self._save_local(collection, doc_id, data)

    def load(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """state を読み込む。

        Returns:
            Dict: 存在すれば内容、無ければ None。
        """
        if self.enabled:
            try:
                snap = self._firestore_doc(collection, doc_id).get()
                if snap.exists:
                    data = snap.to_dict()
                    return data if isinstance(data, dict) else None
                return None
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Phase 87 H4: Firestore load failed ({collection}/{doc_id}): {e}"
                    " → ローカルへフォールバック"
                )
        return self._load_local(collection, doc_id)

    def delete(self, collection: str, doc_id: str) -> bool:
        if self.enabled:
            try:
                self._firestore_doc(collection, doc_id).delete()
                return True
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Phase 87 H4: Firestore delete failed "
                    f"({collection}/{doc_id}): {e} → ローカルへフォールバック"
                )
        return self._delete_local(collection, doc_id)

    def load_collection(self, collection: str) -> Dict[str, Dict[str, Any]]:
        """コレクション全体（doc_id → data のマップ）を取得する。

        SLStatePersistence など「サイド別」マップ形式と互換にするため。
        """
        if self.enabled:
            try:
                docs = self._firestore_collection(collection).stream()
                return {d.id: d.to_dict() for d in docs if d.to_dict()}
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Phase 87 H4: Firestore load_collection failed "
                    f"({collection}): {e} → ローカルへフォールバック"
                )
        return self._load_collection_local(collection)

    # ========================================
    # Firestore helpers
    # ========================================

    def _firestore_doc(self, collection: str, doc_id: str) -> Any:
        # bot_state/{instance_id}/{collection}/{doc_id}
        return (
            self.db.collection("bot_state")
            .document(self.instance_id)
            .collection(collection)
            .document(doc_id)
        )

    def _firestore_collection(self, collection: str) -> Any:
        return self.db.collection("bot_state").document(self.instance_id).collection(collection)

    # ========================================
    # Local JSON fallback
    # ========================================

    def _local_path(self, collection: str) -> Path:
        """ローカル fallback ファイルパス: data/{collection}.json"""
        return self.local_dir / f"{collection}.json"

    def _read_local_collection(self, collection: str) -> Dict[str, Any]:
        path = self._local_path(collection)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError) as e:
            self.logger.warning(f"⚠️ Phase 87 H4: local JSON read error ({path}): {e}")
            return {}

    def _write_local_collection(self, collection: str, state: Dict[str, Any]) -> bool:
        path = self._local_path(collection)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except OSError as e:
            self.logger.error(f"❌ Phase 87 H4: local JSON write error ({path}): {e}")
            return False

    def _save_local(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        with self._lock:
            state = self._read_local_collection(collection)
            state[doc_id] = data
            return self._write_local_collection(collection, state)

    def _load_local(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            state = self._read_local_collection(collection)
            entry = state.get(doc_id)
            return entry if isinstance(entry, dict) else None

    def _delete_local(self, collection: str, doc_id: str) -> bool:
        with self._lock:
            state = self._read_local_collection(collection)
            state.pop(doc_id, None)
            return self._write_local_collection(collection, state)

    def _load_collection_local(self, collection: str) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            state = self._read_local_collection(collection)
            return {k: v for k, v in state.items() if isinstance(v, dict)}
