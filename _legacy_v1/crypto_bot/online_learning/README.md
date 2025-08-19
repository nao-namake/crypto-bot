# online_learning/ - オンライン学習・適応型システム

## 📋 概要

**Online Learning & Adaptive System**  
本フォルダは crypto-bot のオンライン学習機能を提供し、リアルタイムデータからの継続的学習、モデル更新、パフォーマンス追跡を実現します。

## 🎯 主要機能

### **インクリメンタル学習**
- ストリーミングデータからの逐次学習
- メモリ効率的なモデル更新
- 忘却係数による古いデータの影響減衰
- バッチ・サンプル・時間ベース更新

### **適応型モデル**
- 市場変化への自動適応
- ドリフト検出との連携
- 動的パラメータ調整
- アンサンブルモデル対応

### **パフォーマンス監視**
- リアルタイム精度追跡
- 学習曲線可視化
- 更新履歴管理
- A/Bテスト統合

### **スケジューリング**
- 定期的モデル更新
- 条件ベース更新トリガー
- リソース管理
- 並行学習制御

## 📁 ファイル構成

```
online_learning/
├── __init__.py       # パッケージ初期化
├── base.py          # 基底クラス・設定
├── models.py        # オンライン学習モデル実装
├── monitoring.py    # パフォーマンス監視
└── scheduler.py     # 更新スケジューラー
```

## 🔍 各ファイルの役割

### **base.py**
- `OnlineLearningConfig`データクラス - 設定管理
- `OnlineLearnerBase`抽象クラス - 共通インターフェース
- 更新戦略定義（sample/batch/time）
- メモリ管理設定
- パフォーマンス計算窓設定

### **models.py**
- `IncrementalModel`クラス - 基本実装
- River/sklearn統合
- SGDClassifier/Regressor対応
- アンサンブルオンライン学習
- モデル永続化・復元

### **monitoring.py**
- `OnlineLearningMonitor`クラス - 監視システム
- 精度メトリクス追跡
- 学習統計収集
- パフォーマンス劣化検出
- レポート生成

### **scheduler.py**
- `OnlineLearningScheduler`クラス - スケジューラー
- 定期更新タスク管理
- 条件ベーストリガー
- リソース制御
- 並行実行管理

## 🚀 使用方法

### **基本的なオンライン学習**
```python
from crypto_bot.online_learning.models import IncrementalModel
from crypto_bot.online_learning.base import OnlineLearningConfig

# 設定
config = OnlineLearningConfig(
    update_frequency="batch",
    batch_size=100,
    memory_window=10000
)

# モデル初期化
model = IncrementalModel(
    model_type="sgd",
    config=config
)

# ストリーミング学習
for X_batch, y_batch in data_stream:
    model.partial_fit(X_batch, y_batch)
    if model.should_evaluate():
        metrics = model.evaluate()
        print(f"Current accuracy: {metrics['accuracy']}")
```

### **スケジュール実行**
```python
from crypto_bot.online_learning.scheduler import OnlineLearningScheduler

scheduler = OnlineLearningScheduler()

# 定期更新設定
scheduler.schedule_periodic_update(
    model=model,
    interval_minutes=60,
    data_source=data_stream
)

# 条件ベース更新
scheduler.add_trigger(
    condition=lambda: model.performance < 0.6,
    action=lambda: model.intensive_update()
)

# スケジューラー開始
scheduler.start()
```

### **パフォーマンス監視**
```python
from crypto_bot.online_learning.monitoring import OnlineLearningMonitor

monitor = OnlineLearningMonitor(model)

# 監視開始
monitor.start_monitoring()

# 統計取得
stats = monitor.get_learning_stats()
print(f"Learning rate: {stats['learning_rate']}")
print(f"Samples seen: {stats['total_samples']}")
print(f"Current performance: {stats['current_performance']}")
```

## ⚠️ 課題・改善点

### **依存関係**
- River（オプショナル）の統合改善
- より多くのオンライン学習ライブラリ対応
- 統一インターフェース強化

### **メモリ管理**
- 大規模データでのメモリ効率化
- より高度な忘却メカニズム
- データ圧縮・サンプリング

### **並列化**
- 分散オンライン学習未対応
- マルチモデル並行学習
- GPU活用

### **評価機能**
- より詳細な評価メトリクス
- オンライン交差検証
- 統計的有意性テスト

## 📝 今後の展開

1. **高度なアルゴリズム**
   - ディープラーニング対応
   - 強化学習統合
   - メタ学習実装
   - 転移学習対応

2. **分散システム**
   - 分散オンライン学習
   - フェデレーテッド学習
   - エッジコンピューティング
   - ストリーム処理統合

3. **自動化強化**
   - ハイパーパラメータ自動調整
   - アーキテクチャ探索
   - 特徴量自動選択
   - 学習戦略最適化

4. **説明可能性**
   - オンライン特徴量重要度
   - 増分的SHAP値
   - 学習過程可視化
   - 異常検知説明