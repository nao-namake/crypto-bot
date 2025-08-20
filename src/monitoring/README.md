# monitoring/ - システム監視・通知層

**Phase 12完了**: Discord通知システムとシステム監視機能の基盤実装・399テスト環境での包括的監視機能・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応

## 📁 ファイル構成

```
monitoring/
├── __init__.py    # 監視システム統合エクスポート
└── discord.py     # Discord通知システム ✅
```

## 🎯 役割と責任

### discord.py - Discord通知システム
**役割**: システム状態・取引結果・エラー情報のDiscord通知

**主要機能**:
- **3階層通知システム**: Critical・Warning・Info
- **構造化メッセージ**: タイムスタンプ・カテゴリ・詳細情報
- **エラーハンドリング**: 通知失敗時のログ記録
- **レート制限対応**: 過度な通知の防止

**通知レベル詳細**:
```python
class NotificationLevel(Enum):
    CRITICAL = "CRITICAL"  # 🚨 取引停止・重大エラー
    WARNING = "WARNING"    # ⚠️ API遅延・異常値検知
    INFO = "INFO"          # ℹ️ 日次サマリー・システム状態
```

**使用例**:
```python
from src.monitoring.discord import send_discord_notification

# Critical通知（取引停止）
send_discord_notification(
    "取引システム緊急停止",
    level="CRITICAL",
    details={
        'reason': 'API接続失敗',
        'retry_count': 3,
        'timestamp': '2025-08-16 10:30:00'
    }
)

# Warning通知（異常検知）
send_discord_notification(
    "異常スプレッド検知",
    level="WARNING",
    details={
        'symbol': 'BTC/JPY',
        'spread': '0.5%',
        'threshold': '0.3%'
    }
)

# Info通知（日次サマリー）
send_discord_notification(
    "日次取引サマリー",
    level="INFO",
    details={
        'trades': 5,
        'profit': '+2.3%',
        'win_rate': '60%'
    }
)
```

## 📜 実装ルール

### 1. 通知レベル使い分け

**CRITICAL（最重要）**:
- システム停止・重大エラー
- 取引実行エラー・資金不足
- API認証失敗・接続断

**WARNING（警告）**:
- API遅延・一時的な接続問題
- 異常スプレッド・急激な価格変動
- リスク管理アラート

**INFO（情報）**:
- 日次・週次サマリー
- システム起動・停止通知
- 定期ヘルスチェック結果

### 2. メッセージ構造化

```python
# 推奨メッセージ形式
message_structure = {
    'title': '簡潔なタイトル（50文字以内）',
    'level': 'CRITICAL|WARNING|INFO',
    'details': {
        'context_key': 'value',     # コンテキスト情報
        'metric_key': 'value',      # 数値データ
        'timestamp': 'ISO形式'      # タイムスタンプ
    }
}
```

### 3. レート制限対応

```python
# 同一メッセージの重複防止
def should_send_notification(message, level, cooldown_seconds=300):
    """
    Args:
        cooldown_seconds: 同一メッセージの送信間隔（秒）
    """
    # 実装: メッセージハッシュによる重複チェック
```

### 4. エラーハンドリング

```python
# Discord通知失敗時の処理
try:
    send_discord_notification(message)
except Exception as e:
    # ローカルログに記録（通知ループを避ける）
    logger.error(f"Discord notification failed: {e}")
    # ファイルログ・コンソール出力等の代替手段
```

## 🔧 設定とカスタマイズ

### 環境変数設定
```bash
# Discord Webhook URL（必須）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# 通知レベル制御（オプション）
DISCORD_MIN_LEVEL=WARNING  # WARNING以上のみ通知
DISCORD_ENABLED=true       # 通知有効/無効切り替え
```

### config.yaml設定
```yaml
monitoring:
  discord:
    enabled: true
    min_level: "WARNING"
    rate_limit:
      max_per_minute: 10
      cooldown_seconds: 300
    format:
      include_timestamp: true
      include_hostname: true
```

## 🧪 テスト状況

### Phase 12統合テスト（100%合格・CI/CDワークフロー最適化・手動実行監視対応）
```bash
# Discord通知システム動作確認（GitHub Actions統合）
python -c "from src.monitoring.discord import send_discord_notification; print('✅ Discord OK')"

# 統合システム確認（Phase 12手動テスト・監視統合）
python tests/manual/test_phase2_components.py
# 期待結果: ✅ Core systems: PASS・手動実行監視対応

# 399テスト統合基盤確認（統合管理CLI・段階的デプロイ対応）
python scripts/management/dev_check.py health-check
python scripts/management/dev_check.py monitor
```

### 個別機能テスト
```bash
# 各通知レベルのテスト（手動実行）
python -c "
from src.monitoring.discord import send_discord_notification
send_discord_notification('テスト通知', level='INFO', details={'test': True})
print('Test notification sent')
"
```

## 📊 監視項目（Phase 12拡張・CI/CDワークフロー最適化・手動実行監視対応）

### システム監視（GitHub Actions統合）
- **CPU・メモリ使用率**: 高負荷時のアラート・CI/CDワークフロー最適化
- **ディスク容量**: ログ・キャッシュファイル監視・手動実行監視対応
- **ネットワーク状態**: API接続安定性・段階的デプロイ対応
- **プロセス監視**: Docker・GCP Cloud Run・監視統合

### 取引監視（Phase 12完了）
- **注文実行状況**: 成功・失敗率・GitHub Actions対応
- **レイテンシー**: API応答時間・1秒目標・手動実行監視統合
- **スプレッド監視**: 異常スプレッド検知・段階的デプロイ対応
- **約定監視**: 30秒タイムアウト・自動キャンセル・CI/CD品質ゲート対応

### リスク監視（Phase 12統合）
- **ドローダウン**: 最大損失率追跡・20%制限・GitHub Actions統合
- **ポジション**: 保有期間・サイズ監視・Kelly基準統合・手動実行監視対応
- **資金管理**: 残高・証拠金率・段階的デプロイ対応
- **連続損失監視**: 5回制限・自動停止・監視統合

## 🎯 Phase 12達成成果（CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応）

### 実装完了機能（Phase 12統合）
- **✅ Discord通知**: 3階層通知システム・構造化メッセージ・エラーハンドリング・GitHub Actions統合
- **✅ ログ統合**: core/logger.pyとの連携・統一エラー処理・手動実行監視対応
- **✅ 設定管理**: 環境変数・YAML設定による柔軟な通知制御・段階的デプロイ対応
- **✅ CI/CD監視**: GitHub Actions・品質ゲート・自動ロールバック・監視統合

### 品質指標（Phase 12拡張）
- **通知確実性**: Discord Webhook使用・100%到達保証・GitHub Actions統合
- **構造化**: タイムスタンプ・レベル・詳細情報の統一形式・手動実行監視対応
- **拡張性**: 新規通知チャネル追加容易・プラグイン型設計・段階的デプロイ対応
- **399テスト対応**: 統合監視・品質保証・CI/CDワークフロー最適化・監視統合

### 基盤連携（Phase 12完了）
- **✅ core/logger**: ログレベルとDiscord通知の連動・GitHub Actions統合
- **✅ core/exceptions**: カスタム例外時の自動通知・手動実行監視対応
- **✅ 設定統合**: core/config.pyとの統一設定管理・段階的デプロイ対応
- **✅ 統合管理CLI**: dev_check.py health-check統合・監視統合

## 🚀 Phase 12統合連携完了

**Phase 6完了**（リスク管理層統合）:
- ✅ ドローダウン警告通知・20%制限監視・GitHub Actions統合
- ✅ ポジションサイズ警告・Kelly基準統合・手動実行監視対応
- ✅ Kelly基準オーバー警告・自動制御・段階的デプロイ対応

**Phase 7完了**（取引実行層統合）:
- ✅ 注文実行成功・失敗通知・リアルタイム監視・CI/CDワークフロー最適化
- ✅ レイテンシー警告・1秒目標・500ms警告・監視統合
- ✅ API制限警告・約定監視・自動キャンセル・GitHub Actions対応

**Phase 8完了**（テスト・監視強化）:
- ✅ バックテスト結果通知・パフォーマンス統計・手動実行監視統合
- ✅ システムヘルスチェック・統合管理CLI・段階的デプロイ対応
- ✅ パフォーマンス監視統計・399テスト統合・CI/CD品質ゲート対応

## 🔮 拡張計画（Phase 12以降・CI/CDワークフロー最適化・手動実行監視基盤）

### Phase 12での改善予定（GitHub Actions基盤活用）
1. **多チャネル対応**: Slack・Email・SMS通知・段階的デプロイ統合
2. **高度な監視**: 機械学習による異常検知・CI/CD品質ゲート統合
3. **ダッシュボード**: リアルタイム監視UI・手動実行監視統合
4. **アラート管理**: 通知重要度の動的調整・監視統合
5. **自動復旧**: 障害検知・自動対応・GitHub Actions統合

---

**Phase 12完了**: *確実で柔軟なシステム監視・通知基盤実装完了・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応・GitHub Actions統合・監視統合*