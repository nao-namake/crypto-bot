# ha/ - 高可用性・状態管理

## 📋 概要

**High Availability & State Management**  
本フォルダは crypto-bot の高可用性機能を提供し、マルチリージョン環境での状態同期、リーダー選出、フェイルオーバー処理を担当します。

## 🎯 主要機能

### **状態管理**
- アプリケーション状態の永続化
- 分散環境での状態同期
- 一貫性保証
- バージョン管理

### **リーダー選出**
- 分散システムでのリーダー決定
- 自動フェイルオーバー
- スプリットブレイン防止
- ハートビート監視

### **クラウド統合**
- Google Cloud Firestore統合
- Cloud Storage活用
- マルチリージョン対応
- 災害復旧機能

## 📁 ファイル構成

```
ha/
├── __init__.py       # パッケージ初期化
└── state_manager.py  # 状態管理実装
```

## 🔍 ファイルの役割

### **state_manager.py**
- `StateManager`クラス - 状態管理本体
- Google Cloud統合（オプショナル）
- リーダー選出メカニズム
- 状態同期・レプリケーション
- フェイルオーバー処理
- ハートビート機能

## 🚀 使用方法

### **基本的な状態管理**
```python
from crypto_bot.ha.state_manager import StateManager

# 状態管理初期化
state_manager = StateManager(
    project_id="crypto-bot-prod",
    instance_id="instance-1",
    region="asia-northeast1"
)

# 状態保存
state_manager.save_state({
    "last_processed_timestamp": datetime.now(),
    "active_positions": positions,
    "model_version": "v1.2.3"
})

# 状態取得
current_state = state_manager.get_state()
```

### **リーダー選出**
```python
# リーダー確認
if state_manager.is_leader():
    # リーダーとしての処理実行
    execute_leader_tasks()
else:
    # フォロワーとしての処理
    sync_from_leader()

# リーダー監視
state_manager.watch_leader(
    on_become_leader=handle_promotion,
    on_lose_leadership=handle_demotion
)
```

### **フェイルオーバー処理**
```python
# 自動フェイルオーバー設定
state_manager.configure_failover(
    health_check_interval=30,  # 30秒ごとのヘルスチェック
    failover_timeout=60,       # 60秒でフェイルオーバー
    recovery_callback=recover_state
)

# 手動フェイルオーバー
state_manager.trigger_failover(target_instance="instance-2")
```

## ⚠️ 課題・改善点

### **ファイル数不足**
- HA機能に対して実装が少ない
- より包括的なHA機能が必要
- 分散システム機能の拡充

### **クラウド依存**
- Google Cloud固有の実装
- マルチクラウド対応不足
- オンプレミス対応

### **機能制限**
- 分散ロック未実装
- 分散トランザクション不足
- イベントソーシング未対応

### **監視・可観測性**
- メトリクス収集不足
- 分散トレーシング未実装
- ログ集約機能不足

## 📝 今後の展開

1. **HA機能拡充**
   ```
   ha/
   ├── state/           # 状態管理
   │   ├── manager.py
   │   ├── sync.py      # 同期機能
   │   └── storage.py   # ストレージ抽象化
   ├── consensus/       # 合意形成
   │   ├── raft.py      # Raftアルゴリズム
   │   └── leader.py    # リーダー選出
   ├── failover/        # フェイルオーバー
   │   ├── detector.py  # 障害検出
   │   └── handler.py   # 復旧処理
   └── replication/     # レプリケーション
       ├── master.py
       └── slave.py
   ```

2. **分散システム強化**
   - 分散ロック実装
   - 分散キャッシュ
   - イベントソーシング
   - CQRS実装

3. **マルチクラウド対応**
   - AWS DynamoDB統合
   - Azure Cosmos DB対応
   - Redis/etcd統合
   - 抽象化レイヤー

4. **可観測性向上**
   - 分散トレーシング（OpenTelemetry）
   - メトリクス集約（Prometheus）
   - ログ集約（ELK Stack）
   - ダッシュボード統合