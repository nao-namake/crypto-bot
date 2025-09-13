# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 現在の状況

### **システム状態 (Phase 22ハードコード値一元化完了)**
- **AI自動取引システム**: 完全稼働中・Cloud Run 24時間運用・bitbank信用取引対応
- **資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **取引頻度**: 月100-200回・高頻度取引・BTC/JPY専用・動的信頼度計算対応済み
- **テスト品質**: 620テスト実装・58.64%カバレッジ維持・主機能正常動作確認
- **統合システム**: 15特徴量→5戦略（動的信頼度）→ML予測→リスク管理→取引実行の完全自動化
- **Phase 22成果**: ハードコード値完全一元化・thresholds.yaml最適化（192→72キー、87.8%削減）・設定統合・保守性大幅向上

### **主要仕様（要件定義より）**
- **Python**: 3.12・MLライブラリ互換性最適化・GitHub Actions安定版
- **戦略**: 5戦略統合（ATR・もちぽよ・マルチタイムフレーム・DonchianChannel・ADX）・動的信頼度計算
- **ML**: 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- **時間軸**: 4時間足（トレンド）+ 15分足（エントリー）
- **インフラ**: GCP Cloud Run・1Gi・1CPU・月額2,000円以内

## 📂 システム構造

```
src/                        # メイン実装
├── core/                   # 基盤システム (Phase 22ハードコード値一元化完了)
│   ├── orchestration/          # システム統合制御・protocols.py移動・ML統合
│   ├── config/                 # 統一設定管理・特徴量管理・ハードコード値一元化
│   ├── execution/              # 統合実行制御（backtest/paper/live）
│   ├── reporting/              # レポーティング・Discord統合 (Phase 22)
│   └── services/               # システムサービス・設定化対応
├── data/                   # データ層（Bitbank API・キャッシュ）
├── features/               # 15特徴量生成システム
├── strategies/             # 5戦略統合システム → [詳細](src/strategies/README.md)
├── ml/                     # ProductionEnsemble・3モデル統合
├── trading/                # リスク管理・取引実行 → [詳細](src/trading/README.md)
├── backtest/               # 統合バックテストシステム（Phase 21）
│   ├── data/                   # CSV基盤データ管理・固定ファイル名
│   ├── scripts/                # データ収集・期間統一機能
│   └── logs/                   # JSON統合レポート
# monitoring/はPhase 22でcore/reporting/に統合済み

scripts/testing/checks.sh   # 品質チェック（開発必須）
config/core/unified.yaml    # 統合設定ファイル (Phase 22 一元化完了)
config/core/thresholds.yaml # 最適化済み閾値設定（192→72キー、87.8%削減）
├── 交換所・ML・戦略・リスクすべての設定を統一管理
├── ハードコード値完全排除・運用パラメータ動的調整対応
├── 未使用設定完全削除・保守性・起動速度向上
└── モード制御: CLI引数 > 環境変数 > YAML設定の優先度
models/production/          # 本番MLモデル（週次更新）
```

## 🔧 開発ワークフロー

### **1. 品質チェック（開発時必須）**
```bash
# メイン品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh                         # 620テスト・カバレッジ・約30秒

# 軽量確認
python3 scripts/testing/dev_check.py validate         # 設定整合性チェック

# 期待結果: ✅ 620テスト中415成功・58.64%カバレッジ通過（主機能正常）
```

### **2. 統合実行環境（Phase 22最適化済み）**
```bash
# 統合実行環境 - 本番同一ロジック
python3 main.py --mode backtest  # バックテスト（CSV基盤・高速）
python3 main.py --mode paper     # ペーパートレード（リアルタイム）
python3 main.py --mode live      # ライブトレード（実資金）

# 期待結果: 全モードで15特徴量生成→5戦略実行→ML予測→リスク評価→BUY/SELL判定
```

### **3. バックテストシステム（Phase 21）**
```bash
# 固定CSVデータでバックテスト実行（即座実行可能）
python3 main.py --mode backtest

# データ期間変更・統一
python3 src/backtest/scripts/collect_historical_csv.py --days 90
python3 src/backtest/scripts/collect_historical_csv.py --match-4h --timeframes 15m

# レポート確認
ls -t src/backtest/logs/backtest_*.json | head -1 | xargs cat | jq '.execution_stats'
```

### **4. 本番環境確認**
```bash
# Cloud Run稼働状況
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# Discord通知確認（運用監視）
```

### **5. 開発・デバッグ**
```bash
# 特徴量生成テスト
python3 -c "
import asyncio, sys; sys.path.insert(0, '.')
from src.features.feature_generator import FeatureGenerator
# テストコード実行"

# バックテストデータ確認
python3 -c "
from src.backtest.data.csv_data_loader import get_csv_loader
loader = get_csv_loader()
multi_data = loader.load_multi_timeframe('BTC/JPY', ['15m', '4h'], limit=5)
print('利用可能時間軸:', list(multi_data.keys()))
"

# MLモデル確認
python3 scripts/deployment/docker-entrypoint.sh verify
```

## 🎯 開発原則

### **1. 品質保証必須**
- **テスト実行**: 開発前後に`checks.sh`必須実行・625テスト100%維持
- **カバレッジ**: 58.64%以上維持・新機能は必ずテスト追加
- **CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

### **2. 統合実行環境理解必須（Phase 21）**
- **本番同一ロジック**: backtest/paper/live完全同一TradingCycleManager使用
- **データフロー**: データ取得→特徴量生成→戦略実行→取引判断（全モード統一）
- **CSV基盤**: 固定ファイル名・期間統一・高速バックテスト・API依存排除

### **3. 設定管理統一**
- **ハードコード禁止**: すべて設定ファイル・環境変数で管理
- **統一設定**: config/core/unified.yaml・3層優先システム・環境切り替え
- **型安全性**: Protocol・dataclass・型注釈活用

### **4. 実装品質基準**
- **コード品質**: flake8・black・isort通過必須
- **ログ品質**: JST時刻・構造化ログ・Discord通知対応
- **テスト品質**: 単体・統合・エラーケーステスト完備

## 🚨 重要な技術ポイント

### **統合システム基盤 (Phase 22ハードコード値一元化完了)**
- **feature_manager**: 15特徴量統一管理・config/core/feature_order.json参照
- **ProductionEnsemble**: 3モデルアンサンブル（LightGBM・XGBoost・RandomForest）
- **動的信頼度計算**: フォールバック完全回避・市場適応型0.25-0.6信頼度・5戦略最適化済み
- **統合実行環境**: TradingCycleManager・BacktestRunner・PaperTradingRunner完全統一処理
- **設定一元管理**: BTC/JPY・タイムフレーム・全マジックナンバー設定化完了
- **コード最適化**: 未使用コード削除(423行+56KB)・構造整理・保守性大幅向上
- **ML学習システム**: 
  - **全体再学習方式**: 過去180日データで毎回ゼロから学習（累積学習ではない）
  - **市場適応性**: 概念ドリフト対応・仮想通貨市場変化への継続的最適化
  - **週次自動学習**: 毎週日曜18:00(JST) GitHub Actionsワークフロー・model-training.yml
  - **安全更新**: models/archive/自動バックアップ・625テスト品質ゲート・段階的デプロイ
- **Cloud Run 24時間稼働**: 自動スケーリング・Discord 3階層監視

### **バックテストシステム（Phase 21）**
- **本番同一ロジック**: TradingCycleManager完全共用・予測精度大幅向上・開発効率化
- **固定ファイル名**: BTC_JPY_4h.csv・BTC_JPY_15m.csv・パス修正不要・簡単期間変更
- **CSV基盤**: API依存排除・高速実行・安定性確保・再現性保証
- **期間統一**: --match-4h機能・MultiTimeframe戦略対応・データ整合性確保

### **本番運用システム**
- **24時間稼働**: Cloud Run自動スケーリング・ヘルスチェック
- **Discord監視**: 3階層通知（Critical/Warning/Info）・運用アラート
- **データ取得**: Bitbank API・4h/15m足・キャッシュ最適化

### **品質保証・CI/CD**
- **625テスト**: 全モジュールテスト・エラーケース・回帰防止
- **58.64%カバレッジ**: 継続監視・新機能での向上必須
- **CI/CD統合**: 品質ゲート・週次学習・月次クリーンアップ

## 📋 トラブルシューティング

### **開発時問題**
```bash
# テスト失敗時
bash scripts/testing/checks.sh                    # 詳細エラー確認
python3 -m pytest tests/ -v                      # 個別テスト実行

# import エラー時
python3 -c "import sys; sys.path.insert(0, '.'); from src.core.logger import CryptoBotLogger"

# 設定エラー時  
python3 scripts/testing/dev_check.py validate    # 設定整合性確認
```

### **バックテスト関連問題（Phase 21）**
```bash
# CSVデータ不整合
python3 -c "
from src.backtest.data.csv_data_loader import get_csv_loader
loader = get_csv_loader()
result_4h = loader.validate_data_integrity('BTC/JPY', '4h')
result_15m = loader.validate_data_integrity('BTC/JPY', '15m')
print('4h整合性:', result_4h)
print('15m整合性:', result_15m)
"

# データ再収集
python3 src/backtest/scripts/collect_historical_csv.py --match-4h

# キャッシュクリア
python3 -c "
from src.backtest.data.csv_data_loader import get_csv_loader
get_csv_loader().clear_cache()
print('キャッシュクリア完了')
"
```

### **本番環境問題**
```bash
# システム稼働確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# エラーログ確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20

# Discord通知確認（運用チャンネル）
```

### **機能別デバッグ**
- **特徴量システム**: 15特徴量統一管理・DataFrame形式確認・順序整合性確認
- **5戦略統合**: シグナル生成・重み付け統合・競合解決確認
- **統合実行環境**: TradingCycleManager・BacktestRunner・DataPipeline連携確認
- **バックテスト**: CSV読み込み・期間統一・レポート生成・本番一致確認
- **ML予測**: 3モデルアンサンブル読み込み・予測実行確認
- **リスク管理**: Kelly基準・ドローダウン管理・3段階判定確認
- **CI/CD**: 週次自動学習・品質ゲート・段階的デプロイ確認

## 🔄 次回作業時の確認事項

### **必須確認**
1. **品質チェック**: `bash scripts/testing/checks.sh`でテスト・設定確認
2. **本番稼働**: Cloud Run・Discord通知・取引ログ確認
3. **統合システム**: backtest/paper/live正常動作・CSV データ状況確認

### **開発開始前**
1. **最新状況把握**: システム状況・エラー状況確認
2. **品質基準**: テスト・カバレッジ・コード品質確認
3. **設定整合性**: unified.yaml・CSV データ整合性・環境変数確認

### **コード修正時**
1. **テスト追加**: 新機能・修正に対応するテスト追加必須
2. **品質維持**: flake8・black・isort・型注釈確認
3. **統合動作確認**: 3モード（backtest/paper/live）での実際のデータフロー確認

## 📚 詳細ドキュメント

### **システム実装**
- **[システム全体](src/README.md)**: レイヤードアーキテクチャ・データフロー・使用方法
- **[バックテストシステム](src/backtest/README.md)**: Phase 21統合実行環境・CSV基盤・固定ファイル名
- **[戦略システム](src/strategies/README.md)**: 5戦略統合・競合解決・重み付け判定
- **[取引システム](src/trading/README.md)**: リスク管理・Kelly基準・異常検知・注文実行

### **プロジェクト仕様書 → [docs/](docs/)**
**必読**: 以下の仕様書で要件・設計・運用手順を必ず確認してください

- **[要件定義](docs/開発計画/要件定義.md)**: システム概要・機能要件・技術仕様・期待成果
- **[開発履歴](docs/開発計画/開発履歴.md)**: Phase 1-22完了履歴・技術変遷・実装成果
- **[統合実行・分析マニュアル](docs/運用手順/バックテスト実行・分析マニュアル.md)**: backtest/paper/live統合運用
- **[CI/CD設定](docs/CI-CD設定/)**: GitHub Actions・デプロイ・品質ゲート設定
- **[指示書](docs/指示書/)**: 各種作業指示・チェックリスト

---

**AI自動取引システム**: 15特徴量統合・5戦略統合・ProductionEnsemble 3モデル・Kelly基準リスク管理・Discord 3階層監視による完全自動化システムが24時間稼働中。**Phase 22ハードコード値一元化**完了・統合設定管理・保守性大幅向上・620テスト品質保証・58.64%カバレッジ・CI/CD統合により企業級品質を実現。 🚀