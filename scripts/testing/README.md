# Testing Scripts

テスト・検証・実証系スクリプト集（Phase 12 CI/CD統合・手動実行監視・段階的デプロイテスト対応）

## 📂 スクリプト一覧

### test_live_trading.py
**ライブトレードテストスクリプト（Phase 12対応・CI/CD統合・本番前検証）**

実取引環境での動作検証・パフォーマンステスト・統合動作確認・CI/CD統合・手動実行監視テストを行う本番前最終テストスクリプト。

#### 主要機能
- **ライブAPI接続テスト**: Bitbank本番API・認証・レート制限確認・Workload Identity統合
- **エンドツーエンドテスト**: データ取得→特徴量→予測→リスク管理→注文の全フロー・CI/CD統合
- **パフォーマンステスト**: レイテンシー・メモリ使用量・処理時間測定・GitHub Actions対応
- **異常系テスト**: ネットワーク断・API エラー・例外処理の検証・段階的デプロイ対応
- **監視統合テスト**: 手動実行監視・Discord通知・自動復旧・パフォーマンス追跡

#### 使用例
```bash
# ライブトレードテスト実行（CI/CD統合）
python scripts/testing/test_live_trading.py

# 詳細ログモード（監視・デバッグ用）
python scripts/testing/test_live_trading.py --verbose

# 特定期間テスト（手動実行監視テスト）
python scripts/testing/test_live_trading.py --duration 3600  # 1時間

# ペーパートレードモード（段階的デプロイテスト）
python scripts/testing/test_live_trading.py --paper-trade

# 異常系テスト（CI/CD品質ゲート）
python scripts/testing/test_live_trading.py --stress-test

# GitHub Actions統合テスト（推奨・Phase 12対応）
python scripts/testing/test_live_trading.py --ci-mode

# 統合管理CLI経由実行（推奨）
python scripts/management/dev_check.py health-check
```

#### テスト項目
```
✅ API接続テスト
├── 認証確認（APIキー・シークレット）
├── レート制限遵守（1秒間隔）
├── データ取得（OHLCV・ティッカー・残高）
└── エラーハンドリング（404・500・タイムアウト）

✅ データパイプラインテスト  
├── マルチタイムフレーム取得（15m・1h・4h）
├── データ品質確認（欠損値・異常値）
├── キャッシュ機能（ヒット率・更新タイミング）
└── 同期処理（タイムスタンプ整合性）

✅ 機械学習テスト
├── 特徴量生成（12個・実データ）
├── モデル予測（アンサンブル・信頼度）
├── 予測レイテンシー（100ms以内目標）
└── メモリ使用量（500MB以下目標）

✅ 取引実行テスト
├── リスク管理（Kelly基準・ドローダウン）
├── 注文生成（最小単位・スプレッド考慮）
├── 異常検知（価格スパイク・出来高異常）
└── ペーパートレード（実資金使用なし）
```

## 🎯 設計原則

### テスト哲学
- **実環境優先**: 可能な限り本番環境と同条件でのテスト・CI/CD環境対応
- **安全性重視**: ペーパートレード・最小取引単位での検証・段階的デプロイ
- **包括的カバレッジ**: 正常系・異常系・エッジケースの網羅・監視統合テスト
- **自動化**: 人的ミス排除・再現可能な検証手順・GitHub Actions統合

### テスト戦略（Phase 12 CI/CD統合）
- **段階的検証**: コンポーネント→統合→エンドツーエンド・CI/CD対応
- **リスク管理**: 実資金使用前の十分な検証期間・手動実行監視・自動復旧
- **性能基準**: レイテンシー・メモリ・CPU使用率の明確な基準・SLA対応
- **品質ゲート**: 全テスト合格後の本番移行・段階的リリース・ロールバック対応

## 📊 テスト結果評価

### 成功基準
```python
# API接続テスト
api_latency < 500  # ms
api_success_rate > 99.5  # %
rate_limit_compliance = True

# データ品質テスト  
data_completeness > 99.9  # %
cache_hit_rate > 80  # %
sync_accuracy = True

# ML性能テスト
prediction_latency < 100  # ms
model_confidence > 0.5  # 閾値
memory_usage < 500  # MB

# 取引実行テスト
risk_check_accuracy = 100  # %
order_validation = True
paper_trade_success = True
```

### パフォーマンス指標
```
🚀 レイテンシー
├── データ取得: < 500ms
├── 特徴量生成: < 200ms  
├── ML予測: < 100ms
└── リスク評価: < 50ms

💾 メモリ使用量
├── ベースライン: < 200MB
├── データキャッシュ: < 300MB
├── ML予測: < 500MB
└── ピーク使用量: < 800MB

⚡ CPU使用率
├── 通常動作: < 30%
├── バックテスト: < 70%
├── モデル学習: < 90%
└── 待機時: < 10%
```

## 🔧 トラブルシューティング

### よくあるエラー

**1. API認証エラー**
```bash
❌ Bitbank API認証失敗
```
**対処**: 認証情報確認
```bash
# 環境変数確認
echo $BITBANK_API_KEY
echo $BITBANK_API_SECRET

# 手動認証テスト
python -c "
import ccxt
exchange = ccxt.bitbank({
    'apiKey': 'your_api_key',
    'secret': 'your_secret',
    'sandbox': False
})
ticker = exchange.fetch_ticker('BTC/JPY')
print('✅ API認証成功')
"
```

**2. レイテンシー超過**
```bash
❌ レイテンシーテスト失敗: 1200ms > 500ms
```
**対処**: ネットワーク・処理最適化
```bash
# ネットワーク確認
ping api.bitbank.cc

# 処理時間分析
python scripts/testing/test_live_trading.py --profile
```

**3. メモリ使用量超過**
```bash
❌ メモリ使用量テスト失敗: 800MB > 500MB
```
**対処**: メモリプロファイリング・最適化
```bash
# メモリ使用量監視
python scripts/testing/test_live_trading.py --memory-monitor

# GC強制実行・キャッシュクリア
```

**4. 予測精度問題**
```bash
❌ ML予測テスト失敗: confidence 0.3 < 0.5
```
**対処**: モデル再学習・データ確認
```bash
# モデル状態確認
python scripts/management/dev_check.py ml-models --dry-run

# 特徴量品質確認
python scripts/management/dev_check.py data-check
```

## 📈 テスト自動化

### CI/CD統合（Phase 12対応）
```yaml
# GitHub Actions例（Phase 12対応）
- name: Live Trading Test Phase 12
  run: |
    python scripts/testing/test_live_trading.py --ci-mode --duration 300
    python scripts/testing/test_live_trading.py --stress-test --github-actions
    python scripts/management/dev_check.py health-check
    python scripts/management/dev_check.py validate --mode light
```

### 定期実行
```bash
# cron設定例（毎日午前2時）
0 2 * * * cd /app && python scripts/testing/test_live_trading.py --paper-trade
```

### アラート統合
```python
# Discord通知統合
if test_result.failed:
    discord.send_alert(
        level="CRITICAL",
        message=f"ライブトレードテスト失敗: {test_result.error}"
    )
```

## 🔮 テストシナリオ

### 基本シナリオ
```python
scenarios = [
    "normal_market_conditions",     # 通常市場環境
    "high_volatility",             # 高ボラティリティ
    "low_volume",                  # 低出来高
    "api_rate_limit",              # API制限
    "network_latency",             # ネットワーク遅延
    "data_quality_issues",         # データ品質問題
    "model_confidence_edge_cases", # ML信頼度エッジケース
    "risk_management_triggers",    # リスク管理発動
]
```

### ストレステスト
```python
stress_tests = [
    "continuous_operation_24h",    # 24時間連続稼働
    "memory_leak_detection",       # メモリリーク検出
    "concurrent_request_handling", # 同時リクエスト処理
    "api_error_recovery",          # API エラー復旧
    "graceful_shutdown",           # グレースフルシャットダウン
]
```

## 💡 Best Practices

### 安全性
- **ペーパートレード優先**: 実資金使用前の十分な検証
- **最小取引単位**: 実取引時も最小単位から開始
- **段階的展開**: 10%→50%→100%の資金投入
- **緊急停止**: 異常検知時の即座停止機能

### 信頼性
- **冗長性**: 複数環境での並行テスト
- **回復力**: 障害からの自動復旧テスト
- **監視**: リアルタイムパフォーマンス監視
- **バックアップ**: テスト設定・結果の保存

### 効率性
- **並列実行**: 可能なテストの並列化
- **キャッシュ活用**: テストデータの再利用
- **選択実行**: 変更箇所に応じた部分テスト
- **早期終了**: クリティカルエラー時の即座停止

## 🔮 Future Enhancements

Phase 12以降の拡張予定:
- **Visual Testing**: チャート・ダッシュボードの視覚的回帰テスト・UI自動化
- **Performance Regression**: 性能劣化検知システム・ベンチマーク・パフォーマンス追跡
- **Chaos Engineering**: 意図的障害注入テスト・resilience engineering・fault injection
- **User Acceptance**: 本番ユーザビリティテスト・E2Eテスト・シナリオベーステスト
- **Security Testing**: 脆弱性・侵入テスト自動化・SAST/DAST・コンプライアンステスト
- **Load Testing**: 大規模負荷テスト・スケーラビリティテスト・容量計画
- **Contract Testing**: API契約テスト・スキーマ検証・バージョン互換性