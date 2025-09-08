# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 現在の状況

### **システム状態**
- **AI自動取引システム**: 完全稼働中・Cloud Run 24時間運用・bitbank信用取引対応
- **資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **取引頻度**: 月100-200回・高頻度取引・BTC/JPY専用
- **テスト品質**: 625テスト100%成功・58.64%カバレッジ維持
- **統合システム**: 12特徴量→4戦略→ML予測→リスク管理→取引実行の完全自動化
- **ドキュメント**: 全README更新完了・実用的構成に最適化

### **主要仕様（要件定義より）**
- **戦略**: 4戦略統合（ATR・フィボナッチ・もちぽよ・マルチタイムフレーム）
- **ML**: 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- **時間軸**: 4時間足（トレンド）+ 15分足（エントリー）
- **インフラ**: GCP Cloud Run・1Gi・1CPU・月額2,000円以内

## 📂 システム構造

```
src/                        # メイン実装
├── core/                   # 基盤システム
│   ├── orchestration/          # システム統合制御
│   ├── config/                 # 設定管理・特徴量管理
│   ├── execution/              # 取引実行制御  
│   ├── reporting/              # レポーティング
│   └── services/               # システムサービス
├── data/                   # データ層（Bitbank API・キャッシュ）
├── features/               # 12特徴量生成システム
├── strategies/             # 4戦略統合システム → [詳細](src/strategies/README.md)
├── ml/                     # ProductionEnsemble・3モデル統合
├── trading/                # リスク管理・取引実行 → [詳細](src/trading/README.md)
├── backtest/               # バックテストシステム
└── monitoring/             # Discord 3階層監視

scripts/testing/checks.sh   # 品質チェック（開発必須）
config/core/unified.yaml    # 統合設定ファイル
models/production/          # 本番MLモデル（週次更新）
```

## 🔧 開発ワークフロー

### **1. 品質チェック（開発時必須）**
```bash
# メイン品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh                         # 625テスト・カバレッジ・約30秒

# 軽量確認
python3 scripts/testing/dev_check.py validate         # 設定整合性チェック

# 期待結果: ✅ 625テスト100%成功・58.64%カバレッジ通過
```

### **2. システム実行**
```bash
# 本番システム実行
python3 main.py --mode paper    # ペーパートレード
python3 main.py --mode live     # ライブトレード

# 期待結果: 12特徴量生成→4戦略実行→ML予測→リスク評価→BUY/SELL判定
```

### **3. 本番環境確認**
```bash
# Cloud Run稼働状況
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# Discord通知確認（運用監視）
```

### **4. 開発・デバッグ**
```bash
# 特徴量生成テスト
python3 -c "
import asyncio, sys; sys.path.insert(0, '.')
from src.features.feature_generator import FeatureGenerator
# テストコード実行"

# MLモデル確認
python3 scripts/deployment/docker-entrypoint.sh verify
```

## 🎯 開発原則

### **1. 品質保証必須**
- **テスト実行**: 開発前後に`checks.sh`必須実行・625テスト100%維持
- **カバレッジ**: 58.64%以上維持・新機能は必ずテスト追加
- **CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

### **2. システム理解必須**
- **アーキテクチャ**: レイヤードアーキテクチャ・各層責任明確
- **データフロー**: データ取得→特徴量生成→戦略実行→取引判断
- **エラーハンドリング**: カスタム例外・適切なログ・復旧機能

### **3. 設定管理統一**
- **ハードコード禁止**: すべて設定ファイル・環境変数で管理
- **階層化設定**: core/production/development環境別設定
- **型安全性**: Protocol・dataclass・型注釈活用

### **4. 実装品質基準**
- **コード品質**: flake8・black・isort通過必須
- **ログ品質**: JST時刻・構造化ログ・Discord通知対応
- **テスト品質**: 単体・統合・エラーケーステスト完備

## 🚨 重要な技術ポイント

### **統合システム基盤**
- **feature_manager**: 12特徴量統一管理・config/core/feature_order.json参照
- **ProductionEnsemble**: 3モデルアンサンブル（LightGBM・XGBoost・RandomForest）
- **週次自動学習**: GitHub Actionsワークフロー・model-training.yml
- **Cloud Run 24時間稼働**: 自動スケーリング・Discord 3階層監視

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

### **本番環境問題**
```bash
# システム稼働確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# エラーログ確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20

# Discord通知確認（運用チャンネル）
```

### **機能別デバッグ**
- **特徴量システム**: 12特徴量統一管理・DataFrame形式確認・順序整合性確認
- **4戦略統合**: シグナル生成・重み付け統合・競合解決確認
- **ML予測**: 3モデルアンサンブル読み込み・予測実行確認
- **リスク管理**: Kelly基準・ドローダウン管理・3段階判定確認
- **CI/CD**: 週次自動学習・品質ゲート・段階的デプロイ確認

## 🔄 次回作業時の確認事項

### **必須確認**
1. **品質チェック**: `bash scripts/testing/checks.sh`でテスト・設定確認
2. **本番稼働**: Cloud Run・Discord通知・取引ログ確認
3. **システム状態**: FeatureGenerator→戦略フロー→リスク管理正常動作確認

### **開発開始前**
1. **最新状況把握**: システム状況・エラー状況確認
2. **品質基準**: テスト・カバレッジ・コード品質確認
3. **設定整合性**: config整合性・環境変数確認

### **コード修正時**
1. **テスト追加**: 新機能・修正に対応するテスト追加必須
2. **品質維持**: flake8・black・isort・型注釈確認
3. **動作確認**: 実際のデータフローでの動作確認

## 📚 詳細ドキュメント

### **システム実装**
- **[システム全体](src/README.md)**: レイヤードアーキテクチャ・データフロー・使用方法
- **[戦略システム](src/strategies/README.md)**: 4戦略統合・競合解決・重み付け判定
- **[取引システム](src/trading/README.md)**: リスク管理・Kelly基準・異常検知・注文実行

### **プロジェクト仕様書 → [docs/](docs/)**
**必読**: 以下の仕様書で要件・設計・運用手順を必ず確認してください

- **[要件定義](docs/開発計画/要件定義.md)**: システム概要・機能要件・技術仕様・期待成果
- **[開発履歴](docs/開発計画/開発履歴.md)**: Phase 1-19完了履歴・技術変遷・実装成果
- **[運用マニュアル](docs/運用手順/)**: 本番運用・監視・トラブル対応手順
- **[CI/CD設定](docs/CI-CD設定/)**: GitHub Actions・デプロイ・品質ゲート設定
- **[指示書](docs/指示書/)**: 各種作業指示・チェックリスト

---

**AI自動取引システム**: 12特徴量統合・4戦略統合・ProductionEnsemble 3モデル・Kelly基準リスク管理・Discord 3階層監視による完全自動化システムが24時間稼働中。625テスト品質保証・58.64%カバレッジ・CI/CD統合により企業級品質を実現。 🚀