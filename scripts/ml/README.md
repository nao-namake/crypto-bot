# scripts/ml/ - 機械学習・モデル管理

**Phase 13対応**: MLモデル作成・アンサンブル構築・メタデータ管理（2025年8月26日現在）

## 📂 ファイル構成

```
ml/
├── create_ml_models.py    # MLモデル作成・アンサンブル構築
└── README.md              # このファイル
```

## 🎯 役割・責任

機械学習・モデル管理として以下を提供：
- **MLモデル作成**: LightGBM・XGBoost・RandomForest個別学習
- **アンサンブル構築**: ProductionEnsemble統合・重み付け最適化
- **メタデータ管理**: モデル性能・学習パラメータ・検証結果記録
- **品質保証**: モデル検証・予測テスト・CI/CD統合

## 🤖 主要機能・実装

### **create_ml_models.py**: MLモデル作成・アンサンブル構築
- 3モデル学習（LightGBM・XGBoost・RandomForest）・ハイパーパラメータ最適化
- ProductionEnsemble統合・重み付けアンサンブル・性能評価
- 12特徴量最適化・sklearn警告解消・メタデータ生成
- models/production/・models/training/自動保存・バージョン管理

## 🔧 使用方法・例

### **基本使用方法**
```bash
# 通常実行（MLモデル作成・統合）
python scripts/ml/create_ml_models.py

# ドライラン（シミュレーション・事前チェック）
python scripts/ml/create_ml_models.py --dry-run

# 詳細ログ出力（デバッグ・監視用）
python scripts/ml/create_ml_models.py --verbose

# 学習期間指定
python scripts/ml/create_ml_models.py --days 360

# 統合管理CLI経由（推奨）
python scripts/management/dev_check.py ml-models
```

### **期待結果**
```
✅ 個別モデル学習完了 (LightGBM: 0.85, XGBoost: 0.83, RandomForest: 0.78)
✅ ProductionEnsemble統合完了 (総合F1: 0.87)
✅ models/production/production_ensemble.pkl 保存完了
✅ メタデータ・検証結果保存完了
```

## ⚠️ 注意事項・制約

### **実行環境制約**
1. **プロジェクトルート**: 必ず`/Users/nao/Desktop/bot`から実行
2. **Python環境**: scikit-learn・lightgbm・xgboost・pandas・numpy必須
3. **メモリ要件**: 最低1GB RAM・学習データサイズ依存
4. **実行時間**: 約5-20分（データ量・計算リソース依存）

### **データ要件**
- **最低データ量**: 1000サンプル以上推奨
- **特徴量**: 12特徴量完全セット必須
- **データ品質**: 欠損値・異常値事前処理済み
- **時系列データ**: 時間順ソート済み

### **出力管理**
- **models/production/**: production_ensemble.pkl・メタデータJSON
- **models/training/**: 個別モデル・学習ログ・性能指標
- **logs/**: 学習ログ・エラーログ・実行履歴

## 🔗 関連ファイル・依存関係

### **システム統合**
- **scripts/management/**: dev_check.py ml-models統合実行
- **src/ml/**: MLモデルクラス・アンサンブルシステム・予測エンジン
- **src/features/**: 特徴量生成・12特徴量セット・前処理パイプライン

### **データ・設定**
- **models/**: 学習済みモデル保存・メタデータ・バージョン管理
- **config/**: ML設定・ハイパーパラメータ・学習パラメータ
- **data/**: 学習データ・検証データ・テストデータ

### **外部依存**
- **scikit-learn**: 機械学習アルゴリズム・評価指標・前処理
- **LightGBM・XGBoost**: 勾配ブースティング・高性能学習
- **pandas・numpy**: データ処理・数値計算・特徴量処理

---

**🎯 Phase 13対応完了**: MLモデル作成・アンサンブル構築・メタデータ管理により高性能な機械学習システムを実現。