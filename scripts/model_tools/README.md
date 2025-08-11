# scripts/model_tools/ - モデル管理ツール

## 📋 概要

機械学習モデルの作成・再学習・管理を行うツールを集約したディレクトリです。  
97特徴量システムのアンサンブルモデルを中心に、各種モデル操作を統合管理します。

## 🎯 統合管理ツール

### **manage_models.py** ⭐ 推奨
すべてのモデル操作を1つのツールで管理

```bash
# 本番用モデル作成
python scripts/model_tools/manage_models.py create --type production

# CI用モデル作成
python scripts/model_tools/manage_models.py create --type ci

# アンサンブルモデル作成
python scripts/model_tools/manage_models.py create --type ensemble

# 97特徴量モデル再学習
python scripts/model_tools/manage_models.py retrain --features 97
```

## 📦 個別ツール詳細

### **create_proper_ensemble_model.py**
97特徴量アンサンブルモデル作成（本番用）

```bash
python scripts/model_tools/create_proper_ensemble_model.py
```

**特徴:**
- LightGBM (weight: 0.5)
- XGBoost (weight: 0.3)
- RandomForest (weight: 0.2)
- TradingEnsembleClassifier形式
- confidence_threshold: 0.35

**出力:** `models/production/model.pkl`

### **create_production_model.py**
本番用モデル作成（DataFrame対応版）

```bash
python scripts/model_tools/create_production_model.py
```

**特徴:**
- DataFrame入力対応
- フォールバック機能
- 本番環境互換性確保

### **create_ci_model.py**
CI/CD環境用ダミーモデル作成

```bash
python scripts/model_tools/create_ci_model.py
```

**用途:**
- GitHub Actions でのテスト
- API認証なしでのモデルファイル生成
- モデルファイル不在エラー回避

### **retrain_97_features_model.py**
97特徴量モデルの再学習

```bash
python scripts/model_tools/retrain_97_features_model.py
```

**実行内容:**
1. 最新データ取得
2. 97特徴量生成
3. アンサンブルモデル学習
4. バックテスト評価
5. モデル保存

## 🔄 モデル管理ワークフロー

### **定期的な再学習（推奨：週1回）**

```bash
# 1. データ確認
python scripts/data_tools/analyze_training_data.py

# 2. モデル再学習
python scripts/model_tools/manage_models.py retrain --features 97

# 3. バックテスト評価
python -m crypto_bot.main backtest --config config/validation/ensemble_trading.yml

# 4. 本番昇格（検証後）
cp models/validation/best_model.pkl models/production/model.pkl
```

### **CI/CD用モデル準備**

```bash
# CI環境でモデルファイルがない場合
python scripts/model_tools/manage_models.py create --type ci
```

### **新規本番モデル作成**

```bash
# 1. アンサンブルモデル作成
python scripts/model_tools/manage_models.py create --type ensemble

# 2. 検証
python scripts/ci_tools/validate_97_features_optimization.py

# 3. デプロイ
git add models/production/model.pkl
git commit -m "feat: update production model"
git push origin main
```

## 📊 モデル性能指標

### **現在の本番モデル**
- **特徴量数:** 97
- **アンサンブル:** 3モデル統合
- **Confidence閾値:** 0.35
- **期待精度:** 〜65%
- **更新頻度:** 週1回推奨

### **評価指標**
- Accuracy
- Precision/Recall
- Sharpe Ratio
- Maximum Drawdown
- Win Rate

## ⚠️ 注意事項

- **本番モデル更新時** は必ずバックテストを実施
- **models/production/model.pkl** は固定ファイル名（変更不可）
- **CI用モデル** は本番では使用しないこと
- **再学習** には十分なデータ期間（最低3ヶ月）が必要

## 🔍 トラブルシューティング

### **モデルファイルが見つからない**
```bash
python scripts/model_tools/manage_models.py create --type production
```

### **予測精度が低い**
```bash
# データ品質確認
python scripts/data_tools/analyze_training_data.py

# 再学習実行
python scripts/model_tools/manage_models.py retrain --features 97
```

### **CI/CDでモデルエラー**
```bash
# CI用モデル作成
python scripts/model_tools/manage_models.py create --type ci
```

---

*最終更新: 2025年8月11日 - フォルダ整理・統合ツール追加*