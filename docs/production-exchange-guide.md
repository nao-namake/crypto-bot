# 本番取引所運用ガイド

## 概要

このドキュメントでは、crypto-botを実際の取引所で運用するための手順、注意事項、テスト方法について説明します。

## サポート取引所

| 取引所 | テストネット | 現物取引 | 先物取引 | 実装状況 |
|--------|-------------|---------|---------|----------|
| **Bybit** | ✅ | ✅ | ✅ | 完全実装 |
| **Bitbank** | ❌ | ✅ | ❌ | 本番実装済み |
| **BitFlyer** | ❌ | ✅ | ✅ (Lightning FX) | 本番実装済み |
| **OKCoinJP** | ❌ | ✅ | ❌ | 本番実装済み |

## 事前準備

### 1. APIキーの取得

各取引所でAPIキーを取得し、適切な権限を設定してください。

#### Bybit
- **推奨**: まずTestnetでテスト
- **権限**: 現物・先物取引、残高照会
- **IP制限**: セキュリティ強化のため設定推奨

#### Bitbank
- **権限**: 取引、資産の参照
- **IP制限**: 設定可能

#### BitFlyer
- **権限**: 取引、残高照会、Lightning FX（必要に応じて）
- **IP制限**: 設定可能

#### OKCoinJP
- **権限**: 現物取引、残高照会
- **パスフレーズ**: 追加のセキュリティレイヤー
- **IP制限**: 設定推奨

### 2. 環境変数の設定

```bash
# Bybit (Testnet推奨)
export BYBIT_TESTNET_API_KEY="your_testnet_api_key"
export BYBIT_TESTNET_API_SECRET="your_testnet_secret"

# Bitbank (本番環境)
export BITBANK_API_KEY="your_bitbank_api_key"
export BITBANK_API_SECRET="your_bitbank_secret"

# BitFlyer (本番環境)
export BITFLYER_API_KEY="your_bitflyer_api_key"
export BITFLYER_API_SECRET="your_bitflyer_secret"

# OKCoinJP (本番環境)
export OKCOINJP_API_KEY="your_okcoinjp_api_key"
export OKCOINJP_API_SECRET="your_okcoinjp_secret"
export OKCOINJP_PASSPHRASE="your_okcoinjp_passphrase"
```

### 3. 設定ファイルの更新

`config/default.yml` の `data.exchange` を使用したい取引所に変更：

```yaml
data:
  exchange: "bybit"  # or "bitbank", "bitflyer", "okcoinjp"
  symbol: "BTC/USDT"  # 取引所に応じて適切なシンボルに変更
  # ...
```

## 安全なテスト手順

### ステップ1: API互換性チェック

```bash
# 全取引所の互換性チェック
bash scripts/run_production_tests.sh -a -c

# 特定の取引所のみ
bash scripts/run_production_tests.sh -c bitbank
```

### ステップ2: 基本機能テスト

```bash
# 残高照会・データ取得のみ（注文なし）
bash scripts/run_production_tests.sh bitbank

# 詳細ログ付き
bash scripts/run_production_tests.sh -v bitbank
```

### ステップ3: 最小額注文テスト（要注意）

⚠️ **警告**: このテストは実際の注文を発生させる可能性があります

```bash
# 最小額での注文・キャンセルテスト
bash scripts/run_production_tests.sh -s bitbank
```

### ステップ4: 段階的運用開始

1. **ペーパーモード**: データ取得のみで動作確認
2. **最小額運用**: 最小取引単位での実運用
3. **段階的増額**: 成功実績に応じて取引額を増加

## 取引所固有の注意事項

### Bybit
- **Testnet使用推奨**: 本格運用前に必ずTestnetでテスト
- **レバレッジ設定**: 先物取引時は適切なレバレッジを設定
- **レート制限**: 120リクエスト/分

### Bitbank
- **現物のみ**: 先物取引は非対応
- **最小取引単位**: 0.0001 BTC（銘柄により異なる）
- **レート制限**: 60リクエスト/分
- **手数料**: Maker 0.02%, Taker 0.12%

### BitFlyer
- **Lightning FX**: 専用の設定が必要
- **最小取引単位**: 0.001 BTC
- **レート制限**: 100リクエスト/分
- **手数料**: 銘柄・取引方法により異なる

### OKCoinJP
- **パスフレーズ必須**: API v3では必須
- **レート制限**: 20リクエスト/分（厳格）
- **最小取引単位**: 0.001 BTC
- **手数料**: 0.05-0.15%

## エラー対応

### よくあるエラーと対処法

#### 認証エラー
```
AuthenticationError: Invalid API key
```
- APIキーとシークレットを再確認
- IP制限の設定を確認
- パスフレーズ（OKCoinJP）の設定を確認

#### レート制限エラー
```
RateLimitExceeded: Too many requests
```
- リクエスト間隔を調整
- 取引所ごとの制限値を確認
- バックオフアルゴリズムの実装を検討

#### 残高不足エラー
```
InsufficientFunds: Not enough balance
```
- 残高を確認
- 最小取引単位を下回っていないか確認
- 手数料分の余裕があるか確認

#### API仕様変更エラー
```
BadRequest: Unknown symbol/parameter
```
- API仕様の変更を確認
- CCXTライブラリのアップデートを確認
- 取引所のメンテナンス情報を確認

## モニタリング

### 重要な監視項目

1. **API接続状況**: 接続エラー・タイムアウトの監視
2. **残高変動**: 想定外の残高変動の検知
3. **注文状況**: 未約定注文の蓄積監視
4. **レイテンシ**: API応答時間の監視
5. **エラー率**: エラー発生頻度の監視

### Cloud Monitoring連携

```python
# カスタムメトリクスの例
from crypto_bot.monitor import push_custom_metric

# 取引実行時のメトリクス送信
push_custom_metric("crypto_bot/trade_executed", 1, {
    "exchange": "bitbank",
    "symbol": "BTC/JPY",
    "side": "buy"
})

# エラー発生時のメトリクス送信
push_custom_metric("crypto_bot/api_error", 1, {
    "exchange": "bitbank",
    "error_type": "RateLimitExceeded"
})
```

## セキュリティ対策

### APIキー管理
- **環境変数**: 本番環境ではシークレット管理サービスを使用
- **権限最小化**: 必要最小限の権限のみ付与
- **IP制限**: 本番サーバーのIPアドレスのみに制限
- **定期ローテーション**: セキュリティポリシーに従って定期的に更新

### アクセス制御
- **VPN接続**: 可能な場合はVPN経由でのアクセス
- **ファイアウォール**: 不要なポートの閉鎖
- **ログ監視**: 不正アクセスの検知

### データ保護
- **残高情報**: 機密情報として適切に保護
- **取引履歴**: 必要に応じて暗号化保存
- **ログマスキング**: APIキー等の機密情報をログに出力しない

## 緊急時対応

### 緊急停止手順
1. **手動停止**: Ctrl+C または SIGTERM
2. **未約定注文キャンセル**: 全ての未約定注文を確認・キャンセル
3. **ポジション確認**: 保有ポジションを確認・必要に応じてクローズ

### 障害時の連絡先
- **取引所サポート**: 各取引所の緊急連絡先
- **開発チーム**: システム管理者への連絡方法
- **インシデント管理**: エスカレーション手順

## 法的コンプライアンス

### 税務対応
- **取引記録**: 全ての取引を記録・保存
- **損益計算**: 適切な会計処理
- **申告準備**: 税務申告に必要な資料の整備

### 規制対応
- **金商法**: 金融商品取引法の遵守
- **反社チェック**: 適切なKYC/AML対応
- **データ保護**: 個人情報保護法の遵守

## トラブルシューティング

### デバッグコマンド

```bash
# API接続テスト
python -c "
from crypto_bot.execution.factory import create_exchange_client
client = create_exchange_client('bitbank')
print(client.fetch_balance())
"

# 互換性レポート生成
python -c "
from crypto_bot.execution.api_version_manager import ApiVersionManager
manager = ApiVersionManager()
report = manager.generate_compatibility_report()
print(json.dumps(report, indent=2, ensure_ascii=False))
"

# 取引所情報取得
python -c "
from crypto_bot.execution.api_version_manager import ApiVersionManager
manager = ApiVersionManager()
info = manager.get_exchange_client_info('bitbank')
print(json.dumps(info, indent=2, ensure_ascii=False))
"
```

### ログレベル調整

```yaml
# config/default.yml
logging:
  level: DEBUG  # 詳細ログ出力
  handlers:
    - console
    - file
  file_path: logs/production.log
```

## パフォーマンス最適化

### 推奨設定

```yaml
# 本番環境向け最適化設定
execution:
  rate_limit_margin: 0.8  # レート制限の80%で動作
  retry_attempts: 3
  retry_delay: 1.0
  timeout: 30.0

data:
  cache_enabled: true
  cache_ttl: 30  # 30秒キャッシュ
```

### リソース管理
- **メモリ使用量**: 長時間運用時のメモリリーク監視
- **CPU使用率**: 高頻度取引時の負荷監視
- **ネットワーク**: 帯域幅使用量の監視

## 更新・メンテナンス

### 定期メンテナンス項目
1. **依存ライブラリ更新**: セキュリティアップデートの適用
2. **API仕様確認**: 取引所API仕様の変更確認
3. **ログローテーション**: ディスク容量管理
4. **バックアップ**: 設定ファイル・取引履歴のバックアップ

### アップデート手順
1. **テスト環境での検証**: 新バージョンの事前テスト
2. **段階的リリース**: 一部環境での限定リリース
3. **本番適用**: 監視体制下での本番適用
4. **ロールバック準備**: 問題発生時の復旧手順

---

## 関連ドキュメント

- [APIバージョン管理](../crypto_bot/execution/api_version_manager.py)
- [統合テスト仕様](../tests/integration/)
- [Cloud Monitoring設定](../docs/monitoring-setup.md)
- [セキュリティポリシー](../docs/security-policy.md)