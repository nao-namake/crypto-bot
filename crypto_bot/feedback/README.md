# feedback/ - フィードバックループ・継続的改善

## 📋 概要

**Feedback Loop & Continuous Improvement System**  
本フォルダは crypto-bot のフィードバックループ機能を提供し、予測結果の収集・分析、パラメータ自動更新、継続的学習、適応最適化を実現します。

## 🎯 主要機能

### **フィードバック収集**
- 予測結果と実際の結果の比較
- 取引結果の記録
- 市場環境変化の追跡
- パフォーマンスメトリクス収集

### **分析・評価**
- 予測精度の統計分析
- エラーパターン検出
- 市場レジーム認識
- 改善機会の特定

### **自動更新**
- パラメータ動的調整
- 信頼度閾値の最適化
- 重み係数の更新
- 戦略切り替え

### **継続的学習**
- オンライン学習統合
- モデル再訓練トリガー
- 特徴量重要度更新
- 適応的最適化

## 📁 ファイル構成

```
feedback/
└── feedback_loop_manager.py    # フィードバックループ管理システム
```

## 🔍 ファイルの役割

### **feedback_loop_manager.py**
- `FeedbackLoopManager`クラス - フィードバック管理本体
- `FeedbackType` Enum - フィードバック種別定義
- `FeedbackRecord`データクラス - フィードバック記録
- 予測結果追跡・分析
- パラメータ自動更新機能
- Phase C2実装

## 🚀 使用方法

### **基本的なフィードバック収集**
```python
from crypto_bot.feedback.feedback_loop_manager import FeedbackLoopManager

# フィードバックマネージャー初期化
feedback_manager = FeedbackLoopManager(
    update_interval_minutes=60,
    min_samples_for_update=100,
    confidence_threshold=0.8
)

# 予測結果の記録
feedback_manager.record_prediction(
    prediction_id="pred_123",
    predicted_value=1,  # BUY予測
    confidence=0.85,
    features=feature_dict
)

# 実際の結果を記録
feedback_manager.record_outcome(
    prediction_id="pred_123",
    actual_value=1,  # 実際に上昇
    profit=0.02      # 2%利益
)
```

### **自動パラメータ更新**
```python
# 更新コールバック登録
feedback_manager.register_update_callback(
    parameter="confidence_threshold",
    callback=lambda new_value: strategy.set_threshold(new_value)
)

# 自動更新開始
feedback_manager.start_automatic_updates()

# 手動更新トリガー
if feedback_manager.should_update_parameters():
    updates = feedback_manager.calculate_parameter_updates()
    feedback_manager.apply_updates(updates)
```

### **分析レポート生成**
```python
# パフォーマンス分析
analysis = feedback_manager.analyze_performance(
    time_window=timedelta(days=7)
)

print(f"予測精度: {analysis['accuracy']:.2%}")
print(f"平均信頼度: {analysis['avg_confidence']:.2%}")
print(f"高信頼度予測の精度: {analysis['high_conf_accuracy']:.2%}")

# 改善提案
suggestions = feedback_manager.get_improvement_suggestions()
for suggestion in suggestions:
    print(f"提案: {suggestion['action']} - 期待効果: {suggestion['expected_improvement']}")
```

## ⚠️ 課題・改善点

### **ファイル数不足**
- フィードバック機能に対して単一ファイルのみ
- より細分化されたモジュールが必要
- 機能別分離の検討

### **統合不足**
- オンライン学習との密結合
- A/Bテストとの連携
- リアルタイム更新機能

### **分析機能限定**
- より高度な統計分析
- 機械学習ベース最適化
- 多変量分析対応

### **永続化**
- フィードバックデータの長期保存
- 履歴分析機能
- トレンド検出

## 📝 今後の展開

1. **フィードバックシステム拡充**
   ```
   feedback/
   ├── collection/        # データ収集
   │   ├── collector.py
   │   ├── validator.py
   │   └── storage.py
   ├── analysis/         # 分析エンジン
   │   ├── accuracy.py
   │   ├── patterns.py
   │   └── anomaly.py
   ├── optimization/     # 最適化
   │   ├── parameter.py
   │   ├── strategy.py
   │   └── portfolio.py
   └── reporting/        # レポート生成
       ├── dashboard.py
       └── alerts.py
   ```

2. **高度な分析機能**
   - 因果推論
   - 時系列分析
   - クラスタリング
   - 異常検知

3. **自動化強化**
   - リアルタイム適応
   - 予測的最適化
   - 自己修復機能
   - 継続的デプロイ

4. **エンタープライズ機能**
   - 監査ログ
   - コンプライアンス対応
   - 承認ワークフロー
   - マルチテナント対応