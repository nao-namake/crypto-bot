# Data Collection Scripts

Phase 12-2 実データ収集システム（レガシーTradingStatisticsManager改良版）

## 📂 スクリプト一覧

### **📊 trading_data_collector.py**

**Cloud Run実データ収集・統計管理システム（レガシー改良版）**

Cloud Runログから取引データを収集・分析し、体系的な統計管理を実現。レガシーTradingStatisticsManager・TradeRecord・DailyStatisticsの実績あるデータ構造を活用し、シンプルさと実用性のバランスを重視した個人開発最適化版。

#### 主要機能

**実データ収集**:
- **Cloud Runログ取得**: gcloudコマンド・JSON形式・タイムアウト対応
- **取引シグナル解析**: BUY/SELL/HOLDシグナル・信頼度・戦略種別自動判定
- **TradeRecord生成**: レガシー互換データ構造・完全型安全・CSV/JSON出力

**統計計算**:
- **日次統計**: 日別シグナル数・頻度・信頼度・システム稼働時間
- **パフォーマンス指標**: 総合統計・頻度分析・品質指標・収集成功率
- **包括的分析**: 時間当たりシグナル・高信頼シグナル・戦略別分析

**データエクスポート**:
- **CSV形式**: 取引データ・日次統計・表計算ソフト対応
- **JSON形式**: パフォーマンス指標・メタデータ・API連携準備
- **レポート生成**: サマリーレポート・統計情報・ファイル一覧

#### レガシー活用ポイント

**データ構造継承**:
```python
# レガシーTradingStatisticsManagerから継承
@dataclass
class TradeRecord:
    trade_id: str
    timestamp: str
    symbol: str = "BTC_JPY"
    side: str = "unknown"  # 'buy', 'sell', 'hold'
    signal_confidence: float = 0.0
    strategy_type: str = "unknown"

@dataclass  
class DailyStatistics:
    date: str
    total_signals: int = 0
    signal_frequency: float = 0.0  # signals per hour
    avg_confidence: float = 0.0

@dataclass
class PerformanceMetrics:
    total_signals: int = 0
    signals_per_hour: float = 0.0
    avg_confidence: float = 0.0
    high_confidence_signals: int = 0
```

**改良点**:
- **Cloud Run特化**: GCP環境最適化・ログクエリ効率化・リアルタイム収集
- **エラーハンドリング**: タイムアウト対応・例外処理・フォールバック機能
- **データ品質**: 正規表現解析・信頼度抽出・戦略種別判定・包括的統計
- **出力強化**: CSV/JSON両対応・メタデータ付与・ファイル管理統合

#### 使用方法

```bash
# 基本実行（24時間データ収集）
python scripts/data_collection/trading_data_collector.py

# 期間指定収集
python scripts/data_collection/trading_data_collector.py --hours 1   # 1時間
python scripts/data_collection/trading_data_collector.py --hours 6   # 6時間  
python scripts/data_collection/trading_data_collector.py --hours 48  # 48時間
python scripts/data_collection/trading_data_collector.py --hours 168 # 1週間

# サービス・出力ディレクトリ指定
python scripts/data_collection/trading_data_collector.py \
  --service crypto-bot-service-prod \
  --project my-crypto-bot-project \
  --region asia-northeast1 \
  --output logs/data_collection_prod

# 本番環境データ収集
python scripts/data_collection/trading_data_collector.py \
  --service crypto-bot-service \
  --hours 24 \
  --output logs/production_data
```

#### 出力ファイル

**CSV形式**:
```csv
# trades_20250818.csv - 取引データ
trade_id,timestamp,symbol,side,signal_confidence,strategy_type,status
20250818120000_buy,2025-08-18T12:00:00Z,BTC_JPY,buy,0.85,atr_based,detected

# daily_stats_20250818.csv - 日次統計
date,total_signals,buy_signals,sell_signals,hold_signals,signal_frequency,avg_confidence
2025-08-18,48,18,15,15,2.0,0.742
```

**JSON形式**:
```json
{
  "timestamp": "2025-08-18T12:00:00",
  "collection_period_hours": 24,
  "performance_metrics": {
    "total_signals": 48,
    "signals_per_hour": 2.0,
    "avg_confidence": 0.742,
    "high_confidence_signals": 28
  },
  "daily_stats_summary": {
    "total_days": 1,
    "avg_signals_per_day": 48.0
  },
  "data_files": {
    "trades_csv": "logs/data_collection/trades_20250818.csv",
    "daily_stats_csv": "logs/data_collection/daily_stats_20250818.csv"
  }
}
```

#### Phase 12-2統合活用

**A/Bテスト基盤**:
- **ベースライン収集**: 現行システムのパフォーマンス基準値測定
- **バリアント比較**: 新旧モデル・戦略の定量的比較データ提供
- **統計分析支援**: t検定・信頼区間・有意性検証用データ準備

**ダッシュボード連携**:
- **リアルタイムデータ**: 最新取引統計・パフォーマンス指標提供
- **可視化対応**: Chart.js・HTML表示用JSON形式データ
- **履歴分析**: 日次・週次・月次トレンド分析支援

**継続監視**:
- **品質指標**: データ収集成功率・システム稼働率・エラー率追跡
- **傾向分析**: シグナル頻度・信頼度・戦略効果の長期推移
- **アラート生成**: 異常値検知・パフォーマンス低下・システム異常通知

## 🎯 データ収集戦略

### **収集頻度**
```bash
# 短期監視（1-6時間）- リアルタイム確認
python scripts/data_collection/trading_data_collector.py --hours 1

# 日次分析（24時間）- 標準運用
python scripts/data_collection/trading_data_collector.py --hours 24

# 週次レビュー（168時間）- トレンド分析
python scripts/data_collection/trading_data_collector.py --hours 168
```

### **品質保証**
- **データ完整性**: 必須フィールド検証・型チェック・範囲確認
- **重複除去**: タイムスタンプベース・ID重複チェック・クリーニング
- **エラーハンドリング**: ログ取得失敗・解析エラー・ファイル出力エラー対応

### **パフォーマンス**
- **効率的クエリ**: gcloudコマンド最適化・必要データのみ取得・タイムアウト設定
- **メモリ管理**: 大容量データ対応・ストリーミング処理・リソース効率化
- **並列処理**: 複数期間・複数サービス・バッチ処理対応（将来拡張）

## 🔧 カスタマイズ・拡張

### **フィルタリング強化**
```python
# カスタムログクエリ（trading_data_collector.py内で調整）
cmd = [
    "gcloud", "logging", "read",
    f"resource.type=\"cloud_run_revision\" AND "
    f"resource.labels.service_name=\"{service_name}\" AND "
    f"(jsonPayload.message~\"CUSTOM_SIGNAL\" OR "  # カスタムシグナル追加
    f"textPayload~\"STRATEGY_CHANGE\") AND "        # 戦略変更ログ追加
    f"timestamp >= \"{start_time_str}\"",
]
```

### **統計指標追加**
```python
# PerformanceMetricsに追加指標
@dataclass
class PerformanceMetrics:
    # 既存指標...
    strategy_distribution: Dict[str, int] = field(default_factory=dict)
    confidence_histogram: List[int] = field(default_factory=list)
    hourly_signal_pattern: Dict[str, float] = field(default_factory=dict)
```

### **出力形式拡張**
```bash
# 将来の拡張予定
python scripts/data_collection/trading_data_collector.py --format parquet  # Apache Parquet
python scripts/data_collection/trading_data_collector.py --database-url postgresql://  # DB保存
python scripts/data_collection/trading_data_collector.py --bigquery-table my_table    # BigQuery
```

## 📊 監視・運用

### **日次データ収集**
```bash
# 毎日定期実行推奨
0 6 * * * cd /path/to/bot && python scripts/data_collection/trading_data_collector.py --hours 24
```

### **データ品質チェック**
```bash
# 収集データ確認
ls -la logs/data_collection/
head -10 logs/data_collection/trades_*.csv
cat logs/data_collection/performance_metrics_*.json | jq .
```

### **ディスク容量管理**
```bash
# 古いデータのクリーンアップ（30日以上）
find logs/data_collection/ -name "*.csv" -mtime +30 -delete
find logs/data_collection/ -name "*.json" -mtime +30 -delete
```

## 🔮 Future Enhancements

### **Phase 13拡張予定**
- **リアルタイム収集**: WebSocket・ストリーミング・即座分析
- **機械学習統合**: 異常検知・パターン認識・予測分析
- **大容量対応**: BigQuery・Dataflow・分散処理
- **高度な統計**: 時系列分析・相関分析・因果推論

### **統合アーキテクチャ**
- **データパイプライン**: ETL処理・データ品質管理・メタデータ管理
- **API化**: REST API・GraphQL・リアルタイムクエリ
- **監視統合**: Grafana・Prometheus・アラート自動化

---

**Phase 12-2実装完了**: レガシーTradingStatisticsManagerの良い部分を継承・改良し、Cloud Run環境に最適化された実用的なデータ収集・統計管理システムを確立