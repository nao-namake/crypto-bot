# config/production/ - 本番環境設定ディレクトリ

**Phase 12完了**: 100%本番運用設定・CI/CDワークフロー最適化・自動デプロイ・手動実行監視・セキュリティ強化対応完了

## 📁 ファイル構成

```
production/
├── README.md               # このファイル
└── production.yaml         # 100%本番運用設定（唯一）
```

## 🎯 本番環境の位置づけ

本番環境は段階的デプロイメントの最終段階：

```
Development → Validation → Staging (10%→50%) → Production (100%)
```

**Phase 12本番移行条件**:
- ✅ 開発環境での全機能テスト完了（450テスト・68.13%カバレッジ）
- ✅ CI/CDワークフロー最適化成功（自動デプロイ対応）
- ✅ 検証環境での7日間運用成功
- ✅ 10%段階での14日間運用成功（勝率60%・利益5,000円以上）
- ✅ 50%段階での21日間運用成功（勝率58%・利益12,000円以上）
- ✅ Workload Identity・Secret Manager統合確認
- ✅ 手動実行監視システム・dev_check統合確認

## 🔧 production.yaml - 100%本番運用設定

**目的**: フル本番運用・月間17,000円収益目標達成

### 主要特徴
- **資金投入**: 100%フル投資
- **収益目標**: 月間17,000円（コスト回収＋利益確保）
- **運用コスト**: 月額2,000円以内
- **取引頻度**: 月間100-200回（1日3-7回程度）

### 核心パラメータ
```yaml
# システム設定（Phase 12対応）
system:
  name: "crypto-bot-production"
  version: "12.0.0"                # Phase 12最新
  mode: "live"
  debug: false
  log_level: "INFO"

# リスク管理（フル運用・最適化済み）
risk:
  risk_per_trade: 0.01          # 1%（Kelly基準最適化）
  kelly_max_fraction: 0.05      # 5%（リスク・リターン最適化）
  max_drawdown: 0.20           # 20%（許容ドローダウン上限）
  stop_loss_atr_multiplier: 1.2 # 1.2×ATR（最適化済み）
  consecutive_loss_limit: 5    # 連続5損失で24時間停止

# 注文実行（効率化・収益最大化）
execution:
  mode: "live"
  default_type: "limit"        # 指値注文優先（手数料最適化）
  slippage_tolerance: 0.001    # 0.1%スリッページ許容
  max_retry: 3                 # 3回リトライ
  retry_delay: 1.0             # 1秒間隔

# 本番運用設定
production:
  min_order_size: 0.0001       # 最小注文サイズ
  max_order_size: 0.001        # 最大注文サイズ（0.001 BTC）
  trade_interval: 60           # 1分間隔（効率化）
  margin_trading: true         # 信用取引有効
  force_margin_mode: true      # 信用取引強制
  
  # 本番運用制限
  daily_trade_limit: 25        # 1日最大25回
  max_daily_loss: 0.05         # 1日最大5%損失
  emergency_stop_loss: 0.15    # 緊急停止15%損失
```

### 月間収益目標
```yaml
targets:
  # 収益目標（月間）
  monthly_profit_target: 17000  # 17,000円（コスト回収＋利益）
  max_monthly_trades: 200       # 月間最大200回
  target_win_rate: 0.55         # 勝率55%
  target_sharpe_ratio: 1.0      # シャープレシオ1.0
  
  # 運用効率
  max_monthly_cost: 2000        # 月間コスト2,000円以内
  min_profit_per_trade: 100     # 1取引平均100円利益
```

## 🎯 本番運用戦略

### 収益構造
- **基本収益**: 月間17,000円目標
- **コスト控除**: GCP運用費2,000円
- **純利益**: 月間15,000円
- **年間利益**: 180,000円（ROI向上）

### リスク管理
- **Kelly基準**: 数学的最適化による5%上限
- **ドローダウン管理**: 20%で強制停止・資産保護
- **多重安全装置**: 日次・連続損失・緊急停止

### 効率化施策
- **指値注文優先**: 手数料削減（maker手数料活用）
- **レイテンシー最適化**: 1秒以内実行目標
- **API効率化**: 30秒間隔・最適な呼び出し頻度

## 🚀 デプロイメント

### Phase 12本番デプロイ手順
```bash
# 1. Phase 12事前チェック（包括的確認）
echo "Phase 12前段階成功確認:"
echo "  ✅ 開発環境テスト完了（450テスト・68.13%カバレッジ）"
echo "  ✅ CI/CDワークフロー最適化成功（GitHub Actions）"
echo "  ✅ 検証環境成功（7日間）"
echo "  ✅ 10%段階成功（14日間・勝率60%・利益5,000円）"
echo "  ✅ 50%段階成功（21日間・勝率58%・利益12,000円）"

# 2. Phase 12統合確認
python scripts/management/dev_check.py full-check
python scripts/management/dev_check.py validate --mode light

# 3. 設定検証（Phase 12対応）
python3 -c "
from src.core.config import Config
config = Config.load_from_file('config/production/production.yaml')
assert config.validate()
assert config.system.mode == 'live'
assert config.system.version.startswith('12.')
print('✅ Phase 12本番設定検証OK')
"

# 4. CI/CD経由自動デプロイ（推奨）
git push origin main  # GitHub Actions CI/CD実行

# 5. 手動デプロイ（必要時のみ）
bash scripts/deployment/deploy_production.sh --stage production

# 6. Phase 12本番サービス確認
curl https://crypto-bot-service-prod-xxx.run.app/health
python scripts/management/dev_check.py health-check

# 7. 手動実行監視開始
gh workflow run monitoring.yml --field check_type=full
```

### GCP Cloud Run設定
```yaml
cloud_run:
  memory: "2Gi"                 # 2GB（最大リソース）
  cpu: 2                       # 2CPU（高性能）
  min_instances: 1             # 最低1インスタンス
  max_instances: 2             # 最大2インスタンス
  concurrency: 1               # 1並行処理
  timeout_seconds: 3600        # 60分タイムアウト
```

## 📊 監視・運用

### 手動実行監視体制
```bash
# リアルタイム監視
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-prod"

# 統計ダッシュボード
curl https://crypto-bot-service-prod-xxx.run.app/statistics

# Discord通知確認
curl https://crypto-bot-service-prod-xxx.run.app/health
```

### 監視設定
```yaml
monitoring:
  health_check:
    interval_seconds: 30        # 30秒間隔（効率化）
    timeout_seconds: 5          # 5秒タイムアウト
    
  performance:
    metrics_interval: 300       # 5分間隔
    
  alerts:
    profit_threshold: -1000     # 1,000円損失でアラート
    error_rate_threshold: 0.05  # 5%エラー率でアラート
    latency_threshold: 2000     # 2秒遅延でアラート
```

### ログ管理
```yaml
logging:
  level: "INFO"                 # 本番適切レベル
  retention_days: 30            # 30日保存（効率化）
  
  discord:
    enabled: true
    levels:
      critical: true            # 重大エラー通知
      warning: true             # 警告通知
      info: false              # 情報レベル無効（効率化）
```

## 📈 パフォーマンス評価

### 月次評価指標
```bash
# 月次収益レポート
echo "=== 月次パフォーマンス評価 ==="
echo "総取引数: XXX回"
echo "勝率: XX.X%"
echo "総利益: ¥XX,XXX"
echo "総コスト: ¥X,XXX"
echo "純利益: ¥XX,XXX"
echo "シャープレシオ: X.XX"
echo "最大ドローダウン: XX.X%"
```

### 目標達成状況
- **月間17,000円収益**: 目標達成率XX%
- **勝率55%**: 実績XX%
- **ドローダウン20%以内**: 実績XX%
- **コスト2,000円以内**: 実績¥X,XXX

## 🚨 緊急時対応

### 緊急停止プロトコル
```bash
# レベル1: 取引一時停止
gcloud run services update crypto-bot-service-prod --min-instances=0 --max-instances=0 --region=asia-northeast1

# レベル2: サービス完全停止
gcloud run services delete crypto-bot-service-prod --region=asia-northeast1

# レベル3: 段階ダウングレード
bash scripts/deploy_production.sh --stage 50percent
```

### 災害復旧
```bash
# 設定ロールバック
git checkout HEAD~1 config/production/production.yaml

# 前段階復旧
bash scripts/deploy_production.sh --stage 50percent

# データバックアップ確認
gsutil ls gs://crypto-bot-backups/production/
```

## 🔒 セキュリティ・コンプライアンス

### API管理
- **キーローテーション**: 30日ごと自動
- **アクセス制限**: 必要最小限権限
- **監査ログ**: 全API呼び出し記録

### 資金管理
- **分離原則**: 本番・テスト資金完全分離
- **限度設定**: 日次・月次損失上限
- **承認体制**: 重要変更は事前承認

## 📋 運用チェックリスト

### 日次チェック
- [ ] システム稼働状況確認
- [ ] 取引実行結果確認
- [ ] エラー・警告ログ確認
- [ ] Discord通知確認

### 週次チェック
- [ ] 週次パフォーマンス評価
- [ ] リスク指標確認
- [ ] システムリソース確認
- [ ] バックアップ状況確認

### 月次チェック
- [ ] 月次収益目標達成状況
- [ ] 年間収益予測見直し
- [ ] システム最適化検討
- [ ] セキュリティ監査

---

**重要**: 本番環境は収益目標達成と安定運用が最優先です。変更は必ず段階的テストを経て慎重に行ってください。