"""
HA State Manager のテスト
"""

import json
import os
import tempfile
import time
from unittest.mock import Mock, patch
import pytest

from crypto_bot.ha.state_manager import StateManager


class TestStateManager:
    
    @pytest.fixture
    def temp_dir(self):
        """テンポラリディレクトリを作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def state_manager(self, temp_dir):
        """テスト用のStateManagerインスタンス"""
        # テスト用の設定でCloud Storage無効化
        with patch.dict(os.environ, {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'REGION': 'test-region',
            'INSTANCE_ID': 'test-instance'
        }):
            # ワーキングディレクトリを変更
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                sm = StateManager(
                    project_id='test-project',
                    region='test-region',
                    instance_id='test-instance',
                    enable_cloud_storage=False
                )
                yield sm
            finally:
                os.chdir(original_cwd)
    
    def test_get_instance_key(self, state_manager):
        """インスタンスキーの生成をテスト"""
        expected_key = "test-region-test-instance"
        assert state_manager.get_instance_key() == expected_key
    
    def test_update_local_status(self, state_manager):
        """ローカル状態更新をテスト"""
        test_status = {
            "total_profit": 1000.0,
            "trade_count": 5,
            "position": "BUY",
            "last_updated": "2025-06-22 12:00:00"
        }
        
        success = state_manager.update_local_status(test_status)
        assert success is True
        
        # ファイルが作成されることを確認
        assert os.path.exists(state_manager.local_state_file)
        
        # 内容を確認
        with open(state_manager.local_state_file, 'r') as f:
            saved_status = json.load(f)
        
        assert saved_status == test_status
    
    def test_get_local_status(self, state_manager):
        """ローカル状態読み取りをテスト"""
        # 最初は空のデータ
        status = state_manager._get_local_status()
        assert status == {}
        
        # データを書き込んでから読み取り
        test_status = {"test": "data"}
        with open(state_manager.local_state_file, 'w') as f:
            json.dump(test_status, f)
        
        status = state_manager._get_local_status()
        assert status == test_status
    
    def test_leader_election_without_cloud(self, state_manager):
        """Cloud Storage無効時のリーダー選出をテスト"""
        # Cloud Storage無効時は常にリーダーになる
        is_leader = state_manager.elect_leader()
        assert is_leader is True
        assert state_manager.is_leader is True
    
    def test_heartbeat_without_cloud(self, state_manager):
        """Cloud Storage無効時のハートビートをテスト"""
        # Cloud Storage無効時は常に成功
        success = state_manager.send_heartbeat()
        assert success is True
    
    def test_cluster_status_without_cloud(self, state_manager):
        """Cloud Storage無効時のクラスター状態をテスト"""
        cluster_status = state_manager.get_cluster_status()
        
        expected = {
            'instances': ['test-region-test-instance'],
            'leader': 'test-region-test-instance',
            'total_instances': 1
        }
        
        assert cluster_status == expected
    
    def test_failover_without_cloud(self, state_manager):
        """Cloud Storage無効時のフェイルオーバーをテスト"""
        success = state_manager.handle_failover()
        assert success is True
        assert state_manager.is_leader is True
    
    def test_leader_election_with_cloud_enabled(self, state_manager):
        """Cloud Storage有効時のリーダー選出をテスト（簡略版）"""
        # Cloud Storage有効だがクライアント初期化失敗をシミュレート
        state_manager.enable_cloud_storage = True
        state_manager.firestore_client = None
        
        # フォールバック動作のテスト（プライマリリージョンがリーダーになる）
        state_manager.region = "asia-northeast1"
        is_leader = state_manager.elect_leader()
        assert is_leader is True
        
        # セカンダリリージョンの場合
        state_manager.region = "us-central1"
        is_leader = state_manager.elect_leader()
        assert is_leader is False
    
    def test_sync_state_without_leader(self, state_manager):
        """リーダーでない場合の状態同期をテスト"""
        state_manager.is_leader = False
        
        test_state = {"test": "data"}
        success = state_manager.sync_state_to_cloud(test_state)
        
        # リーダーでない場合は常に成功（何もしない）
        assert success is True
    
    def test_background_tasks_start(self, state_manager):
        """バックグラウンドタスクの開始をテスト"""
        with patch('threading.Thread') as mock_thread:
            state_manager.start_background_tasks()
            
            # スレッドが作成されることを確認
            mock_thread.assert_called_once()
            thread_args = mock_thread.call_args
            assert thread_args[1]['daemon'] is True
    
    def test_instance_key_generation(self):
        """異なる設定でのインスタンスキー生成をテスト"""
        sm1 = StateManager(
            region='asia-northeast1',
            instance_id='primary',
            enable_cloud_storage=False
        )
        
        sm2 = StateManager(
            region='us-central1',
            instance_id='secondary',
            enable_cloud_storage=False
        )
        
        assert sm1.get_instance_key() == 'asia-northeast1-primary'
        assert sm2.get_instance_key() == 'us-central1-secondary'
        assert sm1.get_instance_key() != sm2.get_instance_key()
    
    def test_state_persistence(self, state_manager):
        """状態の永続化をテスト"""
        # 初期状態
        initial_state = {
            "total_profit": 0.0,
            "trade_count": 0,
            "position": ""
        }
        
        state_manager.update_local_status(initial_state)
        
        # 状態を更新
        updated_state = {
            "total_profit": 1500.0,
            "trade_count": 10,
            "position": "SELL"
        }
        
        state_manager.update_local_status(updated_state)
        
        # 読み取って確認
        loaded_state = state_manager._get_local_status()
        assert loaded_state == updated_state
    
    def test_error_handling_file_operations(self, state_manager):
        """ファイル操作のエラーハンドリングをテスト"""
        # 無効なディレクトリパスでファイル操作を試行
        state_manager.local_state_file = "/invalid/path/status.json"
        
        # エラーが発生してもFalseを返すことを確認
        success = state_manager.update_local_status({"test": "data"})
        assert success is False
        
        # 読み取りも空辞書を返すことを確認
        status = state_manager._get_local_status()
        assert status == {}