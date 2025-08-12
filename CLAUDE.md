# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 最重要：開発ワークフロー

### **必須の品質チェックフロー**

```bash
# 1. コード変更後、必ず実行
bash scripts/ci_tools/checks.sh

# 2. データ取得ロジックの事前検証（🆕 2025/8/12追加）
python scripts/bot_manager.py data-check

# 3. デプロイ前の包括的検証
python scripts/bot_manager.py full-check

# 4. エラーがあれば自動修復
python scripts/bot_manager.py fix-errors --auto-fix

# 5. 問題なければコミット＆プッシュ
git add -A && git commit -m "your message" && git push origin main
```

### **🎊 完璧稼働状況確認システム（最重要）**

**🆕 2025年8月12日完成 - 隠れたエラー問題の根本解決**:
```bash
# CI通過後の完璧稼働状況確認（推奨・新システム）
python scripts/operational_status_checker.py              # 全4段階チェック実行
python scripts/operational_status_checker.py --verbose    # 詳細ログ付き
python scripts/operational_status_checker.py --phase phase3  # 隠れた問題のみ検出

# 特定の問題調査時
python scripts/operational_status_checker.py --save-report  # HTMLレポート生成
```

**解決する問題**:
- ✅ **表面稼働・実際停止**: ヘルス200だが数時間前からログなし → 検出
- ✅ **毎回異なる手法**: 固定4段階チェックで一貫した確認
- ✅ **隠れたエラー見逃し**: 過去10パターン自動検出で確実発見
- ✅ **UTC/JST混在**: JST統一時刻で時刻混乱解消

**4段階チェック内容**:
| Phase | 内容 | 重み | 検出項目 |
|-------|------|------|---------| 
| Phase 1 | インフラ・基盤確認 | 25% | GCP Cloud Run・API接続・システムヘルス |
| Phase 2 | アプリ動作確認 | 30% | ログ分析・データ取得・シグナル生成 |
| Phase 3 | 隠れた問題検出 | 30% | **過去10パターン**・パフォーマンス異常 |
| Phase 4 | 総合判定・報告 | 15% | スコアリング・アクション提案・HTML生成 |

### **従来のGCP稼働状況確認（参考）**

**日本時間（JST）での確認方法**:
```bash
# CI通過後30分経過時の確認（最新リビジョンのみ自動選択）
python scripts/utilities/gcp_log_viewer.py --hours 0.5

# エラーログのみ確認
python scripts/utilities/gcp_log_viewer.py --severity ERROR --hours 1

# 古いリビジョンの削除（ログの混乱防止）
bash scripts/utilities/cleanup_old_revisions.sh --dry-run
```

### **統合CLIツール（bot_manager.py）**

**すべての検証・監視・修復を1つで管理：**

| コマンド | 用途 | 時間 |
|---------|------|------|
| `status` | システム状態確認 | 即時 |
| `validate --mode quick` | 高速検証 | 1分 |
| `monitor --hours 24` | シグナル監視 | 指定時間 |
| `paper-trade --hours 2` | リスクフリーテスト | 指定時間 |
| `fix-errors --auto-fix` | エラー自動修復 | 5分 |
| `full-check` | 完全検証 | 15分 |

## 🎯 プロジェクト基本方針

### **個人開発プロジェクトの特徴**
- **開発者**: 単一個人（共同開発予定なし）
- **用途**: 個人的な暗号資産取引専用
- **方針**: シンプル・実用性・効率重視
- **コスト**: 月額2,000円以内での運用

### **作業時の判断基準**
✅ **推奨**:
- 個人が理解・保守可能な実装
- 実際の取引に必要な機能
- シンプルな設定・直接的な解決策

❌ **避ける**:
- チーム開発向けの複雑な仕組み
- 過度な抽象化・汎用化
- エンタープライズ向け設定

### **README.md優先原則**
**各フォルダで作業前に必ずREADME.mdを読む**:
- 目的・設計原則・命名規則を理解
- 既存のファイル構成を把握
- 記載された課題・改善点を確認

## 🎊 現在のシステム状況（2025年8月12日）

### **🎯 完璧稼働状況確認システム完成 - 隠れたエラー問題根絶**

**🆕 新システム完成（2025年8月12日）**:
1. ✅ **operational_status_checker.py**: 4段階チェックシステム（2,100行）
   - 過去10パターンの隠れたエラー自動検出
   - 既存監視ツール4つを統合・重複排除
   - JST時刻統一・美しいHTMLレポート生成
   
2. ✅ **status_config.json**: 隠れたエラーパターンDB
   - データ取得停滞（48/300問題）
   - 表面稼働・実際停止（ヘルス200+ログ古い）  
   - メインループ未到達・リビジョン切替失敗等
   
3. ✅ **使い分け明確化**: 
   - デプロイ前: `bot_manager.py` (包括チェック)
   - CI通過後: `operational_status_checker.py` (稼働確認)

**重大問題の完全解決（2025年8月12日）**:
1. ✅ **BitbankCoreExecutor import エラー完全解決**
   - `PositionSide`クラス実装・完全統合
   - `BitbankCoreExecutor`最小実装完成（14テスト全通過）
   
2. ✅ **API接続エラー完全解決**
   - `fetch_ticker`メソッド実装・型定義追加
   - API接続テスト成功: BTC/JPY = 17,582,151 JPY
   
3. ✅ **データ重複取得問題修正**
   - ATR初期化データキャッシュ機能実装
   - メインループ効率化・API負荷軽減

4. ✅ **運用ツール大幅強化**
   - GCP日本時間ログビューア追加
   - 古いリビジョン自動削除機能
   - データ検証強化システム

**品質保証完了**:
- ✅ **611/611テスト成功**（42スキップ）
- ✅ **31.54%カバレッジ**（必要14%の2倍以上達成）
- ✅ **flake8/isort/black完全準拠**
- ✅ **CI/CD Pipeline Ready**

## 🚀 システム技術仕様

### **crypto-bot: AI自動取引システム**
BitbankでのBTC/JPY自動取引を行うMLシステム

**核心技術**:
- **97特徴量システム**: テクニカル指標・市場状態・時間特徴量
- **アンサンブル学習**: LightGBM + XGBoost + RandomForest統合
- **リアルタイム予測**: 1時間足データでのエントリーシグナル生成
- **Kelly基準リスク管理**: 動的ポジションサイジング

**インフラ**:
- **GCP Cloud Run**: 自動スケーリング・堅牢性
- **月額2,000円**: 低コスト運用（prodのみ）
- **高速CI/CD**: GitHub Actions・5分以内デプロイ

### **システム構成**

```
crypto_bot/
├── cli/           # CLIコマンド（live・backtest・train等）
├── data/          # データ取得・前処理（fetcher分割システム）
├── ml/            # 機械学習（97特徴量・アンサンブル予測）
├── strategy/      # 戦略・エントリー判定・リスク管理
├── execution/     # Bitbank API・取引実行
├── utils/         # 共通機能・ログ・設定管理
└── main.py        # エントリーポイント

scripts/           # 開発・運用ツール（5カテゴリ整理済み）
├── bot_manager.py # 統合CLI（11個別スクリプトを統合）
├── operational_status_checker.py # 🆕 完璧稼働状況確認システム
├── status_config.json # 🆕 隠れたエラーパターンDB
├── ci_tools/      # CI/CD前ツール
├── model_tools/   # モデル管理
├── system_tools/  # システム管理・診断
├── data_tools/    # データ準備・分析
└── monitoring/    # 監視・検証・修復（Phase 2-3）

config/production/production.yml  # 本番設定（固定）
models/production/model.pkl       # 本番モデル（固定）
```

### **データフロー**

```
Bitbank API → 1時間足OHLCV取得
    ↓
97特徴量エンジニアリング
    ↓
TradingEnsembleClassifier予測（3モデル統合）
    ↓
エントリーシグナル判定（confidence > 0.35）
    ↓
Kelly基準リスク管理（ポジションサイジング）
    ↓
Bitbank自動取引実行（信用取引）
```

## 🛠️ 開発・運用コマンド

### **日常開発**
```bash
# 品質チェック（コミット前必須）
bash scripts/ci_tools/checks.sh

# ライブトレード（本番設定）
python -m crypto_bot.main live-bitbank --config config/production/production.yml

# バックテスト
python -m crypto_bot.main backtest --config config/validation/unified_97_features_backtest.yml
```

### **デプロイ前検証**
```bash
# 3段階検証システム
bash scripts/ci_tools/validate_all.sh              # フル（〜10分）
bash scripts/ci_tools/validate_all.sh --quick      # 高速（〜1分）
bash scripts/ci_tools/validate_all.sh --ci         # CI用（〜3分）
```

### **Phase 2-3システム**
```bash
# ペーパートレード（リスクフリーテスト）
python scripts/bot_manager.py paper-trade --hours 2

# シグナル監視（異常検出）
python scripts/bot_manager.py monitor --hours 24

# 未来データリーク検出（時系列検証）
python scripts/bot_manager.py leak-detect
```

### **Phase 3システム**
```bash
# エラー分析・自動修復
python scripts/bot_manager.py fix-errors --auto-fix
python scripts/bot_manager.py fix-errors --interactive
```

### **システム監視**
```bash
# ヘルスチェック
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health

# GCPログ確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"TRADE\"" --limit=10
```

### **インフラ管理**
```bash
# Terraform検証
cd infra/envs/prod/
terraform validate && terraform plan

# デプロイ
git push origin main  # CI/CD自動実行・5分以内完了
```

## 🔍 トラブルシューティング

### **よくある問題**

**1. データ取得エラー**
```bash
# 対処: config/production/production.yml の since_hours・limit 値調整
# 確認（日本時間）: python scripts/utilities/gcp_log_viewer.py --search "Progress" --hours 1
# 旧方法（UTC）: gcloud logging でProgress状況をチェック
```

**2. モデル予測エラー**
```bash
# 症状: "No ensemble models are ready"
# 対処: python scripts/model_tools/create_proper_ensemble_model.py
# 確認: python scripts/utilities/gcp_log_viewer.py --search "model" --severity ERROR
```

**3. 取引実行されない**
```bash
# 症状: 予測はできるが取引なし
# 原因: confidence < 0.35
# 確認（日本時間）: python scripts/utilities/gcp_log_viewer.py --search "confidence"
```

### **緊急時対応**
- **取引停止**: `python scripts/utilities/emergency_shutdown.py`
- **システム再起動**: GitHub push（CI/CD自動再デプロイ）
- **ロールバック**: 前バージョンのmodel.pkl・production.ymlに戻す

## 📋 ファイル管理原則

### **本番ファイル（固定名・変更不可）**
- `config/production/production.yml` - 本番設定
- `models/production/model.pkl` - 本番モデル

### **アーカイブ管理**
- `archive/legacy_systems/` - 廃止システム
- `archive/records/` - 運用記録・テスト結果
- `scripts/deprecated/` - 整理済み古いスクリプト（63ファイル）

### **重要README所在地**
- `/crypto_bot/[各サブフォルダ]/README.md` - 各モジュール仕様
- `/scripts/README.md` - スクリプト管理ガイド
- `/scripts/[各サブフォルダ]/README.md` - 詳細使用方法
- `/tests/README.md` - テスト構造・実行方法
- `/config/README.md` - 設定ファイル管理
- `/models/README.md` - モデル管理・昇格フロー

## 🎯 達成成果サマリー

### **完璧稼働状況確認システム完成（2025年8月12日）**
- **隠れたエラー問題根絶**: 4段階チェック・過去10パターン検出システム
- **毎回異なる手法問題解決**: 固定チェック手順で一貫した確認方法確立
- **JST時刻統一**: UTC/JST混在問題完全解消・時刻混乱防止
- **既存ツール統合**: 4つの監視スクリプト統合・重複排除完了

### **Phase 2-3/Phase 3完全実装（2025年8月11日）**
- **デプロイ前エラー根絶**: ChatGPT提案システム完全実装
- **統合CLI**: 11個別スクリプトをbot_manager.pyで統合管理
- **scripts整理**: 5カテゴリ・63古いファイル整理・各フォルダREADME完備
- **品質保証**: 605テスト成功・32.32%カバレッジ・完全準拠

### **技術的成果**
- **97特徴量×アンサンブル学習**: 高精度予測実現
- **8つの隠れたエラー解決**: API認証・モデル・CI/CD等の根本解決
- **モジュラー設計**: 10,644行削除・保守性向上
- **CI/CD完全修正**: GitHub Actions正常化・5分以内デプロイ

### **運用成果**
- **安定稼働**: GCP Cloud Run・24/7自動運用
- **低コスト**: 月額2,000円・高効率インフラ
- **完全自動化**: git push → デプロイまで全自動
- **事前検証体制**: 3段階検証でデプロイ前エラー防止

---

**🚀 「表面稼働・実際停止」「隠れたエラー見逃し」を根絶した完璧稼働状況確認システム搭載AI自動取引システム**（2025年8月12日完成）