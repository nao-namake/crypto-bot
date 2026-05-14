"""
Phase 88 M5: 税務 SQLite を GCS で永続化。

設計:
- 起動時: gs://crypto-bot-tax-backup/trade_history.db → ローカル tax/trade_history.db
- 取引記録直後: ローカル → gs:// にアップロード（5 秒以内の SIGTERM に備える）
- atexit hook で念のためアップロード

無料枠（2026 年現在）:
- GCS Standard 5 GB/月 → 2 MB DB なら余裕
- 操作 5,000 リクエスト/月 → 1日30回起動でも 900/月、無料枠内

エラー処理方針:
- Firestore と同じく fail-safe: GCS 不通時もローカル SQLite は機能継続
- min_instances=0 環境では「次回起動時に古い state を read する」可能性に注意
  → record_trade() 直後の同期 backup でその窓を最小化
"""

from __future__ import annotations

import atexit
import os
import threading
from pathlib import Path
from typing import Optional

from src.core.logger import get_logger


class GCSTaxBackup:
    """税務 SQLite の GCS バックアップ機構。

    使い方:
        backup = GCSTaxBackup()
        backup.restore()                   # 起動時
        # ... record_trade(...) ...
        backup.backup()                    # 取引記録後 or 終了時
    """

    DEFAULT_BUCKET = "crypto-bot-tax-backup"
    DEFAULT_OBJECT_KEY = "trade_history.db"
    DEFAULT_LOCAL_PATH = "tax/trade_history.db"

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        object_key: Optional[str] = None,
        local_path: Optional[str] = None,
    ) -> None:
        self.logger = get_logger()
        self.bucket_name = bucket_name or os.environ.get(
            "TAX_GCS_BUCKET", self.DEFAULT_BUCKET
        )
        self.object_key = object_key or self.DEFAULT_OBJECT_KEY
        self.local_path = Path(local_path or self.DEFAULT_LOCAL_PATH)
        self._lock = threading.Lock()

        self.client = None
        self.bucket = None
        self.enabled = False

        try:
            from google.cloud import storage

            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
            self.enabled = True
            self.logger.info(
                f"✅ Phase 88 M5: GCSTaxBackup 初期化成功 "
                f"(bucket={self.bucket_name}, key={self.object_key})"
            )
        except Exception as e:
            # ImportError / DefaultCredentialsError / 権限不足 等を全て吸収
            self.logger.warning(
                f"⚠️ Phase 88 M5: GCS unavailable → ローカル SQLite のみで動作: {e}"
            )

    def restore(self) -> bool:
        """起動時: GCS の最新スナップショットでローカル DB を復元。

        Returns:
            True: 復元成功 / False: GCS 不通 or オブジェクト無し（新規起動）
        """
        if not self.enabled or self.bucket is None:
            return False
        try:
            blob = self.bucket.blob(self.object_key)
            if not blob.exists():
                self.logger.info(
                    f"📭 Phase 88 M5: GCS にスナップショット無し（新規起動扱い）: "
                    f"gs://{self.bucket_name}/{self.object_key}"
                )
                return False
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                blob.download_to_filename(str(self.local_path))
            size = self.local_path.stat().st_size
            self.logger.info(
                f"📥 Phase 88 M5: GCS → ローカル復元完了 "
                f"({size} bytes → {self.local_path})"
            )
            return True
        except Exception as e:
            self.logger.error(f"❌ Phase 88 M5: GCS restore 失敗: {e}")
            return False

    def backup(self) -> bool:
        """ローカル DB を GCS へアップロード。取引記録直後と終了時に呼ぶ。

        Returns:
            True: アップロード成功 / False: GCS 不通 or ローカル DB 無し
        """
        if not self.enabled or self.bucket is None:
            return False
        if not self.local_path.exists():
            return False
        try:
            blob = self.bucket.blob(self.object_key)
            with self._lock:
                blob.upload_from_filename(str(self.local_path))
            size = self.local_path.stat().st_size
            self.logger.debug(
                f"📤 Phase 88 M5: ローカル → GCS バックアップ完了 ({size} bytes)"
            )
            return True
        except Exception as e:
            self.logger.error(f"❌ Phase 88 M5: GCS backup 失敗: {e}")
            return False

    def register_atexit_backup(self) -> None:
        """プロセス終了時に念のためバックアップ実行する hook を登録。"""
        if not self.enabled:
            return

        def _on_exit():
            try:
                self.backup()
            except Exception:
                # atexit 中のエラーは無視（ログだけ残せれば十分）
                pass

        atexit.register(_on_exit)
