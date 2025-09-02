# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 🚨 最重要：現在の開発状況（2025年9月3日現在）

### **✅ システム完全稼働状態**

**現在の状況**: 
- **Phase 18完了**: 統合システム・重複コード完全排除達成
- **緊急修正完了**: FeatureGenerator問題解決・システム機能完全復旧
- **品質保証継続**: 654テスト100%通過・59.24%カバレッジ維持

**🎯 最新システム状態**:
```
🏆 システム機能: FeatureGenerator→戦略→取引フロー完全稼働
🏆 特徴量生成: 12特徴量正常生成・DataFrame返却・戦略連携正常
🏆 品質保証: 654テスト100%成功・21テストケース追加・回帰防止完備
🏆 CI/CD: GitHub Actions安定動作・30秒品質チェック・自動化完成
🏆 本番運用: Cloud Run 24時間稼働・Discord監視・自動取引継続
```

**重要**: システム機能完全復旧・品質保証継続・実用的AI自動取引システム稼働中

## 📂 システム構造（2025年9月更新版）

```
src/                    # メインシステム（654テスト100%・機能完全稼働）
├── core/              # 基盤システム
│   ├── orchestration/       # 統合制御・MLアダプター
│   │   ├── orchestrator.py      # システム統合制御（534行・Protocol分離）
│   │   ├── ml_adapter.py        # MLサービス統合（660行・フォールバック対応）
│   │   └── ml_loader.py         # MLモデル読み込み（Phase18互換性）
│   ├── config/             # 設定システム（ハードコード完全排除）
│   ├── logger.py          # JST対応ログ・構造化出力・Discord統合
│   ├── exceptions.py      # カスタム例外・階層化エラー処理
│   └── protocols.py       # Protocol分離・型安全性
│   
├── features/          # 特徴量システム（Phase18統合完成）
│   └── feature_generator.py   # 統合FeatureGenerator（12特徴量・DataFrame出力）
│   
├── strategies/        # 取引戦略（4戦略・113テスト100%）
│   ├── base/              # 戦略基盤・マネージャー
│   ├── implementations/   # 4戦略実装（ATR・もちぽよ・MTF・フィボナッチ）
│   └── utils/            # 戦略共通処理
│   
├── ml/                # 機械学習（ProductionEnsemble・89テスト）
├── data/              # データ層（Bitbank API・パイプライン・キャッシュ）
├── backtest/          # バックテスト（統一レポーター・効率化完了）
├── trading/           # 取引実行（リスク管理・Kelly基準）
└── monitoring/        # 監視（Discord通知・アラート）

scripts/testing/       # 品質保証システム
└── checks.sh         # 統合品質チェック（654テスト・30秒実行）

tests/                 # テストスイート（654テスト・59.24%カバレッジ）
├── unit/features/    # 特徴量テスト（21テストケース追加）
└── ...               # 全モジュールテスト完備

config/               # 階層化設定（YAML・環境変数統合）
models/               # MLモデル（ProductionEnsemble・学習済みモデル）
```

## 🔧 開発ワークフロー（2025年9月最新版）

### **1. 品質チェック（開発時必須）**
```bash
# メイン品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh                         # 654テスト・カバレッジ・約30秒

# 軽量システム確認
python3 scripts/management/dev_check.py validate       # 設定・整合性チェック

# 期待結果: ✅ 654テスト100%成功・59.24%カバレッジ・品質保証通過
```

### **2. システム実行**
```bash
# 本番システム実行
python3 main.py --mode paper    # ペーパートレード（安全）
python3 main.py --mode live     # ライブトレード（本番）

# 期待結果: 12特徴量生成→4戦略実行→取引判断→シグナル生成
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

### **Phase 18統合システム対応**
- **FeatureGenerator**: DataFrame返却・12特徴量・マルチタイムフレーム対応
- **importパス**: `src.core.orchestration.ml_adapter`等のPhase18後パス使用
- **後方互換性**: エイリアス機能・既存コード影響ゼロ

### **本番運用中システム**
- **24時間稼働**: Cloud Run自動スケーリング・ヘルスチェック
- **Discord監視**: 3階層通知（Critical/Warning/Info）・運用アラート
- **データ取得**: Bitbank API・4h/15m足・キャッシュ最適化

### **品質保証システム**
- **654テスト**: 全モジュール・エラーケース・統合テスト完備
- **59.24%カバレッジ**: 継続監視・新機能での向上必須
- **CI/CD**: GitHub Actions・自動品質ゲート・段階的デプロイ

## 📋 トラブルシューティング

### **開発時問題**
```bash
# テスト失敗時
bash scripts/testing/checks.sh                    # 詳細エラー確認
python3 -m pytest tests/ -v                      # 個別テスト実行

# import エラー時
python3 -c "import sys; sys.path.insert(0, '.'); from src.core.logger import CryptoBotLogger"

# 設定エラー時  
python3 scripts/management/dev_check.py validate  # 設定整合性確認
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
- **特徴量**: FeatureGeneratorの12特徴量生成・DataFrame形式確認
- **戦略**: 4戦略シグナル生成・統合判定確認
- **ML**: ProductionEnsemble読み込み・予測実行確認
- **取引**: リスク管理・Kelly基準・ポジションサイジング確認

## 🔄 次回作業時の確認事項

### **必須確認**
1. **品質チェック**: `bash scripts/testing/checks.sh`で654テスト確認
2. **本番稼働**: Cloud Run・Discord通知・取引ログ確認
3. **システム状態**: FeatureGenerator→戦略フロー正常動作確認

### **開発開始前**
1. **最新状況把握**: docs/開発計画/ToDo.md確認
2. **品質基準**: テスト・カバレッジ・コード品質確認
3. **設定整合性**: config整合性・環境変数確認

### **コード修正時**
1. **テスト追加**: 新機能・修正に対応するテスト追加必須
2. **品質維持**: flake8・black・isort・型注釈確認
3. **動作確認**: 実際のデータフローでの動作確認

---

**🎯 システム完全稼働**: FeatureGenerator問題解決完了・12特徴量→戦略フロー復旧・654テスト100%・本番24時間稼働継続により、品質保証・機能完全性・運用安定性を確保した実用的AI自動取引システムが稼働中** 🚀

**最終更新**: 2025年9月3日 - FeatureGenerator問題解決・システム機能完全復旧・品質保証継続