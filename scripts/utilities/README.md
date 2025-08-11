# scripts/utilities/ - ユーティリティツール集

## 📋 概要

crypto-bot プロジェクトの補助ツール・診断ツール・監視ツールを管理するディレクトリです。  
Phase 2-3およびPhase 3で実装された高度な検証・監視・修復機能を提供します。

## 🎯 ディレクトリ構造

```
utilities/
├── README.md                    # このファイル
├── signal_monitor.py           # シグナル生成監視（Phase 2-2）
├── future_leak_detector.py     # 未来データリーク検出（Phase 2-3）
├── error_analyzer.py           # エラーパターン分析（Phase 3）
├── monitor_signals.sh          # シグナル監視ラッパー
├── check_gcp_env.sh           # GCP環境確認
├── setup_secrets.sh           # シークレット設定
├── monitor_deployment.sh      # デプロイメント監視
├── verify_wif_hardening.sh    # WIF強化検証
├── test_terraform_local.sh    # Terraformローカルテスト
├── generate_btc_csv_data.py   # BTCデータ生成
├── test_bitbank_auth.py       # Bitbank認証テスト
├── emergency_shutdown.py      # 緊急停止ツール
├── troubleshoot_deployment.sh # デプロイメント診断
└── bigquery_log_queries.sql   # BigQueryクエリ集
```

## 🚀 主要ツール詳細

### **📊 signal_monitor.py** (Phase 2-2)

**シグナル生成の健全性を監視**

```python
from utilities.signal_monitor import SignalMonitor

monitor = SignalMonitor(
    csv_path="logs/trading_signals.csv",
    report_dir="logs/monitoring"
)

# 監視実行
analysis = monitor.analyze_signals(hours=24)
monitor.generate_report(analysis)
```

**機能:**
- 1時間以上シグナルなし検出
- 連続パターン異常検出（30回連続HOLD等）
- Confidence値異常検出
- HTML/JSONレポート生成

**使用方法:**
```bash
# 直近24時間のシグナルを監視
python scripts/utilities/signal_monitor.py --hours 24

# アラート閾値を変更（デフォルト: 70）
python scripts/utilities/signal_monitor.py --hours 48 --threshold-alert 60
```

**連携:** crypto_bot/utils/signal_logger.py が生成するCSVを監視

---

### **🔍 future_leak_detector.py** (Phase 2-3)

**MLパイプラインの時系列整合性を検証**

```python
from utilities.future_leak_detector import FutureLeakDetector

detector = FutureLeakDetector()

# コード分析
issues = detector.analyze_feature_code("crypto_bot/ml/feature_master_implementation.py")

# バックテストデータ検証
detector.check_backtest_data_split(train_data, test_data)
```

**検出パターン:**
- `shift(-1)` などの未来参照
- `center=True` のrolling window
- 不適切なインデックス操作
- データ分割の時系列違反

**使用方法:**
```bash
# プロジェクト全体をスキャン
python scripts/utilities/future_leak_detector.py --project-root . --html

# 特定ファイルをチェック
python scripts/utilities/future_leak_detector.py --file crypto_bot/ml/feature_master_implementation.py

# CI/CD用（終了コードで判定）
python scripts/utilities/future_leak_detector.py --project-root .
echo $?  # 0: 問題なし, 1: リークあり
```

**レポート:** `logs/leak_detection/` にHTML/JSON形式で保存

---

### **🔧 error_analyzer.py** (Phase 3)

**エラーパターンを学習し、修復提案を生成**

```python
from utilities.error_analyzer import ErrorAnalyzer

analyzer = ErrorAnalyzer()

# エラー分析実行
analysis, suggestions = analyzer.run_analysis(source="both", hours=24)

# 修復成功を学習
analyzer.learn_from_resolution("api_auth_error", solution_index=0, success=True)
```

**定義済みエラーパターン（10種類）:**
1. `api_auth_error` - API認証エラー
2. `model_not_found` - モデルファイル不在
3. `data_fetch_error` - ネットワークエラー
4. `feature_mismatch` - 特徴量不一致
5. `memory_error` - メモリ不足
6. `import_error` - インポートエラー
7. `confidence_threshold` - 閾値関連
8. `database_connection` - DB接続エラー
9. `pandas_error` - DataFrame処理エラー
10. `timezone_error` - タイムゾーンエラー

**使用方法:**
```bash
# GCPとローカルログを分析
python scripts/utilities/error_analyzer.py --source both --hours 24

# GCPログのみ分析
python scripts/utilities/error_analyzer.py --source gcp --hours 48

# データベース更新
python scripts/utilities/error_analyzer.py --update-db
```

**データベース:** `data/error_solutions.json` に解決策と成功率を保存

---

## 🔗 統合ツール

### **monitor_signals.sh**

シグナル監視を定期実行するラッパースクリプト

```bash
# cronで1時間毎に実行
0 * * * * /path/to/scripts/utilities/monitor_signals.sh

# 手動実行
bash scripts/utilities/monitor_signals.sh
```

## 🛠️ 環境・インフラツール

### **check_gcp_env.sh**
GCP環境の設定確認
```bash
bash scripts/utilities/check_gcp_env.sh
```

### **setup_secrets.sh**
シークレット設定支援
```bash
bash scripts/utilities/setup_secrets.sh
```

### **test_terraform_local.sh**
Terraformをローカルでテスト
```bash
bash scripts/utilities/test_terraform_local.sh
```

## 📊 データ・テストツール

### **generate_btc_csv_data.py**
テスト用BTCデータ生成
```python
python scripts/utilities/generate_btc_csv_data.py --days 30 --output test_data.csv
```

### **test_bitbank_auth.py**
Bitbank API認証テスト
```python
python scripts/utilities/test_bitbank_auth.py
```

### **emergency_shutdown.py**
緊急停止ツール
```python
# すべての取引を停止
python scripts/utilities/emergency_shutdown.py --confirm
```

## 🔍 診断・トラブルシューティング

### **troubleshoot_deployment.sh**
デプロイメント問題の診断
```bash
bash scripts/utilities/troubleshoot_deployment.sh
```

### **bigquery_log_queries.sql**
BigQueryでのログ分析クエリ集
```sql
-- エラーログ検索
SELECT * FROM logs WHERE severity = 'ERROR' 
AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
```

## 📝 使用上の注意

### **統合CLIの利用推奨**

個別ツールの直接実行も可能ですが、統合CLIの利用を推奨します：

```bash
# 統合CLI経由での実行（推奨）
python scripts/bot_manager.py monitor --hours 24
python scripts/bot_manager.py leak-detect
python scripts/bot_manager.py fix-errors

# 個別実行（詳細制御が必要な場合）
python scripts/utilities/signal_monitor.py --hours 24 --threshold-alert 60
```

### **CI/CD統合**

GitHub Actions やその他のCI/CDツールと統合可能：

```yaml
# .github/workflows/ci.yml
- name: Future Leak Detection
  run: python scripts/utilities/future_leak_detector.py --project-root .
  
- name: Signal Monitoring
  run: python scripts/utilities/signal_monitor.py --hours 1
```

### **ログファイルの場所**

各ツールのレポート出力先：
- シグナル監視: `logs/monitoring/signal_analysis_*.html`
- リーク検出: `logs/leak_detection/leak_report_*.html`
- エラー分析: `logs/error_analysis/error_analysis_*.html`

## 🎯 トラブルシューティング

### **signal_monitor.py でCSVが見つからない**
```bash
# signal_logger.py が動作しているか確認
ls -la logs/trading_signals.csv

# 存在しない場合は、まずシグナル生成を実行
python -m crypto_bot.main live-bitbank --paper-trade --duration 60
```

### **error_analyzer.py でGCPログ取得失敗**
```bash
# GCP認証確認
gcloud auth list

# プロジェクト設定確認
gcloud config get-value project
```

### **future_leak_detector.py の誤検出**
```python
# 安全なパターンの例外設定
# safe_patterns.json に追加
{
  "exceptions": [
    "df['past_return'] = df['close'].shift(1)",  # 過去データ参照は安全
  ]
}
```

---

*最終更新: 2025年8月11日 - Phase 2-3/Phase 3実装*