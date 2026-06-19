# Crypto-Bot

bitbank信用取引・BTC/JPY専用のAI自動取引システム（GCP Cloud Run 24時間稼働）

[![Tests](https://img.shields.io/badge/tests-2400%2B%20passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-73%25%2B-green)](tests/)
[![Phase 87](https://img.shields.io/badge/Phase%2087-Complete-success)](docs/開発履歴/Phase_87.md)
[![Phase 88](https://img.shields.io/badge/Phase%2088-Complete-success)](docs/開発履歴/Phase_88.md)
[![Phase 89](https://img.shields.io/badge/Phase%2089-Complete%20%26%20Deployed-success)](docs/開発履歴/Phase_89.md)
[![Phase 90](https://img.shields.io/badge/Phase%2090ε-Implemented-success)](docs/開発履歴/Phase_90.md)

---

## 現在の状態

**Phase 90ρ TP引き下げ(1200/1000→800) + ライブ分析ノイズ整理 デプロイ済み（2026-06-19・commit `dd033192`・リビジョン `0619-0955`・CI/CD成功）**。ライブ分析を起点に3件を実施。**①R1実証 + ノイズ整理**: 24h分析で `reconcile[LIVE]` 稼働を実証（SL配置3/成行決済2）。invariant の「致命的:1」は scale-to-zero由来の **VP↔実ポジ乖離が R1 reconcile と二重に鳴るノイズ**（reconcileは実建玉基準でSL是正済み＝実害なし）と判明→`standard_analysis.py` の `_check_phase90o_invariants` を**種別分類**（建玉合計超過=CRITICAL維持／VP乖離=reconcile[LIVE]稼働中ならWARNING降格）+reconcile実働可視化に改修し **致命的1→0・🟢正常**（テスト7件・分析スクリプトのみ・取引挙動不変）。**②TP引き下げ検証（ユーザー仮説「TPを下げるとTP約定しやすくなりSL率が下がる」）**: 90日216件シミュ+30日BTで検証→SL固定でTP段階比較し **TP800/SL2000が期待値ピーク(+46円/件)**（TP600は下げすぎ・SL1500系は劣りSL2000維持＝Phase 90ν整合）。`thresholds.yaml` の confidence_based TP **1200/1000→800** に実装。30日BT: **損益+4,252→+5,832(+37%)・勝率61.1→70.7%・DD-650・PF1.134→1.078**（微減だが黒字維持＝薄利多勝化）。**③派生発見＝サイズとTP/SLの信頼度不整合（Stage 2）**: サイズは `ml_confidence`（6/18事象A 0.657→0.02）・TP/SLは `adjusted_confidence`（<0.4→低）を見ており「失敗確信が高いのに大サイズ0.02」が発生→`manager.py` で `strategy_confidence<0.40` なら `ml_confidence` 高でもサイズを `fixed_table.low` にクランプ（`position_sizing.confidence_alignment.enabled` トグル）。クランプ実装も**BT検証で不採用(revert済み)**: 固定金額TP/SLでは「TP距離=TP金額÷サイズ」ゆえサイズ↓＝距離↑で、クランプ(0.015→0.010・310回発動)がTP800の約定改善を相殺し30日BT +5,832→+160悪化(PF0.959)→コード/設定/テスト削除（不整合自体は実在も別アプローチが将来課題）。なお24hの2件SL(-4,352円)は**エントリー判断/TP-SL距離は正常**・stop注文が canceled_unfilled→reconcile成行決済がカバー。**TP800デプロイ済み（commit `dd033192`・リビジョン `0619-0955`・2026-06-19 18:55 JST）**。

**直前の Phase 90π TP/SL管理の Reconciliation Loop 全面再設計 R1（実発注 + 微小端数clean-up）移行（2026-06-18・commit `ce5d1b28`）**。Reconciliation Loop（新規 `src/trading/reconciliation/` 7モジュール・**実建玉(fetch_margin_positions)を唯一の真実源**とし毎サイクル desired↔actual の差分を冪等に埋める・裸ポジを invariant で根治）を **R0（shadow）→ R1（実発注）** へ移行した。R0 shadow で本番の reconcile 動作を確証（**裸ポジ検知・no-op正常・誤MARKET_CLOSE提案0**）。ただし R0 観察中に **0.0018 BTC short の裸ポジ事象**が発生：標準0.015でなく微小端数0.0018が残り、固定金額SL(2000円)÷微小amountで**SL距離が約10%(11,627,135円)に破綻**→SL設置が失敗しループ。**手動で成行決済しフラット化**して対処した。これを受け**微小端数 clean-up を追加**：`desired.py` で固定SL距離が floor(0.7%) の5倍を超えるサイズを `is_micro` 判定／`diff.py` で `is_micro`→`MARKET_CLOSE`（SL設置でなく成行で残さない）／設定 `position_management.reconciliation.micro_sl_multiple=5.0`。**R1**=`reconciliation.shadow_mode=false` で **reconcile が実際に裸ポジを是正**（SL欠損→実SL設置 / 価格割れ・微小端数→成行決済）。**Phase 87 C1 `dry_run` は維持**（解除しない）：reconcile が MARKET_CLOSE を担うため解除すると二重決済になる・reconcile が trigger 冒頭で先に是正→建玉消滅→C1 は無害。テスト57件（micro判定・micro→MARKET_CLOSE・0.0018回帰を追加）・`checks.sh`全PASS。**効果と限界（正直に）**: 「今日のような長時間SL未設置」は起きなくなる（5分ごと実是正＋micro clean-up）。ただし「一瞬も裸にしない」ではない（5分サイクルの隙間）。**実建玉での実証はこれから（現在フラット）**。**残り**: R2（エントリーTP/SLを desired.py 共有に統合）→ R3（旧コード削除）。**派生課題（未対応）**: ログPnL（Phase 61.9）が実口座損益と乖離（成行スリッページ+往復手数料+金利を建値ベース概算が未計上）→ライブ分析の損益をbitbank実口座基準にすべき。plan: `~/.claude/plans/tpsl-bitbank-lexical-quail.md`。**直前の Phase 90ν ライブ分析の解釈改善 + SL引き下げ余地の調査 デプロイ完了（2026-06-06・リビジョン `0605-2226`）**。GCPログ精査でライブ分析の警告2件を改善した（**誤発火をreason別分類**＝`canceled_unfilled`設計どおり昇格と `fetch_error_persistent`真の誤発火を分離・真の誤発火のみ警告 / **drift判定をretrain_triggeredベース化**＝検出多数でも再学習0回なら「strategy_signal主体の想定内変動・実害なし」と正常扱い）。テスト9件・`checks.sh`全PASS・**分析スクリプトのみで取引挙動不変**。**SL引き下げ調査**: `full_entry_simulation` で SL2000→1750/1500 の引下余地を90日277件検証→SL距離が縮むとTP取引がSL転落し期待値悪化（90日 TP1200: -198→-270円）→**SL2000維持・下げる余地なし**（**6月1ヶ月様子見で7月初に再判断**）。**直前の Phase 90μ SLMonitor誤発火の真因修正 デプロイ済み（6/5 06:43 JST・リビジョン `0604-2142`→現 `0605-2226` に内包・デプロイ後 Fire #2 誤発火0確認）**: 6/5 ライブ分析で `SLMonitor DRY_RUN誤発火:2回` を検出し、GCPログ精査（06/04 19:30-20:30 UTC）で**誤発火2回は別々の2メカニズム**と確定。**Fire #1**（reason=`canceled_unfilled`・90θ 3/3）は15分stuckのSLを正しく昇格し同サイクルで Phase 64.12 も実決済＝**設計どおり（誤発火ではない・現状維持）**。**Fire #2**（reason=`fetch_error_persistent`）が**クリーンな誤発火**で2バグの複合: ①`stop_manager._check_tp_sl_execution` が合成ID `market_close_*`（Phase 64.12 成行決済済み）に `fetch_order` して例外を握り潰し**幽霊VPが除去されず**毎サイクル C5/C7 の対象に、②`sl_monitor.check_sl_health` の C7 昇格パスが他の昇格（canceled_unfilled/expired/timeout）と違い `_position_already_closed` 残量ガードを通さず実0でも3サイクルで無条件発火。修正: **Fix 1** `market_close_*` を `fetch_order` せず `stop_loss` 確定で幽霊VP即除去（根本）／**Fix 2** C7 昇格前に残量ガードを対称適用し実0なら抑止（防御）。`dry_run:true` は変更なし（本番で誤発火0を確認後に別タスクで解除判断）。テスト4件追加・`checks.sh` 全 PASS。**非バグと確定**: trending ADXエントリー（実態 normal_range・重み0.15）／torch FULL（本番 `ProductionEnsemble_FULL` 稼働・ローカル限定）／Maker リトライ0%（全試行1で約定）。**直前の Phase 90κ Maker約定率の改善 は本番デプロイ済（2026-06-03 06:34 JST・リビジョン`0602-2134`／headSha`1c2918de`）→ 本番稼働中**

| 項目 | 値 |
|------|-----|
| 🟢 Phase 90ρ TP引下(1200/1000→800) + ライブ分析ノイズ整理 デプロイ済み（2026-06-19・リビジョン `0619-0955`）| ライブ分析起点で3件。**①R1実証+ノイズ整理**: `reconcile[LIVE]` 稼働を実証(SL配置3/成行決済2)・invariant「致命的:1」は scale-to-zero由来のVP↔実ポジ乖離が reconcile と二重に鳴るノイズと判明→`standard_analysis.py` を種別分類(建玉合計超過=CRITICAL維持／VP乖離=reconcile稼働中はWARNING降格)+reconcile可視化に改修・**致命的1→0・🟢正常**(テスト7・分析のみ)。**②TP引き下げ検証(ユーザー仮説「TP下げ→TP約定↑→SL率↓」)**: 90日216件シミュ+30日BTで実証→**TP800/SL2000が期待値ピーク(+46円/件)**・TP1200/1000→800実装・30日BTで**損益+37%(+4,252→+5,832)/勝率61.1→70.7%/DD-650/PF1.134→1.078**(微減だが黒字維持)。**③Stage2 信頼度整合**: サイズ(`ml_confidence`)とTP/SL(`adjusted_confidence`)の不整合(6/18事象A 0.02 long「失敗確信高で大サイズ」)→クランプ実装も**BT検証で不採用(revert)**: 固定金額方式ではサイズ↓＝距離↑がTP800と相反し30日BT +5,832→+160悪化と判明しコード削除。**TP800のみデプロイ済み(commit `dd033192`/`0619-0955`)** |
| 🟢 Phase 90π Reconciliation Loop R1 実発注 + 微小端数clean-up（2026-06-18）| Reconciliation Loop（新規 `src/trading/reconciliation/` 7モジュール・**実建玉(fetch_margin_positions)を唯一の真実源**・毎サイクル desired↔actual 差分を冪等に埋める・裸ポジを invariant で根治）を **R0（shadow）→ R1（実発注）** へ移行。R0 shadow で reconcile 動作を本番確証（裸ポジ検知・no-op正常・**誤MARKET_CLOSE提案0**）。観察中の**0.0018 BTC short 裸ポジ事象**（微小端数で固定SL2000円÷微小amount→SL距離が約10%(11,627,135円)に破綻→SL設置失敗ループ・**手動成行決済で対処**）を受け**微小端数 clean-up を追加**（`desired.py`で固定SL距離が floor(0.7%) の5倍超を `is_micro` 判定／`diff.py`で `is_micro`→`MARKET_CLOSE`／設定 `micro_sl_multiple=5.0`）。**R1**=`shadow_mode=false` で **reconcile が実際に裸ポジを是正**（SL欠損→実SL設置 / 価格割れ・微小端数→成行決済）。**Phase 87 C1 `dry_run` は維持**（reconcile が MARKET_CLOSE を担うため解除すると二重決済・reconcile が trigger 冒頭で先に是正→C1 無害）。テスト57件・checks.sh全PASS。効果＝長時間SL未設置は起きなくなる（5分ごと実是正＋micro clean-up）が「一瞬も裸にしない」ではない（5分サイクルの隙間）・**実建玉での実証はこれから（現在フラット）**。残りR2(エントリーTP/SL統合)→R3(旧コード削除)。派生課題=ログPnLが実口座損益と乖離（手数料・金利・スリッページ未計上）→分析を実口座基準にすべき |
| 🟢 Phase 90ο 根源治療（2026-06-15）| 6/15の「コツコツドカン」(-3,277円)の**根源治療**。原因＝VP(揮発メモリ)と実ポジの**二重管理** + 再起動で空VPが同方向上限をすり抜け→重複ショート0.0325 BTC膨張→一括SLドカン。対症療法でなく**体質改善（実ポジを唯一の正・VPはキャッシュ降格）**を3段デプロイ：**Stage 0**=gating層に建玉合計サイズ上限`max_total_position_btc=0.02`（VP非依存の最終防衛線）+取得失敗時monitor_only（安全優先）／**Stage 1**=`check_limits`を実ポジ(fetch_margin_positions)基準化（取得失敗=エントリー拒否・daily回数のみVP継続）／**Stage 3**=`tp_sl_manager`が毎サイクル「建玉合計>上限/両建て/VP↔実ポジ乖離(3連続)」を検知しCRITICAL+ライブ分析で可視化。テスト計20件追加・checks.sh全PASS・**取引挙動は正常時(1ポジ≤0.02)不変**。別タスク=Stage 2（サイズ信頼度一元化・収益性影響でBT検証後）|
| 🟢 Phase 90ξ ライブ分析の誤検知修正（2026-06-15）| ライブ分析でBot機能診断の「致命的:1」を検出→GCPログ精査で**本番 LOG_LEVEL=WARNING 下の誤検知3件**と確定し修正（`scripts/live/standard_analysis.py`・**分析スクリプトのみ・取引挙動不変**）。①`_check_ml_prediction`がINFOログ(`ProductionEnsemble`/`ML予測`)を見て常に偽CRITICAL→WARNINGの`フル取引サイクル開始`/`固定金額TP適用`を生存シグナル併用 ②`_detect_silent_failure`のsignal/order(INFO)が常に0→`フル取引サイクル開始`/`TP Maker配置成功`併用＋拒否系を`cycle_resolved_count`集計 ③success_rate判定が`--limit=30`頭打ち＋正当拒否大半で偽CRITICAL→実行率段階判定を撤廃。テスト9件追加・checks.sh全PASS。実機--quickで**致命的1→0・正常13→16・判定🟠→🟡**。二次所見=Phase 90αラベル分布チェックが常時NO_DATA（別タスク候補）|
| 🎯 Phase 90ν 解釈改善 + SL調査 | GCPログ精査でライブ分析の警告2件を改善（**誤発火reason別分類**: canceled_unfilled設計どおり昇格 vs fetch_error_persistent真の誤発火 / **drift retrainベース判定**: 検出多数でも再学習0なら正常扱い・「Bonferroni補正薄い」廃止）。+ `full_entry_simulation` でSL引き下げ余地を90日277件検証→SL2000→1750/1500は期待値悪化（TP1200: -198→-270→-219円）でTP取引がSL転落→**SL2000維持・下げる余地なし**。**2026年6月の1ヶ月間様子見で7月初に再判断**。テスト9件・checks.sh全PASS・取引挙動不変 |
| 🎯 Phase 90ζ 観察可能化+整合 | Phase 90ε デプロイ後のライブ分析で①SL土日縮小が本番ログで見えない（SL適用ログが INFO で WARNING抑制）→ `strategy_utils.py` の SL適用ログを INFO→WARNING 昇格（TP昇格と対称・`(土日縮小→N円)` ラベル付きで検証可能化）、②特徴量数37/55の不整合（README図・checks.sh ログが旧37）→ 55に統一。テスト1件追加・取引挙動は不変 |
| 🎯 Phase 90ε 土日TP/SL縮小 | ユーザー指摘「日本の土日祝はBTCが狭いレンジに収まりやすく、TP1000-1200円では約定しないまま月曜を迎える」を起点に実装。実運用の confidence_based（固定金額）経路に **JST土日判定**（`weekday()>=5`・Phase 83C のJST明示変換踏襲）を追加し、**土日は信頼度に関係なくTPを一律500円**（距離≒0.36%でレンジ内利確優先）に上書き。SLは target1000円へ下げるが **floor 0.7% 据え置き（A案）** のため実効SL≒0.70%（≒1,733円@0.015BTC・平日2000円より縮小しつつノイズ耐性維持）。祝日は対象外（jpholiday 不採用・追加依存ゼロ）。変更3ファイル・テスト6件追加・black/isort/flake8 PASS・実config E2E確認済 |
| 最新成果（Phase 90δ）| ライブ分析調査で **Maker 戦略の致命バグを発見・修正（Phase 90δ）**：`bitbank_client.py:840` が `postOnly`（camelCase）を送信していたが bitbank は `post_only`（snake_case）を期待し、ccxt 4.5.1 は変換しないため **post_only が全注文で無視され通常指値化＝即時約定時テイカー約定**していた。旧「Maker 化率 100%」は約定種別を実 API で検証しない虚偽記録。post_only 名前修正 + 約定種別の真実観測 + 緊急決済 DRY_RUN 誤カウント修正 + 50062 レース対策の 4 件を実装、18 テスト追加・`checks.sh` 全 PASS |
| 🎯 Phase 90δ 追加調整 | (1) **レジーム別TP/SL が未適用（dead code）と判明**：`confidence_based` が `regime_based` を常に上書き（5/29 実証: TP適用99回全て信頼度別・normal TP500 は0回）。実態は全エントリーが信頼度別 → ドキュメント訂正。(2) **TP 引き下げ**：TP1500（距離0.956%）が遠く +1000円付近で反転→SL のケース多発のため、高 TP1500→1200 / 低 TP1200→1000 に引き下げ（SL維持・RR 0.83:1 許容）|
| 🎯 Phase 90γ-⑦+⑨ 統合実装内容 | ⑦-1 INFO→WARNING 格上げ 3 箇所 / ⑦-2 例外スワロー解消 3 箇所（trigger_server pragma 解除含む）/ ⑦-3 サイレント失敗ログ 3 箇所（DummyModel fallback・ml_confidence=None・drift skip）/ ⑦-4 persistence=None CRITICAL 警告 / ⑨ 25 件テスト追加（test_backtest_runner.py 新規 8 + _load_state 5 + Drift KS 異常入力系 6 + test_trigger_server.py 新規 6 + 補強 2）+ 副次バグ修正 1 件（時刻ハードコード）|
| 🎯 Phase 90γ-⑥ Day 1 検証結果（5/29 朝・完全成功）| bitbank API 実取引 + WARNING ログで TP 距離 **0.956%**（目標 0.7-0.9% 達成）・実効 RR **~1.02:1**（旧 0.25:1 から **4 倍改善**）・~~Maker 化率 100%~~（⚠️ **Phase 90δ で虚偽判明**：post_only 未機能で約定種別未検証だったため実態はテイカー約定）・信頼度ラベル付き TP 配置ログ **64/65 試行で機能**（旧バグ時 0%）。実取引件数は trending 相場継続で 24h 1 件のみだが、修正①の confidence_based 機能性は完全証明 |
| 🎯 同時エントリー仕様確認 | Phase 50.4 維持率予測拒否 48 件/24h は**バグではなく仕様通り**。証拠金 24 万円 / 1 エントリー 0.015 BTC ≒ 17 万円消費で維持率 130% → 追加エントリーで 76% へ落ちる予測 = 強制ロスカット 50% への 30pt 安全バッファ |
| 🎯 Phase 90γ-⑥ 根本発見（履歴）| `tp_sl_manager.py:2221` の `getattr(evaluation, "confidence", None)` が `TradeEvaluation` の実フィールド名（`confidence_level` / `adjusted_confidence`）と不一致 → Phase 68.8（2026-03-13）以降 **約 2.5 ヶ月間 confidence_based 上書きが全エントリーでスキップ**。修正により全レジームで信頼度ベース TP=1500/SL=2000 に統一 |
| 🎯 Phase 90γ-①〜⑤（履歴）| Drift 検出再設計 / trigger EMERGENCY_STOP 解消 / 取引拒否 91% 解消 / Maker fallback 段階改善 / 観察可能化 / Phase 79 仕様誤読訂正 / 50062 連発対策（詳細は `docs/開発履歴/Phase_90.md`）|
| 🎯 Phase 90α/β 根本発見（履歴）| 90α: メタラベリング有効化（`--meta-label` 追加 6 行）で macro F1 0.347 → 0.546・90β: 本番運用リスク 7 件根本修正 |
| v8e (新) macro F1 | LGB CV **0.546** / Test 0.486・RF CV 0.530・N-BEATS CV 0.514 Test 0.524・XGB CV 0.459 |
| v8e クラス分布 | success 30.8% / failure 69.2%（Triple Barrier 理想分布）|
| 特徴量数 | 37 → **55**（+18・6 カテゴリ追加）|
| ML モデル | 3 → **4**（N-BEATS 追加・重み 0.34/0.34/0.17/0.15） |
| Phase 90γ-⑦+⑨ 修正規模 | 8 ファイル変更（コード 4 + テスト新規 2 + テスト拡張 2）/ **+577 / -15 行・25 件テスト追加 / 全 PASS（カバレッジ 72%+）** |
| 過去 7 日損益（5/21-5/28）| 取引 15 ペア / 勝率 **66.7%** (10勝5敗) / 総 NET **¥-3,056** / **PF 0.496** / 平均勝利 ¥300 vs 平均損失 ¥1,212 (RR 0.25:1) / **月利 -2.6% / 年利 -31%**（目標 +10%/年 から -41pt 未達）→ **Phase 90γ-⑥ Day 1 で機能性確認済**・Day 7（6/4 頃）に PF > 1.2 / 月利 > 0% への改善見込み |
| 外部ソース検証 | bitbank + Binance + 業界標準 ADX で Bot のレジーム判定が **一致**（直近 24h で trending 60-66%）。「取引ない=trending 相場」は妥当。TP/SL 距離は ATR×6 と業界標準（×1.5-2.0）より広いが Phase 85 実証で意図的設定 |
| 次の予定 | **5/30 朝に Phase 90γ-⑦ Day 1 観察可能化検証**: 新規 WARNING 5 種以上が可視化されているか + Phase 90γ-⑥ Day 2 累積効果。健全なら **Phase 90γ-④（ML 改善）着手判断**（バックテスト経路統合 90γ-⑧ は優先度低でスキップ候補）|
| 詳細計画 | [docs/開発計画/ToDo.md](docs/開発計画/ToDo.md) / [docs/開発履歴/Phase_90.md](docs/開発履歴/Phase_90.md) / `~/.claude/plans/humming-prancing-lamport.md`（Phase 90γ-⑦+⑨ 統合プラン）|
| 最終更新 | 2026年6月18日 - Phase 90π TP/SL管理の Reconciliation Loop 全面再設計 R1（実発注 + 微小端数clean-up）移行（`shadow_mode=false`・0.0018 BTC 裸ポジ事象→micro clean-up追加・テスト57件・checks.sh全PASS） |

---

## クイックスタート

### ローカル実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境設定
cp config/secrets/.env.example config/secrets/.env
# → .envにbitbank API設定

# 品質チェック
bash scripts/testing/checks.sh  # 全テスト成功・75%+カバレッジ

# ペーパートレード
bash scripts/paper/run_paper.sh

# ライブトレード
python3 main.py --mode live
```

### GCP確認

```bash
# 稼働状況
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 --format="value(status.conditions[0].status,status.url)"

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# ライブ分析（24時間）
python3 scripts/live/standard_analysis.py --hours 24
```

---

## システム概要

**6 つの取引戦略**と**機械学習（4 モデルアンサンブル）**を統合し、**55 特徴量**を総合分析することで 24 時間自動取引を実現。**メタラベリング**（取引品質の Go/No-Go 判定・Phase 90α）と**レジーム別動的戦略選択**により、市場状況に適応した取引を行います。

| 項目 | 値 |
|------|-----|
| **対象市場** | bitbank信用取引・BTC/JPY専用 |
| **証拠金** | 50万円 |
| **年利目標** | 10%（Phase 88まで） / **15-18%（Phase 91完了後）** |
| **取引頻度** | 5分間隔実行 |
| **稼働体制** | 24時間・GCP Cloud Run |
| **月額コスト** | 現状約3,000円 / **Phase 88 I3 完了後 300-500円目標** |

---

## 6戦略構成（Phase 85 trending全停止）

| 区分 | 戦略名 | 核心ロジック |
|------|--------|-------------|
| **レンジ型** | BBReversal | BB位置主導 + RSIボーナス → 平均回帰 |
| **レンジ型** | StochasticDivergence | 価格とStochasticの乖離検出 → 反転 |
| **レンジ型** | ATRBased | ATR消尽率70%以上 → 反転期待（主力） |
| **レンジ型** | CMFReversal | CMF売り圧力減少→BUY / 買い圧力減少→SELL |
| **トレンド型** | MACDEMACrossover | MACDクロス + EMAトレンド確認 |
| **トレンド型** | ADXTrendStrength | ADX≥22 + DIクロス → トレンドフォロー |

### レジーム別重みづけ

| 戦略 | tight_range | normal_range | trending |
|------|-------------|--------------|----------|
| ATRBased | 0.35 | 0.25 | **0.0** |
| CMFReversal | 0.20 | 0.15 | **0.0** |
| BBReversal | 0.20 | 0.15 | **0.0** |
| StochasticReversal | 0.10 | 0.15 | **0.0** |
| ADXTrendStrength | 0.10 | 0.15 | **0.0** |
| MACDEMACrossover | 0.05 | 0.15 | **0.0** |

**Phase 85 trending全停止根拠**: 過去30日 trending 23件で全シナリオ赤字。「レンジ専用bot」設計と完全合致。

---

## システムアーキテクチャ

```
レイヤードアーキテクチャ設計
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Data Layer     │───▶│ Feature Layer   │───▶│ Strategy Layer  │
│  (Bitbank API)  │    │ (55 Features)   │    │ (6 Strategies)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ML Layer       │───▶│ Risk Layer      │───▶│ExecutionService │
│ (3 Model Ens.)  │    │ (Kelly Crit.)   │    │(BitbankClient)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### ディレクトリ構成

```
src/
├── core/           # 基盤システム（設定・実行制御・レポート）
├── data/           # データ層（Bitbank API・キャッシュ）
├── features/       # 特徴量生成（55特徴量・Phase 89-β/γ/δ で 37→55 拡張）
├── strategies/     # 6戦略（Registry Pattern）
├── ml/             # ML統合（3モデルアンサンブル）
├── trading/        # 取引管理層（5層アーキテクチャ）
└── backtest/       # バックテストシステム

tax/                # 確定申告システム
scripts/            # 運用スクリプト
config/core/        # 設定ファイル群
models/production/  # MLモデル（週次更新）
```

---

## Phase 87/88 計画概要

9エージェント並列調査で **全28欠陥** を確定。決済システム再構築 + 運用基盤強化 + GCPコスト削減を統合実施。

### Phase 87 全 Stage ✅ 完了（2026-05-14 本番デプロイ済）

Critical 5 + High 10 を全完了。SL消失インシデント（2026-05-12）を構造的に防止する仕組みを確立。

**🔴 Critical (5/5 完了 ✅)**:
- ✅ C1: SL CANCELED_UNFILLED 検出（SLMonitor 新規実装）
- ✅ C2: ML信頼度を `predicted_class_proba` に統一
- ✅ C3: TP Maker タイムアウト時の自動キャンセル（_safe_cancel）
- ✅ C4: DummyModel サーキットブレーカー（MLHealthMonitor、3回連続失敗で EMERGENCY_STOP）
- ✅ C5: 5分ループ内 SL health check

**🟠 High (10/10 完了 ✅)**:
- ✅ H1 (SL 24h timeout) / H2 (起動時SL失敗) / H3 (stop_limit+slippage 二重防衛) / H4 (SL Firestore永続化) / H5 (Drawdown Firestore永続化)
- ✅ H6 (品質フィルタ レジーム別閾値: tight 0.55 / normal 0.75 / trending 0.50) / H7 (特徴量定数) / H8 (RECOVERY_TESTING 段階復帰) / H9 (6戦略アサート) / H10 (品質フィルタ共通モジュール化)
- ✅ 補強: src/analysis/common/（sl_validators / canceled_unfilled_detector / tp_sl_helpers）

**実機検証**: 5/13 24h: 勝率25% -¥5,216 → 5/14 12h: 勝率100% +¥1,500（+¥6,716改善）

### Phase 88（GCPコスト削減 + 孤児SL再発防止 + クリーンアップ・2-3週間）

**詳細プラン**: `~/.claude/plans/phase-iterative-biscuit.md`（GCP 仕様 Web 調査反映版）

**💰 Infrastructure 5件（月額¥3,000 → ¥300-500 目標）**:
- I1: Cloud Logging WARNING化（-¥100~200/月、実効ほぼゼロだが防御的に実施）
- I2: Artifact Registry リテンション（30日以上削除・最新10件保持、-¥20~50/月）
- I3: min_instances=0 + Cloud Scheduler（**-¥2,400/月想定**、Flask /trigger endpoint + OIDC認証）
- I4: メモリ 1GiB → 512MiB（-¥150/月、ペーパー稼働で <400MB 確認後）
- I5: bitbank API キャッシュ徹底（-¥20~50/月、Egress 削減）

**🟠 High 1件**:
- H11: 孤児SL注文の再発防止（5分ループ検出 + 指数バックオフ + bitbank 70004 ハンドリング）

**🟡 Medium 5件 + 🟢 Low 3件**: Kelly理由明示(M1)、APIレート制限統一(M2)、TP/SL丸め(M3)、異常検知時間帯別(M4)、税務SQLite GCS化(M5)、Phase XXX コメント整理(L1)、README/CLAUDE同期(L2)、Dead code約500行一掃(L3)

### Phase 89-92 中長期計画（Webリサーチ統合）

Phase 87/88 完了後、最新MLbot技術を段階的に導入:
- **Phase 89**: Purged K-Fold + Fractional Kelly + OFI + Funding Rate（年利12-13%）
- **Phase 90**: N-BEATS + LLM センチメント + HMM（年利14-16%）
- **Phase 91**: WebSocket depth stream + Maker戦略実装化 + BTC-ETH相関（年利15-18%）
- **Phase 92**: PPO/マルチペア/Transformer（条件付き・年利17-20%）

詳細: [docs/開発計画/ToDo.md](docs/開発計画/ToDo.md)

---

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **言語** | Python 3.13 |
| **取引所API** | ccxt（bitbank信用取引対応） |
| **データ処理** | pandas / numpy |
| **機械学習** | scikit-learn / XGBoost / LightGBM |
| **インフラ** | GCP Cloud Run / Secret Manager / Artifact Registry / Firestore (Phase 87 H4-5) / Cloud Scheduler (Phase 88 I3 予定) / Cloud Storage (Phase 88 M5 予定) |
| **CI/CD** | GitHub Actions（自動テスト・週次ML学習・デプロイ） |
| **品質管理** | pytest / coverage 75%+ / flake8 / black / isort |

---

## ドキュメント

- **[CLAUDE.md](CLAUDE.md)**: 開発ガイド・品質基準・設定詳細
- **[ToDo.md](docs/開発計画/ToDo.md)**: 開発計画・Phase 87/88 詳細・Phase 89-92 中長期計画
- **[統合運用ガイド](docs/運用ガイド/統合運用ガイド.md)**: デプロイ・監視・トラブル対応
- **[開発履歴サマリー](docs/開発履歴/SUMMARY.md)**: Phase 1-77総括
- **[Phase 87](docs/開発履歴/Phase_87.md)**: 全 Stage 実装記録（Critical 5 + High 10 達成）
- **[Phase 86](docs/開発履歴/Phase_86.md)**: TP/SL/Entry 根本再構築
- **詳細プラン**: `~/.claude/plans/phase-iterative-biscuit.md`（Phase 88 詳細設計・GCP仕様 Web 調査反映版）

---

## リスク・免責事項

仮想通貨取引には元本割れのリスクがあります。本システムの使用による損失について作成者は責任を負いません。

---

**最終更新**: 2026年6月19日 - Phase 90ρ TP引き下げ(1200/1000→800) + ライブ分析ノイズ整理 デプロイ済み（commit `dd033192`・リビジョン `0619-0955`・CI/CD成功）。①ライブ分析で R1 reconcile 実働を実証(SL配置3/成行決済2)し、invariant「致命的:1」は scale-to-zero由来のVP↔実ポジ乖離が reconcile と二重に鳴るノイズと判明→`standard_analysis.py` を種別分類(建玉合計超過=CRITICAL/VP乖離=reconcile稼働中はWARNING降格)に改修・致命的1→0・🟢正常(テスト7・分析のみ)。②ユーザー仮説「TP下げ→TP約定↑→SL率↓」を90日216件シミュ+30日BTで検証→TP800/SL2000が期待値ピーク(+46円/件)・TP1200/1000→800実装・30日BTで損益+37%(+4,252→+5,832)/勝率+9.6pt(61.1→70.7%)/DD-650/PF微減(1.134→1.078黒字維持)。③派生発見=サイズ(`ml_confidence`)とTP/SL(`adjusted_confidence`)の信頼度不整合(6/18事象A)→Stage2クランプ実装→**BT検証で不採用(revert・固定金額方式と相反し +5,832→+160悪化しコード削除)**。TP800のみ確定。直前の Phase 90π R1（実発注 + 微小端数clean-up）はデプロイ済み。Reconciliation Loop（新規 `src/trading/reconciliation/` 7モジュール・実建玉(fetch_margin_positions)を唯一の真実源・毎サイクル desired↔actual の差分を冪等に埋める・裸ポジを invariant で根治）を R0（shadow）→ R1（実発注）へ移行。R0 shadow で reconcile 動作を本番確証（裸ポジ検知・no-op正常・誤MARKET_CLOSE提案0）。観察中の 0.0018 BTC short 裸ポジ事象（微小端数で固定SL2000円÷微小amount→SL距離が約10%(11,627,135円)に破綻→SL設置失敗ループ・手動成行決済で対処）を受け微小端数 clean-up を追加（`desired.py`で固定SL距離が floor(0.7%) の5倍超を `is_micro` 判定／`diff.py`で `is_micro`→`MARKET_CLOSE`／設定 `micro_sl_multiple=5.0`）。R1=`shadow_mode=false` で reconcile が実際に裸ポジを是正（SL欠損→実SL設置 / 価格割れ・微小端数→成行決済）。Phase 87 C1 `dry_run` は維持（reconcile が MARKET_CLOSE を担うため解除すると二重決済・reconcile が trigger 冒頭で先に是正→C1 無害）。テスト57件・checks.sh全PASS。効果＝長時間SL未設置は起きなくなる（5分ごと実是正＋micro clean-up）が「一瞬も裸にしない」ではない（5分サイクルの隙間）・実建玉での実証はこれから（現在フラット）。残りR2(エントリーTP/SL統合)→R3(旧コード削除)。派生課題=ログPnLが実口座損益と乖離（手数料・金利・スリッページ未計上）。直前は Phase 90ο ポジション状態の単一情報源化 + invariant常時監視（6/15ドカンの根源治療・Stage 0/1/3デプロイ）。VP(揮発)と実ポジの二重管理→再起動で空VPが同方向上限すり抜け→サイズ膨張ドカン、を構造的に解消（Stage 0=gating合計サイズ上限/Stage 1=上限の実ポジ基準化/Stage 3=invariant常時監視）。テスト20件追加・checks.sh全PASS・取引挙動は正常時不変。Stage 2(サイズ信頼度一元化)は別タスク。直前は Phase 90ξ ライブ分析スクリプトの本番WARNING誤検知3件を修正（致命的1→0・分析スクリプトのみ・取引挙動不変・テスト9件追加・checks.sh全PASS）。`_check_ml_prediction`/`_detect_silent_failure`/success_rate判定のINFOログgrep等による構造的誤判定をWARNING生存ログ併用＋拒否考慮で解消。二次所見=Phase 90αラベル分布チェックが常時NO_DATA（別タスク候補）。直前は2026年6月6日 - Phase 90ν ライブ分析の解釈改善（誤発火reason別分類・drift retrainベース判定）+ SL引き下げ余地の調査 デプロイ完了（リビジョン `0605-2226`）。SL2000維持（90日277件で SL1750/1500 引下は期待値悪化・**6月1ヶ月様子見で7月初に再判断**）。テスト9件・checks.sh全PASS・分析スクリプトのみで取引挙動不変。直前の Phase 90μ SLMonitor誤発火の真因修正 デプロイ済み（6/5 06:43 JST・デプロイ後 Fire #2 誤発火0確認）。6/5 ライブ分析→GCPログ精査で Fire #2（fetch_error_persistent）がクリーンな誤発火と確定し、合成ID `market_close_*` の幽霊VP即除去（Fix 1・`stop_manager.py`）＋C7昇格への残量ガード対称適用（Fix 2・`sl_monitor.py`）で修正。テスト4件・`checks.sh` 全 PASS。`dry_run:true` 維持（本番で誤発火0を確認後に解除判断）。Phase 90κ は本番稼働中（リビジョン`0602-2134`／headSha`1c2918de`・6/3 06:34 JST）・本番ML `ProductionEnsemble_FULL` 稼働・trending全停止機能を確認
