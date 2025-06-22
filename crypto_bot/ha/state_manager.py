"""
HA環境での状態管理

マルチリージョン環境でのアプリケーション状態の同期と一貫性を管理します。
リーダー選出、状態同期、フェイルオーバー処理を提供します。
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from google.cloud import storage
    from google.cloud import firestore
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

logger = logging.getLogger(__name__)


class StateManager:
    """マルチリージョン環境での状態管理クラス"""
    
    def __init__(self, 
                 project_id: str = None,
                 region: str = None,
                 instance_id: str = None,
                 bucket_name: str = None,
                 enable_cloud_storage: bool = True):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = region or os.getenv("REGION", "unknown")
        self.instance_id = instance_id or os.getenv("INSTANCE_ID", "unknown")
        self.bucket_name = bucket_name or f"{self.project_id}-crypto-bot-state"
        self.enable_cloud_storage = enable_cloud_storage and GOOGLE_CLOUD_AVAILABLE
        
        self.local_state_file = "status.json"
        self.heartbeat_interval = 30  # seconds
        self.leader_timeout = 120  # seconds
        self.last_heartbeat = None
        self.is_leader = False
        
        # Cloud Storage client (if available)
        self.storage_client = None
        self.firestore_client = None
        
        if self.enable_cloud_storage:
            try:
                self.storage_client = storage.Client(project=self.project_id)
                self.firestore_client = firestore.Client(project=self.project_id)
                logger.info("Cloud Storage and Firestore clients initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize cloud clients: {e}")
                self.enable_cloud_storage = False
    
    def get_instance_key(self) -> str:
        """インスタンスの一意キーを生成"""
        return f"{self.region}-{self.instance_id}"
    
    def send_heartbeat(self) -> bool:
        """ハートビートを送信してリーダーステータスを更新"""
        if not self.enable_cloud_storage:
            return True
        
        try:
            doc_ref = self.firestore_client.collection('crypto_bot_instances').document(self.get_instance_key())
            
            heartbeat_data = {
                'region': self.region,
                'instance_id': self.instance_id,
                'last_heartbeat': firestore.SERVER_TIMESTAMP,
                'is_alive': True,
                'status': self._get_local_status()
            }
            
            doc_ref.set(heartbeat_data, merge=True)
            self.last_heartbeat = datetime.utcnow()
            logger.debug(f"Heartbeat sent for {self.get_instance_key()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False
    
    def elect_leader(self) -> bool:
        """リーダー選出を実行"""
        if not self.enable_cloud_storage:
            self.is_leader = True
            return True
        
        try:
            # 現在のリーダーをチェック
            leader_ref = self.firestore_client.collection('crypto_bot_cluster').document('leader')
            leader_doc = leader_ref.get()
            
            current_time = datetime.utcnow()
            
            if leader_doc.exists:
                leader_data = leader_doc.to_dict()
                last_heartbeat = leader_data.get('last_heartbeat')
                
                # リーダーのハートビートが古い場合は選出を試行
                if last_heartbeat and isinstance(last_heartbeat, datetime):
                    time_diff = (current_time - last_heartbeat).total_seconds()
                    if time_diff < self.leader_timeout:
                        # 現在のリーダーが有効
                        current_leader = leader_data.get('instance_key')
                        self.is_leader = (current_leader == self.get_instance_key())
                        return self.is_leader
            
            # リーダーが存在しないか、タイムアウトしているので選出を試行
            leader_data = {
                'instance_key': self.get_instance_key(),
                'region': self.region,
                'instance_id': self.instance_id,
                'elected_at': firestore.SERVER_TIMESTAMP,
                'last_heartbeat': firestore.SERVER_TIMESTAMP
            }
            
            # トランザクションでリーダー選出
            transaction = self.firestore_client.transaction()
            
            @firestore.transactional
            def update_leader(transaction, leader_ref):
                # 再度チェック（レースコンディション対策）
                snapshot = leader_ref.get(transaction=transaction)
                if snapshot.exists:
                    data = snapshot.to_dict()
                    last_hb = data.get('last_heartbeat')
                    if last_hb and isinstance(last_hb, datetime):
                        if (current_time - last_hb).total_seconds() < self.leader_timeout:
                            return False  # 他のリーダーが有効
                
                transaction.set(leader_ref, leader_data)
                return True
            
            success = update_leader(transaction, leader_ref)
            self.is_leader = success
            
            if success:
                logger.info(f"Leader elected: {self.get_instance_key()}")
            else:
                logger.info(f"Leader election failed, another instance is leader")
            
            return success
            
        except Exception as e:
            logger.error(f"Leader election failed: {e}")
            # フォールバック: プライマリリージョンなら自動的にリーダーになる
            self.is_leader = (self.region == "asia-northeast1")
            return self.is_leader
    
    def sync_state_to_cloud(self, state_data: Dict[str, Any]) -> bool:
        """ローカル状態をクラウドに同期"""
        if not self.enable_cloud_storage or not self.is_leader:
            return True
        
        try:
            # Cloud Storage に状態をアップロード
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob('current_state.json')
            
            state_with_metadata = {
                **state_data,
                'synced_at': datetime.utcnow().isoformat(),
                'synced_by': self.get_instance_key(),
                'region': self.region
            }
            
            blob.upload_from_string(
                json.dumps(state_with_metadata, ensure_ascii=False, indent=2),
                content_type='application/json'
            )
            
            logger.debug("State synced to cloud storage")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync state to cloud: {e}")
            return False
    
    def sync_state_from_cloud(self) -> Optional[Dict[str, Any]]:
        """クラウドから状態を同期"""
        if not self.enable_cloud_storage:
            return None
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob('current_state.json')
            
            if not blob.exists():
                logger.debug("No cloud state found")
                return None
            
            content = blob.download_as_text()
            state_data = json.loads(content)
            
            # メタデータを除去
            clean_state = {k: v for k, v in state_data.items() 
                          if k not in ['synced_at', 'synced_by', 'region']}
            
            logger.debug("State synced from cloud storage")
            return clean_state
            
        except Exception as e:
            logger.error(f"Failed to sync state from cloud: {e}")
            return None
    
    def _get_local_status(self) -> Dict[str, Any]:
        """ローカルの状態ファイルを読み取り"""
        try:
            if os.path.exists(self.local_state_file):
                with open(self.local_state_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to read local status: {e}")
            return {}
    
    def update_local_status(self, status_data: Dict[str, Any]) -> bool:
        """ローカル状態を更新"""
        try:
            with open(self.local_state_file, 'w') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
            
            # リーダーの場合はクラウドにも同期
            if self.is_leader:
                self.sync_state_to_cloud(status_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update local status: {e}")
            return False
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """クラスター全体の状態を取得"""
        if not self.enable_cloud_storage:
            return {
                'instances': [self.get_instance_key()],
                'leader': self.get_instance_key(),
                'total_instances': 1
            }
        
        try:
            # 全インスタンスの状態を取得
            instances_ref = self.firestore_client.collection('crypto_bot_instances')
            instances = instances_ref.stream()
            
            instance_data = {}
            alive_instances = []
            current_time = datetime.utcnow()
            
            for instance in instances:
                data = instance.to_dict()
                instance_key = instance.id
                last_heartbeat = data.get('last_heartbeat')
                
                if last_heartbeat and isinstance(last_heartbeat, datetime):
                    time_diff = (current_time - last_heartbeat).total_seconds()
                    if time_diff < self.leader_timeout:
                        alive_instances.append(instance_key)
                        instance_data[instance_key] = {
                            'region': data.get('region'),
                            'instance_id': data.get('instance_id'),
                            'last_heartbeat': last_heartbeat.isoformat(),
                            'status': data.get('status', {})
                        }
            
            # リーダー情報を取得
            leader_ref = self.firestore_client.collection('crypto_bot_cluster').document('leader')
            leader_doc = leader_ref.get()
            current_leader = None
            
            if leader_doc.exists:
                leader_data = leader_doc.to_dict()
                current_leader = leader_data.get('instance_key')
            
            return {
                'instances': alive_instances,
                'leader': current_leader,
                'total_instances': len(alive_instances),
                'instance_details': instance_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster status: {e}")
            return {
                'instances': [self.get_instance_key()],
                'leader': self.get_instance_key() if self.is_leader else None,
                'total_instances': 1,
                'error': str(e)
            }
    
    def handle_failover(self) -> bool:
        """フェイルオーバー処理"""
        try:
            logger.info("Handling failover...")
            
            # リーダー選出を実行
            if self.elect_leader():
                logger.info("Became new leader, syncing state...")
                
                # クラウドから最新状態を取得
                cloud_state = self.sync_state_from_cloud()
                if cloud_state:
                    # ローカル状態を更新
                    self.update_local_status(cloud_state)
                    logger.info("State restored from cloud")
                
                return True
            else:
                logger.info("Another instance is leader, becoming follower")
                return False
                
        except Exception as e:
            logger.error(f"Failover handling failed: {e}")
            return False
    
    def start_background_tasks(self):
        """バックグラウンドタスクを開始"""
        import threading
        
        def heartbeat_loop():
            while True:
                try:
                    self.send_heartbeat()
                    
                    # 定期的にリーダー選出をチェック
                    if not self.is_leader:
                        self.elect_leader()
                    
                    time.sleep(self.heartbeat_interval)
                    
                except Exception as e:
                    logger.error(f"Heartbeat loop error: {e}")
                    time.sleep(self.heartbeat_interval)
        
        # バックグラウンドスレッドで実行
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        logger.info("Background heartbeat task started")