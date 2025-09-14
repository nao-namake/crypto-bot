# scripts/analytics/ - システム分析基盤

## 🎯 役割・責任

システム分析・監視機能の共通基盤クラスを提供し、Cloud Runログ取得・gcloudコマンド実行・データ処理の統一インターフェースを提供します。主にdev_check.pyから利用され、システム診断・監視機能の中核を担います。

## 📂 ファイル構成

```
scripts/analytics/
├── README.md                    # このファイル
└── base_analyzer.py             # 共通分析基盤クラス（Phase 22最適化完了）
```

## 📋 主要ファイルの役割

### **base_analyzer.py**
システム分析・監視機能の共通基盤クラスとユーティリティ機能を提供します。
- Cloud Runログ取得とシステム監視機能
- gcloudコマンド実行の共通ラッパー
- ログ解析・シグナル頻度分析機能
- CSV/JSONファイル読み込み・保存機能
- dev_check.pyから利用される基盤コンポーネント

**主要機能**:
- `fetch_cloud_run_logs()`: Cloud Runサービスログ取得
- `fetch_error_logs()`: エラーログ専用取得
- `fetch_trading_logs()`: 取引関連ログ取得
- `check_service_health()`: Cloud Runサービス状態確認
- `parse_log_message()`: ログメッセージ解析
- `analyze_signal_frequency()`: シグナル頻度分析

## 📝 使用方法・例

### **dev_check.pyからの使用**
```python
# dev_check.pyでの実際の使用例
from analytics.base_analyzer import BaseAnalyzer

class DevCheck(BaseAnalyzer):
    def __init__(self):
        super().__init__(
            project_id="my-crypto-bot-project",
            service_name="crypto-bot-service",
            region="asia-northeast1"
        )
    
    def check_cloud_run_service(self):
        # BaseAnalyzerの機能を活用
        health_data = self.check_service_health()
        success, logs = self.fetch_trading_logs(hours=24)
        return health_data, logs
```

### **直接利用例**
```python
from scripts.analytics.base_analyzer import BaseAnalyzer

# 基盤クラス直接利用
analyzer = BaseAnalyzer()

# サービス状態確認
health_data = analyzer.check_service_health()
print(f"サービス状態: {health_data['service_status']}")

# 取引ログ分析
success, logs = analyzer.fetch_trading_logs(hours=24)
if success:
    signal_analysis = analyzer.analyze_signal_frequency(logs, 24)
    print(f"シグナル総数: {signal_analysis['total_signals']}")
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.12・必要ライブラリ（pandas）の完全インストール
- **実行場所**: プロジェクトルートディレクトリからの実行必須
- **権限設定**: GCPアクセス権限・Cloud Runログ取得権限の設定

### **GCP関連制約**
- **gcloud CLI**: インストール済み・認証設定完了が必要
- **Cloud Run権限**: サービス記述・ログ読み取り権限必須
- **レート制限**: GCP API呼び出し制限内での適切な使用

### **データ管理**
- **出力先**: `logs/`ディレクトリへの自動保存
- **ファイル形式**: JSON・CSV形式での構造化データ出力
- **一時データ**: メモリ効率とキャッシュ管理の配慮

## 🔗 関連ファイル・依存関係

### **主要利用システム**
- `scripts/testing/dev_check.py`: メイン利用先・システム診断機能
- `src/core/orchestration/`: システム統合制御との連携
- `logs/`: システムログ・分析結果の保存先

### **外部システム統合**
- **GCP Cloud Run**: 本番システムログとメトリクスデータソース
- **gcloud CLI**: コマンド実行・認証・データ取得インターフェース

### **設定・依存関係**
- `config/core/unified.yaml`: GCPプロジェクト設定・サービス名設定
- **Python依存**: pandas（データ処理）・datetime・pathlib・subprocess

---

## 🎯 Phase 22最適化成果

**最適化前**: dashboard.py・data_collector.py・performance_analyzer.py を含む4ファイル構成
**最適化後**: base_analyzer.pyのみの簡潔構成

**削除理由**: 
- 実行履歴なし・CI/CD未統合・コード品質問題・メンテナンス負荷回避
- dev_check.pyからbase_analyzer.pyのみ使用実績

**効果**: 約62KBの未使用コード削減・保守効率向上・システム構成簡素化