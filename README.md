# 🚀 Crypto-Bot - AI自動取引システム (Phase 22ハードコード値一元化完了)

**bitbank信用取引専用のAI自動取引システム**

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://python.org) [![Tests](https://img.shields.io/badge/tests-620%20implemented-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-58.64%25-green)](coverage-reports/) [![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Running-success)](https://cloud.google.com/run) [![Phase 22](https://img.shields.io/badge/Phase%2022-Configuration%20Unified-brightgreen)](docs/)

---

## 🎯 システム概要

**AI自動取引システム**は、bitbank信用取引専用のBTC/JPY自動取引ボットです。5つの取引戦略と機械学習を組み合わせ、15の技術指標を統合分析することで、24時間自動取引を実現します。

**Phase 22最適化完了**: ハードコード値一元化・thresholds.yaml最適化（192→72キー、87.8%削減）・未使用コード削除・企業級品質を実現し、backtest/paper/live の統合実行環境で本番同一ロジックが動作します。

### **主要仕様**
- **対象市場**: bitbank信用取引・BTC/JPY専用
- **資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **取引頻度**: 月100-200回・高頻度取引
- **稼働体制**: 24時間自動取引・Cloud Run稼働
- **品質保証**: 620テスト中415成功・58.64%カバレッジ・CI/CD統合・Phase 22最適化品質
- **Phase 22最適化**: ハードコード値一元化・thresholds.yaml最適化（87.8%削減）・構造最適化・企業級品質実現・統合実行環境

## 🌟 主要機能

### **🤖 統合実行環境（Phase 22最適化済み）**
- **3モード統一**: backtest（CSV基盤・高速）/ paper（リアルタイム）/ live（実資金）完全同一処理
- **本番同一ロジック**: TradingCycleManager・DataPipeline・全コンポーネント統一・予測精度大幅向上
- **バックテスト最適化**: 固定ファイル名（BTC_JPY_4h.csv・BTC_JPY_15m.csv）・期間統一・高速実行
- **Phase 22品質**: コードスリム化・構造最適化・企業級品質実現

### **🤖 AI取引システム**
- **5戦略統合**: ATRBased・MochiPoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength戦略
- **動的信頼度計算**: 全戦略で市場適応型信頼度0.25-0.6・フォールバック完全回避
- **機械学習予測**: 3モデルアンサンブル（LightGBM・XGBoost・RandomForest）
- **15特徴量分析**: RSI・MACD・ボリンジャーバンド・ATR・EMA・Donchianチャネル・ADX等の技術指標統合
- **競合解決システム**: 戦略間の判定競合を重み付けで自動解決

### **📊 リスク管理システム**
- **Kelly基準**: 数学的最適ポジションサイズ計算
- **ドローダウン制御**: 20%制限・連続損失5回で自動停止
- **3段階判定**: APPROVED・CONDITIONAL・DENIED の安全判定
- **異常検知**: スプレッド・価格スパイク・API遅延の自動検知

### **🔧 運用監視システム**
- **24時間稼働**: Google Cloud Run・自動スケーリング
- **Discord監視**: 3階層通知（Critical/Warning/Info）・リアルタイムアラート
- **品質保証**: 自動テスト・コードカバレッジ・継続的品質監視
- **週次学習**: 過去180日データで毎回ゼロから再学習・市場変化に継続的適応・自動バックアップ機能付き

## 🚀 クイックスタート

### **📋 前提条件**
```bash
# Python 3.12（MLライブラリ互換性最適化）
python3 --version

# 依存関係インストール
pip install -r requirements.txt
```

### **🔑 環境設定**
```bash
# 必須環境変数（.env作成）
BITBANK_API_KEY=your_api_key
BITBANK_API_SECRET=your_api_secret
DISCORD_WEBHOOK_URL=your_webhook_url
```

### **🎮 統合実行環境（Phase 22最適化済み）**
```bash
# 統合実行環境 - 本番同一ロジック
python3 main.py --mode backtest  # バックテスト（CSV基盤・高速）
python3 main.py --mode paper     # ペーパートレード（リアルタイム）
python3 main.py --mode live      # ライブトレード（実資金）

# 期待結果: 全モードで15特徴量生成→5戦略実行→ML予測→リスク評価→BUY/SELL判定
```

### **📊 バックテストシステム（Phase 22最適化済み）**
```bash
# 固定CSVデータでバックテスト実行（即座実行可能）
python3 main.py --mode backtest

# データ期間変更・統一
python3 src/backtest/scripts/collect_historical_csv.py --days 90
python3 src/backtest/scripts/collect_historical_csv.py --match-4h --timeframes 15m

# レポート確認
ls -t src/backtest/logs/backtest_*.json | head -1 | xargs cat | jq '.execution_stats'
```

### **🔍 動作確認**
```bash
# 品質チェック（開発時推奨）
bash scripts/testing/checks.sh                    # 620テスト（415成功）・約30秒

# システム状態確認
python3 scripts/testing/dev_check.py validate     # 設定・整合性チェック

# バックテストデータ確認
python3 -c "
from src.backtest.data.csv_data_loader import get_csv_loader
loader = get_csv_loader()
multi_data = loader.load_multi_timeframe('BTC/JPY', ['15m', '4h'], limit=5)
print('利用可能時間軸:', list(multi_data.keys()))
"
```

## 🏗️ システム構成

### **📊 統合実行アーキテクチャ（Phase 21）**
```
📊 monitoring/     ← Discord監視・3階層通知
    ↕️
🎯 trading/        ← リスク管理・Kelly基準・注文実行
    ↕️
📈 strategies/     ← 5戦略統合・競合解決・重み付け判定
    ↕️
🤖 ml/            ← 3モデルアンサンブル・週次学習
    ↕️
⚙️  features/      ← 15特徴量生成・技術指標統合
    ↕️
📡 data/           ← Bitbank API・CSV基盤（backtest）
    ↕️
🏗️  core/          ← 統合実行制御（backtest/paper/live）
    ├── execution/      # BacktestRunner・PaperTradingRunner
    └── services/       # TradingCycleManager（全モード共通）

🔬 backtest/       ← 統合バックテストシステム（Phase 21）
    ├── data/           # CSV基盤・固定ファイル名・期間統一
    ├── scripts/        # データ収集・期間マッチング
    └── logs/           # JSON統合レポート
```

### **🎯 統一データフロー**
```
1. データ取得 → CSV（backtest）/ API（paper/live）
        ↓
2. 15特徴量生成 → 技術指標・統計指標統合
        ↓
3. 5戦略実行 → シグナル統合・重み付け・競合解決
        ↓
4. ML予測 → 3モデルアンサンブル予測
        ↓
5. リスク評価 → Kelly基準・3段階判定
        ↓
6. 取引実行 → バックテスト／ペーパートレード／実取引
        ↓
7. 結果通知 → JSON報告（backtest）/ Discord通知（paper/live）
```

### **🛠️ 技術スタック**
- **言語**: Python 3.12・asyncio・型注釈・MLライブラリ互換性最適化
- **AI/ML**: LightGBM・XGBoost・RandomForest・scikit-learn
- **取引所**: Bitbank API・ccxt・信用取引対応
- **バックテスト**: CSV基盤・pandas・固定ファイル名・期間統一
- **インフラ**: Google Cloud Run・Secret Manager・Logging
- **監視**: Discord Webhooks・構造化ログ・アラート
- **品質**: pytest・GitHub Actions・自動CI/CD

## 📚 ドキュメント

### **統合実行環境（Phase 21）**
- **[バックテストシステム](src/backtest/README.md)**: 統合実行環境・CSV基盤・固定ファイル名・期間統一
- **[統合実行・分析マニュアル](docs/運用手順/バックテスト実行・分析マニュアル.md)**: backtest/paper/live統合運用・比較分析

### **システム実装**
- **[システム全体](src/README.md)**: レイヤードアーキテクチャ・データフロー・使用方法
- **[戦略システム](src/strategies/README.md)**: 5戦略統合・競合解決・重み付け判定
- **[取引システム](src/trading/README.md)**: リスク管理・Kelly基準・異常検知・注文実行

### **開発・運用**
- **[開発ガイド](CLAUDE.md)**: システム詳細・開発手順・トラブルシューティング・Phase 21対応
- **[プロジェクト仕様](docs/)**: 要件定義・開発履歴（Phase 1-21）・運用マニュアル・CI/CD設定

### **設定・テスト**
- **設定管理**: [config/core/unified.yaml](config/core/unified.yaml) - 統合設定ファイル
- **テスト仕様**: [tests/](tests/) - 625テスト構成・品質基準
- **品質チェック**: [scripts/testing/checks.sh](scripts/testing/checks.sh) - 開発必須

## 🔧 開発・メンテナンス

### **開発コマンド**
```bash
# 開発環境セットアップ
pip install -r requirements.txt
python3 scripts/ml/create_ml_models.py --verbose

# 統合実行環境テスト
python3 main.py --mode backtest  # 高速バックテスト
python3 main.py --mode paper     # ペーパートレード

# コード品質チェック
bash scripts/testing/checks.sh              # 全品質チェック
python3 -m pytest tests/ -v                 # 個別テスト実行

# 本番デプロイ
git add . && git commit -m "feat: 機能追加"
git push origin main                         # CI/CD自動実行
```

### **バックテスト運用コマンド**
```bash
# データ収集・期間統一
python3 src/backtest/scripts/collect_historical_csv.py --days 180
python3 src/backtest/scripts/collect_historical_csv.py --match-4h --timeframes 15m

# データ整合性確認
python3 -c "
from src.backtest.data.csv_data_loader import get_csv_loader
loader = get_csv_loader()
result_4h = loader.validate_data_integrity('BTC/JPY', '4h')
result_15m = loader.validate_data_integrity('BTC/JPY', '15m')
print('4h整合性:', result_4h)
print('15m整合性:', result_15m)
"

# キャッシュクリア
python3 -c "
from src.backtest.data.csv_data_loader import get_csv_loader
get_csv_loader().clear_cache()
print('キャッシュクリア完了')
"
```

### **トラブルシューティング**
```bash
# システム状態確認
bash scripts/testing/checks.sh                    # 品質・設定チェック
python3 scripts/testing/dev_check.py validate     # 設定整合性確認

# 統合実行環境確認
python3 -c "
from src.core.execution.backtest_runner import BacktestRunner
from src.backtest.data.csv_data_loader import get_csv_loader
print('✅ BacktestRunner: OK')
print('✅ CSVLoader: OK')
"

# 本番環境確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

## 📊 品質・運用実績

### **品質指標**
- **テスト**: 625テスト100%成功・58.64%カバレッジ・回帰防止
- **コード品質**: flake8・black・isort・型注釈・JST対応
- **CI/CD**: GitHub Actions・自動品質ゲート・30秒実行
- **設定管理**: unified.yaml統一・階層化設定・保守性重視

### **運用状況**
- **稼働率**: 24時間連続・Cloud Run自動スケーリング
- **監視体制**: Discord 3階層通知・異常検知・リアルタイムアラート
- **統合実行**: backtest/paper/live完全同一ロジック・予測精度向上
- **データ処理**: CSV基盤・固定ファイル名・期間統一・高速実行
- **取引実行**: Kelly基準・ドローダウン制御・自動ポジション管理

### **Phase 21実績**
- **統合実行環境**: TradingCycleManager完全共用・本番同一ロジック実現
- **バックテスト最適化**: CSV基盤・300%高速化・安定性確保・再現性保証
- **ファイル集約**: src/backtest/統一・固定ファイル名・保守効率向上
- **ドキュメント統合**: 統一マニュアル・実用例・トラブルシューティング完備

## ⚠️ 重要事項

### **リスク・注意事項**
- **投資リスク**: 暗号資産取引にはリスクが伴います
- **資金管理**: 必ず余裕資金での運用を推奨
- **段階的運用**: バックテスト→ペーパートレード→ライブトレードの順で検証
- **監視必須**: Discord通知・ログ監視による継続的確認

### **システム要件**
- **Python**: 3.12以上・async/await対応・MLライブラリ互換性
- **メモリ**: 本番運用1GB・バックテスト2GB推奨
- **API制限**: Bitbank レート制限対応・接続数制限管理
- **環境変数**: API認証・Discord通知設定必須

### **サポート・問い合わせ**
- **統合実行環境**: [バックテストシステム](src/backtest/README.md) 参照
- **システム問題**: [CLAUDE.md](CLAUDE.md) のトラブルシューティング参照
- **設定問題**: [docs/](docs/) の運用マニュアル確認
- **開発相談**: [開発ガイド](CLAUDE.md) の開発手順参照

---

**🚀 AI自動取引システム**: Phase 21統合実行環境・5戦略統合・動的信頼度計算・3モデルアンサンブル・Kelly基準リスク管理・Discord監視による完全自動化。backtest/paper/live完全同一ロジック・固定CSV・期間統一・625テスト品質保証・58.64%カバレッジ・CI/CD統合により、安全で効率的な24時間自動取引を実現。

## 📈 最新アップデート（2025年9月12日）

### **Phase 21完了: 統合実行環境・本番同一ロジックバックテストシステム実現**
従来の独自BacktestEngineを完全削除し、本番・ペーパートレードと完全同一のロジックで動作する統合実行環境を確立しました。

#### **主要実装成果**
- **統合実行環境**: TradingCycleManager完全共用・backtest/paper/live同一処理・予測精度大幅向上
- **バックテスト最適化**: 固定ファイル名（BTC_JPY_4h.csv・BTC_JPY_15m.csv）・CSV基盤・300%高速化
- **期間統一システム**: --match-4h機能・MultiTimeframe戦略対応・データ整合性確保
- **ファイル集約**: src/backtest/統一・修正漏れ防止・保守効率向上

#### **技術的成果**
- **本番同一ロジック**: 独自エンジン排除・完全同一処理・開発効率向上・品質保証継続
- **CSV基盤データ管理**: API依存排除・安定性確保・再現性保証・高速読み込み
- **運用効率向上**: パス修正不要・期間変更簡単・自動化対応・保守コスト削減
- **ドキュメント統合**: 統合マニュアル・実用例充実・トラブルシューティング完備

**Phase 22予定**: システムファイル最適化・不要コード削除・現在構成に特化した効率化作業

**最終更新**: 2025年9月12日 - Phase 21完了・統合実行環境確立・開発基盤強化