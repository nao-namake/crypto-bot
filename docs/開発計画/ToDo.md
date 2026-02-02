# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 62進行中** - レンジ高速回転bot改善

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 61: ¥149,195・PF 2.68・勝率75.8% |
| 手数料 | Taker統一（0.12%往復0.24%） |
| 固定TP | 500円（Phase 61で採用） |

---

## 進行中タスク

### Phase 62.8: 500円TP vs 1000円TP比較バックテスト

**目的**: Taker手数料(0.24%往復)環境で最適なTP額を決定

**背景**:
- Phase 62.7でバックテスト手数料をTaker統一
- 往復手数料0.28%増加により損益構造が変化
- 最適なTP額の再検証が必要

**手順**:
1. 現在の500円TPでバックテスト結果確認
2. 1000円TPに変更してバックテスト実行
3. 結果比較・最適値決定

**比較指標**:
| 指標 | 成功基準 |
|------|---------|
| 総損益 | 正（手数料負けしない） |
| PF | 1.5以上必須 |
| 勝率 | 60%以上 |
| 取引数 | 300件以上 |
| 最大DD | 10%以下 |

**変更ファイル**: `config/core/thresholds.yaml`
```yaml
position_management.take_profit.fixed_amount:
  target_net_profit: 500 → 1000  # 比較テスト時
```

**判断分岐**:
- 500円TPでPF >= 1.5 → 500円TP維持
- 500円TPでPF < 1.5 → 1000円TP採用検討

---

### Phase 62.9: Maker戦略実装

**目的**: 往復手数料0.28%削減（年間¥40,000+節約）

**bitbank Post-Only機能**:
- `post_only: true`で確実にMaker約定
- 即時約定時は自動キャンセル
- Maker手数料: -0.02%（リベート）

**実装内容**:

| コンポーネント | 内容 |
|--------------|------|
| Post-Only基本実装 | `post_only: true`オプション追加 |
| 価格調整リトライ | キャンセル時に1tick有利な価格で再発注（3回まで） |
| Takerフォールバック | リトライ失敗時に成行で約定 |

**実装例**:
```python
for retry in range(3):
    result = place_order(post_only=True, price=adjusted_price)
    if result.status != "CANCELED":
        break
    adjusted_price -= tick_size  # 価格調整
else:
    place_order(post_only=False)  # Takerフォールバック
```

**変更ファイル**:
- `src/trading/execution/executor.py`
- `src/data/bitbank/client.py`
- `config/core/thresholds.yaml`

**成功基準**:
- Maker約定率80%以上
- 約定遅延5分以内
- 約定漏れ率1%未満

---

## 短期計画（Phase 62.10-62.11）

### Phase 62.10: SL成行フォールバック

**目的**: 急落時の損失を50%削減

**現状の問題**:
- SLが指値のため急落時に約定しない可能性
- ビットコイン急落時にロスカットリスク

**実装内容**:
1. SL指値注文の監視機能追加
2. 一定時間（30秒）約定しない場合に成行変更
3. 緊急成行実行のログ記録

**変更ファイル**:
- `src/trading/execution/executor.py`
- `src/trading/position/tracker.py`

**成功基準**:
- 急落シナリオでのSL約定率99%以上

---

### Phase 62.11: 1年バックテスト並行実施

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

## 中期計画（Phase 62.12以降）

### Phase 62.12: WebSocket板情報導入

**目的**: スリッページ削減・約定精度向上

**実装内容**:
- bitbank WebSocket API接続
- リアルタイム板情報取得
- 最適価格での発注

**期待効果**:
- スリッページ50%削減
- 約定率向上

---

### Phase 62.13: スリッページ分析機能

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
# 標準分析（24時間）
python3 scripts/live/standard_analysis.py

# 期間指定
python3 scripts/live/standard_analysis.py --hours 48

# GCPサービス状態
gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 \
  --format="value(status.conditions[0].status)"
```

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `docs/開発履歴/Phase_62.md` | Phase 62開発記録 |
| `docs/開発履歴/Phase_61.md` | Phase 61完了記録 |
| `docs/開発履歴/SUMMARY.md` | 全Phase総括 |
| `config/core/thresholds.yaml` | 戦略閾値・TP/SL設定 |
| `CLAUDE.md` | 開発ガイド |

---

**最終更新**: 2026年2月2日 - Phase 63マルチペア対応計画追加
