# config/staging/ - 段階的デプロイメント設定ディレクトリ

**Phase 13完了**: 段階的デプロイメント・sklearn警告解消・306テスト100%成功・本番稼働開始・CI/D品質保証完全統合・MLモデル品質管理・自動監視・本番移行準備システム完了

## 📁 ファイル構成

```
staging/
├── README.md                    # このファイル
├── stage_10percent.yaml         # 10%資金投入段階
└── stage_50percent.yaml         # 50%資金投入段階
```

## 🎯 段階的デプロイメント戦略

Phase 12では、リスクを最小化するため段階的デプロイシステムを完備：

```
Development → Validation → Staging → Production
    ↓              ↓         ↓           ↓
ペーパートレード  検証環境   段階的実運用  フル本番運用
                           CI/CDワークフロー最適化    手動監視
```

### Phase 12段階別移行条件
1. **開発環境**: 全機能テスト完了（450テスト・68.13%カバレッジ）
2. **CI/CDワークフロー最適化**: GitHub Actions品質チェック・自動デプロイ確認
3. **検証環境**: 7日間・30取引・勝率55%以上
4. **10%段階**: 14日間・50取引・勝率55%・利益5,000円以上
5. **50%段階**: 21日間・100取引・勝率55%・利益12,000円以上
6. **本番環境**: 完全移行・手動実行監視体制

## 🔧 設定ファイル詳細

### stage_10percent.yaml - 10%資金投入段階
**目的**: 初期本番運用・最大限保守的設定

**特徴**:
- **資金比率**: 10%（保守的）
- **リスク管理**: 0.5%ポジション・10%最大ドローダウン
- **取引制限**: 1日最大10回・0.0002 BTC上限
- **監視強化**: 15秒ヘルスチェック・全レベル通知

**主要パラメータ**:
```yaml
system:
  name: "crypto-bot-stage-10percent"
  mode: "live"

risk:
  risk_per_trade: 0.005         # 0.5%
  kelly_max_fraction: 0.02      # 2%
  max_drawdown: 0.10           # 10%
  consecutive_loss_limit: 3    # 連続3損失で停止

production:
  max_order_size: 0.0002       # 0.0002 BTC
  daily_trade_limit: 10        # 1日10回
  emergency_stop_loss: 0.05    # 5%緊急停止
```

**成功条件**:
- **評価期間**: 14日間
- **最低取引数**: 50取引
- **勝率目標**: 60%以上
- **利益目標**: 5,000円以上
- **最大ドローダウン**: 10%以内

### stage_50percent.yaml - 50%資金投入段階
**目的**: 中間段階・バランス型運用

**特徴**:
- **資金比率**: 50%（バランス型）
- **リスク拡大**: 0.8%ポジション・15%最大ドローダウン
- **取引拡大**: 1日最大15回・0.0005 BTC上限
- **効率化**: 20秒ヘルスチェック・情報レベル通知無効

**主要パラメータ**:
```yaml
system:
  name: "crypto-bot-stage-50percent"
  mode: "live"

risk:
  risk_per_trade: 0.008         # 0.8%
  kelly_max_fraction: 0.03      # 3%
  max_drawdown: 0.15           # 15%
  consecutive_loss_limit: 4    # 連続4損失で停止

production:
  max_order_size: 0.0005       # 0.0005 BTC
  daily_trade_limit: 15        # 1日15回
  emergency_stop_loss: 0.08    # 8%緊急停止
```

**成功条件**:
- **評価期間**: 21日間
- **最低取引数**: 100取引
- **勝率目標**: 58%以上
- **利益目標**: 12,000円以上
- **最大ドローダウン**: 15%以内

## 🚀 デプロイメント手順

### 10%段階デプロイ
```bash
# 1. 事前確認
python3 -c "
from src.core.config import Config
config = Config.load_from_file('config/staging/stage_10percent.yaml')
assert config.validate()
print('✅ 10%段階設定検証OK')
"

# 2. GCPデプロイ
bash scripts/deploy_production.sh --stage 10percent

# 3. 動作確認
curl https://crypto-bot-service-10percent-xxx.run.app/health
```

### 50%段階デプロイ
```bash
# 1. 10%段階成功確認
echo "10%段階結果確認:"
echo "  - 14日間運用完了"
echo "  - 勝率60%以上達成"
echo "  - 利益5,000円以上達成"
echo "  - ドローダウン10%以内"

# 2. 50%段階デプロイ
bash scripts/deploy_production.sh --stage 50percent

# 3. 監視開始
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-50percent"
```

## 📊 段階別パラメータ比較

### リスク管理パラメータ
| パラメータ | 10%段階 | 50%段階 | 100%本番 | 変化 |
|-----------|---------|---------|----------|------|
| risk_per_trade | 0.5% | 0.8% | 1.0% | 段階的拡大 |
| kelly_max_fraction | 2.0% | 3.0% | 5.0% | 段階的拡大 |
| max_drawdown | 10% | 15% | 20% | 段階的緩和 |
| daily_trade_limit | 10 | 15 | 25 | 段階的増加 |
| max_order_size | 0.0002 | 0.0005 | 0.001 | 段階的拡大 |

### 監視・効率化パラメータ
| パラメータ | 10%段階 | 50%段階 | 100%本番 | 変化 |
|-----------|---------|---------|----------|------|
| health_check_interval | 15s | 20s | 30s | 効率化 |
| discord_info_level | true | false | false | 効率化 |
| log_retention_days | 60 | 45 | 30 | 効率化 |
| memory | 1Gi | 1.5Gi | 2Gi | リソース拡大 |

## 🔍 監視・評価

### 自動評価システム
各段階で自動的に成功条件を判定：

```yaml
# stage_10percent.yaml 内の評価設定
targets:
  evaluation_period_days: 14
  min_trades_for_evaluation: 50
  
success_conditions:
  min_win_rate: 0.60
  max_drawdown: 0.10
  min_profit_jpy: 5000
  no_major_errors: true

upgrade_conditions:
  next_stage: "stage_50percent"
  auto_upgrade: false  # 手動確認必要
```

### 監視コマンド
```bash
# 段階別ログ監視
gcloud logging tail "resource.labels.service_name=crypto-bot-service-10percent"
gcloud logging tail "resource.labels.service_name=crypto-bot-service-50percent"

# 統計情報取得
curl https://crypto-bot-service-10percent-xxx.run.app/statistics
curl https://crypto-bot-service-50percent-xxx.run.app/statistics

# エラー監視
gcloud logging read "severity>=ERROR AND resource.labels.service_name=crypto-bot-service-10percent" --limit=10
```

## 🚨 緊急時対応

### 段階ダウングレード
```bash
# 50%→10%へのダウングレード
bash scripts/deploy_production.sh --stage 10percent

# 10%→停止
gcloud run services update crypto-bot-service-10percent --min-instances=0 --max-instances=0 --region=asia-northeast1

# 完全停止
gcloud run services delete crypto-bot-service-10percent --region=asia-northeast1
```

### アラート設定
```bash
# 損失アラート
gcloud alpha monitoring policies create --policy-from-file=monitoring/loss_alert_10percent.yaml

# エラー率アラート
gcloud alpha monitoring policies create --policy-from-file=monitoring/error_rate_alert_10percent.yaml
```

## 📈 成功評価基準

### 10%段階成功基準
- ✅ **運用期間**: 14日間継続運用
- ✅ **取引実績**: 最低50取引実行
- ✅ **勝率**: 60%以上達成
- ✅ **収益性**: 5,000円以上利益
- ✅ **安定性**: ドローダウン10%以内
- ✅ **信頼性**: 重大エラー発生なし

### 50%段階成功基準
- ✅ **運用期間**: 21日間継続運用
- ✅ **取引実績**: 最低100取引実行
- ✅ **勝率**: 58%以上達成
- ✅ **収益性**: 12,000円以上利益
- ✅ **安定性**: ドローダウン15%以内
- ✅ **効率性**: API遅延・エラー率改善

## 🎯 次段階移行判定

### 自動判定プロセス
1. **日次評価**: 24時間ごとの自動評価実行
2. **条件チェック**: 全成功条件の自動判定
3. **レポート生成**: Discord通知・詳細レポート作成
4. **手動確認**: 最終的な移行判断は手動実行

### 移行コマンド
```bash
# 10%→50%移行
echo "10%段階成功確認完了"
bash scripts/deploy_production.sh --stage 50percent

# 50%→100%移行
echo "50%段階成功確認完了"
bash scripts/deploy_production.sh --stage production
```

---

**重要**: 段階的デプロイメントは、リスク最小化と安定した本番移行のための重要なプロセスです。各段階の成功条件を満たしてから次段階に進んでください。