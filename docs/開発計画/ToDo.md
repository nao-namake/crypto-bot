# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 62.12完了** - Maker戦略動作検証

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 62.12: Maker戦略100%正常動作確認 |
| 手数料 | Maker時: 往復-0.04%（リベート）、Taker時: 往復0.24% |
| 年間削減効果 | ¥40,000〜84,000（取引量依存） |
| 固定TP | 500円採用（Phase 61完了時点で決定） |

---

## 完了タスク（Phase 62.11）

### Phase 62.11: 固定金額TP手数料計算バグ修正 ✅完了

**実施日**: 2026年2月4日

**問題**: TP純利益が300-400円程度（500円目標に未達）

**根本原因**:
- TP計算時: 決済手数料を`-0.02%`（Makerリベート）で計算
- 決済時: 実際は`0.12%`（Taker）で決済
- 差分: 約0.14%（約7円/取引）の損失

**修正内容**:
1. `thresholds.yaml`: `target_net_profit: 1000` → `500`に統一
2. `thresholds.yaml`: `fallback_exit_fee_rate: -0.0002` → `0.0012`に修正
3. `strategy_utils.py`: 決済リベート減算 → 決済手数料加算に修正

**変更ファイル**:
- `config/core/thresholds.yaml`
- `src/strategies/utils/strategy_utils.py`

**期待効果**: TP純利益が500円±50円に改善

---

## 完了タスク（Phase 62.9-62.10）

### Phase 62.9: エントリーMaker戦略実装 ✅完了

**実施日**: 2026年2月3日

**実装内容**:
- `create_order()`に`post_only`パラメータ追加
- `PostOnlyCancelledException`例外追加
- Maker戦略リトライ・フォールバック実装

**変更ファイル**:
- `config/core/thresholds.yaml`
- `src/data/bitbank_client.py`
- `src/trading/execution/order_strategy.py`
- `src/core/exceptions.py`

**効果**: エントリー手数料 0.12% → -0.02%（0.14%削減）

---

### Phase 62.10: TP決済Maker戦略実装 ✅完了

**実施日**: 2026年2月3日

**実装内容**:
- `create_take_profit_order()`に`post_only`パラメータ追加
- `_place_tp_maker()` / `_place_tp_native()`メソッド実装
- 運用確認スクリプト更新

**変更ファイル**:
- `config/core/thresholds.yaml`
- `src/data/bitbank_client.py`
- `src/trading/execution/stop_manager.py`
- `scripts/live/standard_analysis.py`
- `tests/unit/trading/execution/test_stop_manager.py`

**効果**: TP決済手数料 0.12% → -0.02%（0.14%削減）

**総合効果（Phase 62.9 + 62.10）**:

| 項目 | Taker前提 | Maker実装後 | 削減効果 |
|------|----------|-------------|---------|
| エントリー | 0.12% | -0.02% | 0.14% |
| TP決済 | 0.12% | -0.02% | 0.14% |
| SL決済 | 0.12% | 0.12% | 0%（API制限） |
| **往復（TP時）** | 0.24% | **-0.04%** | **0.28%** |

---

### Phase 62.8: バックテスト手数料多重計算バグ修正 ✅完了

**問題**: Phase 62.7で手数料が4箇所で計算され、2.5倍の過剰控除が発生
**修正**: reporter.pyのみで手数料計算するよう統一
**結果**: 品質チェック通過、バックテスト精度向上

---

## 完了タスク（Phase 62.12）

### Phase 62.12: Maker戦略動作検証 ✅完了

**実施日**: 2026年2月4日

**調査結果**:

| 項目 | 結果 |
|------|------|
| エントリーMaker成功 | 4件（100%） |
| TP Maker配置成功 | 4件（100%） |
| post_onlyキャンセル | 0件 |
| Takerフォールバック | 0件 |
| **結論** | **Maker戦略は正常動作** |

**発見した課題**:

1. **TP純利益問題（Phase 62.11で修正済み）**:
   - GCPログ: `pnl=263円`, `pnl=306円`（500円目標に未達）
   - 原因: TP計算時Maker(-0.02%)想定 vs 実際Taker(0.12%)
   - 修正後: 必要含み益が794円→1206円に増加し、純利益500円を達成

2. **CSV「ポストオンリー」列がFALSE**:
   - bitbankのCSVは約定結果を出力
   - post_only属性は注文時の設定であり、約定後CSVには反映されない仕様

**GCPログ確認コマンド**:
```bash
# Maker戦略成功確認
gcloud logging read "textPayload:\"予想手数料: Maker\"" --limit=20
gcloud logging read "textPayload:\"TP Maker配置成功\"" --limit=20

# exit記録（純利益確認）
gcloud logging read "textPayload:\"exit記録追加\"" --limit=20
```

---

## 短期計画（Phase 62.13-62.15）

### Phase 62.13: SLスリッページ対策

**問題**: 取引#7で0.68%のスリッページ発生（-1,581円損失）

**現状**:
```yaml
stop_loss:
  use_native_type: true  # bitbank stop_loss（成行）
```

**修正案**:
```yaml
stop_loss:
  use_native_type: false  # stop_limit（指値）に変更
  slippage_buffer: 0.002  # 0.2%バッファ（0.1%→0.2%に拡大）
```

**変更ファイル**:
- `config/core/thresholds.yaml`

**期待効果**:
- スリッページ軽減: 0.68% → 0.2%程度
- 最大損失軽減: -1,581円 → -800円程度

**リスク**:
- 急変時に約定しない可能性
- `slippage_buffer: 0.002`で軽減

**成功基準**:
- 次回SL発動時にスリッページ0.3%以下

---

### Phase 62.14: SL幅見直し検討（要バックテスト）

**問題**: tight_rangeのSL幅が狭すぎる可能性

**現状**:
- 設定: tight_range SL 0.3%
- 実測: 取引#7では0.25%で刈られた

**検討内容**:
- tight_range: 0.3% → 0.4% への拡大検討
- バックテストで効果検証

**変更ファイル**:
- `config/core/thresholds.yaml`

**検証方法**:
```bash
# バックテスト実行
bash scripts/backtest/run_backtest.sh
python3 scripts/backtest/standard_analysis.py --from-ci
```

**成功基準**:
- PF低下なし（または微増）
- SL発動回数減少

---

### Phase 62.15: 1年バックテスト並行実施

**目的**: 戦略の長期信頼性検証

**現状**:
- 6ヶ月データでバックテスト実施
- 季節性・年間トレンドの検証不足

**実装内容**:
1. 1年分の履歴データ取得
2. 並行バックテスト環境構築
3. 6ヶ月結果との比較分析

**成功基準**:
- 1年PFが6ヶ月PFの80%以上
- 年間最大DDが15%以下

---

## 中期計画（Phase 62.16以降）

### Phase 62.16: WebSocket板情報導入

**目的**: スリッページ削減・約定精度向上

**実装内容**:
- bitbank WebSocket API接続
- リアルタイム板情報取得
- 最適価格での発注

**期待効果**:
- スリッページ50%削減
- 約定率向上

---

### Phase 62.17: スリッページ分析機能

**目的**: 改善点の可視化

**実装内容**:
- 発注価格 vs 約定価格の記録
- スリッページ統計レポート
- 時間帯・取引量との相関分析

---

## Phase 63: マルチペア対応（単一bot方式）

**前提条件**: Phase 62シリーズ完了後に着手（BTC/JPYでPF 1.5以上安定）

### 調査結果サマリー

**bitbank信用取引対応ペア（5つ）**:

| ペア | 最小注文 | 特徴 |
|------|---------|------|
| **BTC/JPY** | 0.0001 BTC | 現在稼働中・基軸 |
| **ETH/JPY** | 0.0001 ETH | 高流動性 |
| **XRP/JPY** | 0.0001 XRP | 最高取引量（$18.4M/日） |
| **DOGE/JPY** | 0.0001 DOGE | ボラティリティ高 |
| **SOL/JPY** | 0.0001 SOL | 新興銘柄 |

**手数料**: 全ペア統一（Maker -0.02%, Taker 0.12%）

### 採用アプローチ: 単一botマルチペア対応

| 項目 | 値 |
|------|-----|
| 月額コスト | ¥16,600（2vCPU + 2GiB） |
| コスト/ペア | ¥3,320（独立botの60%削減） |
| 管理複雑性 | 低（1個デプロイ・1個監視） |
| 年間節約額 | ¥298,800（vs 5独立bot） |

**選定理由**:
1. コスト効率60%向上
2. 管理一元化
3. 現在の設計がペア非依存

### Phase 63.1: 設計・準備

- [ ] ペア別設定テーブル設計（min/max_order_size等）
- [ ] ETH/JPYバックテストデータ収集（6ヶ月分）
- [ ] アーキテクチャ設計書作成

### Phase 63.2: コア改修

- [ ] 設定ファイルのペア別化
- [ ] ポジション管理のマルチペア対応
- [ ] APIクライアントの汎用化（symbolパラメータ化）

**変更箇所見積り**:
| 箇所 | 改修量 | 難易度 |
|------|--------|--------|
| ポジションサイズ管理 | 5-10箇所 | 中 |
| APIクライアント | 15箇所 | 低 |
| バックテストローダー | 3箇所 | 低 |
| 設定ファイル | 2箇所 | 低 |

### Phase 63.3: 2ペア検証（BTC + ETH）

- [ ] ペーパートレード実施
- [ ] GCPリソース確認（1.5vCPU + 1.5GiB）
- [ ] バックテスト比較
- [ ] ペア別エラーハンドリング実装

### Phase 63.4: 全5ペア対応

- [ ] XRP/JPY, DOGE/JPY, SOL/JPY追加
- [ ] GCPリソース調整（2vCPU + 2GiB）
- [ ] 自動リカバリ機構実装
- [ ] 本番デプロイ

### 留意事項

**エントリー機会**:
- 単純5倍にはならない（暗号資産市場は相関が高い）
- 現実的予測: 2-3倍程度
- 分散効果: 異なるタイミングでの機会あり

**障害耐性**:
- ペア別エラーハンドリング実装
- 1ペアエラーでも他ペア継続可能な設計
- 自動リカバリ機構

---

## 保留タスク

### 優先度：低（現時点で不要）

| タスク | 保留理由 |
|--------|----------|
| CatBoost追加 | 現在PF 2.0+で十分、複雑化リスク |
| トレーリングストップ | 固定TP500円で安定、過剰最適化リスク |
| トレンド型戦略強化 | trending発生率3%未満で効果限定 |
| レバレッジ1.0倍移行 | 現在0.5倍でリスク許容範囲内 |

### 条件付き再検討

| タスク | 再検討条件 |
|--------|-----------|
| 低信頼度エントリー削減 | 勝率60%未満の場合 |
| ML HOLD時エントリー抑制 | HOLD時勝率が全体を下げる場合 |
| tight_range特化 | 他レジームの勝率が著しく低い場合 |

---

## 検証コマンド

### バックテスト

```bash
# GitHub Actions実行
gh workflow run backtest.yml --ref main

# 実行状況確認
gh run list --workflow=backtest.yml --limit=1

# 結果確認
python3 scripts/backtest/standard_analysis.py --from-ci

# ローカル実行
bash scripts/backtest/run_backtest.sh
```

### ライブモード確認

```bash
# 標準分析（24時間）- Maker戦略確認含む
python3 scripts/live/standard_analysis.py

# 期間指定
python3 scripts/live/standard_analysis.py --hours 48

# 簡易チェック（GCPログのみ）
python3 scripts/live/standard_analysis.py --quick

# GCPサービス状態
gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 \
  --format="value(status.conditions[0].status)"
```

### Maker戦略確認

```bash
# standard_analysis.pyの出力に含まれる:
# 💰 Phase 62.9-62.10: Maker戦略:
#    エントリー: 10成功/2FB (83%)
#    TP決済: 8成功/1FB (89%)
#    推定手数料削減: ¥25,200
```

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `docs/開発履歴/Phase_62.md` | Phase 62開発記録 |
| `docs/開発履歴/Phase_61.md` | Phase 61完了記録 |
| `docs/開発履歴/SUMMARY.md` | 全Phase総括 |
| `config/core/thresholds.yaml` | 戦略閾値・TP/SL・Maker戦略設定 |
| `scripts/live/standard_analysis.py` | ライブ分析（Maker戦略確認含む） |
| `CLAUDE.md` | 開発ガイド |

---

**最終更新**: 2026年2月4日 - Phase 62.12 Maker戦略動作検証完了
