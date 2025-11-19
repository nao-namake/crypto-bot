# scripts/backtest/ - バックテスト実行システム（Phase 52.4）

**最終更新**: 2025年11月15日 - Phase 52.4コード整理・ハードコード撲滅完了

## 🎯 役割・責任

バックテストシステムの実行・管理を支援するディレクトリです。過去データを使用した取引システムの検証、パフォーマンス評価、戦略最適化を実現します。

**Phase 52.4完了成果**:
- ハードコード撲滅（全設定値をthresholds.yamlから動的取得）
- Phase参照統一（Phase 49 → Phase 52.4）
- ユーザー非依存実装（ロックファイルパス一般化）

## 📂 ファイル構成（Phase 52.4）

```
scripts/backtest/
├── README.md                      # このファイル（Phase 52.4）
├── run_backtest.sh                # バックテスト実行スクリプト（Phase 52.4整理）
└── generate_markdown_report.py    # Markdownレポート生成（Phase 52.4整理）
```

**Phase 52.4整理内容**:
- generate_markdown_report.py: ハードコード値をthresholds.yaml参照に変更
- run_backtest.sh: ロックファイルパスをユーザー非依存に変更
- 全ファイル: Phase参照をPhase 52.4に統一

## 📋 主要ファイルの役割

### **run_backtest.sh**（Phase 52.4整理）
バックテスト実行スクリプトで、ログ保存付き実行を実現します。

**機能**:
- タイムスタンプ付きログファイル自動生成
- カスタムログ名接頭辞対応（引数指定可能）
- ロックファイル自動削除（残留対策）

**Phase 52.4変更点**:
- ロックファイルパスをユーザー非依存に変更（`/tmp/crypto_bot_*.lock`）
- Phase参照をPhase 52.4に統一

**使用例**:
```bash
bash scripts/backtest/run_backtest.sh           # デフォルト: backtest_YYYYMMDD_HHMMSS.log
bash scripts/backtest/run_backtest.sh phase52.4 # カスタム: phase52.4_YYYYMMDD_HHMMSS.log
```

### **generate_markdown_report.py**（Phase 52.4整理）
バックテストJSONレポートをMarkdown形式に変換するスクリプトです。

**機能**:
- JSONレポート → Markdown変換
- Phase 51.10-B形式のレポート生成
- レジーム別パフォーマンス分析
- 自動総合評価生成

**Phase 52.4変更点**:
- ハードコードTP/SL値 → thresholds.yaml参照に変更
- ハードコードポジション制限 → thresholds.yaml参照に変更
- ハードコードMLモデル重み → thresholds.yaml参照に変更
- ハードコード信頼度閾値 → thresholds.yaml参照に変更
- デフォルトPhase: 52.1 → 52.4に変更

**使用例**:
```bash
python scripts/backtest/generate_markdown_report.py src/backtest/logs/backtest_20251115_120000.json
python scripts/backtest/generate_markdown_report.py <json_path> --phase 52.4
```

**出力先**: `docs/バックテスト記録/Phase_<phase_name>_<YYYYMMDD>.md`

## 📝 使用方法・例

### **バックテスト実行**（Phase 52.4）
```bash
# プロジェクトルートから実行（必須）
cd /Users/nao/Desktop/bot

# バックテスト実行（ログ自動保存）
bash scripts/backtest/run_backtest.sh           # デフォルト名
bash scripts/backtest/run_backtest.sh phase52.4 # カスタム名

# または直接実行（手動ログ管理）
python3 main.py --mode backtest
```

### **実行例**
```bash
$ bash scripts/backtest/run_backtest.sh phase52.4

🚀 バックテスト実行開始
📂 ログ保存先: src/backtest/logs/phase52.4_20251115_120000.log
=================================================

# バックテスト実行中...
# （ログは自動的にファイルに保存されます）

=================================================
✅ バックテスト実行完了
📁 ログファイル: src/backtest/logs/phase52.4_20251115_120000.log
```

### **Markdownレポート生成**（Phase 52.4）
```bash
# JSONレポートからMarkdownレポート生成
python scripts/backtest/generate_markdown_report.py \
  src/backtest/logs/backtest_20251115_120000.json \
  --phase 52.4

# 出力:
# ✅ Markdownレポート生成完了: docs/バックテスト記録/Phase_52.4_20251115.md
```

### **Phase 52.4設定管理の特徴**
```yaml
# thresholds.yaml から動的に設定値を取得:

risk:
  regime_based_tp_sl:
    tight_range:
      tp_ratio: 0.008  # 0.8%
      sl_ratio: 0.006  # 0.6%
    normal_range:
      tp_ratio: 0.010  # 1.0%
      sl_ratio: 0.007  # 0.7%
    trending:
      tp_ratio: 0.015  # 1.5%
      sl_ratio: 0.010  # 1.0%

trading:
  position_limits:
    tight_range: 1
    normal_range: 2
    trending: 3

ml:
  ensemble:
    model_weights:
      lgbm: 0.5  # 50%
      xgb: 0.3   # 30%
      rf: 0.2    # 20%
    min_ml_confidence: 0.45
    high_confidence_threshold: 0.60
```

**利点**:
- 設定変更が即座に反映（コード修正不要）
- Single Source of Truth実現
- 環境間での設定同期が容易

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.11（Phase 53.8）・全依存関係・機械学習ライブラリ必須
- **実行場所**: プロジェクトルートディレクトリから実行必須
- **Phase 52.4完了**: 1,153テスト・68.77%カバレッジ・品質チェック通過必須
- **設定管理**: thresholds.yaml必須（Single Source of Truth）

### **データ取得**
- **Bitbank Public API**: 15分足・4時間足データ取得
- **データ量**: 180日間データ（15分足: 17,272行、4時間足: 1,081行）
- **キャッシュ**: data/ディレクトリに保存

### **バックテスト制約**
- **過去データのみ**: ルックアヘッドバイアス完全防止
- **決済ロジック**: レジーム別動的TP/SL実装
- **設定管理**: 全設定値をthresholds.yamlから動的取得
- **レポート出力**: src/backtest/logs/ディレクトリ

### **Phase 52.4重要事項**
- **ハードコード撲滅**: 全設定値をthresholds.yaml参照に変更完了
- **3戦略システム**: ATRBased・DonchianChannel・ADXTrendStrength
- **60特徴量**: 50基本 + 3戦略シグナル + 7時間的特徴量
- **動的戦略管理**: StrategyRegistry Pattern（93%影響削減）

## 🔗 関連ファイル・依存関係

### **バックテストシステム**（Phase 52.4）
- `src/backtest/`: バックテストエンジン・データローダー・レポーター・可視化システム
- `src/core/execution/backtest_runner.py`: バックテスト実行ランナー
- `src/backtest/reporter.py`: TradeTrackerによる損益計算・パフォーマンス指標

### **設定・環境管理**（Phase 52.4 Single Source of Truth）
- `config/core/unified.yaml`: 統合設定ファイル
- `config/core/thresholds.yaml`: **動的設定値管理**（TP/SL・ポジション制限・ML設定）
- `config/core/features.yaml`: 機能トグル設定
- `config/core/strategies.yaml`: 戦略定義（3戦略）
- `config/core/feature_order.json`: 60特徴量順序定義

### **戦略システム**（Phase 52.4動的管理）
- `src/strategies/strategy_loader.py`: StrategyLoader（Registry Pattern）
- `src/strategies/base/strategy_config.py`: 戦略設定管理
- `src/strategies/implementations/`: 3戦略実装
  - `atr_based.py`: ATRBasedStrategy
  - `donchian_channel.py`: DonchianChannelStrategy
  - `adx_trend.py`: ADXTrendStrengthStrategy

### **品質保証・テスト**（Phase 52.4）
- `scripts/testing/checks.sh`: 品質チェック・1,153テスト・68.77%カバレッジ
- `tests/unit/`: 単体テスト（1,153テスト）

### **データ・ログ**
- `src/backtest/data/historical/`: 履歴データCSV（15分足・4時間足）
- `src/backtest/logs/`: バックテストログ・JSONレポート
- `docs/バックテスト記録/`: Markdownレポート（Phase別）

### **GitHub Actions統合**
- `.github/workflows/weekly_backtest.yml`: 週次バックテスト自動実行
- 依存: `scripts/backtest/run_backtest.sh`

---

## 📋 Phase 52.4履歴

**Phase 52.4完了内容**（2025-11-15）:

1. **generate_markdown_report.py**: ハードコード撲滅
   - TP/SL値 → `get_threshold("risk.regime_based_tp_sl.*")`
   - ポジション制限 → `get_threshold("trading.position_limits.*")`
   - MLモデル重み → `get_threshold("ml.ensemble.model_weights.*")`
   - 信頼度閾値 → `get_threshold("ml.ensemble.*_confidence*")`
   - デフォルトPhase: 52.1 → 52.4

2. **run_backtest.sh**: ポータビリティ向上
   - ロックファイルパス: `/tmp/crypto_bot_nao.lock` → `/tmp/crypto_bot_*.lock`
   - Phase参照: Phase 51.8 → Phase 52.4
   - コメント整理

3. **README.md**: ドキュメント最新化
   - Phase 49 → Phase 52.4統一
   - 統計更新: 1,117テスト → 1,153テスト、68.32% → 68.77%カバレッジ
   - 戦略数: 5戦略 → 3戦略
   - 特徴量: 55 → 60特徴量
   - 使用例・設定管理の特徴追加

---

**🎯 Phase 52.4重要ポイント**:
- **ハードコード撲滅完了**: 全設定値をthresholds.yamlから動的取得
- **Single Source of Truth**: 設定変更が即座に反映（コード修正不要）
- **ユーザー非依存**: ポータビリティ向上（ロックファイルパス一般化）
- **Phase参照統一**: 全ファイルPhase 52.4に更新

**推奨運用方法**:
1. **品質確認**: `bash scripts/testing/checks.sh` で1,153テスト確認
2. **バックテスト実行**: `bash scripts/backtest/run_backtest.sh phase52.4`
3. **レポート生成**: `python scripts/backtest/generate_markdown_report.py <json_path>`
4. **設定変更**: thresholds.yaml編集のみ（コード修正不要）

---

**最終更新**: 2025年11月15日 - Phase 52.4コード整理完了
