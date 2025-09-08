# config/backtest/ - バックテスト専用設定

## 🎯 役割・責任

バックテスト実行時に本番環境の設定を変更・破損することなく、独立した設定環境を提供します。本番用設定（`config/production/`）とは完全に分離された専用設定ファイル群です。

## 📂 ファイル構成

```
config/backtest/
├── base.yaml            # バックテスト専用メイン設定
├── feature_order.json   # 特徴量定義
├── thresholds.yaml      # 閾値・パラメータ設定
└── README.md            # このファイル
```

## 🔧 各ファイルの役割

### **base.yaml**
- **mode: backtest** でバックテストモードを指定
- 取引所設定（API制限、タイムアウト等）
- ML設定（信頼度閾値、アンサンブル設定等）
- 戦略設定（使用する戦略と重み設定）
- リスク管理設定（Kelly基準、最大ドローダウン等）

### **feature_order.json**
- 機械学習で使用する特徴量の定義
- 特徴量の順序と分類情報
- バックテストで使用する特徴量セットの管理

### **thresholds.yaml**
- 各種閾値の動的設定
- ML予測の信頼度閾値
- 取引実行の判断基準
- システム監視の設定値

## 📝 使用方法

### **基本的な使用方法**
```bash
# バックテスト実行時にこの設定を指定
python scripts/backtest/run_backtest.py --config config/backtest/base.yaml

# 設定ファイルを指定してメインシステム実行
python main.py --config config/backtest/base.yaml --mode backtest
```

### **設定ファイルの読み込み**
```python
from src.core.config import load_config

# バックテスト専用設定で初期化
config = load_config("config/backtest/base.yaml")
```

## ⚠️ 注意事項

### **本番環境との分離**
- **完全独立**: 本番設定（`config/production/`）には一切影響しません
- **安全性**: バックテスト実行中に本番取引が影響を受けることはありません
- **データ分離**: バックテスト結果は独立したディレクトリに保存されます

### **設定変更時の注意**
- バックテスト設定の変更は本番環境に影響しません
- 新しい戦略やパラメータの検証に安全に使用できます
- 設定ファイルの構造は本番設定と同じ形式を維持してください

## 🔗 関連ファイル

- **`config/production/`**: 本番用設定（このフォルダとは完全分離）
- **`scripts/backtest/`**: バックテスト実行スクリプト
- **`src/backtest/`**: バックテストエンジン実装