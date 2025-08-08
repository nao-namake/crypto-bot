# validation/ - 検証・A/Bテストシステム

## 📋 概要

**Validation & A/B Testing System**  
本フォルダは crypto-bot の検証機能を提供し、A/Bテスト実行、統計的有意性検定、戦略比較、実験管理を担当します。

## 🎯 主要機能

### **A/Bテスト管理**
- 実験設計・実行
- コントロール群/実験群管理
- ランダム割り当て
- 結果収集・分析

### **統計的検証**
- t検定・Mann-Whitney U検定
- 有意性検定（p値計算）
- 効果量計算
- 信頼区間推定

### **戦略比較**
- 複数戦略の並行評価
- パフォーマンス比較
- 動的重み vs 固定重み
- 最適戦略選択

### **実験管理**
- 実験履歴記録
- メタデータ管理
- 再現可能性確保
- レポート生成

## 📁 ファイル構成

```
validation/
└── ab_testing_system.py    # A/Bテスト・統計検証システム
```

## 🔍 ファイルの役割

### **ab_testing_system.py**
- `ABTestingSystem`クラス - A/Bテスト管理本体
- `ExperimentStatus` Enum - 実験状態管理
- `ExperimentResult`データクラス - 結果保存
- 統計的検定実装
- 可視化機能（Seaborn統合）
- Phase C2実装

## 🚀 使用方法

### **基本的なA/Bテスト**
```python
from crypto_bot.validation.ab_testing_system import ABTestingSystem

# A/Bテストシステム初期化
ab_system = ABTestingSystem()

# 実験設定
experiment = ab_system.create_experiment(
    name="Dynamic vs Fixed Weights",
    control_config={"weight_type": "fixed"},
    variant_config={"weight_type": "dynamic"},
    metrics=["win_rate", "sharpe_ratio", "total_return"]
)

# 実験実行
for data_batch in data_stream:
    # ランダム割り当て
    group = ab_system.assign_group(experiment.id)
    
    if group == "control":
        result = run_fixed_weight_strategy(data_batch)
    else:
        result = run_dynamic_weight_strategy(data_batch)
    
    # 結果記録
    ab_system.record_result(experiment.id, group, result)
```

### **統計的検証**
```python
# 結果分析
analysis = ab_system.analyze_experiment(experiment.id)

print(f"Control群平均: {analysis['control_mean']:.4f}")
print(f"Variant群平均: {analysis['variant_mean']:.4f}")
print(f"p値: {analysis['p_value']:.4f}")
print(f"統計的有意性: {analysis['is_significant']}")
print(f"効果量: {analysis['effect_size']:.4f}")

# 推奨判定
if analysis['is_significant'] and analysis['variant_mean'] > analysis['control_mean']:
    print("Variant戦略の採用を推奨")
```

### **複数戦略比較**
```python
# 多群比較
multi_test = ab_system.create_multi_variant_test(
    name="Strategy Comparison",
    strategies={
        "baseline": baseline_config,
        "ml_v1": ml_v1_config,
        "ml_v2": ml_v2_config,
        "ensemble": ensemble_config
    }
)

# 結果可視化
ab_system.visualize_results(
    experiment_id=multi_test.id,
    plot_type="boxplot",
    save_path="results/strategy_comparison.png"
)
```

## ⚠️ 課題・改善点

### **ファイル数不足**
- 検証機能に対して単一ファイルのみ
- より多様な検証ツールが必要
- モジュール分割の検討

### **機能拡張余地**
- ベイズA/Bテスト
- 逐次検定（早期停止）
- 多腕バンディット
- 因果推論

### **統合不足**
- バックテストとの連携
- オンライン学習との統合
- リアルタイム実験
- 自動最適化

### **可視化強化**
- インタラクティブダッシュボード
- リアルタイム結果表示
- 詳細な統計レポート

## 📝 今後の展開

1. **検証システム拡充**
   ```
   validation/
   ├── ab_testing/           # A/Bテスト
   │   ├── system.py
   │   ├── sequential.py     # 逐次検定
   │   └── bayesian.py       # ベイズA/B
   ├── statistical/          # 統計検証
   │   ├── hypothesis.py
   │   ├── correlation.py
   │   └── causality.py
   ├── backtesting/          # バックテスト検証
   │   ├── validator.py
   │   └── robustness.py
   └── reporting/            # レポート生成
       ├── generator.py
       └── templates/
   ```

2. **高度な検証手法**
   - オンラインA/Bテスト
   - 多変量テスト
   - バンディットアルゴリズム
   - 因果推論フレームワーク

3. **自動化・最適化**
   - 自動実験設計
   - ハイパーパラメータ探索統合
   - 継続的検証パイプライン
   - MLOps統合

4. **エンタープライズ機能**
   - 実験管理プラットフォーム
   - 承認ワークフロー
   - 監査ログ
   - コンプライアンス対応