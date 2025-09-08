# scripts/analytics/ - データ分析・監視スクリプト

## 🎯 役割・責任

システム運用データの収集、分析、可視化、監視を担当する分析スクリプト群を管理します。取引データ、システム性能、品質指標の統計分析から、リアルタイム監視、HTMLダッシュボード生成、Discord通知まで、包括的な分析・監視システムを提供し、データ駆動型の運用改善を支援します。

## 📂 ファイル構成

```
scripts/analytics/
├── README.md                    # このファイル
├── base_analyzer.py             # 共通基盤クラス・ログ取得・システム監視
├── data_collector.py            # データ収集・統計分析・CSV/JSON出力
├── performance_analyzer.py      # システム性能分析・パフォーマンス監視
└── dashboard.py                 # HTMLダッシュボード・可視化・レポート生成
```

## 📋 主要ファイル・フォルダの役割

### **base_analyzer.py**
分析システムの共通基盤クラスとユーティリティ機能を提供します。
- Cloud Runログ取得とシステム監視機能
- 共通データ構造と処理メソッド
- エラーハンドリングと例外処理
- ログパターン解析とメトリクス抽出
- 他の分析スクリプトの基盤コンポーネント
- 約20KBの実装ファイル

### **data_collector.py**
システム運用データの収集と統計分析を担当します。
- 取引データの収集と統計計算（勝率、収益、シグナル頻度）
- システム稼働データの取得と分析
- 品質メトリクス（テスト結果、カバレッジ）の収集
- CSV/JSON形式でのデータ出力
- 時系列データ分析と傾向把握
- Discord通知との統合機能
- 約17KBの実装ファイル

### **performance_analyzer.py**
システム性能とパフォーマンス分析を実行します。
- システムヘルス監視（CPU、メモリ、レスポンス時間）
- 機械学習モデルの性能分析
- 学習時間とモデル更新の監視
- エラーパターン検出と分析
- 改善提案の自動生成
- 長期トレンド分析と比較
- 約22KBの実装ファイル

### **dashboard.py**
HTMLダッシュボードと可視化レポートを生成します。
- Chart.jsを使用したインタラクティブな可視化
- 取引統計とモデル性能のグラフ表示
- テスト結果とカバレッジの可視化
- Discord連携による自動レポート配信
- HTMLレポートの自動生成と保存
- リアルタイムデータの更新機能
- 約23KBの実装ファイル

## 📝 使用方法・例

### **基本的な分析ワークフロー**
```bash
# 24時間のデータ収集・分析
python3 scripts/analytics/data_collector.py --hours 24

# システム性能分析（7日間）
python3 scripts/analytics/performance_analyzer.py --period 7d

# HTMLダッシュボード生成（Discord通知付き）
python3 scripts/analytics/dashboard.py --discord

# 統合分析レポート（30日間）
python3 scripts/analytics/performance_analyzer.py --period 30d --format json
```

### **詳細データ収集と分析**
```python
from scripts.analytics.base_analyzer import CloudRunAnalyzer
from scripts.analytics.data_collector import TradingDataCollector

# システム初期化
analyzer = CloudRunAnalyzer()
collector = TradingDataCollector()

# データ収集実行
trading_data = collector.collect_trading_statistics(hours=168)  # 1週間
system_analysis = analyzer.run_analysis(hours=168, include_health_check=True)

# 結果確認
print(f"取引データ: {len(trading_data['trades'])}件")
print(f"勝率: {trading_data['win_rate']:.2%}")
print(f"システム稼働率: {system_analysis['uptime']:.1%}")
```

### **可視化とレポート生成**
```python
from scripts.analytics.dashboard import DashboardGenerator

# ダッシュボード生成
dashboard = DashboardGenerator()

# HTMLレポート作成
report_path = dashboard.generate_dashboard(
    hours=24,
    include_charts=True,
    send_to_discord=True
)

print(f"ダッシュボード生成完了: {report_path}")
```

### **長期トレンド分析**
```bash
# 月次包括的分析
python3 scripts/analytics/performance_analyzer.py \
  --period 30d \
  --format json \
  --output-path logs/reports/analytics/

# 週次比較レポート
python3 scripts/analytics/dashboard.py \
  --hours 168 \
  --discord \
  --comparison-mode

# 品質メトリクス推移分析
python3 scripts/analytics/data_collector.py \
  --quality-metrics \
  --period 14d \
  --export csv
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.13以上、必要ライブラリの完全インストール
- **実行場所**: プロジェクトルートディレクトリからの実行必須
- **権限設定**: GCPアクセス権限、Cloud Runログ取得権限の設定
- **外部依存**: Discord WebhookURL、GitHub Actions権限の設定

### **データアクセス制約**
- **ログアクセス**: Cloud Runサービスログへの読み取り権限
- **システム監視**: システムメトリクスとヘルスチェックアクセス
- **外部API**: レート制限内での適切なAPI呼び出し
- **データ保持**: 一時データとキャッシュの適切な管理

### **出力とレポート管理**
- **保存場所**: logs/reports/analytics/ディレクトリへの自動保存
- **ファイル形式**: JSON、CSV、HTMLの適切な形式選択
- **容量管理**: 大量レポートファイルによるディスク使用量注意
- **履歴管理**: 古いレポートファイルの定期クリーンアップ

### **推奨使用パターン**
- **日次監視**: data_collector.py + dashboard.pyによる定期実行
- **週次分析**: performance_analyzer.pyによる詳細パフォーマンス分析
- **月次レポート**: 全スクリプト統合実行による包括的分析
- **問題調査**: 特定期間・特定メトリクスに絞った詳細分析

## 🔗 関連ファイル・依存関係

### **データソースシステム**
- `src/features/feature_manager.py`: 特徴量生成統計データの取得
- `src/ml/ensemble.py`: モデル性能データとメトリクス取得
- `scripts/testing/dev_check.py`: システム診断結果の統合
- `logs/`: システムログ・取引ログ・品質ログの分析対象

### **出力・保存システム**
- `logs/reports/analytics/`: 分析結果の自動保存先
- `logs/reports/data_collection/`: データ収集結果の保存
- `logs/system/`: システムログとCloud Runデータ

### **外部システム統合**
- **GCP Cloud Run**: 本番システムログとメトリクスデータソース
- **Discord API**: 通知・レポート配信・アラート送信
- **Chart.js**: HTMLダッシュボードの可視化ライブラリ
- **GitHub Actions**: CI/CDパイプラインとの連携データ

### **設定・品質保証**
- `config/core/unified.yaml`: 統一設定ファイル（システム設定・パラメータ・全環境対応）
- `tests/unit/`: 分析スクリプトの動作検証テスト
- `scripts/testing/checks.sh`: 品質チェック結果の分析データ

### **Python依存ライブラリ**
- **pandas**: データ分析・統計計算・時系列処理
- **matplotlib/seaborn**: グラフ生成・可視化
- **requests**: API呼び出し・外部データ取得
- **json**: データ構造化・設定管理
- **datetime**: 時系列データ処理・期間計算

### **分析データフロー**
1. **データ収集**: システムログ・取引データ・品質メトリクス収集
2. **統計分析**: パフォーマンス計算・トレンド分析・比較評価
3. **可視化**: グラフ生成・ダッシュボード作成・レポート生成
4. **配信**: Discord通知・HTMLレポート保存・履歴管理
5. **監視**: 継続的分析・アラート・改善提案