# src/ - AI自動取引システム実装

**Phase 49完了**のAI自動取引システム実装。55特徴量→5戦略→ML予測→リスク管理→取引実行の完全自動化レイヤードアーキテクチャ。バックテスト完全改修・確定申告対応・週間レポート実装により、企業級AI自動取引システムを実現。

## 📂 システム構成

```
src/
├── __init__.py                     # パッケージ初期化
├── core/                          # コア基盤システム
│   ├── orchestration/                 # システム統合制御・TradingOrchestrator
│   ├── config/                        # 設定管理・特徴量管理
│   ├── execution/                     # バックテスト実行制御
│   ├── reporting/                     # レポーティング・Discord統合
│   ├── services/                      # システムサービス・正常終了管理
│   └── [基盤ファイル群]                # config.py・logger.py・exceptions.py等
├── data/                          # データ層
│   ├── bitbank_client.py              # Bitbank API統合・残高・取引実行
│   ├── data_pipeline.py               # データ取得・処理パイプライン
│   └── data_cache.py                  # データキャッシュシステム
├── features/                      # 特徴量システム
│   └── feature_generator.py          # 15特徴量生成・統合管理
├── strategies/                    # 戦略システム → [詳細](strategies/README.md)
│   ├── base/                          # 戦略基盤・統合管理
│   ├── implementations/               # 5戦略実装（ATR・MochiPoy・MTF・Donchian・ADX）
│   └── utils/                         # 戦略共通処理
├── ml/                           # 機械学習システム
│   ├── models.py                      # 個別MLモデル実装
│   └── ensemble.py                    # ProductionEnsemble・3モデル統合
├── trading/                      # 取引実行・リスク管理層 → [詳細](trading/README.md)
│   ├── risk_manager.py                # 統合リスク管理・Kelly基準・TP/SL
│   ├── position_manager.py            # ポジション管理・仮想ポジション
│   ├── execution_service.py           # ExecutionService・取引実行統合
│   └── [リスク管理群]                  # risk_monitor.py・thresholds.py等
├── backtest/                     # バックテストシステム
│   ├── data/                          # CSV読み込み・キャッシュ
│   ├── scripts/                       # データ収集スクリプト
│   ├── logs/                          # レポート出力先
│   └── reporter.py                    # レポート生成・JSON出力
└── monitoring/                   # 週間レポート専用（Phase 48）
    └── discord_formatter.py           # Discord週間レポート送信・損益グラフ生成
```

## 🔧 システムアーキテクチャ

### **レイヤード設計**

```
📊 monitoring/     ← 監視・通知層
    ↕️
🎯 trading/        ← 取引実行・リスク管理層
    ↕️
📈 strategies/     ← 戦略判定・シグナル生成層
    ↕️
🤖 ml/            ← 機械学習・予測層
    ↕️
⚙️  features/      ← 特徴量エンジニアリング層
    ↕️
📡 data/           ← データ取得・処理層
    ↕️
🏗️  core/          ← 基盤・統合制御層
```

### **データフロー**

```
1. 【data/】Bitbank API → 市場データ取得（4h/15m足）
        ↓
2. 【features/】15特徴量生成 → 技術指標・統計指標
        ↓
3. 【ml/】ProductionEnsemble → 3モデル予測統合
        ↓
4. 【strategies/】5戦略実行 → シグナル統合・重み付け
        ↓
5. 【trading/】リスク評価 → 3段階判定（APPROVED/CONDITIONAL/DENIED）
        ↓
6. 【trading/】注文実行 → ペーパートレード・実取引
        ↓
7. 【monitoring/】Discord通知 → 実行結果・異常通知
```

## 🔧 主要コンポーネント

### **1. core/ - コア基盤システム**
**目的**: システム全体の基盤・統合制御・設定管理

**主要モジュール**:
- `orchestrator.py`: システム統合制御・取引サイクル管理
- `feature_manager.py`: 15特徴量統一定義・システム連携
- `logger.py`: JST対応ログ・構造化出力・Discord統合
- `config.py`: 設定読み込み・環境変数管理・階層化設定

### **2. data/ - データ層**
**目的**: 市場データ取得・処理・キャッシュ管理

**主要モジュール**:
- `bitbank_client.py`: Bitbank API統合・ccxt利用・レート制限対応
- `data_pipeline.py`: データ取得パイプライン・多時間軸・品質管理
- `data_cache.py`: LRUキャッシュ・ディスクキャッシュ・3ヶ月保存

### **3. features/ - 特徴量システム**
**目的**: 技術指標・統計指標の生成・統合管理

**主要モジュール**:
- `feature_generator.py`: 50基本特徴量生成・feature_manager連携・全システム統合

**生成特徴量（55特徴量 = 50基本 + 5戦略信号）**:
- **基本特徴量（50個）**: close・volume・RSI・MACD・ATR・ボリンジャーバンド・EMA・出来高比率・Donchianチャネル・ADX・DI等
- **戦略信号特徴量（5個・Phase 41.8）**: ATRBased・MochiPoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength
- **Phase 41.8 Strategy-Aware ML**: 訓練時と推論時の完全一貫性確保・look-ahead bias防止

### **4. strategies/ - 戦略システム** → **[詳細ドキュメント](strategies/README.md)**
**目的**: 5戦略統合・シグナル生成・重み付け統合・競合解決

**戦略実装**:
- **ATRBasedStrategy**: ボラティリティ分析・ボリンジャーバンド・RSI統合
- **MochiPoyAlertStrategy**: 複合指標・EMA・MACD・RCI統合
- **MultiTimeframeStrategy**: 4時間足トレンド・15分足タイミング統合
- **DonchianChannelStrategy**: ブレイクアウト戦略・チャネル上下限突破
- **ADXTrendStrengthStrategy**: トレンド強度分析・方向性指標統合

### **5. ml/ - 機械学習システム**
**目的**: 機械学習予測・アンサンブルモデル・モデル管理

**主要モジュール**:
- `models.py`: 個別MLモデル実装（LightGBM・XGBoost・RandomForest）
- `ensemble.py`: ProductionEnsemble・3モデル統合（LightGBM 40%・XGBoost 40%・RandomForest 20%）

**Phase 41.8 Strategy-Aware ML**:
- **55特徴量学習**: 50基本特徴量 + 5戦略信号特徴量
- **訓練/推論一貫性**: 実戦略シグナルを訓練時に生成・look-ahead bias完全防止
- **F1スコア**: XGBoost 0.593・RandomForest 0.614・LightGBM 0.489達成

### **6. trading/ - 取引実行・リスク管理層** → **[詳細ドキュメント](trading/README.md)**
**目的**: リスク管理・異常検知・ドローダウン管理・注文実行

**統合機能**:
- **統合リスク管理**: ML信頼度・ドローダウン・異常検知の総合判定
- **Kelly基準ポジションサイジング**: 数学的最適ポジションサイズ計算
- **3段階判定システム**: APPROVED（<0.6）・CONDITIONAL（0.6-0.8）・DENIED（≥0.8）
- **注文実行**: ペーパートレード・実取引・レイテンシー監視

### **7. backtest/ - バックテストシステム**
**目的**: 本番同一ロジック・バックテスト・CSV過去データ利用

**主要コンポーネント**:
- `data/csv_data_loader.py`: CSV読み込み・キャッシュ・過去データ管理
- `scripts/collect_historical_csv.py`: 過去データ収集・Bitbank API→CSV変換
- `reporter.py`: JSON形式レポート生成・統計分析
- `logs/`: バックテスト結果出力先（空・実行時自動作成）

**Phase 49完了 - バックテスト完全改修**:
- **戦略シグナル事前計算**: 全時点で実戦略を実行・look-ahead bias完全防止
- **TP/SL決済ロジック実装**: 各時点の高値・安値でTP/SL判定・リアル取引完全再現
- **TradeTracker統合**: エントリー/エグジットペアリング・損益計算・パフォーマンス指標算出
- **matplotlib可視化システム**: 4種類グラフ（エクイティカーブ・損益分布・ドローダウン・価格チャート）
- **バックテスト信頼性100%達成**: ライブモード完全一致・SELL判定正常化

## 🚀 使用方法

### **基本システム実行**
```python
# メインシステム実行（main.py経由）
python main.py --mode paper    # ペーパートレード
python main.py --mode live     # ライブトレード

# システム統合実行（直接実行）
from src.core.orchestration.orchestrator import Orchestrator
from src.core.config import load_config

config = load_config("config/core/unified.yaml")
orchestrator = Orchestrator(config)
await orchestrator.run_trading_cycle()
```

### **バックテスト実行**
```bash
# メイン実行（推奨）
python main.py --mode backtest

# CSVデータ更新（月1回推奨）
python src/backtest/scripts/collect_historical_csv.py --days 180
```

```python
# バックテスト結果確認
from src.backtest.data.csv_data_loader import get_csv_loader
from src.backtest.reporter import BacktestReporter

# CSV読み込み確認
loader = get_csv_loader()
data = loader.load_historical_data("BTC/JPY", "4h")

# レポート確認
reporter = BacktestReporter()
# 結果はsrc/backtest/logs/backtest_*.jsonに出力
```

### **個別コンポーネント使用**

**特徴量生成**:
```python
from src.features.feature_generator import FeatureGenerator

generator = FeatureGenerator()
features_df = await generator.generate_features_sync(market_data_df)
```

**戦略実行**:
```python
from src.strategies.base.strategy_manager import StrategyManager

manager = StrategyManager()
# 戦略登録・実行（詳細はstrategies/README.md参照）
```

**取引実行**:
```python
from src.trading import IntegratedRiskManager, create_order_executor

# リスク管理・取引実行（詳細はtrading/README.md参照）
```

## 🧪 テスト・品質保証

### **テスト実行**
```bash
# 全体品質チェック（推奨）
bash scripts/testing/checks.sh

# 個別システムテスト
python -m pytest tests/unit/core/ -v
python -m pytest tests/unit/strategies/ -v
python -m pytest tests/unit/trading/ -v
python -m pytest tests/unit/ml/ -v

# カバレッジ確認
python -m pytest tests/ --cov=src --cov-report=html
```

### **品質指標（Phase 49更新）**
- **テスト成功率**: 1,065テスト100%成功
- **コードカバレッジ**: 66.72%達成
- **実行時間**: システム全体テスト80秒以内

### **継続的品質保証**
- **GitHub Actions**: CI/CD自動品質チェック・失敗時マージ阻止
- **pre-commit hooks**: コード品質・フォーマット自動チェック
- **品質ゲート**: flake8・black・isort・pytest自動実行

## ⚙️ 設定システム

### **設定ファイル階層**
```
config/
├── core/
│   ├── unified.yaml              # 統合設定・本番運用
│   └── feature_order.json       # 15特徴量定義・システム連携KEY
├── backtest/
│   └── backtest.yaml             # バックテスト専用設定
└── infrastructure/
    ├── gcp_config.yaml           # GCP Cloud Run設定
    └── cloudbuild.yaml           # CI/CD設定
```

### **環境変数**
```bash
# API認証
BITBANK_API_KEY=your_api_key
BITBANK_API_SECRET=your_api_secret

# Discord通知
DISCORD_WEBHOOK_URL=your_webhook_url

# システム制御
TRADING_MODE=paper  # paper/live
LOG_LEVEL=INFO      # DEBUG/INFO/WARNING/ERROR
```

## 📈 パフォーマンス指標

### **実行パフォーマンス**
- **取引サイクル**: 15特徴量生成→5戦略→ML予測→リスク評価→実行（2秒以内）
- **データ取得**: Bitbank API・35秒間隔・レート制限遵守
- **メモリ使用量**: 通常運用500MB・バックテスト時1GB以下

### **品質指標**
- **システム統合**: レイヤード設計・疎結合・エラー分離
- **フォールバック**: MLモデル未使用時ダミーモデル自動切替
- **状態管理**: 取引状況・ドローダウン・統計の永続化

## ⚠️ 重要事項

### **システム要件（Phase 49完了）**
- **Python**: 3.13推奨（最新MLライブラリ対応）・async/await完全対応・型ヒント拡充
- **メモリ**: 本番運用1GB・バックテスト2GB推奨
- **ディスク**: キャッシュ・ログ・モデル用に5GB以上
- **可視化ライブラリ**: matplotlib・Pillow（Phase 48-49週間レポート・バックテストグラフ用）
- **コード品質**: Phase 49完了・バックテスト完全改修・確定申告対応・週間レポート実装

### **運用制約**
- **API制限**: Bitbank 35秒間隔・接続数制限・レート制限対応
- **リスク管理**: Kelly基準・20%ドローダウン制限・連続5損失停止
- **監視必須**: Discord 3階層通知・Cloud Run監視・ヘルスチェック

### **開発制約（Phase 49完了）**
- **テスト必須**: scripts/testing/checks.sh実行・カバレッジ66.72%維持
- **品質ゲート**: CI/CD自動チェック・1,065テスト100%成功必須
- **コード品質**: flake8・black・isort通過・SSL証明書セキュリティ対応
- **設定分離**: 本番・バックテスト・開発環境完全分離
- **Phase 49完了**: バックテスト完全改修・確定申告対応・週間レポート実装

### **依存関係**
- **外部ライブラリ**: pandas・numpy・ccxt・lightgbm・xgboost・scikit-learn
- **API依存**: Bitbank API・Discord Webhook
- **インフラ**: GCP Cloud Run・GitHub Actions・Docker

---

## 🔗 詳細ドキュメント

- **[戦略システム詳細](strategies/README.md)**: 5戦略実装・統合管理・使用方法
- **[取引実行システム詳細](trading/README.md)**: リスク管理・異常検知・注文実行
- **[プロジェクト全体概要](../README.md)**: システム全体・運用手順・開発履歴

---

**AI自動取引システム（Phase 49完了）**: 55特徴量→5戦略→ML予測→リスク管理→取引実行の完全自動化。

**Phase 49成果**:
- **バックテスト完全改修**: 戦略シグナル事前計算・TP/SL決済ロジック・TradeTracker統合・matplotlib可視化・信頼性100%達成
- **確定申告対応**: SQLite取引記録・移動平均法損益計算・CSV出力・作業時間95%削減（10時間→30分）
- **週間レポート**: Discord週間レポート・損益グラフ・通知99%削減（300-1,500回/月→4回/月）・コスト35%削減
- **統合TP/SL**: 注文数91.7%削減（24注文→2注文）・トレーリングストップ・状態永続化
- **Strategy-Aware ML**: 55特徴量学習・ML統合率100%達成・訓練/推論一貫性確保

1,065テスト100%成功・66.72%カバレッジ達成・企業級AI自動取引システム完成。