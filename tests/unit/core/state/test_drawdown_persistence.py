"""
ドローダウン状態永続化システムのテスト

DrawdownPersistence基底クラス、LocalFilePersistence、
CloudStoragePersistence、create_persistence関数のテスト。
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from src.core.state.drawdown_persistence import (
    CloudStoragePersistence,
    DrawdownPersistence,
    LocalFilePersistence,
    create_persistence,
)


class TestLocalFilePersistence:
    """LocalFilePersistenceクラスのテスト"""

    @pytest.fixture
    def temp_file_path(self, tmp_path):
        """一時ファイルパスを提供"""
        return str(tmp_path / "test_state.json")

    @pytest.fixture
    def persistence(self, temp_file_path):
        """LocalFilePersistenceインスタンスを提供"""
        return LocalFilePersistence(temp_file_path)

    def test_init_creates_parent_directory(self, tmp_path):
        """初期化時に親ディレクトリが作成されること"""
        nested_path = tmp_path / "nested" / "dir" / "state.json"
        persistence = LocalFilePersistence(str(nested_path))
        assert nested_path.parent.exists()

    @pytest.mark.asyncio
    async def test_save_state_success(self, persistence, temp_file_path):
        """状態保存が成功すること"""
        state = {"key": "value", "number": 42}
        result = await persistence.save_state(state)
        assert result is True
        assert Path(temp_file_path).exists()

        # 保存されたJSONを確認
        with open(temp_file_path, "r", encoding="utf-8") as f:
            saved_state = json.load(f)
        assert saved_state["key"] == "value"
        assert saved_state["number"] == 42
        assert "last_updated" in saved_state

    @pytest.mark.asyncio
    async def test_save_state_adds_timestamp(self, persistence, temp_file_path):
        """保存時にタイムスタンプが追加されること"""
        state = {"data": "test"}
        await persistence.save_state(state)

        with open(temp_file_path, "r", encoding="utf-8") as f:
            saved_state = json.load(f)
        assert "last_updated" in saved_state

    @pytest.mark.asyncio
    async def test_save_state_handles_unicode(self, persistence, temp_file_path):
        """日本語を含む状態が正しく保存されること"""
        state = {"status": "正常", "message": "テスト成功"}
        result = await persistence.save_state(state)
        assert result is True

        with open(temp_file_path, "r", encoding="utf-8") as f:
            saved_state = json.load(f)
        assert saved_state["status"] == "正常"
        assert saved_state["message"] == "テスト成功"

    @pytest.mark.asyncio
    async def test_save_state_error_handling(self, persistence):
        """保存エラー時にFalseを返すこと"""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = await persistence.save_state({"key": "value"})
        assert result is False

    @pytest.mark.asyncio
    async def test_load_state_success(self, persistence, temp_file_path):
        """状態読み込みが成功すること"""
        # まず状態を保存
        state = {"key": "value", "count": 100}
        await persistence.save_state(state)

        # 読み込み
        loaded_state = await persistence.load_state()
        assert loaded_state is not None
        assert loaded_state["key"] == "value"
        assert loaded_state["count"] == 100

    @pytest.mark.asyncio
    async def test_load_state_file_not_exists(self, persistence):
        """ファイルが存在しない場合にNoneを返すこと"""
        result = await persistence.load_state()
        assert result is None

    @pytest.mark.asyncio
    async def test_load_state_invalid_json(self, persistence, temp_file_path):
        """無効なJSONの場合にNoneを返すこと"""
        # 無効なJSONを書き込み
        with open(temp_file_path, "w") as f:
            f.write("invalid json content")

        result = await persistence.load_state()
        assert result is None

    @pytest.mark.asyncio
    async def test_load_state_error_handling(self, persistence, temp_file_path):
        """読み込みエラー時にNoneを返すこと"""
        # ファイルを作成
        Path(temp_file_path).touch()

        with patch("builtins.open", side_effect=IOError("Read error")):
            result = await persistence.load_state()
        assert result is None

    @pytest.mark.asyncio
    async def test_backup_state_success(self, persistence, temp_file_path):
        """バックアップが成功すること"""
        # まず状態を保存
        state = {"data": "backup test"}
        await persistence.save_state(state)

        # バックアップ作成
        result = await persistence.backup_state(suffix="test_backup")
        assert result is True

        # バックアップファイルが存在することを確認
        backup_path = Path(temp_file_path).with_suffix(".test_backup.backup")
        assert backup_path.exists()

    @pytest.mark.asyncio
    async def test_backup_state_file_not_exists(self, persistence):
        """ファイルが存在しない場合にTrueを返すこと（バックアップ不要）"""
        result = await persistence.backup_state()
        assert result is True

    @pytest.mark.asyncio
    async def test_backup_state_auto_suffix(self, persistence, temp_file_path):
        """サフィックスが自動生成されること"""
        state = {"data": "auto suffix test"}
        await persistence.save_state(state)

        result = await persistence.backup_state()  # サフィックス未指定
        assert result is True

    @pytest.mark.asyncio
    async def test_backup_state_error_handling(self, persistence, temp_file_path):
        """バックアップエラー時にFalseを返すこと"""
        # ファイルを作成
        state = {"data": "test"}
        await persistence.save_state(state)

        with patch("shutil.copy2", side_effect=IOError("Copy error")):
            result = await persistence.backup_state(suffix="error_test")
        assert result is False


class TestCloudStoragePersistence:
    """CloudStoragePersistenceクラスのテスト"""

    @pytest.fixture
    def persistence(self):
        """CloudStoragePersistenceインスタンスを提供"""
        return CloudStoragePersistence("test-bucket", "drawdown/state.json")

    def test_init(self, persistence):
        """初期化が正しく行われること"""
        assert persistence.bucket_name == "test-bucket"
        assert persistence.object_path == "drawdown/state.json"
        assert persistence._storage_client is None
        assert persistence._bucket is None

    def test_get_storage_client_import_error(self, persistence):
        """google-cloud-storageがない場合にエラーを発生すること"""
        with patch.dict("sys.modules", {"google.cloud": None, "google": None}):
            with patch(
                "src.core.state.drawdown_persistence.CloudStoragePersistence._get_storage_client",
                side_effect=ImportError("No module named 'google.cloud'"),
            ):
                with pytest.raises(ImportError):
                    persistence._get_storage_client()

    @pytest.mark.asyncio
    async def test_save_state_success(self, persistence):
        """Cloud Storageへの保存が成功すること"""
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        persistence._storage_client = mock_client
        persistence._bucket = mock_bucket

        state = {"key": "value"}
        result = await persistence.save_state(state)

        assert result is True
        mock_blob.upload_from_string.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_error_handling(self, persistence):
        """Cloud Storage保存エラー時にFalseを返すこと"""
        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = Exception("Upload failed")
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        persistence._storage_client = mock_client
        persistence._bucket = mock_bucket

        state = {"key": "value"}
        result = await persistence.save_state(state)
        assert result is False

    @pytest.mark.asyncio
    async def test_load_state_success(self, persistence):
        """Cloud Storageからの読み込みが成功すること"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_text.return_value = '{"key": "value", "count": 10}'
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        persistence._storage_client = mock_client
        persistence._bucket = mock_bucket

        result = await persistence.load_state()

        assert result is not None
        assert result["key"] == "value"
        assert result["count"] == 10

    @pytest.mark.asyncio
    async def test_load_state_not_exists(self, persistence):
        """Cloud Storageにファイルが存在しない場合にNoneを返すこと"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        persistence._storage_client = mock_client
        persistence._bucket = mock_bucket

        result = await persistence.load_state()
        assert result is None

    @pytest.mark.asyncio
    async def test_load_state_error_handling(self, persistence):
        """Cloud Storage読み込みエラー時にNoneを返すこと"""
        mock_blob = MagicMock()
        mock_blob.exists.side_effect = Exception("Access denied")
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        persistence._storage_client = mock_client
        persistence._bucket = mock_bucket

        result = await persistence.load_state()
        assert result is None

    @pytest.mark.asyncio
    async def test_backup_state_success(self, persistence):
        """Cloud Storageバックアップが成功すること"""
        mock_source_blob = MagicMock()
        mock_source_blob.exists.return_value = True
        mock_source_blob.download_as_text.return_value = '{"key": "value"}'

        mock_backup_blob = MagicMock()

        mock_bucket = MagicMock()
        mock_bucket.blob.side_effect = lambda path: (
            mock_source_blob if path == "drawdown/state.json" else mock_backup_blob
        )
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        persistence._storage_client = mock_client
        persistence._bucket = mock_bucket

        result = await persistence.backup_state(suffix="test")
        assert result is True
        mock_backup_blob.upload_from_string.assert_called_once()

    @pytest.mark.asyncio
    async def test_backup_state_source_not_exists(self, persistence):
        """ソースファイルが存在しない場合にTrueを返すこと"""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        persistence._storage_client = mock_client
        persistence._bucket = mock_bucket

        result = await persistence.backup_state()
        assert result is True

    @pytest.mark.asyncio
    async def test_backup_state_error_handling(self, persistence):
        """Cloud Storageバックアップエラー時にFalseを返すこと"""
        mock_blob = MagicMock()
        mock_blob.exists.side_effect = Exception("Access denied")
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        persistence._storage_client = mock_client
        persistence._bucket = mock_bucket

        result = await persistence.backup_state()
        assert result is False


class TestCreatePersistence:
    """create_persistence関数のテスト"""

    def test_create_local_persistence_default(self):
        """デフォルトでローカル永続化が作成されること"""
        with patch.dict(os.environ, {"RUNNING_ON_GCP": "false"}, clear=False):
            persistence = create_persistence(mode="paper")
        assert isinstance(persistence, LocalFilePersistence)

    def test_create_local_persistence_with_custom_path(self):
        """カスタムパスでローカル永続化が作成されること"""
        with patch.dict(os.environ, {"RUNNING_ON_GCP": "false"}, clear=False):
            persistence = create_persistence(mode="live", local_path="/tmp/custom_state.json")
        assert isinstance(persistence, LocalFilePersistence)
        assert str(persistence.file_path) == "/tmp/custom_state.json"

    def test_create_cloud_persistence_on_gcp(self):
        """GCP環境でCloud Storage永続化が作成されること"""
        with patch.dict(os.environ, {"RUNNING_ON_GCP": "true"}, clear=False):
            with patch(
                "src.core.state.drawdown_persistence.CloudStoragePersistence.__init__",
                return_value=None,
            ):
                persistence = create_persistence(
                    mode="live", gcs_bucket="my-bucket", gcs_path="state/live.json"
                )
        assert isinstance(persistence, CloudStoragePersistence)

    def test_create_cloud_persistence_fallback_on_error(self):
        """Cloud Storage初期化失敗時にローカルにフォールバックすること"""
        with patch.dict(os.environ, {"RUNNING_ON_GCP": "true"}, clear=False):
            with patch(
                "src.core.state.drawdown_persistence.CloudStoragePersistence.__init__",
                side_effect=Exception("Init failed"),
            ):
                persistence = create_persistence(
                    mode="live", gcs_bucket="my-bucket", gcs_path="state/live.json"
                )
        assert isinstance(persistence, LocalFilePersistence)

    def test_mode_paper_default_path(self):
        """paperモードのデフォルトパスが正しいこと"""
        with patch.dict(os.environ, {"RUNNING_ON_GCP": "false"}, clear=False):
            persistence = create_persistence(mode="paper")
        assert "paper" in str(persistence.file_path)

    def test_mode_live_default_path(self):
        """liveモードのデフォルトパスが正しいこと"""
        with patch.dict(os.environ, {"RUNNING_ON_GCP": "false"}, clear=False):
            persistence = create_persistence(mode="live")
        assert "live" in str(persistence.file_path)

    def test_mode_backtest_default_path(self):
        """backtestモードのデフォルトパスが正しいこと"""
        with patch.dict(os.environ, {"RUNNING_ON_GCP": "false"}, clear=False):
            persistence = create_persistence(mode="backtest")
        assert "backtest" in str(persistence.file_path)

    def test_gcp_env_without_bucket(self):
        """GCP環境でバケット未指定の場合にローカルを使用すること"""
        with patch.dict(os.environ, {"RUNNING_ON_GCP": "true"}, clear=False):
            persistence = create_persistence(mode="paper")  # バケット未指定
        assert isinstance(persistence, LocalFilePersistence)


class TestDrawdownPersistenceAbstractClass:
    """DrawdownPersistence抽象基底クラスのテスト"""

    def test_cannot_instantiate_abstract_class(self):
        """抽象クラスを直接インスタンス化できないこと"""
        with pytest.raises(TypeError):
            DrawdownPersistence()

    def test_subclass_must_implement_abstract_methods(self):
        """サブクラスは抽象メソッドを実装する必要があること"""

        class IncompletePersistence(DrawdownPersistence):
            pass

        with pytest.raises(TypeError):
            IncompletePersistence()

    def test_complete_subclass_can_be_instantiated(self):
        """完全な実装を持つサブクラスはインスタンス化できること"""

        class CompletePersistence(DrawdownPersistence):
            async def save_state(self, state):
                return True

            async def load_state(self):
                return {}

            async def backup_state(self, suffix=None):
                return True

        # エラーなくインスタンス化できること
        instance = CompletePersistence()
        assert instance is not None
