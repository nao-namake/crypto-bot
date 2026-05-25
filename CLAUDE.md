# CLAUDE.md

## しおり（現在地）

| 項目 | 値 |
|------|-----|
| **現在Phase** | **Phase 90γ-③.3 (ML 信頼度ベース動的 Taker fallback) 完了・本番デプロイ済（2026-05-25）** |
| **直前の作業** | 2026-05-25 ライブ分析 24h で **エントリー 3 件すべて Taker（Phase 86 警告）** を発見。詳細調査で「Phase 90γ-③.2 で実装した Maker タイムアウト対策は機能している（タイムアウトログ 0 件）」が、**真因は BTC/JPY スプレッド 1 円の時間帯にエントリー集中（Phase 79「スプレッド狭小」ログ 17 件/24h）** と判明。spread=1 円では best_bid+1=best_ask で post_only reject が物理的に避けられない。対策として ML 信頼度ベース動的 Taker fallback を実装：confidence >= 0.65 で Taker 進行、< 0.65 でエントリースキップ |
| **次の予定** | 7 日観察で Maker / Taker 進行 / スキップの比率推移と手数料コスト削減効果を測定 → Phase 90γ-④ (ML 品質改善・Optuna 50→100 + Focal Loss + Calibration 修正) 着手 |
| **🎯 Phase 90γ-③.3 最重要発見** | Phase 90γ-③.2 デプロイ後の Maker タイムアウト 0 件で「リトライ系の修正は完了」だが、Taker 100% が継続。GCP ログ 17 件すべて `スプレッド狭小(1円) - Maker 配置不可`。BTC/JPY 板の物理的制約（spread=1 円では post_only 不可能）に対し、無条件 Taker fallback では 0.1% 手数料を毎回支払う構造的問題。ML 信頼度判定で「高品質取引は手数料払ってでも取る・低品質は機会損失より手数料回避」というトレードオフを明示化 |
| **🎯 Phase 90γ-③.2 最重要発見** | GCP ログ 7d 実測で Taker フォールバック 136 件/7日（スプレッド狭小 68 + Maker タイムアウト 68）を確認。コード解析で 3 つのボトルネック特定：① `improvement = max(1, min(spread×0.1, spread-1))` がほぼ常に 1 円張り付き ② `price_adjustment_tick: 100` 円が BTC/JPY spread 範囲外に乖離 ③ `retry_interval_ms: 5000` で 15 秒消費。3 値を同時修正（×0.3 / tick 5 / interval 2000ms）|
| **🎯 Phase 90γ-③.1 最重要発見** | Phase 90γ-③ で価格スケール連動の特徴量（OHLCV/MA/MACD 系）は exclude したが、**0-1 / 0-100 / -1〜+1 に自己正規化されたオシレーター類が漏れていた**。should_emergency_stop からは drift OR 撤廃済（Phase 90γ-③）なので**実害ゼロ**だが、警告ログが過大で観察ノイズに。さらに外部 bitbank API + ADX 計算で **「24h+ 取引なし」はトレンド相場が本物**と確認（24h 平均 ADX=63.0・24h 全てで ADX>30）。Bot 判定（trending = エントリー停止）は一般指標 ADX とも一致 |
| **🎯 Phase 90γ-③ 最重要発見** | **Drift 連続検出 (consecutive=457) → should_emergency_stop True → 取引拒否 91%（8h で 493/544 拒否）+ ダミー secret で Auto Retraining HTTP 401 リトライ 306 件/8h** という連鎖。Phase 90γ-① で見落とした特徴量（macd / close_ma_10/20 / volume_ema / funding/cross_asset 系）が drift 判定対象として残っていた。drift OR 連動撤廃 + exclude_features 大幅拡張で**運用層を完全正常化** |
| **🎯 Phase 90γ-② 最重要発見** | `trigger_server.py:112` が `cmdline_mode="trigger"` を渡すが `config/__init__.py:90` の `valid_modes` に "trigger" がなく ValueError → EMERGENCY_STOP → /health 503 → トラフィック流入停止。env MODE による runtime 判定方式に切替（Option D）|
| **🎯 Phase 90γ-① 最重要発見** | Drift 検出が「reference 初回固定 + 価格絶対値 (OHLCV/MA/BB) を比較対象」という構造的欠陥で 440 回連続発火。exclude_features + 168h reference reset + significant_feature_min 厳格化で対処（ただし新特徴量への漏れが Phase 90γ-③ で対処された）|
| **🎯 Phase 90β 最重要発見** | `executor.py:1084` で必要証拠金 = `order_total / 2`（50% 固定）と bitbank 動的マージン 30-50% に未追従 + `limits.py` に反対方向制限が実装されていなかった（同方向のみ）。両方の独立修正により 1 件ずれても安全側に倒れる設計に |
| **🎯 Phase 90α 最重要発見** | Phase 89 までの学習と運用がセマンティック大破綻（CI workflow に `--meta-label` フラグなし）。`--meta-label` フラグ追加（6 行）で macro F1 が **0.347 → 0.546（LGB CV）**に改善・naive baseline +0.14 で真の予測力獲得 |
| **Phase 87 達成** | Critical 5 + High 10 全完了（本番デプロイ済） |
| **Phase 88 達成** | I1-I4 GCPコスト 4件 + H11 孤児SL + M1-M5 + L1-L3 |
| **Phase 89-α/β/γ/δ 達成** | gating + Fractional Kelly + Drift 検出 + N-BEATS + HMM + VPIN + WebSocket + BTC-ETH 相関 + 特徴量 37→55 |
| **Phase 90α 達成** | メタラベリング有効化 (`--meta-label` 6 行追加) で macro F1 0.347 → 0.546 |
| **Phase 90β 達成** | 本番運用リスク 7 件根本修正（反対方向ポジ制限・必要証拠金率設定経由化・予測トレース・Auto Retraining env/secrets 等） |
| **Phase 90γ-① 達成** | Drift 検出構造バグ修正（OHLCV 系除外 + 168h reference reset + significant_feature_min 厳格化）+ レビュー修正 3 件（drift カウンタクリア + 実在名整理 + reset WARNING 化）|
| **Phase 90γ-② 達成** | trigger モード EMERGENCY_STOP 修正（env MODE 判定）+ bitbank 50062 ポジション反映待ち（`_wait_position_reflected`）+ 孤児SL 自動クリーンアップ確認 |
| **Phase 90γ-③ 達成** | drift OR 撤廃で取引拒否 91%→0 系統 + ダミー token (DUMMY_ プレフィックス) skip で 401 ループ解消 + exclude_features 14→40 個拡張 (macd/close_ma/volume_ema/funding/cross_asset/VPIN/HMM 系) + significant_feature_min 10→5 + enable_auto_retraining false |
| **Phase 90γ-③.1 達成** | exclude_features 43→59 個拡張（オシレーター系 9 個 + volume_lag 3 個 + returns 4 個）+ min_instances 設定整合（thresholds.yaml + gcp_config.yaml いずれも 1→0、CI workflow MIN_INSTANCES="0" と一致）|
| **Phase 90γ-③.2 達成** | Maker 戦略の Taker フォールバック削減：improvement spread×0.1→×0.3 + price_adjustment_tick 100→5 円 + retry_interval_ms 5000→2000 ms（既存テスト 2 件更新で対応）|
| **Phase 90γ-③.3 達成** | ML 信頼度ベース動的 Taker fallback：confidence >= 0.65 で Taker 進行・< 0.65 でエントリースキップ（thresholds.yaml に taker_fallback_confidence_threshold: 0.65 追加 + テスト 3 件新規追加）|
| **特徴量数** | 37 → **55**（Phase 89-β/γ/δ で 6 カテゴリ追加）|
| **ML モデル** | 3 → **4**（N-BEATS 追加・LGB 34%/XGB 34%/RF 17%/N-BEATS 15%） |
| **🎉 v8e (2 クラスメタラベリング) macro F1** | LGB CV 0.546 / Test 0.486・XGB CV 0.459・RF CV 0.530・N-BEATS CV 0.514 Test 0.524（naive 0.41 比 **+0.10〜+0.14 で真の予測力獲得**）|
| **本番効果（5/25 04:25 ライブ分析 24h 時点・Phase 90γ-③.2 デプロイ後）** | Drift 検出 **0 件/24h**（Phase 90γ-③.1 完全成功）/ Maker タイムアウト **0 件**（Phase 90γ-③.2 リトライ系修正成功）/ エントリー **3 件・勝率 100% / +¥1,500**（取引機能再開）/ Phase 86 Taker 率 100%（Phase 90γ-③.3 で対処済・spread<2 円市場特性に対応）|
| **追加課金** | **ゼロ**（GPU 不採用 / LLM 不採用 / 全て無料 API） |
| **GCP 月額** | 現状 ¥3,000 → Stage 1+3 後 **¥1,400-1,700 見込み**（実測待ち） |
| **最終更新** | 2026年5月25日 - Phase 90γ-③.2 (Maker タイムアウト対策) + Phase 90γ-③.3 (ML信頼度ベース動的 Taker fallback) 実装完了 |

> **🚀 セッション再開時は `docs/開発計画/ToDo.md` の「セッション再開時の手順」セクションを最優先で確認**
>
> 詳細計画: `docs/開発計画/ToDo.md` / `~/.claude/plans/c-gleaming-ladybug.md`（Phase 89 修正 + N-BEATS 完全版プラン）
> 開発履歴: `docs/開発履歴/SUMMARY.md`（Phase 1-77）、`docs/開発履歴/Phase_71-81.md`、`Phase_82.md`〜`Phase_89.md`

---

## 🚀 セッション再開時の最優先タスク（2026-05-25 時点・Phase 90γ-③.3 完了 → Maker / Taker 比率改善検証フェーズ）

**Phase 90γ シリーズ (γ-①・γ-① レビュー・γ-②・γ-③・γ-③.1・γ-③.2・γ-③.3) 全工程完了・本番デプロイ済**。
7 日観察で Maker / Taker 進行 / スキップの比率推移と手数料コスト削減効果を測定 → Phase 90γ-④ (ML 品質改善) 着手判断。

### Phase 90γ シリーズ修正サマリ

#### γ-③.3 (コミット `a6b5fe1e`): ML 信頼度ベース動的 Taker fallback
| 修正 | 内容 |
|---|---|
| Maker 失敗時の動的判定 | `executor.py:302-323` の Taker fallback を ML 信頼度で動的判定。confidence_level >= 0.65 → Taker 進行、< 0.65 → エントリースキップ |
| 設定追加 | `thresholds.yaml` に `taker_fallback_confidence_threshold: 0.65` 追加（既存 `high_confidence_failure_threshold` と整合）|
| テスト追加 | `TestPhase90Gamma33MakerFallbackConfidence` クラスで 3 テスト追加（高信頼度→Taker / 低信頼度→スキップ / fallback無効→中止）|
| 期待効果 | **手数料コスト 30-50% 削減**（低信頼度 Maker 失敗をスキップ）/ 高品質取引は機会喪失ゼロ |
| 発見経緯 | 5/25 ライブ分析で「Phase 86 Taker 率 100%」発見 → 24h で Phase 79 ログ 17 件（すべて spread<2 円）= BTC/JPY 板の物理的制約 → 無条件 Taker fallback の構造的問題と判定 |

#### γ-③.2 (コミット `6996737a`): Maker 戦略の Taker フォールバック削減
| 修正 | 内容 |
|---|---|
| improvement 拡大 | `order_strategy.py:499` spread×0.1 → spread×0.3（spread=10 円で改善 1→3 円・約定確率向上）|
| price_adjustment_tick 縮小 | 100 → 5 円（リトライ 3 回で 300 円乖離 → 15 円に・BTC/JPY spread 範囲内維持）|
| retry_interval_ms 短縮 | 5000 → 2000 ms（15 秒消費 → 6 秒・タイムアウト 60 秒内に余裕）|
| テスト更新 | `test_buy_wide_spread` / `test_sell_wide_spread`（spread=100 円で improvement 期待値 10→30）|
| 効果（5/25 ライブ分析時点） | **Maker タイムアウト 0 件/24h**（リトライ系修正は完全成功）|
| 残課題 | spread<2 円由来の Taker は Phase 90γ-③.2 では未対応 → γ-③.3 で対処 |

#### γ-③.1 (コミット `0c40575b`): Drift exclude_features オシレーター漏れ修正 + min_instances 整合
| 修正 | 内容 |
|---|---|
| exclude_features 拡張 | 43→59 個。Phase 90γ-③ で漏れた **正規化済みオシレーター系** を追加（rsi_14, rsi_lag_1, adx_14, plus_di_14, minus_di_14, cci_20, cmf_20, bb_position, channel_position）+ volume_lag_1/2/3 + returns_1/2/3/10 |
| min_instances 設定整合 | `thresholds.yaml.cloud_run.min_instances` 1→0、`gcp_config.yaml.deployment_modes.live.min_instances` 1→0（実デプロイ実態 = Phase 88 I3 で MIN_INSTANCES="0" と一致）|
| 効果（24h 観察期待） | **Drift 検出 545 件/24h → 数十件以下に抑制**（should_emergency_stop からは drift OR 撤廃済なので**実害ゼロ**だったが警告ログを正常化）|
| 副次成果 | 外部 bitbank API + ADX 計算で「24h+ 取引なし」は trending 相場が本物と確認（24h 平均 ADX 63.0・24h 全てで ADX>30）。Bot 判定（trending = エントリー停止）は一般指標 ADX と一致 |

#### γ-① (コミット `6aa26ea9`): Drift 検出構造バグ修正
| 修正 | 内容 |
|---|---|
| 価格絶対値除外 | `exclude_features` (OHLCV/BB/EMA/ATR/Donchian/macd_signal/histogram 14 個) を drift 比較対象から除外 |
| Rolling Reference | reference を「初回固定」→「168h で自動 reset」(古い分布との永続乖離防止) |
| 厳格化 | `significant_feature_min` 3 → 10 (少数特徴量での誤発火抑制) |
| 効果 | **Drift 検出 91 件/24h → 0 件/24h（完全沈静化）** |

#### γ-① レビュー修正 (コミット `8c55dc71`): 3 件のレビュー指摘
| 修正 | 内容 |
|---|---|
| Reset 時 drift カウンタクリア | reset 時に `consecutive_drift_detections` / `last_drift_at` を仕切り直す（reset 直後の emergency_stop 誤発火防止）|
| exclude_features 整理 | feature_generator.py の実生成名と照合・実在しない 10 個を削除、`donchian_high_20/low_20`・`macd_signal/histogram` を追加 |
| Reset ログ WARNING 化 | reference_expired 時のログを INFO → WARNING（本番 Cloud Logging で観測可能化）|

#### γ-② (コミット `488c820f`): 致命的バグ修正 + 運用品質改善
| 修正 | 内容 |
|---|---|
| trigger モード EMERGENCY_STOP 解消 | `trigger_server.py:112` `cmdline_mode="trigger"` → `"live"` + `orchestrator.py` で env MODE 判定方式に変更（Option D）|
| bitbank 50062 対処 | `tp_sl_manager._wait_position_reflected()` 追加・TP/SL 配置直前で最大 5 秒ポジション反映待機 |
| 孤児SL クリーンアップ | `scripts/maintenance/cleanup_orphan_orders.py` 新規（ドライラン/--apply 対応）|

#### γ-③ (コミット `e529909e`): 取引拒否 91% 解消 + Drift 検出再設計
| 修正 | 内容 |
|---|---|
| should_emergency_stop から drift OR 撤廃 | `ml_health_monitor.py:162` 連続失敗のみで判定。drift は警告 + Auto Retraining trigger のみに使用 |
| Auto Retraining ダミー token 検出 | `ml_health_monitor.py:441` 付近 `token.startswith("DUMMY_")` で skip + thresholds.yaml `enable_auto_retraining: false` |
| exclude_features 大幅拡張 | 14→40 個（macd/close_ma_*/volume_ema/funding/cross_asset/VPIN/HMM/時刻系を網羅）+ significant_feature_min 10→5 |

### セッション再開時 Step 1: 24h 監視（5 分）

```bash
# ライブ運用 24h 分析（Phase 86-90γ 全カバー）
venv/bin/python3 scripts/live/standard_analysis.py --hours 24

# Phase 88 I3 EMERGENCY_STOP の消失確認（期待: 0 件）
gcloud logging read 'textPayload=~"Phase 88 I3.*EMERGENCY_STOP|無効なモード"' --freshness=24h | wc -l

# Phase 89-β Drift 検出件数（Phase 90γ-③.1 後の期待: 0 件継続）
gcloud logging read 'textPayload=~"Phase 89-β: Drift 検出"' --freshness=24h | wc -l

# Phase 90γ-③.3 動的判定ログ（Taker 許可 vs スキップの内訳）
echo "Taker 許可:" && gcloud logging read 'textPayload=~"Phase 90γ-③.3.*Taker許可"' --freshness=24h | wc -l
echo "スキップ:"   && gcloud logging read 'textPayload=~"Phase 90γ-③.3.*スキップ"' --freshness=24h | wc -l

# Maker 約定成功（spread>=2 円で Phase 90γ-③.2 効果が出れば増えるはず）
gcloud logging read 'textPayload=~"Maker約定成功"' --freshness=24h | wc -l

# Phase 50.4 拒否件数（既存ポジ保有時の追加発注ブロックなので 0-数件が想定範囲）
gcloud logging read 'textPayload=~"Phase 50.4: 維持率80%未満予測"' --freshness=24h | wc -l

# bitbank 50062 エラー件数（期待: 0 件・Phase 90γ-② P1 効果）
gcloud logging read 'textPayload=~"50062"' --freshness=24h | wc -l

# Auto Retraining HTTP 401 件数（期待: 0 件・Phase 90γ-③ ダミー token skip 効果）
gcloud logging read 'textPayload=~"HTTP 401|DUMMY_"' --freshness=24h | wc -l
```

### セッション再開時 Step 2: SLMonitor DRY_RUN→false 切替判定（7 日後・既存）

```bash
# 誤発火率算出
venv/bin/python3 scripts/analysis/sl_monitor_validator.py --days 7

# 終了コード 0 (SAFE) なら config/core/thresholds.yaml:806 で dry_run: false に切替
```

### セッション再開時 Step 3: Phase 90γ-④ 着手判断

7 日観察結果に基づき以下を判定:
- Maker 約定数 増 / Taker 許可数 ≧ スキップ数 → Phase 90γ-③.2/③.3 完全成功 → Phase 90γ-④ (ML 改善) 着手
- スキップが過剰（取引機会喪失大）→ taker_fallback_confidence_threshold を 0.65 → 0.60 に緩和検討

Phase 90γ-④ 候補（Phase 90α からの継続課題・推奨「案 1: 短期 ROI 最大化」）:
1. **Optuna 試行数増** (50→100) [最優先・容易・1 行変更で XGB 過学習対策・期待 +0.02-0.05]
2. **Focal Loss** (LGB/XGB) [容易・SMOTE と相補・期待 +0.01-0.03]
3. **Isotonic Calibration 修正**（v8e で失敗・`ProductionEnsemble` に `fit` メソッド不足）[容易・品質フィルタ精度向上]
4. **CatBoost 追加** or RF 置換: ensemble 多様性向上 [中・コンテナ肥大化 30-40%]
5. **Multi-Level VPIN + OFI 拡張**: マイクロ構造特徴強化 [困難・WebSocket 統合必要]
6. **ADX 遅行性対策（要慎重検証）**: 価格は収束していても ADX が高止まりして trending 継続判定する問題。Phase 85 全停止根拠（過去 30 日 trending 23 件全シナリオ赤字）との両立検証が必須。

### Phase 90γ 異常時のロールバック

```bash
# 個別コミット revert
git revert a6b5fe1e  # γ-③.3 取消（ML 信頼度ベース動的 fallback）
git revert 6996737a  # γ-③.2 取消（Maker タイムアウト対策）
git revert 0c40575b  # γ-③.1 取消（exclude_features 拡張 + min_instances 整合）
git revert e529909e  # γ-③ 取消
git revert 488c820f  # γ-② 取消
git revert 8c55dc71  # γ-① レビュー修正取消
git revert 6aa26ea9  # γ-① 取消
git push origin main

# Phase 90γ-③.3 の閾値だけ無効化（コード変更は残す・旧挙動と同等）
yq -i '.order_execution.maker_strategy.taker_fallback_confidence_threshold = 0.0' config/core/thresholds.yaml
git add config/core/thresholds.yaml && git commit -m "rollback: Phase 90γ-③.3 動的判定無効化" && git push origin main

# Drift 検出設定だけ旧に戻す（exclude_features 無効化）
yq -i '.ml.drift.exclude_features = []' config/core/thresholds.yaml
yq -i '.ml.drift.significant_feature_min = 3' config/core/thresholds.yaml
git add config/core/thresholds.yaml && git commit -m "rollback: Phase 90γ-① 設定無効化" && git push origin main
```

### Phase 90γ シリーズ関連ファイル

- 計画書: `~/.claude/plans/gcp-humming-bear.md`（Phase 90γ-② 計画含む全体記録）/ `~/.claude/plans/gcp-silly-frog.md`（Phase 90γ-③.1 → γ-③.2 → γ-③.3 と上書き使用）
- 詳細記録: `docs/開発履歴/Phase_90.md` 末尾「Phase 90γ-③.1 / γ-③.2 / γ-③.3」セクション
- 新規スクリプト: `scripts/maintenance/cleanup_orphan_orders.py`
- 修正済本体:
  - γ-①: `src/core/orchestration/ml_health_monitor.py` `config/core/thresholds.yaml`
  - γ-②: `src/core/orchestration/trigger_server.py` `src/core/orchestration/orchestrator.py` `src/trading/execution/tp_sl_manager.py`
  - γ-③.1: `config/core/thresholds.yaml`（exclude_features 拡張）`config/infrastructure/gcp_config.yaml`（min_instances 整合）
  - γ-③.2: `config/core/thresholds.yaml`（retry_interval_ms / price_adjustment_tick）`src/trading/execution/order_strategy.py:499`（improvement 拡大）
  - γ-③.3: `src/trading/execution/executor.py:302-323`（ML 信頼度ベース動的 fallback）`config/core/thresholds.yaml`（taker_fallback_confidence_threshold 追加）
- 修正済テスト: `tests/unit/core/orchestration/test_ml_health_monitor.py` (9 件) `tests/unit/core/orchestration/test_orchestrator.py` (2 件) `tests/unit/trading/execution/test_tp_sl_manager.py` (4 件) `tests/unit/trading/execution/test_order_strategy.py` (γ-③.2 で 2 件更新) `tests/unit/trading/execution/test_executor.py` (γ-③.3 で 3 件新規追加)

### コミット履歴（Phase 90γ 全体）

```
a6b5fe1e fix: Phase 90γ-③.3 ML信頼度ベース動的 Taker fallback
6996737a fix: Phase 90γ-③.2 Maker 戦略の Taker フォールバック削減
0ea1d22b docs: Phase 90γ-③.1 完了に伴うドキュメント更新
0c40575b fix: Phase 90γ-③.1 Drift 検出オシレーター漏れ修正 + min_instances 整合
e5e13e20 docs: Phase 90γ-③ 完了に伴うドキュメント更新
e529909e fix: Phase 90γ-③ 取引拒否 91% 解消 + Drift 検出再設計
2d0f5d24 docs: Phase 90γ シリーズ完了に伴うドキュメント整備 + 軽微な不備 2 件修正
488c820f fix: Phase 90γ-② 致命的バグ修正 + 運用品質改善
8c55dc71 fix: Phase 90γ-① レビュー指摘の 3 件修正
6aa26ea9 fix: Phase 90γ-① Drift 検出構造バグ修正 (440 回連続発火問題)
01d57b90 feat: Phase 90β 構造的問題 7 件根本修正
```

---

## 🔍 過去のセッション再開時の最優先タスク（2026-05-17 時点・Phase 90α 完了 → 実機観察フェーズ）— 履歴用

**Phase 90α (v8e メタラベリング有効化) 本番デプロイ完了**。実機 1 週間観察フェーズに突入。

### 背景：Phase 90α の根本発見と修正

`config/core/thresholds.yaml:142` で `ml.mode: quality_filter`（2 クラスメタラベリング前提）に設定されているのに、CI workflow `.github/workflows/model-training.yml` に `--meta-label` フラグがなかった → **学習は 3 クラス方向予測 / 運用は 2 クラス品質判定として誤解釈**という致命的セマンティック大破綻。`prediction == 0 (SELL方向)` を「低品質」、`prediction == 1 (HOLD方向)` を「高品質」と読んでいた。

**修正は 2 ファイル × 計 6 行追加のみ**:
- `.github/workflows/model-training.yml`: `--meta-label --meta-tp-ratio 0.007 --meta-sl-ratio 0.0086` 追加
- `scripts/ml/run_local_training.sh`: 同上 + caffeinate スリープ防止ラップ

下流コード（quality_filter / ensemble / fallback / trading_cycle_manager）は最初から 2 クラスメタラベリング対応済みのため**互換性破壊ゼロ**。

### Step 1: 毎日チェック（5 分）

```bash
# ライブ運用 24h 分析（Phase 86-90 全カバー・Phase 90α 監視追加済）
venv/bin/python3 scripts/live/standard_analysis.py --hours 24

# 異常ログのスキャン
gcloud logging read 'resource.type=cloud_run_revision AND severity>=ERROR' --freshness=24h --limit=20

# ML 品質フィルタ動作確認（accept_threshold で reject されたケース数）
gcloud logging read 'textPayload=~"quality_filter.*reject|低品質"' --freshness=24h | wc -l
```

**ライブ分析の Phase 90α 監視項目**（standard_analysis.py で自動レポート出力）:
- **品質フィルタ accept/reject 比率**: reject > 70% で過剰防衛警告
- **高品質/低品質ラベル分布**: 旧 3 クラス方向予測ラベル残存検出（v8e モデル未配備の疑い）
- **モデル整合性**: DummyModel フォールバック検知（サーキットブレーカー作動候補）

### Step 2: 1 週間後の総合評価（30 分）

```bash
# 1 週間分析
venv/bin/python3 scripts/live/standard_analysis.py --hours 168

# 期待値 vs 実測比較（Phase 90α 目標）
# - PF: 0.8-1.2 → 1.3-1.7
# - 勝率: 50-55% → 55-65%
# - 取引数: 月 20-50 件（品質フィルタが過剰防衛していないか）
```

### Step 3: 観察結果次第で Phase 90β 着手判断

Phase 90β 候補（macro F1 +0.05-0.10 期待）:
1. **Isotonic Calibration 修正**: v8e で失敗（`ProductionEnsemble` に `fit` メソッド不足）→ 信頼度校正で取引品質判定の精度向上
2. **Focal Loss** (LGB/XGB): クラス不均衡対策（容易サンプル抑制）
3. **CatBoost 追加** or RF 置換: ensemble 多様性向上
4. **Optuna 試行数増** (50→100): XGBoost 過学習対策
5. **Multi-Level VPIN + OFI 拡張**: マイクロ構造特徴強化

### 異常時のロールバック

```bash
# v8e から v8c (旧 3 クラス方向予測) に戻す（10 分以内）
cp models/production/ensemble_full.pre_v8_20260517_101041.pkl.bak \
   models/production/ensemble_full.pkl
cp models/production/production_model_metadata.pre_v8_20260517_101041.json.bak \
   models/production/production_model_metadata.json
git revert <Phase 90α コミットハッシュ>
git push origin main

# または Phase 84 安定モデルに戻す
cp models/production/ensemble_full.phase84.pkl.bak \
   models/production/ensemble_full.pkl
```

### Phase 90α 関連ファイル

- `~/.claude/plans/calm-noodling-cat.md` Phase 90 計画書
- `docs/開発履歴/Phase_90.md` Phase 90α 詳細記録（v8e + 補強 + ライブ分析対応）
- 修正済 (本体): `.github/workflows/model-training.yml` `scripts/ml/run_local_training.sh` `src/ml/nbeats_predictor.py` `config/core/thresholds.yaml`
- 修正済 (補強): `tests/conftest.py` `src/core/orchestration/ml_health_monitor.py` `src/core/persistence/firestore_state.py` `scripts/testing/checks.sh` `requirements.txt`
- 修正済 (ライブ分析): `src/analysis/common/gcp_metrics.py` (count_phase90_* 3 関数) `scripts/live/standard_analysis.py` (_check_phase90_features + _generate_phase90_markdown)
- v8e backup: `models/production/ensemble_full.pre_v8_20260517_101041.pkl.bak`

### Phase 90α 関連コミット履歴

- `7deb5e01` feat: メタラベリング有効化で学習-運用整合性回復・macro F1 +0.20
- `59e3aa4d` fix: black フォーマット整形
- `8afcd406` fix: ローカル checks.sh 完全 PASS 対応 (2426 tests / 73.70%)
- `ad3cd48b` feat: ライブモード分析 Phase 90α 対応 - v8e メタラベリング動作確認追加

---

## 🔍 過去のセッション再開時の最優先タスク（2026-05-17 時点・ローカル再学習 v8c 実行中）— 履歴用

**進行中**: ローカル ML 再学習 v8c が `scripts/ml/run_local_training.sh 50` で稼働中（macOS 8 コア・想定 25-30 分・N-BEATS ハング修正済）。

### 背景（重要な経緯）

**ML 再学習 v7** (run id 25971359708) は **timeout failure**（RF 31 分超でキャンセル・新モデル生成せず）。**ただし途中で得られた macro F1 数値**から **Phase 89 の真の性能を判定済**:

| モデル | 旧 weighted F1（CV）| 新 macro F1（Optuna Best）| 評価 |
|---|---|---|---|
| LightGBM | 0.893（見かけ）| **0.4048** | ランダム 0.33 **+0.07** |
| XGBoost | 0.891（見かけ）| **0.3560** | ランダム **+0.02** |
| RandomForest | 0.820（見かけ）| **0.4031**（v8 ローカル時 macro）| ランダム +0.07 |
| N-BEATS | 0.855（見かけ）| 測定中（v7 で未到達）| confidence_std ×400 万倍改善は本物 |

**結論**: Phase 89 の「+48〜54% 改善」は**評価指標歪みが 100%**。N-BEATS の定数予測脱出（confidence_std 改善）は本物だが、**分類精度は構造的にほぼ未改善**。**Phase 90α ラベリング再設計が必須**。

### 同時に実施した CI/ローカル両対応の n_jobs 修正

`scripts/ml/create_ml_models.py:216, 885` の `n_jobs=1`（GCP gVisor 制約対応）を環境変数 `ML_TRAINING_N_JOBS`（default 1）に変更。CI workflow と新規 `scripts/ml/run_local_training.sh` 双方で `-1`（全コア）を設定 → **RF 31 分 → 6.5 分（約 5 倍速）**。

### N-BEATS macOS ハング修正（v8a/v8b で再現後修正）

**原因**: PyTorch + sklearn/LightGBM が macOS Apple Silicon で OpenMP/BLAS スレッドプールを奪い合い deadlock（CLAUDE.md 既知問題「macOS SEGFAULT」と同根）。

**修正**:
- `src/ml/nbeats_predictor.py:fit()` 冒頭に `torch.set_num_threads(1)` + `torch.set_num_interop_threads(1)`
- `scripts/ml/run_local_training.sh` に `MKL_NUM_THREADS=1` `OMP_NUM_THREADS=1` `OPENBLAS_NUM_THREADS=1` `PYTORCH_ENABLE_MPS_FALLBACK=0` を export
- `config/core/thresholds.yaml` の N-BEATS hyperparam: `n_epochs 200→50` / `patience 20→10`（macOS でハング再発時の早期検出）

### Step 1: v8c 完了確認

```bash
# バックグラウンドタスク（task ID: bwaszgl0f）の完了通知を待つ
# ログ: logs/ml_local/training_<latest>.log

ls -lat logs/ml_local/ | head -3
tail -50 logs/ml_local/training_<latest>.log
```

### Step 2: macro F1 比較表作成（必須・5 分）

```bash
venv/bin/python3 -c "
import json
print('=== macro F1 比較表（真の性能・v8c）===')
with open('models/production/production_model_metadata.phase84.json.bak') as f: p84 = json.load(f)
with open('models/production/phase89_buggy_nbeats_metadata.json.bak') as f: p89b = json.load(f)
with open('models/production/production_model_metadata.json') as f: v8c = json.load(f)
print(f'{\"model\":15s} {\"P84 weighted\":>13s} {\"P89-buggy weighted\":>20s} {\"P89 v8c MACRO\":>15s}')
for m in ['lightgbm', 'xgboost', 'random_forest', 'nbeats']:
    p84_v = p84.get('performance_metrics', {}).get(m, {}).get('f1_score', '-')
    p89b_v = p89b.get('performance_metrics', {}).get(m, {}).get('f1_score', '-')
    v8c_v = v8c.get('performance_metrics', {}).get(m, {}).get('f1_score', '-')
    print(f'{m:15s} {p84_v:>13.4f} {p89b_v:>20.4f} {v8c_v:>15.4f}')
"
```

### Step 3: 判定 → Phase 90α 着手

判定基準（CLAUDE.md 旧基準・v7 で既に判明している通り）:
- macro F1 > 0.6: 真の改善（喜べる・ただし v8c で達成は非現実的）
- macro F1 0.4-0.6: 部分的改善（**ほぼ確定的にここ**）
- macro F1 < 0.4: ランダム水準（XGB はここに該当）

**Phase 90α ラベリング再設計の 3 仮説**（ユーザー承認済）:
- **仮説 A**: Triple Barrier threshold 緩和（meta_tp/sl_ratio 緩めて HOLD 96% → 70% 目標）
- **仮説 B**: 2 クラス化（BUY/SELL のみ・HOLD 排除・「取引する/しない」品質フィルタに専念）
- **仮説 C**: lookahead 短縮（15min → 5min 先予測）

実装場所:
- `scripts/ml/create_ml_models.py:675-742` `_generate_meta_label_target()`
- CLI 引数 `--meta-tp-ratio`, `--meta-sl-ratio`, `--lookahead-periods` で外部から指定可能

### 関連ファイル（v7 timeout + v8c 関連）

- `scripts/ml/run_local_training.sh`（NEW・ローカル wrapper）
- `scripts/ml/create_ml_models.py:216, 885`（n_jobs 環境変数化）
- `src/ml/nbeats_predictor.py:fit()`（torch.set_num_threads 追加）
- `.github/workflows/model-training.yml`（CI も ML_TRAINING_N_JOBS=-1 + per-model timeout 1800s）
- `config/core/thresholds.yaml:178-184`（nbeats hyperparam 削減）
- v8 backup: `models/production/ensemble_full.pre_v8_20260517_062507.pkl.bak`

---

## 🚀 Phase 89 リリース完了 - 次の 5 アクション（参考・履歴用）

| Step | アクション | 必須 | 時間 |
|------|-----------|------|------|
| 1 | **既知の問題調査**（macOS SEGFAULT / pickle ハング） | 任意 | - |
| 2 | **手動 ML 再学習**: `gh workflow run model-training.yml --ref main -f n_trials=50` | 必須 | 10分 |
| 3 | **新モデル整合性確認**: `joblib.load('models/production/ensemble_full.pkl').n_features_in_ == 55` | 必須 | 1分 |
| 4 | **本番デプロイ**: `git push origin main` | 必須 | 10分 |
| 5 | **実機 1 週間観察**: 勝率改善 + Drift 検知 + Auto Retraining trigger | 必須 | 7日 |

詳細手順とロールバック手順: `docs/開発計画/ToDo.md` 「🚀 セッション再開時の手順」セクション

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

### 固定金額TP/SL（Phase 85: レジーム別設定 + floor 0.7%復活）

#### レジーム別TP/SL目標

| レジーム | TP目標 | SL目標 | 実TP距離 | 実SL距離 | 過去30日勝率 | 期待値/件 |
|---------|--------|--------|---------|---------|-------------|----------|
| **tight_range** | **1,500円** | **2,000円** | 0.70% | 0.86% | **67.9%** | **+362円** ✅ |
| **normal_range** | **500円** | **1,500円** | 0.23% | 0.70% | 75.0% | ±0円 |
| **trending** | エントリー停止 | エントリー停止 | - | - | - | 損失回避 |

#### 信頼度別TP/SL目標（フォールバック用）

| 信頼度 | 閾値 | TP金額 | SL金額 |
|--------|------|--------|--------|
| 低 | <0.40 | 1,200円 | 1,500円 |
| 高 | >=0.40 | 1,500円 | 2,000円 |

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

### Maker戦略（Phase 79修正）

| 設定 | 値 |
|------|-----|
| 価格配置 | スプレッド内（Phase 79: best_bid直接配置→spread内に修正） |
| improvement | max(1, min(spread×0.1, spread-1)) |
| spread<2円 | Maker不可、即Takerフォールバック |
| timeout | 60秒、リトライ3回 |
| fallback | Maker失敗時はTakerで成行注文 |

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
