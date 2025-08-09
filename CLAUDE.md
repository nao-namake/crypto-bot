# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 重要な作業原則（必須）

### **README.md優先原則**
各フォルダで作業を行う前に、必ず以下の手順を実行してください：

1. **作業前の必須確認**
   ```
   1. 対象フォルダのREADME.mdを必ず最初に読む
   2. フォルダの目的・役割・設計原則を理解する
   3. 既存のファイル構成と命名規則を確認する
   4. 記載されている課題・改善点を把握する
   ```

2. **作業時の遵守事項**
   ```
   - README.mdに記載された設計原則に従う
   - 既存の命名規則・コーディング規約を維持する
   - 新規ファイル追加時は適切なセクションに配置
   - 変更後はREADME.mdの更新も検討する
   ```

3. **重要なREADME.md所在地**
   - `/crypto_bot/[各サブフォルダ]/README.md` - 各モジュールの詳細仕様
   - `/scripts/README.md` - スクリプト管理ガイド
   - `/tests/README.md` - テスト構造・実行方法
   - `/config/README.md` - 設定ファイル管理
   - `/models/README.md` - モデル管理・昇格フロー
   - `/infra/README.md` - インフラ管理ガイド

4. **違反を避けるべき事項**
   ```
   ❌ README.mdを読まずに作業開始
   ❌ 既存の設計原則を無視した実装
   ❌ 独自の命名規則の導入
   ❌ フォルダの役割から逸脱した機能追加
   ```

## 📋 システム要件定義・開発方針

### **🎯 プロジェクト性格・開発体制**

このシステムは**完全な個人開発プロジェクト**であり、以下の特徴を持ちます：

```
📌 個人開発限定システム
├── 開発者: 単一個人（共同開発予定なし）
├── 用途: 個人的な暗号資産取引専用
├── 規模: 小規模・効率重視
└── 方針: シンプル・実用性優先
```

### **⚡ 開発・運用方針**

**シンプル・効率重視の原則**:
- **過剰な設定排除**: エンタープライズ向け複雑設定は不要
- **デプロイ手順簡素化**: 個人使用のため、複雑なCI/CD手順・承認フロー不要
- **ドキュメント実用性**: 個人理解・保守性重視、過度な文書化は避ける
- **機能最小限**: 必要最小限機能に集中、汎用性より専用性重視

**個人開発最適化指針**:
```bash
✅ 推奨アプローチ
- シンプルな設定ファイル（production.yml一択）
- 直接的なデプロイコマンド
- 必要最小限の監視・ログ
- 個人理解しやすいコード構造

❌ 避けるべきアプローチ  
- 複数環境対応（dev/staging/prod分離）
- 複雑な承認・レビューフロー
- 過剰なセキュリティ・監査機能
- チーム開発向け設定・文書
```

### **🔧 技術選択基準**

**個人使用特化の技術判断**:
- **学習コスト**: 個人で理解・保守可能な技術選択
- **運用負荷**: 最小限の運用作業で稼働継続
- **コスト効率**: 月額2,200円以内での運用最適化
- **実装速度**: 迅速な機能実装・問題解決重視

### **🎯 Claude Code作業時の重要指針**

**個人開発プロジェクトとしての作業方針**:

```bash
🔍 問題解決アプローチ
├── 実用性重視: 動作する最小限の解決策を優先
├── シンプル実装: 複雑な設計パターンより直接的解決
├── 迅速修正: エラー発生時は即座に実用的修正
└── 個人理解: コメント・説明は個人保守性重視

⚡ 開発効率化指針
├── 設定統一: production.yml中心の単一設定管理
├── デプロイ簡素: git push → CI/CD自動実行で完結
├── 監視最小限: 必要な監視のみ、過剰なメトリクス回避
└── 文書実用性: 作業に直接必要な情報のみ記載
```

**作業時の判断基準**:
- ✅ **個人が理解・保守可能か？**
- ✅ **実際の取引に必要な機能か？**  
- ✅ **コスト・運用負荷は適切か？**
- ❌ チーム開発・エンタープライズ機能は不要
- ❌ 過度な抽象化・汎用化は避ける

---

## 現在のシステム概要 (2025年8月10日最終更新)

### 🎊 **crypto-bot: 次世代AI自動取引システム**

BitbankでのBTC/JPY自動取引を行う高度なMLシステムです。Phase 1-19+の継続的改善により、安定性・精度・運用効率・CI/CD高速化を大幅に向上させました。

### **🚀 システム特徴**

**機械学習・予測精度**：
- **97特徴量システム**: テクニカル指標・市場状態・時間特徴量の最適化セット
- **アンサンブル学習**: LightGBM + XGBoost + RandomForest統合モデル
- **リアルタイム予測**: 1時間足データでの高精度エントリーシグナル生成

**インフラ・運用**：
- **GCP Cloud Run**: 自動スケーリング対応の堅牢なコンテナ実行環境
- **高速CI/CD**: GitHub Actions・Terraform処理時間 5分以内達成
- **低コスト運用**: 月額2,200円（dev: 200円、prod: 2,000円）

**データ・アーキテクチャ**：
- **modular design**: cli/、data/、ml/、strategy/、execution/ の責任分離設計
- **fetcher分割システム**: 高効率なデータ取得・前処理パイプライン
- **archive管理**: 開発履歴・設定バックアップの体系的保管

### **🏗️ 開発進化の軌跡**

**基盤技術確立期（Phase 1-11）**
- 機械学習基盤構築・97特徴量システム・外部API依存除去・取引実行基盤

**システム成熟期（Phase 12-17）** 
- モジュラーアーキテクチャ設計・10,644行コード最適化・文書体系整備・品質保証体制

**運用最適化期（Phase 18-19+）**
- エントリーシグナル問題解決・Terraform Infrastructure安定化・CI/CD高速化（5分以内達成）

## 主要機能・技術仕様

### **🎛️ 現在のシステム構成**

```
crypto_bot/                    # メインアプリケーション
├── cli/                       # CLIコマンド（backtest・live・train等）
├── data/                      # データ管理
│   ├── fetcher.py            # 統合データ取得API
│   └── fetching/             # 分割システム（Phase 16）
├── ml/                        # 機械学習パイプライン  
│   ├── feature_master_implementation.py  # 97特徴量エンジン
│   └── preprocessor.py       # データ前処理
├── strategy/                  # 戦略・リスク管理
├── execution/                 # Bitbank取引実行
├── utils/                     # 共通ユーティリティ
└── main.py                   # エントリーポイント（130行・95%削減達成）

config/production/production.yml  # 本番設定（固定ファイル）
models/production/model.pkl       # 本番モデル（固定ファイル）
infra/envs/prod/                   # 本番インフラ（Terraform）
```

### **🧠 97特徴量システム**

**構成**: OHLCV基本データ(5) + 高度ML特徴量(92) = 97特徴量

**主要カテゴリ**:
- **基本ラグ・リターン**: close_lag_1/3, returns_1/2/3/5/10
- **移動平均・トレンド**: ema_5/10/20/50/100/200, price_position_20/50
- **テクニカル指標**: RSI, MACD, Bollinger Bands, ATR, Stochastic
- **出来高分析**: VWAP, OBV, CMF, MFI, volume系指標
- **高度パターン**: サポレジ、ブレイクアウト、ローソク足パターン
- **市場状態**: volatility_regime, momentum_quality, market_phase
- **時間特徴**: hour, day_of_week, session分析

詳細は `config/production/production.yml` の `extra_features` セクション参照

### **🤖 アンサンブル学習システム**

**TradingEnsembleClassifier**:
- **LightGBM**: 高速・高精度な勾配ブースティング（重み: 0.5）
- **XGBoost**: 堅牢な性能の勾配ブースティング（重み: 0.3）
- **RandomForest**: アンサンブル効果による安定性（重み: 0.2）  
- **Stacking方式**: trading_stacking統合・confidence_threshold: 0.35

### **📊 本番運用状況**

**システム状態**: ✅ **正常稼働中**（GCP Cloud Run・Phase 19+対応）
- **取引モード**: live（BTC/JPY自動取引）
- **予測精度**: 97特徴量アンサンブル学習
- **リスク管理**: Kelly基準・信用取引対応

**運用パラメータ**:
- **エントリー閾値**: confidence > 0.35
- **リスク許容**: 1取引あたり1%・最大3%
- **データソース**: Bitbank 1時間足・96時間分
- **実行環境**: GCP Cloud Run・自動スケーリング

## 開発・運用コマンド

### **🚀 ローカル開発**

```bash
# 依存関係チェック（Phase 12.5実装）
python requirements/validate.py
make validate-deps

# 品質チェック実行
bash scripts/checks.sh
# 期待結果: flake8・isort・black・pytest全通過

# ライブトレード（本番設定）
python -m crypto_bot.main live-bitbank --config config/production/production.yml

# バックテスト実行
python -m crypto_bot.main backtest --config config/validation/unified_97_features_backtest.yml

# モデル再学習
python scripts/retrain_97_features_model.py
python scripts/create_proper_ensemble_model.py
```

### **🔧 システム監視**

```bash
# 本番システムヘルスチェック
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health

# GCPログ監視
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"TRADE\"" --limit=10

# システム性能分析
python scripts/analyze_live_performance.py
```

### **🏗️ インフラ操作（Phase 19+高速化対応）**

```bash
# Terraformローカル検証（Phase 19+高速化設定）
cd infra/envs/prod/ 
terraform validate && terraform plan
# 期待: 5分以内処理・FEATURE_MODE削除確認

# 高速CI/CDデプロイ（本番環境）
git push origin main  # GitHub Actions自動実行・5分以内完了

# GCP Phase 19+状況確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=3
```

## アーキテクチャ・データフロー

### **🔄 データフロー**

```
Bitbank API → 1時間足OHLCV取得
    ↓
97特徴量エンジニアリング（テクニカル指標・市場状態・時間特徴量）
    ↓  
TradingEnsembleClassifier予測（LGBM+XGBoost+RandomForest統合）
    ↓
エントリーシグナル判定（confidence threshold: 0.35）
    ↓
Kelly基準リスク管理（ポジションサイジング・ストップロス）
    ↓
Bitbank自動取引実行（信用取引・手数料最適化）
```

### **🏛️ システムアーキテクチャ**

**責任分離設計**:
- **CLI**: コマンドライン操作（backtest・live・train・optimize等）
- **Data**: 取得・前処理・キャッシュ管理（fetching/分割システム）
- **ML**: 特徴量エンジニアリング・モデル管理・予測
- **Strategy**: エントリー判定・リスク管理・シグナル生成
- **Execution**: Bitbank API・注文管理・手数料最適化
- **Utils**: 設定管理・ログ・エラーハンドリング

**モジュラー設計**:
- **互換性レイヤー**: 既存import継続動作保証
- **段階的移行**: 新機能統合時の安全性確保  
- **テスト容易性**: 単体・統合テスト効率化

## 運用指針・重要事項

### **📋 開発ワークフロー**

**品質保証**:
1. README.md優先原則 - 作業前に必ず対象フォルダのREADME.mdを読む
2. 品質チェック - `bash scripts/checks.sh` でflake8・pytest・カバレッジ確認
3. 依存関係検証 - `python requirements/validate.py` でEnvironment Parity確認

**本番デプロイフロー**:
1. ローカルテスト・品質チェック
2. GitHub push → CI/CD自動実行
3. Terraform適用 → GCP Cloud Run デプロイ
4. ヘルスチェック・監視ログ確認

### **🛠️ ファイル管理原則**

**本番ファイル固定**:
- `config/production/production.yml` - 本番設定（固定ファイル名）
- `models/production/model.pkl` - 本番モデル（固定ファイル名）
- 検証→本番昇格ワークフロー（validation/ → production/上書き）

**Archive管理**:
- `archive/legacy_systems/` - 廃止システム・古い設定
- `archive/records/` - 運用記録・テスト結果・カバレッジレポート
- 開発履歴保持・トレーサビリティ維持

### **💰 コスト・運用効率**

**月額運用コスト**: 2,200円（dev: 200円、prod: 2,000円）
- CPU/メモリ環境別最適化（dev: 500m/1Gi、prod: 1000m/2Gi）
- Static Environment Variables採用で安定性確保
- 外部API依存除去によるコスト削減・エラー要因除去

**運用効率化**:
- Phase 16分割システムによる10,644行削除・保守性向上
- modular design による開発効率最大化
- Phase 19+高速CI/CD: Terraform処理時間 5分以内達成・古いリソース削除・環境変数最適化完了

## トラブルシューティング・重要事項

### **🚨 よくある問題と対処法**

**1. データ取得エラー**
```bash
# データ取得エラー
# 対処: config/production/production.yml の since_hours・limit 値調整
# 確認: gcloud logging でProgress状況をチェック
```

**1.5. Phase 19+ CI/CDエラー**
```bash
# CI/CD・Terraformエラー  
# 対処: Phase 19+最適化済み（5分以内処理・環境変数3個に最適化）
# 確認: infra/envs/prod/ でローカル検証後にCI/CD実行
```

**2. モデル予測エラー**
```bash
# 症状: "No ensemble models are ready"
# 原因: models/production/model.pkl が無いか破損
# 対処: python scripts/create_proper_ensemble_model.py 実行
```

**3. 取引実行エラー**  
```bash
# 症状: 予測はできるがトレードが発生しない
# 原因: confidence < threshold (0.35)
# 対処: gcloud logging でconfidence値確認・閾値調整検討
```

### **🔍 システム診断手順**

**Step 1: 基本ヘルスチェック**
```bash
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health
# 期待: {"status":"healthy","mode":"live"}
```

**Step 2: ログ分析**
```bash
# 直近のトレード実行確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"TRADE\"" --limit=5

# エラー確認
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" --limit=10

# 予測confidence確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"confidence\"" --limit=5
```

**Step 3: データ品質確認**
```bash
# データ取得状況確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"Progress:\"" --limit=3

# 97特徴量生成確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"features\"" --limit=3
```

### **⚡ 緊急時対応**

**取引停止**: `scripts/emergency_shutdown.py`実行
**システム再起動**: GitHub push（CI/CD自動再デプロイ）
**ロールバック**: 前バージョンのmodel.pkl・production.ymlに戻す

---

## 🎯 開発成果サマリー

### **解決された主要課題**
- **取引実行基盤**: 97特徴量システム・アンサンブル学習・リスク管理統合
- **システム安定性**: データ取得最適化・エラー処理強化・品質保証体制
- **開発効率**: モジュラー設計（10,644行削除）・文書体系整備・CI/CD高速化
- **運用最適化**: インフラ安定化・コスト効率化・監視体制確立

### **現在のシステム特徴**
- ✅ **高精度予測**: 97特徴量×アンサンブル学習（LGBM+XGBoost+RF）
- ✅ **安全なリスク管理**: Kelly基準・信用取引・動的ポジションサイジング
- ✅ **効率的運用**: 月額2,200円・自動スケーリング・CI/CD 5分以内
- ✅ **保守性**: モジュラー設計・完全文書化・テスト体制（579テスト）

---

**🚀 継続的改善により進化し続ける次世代AI自動取引システム** （2025年8月10日現在）

