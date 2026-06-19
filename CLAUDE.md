# CLAUDE.md

## しおり（現在地）

| 項目 | 値 |
|------|-----|
| **🔴 セッション中断・引き継ぎ（2026-06-10）** | 表示/伝送の異常（ANSIで出力破損・**ユーザー未入力のメッセージがClaude側に到達**）のため安全策でセッションを新規化。**bot本体・実取引・GCPログ・設定に影響なし（検証済）・問題は会話セッションの表示/伝送のみ**。**進行中の作業**: ①収益性アトリビューション分析スクリプト `scripts/analysis/trade_attribution.py`（読み取り専用・本体完成だが**テスト1件失敗・checks.sh未実行・実機未確認**＝再開時に完成させる）。背景と残作業手順は `docs/開発計画/ToDo.md` 冒頭「セッション再開時の最優先（2026-06-10）」を参照。**今日の成果**: `docs/検証記録/strategy_usage_analysis_2026-06-10.md`（6戦略中3戦略不発＝概ね設計どおり正常）＋ `docs/検証記録/2026-06-10_bot性能向上の方針整理.md`（性能向上ロードマップ）。**長期の核心**: このbotにエッジがあるか未検証→**バックテスト修復が本筋**。ユーザーへの未回答の問い「botに求めるのは利益か/作ること自体か」。教訓: gcloud出力はANSI除去してから集計。 |
| **🟢 今セッションの作業（Phase 90σ GCPログ健全性監査 → 15分足ログノイズ修正 + 形骸化スリッページコード掃除・2026-06-20・未デプロイ）** | ライブ分析(36h・致命的0・🟡監視継続)を起点に「バグ/エラー/不具合の有無」をGCPログ精査し**致命的バグ無し**を確認（**0.02 BTCポジは`fixed_table.high`の高信頼度時の正規サイズ＝膨張でない**／reconcile[LIVE]完璧稼働(noop継続)／各種「注文実行失敗」=ポジション制限・クールダウン・Maker低信頼度スキップ・trending全停止は設計どおりの拒否）。対応2件を実施。**①15分足エラー10000の毎日00:00 UTC ERRORノイズ(7日連続100%)是正**: 真因＝`bitbank_client.py:586 except Exception`がbitbank APIエラー応答(当日分の日次ファイル未生成=code10000)の`DataFetchError`を再キャッチし「予期しないエラー」ERROR化(L588)→**`except DataFetchError: raise`を前置**しノイズ抑止(呼び出し元の WARNING+continue は不変＝**取引挙動不変**・実害は元々なし＝フル取引サイクルは完遂していた)。テスト2件追加。**②変更2(SLスリッページ計測)はユーザー指摘「62はかなり過去・やり残しか/不要になったか調べよ」で過去履歴調査→「やる必要がなくなった」と確定し形骸化コードを掃除**: スリッページは **Phase 69.7(bitbank実約定PnL)移行で実損益に内包済み**(ライブ分析の損益¥-3,149がスリッページ込み)・Phase 62.16の`_analyze_slippage`はAPI失敗時フォールバック内で本番非実行・Phase 62.18 exit記録は本番0件、と**三重に形骸化**→`standard_analysis.py`(slippage_*フィールド6/呼出/メソッド/Markdown節)と`executor.py`エントリーslippage計算を削除(**DBスキーマ・Phase 62.18 exit記録・SLパターン分析・slippage_buffer は温存**)。**SL canceled_unfilled根本調査**=7日12回検知も実損は2回のみ・reconcileが価格割れ後に正しく成行決済・stop_limit化は過去3回(Phase 69.8/78/80)失敗で見送り(実スリッページは実PnLで把握可)。checks.sh全PASS(72%+)・関連137 passed・**取引挙動不変**。**デプロイは未実施(現在short 0.015保有・要判断)**。 |
| **🟢 前セッションの作業（Phase 90ρ TP引下(1200/1000→800) + ライブ分析ノイズ整理 デプロイ済み・2026-06-19・commit`dd033192`/リビジョン`0619-0955`）** | ライブ分析を起点に3件を実施。**①ライブ分析でR1実証 + ノイズ整理**: 24h分析で `reconcile[LIVE]` 稼働を実証（SL配置3/成行決済2）。「致命的:1」は scale-to-zero由来の **VP↔実ポジ乖離が R1 reconcile と二重に鳴るノイズ**と判明（reconcileは実建玉基準でSL是正済み＝実害なし）→`standard_analysis.py _check_phase90o_invariants` を**種別分類**（建玉合計超過=CRITICAL維持／VP乖離=reconcile[LIVE]稼働中ならWARNING降格）+reconcile実働可視化に改修。**致命的1→0・🟢正常**。テスト7件・分析スクリプトのみ・取引挙動不変。**②TP引き下げ検証（ユーザー仮説「TP下げ→TP約定↑→SL率↓」）**: 90日216件シミュ+30日BTで検証。SL固定でTP段階比較→**TP800/SL2000が期待値ピーク(+46円/件)**（TP600は下げすぎ・SL1500系は劣りSL2000維持＝Phase 90ν整合）。`thresholds.yaml` の confidence_based TP **1200/1000→800** に実装。30日BT: **損益+4,252→+5,832(+37%)・勝率61.1→70.7%・DD-650・PF1.134→1.078**(微減だが黒字維持＝薄利多勝化)。**③派生発見＝サイズとTP/SLの信頼度不整合(Stage 2)**: サイズは`ml_confidence`(事象A 0.657→0.02)・TP/SLは`adjusted_confidence`(<0.4→低)を見る不整合。**Stage 2クランプを実装→BT検証で不採用(revert済み)**: `strategy_confidence<0.40`でサイズを`fixed_table.low`にクランプしたが30日BTで**+5,832→+160に悪化(PF0.959)**。理由＝**固定金額TP/SLでは「TP距離=TP金額÷サイズ」ゆえサイズ↓＝距離↑**で、クランプ(0.015→0.010・310回発動)がTP距離を0.52→0.78%に広げ TP800の約定改善を相殺＝サイズクランプは固定金額方式と相反すると判明→コード/設定/テストを削除。不整合自体は実在も別アプローチが要(将来)。なお24hの2件SL(-4,352円)は**エントリー判断/TP-SL距離は正常**・stop注文がcanceled_unfilled→reconcile成行決済がカバー(スリッページ計上)。**TP800デプロイ済み（commit`dd033192`・リビジョン`0619-0955`・2026-06-19 18:55 JST・CI/CD成功）**。 |
| **🟢 前セッションの作業（Phase 90π R1 実発注 + 微小端数clean-up・2026-06-18）** | Phase 90π Reconciliation Loop を **R0（shadow）→ R1（実発注）** へ移行（plan: `~/.claude/plans/tpsl-bitbank-lexical-quail.md`）。R0 shadow で本番の reconcile 動作を確証（**裸ポジ検知・no-op正常・誤MARKET_CLOSE提案0**）。ただし R0 観察中に **0.0018 BTC short の裸ポジ事象**が発生：標準0.015でなく微小端数0.0018が残り、固定金額SL(2000円)÷微小amountで**SL距離が約10%(11,627,135円)に破綻**→SL設置が失敗しループ。**手動で成行決済しフラット化**して対処。これを受け**微小端数 clean-up を追加**：`desired.py`で固定SL距離が floor(0.7%)の5倍を超えるサイズを `is_micro` 判定／`diff.py`で `is_micro`→`MARKET_CLOSE`（SL設置でなく成行で残さない）／設定 `position_management.reconciliation.micro_sl_multiple=5.0`。**R1 移行（commit`ce5d1b28`・CI実行中→デプロイ）**=`reconciliation.shadow_mode=false` で **reconcile が実際に裸ポジを是正**（SL欠損→実SL設置 / 価格割れ・微小端数→成行決済）。**Phase 87 C1 `dry_run` は維持**（解除しない）：reconcile が MARKET_CLOSE を担うため解除すると二重決済になる・reconcile が trigger 冒頭で先に是正→建玉消滅→C1 は無害。テスト57件（micro判定・micro→MARKET_CLOSE・0.0018回帰を追加）・checks.sh全PASS。**効果と限界（正直に）**: 「今日のような長時間SL未設置」は起きなくなる（5分ごと実是正＋micro clean-up）。ただし「一瞬も裸にしない」ではない（5分サイクルの隙間）。**実建玉での実証はこれから（現在フラット）**。**残り**: R2（エントリーTP/SLを desired.py 共有に統合）→ R3（旧コード削除）。**派生課題(未対応)**: ログPnL(Phase 61.9)が実口座損益と乖離（成行スリッページ+往復手数料+金利を建値ベース概算が未計上）→ライブ分析の損益をbitbank実口座基準にすべき。 |
| **🟢 前セッションの作業（Phase 90ο 根源治療・2026-06-15）** | 6/15の「コツコツドカン」(-3,277円)の**根源治療**。原因＝VP(揮発メモリ)と実ポジの**二重管理** + 本番trigger経路に復元なし + 再起動でVP揮発→空VPで同方向上限すり抜け→重複ショート0.0325 BTC膨張→一括SLドカン。ユーザー合意で対症療法でなく**体質改善（実ポジを唯一の正・VPはキャッシュ降格・invariant常時監視）**を3段デプロイ。**Stage 0**(commit`563cd1f5`)=gating層に建玉合計サイズ上限`max_total_position_btc=0.02`（VP非依存の最終防衛線）+ trigger_server取得失敗時monitor_onlyフォールバック（安全優先）。**Stage 1**(`2cb93c74`)=`check_limits`を実ポジ(fetch_margin_positions)基準化（live時・取得失敗=エントリー拒否・daily回数のみVP継続・paper/backtestは従来VP）。**Stage 3**(`1fe431fb`)=`tp_sl_manager._check_position_invariants`が両経路合流点で毎サイクル「建玉合計>上限/両建て/VP↔実ポジ乖離(3連続)」を検知しCRITICAL/WARNING、standard_analysisで可視化（自己修復はStage0/1で実害防止済み+循環リスクで見送り）。テスト=trade_gating7+limits2+invariant9+統合(6/15回帰)2件・checks.sh全PASS・**取引挙動は正常時(1ポジ≤0.02)不変**。**別タスク=Stage 2**（サイズ判定をml_confidence(max(p0,p1))→adjusted_confidence一元化・収益性影響でバックテスト検証後）。教訓: インフラ変更(Phase88 scale-to-zero)が状態保持の前提を壊す横断影響を見落としていた。[[live-analysis-warning-log-trap]] |
| **前セッションの作業（Phase 90ξ・2026-06-15）** | ライブ分析でBot機能診断の「致命的:1」を検出→GCPログ精査で**本番 LOG_LEVEL=WARNING 下の誤検知3件**と確定し修正（`scripts/live/standard_analysis.py`・**分析スクリプトのみ・取引挙動不変**）。真因=複数チェックが**INFOレベルのログをgrep**し構造的に0件→誤判定。①`_check_ml_prediction`②`_detect_silent_failure`③success_rate判定をWARNING生存ログ併用＋拒否考慮で解消。テスト9件・checks.sh全PASS。実機--quickで**致命的1→0・正常13→16・判定🟠→🟡**。二次所見=Phase 90αラベル分布チェックが常時NO_DATA（別タスク候補）。 |
| **現在Phase** | **Phase 90ρ TP引き下げ(1200/1000→800) + ライブ分析ノイズ整理 デプロイ済み（2026-06-19・commit`dd033192`・リビジョン`0619-0955`・CI/CD成功）**。①TP800: 90日216件シミュ+30日BTで期待値改善を実証（損益+4,252→+5,832/勝率61.1→70.7%/DD-650/PF1.134→1.078）。②Stage2(信頼度クランプ): 実装→**BT検証で不採用(revert済み)**。固定金額TP/SLではサイズ↓＝距離↑でTP800と相反し+5,832→+160悪化(PF0.959)。不整合自体は実在も別アプローチが要(将来)。③ライブ分析: R1 reconcile 実働を実証(SL配置3/成行決済2)し invariant VP乖離ノイズを WARNING 降格(致命的1→0・🟢正常)。**Phase 90π R1（reconcile実発注）はデプロイ済み・本セッションのライブ分析で実証確認**。実建玉を唯一の真実源とし毎サイクル desired↔actual の差分を冪等に埋める設計（新規`src/trading/reconciliation/`7モジュール）で裸ポジを根治。R0(shadow)で reconcile 動作を確証（裸ポジ検知・no-op正常・誤MARKET_CLOSE提案0）したが、観察中の**0.0018 BTC short 裸ポジ事象**（微小端数でSL距離が約10%に破綻→SL設置失敗ループ・手動成行決済で対処）を受け**微小端数 clean-up を追加**（`desired.py`で固定SL距離がfloor(0.7%)の5倍超を`is_micro`判定／`diff.py`で`is_micro`→`MARKET_CLOSE`／`micro_sl_multiple=5.0`）。R1=`shadow_mode=false`で**reconcile が実際に裸ポジを是正**（SL欠損→実SL設置/価格割れ・微小端数→成行決済）。**Phase 87 C1 `dry_run` は維持**（reconcile が MARKET_CLOSE を担うため解除すると二重決済・reconcile が trigger 冒頭で先に是正→C1 無害）。テスト57件・checks.sh全PASS。効果＝長時間SL未設置は起きなくなる（5分ごと実是正＋micro clean-up）が「一瞬も裸にしない」ではない（5分サイクルの隙間）・**実建玉での実証はこれから（現在フラット）**。残りR2(エントリーTP/SL統合)→R3(旧コード削除)。**直前の Phase 90ν ライブ分析の解釈改善 + SL引き下げ余地の調査 デプロイ完了（2026-06-06・リビジョン`0605-2226`）**。GCPログ精査でライブ分析の警告2件が「カウントは正しいが解釈が粗い」と判明→**改善A 誤発火をreason別分類**（`canceled_unfilled`=3/3連続検出を経た設計どおり昇格＝誤発火ではない、と `fetch_error_persistent`=真のFire #2誤発火 を分離。真の誤発火>0のみ警告）+**改善B drift判定をretrain_triggeredベース化**（検出多数でも再学習0なら「strategy_signal主体の想定内変動・実害なし」と正常扱い・「Bonferroni補正薄い」廃止）。テスト9件・checks.sh全PASS・**分析スクリプトのみで取引挙動不変**。実機--quickでdrift正常表示確認。**SL引き下げ調査**: `full_entry_simulation`で SL2000→1750/1500 の引下余地を90日277件検証→SL距離が縮むと一時的逆行を吸収できずTP取引がSL転落し期待値悪化（90日TP1200: -198→-270→-219円）→**SL2000維持・下げる余地なし**。ただし**2026年6月の1ヶ月間ライブ様子見で7月初に再判断**。警告残3件（メモリP95 87%・孤児SL・オーダーブックCSV）は実害なし確認済。**直前の Phase 90μ SLMonitor誤発火の真因修正 デプロイ済み（6/5 06:43 JST・リビジョン`0604-2142`→現`0605-2226`に内包・デプロイ後Fire #2誤発火0を確認）**。6/5ライブ分析で`SLMonitor DRY_RUN誤発火:2回`を検出→GCPログ精査（06/04 19:30-20:30 UTC）で**誤発火2回は別々の2メカニズム**と確定。**Fire #1**（reason=canceled_unfilled・90θ 3/3）は15分stuckのSLを正しく昇格し同サイクルでPhase 64.12も実決済＝**設計どおり（誤発火ではない・現状維持）**。**Fire #2**（reason=fetch_error_persistent）が**クリーンな誤発火**で2バグの複合: ①`stop_manager._check_tp_sl_execution`が合成ID`market_close_*`（Phase 64.12成行決済済み）に`fetch_order`して例外を握り潰し**幽霊VPが除去されず**毎サイクルC5/C7の対象に ②`sl_monitor.check_sl_health`のC7昇格パスが他の昇格（canceled_unfilled/expired/timeout）と違い`_position_already_closed`残量ガードを通さず実0でも3サイクルで無条件発火。修正: **Fix 1** `market_close_*`を`fetch_order`せず`stop_loss`確定で幽霊VP即除去（根本・`stop_manager.py`）/ **Fix 2** C7昇格前に残量ガードを対称適用し実0なら抑止（防御・`sl_monitor.py`）。`dry_run:true`は変更なし（誤発火0を本番確認後に別タスクで解除判断）。テスト4件追加（sl_monitor 3＋stop_manager 1）・checks.sh全PASS。**非バグと確定**: trending ADXエントリー（実態normal_range・重み0.15）/ torch FULL（本番ProductionEnsemble_FULL稼働・ローカル限定）/ Makerリトライ0%（全試行1で約定） |
| **直近の調査（2026-06-10・戦略稼働分析）** | 6/5デプロイ後4日のライブ実績で**6戦略中3戦略がエントリー0件**（不発=ATRBased/StochasticReversal/MACDEMACrossover、稼働=CMFReversal/ADXTrendStrength/BBReversal）の理由を、ソース・GCPログ・Web知見で多角分析。**コード変更なし・分析のみ**。結論は**2層構造**: ①trending64%で全6戦略停止（3戦略特有でない・レンジ専用設計どおり。trending判定=ADX>22 AND \|EMA傾き\|>0.1%）②残り36%のnormal/tight窓で3戦略は発動条件が構造的に厳しくシグナル自体出にくい（ATR消尽率70%/Stochastic価格変動0.5%/MACDトレンド型ジレンマ）。維持率拒否(Phase 50.4)はシグナル後で機会をさらに細らせる二次要因。Web知見も「一部だけ発動・他不発はレジーム適応設計では正常」と裏付け。**総合=概ね設計どおりの正常挙動・ただし機会損失あり**。実績は6決済・勝率50%(3勝3敗)・ネット約-1,910円・RR0.78:1（以前0.25から改善）。未確定点=「シグナルを出して潰されたか/出していないか」はBACKTEST_MODEのDEBUGログ解析が要・将来オプション。詳細`docs/検証記録/strategy_usage_analysis_2026-06-10.md`。※調査中`gcloud logging read`出力にロガー由来ANSI色コードが混入し表示が乱れたが、データ汚染/インジェクションは全件検証で無しと確認（無害・教訓=今後ANSI除去して集計） |
| **直前の作業（Phase 90κ）** | Maker約定率の改善（リトライ実動化＋best気配追従）実装・デプロイ完了（2026-06-03 06:34 JST・リビジョン`crypto-bot-service-prod-phase89a-cost-opt-0602-2134`／headSha`1c2918de`・CI/CD PASS）。GCPログ30日精査で真因確定: ①**post_onlyキャンセル0件**②**リトライ実質1回**（`max_retries=5`が機能しないバグ・`_wait_for_maker_fill`に残り総時間120秒フルを渡し試行1で全体timeout消費）③タイムアウト44%はqueue末尾/56%は逆行。修正: **P1** `per_attempt_timeout=timeout//max_retries`でリトライ実動化（timeout120→60・max_retries5→4で実効4回）/ **P2** リトライ毎に最新best気配を再取得し追従。**効果は部分的**（逆行56%・薄板73%は救えない）。テスト6件・checks.sh全PASS(2507テスト) |
| **直前の作業（Phase 90ι）** | 収益構造のデータ駆動分析＋tight逆行の観察可能化（コミット`165e0dcb`）。「勝率・収益率を上げるには」の問いに対し、改善レバーを順にデータ検証: ①Maker率向上=無効（未約定の主因は価格逆行・タイムアウト7件中5件は120秒で指値未到達）②コスト織り込み=穴小（TP決済も実態大半Maker）③**実MFE/MAE分析（90日277件）で真因確定**=レジーム別の方向性エッジ。**normal_range=順エッジ黒字(MFE0.609%>MAE0.424%・期待値+333〜500円)、tight_range=逆エッジ赤字(MFE0.355%<MAE0.583%・主力56%なのに-170〜250円)、trending=大逆行(停止済・5/11以降混入ほぼ0)**。tight逆行は「小勝ち大負け（平均回帰のブレイク弱点）」で最有力はATRBased(重み0.35・消尽=反転で反転確認なし)だが**戦略名がエントリーログに無く確証不可**。→ **観察可能化を実装**: (A)`market_regime_classifier`のtight検出にADX・EMA傾き長期を併記（トレンド初期誤判定の診断）、(B)`executor`のエントリー成功ログに戦略名・レジームを併記しWARNING昇格（本番で戦略別逆行を追跡可能化）。+ MFE/MAE分析ツール(`full_entry_simulation.py`)実装・テスト7件。取引挙動は不変・ログのみ。数日蓄積後に戦略別逆行を特定→ATRBased等の的を射た修正へ |
| **🎯 Phase 90ι 収益分析の結論（重要）** | 損益-4,240円/週≒手数料-2,796+グロス-1,444。**手数料はMaker率改善では減らせない（価格逆行が主因）**。**収益の本丸はレジーム別の方向性エッジ**: normal集中・tight見直し・trending停止維持。TP/SLは normal=薄利多勝(TP500-750/SL1500)が最適だがレジーム別TP/SL有効化は構造変更(confidence_based上書き解除)で小サンプル(各20-30件)ゆえ慎重に。tight赤字はTP/SLでは救えず**エントリー品質(ML・戦略)が根本**。`scripts/analysis/full_entry_simulation.py --mfe-mae --days N`でMFE/MAE再測定可。Cloud Loggingレジームログ保持は約30日 |
| **直前の作業（Phase 90θ）** | SLMonitor誤発火 真因特定＆根本修正（コミット`96ab5525`）。Phase 90ηガードがデプロイ後も誤発火継続→真因2層(幽霊VPクリーンアップ漏れ＋canceled_unfilled中間状態タイミング競合)を修正。P0-A `is_canceled_unfilled`をSL約定検知し幽霊VP即除去 / P0-B 連続検出カウンタ(3回連続で昇格) / P1 REJECTEDをガード除外 / P3 ライブ分析に誤発火監視追加。dry_run継続。デプロイ後に`sl_monitor_dry_run_fire_count`=0を確認予定 |
| **直前の作業（Phase 90η）** | 稼働中Bot健全性監査。Day 1検証で土日縮小（90ε/ζ）正常・GCPコスト最適化(I3)完璧・取引/設定/Maker正常を確認、致命的バグなし。不整合3件修正: (A)稼働率46.8%誤表示→15分ベースに訂正、(B)WebSocket NOT_STARTED誤警告→triggerモードSKIPPED扱い、(C)SLMonitor誤発火率100%→ポジ残量ガード`position_close_guard`導入（※Phase 90θでこのガードがデプロイ後も誤発火継続と判明し真因修正）|
| **直前の作業（Phase 90ζ）** | Phase 90ε デプロイ後のライブ分析で判明した観察性の穴を補修。①**SL土日縮小が本番ログで見えない**問題（SL適用ログが INFO で LOG_LEVEL=WARNING に抑制）→ `strategy_utils.py` の `🛡️ 固定金額SL適用` を INFO→WARNING 昇格（Phase 90γ-⑥ のTP昇格と対称）。`confidence_label` に Phase 90ε の `(土日縮小→N円)` 含むため土日SL縮小が検証可能に。②**特徴量数の37/55不整合**（README図・checks.sh ログが旧37のまま）→ 現在形参照を55に統一。テスト1件追加（assertLogs でWARNING昇格担保）。**取引挙動は不変・ログレベルと文言のみ**。③**ライブ分析スクリプト `standard_analysis.py` を直近修正に追従**（5点）：90δ post_only実Taker約定WARNING監視追加 / 90ε土日TP500監視 / 90ζ SL適用ログ(Phase 86)監視 + SL grep空振り修正(`Phase 70.2`→`Phase 86`) / 特徴量grep 37→55 修正(`feature_37_count`→`feature_full_count`)。テスト5件追加・quick分析で実行確認済（土日TP500を50件検出・SL WARNINGはデプロイ後計算機会待ち）|
| **直前の作業** | ユーザー指摘「日本の土日祝はBTCが狭いレンジに収まりやすく、TP1000-1200円では約定しないまま月曜を迎える」を起点に **Phase 90ε 土日TP/SL縮小** を実装。実運用の confidence_based（固定金額）経路に **JST土日判定**（Phase 83C のJST明示変換を踏襲・`weekday()>=5`）を追加し、**土日は信頼度に関係なくTPを一律500円**（距離≒0.36%でレンジ内利確優先）に上書き。SLは target1000円へ下げるが **floor 0.7% 据え置き（A案）** のため実効SL≒0.70%（≒1,733円@0.015BTC・平日2000円より縮小しつつノイズ耐性維持）。祝日は対象外（jpholiday 不採用・追加依存ゼロ）。変更3ファイル（thresholds.yaml / strategy_utils.py / test_risk_manager.py）・テスト6件追加・black/isort/flake8 PASS・実config E2E確認済|
| **直前の作業（Phase 90δ）** | ライブ分析調査でユーザー指摘（取引画面の M/T 列がテイカー）を起点に **Maker 戦略の致命バグを発見**：`bitbank_client.py:840` が `postOnly`（camelCase）を送信していたが bitbank API は `post_only`（snake_case）を期待し、ccxt 4.5.1 は変換しないため **post_only が全注文で無視され通常指値化 → 即時約定時にテイカー約定**していた。**Phase 90γ-⑥ Day1 の「Maker 化率100%」は虚偽記録**（約定種別を実 API で検証せず「Maker(0%)」決め打ちだった）。Phase 90δ で 4 修正実装（1-A post_only 名前修正 / 1-B 約定種別の真実観測 / 2-C 緊急成行決済の DRY_RUN 誤カウント修正 / 2-D 50062 レース対策）+ 18 テスト追加・`checks.sh` 全 PASS（72%+ カバレッジ）|
| **次の予定** | **Phase 90ι: 6/6頃にエントリーログ（戦略名・レジーム併記・WARNING昇格）の蓄積を分析→tight_rangeで逆行する戦略を特定→的を射た修正（ATRBased反転確認追加 / tight判定厳格化 / レジーム別TP/SL有効化のいずれか）**。`scripts/analysis/full_entry_simulation.py --mfe-mae --days N` でMFE/MAE再測定。並行して **Phase 90θ デプロイ後の検証**（誤発火解消の確認）：①ライブ分析 `standard_analysis.py` の新項目 **`sl_monitor_dry_run_fire_count` が 0** になったか（従来は5分毎に `🧪 Phase 87 C1 [DRY_RUN]` 発火）、②GCPログで `Phase 87 C5: SL異常検出 reason=canceled_unfilled` が激減/消滅・出ても `canceled_unfilled_pending` 抑止ログで止まりDRY_RUN緊急決済に至らないか、③`detect_auto_executed_orders` で canceled_unfilled SL が `stop_loss` 約定検知され幽霊VPが翌サイクルに持ち越されないか、④`sl_monitor_validator.py --days 3` で誤発火率100%→0%付近を確認→改善できれば**別タスクで `dry_run: false` 解除を判断**。1-2日継続0で解消確定。**並行して既存項目**：(Phase 90ζ)土日SL縮小WARNING / (Phase 90ε)土日TP500 / (Phase 90δ)post_only実Maker化率。Phase 90γ-⑥累積効果(PF・月利)はDay 7に最終判定 |
| **🎯 Phase 90γ-⑦+⑨ 統合実装内容** | ⑦-1 INFO→WARNING 格上げ 3 箇所 (backtest_runner L935/L1063, ml_health_monitor L155) / ⑦-2 例外スワロー解消 3 箇所 (trigger_server L73 pragma 解除含む) / ⑦-3 サイレント失敗ログ 3 箇所 (DummyModel fallback / ml_confidence=None / drift skip) / ⑦-4 persistence=None CRITICAL 警告 (初回のみ・重複防止) / ⑨ 25 件テスト追加（8+5+6+6+2）。**カバレッジ目標 73→78% / コードロジック変更ゼロ・観察可能性のみ強化** |
| **🎯 Phase 90γ-⑥ Day 1 検証結果（5/29 朝・完全成功）** | bitbank API 実取引で TP 距離 **0.956%**（目標 0.7-0.9% を上回り達成）・実効 RR **~1.02:1**（旧 0.25:1 から 4 倍改善）・~~Maker 化率 100%~~（⚠️ **Phase 90δ で虚偽判明**：post_only 未機能で約定種別未検証だったため実態はテイカー約定）・信頼度ラベル WARNING ログ **64/65 試行で機能**（旧バグ時 0%）。実取引件数は trending 相場継続で 1 件のみだが、修正①の confidence_based 機能性は完全証明 |
| **🎯 同時エントリー仕様確認** | Phase 50.4 維持率予測拒否 48 件/24h は**バグではなく仕様通り**。証拠金 24 万円 / 1 エントリー 0.015 BTC ≒ 17 万円消費で維持率 130%・追加エントリーで 76% へ落ちる予測 → 強制ロスカット 50% への 30pt 安全バッファとして妥当。同時エントリー数増加は証拠金増額が正攻法 |
| **🎯 Phase 90γ-⑥ 最重要発見（履歴）** | bitbank API 7 日実取引で TP 平均勝利 ¥300・平均損失 ¥1,212・実効 RR 0.25:1 と判明。原因は `TradeEvaluation` に `confidence` フィールドが存在しないのに `getattr(evaluation, "confidence", None)` で取得していた致命バグ。修正で `evaluation.adjusted_confidence or evaluation.confidence_level` の fallback chain に変更 |
| **🎯 外部ソース検証結果（5/28）** | bitbank・Binance・業界標準 ADX で Bot のレジーム判定が一致確認（直近 24h で trending 60-66%）。「取引ない = trending 相場」は妥当。TP/SL 距離は ATR×6 と業界標準（×1.5-2.0）より広いが Phase 85 実証で意図的設定 |
| **過去 7 日実績（5/21-5/28）** | 取引 15 ペア / 勝率 **66.7%** (10勝5敗) / 総 NET **¥-3,056** / **PF 0.496** / 平均勝利 ¥300 vs 平均損失 ¥1,212 (RR 0.25:1) / **月利 -2.6% / 年利 -31%**。**主因は Phase 90γ-⑥ で修正済 confidence バグの累積影響**。Day 1 で機能性確認済のため、Day 7（6/5 頃）に PF > 1.2 / 月利 > 0% への改善見込み |
| **総合評価** | ✅ **Phase 90γ-⑥ Day 1 完全成功で核バグ修正済・Phase 90γ-⑦+⑨ で観察体制も強化**。勝率 66.7% は健全、レジーム判定は外部ソースで妥当性確認済。**Phase 90δ で Maker 戦略の致命バグ（post_only 未機能）を修正済**（旧「Maker 化率 100%」は虚偽）。**次の 2.5 ヶ月放置型バグを 24h 以内に検知できる体制**を構築。Bot 継続稼働推奨・Day 7 で年利改善を最終判定 |
| **特徴量数 / ML モデル** | 37 → **55** / 3 → **4**（LGB 34%/XGB 34%/RF 17%/N-BEATS 15%）|
| **v8e macro F1** | LGB CV 0.546 / Test 0.486・XGB CV 0.459・RF CV 0.530・N-BEATS CV 0.514（naive 0.41 比 +0.10〜+0.14）|
| **追加課金 / GCP 月額** | ゼロ（GPU・LLM 不採用）/ 現状 ¥1,400-1,700（うち Cloud Run compute は Phase 88 I3 scale-to-zero で月~110円・課金インスタンス時間1.1%。残りは Logging/Artifact Registry 等）|
| **最終更新** | 2026年6月20日 - **Phase 90σ GCPログ健全性監査 → 15分足ログノイズ修正 + 形骸化スリッページコード掃除（未デプロイ・現在short 0.015保有）**。ライブ分析(36h・致命的0・🟡)起点に「バグ/エラー/不具合の有無」をGCPログ精査し**致命的バグ無し**確認(0.02 BTCポジは`fixed_table.high`の高信頼度時の正規サイズ＝膨張でない/reconcile[LIVE]完璧稼働/各種「注文実行失敗」は設計どおり拒否)。①15分足エラー10000の毎日00:00 UTC ERRORノイズ(7日連続100%)是正＝`bitbank_client.py:586 except Exception`がbitbank APIエラー応答(当日分の日次ファイル未生成=code10000)の`DataFetchError`を再キャッチし「予期しないエラー」ERROR化(L588)→**`except DataFetchError: raise`前置**で抑止(呼び出し元WARNING+continue不変＝取引挙動不変・実害は元々なし＝フル取引サイクルは完遂)・テスト2件。②変更2(SLスリッページ計測)はユーザー指摘「62は過去・やり残しか不要になったか調べよ」で過去履歴調査→**「やる必要がなくなった」と確定し形骸化コード掃除**＝スリッページはPhase 69.7(bitbank実約定PnL)移行で実損益に内包済み(ライブ分析損益がスリッページ込み)・Phase 62.16の`_analyze_slippage`はAPI失敗時フォールバック内で本番非実行・Phase 62.18 exit記録は本番0件と**三重に形骸化**→`standard_analysis.py`(slippage_*フィールド6/呼出/メソッド/Markdown節)と`executor.py`エントリーslippage計算を削除(**DBスキーマ・Phase 62.18 exit記録・SLパターン分析・slippage_bufferは温存**)。SL canceled_unfilled根本調査=7日12回検知も実損2回のみ・reconcileが価格割れ後に正しく成行決済・stop_limit化は過去3回(Phase 69.8/78/80)失敗で見送り。checks.sh全PASS(72%+)・関連137 passed・取引挙動不変。**直前は Phase 90ρ TP引き下げ(1200/1000→800) + ライブ分析ノイズ整理 デプロイ済み（commit`dd033192`・リビジョン`0619-0955`・CI/CD成功）**。①ライブ分析で R1 reconcile 実働を実証(SL配置3/成行決済2)し、invariant の「致命的:1」は scale-to-zero由来のVP↔実ポジ乖離が reconcile と二重に鳴るノイズと判明→`standard_analysis.py` を種別分類(建玉合計超過=CRITICAL/VP乖離=reconcile稼働中はWARNING降格)に改修・致命的1→0・🟢正常(テスト7・分析のみ)。②ユーザー仮説「TP下げ→TP約定↑→SL率↓」を90日216件シミュ+30日BTで検証→**TP800/SL2000が期待値ピーク(+46円/件)**・TP1200/1000→800実装・30日BTで損益+37%(+4,252→+5,832)・勝率+9.6pt(61.1→70.7%)・DD-650・PF微減(1.134→1.078黒字維持)。③派生発見=サイズ(`ml_confidence`)とTP/SL(`adjusted_confidence`)の信頼度不整合(6/18事象A 0.02 long「失敗確信高で大サイズ」)→Stage2クランプ実装→**BT検証で不採用(revert済み)**: 固定金額TP/SLではサイズ↓＝距離↑でTP800と相反しBT+5,832→+160悪化と判明しコード削除。**直前の Phase 90π R1（実発注 + 微小端数clean-up）はデプロイ済み**。R0(shadow)で reconcile 動作を本番確証（裸ポジ検知・no-op正常・誤MARKET_CLOSE提案0）。ただし観察中の**0.0018 BTC short 裸ポジ事象**（標準0.015でなく微小端数0.0018が残り、固定SL2000円÷微小amountでSL距離が約10%(11,627,135円)に破綻→SL設置失敗ループ・手動成行決済で対処）を受け**微小端数 clean-up を追加**（`desired.py`で固定SL距離がfloor(0.7%)の5倍超を`is_micro`判定／`diff.py`で`is_micro`→`MARKET_CLOSE`＝成行で残さない／設定`position_management.reconciliation.micro_sl_multiple=5.0`）。R1=`shadow_mode=false`で**reconcile が実際に裸ポジを是正**（SL欠損→実SL設置/価格割れ・微小端数→成行決済）。**Phase 87 C1 `dry_run` は維持**（解除しない）：reconcile が MARKET_CLOSE を担うため解除すると二重決済になる・reconcile が trigger 冒頭で先に是正→建玉消滅→C1 は無害。テスト57件（micro判定・micro→MARKET_CLOSE・0.0018回帰を追加）・checks.sh全PASS。効果＝長時間SL未設置は起きなくなる（5分ごと実是正＋micro clean-up）が「一瞬も裸にしない」ではない（5分サイクルの隙間）・**実建玉での実証はこれから（現在フラット）**。残りR2(エントリーTP/SLを desired.py 共有に統合)→R3(旧コード削除)。派生課題=ログPnLが実口座損益と乖離（手数料・金利・スリッページ未計上）→分析を実口座基準にすべき。直前は **Phase 90ο ポジション状態の単一情報源化 + invariant常時監視（6/15ドカンの根源治療・Stage 0/1/3デプロイ）**。VP(揮発)と実ポジの二重管理→再起動で空VPが同方向上限すり抜け→サイズ膨張ドカン、を構造的に解消。Stage 0=gating合計サイズ上限(0.02)・取得失敗時monitor_only / Stage 1=上限チェック実ポジ基準化(取得失敗=拒否) / Stage 3=invariant常時監視(検知+ログ+ライブ分析可視化)。テスト計20件追加・checks.sh全PASS・取引挙動は正常時不変。Stage 2(サイズ信頼度一元化)は別タスク。直前は **Phase 90ξ ライブ分析スクリプトの本番WARNING誤検知3件を修正（致命的1→0・分析スクリプトのみ・取引挙動不変・テスト9件追加・checks.sh全PASS）**。`_check_ml_prediction`/`_detect_silent_failure`/success_rate判定がINFOログのgrep等で構造的に誤判定していたのをWARNING生存ログ併用＋拒否考慮で解消。二次所見=Phase 90αラベル分布チェックが常時NO_DATA（別タスク候補）。直前は2026年6月6日 - **Phase 90ν ライブ分析の解釈改善（誤発火reason別分類・drift retrainベース判定）+ SL引き下げ余地の調査 デプロイ完了（リビジョン`0605-2226`）**。SL2000維持（90日277件で SL1750/1500 引下は期待値悪化と判明）・**6月1ヶ月様子見で7月初に再判断**。テスト9件・checks.sh全PASS・取引挙動不変。**直前の Phase 90μ SLMonitor誤発火の真因修正 デプロイ済み（6/5 06:43 JST・デプロイ後Fire #2誤発火0確認）**。6/5ライブ分析→GCPログ精査でFire #2（fetch_error_persistent）がクリーンな誤発火と確定し、合成ID`market_close_*`の幽霊VP即除去（Fix 1）＋C7昇格への残量ガード対称適用（Fix 2）で修正。テスト4件・checks.sh全PASS。`dry_run:true`維持（本番で誤発火0を確認後に解除判断）。**直前の Phase 90λ**: GCPログ精査で検出した低重大度3件に対応 — ①bitbank 50026を孤児SL解消済み＝成功扱い（CRITICALノイズ解消・`tp_sl_manager.py`＋`thresholds.yaml already_resolved_patterns`・テスト2件）②CI/CD SetIamPolicy権限拒否（要IAM付与・別途）③デプロイはフラット時推奨の運用メモ。**Phase 90κ** は本番デプロイ済み（リビジョン`0602-2134`／headSha`1c2918de`・6/3 06:34 JST・UTC命名）→ 本番稼働中・本番ML `ProductionEnsemble_FULL`稼働・trending全停止機能を確認 |

> **🚀 セッション再開時は `docs/開発計画/ToDo.md` の「セッション再開時の手順」セクションを最優先で確認**
>
> 詳細計画: `docs/開発計画/ToDo.md` / `~/.claude/plans/humming-prancing-lamport.md`（Phase 90γ-⑦+⑨ 統合プラン）
> 開発履歴: `docs/開発履歴/SUMMARY.md`（Phase 1-90γ-⑦+⑨）、`docs/開発履歴/Phase_71-81.md`、`Phase_82.md`〜`Phase_90.md`

---

## 🚀 セッション再開時の最優先タスク（2026-05-29 時点・Phase 90γ-⑦+⑨ デプロイ完了 → Day 1 観察可能化検証段階）

Phase 90γ-⑦（観察可能化）+ Phase 90γ-⑨（テストカバレッジ向上）統合 PR は commit `ea79e25e` で本番デプロイ完了（5/29 06:28 JST / revision `crypto-bot-service-prod-phase89a-cost-opt-0528-2124`）。CI/CD 全 PASS（14m10s）。

統合プラン: [`~/.claude/plans/humming-prancing-lamport.md`](~/.claude/plans/humming-prancing-lamport.md)（Phase 90γ-⑦+⑨ 詳細）

### Step 1: Phase 90γ-⑦ Day 1 観察可能化検証（5/30 朝・5 分）

```bash
# (1) 新規 WARNING ログ確認（Phase 90γ-⑦ で可視化した 5 イベント）
gcloud logging read 'textPayload=~"Phase 90γ-⑦"' --freshness=24h --format='value(textPayload)' | head -30

# (2) 個別イベント別の出現数（健全性指標）
for ev in "feature_values 空" "precomputed ML 予測範囲外" "全レベル失敗 → DummyModel" \
          "MLHealthMonitor persistence=None" "Firestore health_check ping 削除失敗" \
          "QualityFilter 評価失敗" "pandas 未インストール" "有意特徴量"; do
  count=$(gcloud logging read "textPayload=~\"$ev\"" --freshness=24h --format='value(timestamp)' | wc -l)
  echo "  $ev: $count 件"
done

# (3) Phase 90γ-⑥ Day 2 累積効果（信頼度ラベル + TP 距離の継続観察）
gcloud logging read 'textPayload=~"Phase 61.7: 固定金額TP適用"' --freshness=24h --format='value(textPayload)' | head -20
venv/bin/python3 scripts/live/standard_analysis.py --hours 24
```

### Step 2: KPI 達成判定マトリクス（Phase 90γ-⑦ Day 1）

| 指標 | Day 1 期待 | 不達時 |
|---|---|---|
| 新規 WARNING ログ可視化 | ≥ 5 種類のうち 3 種類以上 | ⑦-x 個別調査 |
| `DummyModel フォールバック` | 0 件 | ML モデル健全性チェック |
| `MLHealthMonitor persistence=None` | 0 件（Firestore 正常時）| Firestore 接続調査 |
| `Firestore ping 削除失敗` | 0 件 | Firestore 権限調査 |
| `有意特徴量 N < 3` | あっても OK（既知の正常パターン）| - |

### Step 3: Phase 90γ-⑥ Day 7 累積効果（6/4 頃・最終判定）

| 指標 | 修正前（7 日実績）| Day 7 目標 |
|---|---|---|
| 平均勝利 | ¥300 | **¥1,200+** |
| 実効 RR 比 | 0.25:1 | **0.6-0.75:1** |
| PF | 0.496 | **> 1.2** |
| 月利 | -2.6% | **+1-2%** |
| 年利換算 | -31% | **+12-24%** |

### Step 4: Day 1 結果に応じた次フェーズ判断

| Day 1 結果 | 次フェーズ | 着手時期 |
|---|---|---|
| ✅ 新規 WARNING 5 種以上可視化 + 致命イベント 0 件 | Phase 90γ-⑥ Day 7 待機 + **必要なら ML 改善（Phase 90γ-④）着手判断** | 6/4 以降 |
| 🟡 DummyModel フォールバック検出 | **ML モデル復旧優先**（再学習 or ロールバック）| 即時 |
| 🔴 persistence=None 頻発 | **Firestore 接続調査優先**（IAM・project ID 確認）| 即時 |
| バックテスト本気でやるなら | **Phase 90γ-⑧（経路統合）着手判断**（現状は優先度低）| 6/5 以降 |

### 緊急ロールバック（5 分以内）

```bash
# Phase 90γ-⑦+⑨ 統合 PR の revert（観察可能化を無効化）
git revert ea79e25e && git push origin main

# Phase 90γ-⑥ も同時に revert したい場合
git revert ea79e25e 68cf68e3 && git push origin main
```

### Phase 90γ-⑥ Day 1 検証結果（5/29 朝・完全成功）

| 指標 | 旧バグ時 | Day 1 実測 | 目標 | 判定 |
|---|---|---|---|---|
| TP 距離 | 0.3% / 0.9% 混在 | **0.956%** | 0.7-0.9% 統一 | ✅ ほぼ達成 |
| SL 距離 | 0.86% | **0.941%** | - | ✅ |
| 実効 RR 比 | 0.25:1 | **~1.02:1** | 0.6:1 以上 | ✅ 大幅達成 |
| Taker 率 | 87.5% | **0%（Maker 100%）** | ≤ 30% | ✅ 達成 |
| 信頼度ラベル | 全スキップ | 高信頼度 **64 回** / 低信頼度 **1 回** | 信頼度別運用 | ✅ 完璧 |

→ Phase 90γ-⑥ 修正① の confidence 属性名バグ修正は **完全に機能**。`adjusted_confidence or confidence_level` の fallback chain で 65 試行全てに信頼度ベース TP=1500/SL=2000 が適用された。

### Phase 90γ-⑦+⑨ 実装内訳

| 修正 | 内容 |
|---|---|
| ⑦-1 (3 箇所) | INFO→WARNING 格上げ (backtest_runner L935/L1063 + ml_health_monitor L155) |
| ⑦-2 (3 箇所) | 例外スワロー解消 (backtest_runner L1299 + ml_health_monitor L325 + trigger_server L73 pragma 解除) |
| ⑦-3 (3 箇所) | サイレント失敗ログ (ml_loader DummyModel fallback + backtest_runner ml_confidence=None + ml_health_monitor drift skip) |
| ⑦-4 (1 箇所) | persistence=None CRITICAL ログ (ml_health_monitor._save_state・初回のみ・重複防止) |
| ⑨-1 (8 件) | test_backtest_runner.py 新規・TestBacktestRunnerMLPrecompute |
| ⑨-2 (5 件) | TestMLHealthMonitorStateRecovery 新規（_load_state 異常系）|
| ⑨-3 (6 件) | TestPhase90GammaDriftAnomalyInputs 新規（KS 異常入力）|
| ⑨-4 (6 件) | test_trigger_server.py 新規・TestPhase90GammaTriggerServer |
| ⑨ 補強 (2 件) | TestPhase90Gamma7PersistenceWarning（⑦×⑨ クロス連携）|
| 副次 | test_standard_analysis_tp_sl_count.py の時刻ハードコードバグ修正 |

合計 **25 件テスト追加**・8 ファイル変更（コード 4 + テスト新規 2 + テスト拡張 2）・+577/-15 行。

### Phase 90γ-⑧（バックテスト経路統合）の扱い

バックテスト自体が現在うまく動かないため **優先度低・スキップ候補**。プラン作成時にユーザーから「⑧ なしで良い」明示。ML 改善（Phase 90γ-④）の方が次の優先度として高い見込み。

### 同時エントリー仕様（5/29 ユーザー確認）

- 証拠金 24 万円 / 1 エントリー 0.015 BTC ≒ 17 万円 → エントリー後維持率 ~130%
- 追加エントリー予測維持率 76% < 強制ロスカット 50% +30pt = **安全バッファ**
- **Phase 50.4 維持率予測拒否（24h で 48 件）は仕様通りの正常動作**
- 同時エントリー数増加は証拠金増額が正攻法（予測ロジック調整は不要）

### 関連コミット

- `ea79e25e` feat: Phase 90γ-⑦ + γ-⑨ 観察可能化 + テストカバレッジ向上（2026-05-29 デプロイ済）
- `68cf68e3` fix: Phase 90γ-⑥ TP/SL confidence 属性名バグ + 観察可能化 3 件（2026-05-28 デプロイ済）
- `8bc2cd53` fix: Phase 90γ-③.5 + γ-⑤ + 分析スクリプト修正
- `1dbaf0ec` fix: Phase 90γ-③.4 Maker 観察可能化 + timeout 拡張

---

## 推論言語

このプロジェクトでは**日本語で推論**してください。コード内のコメント・変数名は英語のまま維持しますが、思考プロセス・計画・説明は日本語で行ってください。

---

## システム概要

| 項目 | 値 |
|------|-----|
| **対象** | bitbank信用取引・BTC/JPY専用 |
| **稼働** | 24時間（GCP Cloud Run）・5分間隔 |
| **月額コスト** | **現状: 約3,000円**（min_instances=1 常時稼働分が主因）/ Phase 88 I3 完了後の目標: **300-500円** |
| **証拠金** | 50万円 |
| **年利目標** | 10% (Phase 88 まで) / Phase 89-91 で **15-18%** / Phase 92 で **17-20%**（DD 10%許容） |
| **戦略数** | 6戦略（レンジ型4 + トレンド型2、CMFReversalがDonchianChannel置換） |
| **特徴量数** | **55 特徴量**（Phase 89-β/γ/δ で 37→55 拡張・Phase 92 で更なる拡張余地）|
| **MLモデル** | **ProductionEnsemble 4 モデル**（LGB 34%/XGB 34%/RF 17%/N-BEATS 15%・Phase 89-γ で N-BEATS 追加）|
| **ML方式** | **メタラベリング 2 クラス**（success/failure・Phase 90α）+ HMM レジーム検出（Phase 89-γ）+ Fear & Greed センチメント（LLM 不採用・Phase 89-β で確定）|

---

## クイックリファレンス

### 品質チェック（開発前後必須）

```bash
bash scripts/testing/checks.sh
# 期待結果: 全テスト成功・75%+カバレッジ・flake8/black/isort PASS
```

### システム実行

```bash
# ペーパートレード
bash scripts/paper/run_paper.sh

# 停止 / 状況確認
bash scripts/paper/run_paper.sh stop
bash scripts/paper/run_paper.sh status

# ライブトレード
python3 main.py --mode live
```

### GCP確認

```bash
# サービス稼働状況
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 \
  --format="value(status.conditions[0].status,status.url)"

# 最新リビジョン
TZ='Asia/Tokyo' gcloud run revisions list \
  --service=crypto-bot-service-prod \
  --region=asia-northeast1 --limit=3

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

### 分析コマンド

```bash
# ライブモード標準分析（24時間）
python3 scripts/live/standard_analysis.py
python3 scripts/live/standard_analysis.py --hours 48
python3 scripts/live/standard_analysis.py --quick

# バックテスト実行
bash scripts/backtest/run_backtest.sh

# バックテスト標準分析
python3 scripts/backtest/standard_analysis.py --from-ci
python3 scripts/backtest/standard_analysis.py results/backtest_result.json

# 戦略個別パフォーマンス分析（旧 strategy_performance_analysis.py の後継・Phase 61 統合）
python3 scripts/analysis/unified_strategy_analyzer.py --mode theoretical  # 理論分析（数秒）
python3 scripts/analysis/unified_strategy_analyzer.py --mode full         # 完全実証（3分）

# シグナルシミュレーション（Phase 75: 事後検証）
python3 scripts/analysis/signal_simulation.py                          # 直近7日全足
python3 scripts/analysis/signal_simulation.py --with-signals           # GCPシグナル検証
python3 scripts/analysis/signal_simulation.py --start 2026-03-25 --end 2026-04-01 --full
```

---

## アーキテクチャ概要

### ディレクトリ構成

```
src/
├── core/                   # 基盤システム
│   ├── orchestration/      # TradingOrchestrator
│   ├── config/             # 設定管理（thresholds.yaml）
│   ├── execution/          # 取引実行制御
│   ├── reporting/          # レポート生成
│   └── services/           # GracefulShutdown・MarketRegimeClassifier
├── data/                   # Bitbank API・キャッシュ
├── features/               # 特徴量生成（15指標）
├── strategies/             # 6戦略（Registry Pattern）
├── ml/                     # ProductionEnsemble（3モデル）
├── trading/                # 取引管理（5層分離）
│   ├── core/               # enums・types
│   ├── balance/            # MarginMonitor
│   ├── execution/          # ExecutionService・OrderStrategy・TPSLManager・PositionRestorer
│   ├── position/           # Tracker・Limits・Cleanup
│   └── risk/               # IntegratedRiskManager
└── backtest/               # バックテストシステム

tax/                        # 税務システム（SQLite・移動平均法）
scripts/                    # 運用スクリプト
config/core/                # 設定ファイル群
models/production/          # MLモデル（週次更新）
```

### データフロー

```
Bitbank API（15分足取得）
    ↓
特徴量生成（55 特徴量・Phase 89-β/γ/δ 拡張）
    ↓
ML予測（ensemble_full.pkl → 信頼度）
    ↓
レジーム判定（tight_range / normal_range / trending）
    ↓
動的戦略選択（レジーム別重みづけ適用）
    ↓
リスク評価（Kelly基準・ポジション制限）
    ↓
取引判断（レジーム別TP/SL適用）
    ↓
取引実行（完全指値・bitbank API）
```

### 設定管理

#### 1ファイル設定体系

| ファイル | 役割 |
|---------|------|
| `config/core/thresholds.yaml` | 全設定一元管理（環境設定 + パラメータ + 機能トグル） |

#### 設定参照パターン

```python
# ハードコード禁止
from src.core.config.threshold_manager import get_threshold

sl_rate = get_threshold("risk.sl_min_distance_ratio", 0.02)

# TP/SL設定はTPSLConfig定数を使用（文字列リテラル禁止）
from src.trading.execution.tp_sl_config import TPSLConfig

tp_ratio = get_threshold(TPSLConfig.TP_MIN_PROFIT_RATIO, 0.009)
sl_ratio = get_threshold(TPSLConfig.SL_MAX_LOSS_RATIO, 0.007)
regime_tp = get_threshold(TPSLConfig.tp_regime_path("tight_range", "min_profit_ratio"), 0.004)

# 機能トグル参照（thresholds.yaml の feature_flags セクション）
from src.core.config import get_features_config

features = get_features_config()
cooldown_enabled = features.get("trading", {}).get("cooldown", {}).get("enabled", True)
```

#### 動的戦略選択

```yaml
# thresholds.yaml
dynamic_strategy_selection:
  enabled: true
  regime_strategy_mapping:
    tight_range:    # レンジ型3戦略に集中
    normal_range:   # バランス型配分
    trending:       # トレンド型優先
    high_volatility: # 全戦略無効化
```

#### シークレット管理

- ローカル: `config/secrets/.env`（`.gitignore`で除外済み）
- GCP: Secret Manager（具体的バージョン番号使用。`key:latest`は禁止）

---

## 現行設定値

### 6戦略構成

| 区分 | 戦略名 | 核心ロジック |
|------|--------|-------------|
| **レンジ型** | BBReversal | BB位置主導 + RSIボーナス → 平均回帰 |
| **レンジ型** | StochasticDivergence | 価格とStochasticの乖離検出 → 反転 |
| **レンジ型** | ATRBased | ATR消尽率70%以上 → 反転期待（主力） |
| **レンジ型** | CMFReversal | CMF売り圧力減少→BUY / 買い圧力減少→SELL |
| **トレンド型** | MACDEMACrossover | MACDクロス + EMAトレンド確認 |
| **トレンド型** | ADXTrendStrength | ADX≥22 + DIクロス → トレンドフォロー |

### レジーム別重みづけ（Phase 85: trending全停止）

| 戦略 | tight_range | normal_range | trending |
|------|------------|-------------|---------|
| ATRBased | 0.35 | 0.25 | **0.0** |
| CMFReversal | 0.20 | 0.15 | **0.0** |
| BBReversal | 0.20 | 0.15 | **0.0** |
| StochasticReversal | 0.10 | 0.15 | **0.0** |
| ADXTrendStrength | 0.10 | 0.15 | **0.0** |
| MACDEMACrossover | 0.05 | 0.15 | **0.0** |

**Phase 85 trending全停止根拠**: 過去30日 trending 23件で全シナリオ赤字（TP1500/SL2000 floor 0.7%でも勝率45%・-8,500円）。設計思想「レンジ専用bot」と完全合致。

### レジーム別TP/SL設定

#### 平日

| レジーム | TP | SL | RR比 |
|---------|-----|-----|------|
| tight_range | 0.4% | 0.4% | 1.00:1 |
| normal_range | 1.0% | 0.7% | 1.43:1 |
| trending | 1.5% | 1.0% | 1.50:1 |

#### 土日（平日の約65%）

| レジーム | TP | SL |
|---------|-----|-----|
| tight_range | 0.25% | 0.25% |
| normal_range | 0.65% | 0.45% |
| trending | 1.0% | 0.65% |

### 固定金額TP/SL（Phase 85 + Phase 90δ + Phase 90ε 土日縮小）

> ⚠️ **Phase 90δ 重要訂正**: 下の「レジーム別TP/SL目標」は **実装上は未適用（dead code）**。`strategy_utils.py:518-531`（TP）/`440-447`（SL）で `confidence_based` が `regime_based` を常に上書きするため、**全エントリーが信頼度別TP/SLで決まる**（5/29 実証: TP適用99回が全て信頼度別、normal TP500 は0回）。`regime_based` は post_only 修正後の実 MFE データで要否を再評価予定。trending はそもそもエントリー停止（重み0）。

#### 信頼度別TP/SL目標（平日・実運用で常用・Phase 90δ で TP 引き下げ）

| 信頼度 | 閾値 | TP金額 | SL金額 | TP距離 | SL距離 | RR |
|--------|------|--------|--------|--------|--------|-----|
| 低 | <0.40 | **1,000円**（旧1,200）| 1,500円 | 0.67% | 0.70%(floor) | 0.96:1 |
| 高 | >=0.40 | **1,200円**（旧1,500）| 2,000円 | 0.79% | 0.94% | 0.83:1 |

**Phase 90δ TP引き下げ理由（2026-05-30）**: TP1500（距離0.956%）は遠く、+1000円付近で反転→TP未達→SL のケースが発生。TP を高1200/低1000 に下げて利確しやすくし、長時間保有→SL反転リスクを低減。SL はノイズ耐性維持のため据え置き（RR 1.02→0.83 を許容）。

**Phase 90ν SL引き下げ調査（2026-06-06・結論: SL2000据え置き）**: SLを2000→1750/1500に下げる余地を `full_entry_simulation.py`（SCENARIOS追加・90日277件）で時系列TP/SL先着検証。SL距離が縮むとBTC 15分足の一時的逆行(0.8〜1.0%)を吸収できず、**SL2000では持ちこたえてTPに到達していた取引がSL転落**する（90日 TP1200: SL2000 -198円 → SL1750 -270円 → SL1500 -219円／期待値/件・理論値）。**SL2000維持が最良・下げる余地なし**。現状の高勝率・低RR構造はSL2000が支えている。ただし**2026年6月の1ヶ月間ライブ運用を様子見し、7月初に実データで再判断する**。`scripts/analysis/full_entry_simulation.py --days N`（SCENARIOSにTP1200/1000×SL2000/1750/1500を内蔵）で再測定可。

#### 土日TP/SL（Phase 90ε・2026-05-30 追加）

| 区分 | TP金額 | SL目標 | 実TP距離 | 実SL距離 | 備考 |
|------|--------|--------|---------|---------|------|
| **土日（土・日 JST）** | **一律500円**（信頼度無関係）| 1,000円 → **floor 0.7% で実効≒1,733円** | **0.36%** | **0.70%** | 月曜持ち越し回避 |

**Phase 90ε 導入理由**: 日本の土日はBTCが特別イベント無き限り狭いレンジに収まりやすく、平日基準のTP1000-1200円（距離0.79%）では約定しないまま月曜を迎えるケースが多発。**土日のみ**（祝日は対象外・jpholiday 不採用）TP を一律500円（距離0.36%）に縮小しレンジ内利確を優先。SL は target1000円へ下げるが **A案（floor 0.7% 据え置き）** のため実効SL≒0.70%（平日2000円より縮小しつつノイズ耐性維持）。

**実装**: `strategy_utils.py` の固定金額 confidence_based 経路に JST土日判定 `is_weekend_jst`（`weekday()>=5`・Phase 83C のJST明示変換踏襲）を追加し、信頼度判定の**後に最終上書き**。設定は `thresholds.yaml` の `take_profit.fixed_amount.weekend`（target_net_profit:500）/ `stop_loss.fixed_amount.weekend`（target_max_loss:1000）でトグル化。ログに `(土日一律縮小)` ラベル出力で観察可能。

> 注: 既存 Phase 58.6 の `weekend_adjustment` + `regime_based.{regime}.weekend_ratio` は **%ベース（dead code）** にしか効かず実運用では無効。Phase 90ε はそれとは独立に、実際に動く固定金額経路へ土日縮小を導入したもの。

#### レジーム別TP/SL目標（⚠️ 現状未適用・参考）

| レジーム | TP目標 | SL目標 | 実TP距離 | 実SL距離 | 過去30日勝率 | 期待値/件 |
|---------|--------|--------|---------|---------|-------------|----------|
| **tight_range** | **1,500円** | **2,000円** | 0.70% | 0.86% | **67.9%** | **+362円** ✅ |
| **normal_range** | **500円** | **1,500円** | 0.23% | 0.70% | 75.0% | ±0円 |
| **trending** | エントリー停止 | エントリー停止 | - | - | - | 損失回避 |

**Phase 85 変更理由**:
1. **Phase 83B floor撤廃は虚像**: `sl_simulation.py` の手数料加算バグ（実コードは控除）で SL距離を約7倍過大評価。「勝率95.5%」は嘘
2. **真の運用シミュ実証**: bitbank API から過去30日全エントリー106件取得→TP/SL先着判定→**全シナリオ赤字**判明
3. **レジーム別が黒字化の鍵**: tight_range で TP1500/SL2000 + floor 0.7% で +362円/件、trendingは全シナリオ赤字
4. **設計思想と合致**: ユーザー「botはレンジ専用」設計 → trending時のエントリー停止が正解

**SL floor 0.7% 復活**:
- `min_distance.enabled: true`, `ratio: 0.007`
- BTC 15分足ノイズ幅（0.3-0.5%）を確実に超える SL距離 0.7%以上を強制
- Phase 83A-2 状態に近い（ただし TP/SL目標金額はレジーム別）

**Phase 86 TP/SL計算の単一実装**: `src/trading/execution/tpsl_calculator.py` の `TPSLCalculator` クラスがすべてのTP/SL計算箇所で使用される唯一の実装（旧4箇所分散を解消）。

TP計算式: `TP価格 = エントリー価格 ± (gross_needed / 数量)`
gross_needed: `TP目標 + エントリー手数料(0.1%) + 決済手数料(Maker 0%想定で 0)` （Phase 86: entry_fee加算バグ修正）

SL計算式: `SL価格 = エントリー価格 ∓ (SL距離 / 数量)`
SL距離: `max((SL目標 - エントリー手数料(0.1%) - 決済手数料(Taker 0.1%)) / ポジションサイズ, エントリー価格 * 0.007)`

実例（amount 0.015 BTC、BTC 12.84M円、tight_range TP1500/SL2000）:
- TP距離 = (1500+193+0)/0.015 = **112,840円 = 0.879%** （Phase 86: +13%拡大）
- SL距離 = max((2000-193-193)/0.015, 12.84M×0.007) = max(107,613円, 89,880円) = **107,613円 = 0.838%**

### 手数料設定（2026年2月2日改定）

| 項目 | エントリー | TP決済 | SL決済 |
|------|----------|--------|--------|
| 手数料率 | 0%（Maker成功時）/ 0.1%（Taker） | 0%（Maker） | 0.1%（Taker） |
| TP/SL計算時 | 0.1%（Taker想定） | 0%（Maker想定） | 0.1%（Taker想定） |

### SL設定

| 設定 | 値 |
|------|-----|
| 注文タイプ | `stop`（成行）（Phase 80: stop_limit→stopロールバック、Phase 69.8の教訓再確認） |
| slippage_buffer | 0.8%（Phase 69.6設定維持） |
| skip_bot_monitoring | true |
| stop_limit_timeout | 900秒（Phase 69.3: 300→900秒） |
| 固定金額SL | 1,200-1,500円（Phase 83A-2 信頼度別）+ floor 0.7%強制 |
| 日次損失上限 | 5,000円（1%） |
| 週次損失上限 | 20,000円（4%） |
| 連敗サイズ縮小 | 5回:50% / 6回:40% / 7回:25% / 8回:停止 |
| 同方向ポジション上限 | **1件**（Phase 85: 2→1 ロールバック・Phase 84で損失40%増幅） |

### Maker戦略（Phase 90γ-③.5 仕様訂正・Phase 90δ post_only 修正）

| 設定 | 値 |
|------|-----|
| **post_only パラメータ名** | **Phase 90δ**: `params["post_only"]`（snake_case）。旧 `postOnly`（camelCase）は ccxt 4.5.1 が変換せず bitbank に無視され、全注文が通常指値化＝テイカー約定していた致命バグを修正（`bitbank_client.py:840`）|
| **約定種別の記録** | **Phase 90δ**: `order_strategy._resolve_fill_type` が fetch_my_trades から実 `taker_or_maker`/`fee` を取得。旧実装は「Maker(0%)」決め打ちで虚偽記録だった。taker 約定時は WARNING `Phase 90δ: post_only指定だがTaker約定` を出力 |
| 価格配置 (spread≥2円) | best_bid + improvement / best_ask - improvement（queue 先頭側に並ぶ既存戦略）|
| 価格配置 (spread<2円) | **Phase 90γ-③.5**: best_bid / best_ask 直接配置（queue 末尾待機戦略・bitbank post_only は反対側板マッチ時のみ cancel という公式仕様に基づく） |
| improvement | max(1, min(int(spread×0.3), spread-1))（Phase 90γ-③.2 で ×0.1→×0.3）|
| spread<=0円（クロス板） | 配置中止（異常検出） |
| timeout | 120秒（Phase 90γ-③.4: 60→120）、リトライ 5 回（Phase 90γ-③.4: 3→5）|
| retry_interval_ms | 1500（Phase 90γ-③.4: 2000→1500）|
| Maker 失敗時 fallback | Phase 90γ-③.3 ML信頼度動的判定：confidence≥0.65 で Taker 進行、<0.65 でスキップ |
| 注: Phase 79 コメント | 「best_bid 直接配置で必ず reject」は仕様誤読・Phase 90γ-③.5 で訂正 |

### ML品質フィルタ（Phase 85 再学習）

メタラベリング（Triple Barrier Method）方式。MLは方向予測ではなく、戦略の出した取引が成功するかを判定。
Phase 85: tight基準 TP1500/SL2000 + floor 0.7%に合わせ再学習（meta_tp_ratio 0.007 / meta_sl_ratio 0.0086）。

| 閾値 | 値 | 動作 |
|------|-----|------|
| accept_threshold | **0.58**（維持） | p(1)≥0.58 → 取引承認 |
| reject_threshold | **0.42**（維持） | p(1)<0.42 → 拒否 |
| uncertain_penalty | **0.5**（維持） | 中間帯(0.42-0.58)は信頼度を50%縮小 |
| high_confidence_failure_threshold | **0.65**（Phase 84） | ml_pred==0 かつ confidence≥0.65 で拒否（旧ハードコード0.55） |

**Phase 84 補足**: confidence は `max(p_0, p_1)`（class 1確率ではない）。ml_pred==0 + confidence=0.808 なら失敗確信80.8%＝正常な拒否動作。

**再学習後モデル性能**（2026/5/11学習、Phase 85）:
- CV F1: LGB 0.602±0.051 / XGB 0.577±0.073 / RF 0.571±0.074（Phase 83A-3とほぼ同等）
- 学習サンプル: 35,036件（365日分、2025-05-11〜2026-05-10）
- 信頼度分布: LGB mean=0.633 / XGB mean=0.740 / RF mean=0.677
- 最適閾値: 0.50 (F1=0.5021)
- SMOTE適用: 29,780 → 41,312サンプル

**Phase 85採算ライン勝率**（レジーム別）:
- tight_range (実RR 0.81:1): 採算 55%、実証67.9%で大幅余裕 ✅
- normal_range (実RR 0.16:1): 採算 86%、実証75%でやや厳しい（薄利OK狙い）

**モデルバックアップ**:
- `models/production/ensemble_{full,basic}.phase82.pkl.bak`: Phase 82モデル
- `models/production/ensemble_{full,basic}.phase83a.pkl.bak`: Phase 83A-3モデル
- `models/production/ensemble_{full,basic}.phase84.pkl.bak`: Phase 84モデル

---

## 開発原則

### 品質基準

- **開発前後**: `bash scripts/testing/checks.sh`必須実行
- **テスト**: 全テスト100%成功維持
- **カバレッジ**: 75%以上維持
- **コード品質**: flake8 / black / isort通過必須
- **CI/CD**: GitHub Actions自動品質ゲート

### コーディング規約

- **設定**: ハードコード禁止・`get_threshold()`パターン使用
- **ログ**: JST時刻・構造化ログ
- **テスト**: 単体・統合・エラーケーステスト完備
- **アーキテクチャ**: レイヤードアーキテクチャ遵守

### GCP特有の制約

| 制約 | 対策 |
|------|------|
| gVisor fork()制限 | RandomForest `n_jobs=1`固定 |
| Cloud Runタイムアウト | `signal.alarm`無効化 |
| Container再起動 | 起動時ポジション復元（実ポジションベース） |

### Git運用規則

| 規則 | 内容 |
|------|------|
| **全体コミット必須** | `git add .`を使用（個別add禁止） |
| **コミット前確認** | `git status`必須 |

```bash
git status && git add . && git commit -m "..." && git push origin main
```

---

## トラブルシューティング + ドキュメント索引

### よくあるエラー

| エラー | 対策 |
|--------|------|
| `'BitbankClient' has no attribute 'get_active_orders'` | `fetch_active_orders`を使用 |
| Container exit(1) | GCP制約対策確認（n_jobs=1, signal.alarm無効化） |
| bitbank 50062「保有建玉数量超過」 | 既存TP/SL注文キャンセル後に成行決済（Phase 68.2で修正済み） |
| bitbank 50026「該当注文なし」 | 孤児SLキャンセル時の50026は「注文が既に消滅＝解消済み」で正常。Phase 90λ で成功扱い（CRITICAL化しない） |

> **デプロイのタイミング**: 可能な限りフラット（ポジション0）時に実施する。建玉保有中のデプロイは再起動時のポジション復元で一時的に孤児ポジ/孤児SL検出が集中する（最終的に自己解消・実害なし。Phase 90λ 改修後はノイズも軽減）。

### デバッグコマンド

```bash
# importエラー確認
python3 -c "import sys; sys.path.insert(0, '.'); from src.core.logger import CryptoBotLogger"

# 設定整合性確認（checks.sh [5/12] で実施・dev_check.py は Phase 40.6 で統合廃止）
bash scripts/testing/checks.sh

# GCPエラーログ
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20
```

### ドキュメント索引

| カテゴリ | ファイル | 内容 |
|---------|---------|------|
| **運用** | [統合運用ガイド.md](docs/運用ガイド/統合運用ガイド.md) | デプロイ・日常運用・緊急対応 |
| **運用** | [GCP運用ガイド.md](docs/運用ガイド/GCP運用ガイド.md) | IAM権限・リソースクリーンアップ |
| **運用** | [システムリファレンス.md](docs/運用ガイド/システムリファレンス.md) | 仕様+実装の統合リファレンス |
| **運用** | [bitbank_APIリファレンス.md](docs/運用ガイド/bitbank_APIリファレンス.md) | API仕様・署名方式 |
| **運用** | [税務対応ガイド.md](docs/運用ガイド/税務対応ガイド.md) | 確定申告・移動平均法 |
| **履歴** | [SUMMARY.md](docs/開発履歴/SUMMARY.md) | 全Phase総括（Phase 1-77） |
| **履歴** | [Phase_71-81.md](docs/開発履歴/Phase_71-81.md) | 最新Phase詳細 |
| **計画** | [ToDo.md](docs/開発計画/ToDo.md) | 開発計画 |
