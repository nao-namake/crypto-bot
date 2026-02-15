# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 64進行中**（64.1-64.2完了）

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 64.2完了: TP/SL配置信頼性の根本修正 |
| Phase 64目的 | **src/フォルダ全体のリファクタリング**（下記参照） |
| バックテスト | ¥+119,815（PF 1.65、年利24%相当） |

---

## 現在のPhase

### Phase 64: src/ 全体リファクタリング

**大目的**: `src/` フォルダ全体のコード整理・不要ファイル/コード削除・重複統合

**⚠️ 注意**: ドキュメント整理タスクではない。各サブフェーズの目的は「対象フォルダのコード品質改善」であり、新機能追加やドキュメント更新は副次的な作業に留める。

**方針**:
- 1サブフェーズにつき1フォルダを対象とする
- 各フォルダで行うこと: 不要コード削除・重複統合・責務整理・行数削減
- 各フォルダで行わないこと: 新機能追加・ロジック変更・過度な抽象化

#### サブフェーズ一覧

| Phase | 対象フォルダ | 行数 | 内容 | 状態 |
|-------|-------------|------|------|------|
| **64.1** | `src/trading/` | 10,526行 | メソッド移動・責務分離・ラッパー削除 | ✅ 完了 |
| **64.2** | `src/trading/` | — | TP/SL例外スワロー排除・リトライ正常化 | ✅ 完了 |
| **64.3** | `src/strategies/` | 6,200行 | 不要コード削除・重複統合・整理 | ⏳ 次 |
| **64.4** | `src/ml/` | 2,712行 | 不要コード削除・重複統合・整理 | ⏳ 待機 |
| **64.5** | `src/core/` | 10,237行 | 不要コード削除・重複統合・整理 | ⏳ 待機 |
| **64.6** | `src/data/` `src/features/` `src/backtest/` | 6,728行 | 不要コード削除・重複統合・整理 | ⏳ 待機 |

#### 64.1-64.2 成果（完了）

| 項目 | 値 |
|------|-----|
| executor.py | 1,943行→1,297行（-33%） |
| stop_manager.py | 2,177行→1,525行（-30%） |
| TP/SL配置 | 例外スワロー排除・リトライ正常化・ゾンビエントリ防止 |
| 純削減 | -2,111行（41ファイル変更） |

#### 64.3 作業内容（次回）

**対象**: `src/strategies/`（6,200行・16ファイル）

**やること**:
- 不要な戦略コード・無効化された戦略の削除
- strategy_utils.py（939行）の重複ロジック統合
- 各戦略ファイルの共通パターン抽出・簡素化

**やらないこと**:
- 戦略ロジックの変更（バックテスト結果に影響する変更は禁止）
- 新戦略の追加
- ドキュメントの大規模整理

#### 64.4 作業内容

**対象**: `src/ml/`（2,712行・5ファイル）

**やること**:
- 無効化されたStacking関連コードの削除
- モデルローダーの簡素化
- 不要なフォールバック分岐の整理

**やらないこと**:
- モデル構成の変更
- 予測ロジックの変更

---

## 次のPhase

### Phase 65: マルチペア対応（単一bot方式）

**前提条件**: Phase 64完了後に着手

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

## 完了タスク

<details>
<summary>Phase 63（クリックして展開）</summary>

### Phase 63-63.6: TP/SL管理改善・残存バグ修正 ✅完了

**実施日**: 2026年2月9日-13日

**Phase 63 Bug修正（6件）**:
1. stop_limit注文タイプ検出対応
2. ポジション集約時マッチング緩和（3箇所）
3. asyncio.create_task廃止→pending_verifications方式
4. stop_limitタイムアウト→SL状態確認追加
5. virtual_positions消失検知マッチング修正
6. virtual_positionsデータ整合性チェック追加

**Phase 63.2**: 固定金額TP累積手数料バグ修正（TP膨張+48%→正常化）

**Phase 63.4 Bug修正（5件）**:
1. SLタイムアウト価格安全チェック追加
2. restore_positions_from_api実ポジションベース化
3. _verify_and_rebuild_tp_sl amount修正
4. 孤児スキャンsl_placed_at追加
5. ensure_tp_sl重複防止チェック追加

**Phase 63.5**: TP/SL定期チェック実装（10分間隔）

**Phase 63.6 Bug修正（3件）**:
1. _place_missing_tp_sl get_thresholdパス修正（CRITICAL）
2. _scan_orphan_positions 設定パス修正（HIGH）
3. ensure_tp_sl restoredフィルタ削除（MEDIUM）

</details>

<details>
<summary>Phase 62（クリックして展開）</summary>

### Phase 62.1-62.21: Maker戦略・SL改善 ✅完了

**実施日**: 2026年2月1日-8日

**主要成果**:
- Maker戦略実装（往復手数料0%）
- SL逆指値指値化（stop_limit、slippage_buffer 0.2%）
- SL幅見直し（tight_range 0.4%）
- 手数料改定対応（2026/2/2: Maker 0%, Taker 0.1%）
- TP/SL欠損自動復旧

**Phase 62.1-62.8**: 戦略閾値緩和・条件型変更・手数料計算修正
**Phase 62.9-62.12**: Maker戦略実装・動作検証
**Phase 62.13**: ATRフォールバック問題修正
**Phase 62.14-62.16**: SL逆指値指値化・SL幅見直し・スリッページ分析
**Phase 62.17-62.20**: stop_limit未約定修正・手数料改定・TP/SL自動復旧
**Phase 62.21**: SL検証10分化・タイムアウトバグ修正

</details>

---

## 中期計画

### Phase 65: マルチペア対応（単一bot方式）

**前提条件**: Phase 64完了後に着手（BTC/JPYでPF 1.5以上安定）

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
| `docs/開発履歴/Phase_64.md` | Phase 64開発記録 |
| `docs/開発履歴/Phase_63.md` | Phase 63完了記録 |
| `docs/開発履歴/Phase_62.md` | Phase 62完了記録 |
| `docs/開発履歴/SUMMARY.md` | 全Phase総括 |
| `config/core/thresholds.yaml` | 戦略閾値・TP/SL・Maker戦略設定 |
| `scripts/live/standard_analysis.py` | ライブ分析（Maker戦略・スリッページ分析含む） |
| `CLAUDE.md` | 開発ガイド |

---

**最終更新**: 2026年2月15日 - Phase 64進行中（64.1-64.2完了・src/全体リファクタリング）
