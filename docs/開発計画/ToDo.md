# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 62.20完了** - 手数料改定対応・TP/SL欠損自動復旧

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 62.20完了: TP/SL欠損自動復旧 |
| 手数料 | エントリー/TP: Maker 0%、SL: Taker 0.1%（2026/2/2改定対応） |
| SL注文 | 逆指値指値化（stop_limit、slippage_buffer 0.2%） |
| SL幅 | tight_range 0.4% |
| 安全機能 | 5分後TP/SL検証・欠損時自動再構築 |
| バックテスト | ¥+119,815（PF 1.65、年利24%相当） |

---

## 次のPhase

### Phase 63: マルチペア対応（単一bot方式）

**前提条件**: Phase 62完了 ✅（62.20まで完了）

**対象ペア（bitbank信用取引対応）**:
- BTC/JPY（現在稼働中）
- ETH/JPY、XRP/JPY、DOGE/JPY、SOL/JPY

詳細は下記「中期計画」セクション参照。

---

## 保留タスク

### 1年バックテスト（元Phase 62.17）

**保留理由**: GitHub Actions上限6時間を超える可能性（現在6ヶ月で3時間）

**対応方針**: 必要になった時点でローカル実行 or 分割実行を検討

---

## 完了タスク（Phase 62.1-62.20）

<details>
<summary>クリックして展開</summary>

### Phase 62.17-62.20: SLパターン分析・手数料改定・TP/SL自動復旧 ✅完了

**実施日**: 2026年2月6日-7日

**Phase 62.17: stop_limit未約定バグ修正**
- Bot側SL監視スキップ（`skip_bot_monitoring: true`）
- タイムアウトフォールバック（300秒後に成行決済）

**Phase 62.18: SLパターン分析機能**
- MFE/MAE活用した改善示唆自動生成
- ライブ/バックテスト両対応

**Phase 62.19: 手数料改定対応（2026年2月2日〜）**
- Maker: -0.02% → 0%（リベート終了）
- Taker: 0.12% → 0.1%
- 全設定ファイル・コード・テスト統一更新

**Phase 62.20: TP/SL欠損自動復旧**
- Atomic Entry完了後5分後に自動検証
- 欠損検出時、tight_rangeのTP/SL幅で自動再構築
- APIエラー50062等による状態不整合を自動修復

---

### Phase 62.14-62.16: SL改善・スリッページ分析 ✅完了

**実施日**: 2026年2月5日

**Phase 62.14: SL逆指値指値化**
- `use_native_type: false` に変更（stop_limit使用）
- `slippage_buffer: 0.002` に拡大（0.2%で約定確実性確保）

**Phase 62.15: SL幅見直し**
- tight_range: `max_loss_ratio: 0.004`（0.3%→0.4%）
- weekend_ratio: 0.0025（平日比62.5%維持）

**Phase 62.16: スリッページ分析機能**
- TradeHistoryRecorderにslippage/expected_priceフィールド追加
- executor.pyでエントリー時スリッページ記録
- standard_analysis.pyにスリッページ統計レポート追加

---

### Phase 62.13: ATRフォールバック問題修正 ✅完了

**実施日**: 2026年2月5日

- executor.py: Level 0追加（atr_current直接参照）
- thresholds.yaml: `fallback_atr: 500000` → `120000`
- standard_analysis.py: ATR取得状況の検知・レポート機能追加

---

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

## 中期計画

### Phase 63: マルチペア対応（単一bot方式）

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

**手数料**: 全ペア統一（Maker 0%, Taker 0.1%）※2026年2月2日改定

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
# 標準分析（24時間）- Maker戦略・スリッページ分析含む
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

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `docs/開発履歴/Phase_62.md` | Phase 62開発記録 |
| `docs/開発履歴/Phase_61.md` | Phase 61完了記録 |
| `docs/開発履歴/SUMMARY.md` | 全Phase総括 |
| `config/core/thresholds.yaml` | 戦略閾値・TP/SL・Maker戦略設定 |
| `scripts/live/standard_analysis.py` | ライブ分析（Maker戦略・スリッページ分析含む） |
| `CLAUDE.md` | 開発ガイド |

---

**最終更新**: 2026年2月7日 - Phase 62.20完了（手数料改定対応・TP/SL欠損自動復旧）
