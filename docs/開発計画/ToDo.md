# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 67 進行中**

| 項目 | 値 |
|------|-----|
| 最新成果 | Phase 67: SL500→700円 + StochasticReversal重み削減 |
| コード修正 | ✅ 変更1-2完了 |
| バックテスト | ⏳ CI実行中 |
| 目標 | 勝率65%+、総損益¥+100,000+、PF 1.5+ |

---

## 現在のPhase

### Phase 67: SL 700円 + 勝率改善施策 🔧進行中

**目的**: SL拡大（500→700円）でPhase 65の実効SL水準に回復 + 低勝率戦略の重み削減

#### 完了タスク

| 変更 | 内容 | 状態 |
|------|------|------|
| **変更1** | 固定金額SL 500円→700円（全5箇所） | ✅ 完了 |
| **変更2** | StochasticReversal重み削減（0.30→0.10）+ ATRBased集中 | ✅ 完了 |
| **品質チェック** | 全テスト通過（1907 passed）・カバレッジ75.18%・lint全PASS | ✅ 完了 |
| **ドキュメント** | Phase_67.md新規作成・SUMMARY.md/ToDo.md/CLAUDE.md更新 | ✅ 完了 |

#### 未達成タスク

| タスク | 内容 | 状態 | 優先度 |
|--------|------|------|--------|
| **バックテスト結果確認** | CI完了後 `python3 scripts/backtest/standard_analysis.py --from-ci` | ⏳ CI実行中 | 高 |
| **バックテスト結果記録** | Phase_67.mdに結果記載 | ⬜ 待ち（結果待ち） | 高 |
| **判断** | 勝率≥65%→ライブ投入 / 58-65%→追加施策 / <58%→SL再検討 | ⬜ 待ち | 高 |
| **GCPデプロイ** | 検証成功後にCloud Runにデプロイ | ⬜ 未着手（検証後） | 中 |

#### 目標指標

| 指標 | Phase 66.8 | 目標 | Phase 65参考値 |
|------|-----------|------|---------------|
| 勝率 | 49.0% | **65%+** | 85.4% |
| 総損益 | ¥-3,804 | **¥+100,000+** | ¥+102,135 |
| PF | 0.97 | **1.5+** | 2.47 |
| 最大DD | 3.72% | **2%以下** | 0.94% |

#### 判断基準

| 勝率 | 判定 | 次のアクション |
|------|------|---------------|
| ≥ 65% | 成功 | ライブ投入検討 |
| 58-65% | 部分成功 | 追加施策（ML調整等）検討 |
| < 58% | 失敗 | SL金額再検討 or 百分率SLへの回帰 |

---

### Phase 66: ライブ取引再開 — 根本原因修正 + RR比改善 ✅完了

**成果**: 修正1-8全完了。520取引、勝率49%、¥-3,804（SL=500円が狭すぎ）→ Phase 67でSL拡大へ

### Phase 65: ライブ取引頻度回復 + TP/SLフルカバー + Maker/ML改善 ✅完了

**成果**: 三重壁対策 + 設定1ファイル化 + 包括的レビュー → ¥+102,135（PF 2.47・勝率89.2%）

---

## 完了タスク

<details>
<summary>Phase 64（クリックして展開）</summary>

### Phase 64: src/ 全体リファクタリング ✅完了

**実施日**: 2026年2月14日-21日

**大目的**: `src/` フォルダ全体のコード整理・不要ファイル/コード削除・重複統合

| Phase | 内容 | 状態 |
|-------|------|------|
| 64.1-64.4 | src/trading/ 整理・TP/SL修正・デッドコード削除 | ✅ 完了 |
| 64.5 | src/strategies/ 監査・クリーンアップ | ✅ 完了 |
| 64.6 | src/ml/ 監査（-70%削減） | ✅ 完了 |
| 64.7-64.8 | src/features/・src/data/ 監査 | ✅ 完了 |
| 64.9-64.12 | stop_limit修正・SL安全網・ログ統合 | ✅ 完了 |
| 64.13-64.21 | src/core/ 全体監査・Discord全削除・state/全削除 | ✅ 完了 |

</details>

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

</details>

---

## 次のPhase

### Phase 68: マルチペア対応（単一bot方式）

**前提条件**: ライブ取引安定後に着手（BTC/JPYでPF 1.5以上安定）

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

## 中期計画

### Phase 68: マルチペア対応（単一bot方式）

**前提条件**: ライブ取引安定後に着手（BTC/JPYでPF 1.5以上安定）

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
| トレーリングストップ | 固定TP/SL安定、過剰最適化リスク |
| トレンド型戦略強化 | trending発生率3%未満で効果限定 |
| レバレッジ1.0倍移行 | 現在0.5倍でリスク許容範囲内 |

### 条件付き再検討

| タスク | 再検討条件 |
|--------|-----------|
| 低信頼度エントリー削減 | 勝率60%未満の場合 |
| ML HOLD時エントリー抑制 | HOLD時勝率が全体を下げる場合 |
| tight_range特化 | 他レジームの勝率が著しく低い場合 |
| TP/SL金額調整 | RR分析でTP500/SL700が最適でない場合 |

---

## 検証コマンド

### バックテスト

```bash
# GitHub Actions実行
gh workflow run backtest.yml --ref main

# 実行状況確認
gh run list --workflow=backtest.yml --limit=1

# 結果確認（RR分析含む）
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
| `docs/開発履歴/Phase_67.md` | Phase 67開発記録 |
| `docs/開発履歴/Phase_66.md` | Phase 66開発記録（修正1-8） |
| `docs/開発履歴/Phase_65.md` | Phase 65開発記録 |
| `docs/開発履歴/SUMMARY.md` | 全Phase総括 |
| `config/core/thresholds.yaml` | 戦略閾値・TP/SL設定 |
| `scripts/backtest/standard_analysis.py` | バックテスト分析（RR分析含む） |
| `CLAUDE.md` | 開発ガイド |

---

**最終更新**: 2026年3月1日 - Phase 67 SL700円+StochasticReversal重み削減、バックテストCI実行中
