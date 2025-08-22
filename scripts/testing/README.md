# scripts/testing/ - 統合テスト・品質チェックディレクトリ

**Phase 13完了**: quality/統合・パス修正完了・全テスト品質保証完成。テスト・品質チェック機能を統合し、開発からライブ運用まで包括的な品質保証を提供する統合ディレクトリです。

## 📁 ファイル構成

```
testing/
├── checks.sh               # 統合品質チェックスクリプト（旧quality/checks.sh）
├── test_live_trading.py    # ライブトレーディングテスト・本番前検証
└── README.md               # このファイル
```

## 🎯 ディレクトリの目的・役割

### **統合品質保証基盤**
Phase 13で確立された**306テスト100%成功・品質保証完成**環境を支える統合システム：
- 🔍 **自動品質チェック**: flake8・black・isort・pytest統合実行
- 🧪 **ライブテスト**: 本番環境での動作検証・リスク管理
- ✅ **CI/CD統合**: GitHub Actions・自動化ワークフロー対応
- 📊 **品質メトリクス**: カバレッジ・テスト成功率・コード品質指標

### **統合効果**
- **品質チェック一元化**: 分散していた品質関連機能を集約
- **テスト効率化**: 開発・CI・本番で統一されたテスト環境
- **継続的品質保証**: 自動化された品質管理・回帰防止

## 🔧 各スクリプトの使用方法

### **🔍 checks.sh - 統合品質チェック**

**目的**: プロジェクト全体の品質チェック・テスト実行・コード整形を統合実行

```bash
# 基本的な品質チェック実行
bash scripts/testing/checks.sh

# 詳細出力での実行
VERBOSE=1 bash scripts/testing/checks.sh

# 特定チェックのみ実行
SKIP_TESTS=1 bash scripts/testing/checks.sh        # テストスキップ
SKIP_FORMAT=1 bash scripts/testing/checks.sh       # フォーマットスキップ
SKIP_LINT=1 bash scripts/testing/checks.sh         # lintスキップ
```

**実行内容**:
- ✅ **pytest実行**: 306テスト・全ディレクトリ対象・カバレッジ測定
- ✅ **flake8検査**: コードスタイル・構文エラー・品質指標
- ✅ **black整形**: 自動コードフォーマット・一貫性確保
- ✅ **isort整形**: import文整理・順序統一
- ✅ **総合判定**: 全チェック成功で✅、一部失敗で⚠️、重大問題で❌

**出力例**:
```bash
🔍 Phase 13統合品質チェック開始
📊 306テスト・sklearn警告解消・品質保証完成対応

[1/4] pytest実行中...
================================ 306 passed in 25.43s ================================
✅ pytest: 306テスト全成功

[2/4] flake8検査中...
✅ flake8: 品質基準合格（0エラー）

[3/4] black整形中...
✅ black: フォーマット完了

[4/4] isort整形中...
✅ isort: import整理完了

🎉 統合品質チェック完了: すべて合格
📈 品質メトリクス: 306テスト・58.88%カバレッジ・sklearn警告解消
```

### **🧪 test_live_trading.py - ライブトレーディングテスト**

**目的**: 本番環境での実際の取引システム動作検証・リスク管理テスト

```bash
# 基本的なライブテスト実行
python scripts/testing/test_live_trading.py

# 短時間テスト（5分間）
python scripts/testing/test_live_trading.py --duration 300

# ペーパートレードモード
python scripts/testing/test_live_trading.py --mode paper

# 詳細ログ付き実行
python scripts/testing/test_live_trading.py --verbose

# カスタム設定ファイル使用
python scripts/testing/test_live_trading.py --config config/testing/live_test.yml
```

**テスト項目**:
- ✅ **API接続テスト**: Bitbank API・認証・レート制限確認
- ✅ **データ取得テスト**: OHLCV・ティッカー・リアルタイムデータ
- ✅ **戦略実行テスト**: シグナル生成・ML予測・統合判定
- ✅ **リスク管理テスト**: Kelly基準・ドローダウン・異常検知
- ✅ **注文テスト**: ペーパートレード・バリデーション・実行ログ
- ✅ **監視テスト**: Discord通知・エラーハンドリング・復旧処理

**実行結果例**:
```bash
🧪 ライブトレーディング統合テスト開始
📊 Phase 13品質保証・本番環境対応・sklearn警告解消

[1/6] API接続テスト...
  ✅ Bitbank API認証成功
  ✅ レート制限内（80%）
  ✅ 市場データ取得成功

[2/6] データパイプラインテスト...
  ✅ OHLCV取得成功（15m/1h/4h）
  ✅ 特徴量生成成功（12特徴量）
  ✅ データ品質チェック合格

[3/6] 戦略実行テスト...
  ✅ ATRBased戦略: シグナル生成成功
  ✅ ML予測: 信頼度0.67（閾値0.35クリア）
  ✅ 統合判定: BUY推奨

[4/6] リスク管理テスト...
  ✅ Kelly基準: 2.3%ポジション推奨
  ✅ ドローダウン制限: 正常範囲内
  ✅ 異常検知: スプレッド0.2%（正常）

[5/6] 注文実行テスト（ペーパートレード）...
  ✅ 注文バリデーション合格
  ✅ ポジション管理正常
  ✅ PnL計算正確

[6/6] 監視・通知テスト...
  ✅ Discord通知送信成功
  ✅ エラーハンドリング正常
  ✅ ログ出力完了

🎉 ライブテスト完了: 6/6項目合格
📊 システム健全性: 100%・本番運用準備完了
```

## 📋 利用ルール・制約事項

### **✅ 推奨される使用パターン**

#### **開発時の品質チェック**
```bash
# 開発完了時の必須チェック
bash scripts/testing/checks.sh

# コミット前の最終確認
git add . && bash scripts/testing/checks.sh && git commit -m "..."
```

#### **デプロイ前の検証**
```bash
# 本番デプロイ前の必須テスト
python scripts/testing/test_live_trading.py --mode paper --duration 600

# 段階的デプロイ時の検証
bash scripts/testing/checks.sh && python scripts/testing/test_live_trading.py
```

#### **CI/CD統合**
```yaml
# .github/workflows/ci.yml内での使用
- name: 統合品質チェック
  run: bash scripts/testing/checks.sh

- name: ライブテスト
  run: python scripts/testing/test_live_trading.py --mode paper --duration 300
```

### **⚠️ 注意事項**
1. **環境依存性**: Pythonライブラリ・GCP認証・API設定が必要
2. **実行時間**: checks.shは約30秒、ライブテストは設定に応じて数分～数時間
3. **ネットワーク**: API接続・Discord通知のためのインターネット接続必須
4. **本番影響**: test_live_trading.pyは本番環境に接続するため注意

### **🚫 禁止・非推奨事項**
1. **本番モード無許可実行**: --mode liveは十分な検証後のみ
2. **高頻度実行**: API制限・コスト考慮し適切な間隔で実行
3. **テスト結果改ざん**: 自動生成されるレポートの手動編集禁止
4. **認証情報埋め込み**: ハードコード禁止・環境変数使用

### **🔒 セキュリティ・安全性**
1. **API認証**: 環境変数・gcloud auth・OAuth使用
2. **ペーパートレード**: 実金を使わない検証環境推奨
3. **ログ管理**: 機密情報のログ出力回避・適切なマスキング
4. **エラーハンドリング**: 異常時の安全停止・アラート通知

## 🔄 他システムとの連携

### **CI/CD統合（GitHub Actions）**
```yaml
# 自動品質チェック・テスト実行
name: Quality & Live Testing
on: [push, pull_request]
jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run quality checks
        run: bash scripts/testing/checks.sh
      - name: Run live tests
        run: python scripts/testing/test_live_trading.py --mode paper --duration 300
```

### **management/との連携**
```bash
# dev_check.pyからの統合実行
python scripts/management/dev_check.py full-check  # checks.sh自動実行
python scripts/management/dev_check.py validate    # 品質チェックのみ
```

### **deployment/との連携**
```bash
# デプロイ前の自動検証
bash scripts/deployment/deploy_production.sh  # 内部でchecks.sh実行
```

### **analytics/との連携**
- テスト結果の統計分析・可視化
- 品質メトリクスの長期トレンド監視

## 📊 品質メトリクス・目標値

### **Phase 13達成指標**
- ✅ **テスト成功率**: 306/306 (100%)
- ✅ **カバレッジ**: 58.88%（Phase 13品質保証完成）
- ✅ **flake8エラー**: 0件（品質基準クリア）
- ✅ **sklearn警告**: 0件（警告解消完了）

### **継続的品質目標**
```yaml
品質基準:
  テスト成功率: ≥99%
  カバレッジ: ≥55%
  flake8エラー: =0
  実行時間: ≤60秒 (checks.sh)
  ライブテスト成功率: ≥95%
```

### **品質改善トレンド**
- **テスト数**: 438 → 316 → 306（最適化・統合完了）
- **カバレッジ**: 68.13% → 58.88%（実用的範囲で安定）
- **flake8エラー**: 1,184 → 538 → 0（54%削減→根絶）

## 🚀 今後の拡張計画

### **Phase 13+での改善予定**
- **並列テスト実行**: pytest-xdist活用・実行時間短縮
- **自動修復**: flake8・black・isortエラーの自動修正
- **性能テスト**: ベンチマーク・負荷テスト・パフォーマンス回帰検出
- **セキュリティテスト**: 脆弱性スキャン・認証テスト

### **統合テスト基盤の進化**
- **クラウドテスト**: GCP Cloud Build統合・分散実行
- **A/Bテスト**: 本番環境での段階的デプロイ検証
- **監視統合**: Grafana・Prometheus・アラート連携

### **自動化・効率化**
- **pre-commitフック**: コミット時自動品質チェック
- **自動レポート**: 品質ダッシュボード・週次レポート
- **インテリジェントテスト**: 変更影響範囲のみテスト実行

---

**Phase 13完了**: sklearn警告解消・306テスト100%成功・品質保証完成。統合テスト・品質チェック基盤による信頼性の高い開発・運用環境を実現 🚀

*継続的品質保証・自動化・統合テスト環境により、安全で効率的なAI自動取引システム開発を支援*