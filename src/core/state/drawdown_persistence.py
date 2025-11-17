"""
ドローダウン状態永続化システム - Phase 52.4完了

ローカルファイルとCloud Storageの両方に対応した
統一的な永続化インターフェースを提供。
GCP/ローカル環境の自動判定により適切な実装を選択。
モード別（paper/live/backtest）状態分離による安全性確保。

Phase 52.4: 設定ファイル統合・ハードコード削除
- unified.yamlからパステンプレート取得（local_path_template/gcs_path_template）
- get_config()パターン適用によるハードコード値削除

Phase 49完了:
- 統一永続化インターフェース（DrawdownPersistence基底クラス）
- ローカルファイル実装（LocalFilePersistence・JSON保存）
- Cloud Storage実装（CloudStoragePersistence・GCSバケット保存）
- 環境自動判定（create_persistence・GCP/ローカル環境判別）
- モード別完全分離（paper/live/backtest独立状態ファイル）

Phase 28-29: 永続化インターフェース統一・GCP/ローカル環境対応・モード別分離実装
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ...core.logger import get_logger
from ..config import get_config


class DrawdownPersistence(ABC):
    """ドローダウン状態永続化基底クラス"""

    def __init__(self):
        self.logger = get_logger()

    @abstractmethod
    async def save_state(self, state: Dict[str, Any]) -> bool:
        """
        状態保存

        Args:
            state: 保存する状態データ

        Returns:
            保存成功フラグ
        """
        pass

    @abstractmethod
    async def load_state(self) -> Optional[Dict[str, Any]]:
        """
        状態読み込み

        Returns:
            読み込んだ状態データ（失敗時はNone）
        """
        pass

    @abstractmethod
    async def backup_state(self, suffix: str = None) -> bool:
        """
        状態バックアップ作成

        Args:
            suffix: バックアップファイル名サフィックス

        Returns:
            バックアップ成功フラグ
        """
        pass


class LocalFilePersistence(DrawdownPersistence):
    """ローカルファイル永続化実装"""

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = Path(file_path)
        # 親ディレクトリを確実に作成
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    async def save_state(self, state: Dict[str, Any]) -> bool:
        """ローカルファイルに状態保存"""
        try:
            # タイムスタンプ追加
            state["last_updated"] = datetime.now().isoformat()

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2, default=str)

            self.logger.debug(f"ドローダウン状態保存成功: {self.file_path}")
            return True

        except Exception as e:
            self.logger.error(f"ローカルファイル保存エラー: {e}")
            return False

    async def load_state(self) -> Optional[Dict[str, Any]]:
        """ローカルファイルから状態読み込み"""
        try:
            if not self.file_path.exists():
                self.logger.info(f"状態ファイルが存在しません（初回起動）: {self.file_path}")
                return None

            with open(self.file_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            self.logger.debug(f"ドローダウン状態読み込み成功: {self.file_path}")
            return state

        except Exception as e:
            self.logger.error(f"ローカルファイル読み込みエラー: {e}")
            return None

    async def backup_state(self, suffix: str = None) -> bool:
        """ローカルファイルバックアップ作成"""
        try:
            if not self.file_path.exists():
                return True

            if suffix is None:
                suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

            backup_path = self.file_path.with_suffix(f".{suffix}.backup")

            # 既存ファイルをコピー
            import shutil

            shutil.copy2(self.file_path, backup_path)

            self.logger.info(f"ドローダウン状態バックアップ作成: {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"ローカルファイルバックアップエラー: {e}")
            return False


class CloudStoragePersistence(DrawdownPersistence):
    """Cloud Storage永続化実装"""

    def __init__(self, bucket_name: str, object_path: str):
        super().__init__()
        self.bucket_name = bucket_name
        self.object_path = object_path
        self._storage_client = None
        self._bucket = None

    def _get_storage_client(self):
        """Cloud Storageクライアント取得（遅延初期化）"""
        if self._storage_client is None:
            try:
                from google.cloud import storage

                self._storage_client = storage.Client()
                self._bucket = self._storage_client.bucket(self.bucket_name)
                self.logger.info(f"Cloud Storage初期化成功: {self.bucket_name}")
            except ImportError:
                self.logger.error("google-cloud-storageライブラリが見つかりません")
                raise
            except Exception as e:
                self.logger.error(f"Cloud Storage初期化エラー: {e}")
                raise

        return self._storage_client

    async def save_state(self, state: Dict[str, Any]) -> bool:
        """Cloud Storageに状態保存"""
        try:
            self._get_storage_client()

            # タイムスタンプ追加
            state["last_updated"] = datetime.now().isoformat()

            # JSONデータ準備
            json_data = json.dumps(state, ensure_ascii=False, indent=2, default=str)

            # Cloud Storageにアップロード
            blob = self._bucket.blob(self.object_path)
            blob.upload_from_string(json_data, content_type="application/json")

            self.logger.debug(f"Cloud Storage保存成功: gs://{self.bucket_name}/{self.object_path}")
            return True

        except Exception as e:
            self.logger.error(f"Cloud Storage保存エラー: {e}")
            return False

    async def load_state(self) -> Optional[Dict[str, Any]]:
        """Cloud Storageから状態読み込み"""
        try:
            self._get_storage_client()

            blob = self._bucket.blob(self.object_path)

            if not blob.exists():
                self.logger.info(
                    f"Cloud Storageに状態ファイルが存在しません: gs://{self.bucket_name}/{self.object_path}"
                )
                return None

            # ダウンロードして解析
            json_data = blob.download_as_text()
            state = json.loads(json_data)

            self.logger.debug(
                f"Cloud Storage読み込み成功: gs://{self.bucket_name}/{self.object_path}"
            )
            return state

        except Exception as e:
            self.logger.error(f"Cloud Storage読み込みエラー: {e}")
            return None

    async def backup_state(self, suffix: str = None) -> bool:
        """Cloud Storageバックアップ作成"""
        try:
            self._get_storage_client()

            # 現在のオブジェクトが存在するかチェック
            source_blob = self._bucket.blob(self.object_path)
            if not source_blob.exists():
                return True

            if suffix is None:
                suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

            # バックアップパス作成
            backup_path = f"backup/{self.object_path}.{suffix}"
            backup_blob = self._bucket.blob(backup_path)

            # オブジェクトをコピー
            source_blob.reload()  # メタデータ取得
            backup_blob.upload_from_string(
                source_blob.download_as_text(), content_type="application/json"
            )

            self.logger.info(
                f"Cloud Storageバックアップ作成: gs://{self.bucket_name}/{backup_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Cloud Storageバックアップエラー: {e}")
            return False


def create_persistence(
    mode: str = "paper",
    local_path: str = None,
    gcs_bucket: str = None,
    gcs_path: str = None,
) -> DrawdownPersistence:
    """
    環境に応じて適切な永続化実装を作成（モード別分離対応）

    Args:
        mode: 実行モード（"paper"/"live"/"backtest"）- 状態ファイル分離用
        local_path: ローカルファイルパス（Noneの場合はモード別デフォルト）
        gcs_bucket: Cloud Storageバケット名
        gcs_path: Cloud Storageオブジェクトパス（Noneの場合はモード別デフォルト）

    Returns:
        DrawdownPersistence実装インスタンス
    """
    logger = get_logger()

    # モード別デフォルトパス設定（unified.yamlから取得）
    if local_path is None:
        path_template = get_config(
            "risk.drawdown_manager.persistence.local_path_template",
            "src/core/state/{mode}/drawdown_state.json",
        )
        local_path = path_template.format(mode=mode)
    if gcs_path is None:
        path_template = get_config(
            "risk.drawdown_manager.persistence.gcs_path_template",
            "drawdown/{mode}/state.json",
        )
        gcs_path = path_template.format(mode=mode)

    # GCP環境判定
    is_gcp = os.getenv("RUNNING_ON_GCP", "false").lower() == "true"

    if is_gcp and gcs_bucket:
        try:
            logger.info(f"Cloud Storage永続化を選択（{mode}モード）: gs://{gcs_bucket}/{gcs_path}")
            return CloudStoragePersistence(gcs_bucket, gcs_path)
        except Exception as e:
            logger.warning(f"Cloud Storage初期化失敗、ローカルファイルにフォールバック: {e}")

    # ローカルファイル永続化（デフォルト）
    logger.info(f"ローカルファイル永続化を選択（{mode}モード）: {local_path}")
    return LocalFilePersistence(local_path)
