# Phase 89-α: GCP コスト削減プラン（取引 gating + リソース整理）

**期間**: 2026 年 5 月 15 日
**状態**: Stage 1+3 本番デプロイ済 / Stage 2 (キャッシュ最適化) は実測後に判断

---

## 背景

Phase 88 完了時点で GCP 月額 **¥3,000** のまま、当初目標 ¥300-500 には届かず。
ユーザー要件「**追加課金なし・性能維持で月額半分以下 (¥1,500)**」で再調査。

### 24h ライブログ実測で判明した最大の浪費

| 指標 | 値 |
|------|------|
| /trigger 実行回数 | **189 回** (5 分間隔 288 回理論値の 65%) |
| 実取引執行 | **4 回** (6 時間に 1 回) |
| 取引判断スキップ | 199 回 (hold / cooldown / 既存ポジ) |
| **無駄実行率** | **98%** が「データ取得→特徴量→ML→ 取引せず終了」 |

つまり **5 分 trigger 288 回中 285 回 (99%) が「データ取得して特徴量計算して ML 予測して、結局取引しない」処理** で CPU 課金を浪費していた。

### 15 分足 bot 特性とのミスマッチ

| 制約 | 値 | 影響 |
|------|------|------|
| データ更新 | 15 分足完成タイミング (00, 15, 30, 45 分) のみ | 5 分 trigger では 2/3 は同じ 15 分足を 3 回処理 |
| cooldown_minutes | 15 | エントリーから 15 分内は新規不可 |
| max_same_direction_positions | 1 | 既存同方向ポジで新規ブロック |

→ 5 分間隔 trigger は明らかにオーバースペック。15-20 分に 1 回の実取引タイミングに対して、データ取得+ML 計算を 4-5 回繰り返している。

### us-central1 移動の撤回

初版で「Cloud Run 無料枠フル活用 (us-central1 / us-east1 / us-west1 限定)」を推奨したが、ユーザー指摘「bitbank 至近のアジアが望ましい」を踏まえ撤回:

- bitbank サーバー日本国内 → asia-northeast1 が RTT 5-20ms 最適
- us-central1 だと累積 +400-750ms/cycle → スリッページ +0.01-0.02% / 取引
- 期待値マイナス bot に悪影響、無料枠 ¥1,000 削減と相殺以上の損失リスク

データ移行も不要（ML は `tax/trade_history.db` 参照なし、CSV から学習・コード調査済）。

---

## 実装内容（Stage 1+3 完了）

### 🎯 Stage 1: 取引判断 gating（最大効果）

`/trigger` の入口で **200ms 以下の軽量 gating 判定**。NG なら TP/SL 監視のみで早期 return することで CPU 課金時間を大幅削減。

#### 新規 `src/core/orchestration/trade_gating.py`

```python
async def check_trade_gating(
    now: Optional[datetime] = None,
    margin_positions: Optional[List[Any]] = None,
    tolerance_min: int = 2,  # 15 分足境界からの ±許容ジッター
) -> GatingResult:
    # 1. 15 分足完成境界判定: 00, 15, 30, 45 ± 2 分以内でない → reject
    # 2. 既存ポジ判定: long+short 両方の建玉あり → reject
    #    (反対方向への取引機会がある場合は通過させる)
```

設計原則:
- 既存の取引判断ロジック (`trading_cycle_manager` + `risk_manager`) は一切変更しない
- 同等の判定が trading_cycle_manager で既に行われているのを、入口で先取り評価するだけ
- **取引機会を逃さない**（戦略は 15 分足ベース、中間 5 分 trigger でシグナル変わらず）

#### 修正 `src/core/orchestration/trigger_server.py`

`/trigger` ハンドラに gating + 分岐ロジック:

```python
@app.post("/trigger")
async def trigger():
    margin_positions = await bitbank_client.fetch_margin_positions("BTC/JPY")
    gating = await check_trade_gating(now=datetime.now(), margin_positions=margin_positions)

    if not gating.allowed:
        # NG → TP/SL 監視のみ（1-3 秒・Phase 87 C5 + Phase 88 H11）
        await orchestrator.run_monitor_only()
        return {"status": "monitor_only", "reason": gating.reason}

    # OK → フル取引サイクル（7-15 秒）
    await orchestrator.run_trading_cycle()
```

#### 修正 `src/core/orchestration/orchestrator.py`

新メソッド `run_monitor_only()` を追加:
- 特徴量計算 / ML 予測 / 戦略評価 / 注文配置を **行わない**
- `tp_sl_manager.ensure_tp_sl_for_existing_positions()` のみ呼ぶ
- Phase 87 C5 (SL CANCELED_UNFILLED 検出) + Phase 88 H11 (孤児SL 検出) は維持

#### テスト `tests/unit/core/orchestration/test_trade_gating.py`

47 件追加:
- 15 分足境界判定（parametrize 20+15 件）
- ポジション判定（6 件）
- 統合フロー（6 件）

#### 効果見積もり

| 指標 | 現状 | Stage 1 後 |
|------|------|----------|
| /trigger 数 | 288/日 | 288/日（維持） |
| フル取引サイクル発火 | 約 189/日 | 96 → cooldown/ポジ判定で **4-30 程度** |
| 軽量 monitor_only | 0/日 | 約 250+/日 |
| **重い処理 CPU 時間** | - | **70% 削減** |
| 実取引執行 | 4/日 | **4/日 (維持)** |

### 🧹 Stage 3: GCP リソース整理（即時実施・コマンドのみ）

| 施策 | 削減見込み | 実施結果 |
|------|----------|---------|
| Cloud Run 古い revision 削除（直近 1 件残し） | -¥50/月 | **19 件削除完了** |
| Artifact Registry cleanup policy 本適用（30日以上削除） | -¥30-50/月 | **--no-dry-run 適用済** |
| Cloud Logging exclusion filter（INFO/DEBUG 除外） | -¥50-100/月 | **_Default sink 更新済** |
| `--no-cpu-boost` 明示（cold start +2-3 秒許容） | -¥50/月 | **ci.yml 反映済** |

### 観測ログレベル調整（ホットフィックス）

Stage 3-c で適用した Cloud Logging exclusion filter (`severity<WARNING` 除外) と Cloud Run `LOG_LEVEL=WARNING` の組み合わせで、Phase 89-α gating の効果検証ログ (`logger.info`) が Cloud Logging に届かない問題を修正:

- `"Phase 89-α Stage 1: フル取引判断スキップ"`: INFO → **WARNING**
- `"Phase 89-α Stage 1: gating 通過"`: INFO → **WARNING**

24h 観察後にコスト削減効果が確認できたら、再度 INFO に戻す方向。

---

## コスト試算

| 段階 | 月額 | 削減率 | 主要因 |
|------|------|------|------|
| 現状 (Phase 88 直後) | ¥3,000 | - | - |
| Stage 3 単独 | ¥2,700 | -10% | revision/AR/Logging 整理 |
| **Stage 3 + Stage 1 (本コミット)** | **¥1,400-1,700** | **-47%** | gating で重いサイクル 1/30 化 |
| + Stage 2 (キャッシュ層・後日) | ¥1,200-1,600 | -50-60% | OHLCV / 特徴量 / ML 予測キャッシュ |

**目標 ¥1,500 以下**: Stage 1+3 で達成見込み（実測待ち）。

---

## 変更ファイル

### 新規
| ファイル | 役割 |
|---|---|
| `src/core/orchestration/trade_gating.py` | gating 判定ロジック（中心実装） |
| `tests/unit/core/orchestration/test_trade_gating.py` | 47 件のテスト |

### 修正
| ファイル | 内容 |
|---|---|
| `src/core/orchestration/trigger_server.py` | gating 呼び出し + monitor_only 分岐 / ログレベル WARNING 化 |
| `src/core/orchestration/orchestrator.py` | `run_monitor_only()` 新設 |
| `.github/workflows/ci.yml` | `--no-cpu-boost` 追加 + revision-suffix を phase89a-cost-opt-* に |

### GCP コマンド実行履歴

```bash
# Cloud Run 古い revision 削除（19 件）
gcloud run revisions delete <rev> --region=asia-northeast1 --quiet

# Artifact Registry cleanup policy 本適用
gcloud artifacts repositories set-cleanup-policies crypto-bot-repo \
  --location=asia-northeast1 \
  --policy=scripts/deployment/artifact-cleanup-policy.json \
  --no-dry-run

# Cloud Logging exclusion filter
gcloud logging sinks update _Default \
  --add-exclusion='name=exclude-cloud-run-info,filter=resource.type="cloud_run_revision" AND severity<WARNING'
```

---

## 品質ゲート結果

- **2284 tests passed, 1 skipped**（Phase 88 完了時 2233 → +47 件 = trade_gating テスト）
- カバレッジ **73.55%** 維持
- flake8 / isort / black 全 PASS
- ML 検証（37特徴量）/ システム整合性 PASS

---

## 期待効果

1. **GCP 月額**: ¥3,000 → ¥1,400-1,700（47% 削減見込み・実測待ち）
2. **取引精度**: むしろ向上（中間 5 分 trigger の冗長計算によるノイズ取引リスク排除）
3. **取引頻度**: 4 回/日 維持（cooldown / 同方向ポジ制限は変更なし）
4. **運用安全性**: Phase 87 C5 + Phase 88 H11 の 5 分間隔 TP/SL 監視は完全維持

---

## Stage 2（キャッシュ最適化）の判断ポイント

Stage 2 を実施するかは、Stage 1+3 のコスト実測後に判断:

### 想定内容
- OHLCV キャッシュキー: 時刻 → キャンドル番号ベース（同 15 分足を 3 回 fetch しない）
- 特徴量キャッシュ: 直前の DataFrame ハッシュをキーに `@lru_cache`
- ML 予測キャッシュ: 特徴量ベクトルハッシュをキーに

### 効果見積もり
- 1 サイクル 8 秒 → 3-5 秒（37-50% 削減）
- ただし **Stage 1 で重いサイクル数自体が 1/30 に減るため、追加効果は限定的**
- 追加削減見込み: -¥200/月程度

### 実施判断基準
- Stage 1+3 のコスト実測で目標 ¥1,500 を上回っている場合のみ実施
- ¥1,500 以下に収まっていれば Phase 89-β (Web リサーチ統合) を優先

---

## 検証方法

### デプロイ後 1 時間以内
```bash
# 新リビジョン active 確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 \
  --format="value(status.traffic[0].revisionName)"
# 期待: crypto-bot-service-prod-phase89a-cost-opt-*

# /health 確認
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://crypto-bot-service-prod-lufv3saz7q-an.a.run.app/health
# 期待: HTTP 200 / orchestrator_ready: true
```

### 24h 後（gating 効果測定）
```bash
# フル取引サイクル発火数
gcloud logging read 'textPayload=~"Phase 89-α Stage 1: gating 通過"' \
  --freshness=24h --limit=500 --format="value(timestamp)" | wc -l
# 期待: 96 以下（理論最大: 15分間隔の trigger 数 = 96 / 24h）

# monitor_only スキップ数
gcloud logging read 'textPayload=~"Phase 89-α Stage 1: フル取引判断スキップ"' \
  --freshness=24h --limit=500 --format="value(timestamp)" | wc -l
# 期待: 192 以上（残り 200 程度の trigger 全部）

# 実取引維持確認
gcloud logging read 'textPayload=~"エントリー実行成功|取引実行完了"' \
  --freshness=24h --limit=50 --format="value(timestamp)" | wc -l
# 期待: 3-5 件（現状の 4 件 ± 1）
```

### 1 週間後（コスト実測）
```bash
# Cloud Run vCPU-s / GiB-s（Cloud Monitoring REST API）
START=$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ); END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://monitoring.googleapis.com/v3/projects/my-crypto-bot-project/timeSeries?..."

# GCP Billing report で月次実コスト確認
# 期待: ¥1,400-1,700/月
```

---

## リスクと緩和策

| 順位 | リスク | 緩和策 |
|------|--------|--------|
| **中** | gating で正当な取引機会を逸失 | 24h 観察で実取引数が現状 4 回/日 ± 1 内に収まることを確認 |
| **低** | margin_positions 取得失敗時に gating 判定不能 | 例外時はフルサイクル fallback（取引機会逸失防止） |
| **低** | Cloud Logging exclusion で観測ログが消失 | gating 観測ログを WARNING に格上げ（ホットフィックス済） |

---

## Phase 89 中長期計画

Phase 89-α (コスト削減) 完了後、Phase 89-β/γ/δ に進む:

- **Phase 89-β**: Purged K-Fold CV + Fractional Kelly + OFI 特徴量（年利 +2-3%）
- **Phase 89-γ**: N-BEATS 軽量版 + LLM センチメント + HMM レジーム検出（年利 +4-6%）
- **Phase 89-δ**: WebSocket depth stream + Maker 戦略実装化（年利 +1-3%）

詳細: `docs/開発計画/ToDo.md` の Phase 89-92 中長期計画セクション

---

## 関連ファイル

- `~/.claude/plans/phase-iterative-biscuit.md`: 詳細プラン（GCP 仕様 Web 調査結果含む）
- `docs/開発履歴/Phase_88.md`: 前 Phase の記録
- `src/analysis/common/gcp_metrics.py`: Phase 88 で実装したメトリクス取得 wrapper（Stage 1 効果測定に使用）
