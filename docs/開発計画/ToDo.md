# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 62.12完了** - Maker戦略動作検証完了

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 62.12: Maker戦略動作検証完了（100%成功率） |
| 手数料 | エントリー/TP: Maker -0.02%、SL: Taker 0.12% |
| バックテスト | ライブと同一の手数料計算に統一 |
| 固定TP | 500円採用（Phase 61完了時点で決定） |
| **発見した問題** | **ATRフォールバック常時発生（要修正）** |

---

## 🚨 Phase 62 残タスク（優先度順）

### Phase 62.13: ATRフォールバック問題修正 ⚠️最優先

**発見日**: 2026年2月4日（ライブモード分析時）

**問題**: TP/SL再計算時にATR取得が常に失敗し、フォールバック値を使用

**GCPログ証跡**:
```
ATR取得元=thresholds.yaml[fallback_atr], ATR=500000円
```

| 項目 | 値 |
|------|-----|
| フォールバックATR | **500,000円**（異常に大きい） |
| 実際のATR推定値 | 約110,000円（0.9%相当） |
| 発生頻度 | **100%**（全エントリーで発生） |

**影響**:
- 現在はSL距離0.3%固定が優先されているため直接的な損失はなし
- ただし、ATRベースのTP/SL計算が機能していない

**調査項目**:
1. ATR取得が失敗する原因の特定
2. `require_tpsl_recalculation`設定の確認
3. データ取得タイミングの検証

**変更ファイル候補**:
- `src/trading/execution/stop_manager.py`（ATR取得ロジック）
- `src/features/feature_generator.py`（ATR計算）
- `config/core/thresholds.yaml`（フォールバック設定）

**成功基準**:
- GCPログで「ATR取得元=calculated」と表示される
- ATR値が100,000〜150,000円程度の妥当な値

---

### Phase 62.14: SL逆指値指値化（スリッページ対策）

**調査日**: 2026年2月4日

**問題**: SL注文が成行（`stop_loss`タイプ）のため、価格急変時に想定より不利な価格で約定

**スリッページとは**:
- 注文価格と実際の約定価格の差
- 例: SL発動価格12,000,000円 → 実約定12,050,000円（5万円のスリッページ）
- 損切り500円想定が800円になってしまう現象

---

#### bitbank API調査結果

| タイプ | 説明 | トリガー価格 | 約定方式 | UI表示 |
|--------|------|-------------|---------|--------|
| `stop` | 逆指値成行 | あり | **成行** | 「逆指値」 |
| `stop_limit` | 逆指値指値 | あり | **指値** | 「逆指値」 |
| `stop_loss` | 損切り | あり | **成行** | 「損切り」 |

**発見**: `stop_loss`タイプは成行約定。指値約定するには`stop_limit`タイプを使用する必要がある。

**既存実装**: `stop_limit`対応は**Phase 37.5で実装済み**（コード変更不要）

---

#### SL Maker対応調査結果（業界全体）

**調査日**: 2026年2月4日

**結論**: SLでMaker約定は**業界全体で実用上不可能**（bitbank固有の制限ではない）

| 取引所 | SL + Post-Only | 備考 |
|--------|---------------|------|
| **bitbank** | ❌不可 | `post_only`は`limit`のみ |
| **Binance** | ❌不可 | `post_only`は`limit`のみ |
| **Bybit** | ⚠️理論上可能 | Conditional Limit + Post-Only（実用上リスクあり） |
| **Kraken** | ❌不可 | SLは即時執行 |
| **Coinbase** | ❌不可 | SLはTaker扱い |

**根本的な矛盾**:

| 要件 | Maker（Post-Only） | SL（ストップロス） |
|------|-------------------|-------------------|
| 約定タイミング | 板に並んで待機 | **即座に約定が必要** |
| 即時約定時 | **キャンセル** | 約定しないと危険 |
| 目的 | 手数料削減 | **リスク管理（確実な決済）** |

**理由**: SLがトリガーされた時点で価格はすでにSL価格に達しているため、Post-Only注文を出すと即座にマッチ → キャンセル → **SLが機能しない**

**業界の見解**:
> "TP/SL orders can only be executed with the Allow Taker flag."
> — Kraken Support

> "The trade-off is that stop-limit orders may not fill at all during fast-moving markets, which defeats the protective purpose of a stop loss."
> — tastycrypto

**最終判断**: SLはTaker手数料（0.12%）を受け入れ、**確実な決済を優先**

| 項目 | TP | SL |
|------|-----|-----|
| Maker対応 | ✅可能 | ❌不可（業界標準） |
| 手数料 | **-0.02%** | **0.12%** |

---

#### 現状設定

```yaml
stop_loss:
  use_native_type: true     # stop_lossタイプを使用（成行約定）
  order_type: "stop_limit"  # ← use_native_type=false時のみ有効（現在未使用）
  slippage_buffer: 0.001    # 0.1%バッファ
```

---

#### 修正内容

```yaml
stop_loss:
  use_native_type: false    # stop_limit（逆指値指値）を使用
  order_type: "stop_limit"  # 指値約定
  slippage_buffer: 0.002    # 0.2%バッファ（スリッページ許容幅）
```

| 設定 | 注文タイプ | 約定方式 | UI表示 |
|------|----------|---------|--------|
| 変更前 | `stop_loss` | 成行 | 「損切り」 |
| **変更後** | `stop_limit` | **指値** | 「逆指値」 |

---

#### 変更ファイル

- `config/core/thresholds.yaml`（設定変更のみ、コード変更不要）

---

#### 期待効果

- スリッページ軽減: 成行→指値で想定損失に近い約定
- 最大損失の安定化: 損切り500円想定が800円になる問題を解消

---

#### トレードオフ

| 項目 | メリット | デメリット |
|------|---------|-----------|
| 約定方式 | 指値約定でスリッページ軽減 | - |
| UI表示 | - | 「損切り」→「逆指値」に変わる |
| 約定確実性 | - | 急変時に約定しない可能性（slippage_bufferで軽減） |

---

#### リスク軽減策

- `slippage_buffer: 0.002`（0.2%）で約定確実性を確保
- 例: SL価格12,000,000円 → 指値11,976,000円（0.2%低い価格で指値）
- これにより、0.2%以内のスリッページなら約定する

---

#### 成功基準

- SL発動時のスリッページ0.3%以下
- GCPログで`stop_limit`注文が正常に発行される

**優先度**: 中（ATRフォールバック修正後）

**実装難易度**: 低（設定変更のみ）

---

### Phase 62.15: SL幅見直し検討（要バックテスト）

**問題**: tight_rangeのSL幅0.3%が狭すぎる可能性

**現状**:
- 設定: tight_range SL 0.3%
- ATR×2.0 = 約220,000円（1.8%相当）との乖離が大きい

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

**優先度**: 低（Phase 62.13・62.14完了後）

---

### Phase 62.16: スリッページ分析機能

**目的**: スリッページの実態把握・改善点の可視化

**実装内容**:
- 発注価格 vs 約定価格の記録
- スリッページ統計レポート
- 時間帯・取引量との相関分析

**優先度**: 低（情報収集のため）

---

### Phase 62.17: 1年バックテスト並行実施

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

**優先度**: 低

---

## Phase 62 残タスク サマリー

| Phase | 内容 | 優先度 | 難易度 | 状態 |
|-------|------|--------|--------|------|
| **62.13** | **ATRフォールバック問題修正** | **🚨最優先** | 中 | 📋未着手 |
| 62.14 | SL逆指値指値化（スリッページ対策） | 中 | **低（設定のみ）** | 📋未着手 |
| 62.15 | SL幅見直し検討 | 低 | 低 | 📋未着手 |
| 62.16 | スリッページ分析機能 | 低 | 中 | 📋未着手 |
| 62.17 | 1年バックテスト | 低 | 低 | 📋未着手 |

### 調査完了状況

| Phase | 調査 | 実装方針 |
|-------|------|---------|
| 62.13 | 📋未着手 | ATR取得失敗原因の特定が必要 |
| **62.14** | **✅完了** | `use_native_type: false`に変更（設定のみ） |
| 62.15 | 📋未着手 | バックテスト検証が必要 |

---

## 完了タスク（Phase 62.1-62.12）

<details>
<summary>クリックして展開</summary>

### Phase 62.11B: バックテスト/ライブ手数料統一 ✅完了

**実施日**: 2026年2月4日

**目的**: バックテストをMaker手数料対応にし、ライブと一致させる

**変更内容**:
1. `thresholds.yaml`: バックテスト手数料をMaker対応
2. `reporter.py`: `calculate_pnl_with_fees`にexit_type引数追加
3. `backtest_runner.py`: TP/SL判定をexit_typeに変換

---

### Phase 62.11: 固定金額TP手数料計算バグ修正 ✅完了

**実施日**: 2026年2月4日

**問題**: TP純利益が300-400円程度（500円目標に未達）

**修正内容**:
1. `thresholds.yaml`: `fallback_exit_fee_rate: 0.0012`に修正
2. `strategy_utils.py`: 決済リベート減算 → 決済手数料加算に修正

---

### Phase 62.12: Maker戦略動作検証 ✅完了

**実施日**: 2026年2月4日

**調査結果**: Maker戦略100%成功率

---

### Phase 62.9-62.10: Maker戦略実装 ✅完了

**実施日**: 2026年2月3日

**効果**: 往復手数料 0.24% → -0.04%（0.28%削減）

---

### Phase 62.1-62.8 ✅完了

- 62.1: 3戦略閾値一括緩和
- 62.1-B: さらなる閾値緩和（効果なし）
- 62.2: 戦略条件型変更（RSIボーナス・BB主導）
- 62.3: BBReversal無効化（tight_range）
- 62.4: DonchianChannel重み増加
- 62.5: HOLD診断機能実装
- 62.6: 手数料考慮した実現損益計算
- 62.7: バックテスト手数料修正（Taker統一）
- 62.8: バックテスト手数料多重計算バグ修正

</details>

---

## 中期計画（Phase 62.18以降）

### Phase 62.18: WebSocket板情報導入

**目的**: スリッページ削減・約定精度向上

**実装内容**:
- bitbank WebSocket API接続
- リアルタイム板情報取得
- 最適価格での発注

**期待効果**:
- スリッページ50%削減
- 約定率向上

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

### ATRフォールバック確認

```bash
# ATR取得元の確認
gcloud logging read "textPayload:\"ATR取得元\"" --limit=10

# 期待される正常ログ
# ATR取得元=calculated, ATR=110000円
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

**最終更新**: 2026年2月4日 - Phase 62.14調査完了（SL Maker不可は業界標準・stop_limitでスリッページ対策のみ実施）
