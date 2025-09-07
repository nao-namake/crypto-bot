# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 最重要：現在の開発状況（2025年9月7日現在）

### **✅ Phase 19.1完了・4戦略統合システム詳細解明完成**

**現在の状況**: 
- **Phase 19.1完了**: 4戦略統合システム詳細解明・競合解決メカニズム・信頼度閾値システム・取引判定フロー完全理解
- **Phase 19+攻撃的設定完成**: feature_manager 12特徴量統合・ProductionEnsemble 3モデル統合・**攻撃的戦略ロジック実装**・**Dynamic Confidence完成**・週次自動学習・Cloud Run 24時間稼働統合
- **攻撃的取引システム完成**: **月100-200取引対応**・1万円運用最適化・戦略攻撃化・取引機会最大化・リスク管理攻撃化
- **全README更新完成**: 攻撃的設定対応更新・4戦略統合システム詳細分析反映・Phase 19+攻撃的設定反映・企業級品質保証ドキュメント体系確立
- **625テスト品質保証**: 100%通過・58.64%カバレッジ維持・攻撃的設定対応・CI/CD完全統合・回帰防止完備

**🎯 最新システム状態（Phase 19+攻撃的設定完成）**:
```
🏆 攻撃的MLOps統合システム: feature_manager 12特徴量統合・ProductionEnsemble 3モデル統合・攻撃的戦略ロジック・企業級品質保証完備
🏆 攻撃的取引システム: 月100-200取引対応・ATRBased不一致取引・MochipoyAlert 1票取引・Dynamic Confidence完成
🏆 週次自動学習: GitHub Actions週次学習ワークフロー・CI/CD品質ゲート・段階的デプロイ・自動モデル更新
🏆 Cloud Run統合: 24時間稼働・スケーラブル実行・Discord 3階層監視・攻撃的運用最適化・自動スケーリング
🏆 625テスト品質保証: 58.64%カバレッジ・攻撃的設定対応テスト・品質管理完備・回帰防止・継続監視
🏆 ドキュメント統合: 全README攻撃的設定対応・Phase 19+統一・企業級ドキュメント体系確立
```

**重要**: Phase 19+攻撃的設定完成・全README更新完成・企業級品質保証・**月100-200取引実用的攻撃的AI自動取引システム稼働中**

## 📂 システム構造（2025年9月6日 Phase 19+攻撃的設定完成版）

```
src/                    # 攻撃的MLOps統合メインシステム（625テスト100%・Phase 19+攻撃的設定完成）
├── core/              # MLOps統合基盤システム
│   ├── orchestration/       # 統合制御・MLアダプター
│   │   ├── orchestrator.py      # システム統合制御（534行・Protocol分離）
│   │   ├── ml_adapter.py        # MLサービス統合（660行・フォールバック対応）
│   │   └── ml_loader.py         # MLOpsモデル読み込み（ProductionEnsemble優先・週次学習対応）
│   ├── config/             # MLOps統合設定システム・特徴量管理
│   │   └── feature_manager.py   # feature_manager 12特徴量統一管理・ProductionEnsemble連携★MLOps統合
│   ├── logger.py          # JST対応ログ・構造化出力・Discord統合
│   ├── exceptions.py      # カスタム例外・階層化エラー処理
│   └── protocols.py       # Protocol分離・型安全性
│   
├── features/          # MLOps統合特徴量システム（Phase 19 MLOps統合完成）
│   └── feature_generator.py   # feature_manager統合FeatureGenerator（12特徴量統一・ProductionEnsemble連携・週次学習対応）
│   
├── strategies/        # 攻撃的MLOps統合取引戦略（4戦略・攻撃的ロジック・Dynamic Confidence・feature_manager連携・ProductionEnsemble統合・週次学習対応）
├── ml/                # MLOps統合機械学習（ProductionEnsemble 3モデル統合・週次自動学習・625テスト品質保証）
├── data/              # データ層（Bitbank API・パイプライン・キャッシュ）
├── backtest/          # バックテスト（統一レポーター・効率化完了）
├── trading/           # 取引実行（リスク管理・Kelly基準）
└── monitoring/        # MLOps統合監視（Discord 3階層監視・Cloud Run 24時間稼働監視・週次学習監視）

scripts/               # 攻撃的MLOps統合スクリプト群
├── testing/checks.sh       # 攻撃的MLOps統合品質チェック（625テスト・58.64%カバレッジ・攻撃的設定対応・30秒実行）
└── ml/create_ml_models.py  # MLOps統合モデル学習（ProductionEnsemble・週次学習・Git追跡・自動アーカイブ）★MLOps統合

.github/workflows/     # 攻撃的MLOps統合CI/CD自動化
├── ci.yml            # 攻撃的MLOps品質チェック・本番デプロイ（毎回プッシュ・625テスト・攻撃的設定品質ゲート）
├── cleanup.yml       # MLOps統合GCPリソースクリーンアップ（月次・Cloud Run最適化）
└── model-training.yml # MLOps統合週次自動学習（ProductionEnsemble更新・段階的デプロイ）★MLOps統合

config/               # MLOps統合階層化設定・特徴量定義
├── core/feature_order.json  # feature_manager 12特徴量統一定義・MLOps全システム参照★MLOps統合KEY
└── ...               # MLOps環境別設定・YAML統合・Cloud Run対応

models/               # MLOps統合モデル・バージョン管理
├── production/       # ProductionEnsemble本番モデル（3モデル統合・Git情報・週次更新対応）
├── training/         # MLOps学習用個別モデル（週次自動学習・品質検証）
└── archive/          # MLOps自動アーカイブ・履歴保持・品質トレーサビリティ★MLOps統合
```

## 🔧 開発ワークフロー（2025年9月最新版）

### **1. 品質チェック（開発時必須・攻撃的設定対応）**
```bash
# メイン品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh                         # 625テスト・攻撃的設定対応・カバレッジ・約30秒

# 軽量システム確認
python3 scripts/testing/dev_check.py validate       # 設定・整合性チェック

# 期待結果: ✅ 625テスト100%成功・58.64%カバレッジ・攻撃的設定品質保証通過
```

### **2. 攻撃的システム実行**
```bash
# 攻撃的本番システム実行
python3 main.py --mode paper    # ペーパートレード（攻撃的設定）
python3 main.py --mode live     # ライブトレード（攻撃的本番・月100-200取引）

# 期待結果: 12特徴量生成→4攻撃的戦略実行→Dynamic Confidence→攻撃的取引判断→BUY/SELLシグナル生成
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

## 🎯 開発原則・方針（2025年9月版）

### **1. 品質保証必須**
- **テスト実行**: 開発前後に`checks.sh`必須実行・654テスト100%維持
- **カバレッジ**: 59.24%以上維持・新機能は必ずテスト追加
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

### **Phase 19 MLOps統合システム基盤**
- **feature_manager統合**: 12特徴量統一管理・feature_order.json単一真実源・ProductionEnsemble連携・全システム統合
- **ProductionEnsemble統合**: 3モデルアンサンブル（LightGBM 40%・XGBoost 40%・RandomForest 20%）・重み付け投票・feature_manager連携
- **週次自動学習**: GitHub Actionsワークフロー・model-training.yml・自動モデル更新・CI/CD品質ゲート・段階的デプロイ
- **Cloud Run 24時間稼働**: スケーラブル実行・Discord 3階層監視（Critical/Warning/Info）・自動スケーリング・本番運用最適化

### **本番運用中システム**
- **24時間稼働**: Cloud Run自動スケーリング・ヘルスチェック
- **Discord監視**: 3階層通知（Critical/Warning/Info）・運用アラート
- **データ取得**: Bitbank API・4h/15m足・キャッシュ最適化

### **654テスト品質保証・MLOps統合CI/CD**
- **654テスト100%成功**: 全モジュール・MLOps統合テスト・エラーケース・回帰防止・統合テスト完備
- **59.24%カバレッジ**: MLOps統合テスト・品質管理完備・継続監視・新機能での向上必須
- **MLOps統合CI/CD**: ci.yml（品質・デプロイ・654テスト）・model-training.yml（週次学習・ProductionEnsemble更新）・cleanup.yml（月次クリーンアップ・Cloud Run最適化）

## 📋 トラブルシューティング

### **開発時問題**
```bash
# テスト失敗時
bash scripts/testing/checks.sh                    # 詳細エラー確認
python3 -m pytest tests/ -v                      # 個別テスト実行

# import エラー時
python3 -c "import sys; sys.path.insert(0, '.'); from src.core.logger import CryptoBotLogger"

# 設定エラー時  
python3 scripts/testing/dev_check.py validate  # 設定整合性確認
```

### **本番環境問題**
```bash
# システム稼働確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# エラーログ確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20

# Discord通知確認（運用チャンネル）
```

### **Phase 19 MLOps統合機能別デバッグ**
- **feature_manager統合**: 12特徴量統一管理・ProductionEnsemble連携・DataFrame形式確認・特徴量順序整合性確認
- **4戦略MLOps統合**: feature_manager連携シグナル生成・ProductionEnsemble統合判定・週次学習対応確認
- **ProductionEnsemble統合**: 3モデルアンサンブル読み込み・Git情報確認・MLOps予測実行確認・週次更新対応
- **MLOps統合取引**: リスク管理・Kelly基準・Cloud Runポジションサイジング・Discord監視確認
- **MLOps統合CI/CD**: model-training.yml週次自動学習・手動実行・段階的デプロイ・654テスト品質検証

## 🔄 次回作業時の確認事項

### **必須確認**
1. **品質チェック**: `bash scripts/testing/checks.sh`で625テスト・攻撃的設定確認
2. **本番稼働**: Cloud Run・Discord通知・攻撃的取引ログ確認
3. **システム状態**: FeatureGenerator→攻撃的戦略フロー→Dynamic Confidence正常動作確認

### **開発開始前**
1. **最新状況把握**: docs/開発計画/ToDo.md確認
2. **品質基準**: テスト・カバレッジ・コード品質確認
3. **設定整合性**: config整合性・環境変数確認

### **コード修正時**
1. **テスト追加**: 新機能・修正に対応するテスト追加必須
2. **品質維持**: flake8・black・isort・型注釈確認
3. **動作確認**: 実際のデータフローでの動作確認

---

**🎯 Phase 19+攻撃的設定完成・全README更新完成**: feature_manager 12特徴量統一管理・ProductionEnsemble 3モデル統合・**攻撃的戦略ロジック実装**・**Dynamic Confidence完成**・625テスト品質保証・週次自動学習・Cloud Run 24時間稼働統合・全README攻撃的設定対応更新により、**月100-200取引対応のMLOps完全統合攻撃的取引システム**・企業級品質保証・統一ドキュメント体系を実現。625テスト100%・58.64%カバレッジ・本番24時間攻撃的稼働継続・MLOps統合攻撃的基盤確立した**実用的攻撃的AI自動取引システムが稼働中** 🚀

**最終更新**: 2025年9月6日 - Phase 19+攻撃的設定完成・全README攻撃的設定対応更新完成・統一ドキュメント体系確立・MLOps統合攻撃的基盤確立