# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 73-C 調査完了 — MLアーキテクチャ再設計が必要**

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 71-73: DonchianChannel無効化 / レジーム修正 / 新特徴量(CMF/CCI/WR) / バイナリ分類 / データ2倍化 |
| 根本問題 | **15分足方向予測の実力は51%（コイントス）。DOWN偏重で高信頼度もDOWN方向のみ** |
| 次のアクション | **Phase 73-D: MLをメタラベリング（取引品質フィルタ）に切替** |
| 方針 | MLの役割を「方向予測」→「取引品質判定（Go/No-Go）」に変更 |

---

## 完了Phase

### Phase 71: 緊急止血 ✅完了
- DonchianChannel無効化（勝率14%→排除）
- レジーム分類: trending優先判定（tight_range偏重修正）
- トレンドフィルタ: 強トレンド時ブロック + DI確認

### Phase 72: 戦略品質改善 ✅完了
- CMF/CCI/Williams %R 特徴量追加（低重要度3特徴量と入替）
- ATRBased戦略に出来高確認（CMF方向確認 + 低出来高ペナルティ）

### Phase 73: ML刷新 ✅完了（ただし方向予測の限界判明）
- 73-A: 学習データ2倍化（17,628→34,970サンプル、12ヶ月）
- 73-B: バイナリ分類導入（3クラス→2クラス、F1改善）
- 73-C: 多角検証で方向予測の限界を確認
  - 8パターン正則化実験: 全パターンでベースライン以下
  - クラス均衡実験: 均衡にすると精度50%
  - DOWN偏重の発見と原因特定（非対称閾値）

---

## 次のPhase

### Phase 73-D: MLメタラベリング（取引品質フィルタ）⬜ 次回着手

**目的**: MLの役割を「方向予測（51%精度）」から「取引品質判定（Go/No-Go）」に変更

**背景（Lopez de Prado メタラベリング）**:
- クオンツ業界で実績のあるアプローチ
- 戦略が方向を決定 → MLは「この局面でエントリーすべきか」を判定
- 方向予測が50%でも問題ない。局面の質を評価する方が予測可能性が高い

**実装ステップ**:

| Step | 内容 | ファイル |
|------|------|---------|
| 1 | Triple Barrierラベル生成（TP到達→成功/SL到達→失敗） | `scripts/ml/create_ml_models.py` |
| 2 | 品質特徴量追加（Signal Confluence, Volatility Percentile等） | `src/features/feature_generator.py` |
| 3 | 推論をGo/No-Go判定に変更（方向はML不介入） | `src/core/services/trading_cycle_manager.py` |
| 4 | 設定ファイルにquality_filterモード追加 | `config/core/thresholds.yaml` |
| 5 | 再学習 + 多角検証 | `scripts/ml/create_ml_models.py` |

**期待効果**:
- 予測偏り解消（DOWN偏重→均衡）
- 実戦勝率改善（25%→40-50%目標）
- 悪い取引の自動排除

**検証基準**:
- テスト精度 > ベースライン+5pt
- UP/DOWN予測偏りなし
- 過学習ギャップ < 10%
- 実戦24時間でTP/SLバランス改善

---

## 中長期計画

### Phase 74: 適応型システム

| タスク | 内容 |
|--------|------|
| 74-A | 動的TP/SL（ボラティリティ連動、RR 1.5:1維持） |
| 74-B | 自己改善フィードバック（戦略×レジーム×方向の勝率追跡・自動無効化） |
| 74-C | 適応的レジーム検出（静的閾値→ローリングパーセンタイル） |

### 保留タスク

| タスク | 保留理由 |
|--------|----------|
| BBReversal/StochasticReversal評価 | メタラベリング導入後に再評価 |
| 信頼度キャリブレーション | ProductionEnsembleにfit()なし。メタラベリング後に再検討 |
| マルチペア対応 | BTC/JPYで安定収益確立が前提 |

---

## ML実験ログ（Phase 73）

| 日付 | 実験 | 結果 | 備考 |
|------|------|------|------|
| 3/27 | 3クラス→バイナリ切替 | F1: 0.45→0.60（見かけ） | DOWN偏重が原因 |
| 3/28 | 8パターン正則化比較 | 全パターンBL以下 | 正則化では解決不能 |
| 3/28 | 5パターン閾値比較 | 均衡時51%精度 | 方向予測の実力値 |
| 3/28 | 12ヶ月データ再学習 | Gap 7.2%に改善 | テスト精度はBL-1.7pt |
| 3/29 | DOWN偏重詳細分析 | 0.65+で99.2%がDOWN予測 | 致命的偏り確認 |
| 3/29 | ライブ48h分析 | TP2/SL8、-4,066円 | sell偏重で上昇相場に対応不能 |

---

## 検証コマンド

```bash
# ライブモード分析
python3 scripts/live/standard_analysis.py
python3 scripts/live/standard_analysis.py --hours 48

# バックテスト
bash scripts/backtest/run_backtest.sh

# 品質チェック
bash scripts/testing/checks.sh

# ML再学習
python3 scripts/ml/create_ml_models.py --model both --n-classes 2 --optimize --n-trials 50 --verbose
```

---

**最終更新**: 2026年3月29日 - Phase 73-C調査完了、メタラベリングへの転換を計画
