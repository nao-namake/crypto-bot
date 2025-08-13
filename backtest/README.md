# backtest/ - 統合バックテストシステム

## 📋 概要

**Integrated Backtest System**  
バックテスト関連のすべてを一箇所に集約した統合システムです。設定、結果、スクリプト、アーカイブを単一のフォルダで管理し、シンプルで保守しやすい構造を提供します。

## 🎯 主要機能

### **完全統合システム**
- すべてのバックテスト関連ファイルを一元管理
- 97特徴量から任意の指標組み合わせテスト
- 固定ファイル名・絶対パス対応
- production.yml設定継承

### **バックテストエンジン**
- ウォークフォワード分析対応
- JPY建て取引特化機能
- パフォーマンス評価・レポート生成
- 可視化（チャート生成）対応

## 📁 統合フォルダ構成

```
backtest/
├── README.md                    # このファイル（統合システム説明）
├── configs/                     # 設定ファイル集約
│   ├── README.md                # 設定ファイル使用方法
│   ├── base_backtest_config.yml # ベース設定（97特徴量フル）
│   ├── indicator_combination_samples.yml  # 指標組み合わせサンプル
│   └── test_rsi_macd_ema.yml    # テスト用設定例
├── results/                     # 結果ファイル集約
│   ├── *.csv                    # バックテスト結果CSV
│   ├── *.png                    # パフォーマンスチャート
│   └── *.log                    # ログファイル
├── scripts/                     # ヘルパースクリプト集約
│   └── run_backtest.py          # バックテスト実行ヘルパー
└── archive/                     # 古いファイルアーカイブ
```

## 🚀 クイックスタート

### **1. 基本的なバックテスト実行**
```bash
# RSI + MACD + EMAテスト
cd /Users/nao/Desktop/bot
python backtest/scripts/run_backtest.py test_rsi_macd_ema

# 97特徴量フルテスト
python backtest/scripts/run_backtest.py base_backtest_config
```

### **2. 結果確認**
```bash
# 結果フォルダ確認
ls -la backtest/results/

# CSVファイル確認
cat backtest/results/test_rsi_macd_ema_results.csv
```

### **3. カスタム指標組み合わせテスト**
```bash
# 設定ファイルをコピー
cp backtest/configs/base_backtest_config.yml backtest/configs/my_test.yml

# 特徴量を編集（お好みの指標を選択）
vim backtest/configs/my_test.yml

# テスト実行
python backtest/scripts/run_backtest.py my_test
```

## 🔧 設定ファイル管理

### **設定ファイルの場所**
- **場所**: `/Users/nao/Desktop/bot/backtest/configs/`
- **命名**: `{test_name}.yml` 形式
- **継承**: production.ymlから基本設定を継承

### **パス仕様**
- **絶対パス使用**: 相対パス問題を完全回避
- **固定出力先**: `backtest/results/` に統一
- **ログ統一**: `backtest/results/{test_name}.log`

### **利用可能な97特徴量**
詳細な特徴量リストは `configs/README.md` を参照してください。

#### **主要カテゴリ**
- **価格・リターン系**: close_lag_1, returns_1, returns_2...
- **移動平均系**: ema_5, ema_10, ema_20, ema_50...
- **オシレーター系**: rsi_14, macd, stoch_k...
- **ボリューム系**: volume_ratio, vwap, obv...
- **時間・セッション系**: hour, is_asian_session...

## 📊 結果ファイル管理

### **自動生成ファイル**
- `{test_name}_results.csv` - バックテスト統計
- `{test_name}_portfolio.csv` - ポートフォリオ推移
- `{test_name}_trades.csv` - 個別取引記録
- `{test_name}_performance.png` - パフォーマンスチャート
- `{test_name}.log` - 実行ログ

### **重要メトリクス**
- **Total Return**: 総リターン（%）
- **Sharpe Ratio**: リスク調整後リターン
- **Max Drawdown**: 最大ドローダウン（%）
- **Win Rate**: 勝率（%）
- **Profit Factor**: プロフィットファクター

## 🛠️ 高度な使用方法

### **プロジェクトルートからの実行**
```bash
cd /Users/nao/Desktop/bot

# CLI経由（従来方式）
python -m crypto_bot.main backtest --config backtest/configs/test_rsi_macd_ema.yml

# ヘルパー経由（推奨）
python backtest/scripts/run_backtest.py test_rsi_macd_ema
```

### **複数テストの一括実行**
```bash
# 設定ファイル一覧確認
python backtest/scripts/run_backtest.py --list-configs

# 複数テスト実行（bash script作成例）
for config in base_backtest_config test_rsi_macd_ema; do
    echo "Testing $config..."
    python backtest/scripts/run_backtest.py $config
done
```

### **カスタム出力パス**
```bash
# 特定の出力先指定
python backtest/scripts/run_backtest.py test_rsi_macd_ema --output /path/to/custom/output.csv
```

## ⚙️ システム統合の利点

### **1. 一元管理**
- すべてのバックテスト関連ファイルが単一の場所
- 設定・結果・スクリプトの混在なし
- 見つけやすく管理しやすい構造

### **2. パス問題解決**
- 絶対パス使用で相対パス問題を完全排除
- 設定ファイル、実行スクリプト、結果すべて一貫したパス
- 実行場所に依存しない動作

### **3. 簡素化**
- 6つのbacktestモジュールから4つに簡素化
- metrics.py + analysis.py → evaluation.py に統合
- 機能重複の排除

### **4. 拡張性**
- 新しいテスト設定の追加が簡単
- 結果の比較分析が効率的
- アーカイブ機能で履歴管理

## 🔍 トラブルシューティング

### **よくあるエラー**

**1. 設定ファイルが見つからない**
```bash
# 確認: 設定ファイル存在チェック
ls -la backtest/configs/

# 解決: 正しいファイル名を使用（拡張子.ymlなし）
python backtest/scripts/run_backtest.py base_backtest_config
```

**2. 結果ファイルが見つからない**
```bash
# 確認: 結果フォルダ確認
ls -la backtest/results/

# 解決: テスト実行後に結果が生成される
```

**3. モジュール読み込みエラー**
```bash
# 解決: プロジェクトルートから実行
cd /Users/nao/Desktop/bot
python backtest/scripts/run_backtest.py test_name
```

## 📈 パフォーマンス最適化

### **大規模データでのテスト**
```yaml
# 設定ファイル調整例
data:
  limit: 1000      # データ制限
  since_hours: 168 # 1週間分

walk_forward:
  train_window: 500  # 軽量化
  test_window: 100
  step: 50
```

### **特徴量絞り込み**
```yaml
# 20-30特徴量に絞る推奨
ml:
  extra_features:
    - rsi_14
    - macd
    - ema_20
    - volume_ratio
    # ... 必要最小限の特徴量のみ
```

## 🎯 次のステップ

1. **基本テスト**: RSI + MACD + EMA から開始
2. **指標探索**: サンプルから有効な組み合わせ発見
3. **最適化**: 閾値・パラメータ調整
4. **検証**: ペーパートレードでリアルタイム検証
5. **本番反映**: production.yml への組み込み

---

**🎊 完全統合バックテストシステム - すべての関連ファイルを一元管理し、シンプルで効率的なテスト環境を提供**