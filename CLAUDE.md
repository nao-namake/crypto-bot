# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 現在の状況

### **システム状態**
- **AI自動取引システム**: 完全稼働中・Cloud Run 24時間運用・bitbank信用取引対応
- **資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **取引頻度**: 月100-200回・3分間隔実行（高頻度取引）・BTC/JPY専用
- **テスト品質**: 620テスト100%成功・64.74%カバレッジ維持
- **統合システム**: 15特徴量→5戦略（動的信頼度）→ML予測→リスク管理→取引実行の完全自動化
- **Secret Manager**: 2025/09/15修正完了（key:latest問題解決・具体的バージョン使用）

### **主要仕様**
- **Python**: 3.12・MLライブラリ互換性最適化・GitHub Actions安定版
- **戦略**: 5戦略統合（ATR・MochiPoy・MultiTimeframe・DonchianChannel・ADX）・動的信頼度計算
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
│   ├── reporting/              # レポーティング・Discord通知
│   └── services/               # システムサービス
├── data/                   # データ層（Bitbank API・キャッシュ）
├── features/               # 15特徴量生成システム
├── strategies/             # 5戦略統合システム
├── ml/                     # ProductionEnsemble・3モデル統合
├── trading/                # リスク管理・取引実行
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
bash scripts/testing/checks.sh                         # 620テスト・カバレッジ・約30秒

# 期待結果: ✅ 620テスト100%成功・64.74%カバレッジ通過
```

### **2. システム実行**
```bash
# 本番システム実行
python3 main.py --mode paper    # ペーパートレード
python3 main.py --mode live     # ライブトレード

# 期待結果: 15特徴量生成→5戦略実行→ML予測→リスク評価→BUY/SELL判定
```

### **3. 本番環境確認**
```bash
# Cloud Run稼働状況
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# 残高確認（Secret Manager修正後）
gcloud logging read "textPayload:\"残高\" OR textPayload:\"balance\"" --limit=5
```

## 🎯 開発原則

### **1. 品質保証必須**
- **テスト実行**: 開発前後に`checks.sh`必須実行・620テスト100%維持
- **カバレッジ**: 64.74%以上維持・新機能は必ずテスト追加
- **CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

### **2. システム理解必須**
- **アーキテクチャ**: レイヤードアーキテクチャ・各層責任明確
- **データフロー**: データ取得→特徴量生成→戦略実行→取引判断
- **エラーハンドリング**: カスタム例外・適切なログ・復旧機能

### **3. 設定管理統一**
- **ハードコード禁止**: すべて設定ファイル・環境変数で管理
- **階層化設定**: core/production/development環境別設定
- **Secret Manager**: 具体的バージョン番号使用（key:latest禁止）

### **4. 実装品質基準**
- **コード品質**: flake8・black・isort通過必須
- **ログ品質**: JST時刻・構造化ログ・Discord通知対応
- **テスト品質**: 単体・統合・エラーケーステスト完備

## 🚨 重要な技術ポイント

### **統合システム基盤**
- **feature_manager**: 15特徴量統一管理・config/core/feature_order.json参照
- **ProductionEnsemble**: 3モデルアンサンブル（LightGBM・XGBoost・RandomForest）
- **動的信頼度計算**: フォールバック回避・市場適応型0.25-0.6信頼度
- **ML学習システム**: 
  - **全体再学習方式**: 過去180日データで毎回ゼロから学習
  - **週次自動学習**: 毎週日曜18:00(JST) GitHub Actionsワークフロー
  - **安全更新**: models/archive/自動バックアップ・620テスト品質ゲート

### **Secret Manager管理（重要）**
- **修正済み**: 2025/09/15にkey:latest問題解決
- **現行設定**: 具体的バージョン使用
  - bitbank-api-key:3
  - bitbank-api-secret:3  
  - discord-webhook-url:5
- **注意**: Secret更新時はci.yml:319も同時更新必須

### **本番運用システム**
- **24時間稼働**: Cloud Run自動スケーリング・ヘルスチェック
- **Discord監視**: 3階層通知（Critical/Warning/Info）・運用アラート
- **データ取得**: Bitbank API・4h/15m足・キャッシュ最適化・残高取得正常化済み

## 📋 トラブルシューティング

### **開発時問題**
```bash
# テスト失敗時
bash scripts/testing/checks.sh                    # 詳細エラー確認

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

# 残高取得確認（修正後）
gcloud logging read "textPayload:\"BITBANK_API_KEY\" OR textPayload:\"残高\"" --limit=10
```

## 🔄 次回作業時の確認事項

### **必須確認**
1. **品質チェック**: `bash scripts/testing/checks.sh`でテスト・設定確認
2. **本番稼働**: Cloud Run・Discord通知・取引ログ確認
3. **残高取得**: Bitbank API 10,000円正常取得確認（修正効果確認）

### **開発開始前**
1. **最新状況把握**: システム状況・エラー状況確認
2. **品質基準**: テスト・カバレッジ・コード品質確認
3. **設定整合性**: config整合性・環境変数確認

---

**AI自動取引システム**: 15特徴量統合・5戦略統合・ProductionEnsemble 3モデル・Kelly基準リスク管理・Discord 3階層監視による完全自動化システムが24時間稼働中。620テスト品質保証・64.74%カバレッジ・CI/CD統合により企業級品質を実現。 🚀