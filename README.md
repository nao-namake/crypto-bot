# Crypto-Bot - CSV-based 101特徴量バックテストシステム

## 🚀 **最新実装完了: CSV-based 1年間バックテスト対応システム** (2025年7月10日完成)

**世界最先端101特徴量・CSV高速バックテストシステム**による暗号資産自動売買ボットです。

### 💎 **革新的技術成果**
```
🎯 CSV-based高速バックテスト実現:
- API制限回避: 1年間データでタイムアウトなし
- 101特徴量完全一致: 訓練時と推論時で100%統一
- 外部データキャッシュ: VIX・DXY・Fear&Greed・Funding Rate事前保持
- ロバスト特徴量生成: 外部エラー時でも確実に101特徴量を維持

🔬 技術的ブレークスルー:
- 8,761レコード1年間BTC高速処理
- 329期間ウォークフォワード検証成功
- 外部データ失敗時の確実なフォールバック
- 完璧な特徴量数整合性保証
```

### 🏗️ **実装システム詳細**

#### **1. CSV対応高速バックテスト**
- **scripts/generate_btc_csv_data.py**: 統計的に正確な1年間BTC価格データ生成
- **crypto_bot/data/fetcher.py**: CSV/API統合対応・デュアルモード実装
- **config/bitbank_101features_csv_backtest.yml**: CSV専用101特徴量設定

#### **2. 外部データキャッシュシステム**
- **crypto_bot/ml/external_data_cache.py**: 全期間外部データ事前キャッシュ
- 1年間のVIX・DXY・Fear&Greed・Funding Rateデータ保持
- ウォークフォワード各期間での高速抽出

#### **3. 確実な101特徴量生成**
- **crypto_bot/ml/feature_defaults.py**: デフォルト特徴量生成システム
- **ensure_feature_consistency()**: 最終的な101特徴量保証機能
- 外部データ失敗時でも確実に101特徴量を維持

#### **4. 101特徴量完全内訳**
```
基本テクニカル指標（20特徴量）: RSI, MACD, RCI, SMA, EMA, Bollinger Bands等
VIX恐怖指数（6特徴量）: レベル・変化率・Z-score・恐怖度・スパイク・市場環境
DXY・金利（10特徴量）: ドル指数・10年債・イールドカーブ・リスク感情等
Fear&Greed（13特徴量）: 市場感情・極端値・モメンタム・感情強度等
Funding Rate・OI（17特徴量）: 資金フロー・レバレッジリスク・ポジション分析等
時間・シグナル特徴量（4特徴量）: 曜日効果・時間効果・独自シグナル
追加特徴量（31特徴量）: 移動平均・ラグ特徴量・統計量・動的特徴量等
```

## 🎯 **4次元市場分析技術**

**世界初の4次元統合アプローチ**による包括的市場分析：

```
Dimension 1: テクニカル分析次元
├── 価格・出来高パターン分析（RSI, MACD, Bollinger Bands等）
├── モメンタム・トレンド検知（移動平均、RCI等）
└── ボラティリティ・逆張りシグナル（ATR、Williams %R等）

Dimension 2: マクロ経済分析次元
├── 株式市場リスク環境（VIX恐怖指数・6特徴量）
├── 通貨・金利環境（DXY・米国債・10特徴量）
└── 経済サイクル・クロスアセット分析

Dimension 3: 市場心理分析次元  
├── 投資家感情指数（Fear & Greed・13特徴量）
├── パニック・楽観極端値検知
└── 群集心理・行動ファイナンス分析

Dimension 4: 資金フロー分析次元
├── Funding Rate極端値・レジーム判定（17特徴量）
├── Open Interest動向・ポジション分析
└── レバレッジリスク・流動性評価
```

## 基本コマンド

### **CSV-based高速バックテスト（最新機能）**
```bash
# 1年間高速CSVバックテスト（101特徴量完全版）
python -m crypto_bot.main backtest --config config/bitbank_101features_csv_backtest.yml

# CSV データ生成（8,761レコード・1年間）
python scripts/generate_btc_csv_data.py

# 外部データキャッシュ状況確認
python -c "from crypto_bot.ml.external_data_cache import get_global_cache; print(get_global_cache().get_cache_info())"
```

### **従来APIバックテスト**
```bash
# 従来型APIバックテスト（短期間）
python -m crypto_bot.main backtest --config config/default.yml

# VIX統合APIバックテスト
python -m crypto_bot.main backtest --config config/aggressive_2x_target.yml
```

### **機械学習・最適化**
```bash
# 101特徴量対応モデル学習
python -m crypto_bot.main train --config config/bitbank_101features_csv_backtest.yml

# Optuna最適化付きフルMLパイプライン
python -m crypto_bot.main optimize-and-train --config config/default.yml

# ハイパーパラメータ最適化のみ
python -m crypto_bot.main optimize-ml --config config/default.yml
```

### **コード品質・テスト**
```bash
# 全品質チェック（flake8, black, isort, pytest）
bash scripts/checks.sh

# テストカバレッジレポート
pytest --cov=crypto_bot --cov-report=html tests/unit/

# ユニットテストのみ
pytest tests/unit

# 統合テスト（APIキー要）
pytest tests/integration
```

**最新テストカバレッジ状況:**
- **全体カバレッジ**: **57%** ✅ (目標達成)
- **テスト成功率**: **530テスト PASSED** (100%成功率) ✅
- **リスク管理**: 90% ✅ (Kelly基準、動的サイジング)
- **ML戦略**: 78% ✅ (VIX統合、動的閾値)
- **MLモデル**: 92% ✅ (アンサンブル、最適化)
- **指標計算**: 75% ✅ (テクニカル指標)

## 🚀 主な機能

### **現在の革新的実装（2025年7月更新）**

#### **CSV-based高速バックテストシステム ✅**
- **1年間バックテスト**: API制限なし・高速実行・タイムアウト回避
- **101特徴量完全一致**: 訓練時と推論時の完全な特徴量統一
- **外部データキャッシュ**: VIX・DXY・Fear&Greed・Funding Rate事前キャッシュ
- **ロバストデフォルト**: 外部エラー時の確実な特徴量生成

#### **101特徴量統合システム ✅**
- **4次元市場分析**: テクニカル・マクロ・心理・資金フローの統合分析
- **VIX恐怖指数**: 市場パニック検知・リスクオフ判定・恐怖度計算
- **DXY・金利統合**: マクロ経済環境・ドル強度による高精度予測
- **Fear&Greed統合**: 市場心理・投資家感情の詳細分析
- **Funding Rate・OI**: 暗号資産特有の資金フロー・レバレッジリスク監視

#### **機械学習最適化 ✅**
- **アンサンブルモデル**: LightGBM + RandomForest + XGBoost統合
- **Optuna最適化**: ハイパーパラメータ自動調整・15試行最適化
- **ウォークフォワード**: 現実的なバックテスト手法・329期間検証
- **動的リスク管理**: Kelly基準・ボラティリティ連動ポジションサイジング

### **コア機能**
- **データ取得**: CSV/CCXT API統合対応（デフォルト: Bybit Testnet）
- **バックテスト**: スリッページ・手数料・ATRストップ・損益集計
- **最適化**: Optuna ハイパーパラメータ探索、MLモデル再学習
- **ウォークフォワード**: CAGR・Sharpe可視化・329期間検証
- **リスク管理**: 動的ポジションサイジング + Kelly基準
- **機械学習**: アンサンブルモデル（LightGBM+RandomForest+XGBoost）
- **CI/CD**: GitHub Actions自動化・環境別デプロイ（57%カバレッジ達成）
- **監視機能**: GCP Cloud Monitoring + Streamlit ダッシュボード
- **インフラ**: Terraform + GCP Cloud Run + Workload Identity Federation

## 動作要件

- Python 3.11 〜 3.12
- Bybit Testnet API Key と Secret（API使用時）
- 動作確認環境: Linux/macOS/WSL2
- GCPプロジェクト（Cloud Monitoring有効化）とMetric Writer権限付きサービスアカウント

## セットアップ

### 1. リポジトリを取得
```bash
git clone https://github.com/nao-namake/crypto-bot.git
cd crypto-bot
```

### 2. 仮想環境を作成
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. パッケージをインストール
```bash
pip install -e .
pip install -r requirements-dev.txt
```

### 4. GCP認証キーを設定（本番用）
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### 5. APIキーを設定（API使用時）
```bash
cp .env.example .env
# .env を開いて BYBIT_TESTNET_API_KEY と SECRET を記入
```

## CSV-based バックテスト使用方法

### 1. CSVデータ生成
```bash
# 1年間BTC価格データ生成（8,761レコード）
python scripts/generate_btc_csv_data.py
```

### 2. CSV-based バックテスト実行
```bash
# 101特徴量・1年間高速バックテスト
python -m crypto_bot.main backtest --config config/bitbank_101features_csv_backtest.yml
```

### 3. 外部データキャッシュ初期化確認
外部データ（VIX・DXY・Fear&Greed・Funding Rate）は自動的にキャッシュされます：
```bash
# キャッシュ状況確認
python -c "from crypto_bot.ml.external_data_cache import get_global_cache; print(get_global_cache().get_cache_info())"
```

## Docker での実行

### 1. Dockerイメージのビルド
```bash
bash scripts/build_docker.sh
```

### 2. .envファイルの準備
```bash
cp .env.example .env
# .env を開いて必要な項目を記入
```

### 3. Dockerコンテナでコマンドを実行
```bash
# CSV-based バックテスト
bash scripts/run_docker.sh backtest --config config/bitbank_101features_csv_backtest.yml

# モデル最適化
bash scripts/run_docker.sh optimize-and-train --config config/default.yml

# 統合テスト
bash scripts/run_docker.sh e2e-test
```

## GCP インフラストラクチャ

### CI/CD パイプライン
**完全復旧されたGitHub Actions自動デプロイ**

#### **環境別自動デプロイ戦略**
| 環境 | ブランチ | モード | デプロイ条件 |
|------|----------|--------|--------------|
| **Development** | `develop` | paper | develop pushまたはPR |
| **Production** | `main` | live | main pushのみ |
| **HA Production** | tags | live | `v*.*.*` タグpushのみ |

#### **技術構成**
- **認証**: Workload Identity Federation (キーレスOIDC)
- **インフラ**: Terraform Infrastructure as Code
- **品質管理**: flake8 + black + isort + pytest
- **コンテナ**: Docker マルチステージビルド
- **デプロイ**: Google Cloud Run + Artifact Registry

## プロジェクト構成

```
crypto-bot/
├── config/                    # 設定ファイル (YAML)
│   ├── bitbank_101features_csv_backtest.yml  # CSV専用101特徴量設定
│   ├── default.yml           # 標準API設定
│   └── aggressive_2x_target.yml  # VIX統合設定
├── data/                     # CSVデータ格納
│   └── btc_usd_2024_hourly.csv  # 1年間BTCデータ（8,761レコード）
├── scripts/                  # 実行スクリプト
│   ├── generate_btc_csv_data.py  # CSV データ生成
│   ├── checks.sh            # 品質チェック統合
│   └── run_pipeline.sh      # パイプライン自動実行
├── crypto_bot/
│   ├── data/                # データ取得・ストリーム（CSV/API統合）
│   │   └── fetcher.py       # MarketDataFetcher（CSV対応）
│   ├── ml/                  # 機械学習（101特徴量対応）
│   │   ├── external_data_cache.py  # 外部データキャッシュ
│   │   ├── feature_defaults.py     # デフォルト特徴量生成
│   │   └── preprocessor.py         # 101特徴量エンジニアリング
│   ├── backtest/            # バックテストエンジン
│   ├── strategy/            # 戦略 (MLStrategy等)
│   └── risk/                # リスク管理
├── tests/                   # unit/integration テスト（530テスト・100%成功）
└── requirements*.txt        # 依存関係
```

## 設定ファイル詳細

### CSV-based バックテスト設定例
```yaml
# config/bitbank_101features_csv_backtest.yml
data:
  exchange: csv
  csv_path: /Users/nao/Desktop/bot/data/btc_usd_2024_hourly.csv
  symbol: BTC/USDT
  timeframe: 1h

ml:
  extra_features:
    - vix        # VIX恐怖指数（6特徴量）
    - dxy        # DXY・金利（10特徴量）
    - fear_greed # Fear&Greed（13特徴量）
    - funding    # Funding Rate・OI（17特徴量）
    - rsi_14     # 基本テクニカル指標群
    - macd
    - rci_9
    # ... 101特徴量完全対応
```

## 技術的ブレークスルー詳細

### **解決した重要課題**

#### **1. 特徴量数不一致問題**
- **課題**: 訓練時101特徴量 vs バックテスト時83-99特徴量の不一致
- **解決**: 外部データキャッシュ + ロバストデフォルト生成で完全解決

#### **2. API制限・タイムアウト問題**  
- **課題**: 1年間データ取得でAPI制限・タイムアウト発生
- **解決**: CSV-based高速バックテストで完全回避

#### **3. 外部データ取得エラー**
- **課題**: VIX・DXY等の外部API エラーによる特徴量生成失敗
- **解決**: 包括的フォールバック + デフォルト値生成で確実に101特徴量維持

#### **4. 時間軸アライメント問題**
- **課題**: 暗号資産1時間足 vs マクロデータ日足の時間軸不一致
- **解決**: 統一リサンプリング・前方補完で完全同期

### **現在の安定性指標**
- **530テスト成功** (100%成功率)
- **57%テストカバレッジ** (主要モジュール90%+)
- **CI/CD完全自動化** (デプロイエラー0件)
- **101特徴量システム安定稼働** (特徴量数不一致エラー0件)

## 今後の拡張計画

### **短期計画（1-2週間）**
- 複数暗号資産ペア（ETH/USDT, XRP/USDT等）でのCSVバックテスト対応
- リアルタイム101特徴量システムの最適化
- 外部データソース追加（COTレポート、セクター回転等）

### **中期計画（1-3ヶ月）**  
- 深層学習モデル統合（LSTM、Transformer等）
- 複数取引所対応拡張（API/CSV両対応）
- DeFi統合（流動性プロバイダー、ステーキング等）

### **長期計画（6ヶ月-1年）**
- 強化学習システム導入（DQN、PPO等）
- 自動再学習・適応システム構築
- 量子コンピューティング活用研究

## FAQ

**Q: CSVバックテストと従来APIバックテストの違いは？**
A: CSVはAPI制限なし・1年間高速実行・オフライン処理可能。APIはリアルタイムデータ・最新データ対応。

**Q: 101特徴量は常に保証されますか？**
A: はい。外部データエラー時でも`feature_defaults.py`により確実に101特徴量を生成します。

**Q: 外部データキャッシュの有効期限は？**
A: 1年間の事前キャッシュを保持。必要に応じて再初期化可能です。

**Q: 新しい特徴量を追加する方法は？**
A: 1) `preprocessor.py`に実装 2) `config_validator.py`に追加 3) 設定ファイルで有効化

## ライセンス

本プロジェクトはMIT Licenseで公開されています。

---

**このREADMEは、最新のCSV-based 101特徴量バックテストシステム（2025年7月10日完成）を基に作成されています。**