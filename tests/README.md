# tests/ - テスト・品質保証システム

**Phase 13対応**: 統合テスト・品質保証・CI/CD統合（2025年8月26日現在）

## 🎯 役割・責任

テスト・品質保証システムとして以下を提供：
- **単体テスト**: 全モジュールの個別機能検証・306テスト実装済み
- **手動テスト**: 開発時コンポーネント動作確認・統合検証
- **品質保証**: 継続的品質管理・58.88%カバレッジ・CI/CD統合
- **回帰防止**: 自動テスト・品質ゲート・GitHub Actions統合

## 📂 ファイル構成

```
tests/
├── manual/              # 手動テスト・開発検証
│   ├── test_phase2_components.py    # Phase 2基盤コンポーネント検証
│   ├── manual_bitbank_client.py     # Bitbank APIマニュアルテスト
│   └── README.md                    # 手動テスト説明
├── unit/                # 単体テスト（306テスト・100%合格）
│   ├── strategies/      # 戦略システムテスト（113テスト）
│   ├── ml/              # 機械学習テスト（89テスト・8クラス・164関数）
│   ├── trading/         # 取引実行・リスク管理テスト（113テスト）
│   ├── backtest/        # バックテストエンジンテスト（84テスト）
│   ├── data/            # データ層テスト
│   ├── features/        # 特徴量システムテスト
│   ├── monitoring/      # 監視・Discord通知テスト
│   └── README.md        # 単体テスト詳細
└── README.md            # このファイル
```

## 🧪 主要機能・実装

### **manual/**: 手動テスト・開発検証
- Phase 2基盤コンポーネント検証・5種類テスト・100%合格
- BitbankClient・DataPipeline・DataCache統合テスト
- 公開API活用・認証不要・開発時動作確認

### **unit/**: 単体テスト・306テスト実装済み
- 戦略システム113テスト・ML 89テスト・取引113テスト・バックテスト84テスト
- pytest・モック・スタブ活用・包括的品質管理
- 58.88%カバレッジ・0.44秒高速実行・CI/CD統合

## 🔧 使用方法・例

### **統合テスト実行**
```bash
# 全テスト実行（306テスト）
python -m pytest tests/unit/ -v

# 手動テスト実行
python tests/manual/test_phase2_components.py

# カバレッジ付きテスト
python -m pytest tests/unit/ --cov=src --cov-report=html

# 特定モジュールテスト
python -m pytest tests/unit/strategies/ -v    # 戦略テスト
python -m pytest tests/unit/ml/ -v           # MLテスト
python -m pytest tests/unit/trading/ -v      # 取引テスト
```

### **開発時品質チェック**
```bash
# 統合品質チェック
bash scripts/testing/checks.sh

# 統合管理CLI経由
python scripts/management/dev_check.py validate
```

### **期待結果**
```
collected 306 items
tests/unit/strategies ✅ 113 passed
tests/unit/ml ✅ 89 passed  
tests/unit/trading ✅ 113 passed
tests/unit/backtest ✅ 84 passed
========================= 306 passed in 25.44s =========================
Coverage: 58.88% (target achieved)
```

## ⚠️ 注意事項・制約

### **実行環境制約**
1. **プロジェクトルート**: 必ず`/Users/nao/Desktop/bot`から実行
2. **Python環境**: pytest・pytest-cov・pytest-mock・numpy・pandas必須
3. **依存関係**: src/配下全モジュール・設定ファイル・MLモデル
4. **実行時間**: 全テスト約25秒・個別テスト数秒

### **テスト品質基準**
- **成功率**: 306テスト100%合格必須
- **カバレッジ**: 58%以上維持・正常系・異常系・境界値
- **実行速度**: 全テスト30秒以内・個別テスト2秒以内
- **保守性**: モック・スタブ活用・テストデータ管理

### **モック・スタブ戦略**
- **外部API**: BitbankAPI・Discord Webhook完全モック化
- **ファイルシステム**: 一時ディレクトリ・in-memoryファイル
- **データベース**: インメモリDB・テストデータ分離
- **時間依存**: 固定タイムスタンプ・予測可能テスト

## 🔗 関連ファイル・依存関係

### **システム統合**
- **src/**: 全モジュール・テスト対象・品質確認対象
- **scripts/testing/**: checks.sh統合品質チェック・CI/CD統合
- **scripts/management/**: dev_check.py統合管理・テスト実行統合

### **設定・環境**
- **config/**: 設定ファイル・テスト用設定・環境別設定
- **models/**: MLモデル・テスト用モデル・メタデータ
- **coverage-reports/**: カバレッジレポート・HTML・品質指標

### **外部依存**
- **pytest**: テストフレームワーク・テストランナー・アサーション・フィクスチャ
- **pytest-cov**: カバレッジ測定・レポート生成・品質指標
- **pytest-mock**: モック・スタブ・外部依存分離・テスト分離
- **GitHub Actions**: CI/CD・自動テスト・品質ゲート・継続的統合

---

**🎯 Phase 13対応完了**: 306テスト・58.88%カバレッジ・CI/CD統合により包括的な品質保証システムを実現。