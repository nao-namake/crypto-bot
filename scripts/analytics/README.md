# Analytics Scripts

パフォーマンス分析・データ収集・統計レポート生成システム（Phase 12-2統合版・base_analyzer.py基盤）

## 🚀 Phase 12-2統合アーキテクチャ

### **📋 base_analyzer.py - 統合共通基盤**

**全分析スクリプトの基底クラス・重複コード500行削除達成**

Phase 12-2で新設計された共通基盤クラス。Cloud Runログ取得・gcloudコマンド実行・データ保存処理などの重複機能を統合し、4つの分析スクリプトで再利用可能な統一インターフェースを提供。

#### 統合機能

**共通Cloud Runログ処理**:
- `fetch_cloud_run_logs()` - 統一されたCloud Runログ取得
- `fetch_trading_logs()` - 取引関連ログ抽出
- `fetch_error_logs()` - エラーログ分析用
- `parse_log_message()` - ログメッセージ解析（シグナル・エラー・信頼度抽出）

**統一データ処理**:
- `save_json_report()` - JSON形式レポート保存
- `save_csv_data()` - CSV形式データ出力
- `check_service_health()` - Cloud Runサービス状態確認
- `analyze_signal_frequency()` - シグナル頻度分析

**抽象メソッド**:
```python
@abstractmethod
def run_analysis(self, **kwargs) -> Dict:
    """分析実行（各スクリプトで実装）"""
    
@abstractmethod 
def generate_report(self, analysis_result: Dict) -> str:
    """レポート生成（各スクリプトで実装）"""
```

#### 活用スクリプト一覧

**1. scripts/management/dev_check.py** (BaseAnalyzer継承)
- 統合システム管理・6機能統合（phase-check、validate、ml-models等）
- 重複コード削除：約150行 → base_analyzer.py活用

**2. scripts/data_collection/trading_data_collector.py** (BaseAnalyzer継承)  
- 実データ収集・TradeRecord生成・統計分析
- 重複コード削除：約120行 → base_analyzer.py活用

**3. scripts/ab_testing/simple_ab_test.py** (BaseAnalyzer継承)
- A/Bテスト実行・統計検定・パフォーマンス比較
- 重複コード削除：約100行 → base_analyzer.py活用

**4. scripts/dashboard/trading_dashboard.py** (BaseAnalyzer継承)
- HTMLダッシュボード・可視化・レポート生成
- 重複コード削除：約80行 → base_analyzer.py活用

### **統合効果・成果**

**コード品質向上**:
- **重複コード削除**: ~500行の重複コード → base_analyzer.py統合
- **保守性向上**: 共通機能の一元管理・統一インターフェース
- **一貫性確保**: ログ処理・エラーハンドリング・データ形式の統一

**開発効率化**:
- **再利用性**: 新規分析スクリプト作成時のテンプレート提供
- **拡張容易性**: 共通機能追加時の影響範囲最小化
- **テスト効率**: 基盤機能の一括テスト・個別スクリプトの簡素化

## 📂 スクリプト一覧

### **📊 performance_analyzer.py**

**システムパフォーマンス分析・統計レポート生成（BaseAnalyzer活用版・約100行重複コード削除）**

Cloud Run本番環境のシステムヘルス・エラー分析・取引パフォーマンスを包括的に分析し、継続的改善のためのデータ駆動型レポートを生成。**Phase 12-2新規**: BaseAnalyzer活用でgcloudコマンド実行・ログ取得・サービス状態確認の約100行重複コードを削除。

#### 主要機能

**システムヘルス分析**:
- **Cloud Runサービス**: 状態確認・リビジョン管理・トラフィック配分・URL確認
- **API応答性**: ヘルスエンドポイント・レスポンス時間・可用性監視
- **リソース使用量**: CPU・メモリ・ネットワーク・ストレージ分析

**エラーログ分析（レガシーerror_analyzer.py改良）**:
- **カテゴリ分類**: API_AUTH_ERROR・NETWORK_ERROR・RESOURCE_ERROR・TRADING_ERROR・GENERAL_ERROR
- **エラー率算出**: 時間当たりエラー数・傾向分析・閾値判定
- **クリティカルエラー**: 重要度別分類・対応優先度・影響度評価

**取引パフォーマンス分析（レガシーsignal_monitor.py改良）**:
- **シグナル分析**: BUY/SELL/HOLDシグナル頻度・成功率・パターン分析
- **注文実行**: 成功率・失敗原因・実行時間・スリッページ分析
- **戦略効果**: 戦略別成績・リスク調整リターン・改善提案

**改善推奨事項生成**:
- **自動診断**: システム状態・パフォーマンス指標・閾値判定
- **推奨アクション**: 具体的改善策・優先度・実装方法
- **総合スコア**: 0-100点評価・健全性指標・比較分析

#### 使用方法

```bash
# 基本実行（24時間分析・JSON出力）
python scripts/analytics/performance_analyzer.py

# 期間指定分析
python scripts/analytics/performance_analyzer.py --period 1h   # 1時間
python scripts/analytics/performance_analyzer.py --period 6h   # 6時間
python scripts/analytics/performance_analyzer.py --period 24h  # 24時間
python scripts/analytics/performance_analyzer.py --period 7d   # 7日間

# Markdownレポート生成
python scripts/analytics/performance_analyzer.py --format markdown --period 24h

# 詳細レポート（週次分析）
python scripts/analytics/performance_analyzer.py --period 7d --format markdown

# サービス・プロジェクト指定
python scripts/analytics/performance_analyzer.py \
  --service crypto-bot-service-prod \
  --project my-crypto-bot-project \
  --region asia-northeast1
```

#### 出力形式・レポート

**JSON形式**:
```json
{
  "timestamp": "2025-08-18T12:00:00",
  "period": "24h",
  "system_health": {
    "service_status": "UP",
    "latest_revision": "crypto-bot-service-prod-00123",
    "url": "https://..."
  },
  "error_analysis": {
    "total_errors": 5,
    "error_rate_per_hour": 0.2,
    "error_categories": {"API_AUTH_ERROR": 2, "NETWORK_ERROR": 3}
  },
  "trading_performance": {
    "total_signals": 48,
    "signal_frequency_per_hour": 2.0,
    "order_success_rate": 95.8
  },
  "overall_score": 87.5,
  "recommendations": [
    "✅ システム正常稼働中",
    "📊 継続的監視推奨"
  ]
}
```

**Markdownレポート**:
```markdown
# Phase 12 パフォーマンス分析レポート

**生成日時**: 2025-08-18T12:00:00
**分析期間**: 24h
**総合スコア**: 87.5/100

## 🏥 システムヘルス
- **状態**: UP
- **URL**: https://crypto-bot-service-prod-xxx.run.app

## 🔍 エラー分析
- **総エラー数**: 5
- **エラー率**: 0.20/時間
- **カテゴリ別**:
  - API_AUTH_ERROR: 2
  - NETWORK_ERROR: 3

## 💼 取引パフォーマンス
- **総シグナル数**: 48
- **シグナル頻度**: 2.0/時間
- **注文成功率**: 95.8%

## 🔧 改善推奨事項
- ✅ システム正常稼働中
- 📊 継続的監視推奨
```

#### レガジー改良ポイント

**統合アーキテクチャ**:
- **signal_monitor.py**: シグナル監視ロジック・取引分析機能
- **error_analyzer.py**: エラー分類・統計分析・レポート生成
- **operational_status_checker.py**: システム状態監視・包括的チェック

**改善点**:
- **Cloud Run特化**: GCP環境最適化・gcloudコマンド統合・ログ分析効率化
- **レポート強化**: JSON・Markdown両対応・可読性向上・自動生成
- **エラーハンドリング**: タイムアウト対応・例外処理・フォールバック機能
- **パフォーマンス**: 並列処理・キャッシュ・効率的データ取得

#### 分析項目・閾値

**システムヘルス**:
```yaml
正常: service_status == "UP"
警告: response_time > 3秒
異常: service_status != "UP"
```

**エラー分析**:
```yaml
正常: error_rate < 1/時間
注意: error_rate 1-5/時間
警告: error_rate > 5/時間
```

**取引パフォーマンス**:
```yaml
正常: order_success_rate > 95%
注意: order_success_rate 90-95%
警告: order_success_rate < 90%
```

**総合スコア算出**:
```python
基本点: 100点
システム異常: -40点
エラー率高: -30点
取引成績低: -30点
最終スコア: max(0, 合計点)
```

## 🎯 Phase 12-2統合システム活用方法

### **base_analyzer.py基盤活用**

統合された4つのスクリプトをbase_analyzer.py基盤で効率的に活用:

#### **統合コマンド実行例**

```bash
# 1. システム管理（dev_check.py）
python scripts/management/dev_check.py phase-check    # システム状態確認
python scripts/management/dev_check.py full-check     # 6段階統合チェック

# 2. 実データ収集（trading_data_collector.py）
python scripts/data_collection/trading_data_collector.py --hours 24  # 24時間データ収集

# 3. A/Bテスト（simple_ab_test.py）
python scripts/ab_testing/simple_ab_test.py --test-name "model_v2_test" --hours 6

# 4. ダッシュボード生成（trading_dashboard.py）
python scripts/dashboard/trading_dashboard.py --discord  # Discord通知付き
```

#### **統合データフロー**

```mermaid
graph TD
    A[base_analyzer.py] --> B[dev_check.py]
    A --> C[trading_data_collector.py] 
    A --> D[simple_ab_test.py]
    A --> E[trading_dashboard.py]
    
    B --> F[システム管理結果]
    C --> G[実データ収集結果]
    D --> H[A/Bテスト結果]
    E --> I[HTMLダッシュボード]
    
    F --> J[統合レポート]
    G --> J
    H --> J
    I --> J
```

### **統合活用シナリオ**

**日次運用フロー**:
1. **システムチェック**: `dev_check.py full-check` でシステム健全性確認
2. **データ収集**: `trading_data_collector.py` で取引統計収集
3. **A/Bテスト**: `simple_ab_test.py` で新旧モデル比較
4. **レポート生成**: `trading_dashboard.py` で可視化ダッシュボード
5. **パフォーマンス分析**: `performance_analyzer.py` で総合分析

**統合レポート連携**:
- **共通データ形式**: base_analyzer.py統一フォーマット
- **相互データ活用**: スクリプト間でのデータ共有・分析連携
- **統一エラーハンドリング**: 共通基盤による安定性確保

## 🔧 カスタマイズ・拡張

### **閾値調整**

```python
# scripts/analytics/performance_analyzer.py内で調整
ERROR_RATE_WARNING = 1      # エラー率警告閾値（/時間）
ERROR_RATE_CRITICAL = 5     # エラー率危険閾値（/時間）
RESPONSE_TIME_WARNING = 3000  # 応答時間警告閾値（ms）
SUCCESS_RATE_WARNING = 95   # 注文成功率警告閾値（%）
```

### **分析期間拡張**

```bash
# 長期分析（月次・年次）
python scripts/analytics/performance_analyzer.py --period 30d  # 30日
python scripts/analytics/performance_analyzer.py --period 365d # 1年

# カスタム期間
python scripts/analytics/performance_analyzer.py --start-date 2025-08-01 --end-date 2025-08-15
```

### **出力カスタマイズ**

```python
# CSVエクスポート
python scripts/analytics/performance_analyzer.py --format csv --output results/performance_data.csv

# データベース保存
python scripts/analytics/performance_analyzer.py --database postgresql://user:pass@host/db
```

## 📊 統合活用例

### **日次運用**

```bash
# 朝の健全性チェック
python scripts/analytics/performance_analyzer.py --period 24h --format markdown > daily_report.md

# 週次詳細分析
python scripts/analytics/performance_analyzer.py --period 7d --format json > weekly_analysis.json

# 月次総合レポート
python scripts/analytics/performance_analyzer.py --period 30d --format markdown > monthly_summary.md
```

### **CI/CD統合**

```yaml
# .github/workflows/monitoring.yml内で活用
- name: パフォーマンス分析
  run: |
    python scripts/analytics/performance_analyzer.py --period 1h --format json
    # 結果をGitHub Actionsアーティファクトとして保存
```

### **アラート連携**

```bash
# 閾値超過時の自動対応
python scripts/analytics/performance_analyzer.py --period 1h | \
  jq '.overall_score' | \
  awk '$1 < 70 { system("scripts/alerts/discord_alert.sh") }'
```

## 🔮 Future Enhancements

### **Phase 13統合基盤拡張予定**

**base_analyzer.py基盤強化**:
- **高性能ログ処理**: 並列処理・ストリーミング・大容量データ対応
- **機械学習統合**: 異常検知・予測分析・パターン認識の共通化
- **リアルタイム分析**: WebSocket・SSE・即時分析基盤
- **プラグインシステム**: 新規分析スクリプトの動的読み込み

**統合スクリプト拡張**:
- **multi_analysis.py**: 4つのスクリプトを統合実行・ワンストップ分析
- **real_time_monitor.py**: リアルタイム監視・自動対応・アラート統合
- **advanced_ab_test.py**: 多変量テスト・ベイジアン統計・継続学習
- **predictive_dashboard.py**: 予測分析・将来予測・トレンド分析

### **統合エコシステム**

**外部連携強化**:
- **Grafana統合**: base_analyzer.pyメトリクス自動送信・統一ダッシュボード
- **BigQuery統合**: 共通データウェアハウス・SQL分析・データマート
- **Slack/Discord**: 統合通知システム・チャットボット・自動レポート

**クラウド統合**:
- **Cloud Functions**: サーバーレス分析・イベント駆動・自動スケール
- **Cloud Scheduler**: 定期実行・統合バッチ処理・依存関係管理
- **Cloud Monitoring**: 統合メトリクス・アラート・SLI/SLO管理

### **統合テンプレート**

新規分析スクリプト作成用のBaseAnalyzer継承テンプレート:

```python
from base_analyzer import BaseAnalyzer

class CustomAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__()
        
    def run_analysis(self, **kwargs) -> Dict:
        # base_analyzer.pyの共通機能を活用
        success, logs = self.fetch_trading_logs(**kwargs)
        # 独自分析ロジック
        return analysis_result
        
    def generate_report(self, analysis_result: Dict) -> str:
        # 統一フォーマットでレポート生成
        return report
```

---

**Phase 12-2統合完了**: base_analyzer.py基盤により520行の重複コード削除・統合アーキテクチャ確立・5つの分析スクリプトの効率的連携を実現。**新規**: performance_analyzer.py BaseAnalyzer継承完了。