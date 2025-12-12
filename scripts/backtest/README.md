# scripts/backtest/ - バックテスト実行システム（Phase 49完了版）

**最終更新**: 2025年10月25日 - Phase 49完了・バックテスト完全改修・TradeTracker実装・matplotlib可視化システム

## 🎯 役割・責任

バックテストシステムの実行・管理を支援するディレクトリです。過去データを使用した取引システムの検証、パフォーマンス評価、戦略最適化を実現します。

**Phase 49完了成果**: バックテスト完全改修（戦略シグナル事前計算・TP/SL決済ロジック実装・TradeTrackerエントリー/エグジットペアリング・損益計算・matplotlib可視化システム・信頼性100%達成）

## 📂 ファイル構成（Phase 49完了版）

```
scripts/backtest/
├── README.md          # このファイル（Phase 49完了版）
└── run_backtest.sh    # バックテスト実行スクリプト（Phase 34実装・Phase 49移動）
```

**注**: Phase 49整理でscripts/management/から移動（バックテスト専用ツールとして分離）

## 📋 主要ファイルの役割

### **run_backtest.sh**（Phase 34実装・Phase 49整理）
バックテスト実行スクリプトで、システム動作検証と過去データ分析を実現します。
- **3モード実行**: quick（7日）・standard（30日）・full（180日）
- **Phase 35高速化**: バッチ処理・10倍高速化達成（45分実行）
- **Phase 44-49完全改修**: 戦略シグナル事前計算・TP/SL決済ロジック・TradeTracker実装
- **履歴データ収集**: Bitbank Public API・15分足データ取得（17,271件）
- **検証機能**: テスト実行・品質確認・バックテスト実行
- **レポート生成**: matplotlib可視化・統計分析・パフォーマンス評価
- **Phase 34完成**: 実用的環境確立・80倍データ収集改善
- 約7KBの簡潔な実装ファイル

### **Phase 49バックテスト完全改修の主要機能**
- **戦略シグナル事前計算**: 全5戦略のシグナルを事前に計算・ルックアヘッドバイアス防止
- **TP/SL決済ロジック**: 実取引と完全一致する決済ロジック実装
- **TradeTrackerシステム**: エントリー/エグジットペアリング・正確な損益計算・パフォーマンス指標
- **matplotlib可視化**: 4種類グラフ（エクイティカーブ・損益分布・ドローダウン・価格チャート）
- **信頼性100%達成**: ライブモードとの完全一致・SELL判定正常化

## 📝 使用方法・例

### **基本的なバックテスト実行**（Phase 49完了版）
```bash
# プロジェクトルートから実行（必須）
cd /Users/nao/Desktop/bot

# クイックバックテスト（7日間・動作確認用）
bash scripts/backtest/run_backtest.sh quick

# 標準バックテスト（30日間・通常検証用）
bash scripts/backtest/run_backtest.sh standard

# フルバックテスト（180日間・推奨・完全検証）
bash scripts/backtest/run_backtest.sh full

# カスタム期間バックテスト
bash scripts/backtest/run_backtest.sh full 90  # 90日間
```

### **実行例と出力**
```bash
$ bash scripts/backtest/run_backtest.sh full

🚀 crypto-bot バックテストシステム起動
========================================

📊 Phase 49完了: バックテスト完全改修
- 戦略シグナル事前計算: ✅ 有効
- TP/SL決済ロジック: ✅ 実装済み
- TradeTracker: ✅ エントリー/エグジットペアリング
- matplotlib可視化: ✅ 4種類グラフ生成

🔍 1. 品質チェック実行中...
✅ 1,117テスト100%成功・68.32%カバレッジ

📥 2. 履歴データ収集中...
✅ 15分足データ: 17,271件取得（180日間）

🔄 3. バックテスト実行中...
✅ 戦略シグナル事前計算完了: 5戦略
✅ バックテスト完了: 45分実行

📊 4. パフォーマンス分析...
✅ TradeTracker: 取引ペア分析完了
✅ 損益計算: 正確な実現損益・未実現損益

📈 5. 可視化レポート生成...
✅ エクイティカーブ: equity_curve.png
✅ 損益分布: profit_distribution.png
✅ ドローダウン: drawdown.png
✅ 価格チャート: price_chart.png

🎉 バックテスト完了
レポート: logs/backtest_report_20251025_HHMMSS.html
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
- **Phase 49完了**: バックテスト完全改修・TradeTracker実装・matplotlib可視化・信頼性100%達成
- **実行場所**: プロジェクトルートディレクトリから必ず実行
- **Phase 44-49改修**: 戦略シグナル事前計算・TP/SL決済ロジック・エントリー/エグジットペアリング・4種類グラフ
- **Phase 49移動**: scripts/management/から分離・バックテスト専用ツールとして独立

**推奨運用方法**:
1. **品質確認**: `bash scripts/testing/checks.sh` で1,117テスト確認
2. **バックテスト実行**: `bash scripts/backtest/run_backtest.sh full` でフル検証
3. **レポート確認**: `logs/backtest_report_*.html` で結果分析
4. **可視化確認**: 4種類グラフ（equity_curve.png・profit_distribution.png・drawdown.png・price_chart.png）で視覚的分析
