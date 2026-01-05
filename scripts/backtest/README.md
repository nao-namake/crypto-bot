# scripts/backtest/ - バックテスト実行システム（Phase 57.13完了版）

**最終更新**: 2026年1月6日 - Phase 57.13完了・固定期間バックテスト・標準分析スクリプト・CI/ローカル連携

## 🎯 役割・責任

バックテストシステムの実行・管理を支援するディレクトリです。過去データを使用した取引システムの検証、パフォーマンス評価、戦略最適化を実現します。

**Phase 57.13成果**: 固定期間バックテスト（2025/07/01〜12/31）・標準分析スクリプト（84項目固定）・CI/ローカル連携

## 📂 ファイル構成（Phase 57.13完了版）

```
scripts/backtest/
├── README.md                      # このファイル（Phase 57.13完了版）
├── run_backtest.sh                # バックテスト実行スクリプト（Phase 57.13改修）
├── generate_markdown_report.py    # Markdownレポート生成（Phase 57.11追加）
└── standard_analysis.py           # 標準分析スクリプト（Phase 57.13新規）
```

**Phase 57.13新機能**: 固定期間モード・標準分析スクリプト・CI artifact連携・ローカル結果自動保存

## 📋 主要ファイルの役割

### **run_backtest.sh**（Phase 57.11改修）
バックテスト実行スクリプトで、CI同等の機能をローカルで実現します。

**Phase 57.11 新機能**:
- **CSVデータ収集**: Bitbank APIから履歴データを自動取得
- **日数指定**: `--days N`オプションで設定ファイル編集不要
- **Markdownレポート自動生成**: バックテスト後に分析レポート生成
- **設定ファイル自動復元**: trap処理でエラー時も設定を復元

**従来機能**:
- **Phase 44-49完全改修**: 戦略シグナル事前計算・TP/SL決済ロジック・TradeTracker実装
- **履歴データ収集**: Bitbank Public API・15分足データ取得（17,271件）
- **レポート生成**: matplotlib可視化・統計分析・パフォーマンス評価

### **standard_analysis.py**（Phase 57.13新規）
標準化された分析を実行し、毎回同一の84項目で比較可能な分析レポートを生成します。

**Phase 57.13 機能**:
- **84項目の固定指標**: 基本指標・戦略別・ML別・レジーム別・時系列統計
- **CI連携**: `--from-ci`で最新のCI結果を自動取得・分析
- **ローカル連携**: `--local`で最新のローカル結果を自動検出・分析
- **履歴CSV**: 変更前後の比較が一目瞭然
- **改善提案**: 分析結果から自動的に改善案を生成

```bash
# CI結果を分析
python3 scripts/backtest/standard_analysis.py --from-ci --phase 57.13

# ローカル結果を分析
python3 scripts/backtest/standard_analysis.py --local --phase 57.13

# 特定ファイルを分析
python3 scripts/backtest/standard_analysis.py <json_path> --phase 57.13
```

**出力**:
1. コンソール: サマリーテーブル
2. JSON: `results/analysis_YYYYMMDD_HHMMSS.json`
3. Markdown: `results/analysis_YYYYMMDD_HHMMSS.md`
4. CSV: `results/analysis_history.csv`（履歴追記）

### **generate_markdown_report.py**（Phase 57.11追加）
JSONレポートをMarkdownに変換し、詳細な分析レポートを生成します。

**Phase 57.11 新機能**:
- **日毎損益分析**: 取引を日付でグループ化し損益推移を表示
- **ASCII損益曲線**: GitHub Markdownで可視化できるグラフ生成
- **月別パフォーマンス**: 月毎の取引数・勝率・損益を集計
- **信頼度帯別統計**: ML信頼度（低/中/高）別のパフォーマンス
- **戦略×レジーム クロス集計**: 戦略とレジームの組み合わせ分析

### **Phase 49バックテスト完全改修の主要機能**
- **戦略シグナル事前計算**: 全5戦略のシグナルを事前に計算・ルックアヘッドバイアス防止
- **TP/SL決済ロジック**: 実取引と完全一致する決済ロジック実装
- **TradeTrackerシステム**: エントリー/エグジットペアリング・正確な損益計算・パフォーマンス指標
- **matplotlib可視化**: 4種類グラフ（エクイティカーブ・損益分布・ドローダウン・価格チャート）
- **信頼性100%達成**: ライブモードとの完全一致・SELL判定正常化

## 📝 使用方法・例

### **Phase 57.11 新コマンド（推奨）**
```bash
# プロジェクトルートから実行（必須）
cd /Users/nao/Desktop/bot

# 基本実行（180日・CSV収集あり・Markdownレポート生成）
bash scripts/backtest/run_backtest.sh

# 日数指定（30日間テスト）
bash scripts/backtest/run_backtest.sh --days 30

# 日数指定（60日間テスト）
bash scripts/backtest/run_backtest.sh --days 60

# 既存CSVを使用（収集スキップ・高速）
bash scripts/backtest/run_backtest.sh --days 30 --skip-collect

# カスタムログ名
bash scripts/backtest/run_backtest.sh --days 60 --prefix phase57

# ヘルプ表示
bash scripts/backtest/run_backtest.sh --help
```

### **オプション一覧**
| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--days N` | バックテスト日数 | 180 |
| `--prefix NAME` | ログファイル名の接頭辞 | backtest |
| `--skip-collect` | CSVデータ収集をスキップ | false |
| `--help`, `-h` | ヘルプ表示 | - |

### **旧コマンド（互換性維持）**
```bash
# クイックバックテスト（7日間・動作確認用）
bash scripts/backtest/run_backtest.sh quick

# 標準バックテスト（30日間・通常検証用）
bash scripts/backtest/run_backtest.sh standard

# フルバックテスト（180日間・推奨・完全検証）
bash scripts/backtest/run_backtest.sh full
```

### **実行例と出力（Phase 57.11）**
```bash
$ bash scripts/backtest/run_backtest.sh --days 60

🚀 バックテスト実行開始（Phase 57.11）
📅 バックテスト期間: 60日間
📂 ログ保存先: src/backtest/logs/backtest_20260104_123456.log
=================================================

📥 Step 1: CSVデータ収集開始（60日間）...
✅ 15分足データ収集完了: 5,761行

⚙️ Step 2: バックテスト期間設定（60日間）...
✅ 設定ファイル更新完了

🔄 Step 3: バックテスト実行中...
✅ バックテスト完了

🔧 Step 4: 設定ファイル復元...
✅ 設定ファイル復元完了

📝 Step 5: Markdownレポート生成...
✅ Markdownレポート生成完了: docs/検証記録/backtest_20260104.md

=================================================
✅ バックテスト実行完了
📁 ログファイル: src/backtest/logs/backtest_20260104_123456.log
📊 バックテスト期間: 60日間
📝 レポート: docs/検証記録/backtest_20260104.md
```

### **Markdownレポートに追加されるセクション（Phase 57.11）**
```markdown
## 日毎損益分析（Phase 57.11追加）

### 損益曲線
¥ +4,000 |                              ****
¥ +3,000 |                    ****  ****
¥ +2,000 |          ****  ****
¥ +1,000 |    ****
¥      0 |----****------------------------------------
         +--------------------------------------------
           2025-07                            2025-09

### 日別サマリー
| 指標 | 値 |
|------|-----|
| 取引日数 | 45日 |
| 利益日数 | 28日 |
| 損失日数 | 17日 |
| 最良日 | 2025-08-15 (+¥1,500) |
| 最悪日 | 2025-07-20 (-¥800) |
| 平均日次損益 | ¥+90 |

### 月別パフォーマンス
| 月 | 取引数 | 勝率 | 総損益 |
|----|--------|------|--------|
| 2025-07 | 85 | 45.0% | +¥3,200 |
| 2025-08 | 92 | 48.0% | +¥800 |
```

### **Phase 49完了版の改善点**
```bash
# Phase 44-49で実装された機能:

1. 戦略シグナル事前計算（Phase 44）:
   - 全5戦略を事前計算
   - ルックアヘッドバイアス完全防止
   - df.iloc[:i+1]による過去データのみ使用

2. TP/SL決済ロジック（Phase 45）:
   - 実取引と完全一致する決済処理
   - トリガー価格による自動決済
   - 利益確定・損切り完全実装

3. TradeTrackerシステム（Phase 46）:
   - エントリー/エグジットペアリング
   - 正確な実現損益・未実現損益計算
   - 勝率・平均損益・最大ドローダウン算出

4. matplotlib可視化（Phase 47-49）:
   - エクイティカーブ: 累積損益推移
   - 損益分布: ヒストグラム分析
   - ドローダウン: 最大損失期間分析
   - 価格チャート: エントリー/エグジットマーカー

5. 信頼性100%達成（Phase 49）:
   - ライブモードとの完全一致
   - SELL判定正常化
   - 証拠金維持率80%遵守
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.8以上・全依存関係・機械学習ライブラリ必須
- **実行場所**: プロジェクトルートディレクトリ（/Users/nao/Desktop/bot）から実行必須
- **Phase 49完了**: 1,117テスト・68.32%カバレッジ・品質チェック通過必須
- **matplotlib依存**: グラフ生成にmatplotlib・Pillow必須

### **データ取得制約**
- **Bitbank Public API**: 15分足データ・日別イテレーション実装
- **レート制限**: API制限内での実行・過度な頻繁実行回避
- **データ量**: 180日間で17,271件取得（Phase 34完成）
- **実行時間**: quick 5分・standard 15分・full 45分（Phase 35高速化達成）

### **バックテスト制約**
- **過去データのみ**: ルックアヘッドバイアス完全防止（Phase 44実装）
- **決済ロジック**: TP/SL決済完全実装（Phase 45実装）
- **取引ペアリング**: TradeTrackerによる正確な損益計算（Phase 46実装）
- **可視化出力**: logs/ディレクトリにHTML・PNG保存

### **Phase 49完了時点の重要事項**
- **信頼性100%**: ライブモードとの完全一致確認済み
- **SELL判定正常化**: Phase 49完了で問題解決
- **証拠金維持率80%**: critical: 100.0 → 80.0変更適用済み
- **TP/SL設定同期**: thresholds.yaml完全準拠（Phase 42.4同期）

## 🔗 関連ファイル・依存関係

### **バックテストシステム**
- `src/backtest/engine.py`: バックテストエンジン・戦略シグナル事前計算・Phase 44実装
- `src/backtest/data_loader.py`: 履歴データ収集・Bitbank Public API統合
- `src/backtest/reporter.py`: レポート生成・TradeTracker統合・Phase 46実装
- `src/backtest/visualizer.py`: matplotlib可視化・4種類グラフ生成・Phase 47-49実装
- `src/backtest/evaluator.py`: パフォーマンス評価・統計分析
- `tests/test_backtest/`: バックテストシステムテスト

### **TradeTrackerシステム（Phase 46実装）**
- `src/backtest/trade_tracker.py`: エントリー/エグジットペアリング・損益計算
- 機能: 実現損益・未実現損益・勝率・平均損益・最大ドローダウン算出

### **設定・環境管理**
- `config/core/unified.yaml`: 統合設定ファイル・バックテスト設定
- `config/core/thresholds.yaml`: TP/SL設定（Phase 42.4同期済み）・ML統合設定
- `config/core/features.yaml`: 機能トグル設定・55特徴量Strategy-Aware ML

### **品質保証・テスト**
- `scripts/testing/checks.sh`: 品質チェック（Phase 49完了版）・1,117テスト実行
- `tests/`: 単体テスト・統合テスト・バックテストテスト

### **データ・ログ**
- `data/`: 履歴データ・キャッシュ・15分足データ（17,271件）
- `logs/`: バックテストレポート・HTML・PNG可視化・実行ログ

### **外部システム統合**
- **Bitbank Public API**: 履歴データ取得・15分足データ・レート制限対応
- **matplotlib**: グラフ生成・エクイティカーブ・損益分布・ドローダウン・価格チャート
- **Pillow**: 画像処理・グラフ保存

---

**🎯 重要**:
- **Phase 57.11完了**: CSV収集・日数指定・日毎損益分析・Markdownレポート自動生成
- **実行場所**: プロジェクトルートディレクトリから必ず実行
- **Phase 44-49改修**: 戦略シグナル事前計算・TP/SL決済ロジック・エントリー/エグジットペアリング・4種類グラフ
- **設定自動復元**: エラー時もtrap処理で設定ファイルを自動復元

**推奨運用方法**:
1. **品質確認**: `bash scripts/testing/checks.sh` でテスト確認
2. **バックテスト実行**: `bash scripts/backtest/run_backtest.sh --days 180` でフル検証
3. **短期テスト**: `bash scripts/backtest/run_backtest.sh --days 30` で素早く確認
4. **レポート確認**: `docs/検証記録/backtest_*.md` で結果分析
5. **日毎分析**: ASCII損益曲線・月別パフォーマンスで改善ポイント特定
