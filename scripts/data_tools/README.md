# scripts/data_tools/ - データ準備・分析ツール

## 📋 概要

取引データの準備、分析、クリーニング、キャッシュ作成など、データ関連の操作を行うツールを集約したディレクトリです。

## 🎯 ツール一覧

### **prepare_initial_data.py** ⭐ 重要
初期データの事前取得

```bash
# 環境変数設定後に実行
export BITBANK_API_KEY="your-key"
export BITBANK_API_SECRET="your-secret"
python scripts/data_tools/prepare_initial_data.py
```

**機能:**
- 72時間分のOHLCVデータ取得
- 97特徴量事前計算
- cache/initial_data.pkl として保存
- 本番デプロイ前に実行推奨

### **create_minimal_cache.py**
CI/CD用最小限キャッシュ作成

```bash
python scripts/data_tools/create_minimal_cache.py
```

**用途:**
- CI環境用ダミーデータ生成
- API認証不要
- リアリスティックなBTC/JPY価格
- 72時間分のデータ

### **analyze_training_data.py**
学習データの統計分析

```bash
python scripts/data_tools/analyze_training_data.py
```

**分析内容:**
- データ分布
- 欠損値チェック
- 特徴量相関
- 時系列パターン
- 異常値検出

### **market_data_analysis.py**
市場データの詳細分析

```bash
python scripts/data_tools/market_data_analysis.py --period 30
```

**分析項目:**
- 価格トレンド
- ボラティリティ
- 出来高分析
- 相場パターン
- サポート・レジスタンス

### **create_backtest_data.py**
バックテスト用データ作成

```bash
python scripts/data_tools/create_backtest_data.py --start 2024-01-01 --end 2024-12-31
```

**オプション:**
- 期間指定
- 特徴量選択
- データ分割設定
- 保存形式（CSV/Pickle）

### **clean_historical_data.py**
履歴データのクリーニング

```bash
python scripts/data_tools/clean_historical_data.py
```

**処理内容:**
- 欠損値補完
- 異常値除去
- データ正規化
- 重複削除
- 時系列整合性確認

### **pre_compute_data.py**
データ事前計算

```bash
python scripts/data_tools/pre_compute_data.py
```

**計算内容:**
- テクニカル指標
- 特徴量エンジニアリング
- 統計量算出
- キャッシュ生成

## 💡 推奨ワークフロー

### **本番デプロイ前のデータ準備**

```bash
# 1. 初期データ準備
python scripts/data_tools/prepare_initial_data.py

# 2. データ品質確認
python scripts/data_tools/analyze_training_data.py

# 3. クリーニング（必要に応じて）
python scripts/data_tools/clean_historical_data.py

# 4. デプロイ
bash scripts/ci_tools/deploy_with_initial_data.sh
```

### **モデル再学習前のデータ準備**

```bash
# 1. 市場データ分析
python scripts/data_tools/market_data_analysis.py --period 90

# 2. 学習データ準備
python scripts/data_tools/create_backtest_data.py --start 2024-01-01

# 3. データ品質確認
python scripts/data_tools/analyze_training_data.py

# 4. モデル学習
python scripts/model_tools/manage_models.py retrain --features 97
```

### **CI/CD環境のデータ準備**

```bash
# ダミーデータ作成
python scripts/data_tools/create_minimal_cache.py

# CI実行
bash scripts/ci_tools/validate_all.sh --ci
```

## 📊 データ仕様

### **OHLCVデータ形式**
```python
{
    'timestamp': datetime,
    'open': float,
    'high': float,
    'low': float,
    'close': float,
    'volume': float
}
```

### **キャッシュファイル**
- `cache/initial_data.pkl` - 初期データキャッシュ
- `cache/feature_cache.pkl` - 特徴量キャッシュ
- `cache/market_data.pkl` - 市場データキャッシュ

### **データ期間要件**
- 最小: 72時間（3日）
- 推奨: 2,304時間（96日）
- 理想: 8,760時間（365日）

## ⚠️ 注意事項

- **API制限**: Bitbank APIは1時間あたりの制限あり
- **データサイズ**: 大量データ取得時はメモリに注意
- **キャッシュ**: 定期的にクリアして最新化
- **本番データ**: 実データでのテストは慎重に

## 🔍 トラブルシューティング

### **データ取得エラー**
```bash
# API認証確認
python scripts/utilities/test_bitbank_auth.py

# キャッシュクリア
rm -rf cache/*.pkl

# 再取得
python scripts/data_tools/prepare_initial_data.py
```

### **データ品質問題**
```bash
# 分析実行
python scripts/data_tools/analyze_training_data.py

# クリーニング
python scripts/data_tools/clean_historical_data.py
```

### **CI/CDでデータ不足**
```bash
# ダミーデータ作成
python scripts/data_tools/create_minimal_cache.py
```

---

*最終更新: 2025年8月11日 - フォルダ整理実施*