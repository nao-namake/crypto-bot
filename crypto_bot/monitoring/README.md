# monitoring/ - 監視・品質管理システム

## 📋 概要

**Monitoring & Quality Management System**  
本フォルダは crypto-bot の監視機能を提供し、データ品質監視、パフォーマンス追跡、異常検知、アラート管理を担当します。

**📊 visualization/との差別化**:
- **monitoring/**: システム内部監視・品質管理・自動アラート（システム向け）
- **visualization/**: ユーザー分析・可視化・インタラクティブ操作（ユーザー向け）

## 🎯 主要機能

### **データ品質監視**
- 30%ルール実装（デフォルト値比率監視）
- 欠損値・異常値検出
- 品質スコアリング
- 自動品質回復判定

### **パフォーマンス監視**
- リアルタイム取引成績追跡
- 勝率・収益性・リスク指標計算
- パフォーマンス劣化検知
- 統計的有意性検定

### **アラート・対応**
- 多段階アラートレベル（INFO/WARNING/CRITICAL/EMERGENCY）
- 自動取引停止機能
- 品質回復時の自動再開
- アラート履歴管理

## 📁 ファイル構成

```
monitoring/
├── data_quality_monitor.py      # データ品質監視システム
└── performance_monitor.py       # パフォーマンス監視システム
```

## 🔍 各ファイルの役割

### **data_quality_monitor.py**
- `DataQualityMonitor`クラス - データ品質監視本体
- `QualityStatus` Enum - 品質状態定義
- `QualityMetrics`データクラス - 品質メトリクス
- 30%ルール実装 - デフォルト値使用率監視
- 緊急停止機能 - 品質劣化時の自動停止
- 回復判定 - 品質改善時の自動再開

### **performance_monitor.py**
- `PerformanceMonitor`クラス - パフォーマンス監視本体
- `AlertLevel` Enum - アラートレベル定義
- `PerformanceMetrics`データクラス - 成績指標
- リアルタイム統計計算
- 異常検知アルゴリズム
- DynamicWeightAdjusterとの統合

## 🚀 使用方法

### **データ品質監視**
```python
from crypto_bot.monitoring.data_quality_monitor import DataQualityMonitor

monitor = DataQualityMonitor(
    quality_threshold=0.7,  # 70%以上の品質要求
    recovery_threshold=0.8,  # 80%で回復判定
    monitoring_window=100    # 直近100件監視
)

# 品質チェック
quality_metrics = monitor.check_quality(features_df)
if quality_metrics.status == QualityStatus.EMERGENCY_STOP:
    # 取引停止処理
    stop_trading()
```

### **パフォーマンス監視**
```python
from crypto_bot.monitoring.performance_monitor import PerformanceMonitor

perf_monitor = PerformanceMonitor(
    alert_thresholds={
        "win_rate": 0.4,      # 勝率40%未満で警告
        "sharpe_ratio": 0.5,  # シャープレシオ0.5未満で警告
        "max_drawdown": 0.2   # 最大DD20%で警告
    }
)

# 取引結果記録
perf_monitor.record_trade(trade_result)

# パフォーマンス評価
metrics = perf_monitor.get_performance_metrics()
alerts = perf_monitor.check_alerts()
```

### **統合監視**
```python
# データ品質とパフォーマンスの統合監視
if data_quality_monitor.is_quality_acceptable() and \
   perf_monitor.is_performance_acceptable():
    # 取引継続
    continue_trading()
else:
    # 問題対応
    handle_issues()
```

## ⚠️ 課題・改善点

### **ファイル数不足**
- 監視機能に対してファイル数が少ない
- より細分化された監視モジュールが必要
- リソース監視、API監視等の追加

### **統合不足**
- 他のシステムコンポーネントとの連携強化
- 統一監視ダッシュボードの実装
- メトリクス集約システム

### **可視化機能**
- リアルタイムダッシュボード未実装
- 履歴データの可視化機能不足
- アラート通知の多様化

### **永続化**
- メトリクスデータの永続化機能
- 時系列データベース統合
- 長期トレンド分析機能

## 📝 今後の展開

1. **監視範囲拡大**
   - システムリソース監視（CPU/メモリ/ディスク）
   - API呼び出し監視（レート制限/エラー率）
   - ネットワーク監視（レイテンシ/スループット）
   - 取引所接続状態監視

2. **高度な異常検知**
   - 機械学習ベース異常検知
   - 予測的アラート
   - 根本原因分析
   - 自己修復機能

3. **統合ダッシュボード**
   - Grafana/Prometheus統合
   - リアルタイムメトリクス表示
   - カスタムアラートルール
   - モバイル通知対応

4. **分散監視**
   - マイクロサービス対応
   - 分散トレーシング
   - ログ集約・分析
   - サービスメッシュ統合