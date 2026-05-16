# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 86-89 総合レビュー + P0+P1 軽微修正完了（2026-05-16）→ ML 再学習 v7 待ち**

| 項目 | 値 |
|------|-----|
| 最新成果 | **Phase 86-89 全 72 観点 3-agent レビュー + ML 評価指標構造修正**: weighted→macro F1 / cross_asset リーク防止 / 訓練 180→365 日統一 + 軽微 4 件 |
| Phase 86-89 レビュー | **Critical ゼロ**・軽微 9 件（P0+P1 4 件修正完了・P2 5 件 Phase 90 繰越） |
| 特徴量数 | 37 → **55**（+18・6 カテゴリ追加） |
| ML モデル | 3 → **4**（N-BEATS 追加） |
| ⚠️ 旧 weighted F1 | LGB 0.612→0.893 等は**評価指標歪み**（HOLD 94% + weighted F1 = ランダム予測 0.893 と同水準） |
| 🔄 真の性能 (macro F1) | ML 再学習 v7 で確認予定（Phase 84/85 と公平比較） |
| N-BEATS 修復は本物 | confidence_std 2.98e-08 → 0.115（400 万倍改善・定数予測脱出は事実）|
| TPSL 検証 | 実装健全・Phase 85 報告 +362 円/件は手数料未控除・真の期待値 +138-254 円/件 |
| テスト追加 | +119 件 PASS（既存 2284 → 2403）|
| 追加課金 | ゼロ |
| 完了 Phase | Phase 87 / 88 / **89 全実装 + P0+P1 修正完了** |
| **次の予定** | ML 再学習 v7 → macro F1 確認 → 実機 1 週間観察 → Phase 90 計画 |
| **Phase 90 候補（P2 5 件）** | HMM convergence warning / drift reference 更新 / position_restorer TP/SL 抽出高度化 / GCS backup 統合テスト / WebSocket cleanup integration test |
| 最終更新 | 2026年5月16日 - Phase 86-89 総合レビュー + P0+P1 修正完了 |

---

## 🚀 セッション再開時の手順（Phase 89 観察フェーズ）

Phase 89 は本番デプロイ完了済。次のセッションは観察結果の確認。

### Step 1: 毎日チェック（5 分）

```bash
# ライブ運用 24h 分析（39 指標 + Phase 89 カバレッジ 5 セクション）
venv/bin/python3 scripts/live/standard_analysis.py --hours 24

# 異常ログのスキャン
gcloud logging read 'resource.type=cloud_run_revision AND severity>=ERROR' --freshness=24h --limit=20

# SL placeholder 検出（期待: 0 件）
gcloud logging read 'textPayload=~"Phase 89 C7: SL placeholder ID 検出|ID=existing"' --freshness=24h
```

### Step 2: 1 週間後の総合評価（30 分）

```bash
# 1 週間分析
venv/bin/python3 scripts/live/standard_analysis.py --hours 168

# 確認項目（docs/開発履歴/Phase_89.md 末尾「期待値 vs 警告水準」表参照）
```

### Step 3: 観察結果次第で Phase 90 計画

- LLM センチメント（Twitter/News 感情）
- Transformer 時系列予測（N-BEATS 置換 or 5 モデル目）
- WebSocket microstructure 実装（ofi_top5 等の実数化）
- マルチペア（ETH/JPY）展開

### 異常時のロールバック

`docs/運用ガイド/Phase89_N-BEATS_rollback.md` 参照:
- 軽度（N-BEATS のみ無効化）: `weights.nbeats: 0.0` で 3 モデル運用
- 重度（Phase 89 全体）: `git tag phase-89-stable` から checkout

---

## 🚀 過去のセッション再開手順（参考・履歴用）

クリア後の再開ガイド。**実行順序厳守**。

### Step 1: 既知の問題調査（任意・スキップ可能・本番影響なし）

両方とも macOS ローカル pytest 環境固有の問題で、本番（Linux Cloud Run / Ubuntu CI）には影響なし。

#### 1-a. macOS 上のテスト連続実行時 SEGFAULT

```bash
# 再現条件: test_nbeats.py の後に test_ensemble.py / test_ml_health_monitor.py を連続実行
/Users/nao/Developer/active/bitbank-btc-bot/venv/bin/python3 -m pytest tests/unit/ml/ -q --no-header
# 期待: "Fatal Python error: exit: 139" が test_nbeats.py 終了直後に発生

# 単独実行では全 PASS（既に確認済）
/Users/nao/Developer/active/bitbank-btc-bot/venv/bin/python3 -m pytest tests/unit/ml/test_nbeats.py -q  # 16 PASS
/Users/nao/Developer/active/bitbank-btc-bot/venv/bin/python3 -m pytest tests/unit/ml/production/test_ensemble.py -q  # 21 PASS
```

**推定原因**: PyTorch (2.12.0) と sklearn / numpy の C 拡張ライブラリ干渉。macOS Apple Silicon 固有。
**緩和策候補**:
- `pytest --forked`（pytest-forked 必要）で各テストを別プロセス分離
- `conftest.py` で `torch.set_num_threads(1)` の早期設定
- `MKL_NUM_THREADS=1 OMP_NUM_THREADS=1` 環境変数
- CI（Ubuntu）では未発生想定（要確認）

#### 1-b. `test_production_ensemble_pickle_error` 単独ハング

```bash
# 再現
/Users/nao/Developer/active/bitbank-btc-bot/venv/bin/python3 -m pytest tests/unit/core/test_ml_adapter_exception_handling.py::TestMLServiceAdapterExceptionHandling::test_production_ensemble_pickle_error -v
# 21% で永遠に止まる
```

**推定原因**: `MLServiceAdapter(mock_logger)` 初期化中、`pickle.UnpicklingError` を mock した状態で N-BEATS / HMM の load 経路に入る無限ループ？
**調査要点**: `src/core/orchestration/ml_loader.py` で pickle 失敗時の fallback パスに新規追加した torch / hmmlearn が干渉していないか確認。

### Step 2: 手動 ML 再学習（必須・約 10 分）

```bash
# GitHub Actions で 55 特徴量モデルを学習
gh workflow run model-training.yml --ref main -f n_trials=50 -f dry_run=false

# 完了監視（約 10 分）
gh run watch

# または手動確認
gh run list --workflow=model-training.yml --limit 1
```

**学習内容**:
- 55 特徴量（Phase 77 SHAP 37 + 89-β 10 + 89-γ 5 + 89-δ 3）
- 4 モデル: LGB / XGB / RF / N-BEATS
- Purged K-Fold (embargo_pct=0.01)
- メタラベリング (Triple Barrier)
- SMOTE オーバーサンプリング
- Optuna ハイパラ最適化（50 trials）

### Step 3: 新モデル整合性確認（必須・1 分）

```bash
# 学習完了後、models/ をプル
git pull origin main

# モデル特徴量数確認
/Users/nao/Developer/active/bitbank-btc-bot/venv/bin/python3 -c "
import joblib
m = joblib.load('models/production/ensemble_full.pkl')
print('n_features_in_:', m.n_features_in_)
print('models:', list(m.models.keys()))
print('weights:', m.weights)
assert m.n_features_in_ == 55, f'55 特徴量モデルではない: {m.n_features_in_}'
assert 'nbeats' in m.models, 'N-BEATS が含まれていない'
print('✅ 55 特徴量 + 4 モデル統合 OK')
"
```

**期待結果**:
- `n_features_in_: 55`
- `models: ['lightgbm', 'xgboost', 'random_forest', 'nbeats']`
- `weights: {'lightgbm': 0.34, 'xgboost': 0.34, 'random_forest': 0.17, 'nbeats': 0.15}`

### Step 4: 本番デプロイ（必須）

```bash
# CI を通して Cloud Run へ自動デプロイ
git push origin main

# デプロイ監視（約 8-10 分）
gh run watch

# Cloud Run リビジョン確認
TZ='Asia/Tokyo' gcloud run revisions list \
  --service=crypto-bot-service-prod \
  --region=asia-northeast1 --limit=3
```

**注意事項**:
- 起動時に `n_features_in_ mismatch` でクラッシュしないこと（Step 3 で確認済みなら OK）
- Phase 89-γ で追加した `GITHUB_REPO_DISPATCH_TOKEN` Secret を GCP Secret Manager に登録（Auto Retraining 用・初回のみ）

### Step 5: 実機 1 週間観察（必須）

以下を毎日確認:

```bash
# 1. 取引パフォーマンス（24h）
/Users/nao/Developer/active/bitbank-btc-bot/venv/bin/python3 scripts/live/standard_analysis.py --hours 24

# 2. Drift 検出ログ（Phase 89-β）
gcloud logging read 'textPayload=~"Phase 89-β.*Drift|drift|distribution"' --freshness=24h

# 3. Fractional Kelly 動作（Phase 89-β）
gcloud logging read 'textPayload=~"Phase 89-β Fractional Kelly|dynamic_safety"' --freshness=24h

# 4. WebSocket 接続健全性（Phase 89-δ）
gcloud logging read 'textPayload=~"Phase 89-δ WebSocket|websocket"' --freshness=24h

# 5. Auto Retraining trigger（Phase 89-γ・通常は trigger されないはず）
gcloud logging read 'textPayload=~"Auto Retraining triggered"' --freshness=168h
```

**期待結果（1 週間後）**:
- 勝率改善: 既存 25-50% → **55%+**
- Max Drawdown: -20% 以内
- Drift 検知: 通常 0 件、急変時のみ trigger
- WebSocket: reconnect は許容、長時間切断なし
- 期待値: プラス側へ転換（目標 +¥6,000-7,500/月）

#### 失敗時のロールバック

```bash
# 旧モデル（37 特徴量）に戻す場合
cd /Users/nao/Developer/active/bitbank-btc-bot
git revert <Phase 89 commit hash>
git push origin main

# またはモデルファイルだけ戻す
cp models/production/ensemble_full.phase84.pkl.bak models/production/ensemble_full.pkl
git add models/production/ensemble_full.pkl
git commit -m "rollback: Phase 89 model → Phase 84 backup"
git push origin main
```

---

## Phase 89-α コスト削減プラン（最新・着手中）

詳細プラン: `~/.claude/plans/phase-iterative-biscuit.md`
実装記録: [docs/開発履歴/Phase_89.md](../開発履歴/Phase_89.md)

### Stage 1: 取引判断 gating（実装完了・デプロイ済）

5 分間隔 trigger で 15 分足完成境界（00, 15, 30, 45 分の ±2 分以内）外 or 既存両方向ポジ時は TP/SL 監視のみで早期 return。**取引機会は維持しつつ重い処理発火を 1/30 に削減**。

実測根拠:
- 5 分 trigger 189 回 / 24h
- 実取引 4 回 / 24h
- **98% が「データ取得→特徴量→ML→ 取引せず終了」で CPU 浪費**

### Stage 3: GCP リソース整理（完了済・GCP コマンド）

- Cloud Run 旧 revision 19 件削除
- Artifact Registry cleanup policy 本適用（30 日以上削除）
- Cloud Logging exclusion filter（INFO/DEBUG 除外）
- `--no-cpu-boost` 明示（cold start +2-3 秒許容で削減）

### Stage 2: コード最適化（pending・実測後に判断）

Stage 1+3 後のコスト実測が ¥1,500 を上回っている場合のみ実施。¥1,500 以下なら Phase 89-β を優先。

#### Stage 2-a: OHLCV キャッシュキー改善

**対象**: `src/data/data_cache.py`

| 項目 | 現状 | 改善後 |
|------|------|------|
| キャッシュキー | `{symbol}_{timeframe}_{start_time}_{limit}`（時刻依存） | `{symbol}_{timeframe}_{candle_id}`（キャンドル番号ベース） |
| 5分間隔 trigger | 別キー生成 → 毎回 API 再取得 | 同 15分足キャンドル → 同一キー → キャッシュヒット |
| 効果 | - | bitbank API 呼び出し -33%（月 8,640 → 5,760） |

実装イメージ:
```python
def _candle_id(timestamp: datetime, timeframe: str) -> int:
    """15 分足なら 00:00 ベースで candle 番号を返す（同 15分足は同 ID）"""
    minutes_per_candle = {"15m": 15, "4h": 240}[timeframe]
    epoch_min = int(timestamp.timestamp() // 60)
    return epoch_min // minutes_per_candle
```

#### Stage 2-b: 特徴量キャッシュ

**対象**: `src/features/feature_generator.py`

- DataFrame のハッシュ（最終 timestamp + close 値の hash）をキーに `@lru_cache(maxsize=4)`
- 同一 OHLCV に対する 37 特徴量計算を 1 回のみ
- **想定削減**: 20-60ms / cycle

実装イメージ:
```python
from functools import lru_cache

def _features_key(df: pd.DataFrame) -> str:
    return f"{df.index[-1].isoformat()}_{hash(tuple(df['close'].tail(50)))}"

@lru_cache(maxsize=4)
def _compute_features_cached(key: str, ...) -> pd.DataFrame:
    ...
```

#### Stage 2-c: ML 予測キャッシュ

**対象**: `src/ml/ensemble.py` or `src/core/orchestration/ml_adapter.py`

- 特徴量ベクトル（37 個の float）のハッシュをキーに直前 1 件のみキャッシュ
- 同一特徴量に対する 3 モデルアンサンブル予測を 1 回のみ
- **想定削減**: 40-100ms / cycle

#### テスト追加

- `tests/unit/data/test_data_cache.py` に candle_id テスト 4-6 件
- `tests/unit/features/test_feature_generator.py` に lru_cache 動作テスト 3-4 件
- `tests/unit/ml/test_ensemble.py` に predict キャッシュテスト 3-4 件

#### 効果見積もり

| 指標 | Stage 1+3 後 | + Stage 2 後 |
|------|------------|------------|
| 1 サイクル所要時間（フル取引） | 7-15 秒 | **3-5 秒** |
| 1 サイクル所要時間（monitor_only） | 1-3 秒 | 1-3 秒（変化なし） |
| 月額 GCP | ¥1,400-1,700 | **¥1,200-1,600** |
| 追加削減 | - | **-¥200-300/月** |

**注意**: Stage 1 で重いサイクル数自体が 1/30 に減るため、Stage 2 の追加効果は限定的。

### us-central1 移動の撤回

初版で Cloud Run 無料枠フル活用のため推奨したが撤回:
- bitbank サーバー日本国内 → asia-northeast1 が RTT 5-20ms 最適
- us-central1 だと累積 +400-750ms/cycle → スリッページ +0.01-0.02%/取引
- 期待値マイナス bot に悪影響、無料枠 ¥1,000 削減と相殺以上の損失

データ移行も不要（ML は `tax/trade_history.db` 参照なし）。

---

## 🗂️ ローカル環境整備 ToDo（2026-05-15 起票・iCloud 同期完了待ち）

### 目的

リポジトリを `/Users/nao/Developer/active/bitbank-btc-bot` から Apple 推奨の `/Users/nao/Developer/active/bitbank-btc-bot` へ移動し、Desktop の iCloud 同期対象から外す（venv/models/logs 計約 2.8GB・22,580 ファイルの無駄なクラウドアップロードを根絶）。

### ブロッカー

iCloud Drive「デスクトップと書類」初回フル同期が進行中（2026-05-15 14:02 時点で 4.37GB アップロード中・総量推定が走査中で増加継続）。同期途中で `mv` するとクラウド側に孤児ファイルが残るリスクあり、**完了まで待機**。

### 影響調査結果（事前確認済み）

| 対象 | 影響 | 備考 |
|------|------|------|
| GitHub リポジトリ / Actions / git remote | **影響なし** | クラウド側リソース。`.github/workflows/` 6 本に絶対パス参照ゼロ |
| GCP Cloud Run / Cloud Build / Secret Manager / Artifact Registry / Firestore | **影響なし** | 全てクラウド側。Dockerfile に絶対パスゼロ |
| コード本体（.py/.sh/.yaml/.json/.toml） | **影響なし** | `Desktop/bot` 参照ゼロ。全て相対パス＋ `Path(__file__).parent` |
| launchctl / cron / shell rc | **影響なし** | 設定なし |
| **venv（要再作成）** | `venv/bin/{python,pip}` シェバンと `pyvenv.cfg` の `command =` が絶対パス | 移動後 `rm -rf venv && python3 -m venv venv && pip install -r requirements.txt` |
| **`~/.claude/projects/-Users-nao-Desktop-bot/`** | Claude Code は cwd からディレクトリ名自動生成。memory と過去セッションは新パスに引き継がれない | 移動後 `memory/` を `~/.claude/projects/-Users-nao-Developer-active-bitbank-btc-bot/` へコピー |
| `~/.claude/plans/ml-tpsl-sl-sl-tp-polymorphic-marshmallow.md` | 1 件参照あり | 任意で sed 置換 |
| ドキュメント `.md` 12 件 | tax/scripts/README.md / docs/運用ガイド/統合運用ガイド.md / docs/開発履歴/Phase_21-30 等 | 動作影響ゼロ。任意で一括 sed |
| `logs/` 内過去ログ | テキスト内参照のみ | 動作影響ゼロ。放置可 |

### 実行手順（同期完了後）

```bash
# 1. ローカルで bot プロセスが動いていないか確認（GCP 本番は別プロセスで稼働継続・無影響）
ps aux | grep -E "python.*main.py" | grep -v grep

# 2. 移動
mv /Users/nao/Developer/active/bitbank-btc-bot /Users/nao/Developer/active/bitbank-btc-bot

# 3. venv 再作成
cd /Users/nao/Developer/active/bitbank-btc-bot
rm -rf venv && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 4. Claude memory 引き継ぎ（cd 後に claude を 1 度起動して新 projects ディレクトリ生成 → コピー）
cp -r ~/.claude/projects/-Users-nao-Desktop-bot/memory \
      ~/.claude/projects/-Users-nao-Developer-active-bitbank-btc-bot/

# 5. ドキュメント絶対パス一括置換（任意・動作影響なし）
grep -rl "/Users/nao/Developer/active/bitbank-btc-bot" --include="*.md" . | \
  xargs sed -i '' 's|/Users/nao/Developer/active/bitbank-btc-bot|/Users/nao/Developer/active/bitbank-btc-bot|g'
sed -i '' 's|/Users/nao/Developer/active/bitbank-btc-bot|/Users/nao/Developer/active/bitbank-btc-bot|g' \
  ~/.claude/plans/ml-tpsl-sl-sl-tp-polymorphic-marshmallow.md

# 6. CLAUDE.md / README.md のしおり更新（任意・パス文言を含む箇所のみ）
```

### 補足

- `/Users/nao/Developer/` は iCloud Drive 同期対象外（Apple 公式推奨）。移動完了後、bot 全体（venv 含む 22,580 ファイル）が iCloud から外れて容量・帯域節約。
- iCloud 同期完了後、Finder の iCloud Drive > デスクトップから旧 `bot/` のクラウドコピーを削除する余地あり。

---

## 🎯 Phase 89-β/γ/δ 連続実装方針（2026-05-15 確定）

### 背景

- 4 月 1 ヶ月稼働で **-数万円**（実機検証で期待値マイナス確定）
- ちまちま修正→検証ループでは状況改善の見込み薄
- Phase 89-β/γ/δ を**累積実装** + 各 Phase 末で ML 再学習で一気に勝率向上を目指す

### 確定方針

| 項目 | 確定内容 |
|------|---------|
| **Phase 90 (PPO 強化学習)** | **見送り** |
| **理由 1** | GPU 月 ¥500-1,000 の追加課金が必要（「追加課金なし」方針に反する） |
| **理由 2** | 期待値マイナス bot で強化学習 = 誤った報酬信号で学習 → 損失加速リスク |
| **理由 3** | 元計画でも「Sharpe 比 > 2.0 達成後の条件付き再検討」と明記済 |
| **LLM センチメント (Phase 89-γ 当初候補)** | **不採用** |
| **理由** | Claude API トークン課金（月 ¥30-150）が発生・使用量に左右される従量課金は予測不能 |
| **代替** | **Fear & Greed Index**（alternative.me free API）で完全無料代替。シグナル精度 +5-10% は確保（LLM の +10-15% よりやや劣るが課金ゼロ） |

### 実装オーダー

```
Week 1-2: Phase 89-β（Purged K-Fold + Fractional Kelly + OFI + Funding Rate + Fear & Greed + Drift Detection）
  ↓ ML 再学習（47-50 特徴量へ拡張）+ 実機 1 週間観察
Week 4-6: Phase 89-γ（N-BEATS 軽量版 + HMM レジーム + VPIN + Automated Retraining）
                  ※ LLM センチメントは除外（Fear & Greed Index で代替済）
  ↓ ML 再学習（4 モデルアンサンブル化）+ 実機 1 週間観察
Week 8-10: Phase 89-δ（WebSocket depth stream + Maker 戦略実装化 + BTC-ETH 相関）
  ↓ 実機 1 ヶ月観察
完了判断: 期待値プラス + 月利 1% 達成
```

**期待効果**:
- 89-β 完了: 年利 12-13% / Max DD -20% / 期待値ほぼゼロまで改善
- 89-γ 完了: 年利 14-16% / 期待値プラス側へ
- 89-δ 完了: **年利 15-18% / 月利 1-1.5%**

50 万円証拠金で月 ¥6,000-7,500 → 月数万円のマイナスから**月数万円のプラス**へ転換目標

### 追加課金確認（最終）

| 候補 | 月額 | 採用 |
|------|------|------|
| Phase 89-β: OFI 特徴量（既存 `data/orderbook/` 活用） | ¥0 | ✅ |
| Phase 89-β: Funding Rate（Binance 無料 API） | ¥0 | ✅ |
| Phase 89-β: Fear & Greed（alternative.me 無料 API） | ¥0 | ✅ |
| Phase 89-γ: N-BEATS（Cloud Run 内推論・GPU 不要） | ¥0 | ✅ |
| Phase 89-γ: HMM（hmmlearn ローカル実行） | ¥0 | ✅ |
| Phase 89-γ: VPIN（独自計算） | ¥0 | ✅ |
| **Phase 89-γ: LLM センチメント** | ¥30-150 | **❌（Fear & Greed で代替）** |
| Phase 89-δ: WebSocket（bitbank 無料） | ¥0 | ✅ |
| Phase 89-δ: Maker 戦略強化（既存 API） | ¥0 | ✅ |
| Phase 89-δ: BTC-ETH 相関（Binance 無料 API） | ¥0 | ✅ |
| **Phase 90: PPO 強化学習** | GPU ¥500-1,000 | **❌（見送り確定）** |

→ Phase 89-β/γ/δ 全実装で **追加課金ゼロ確定**

---

## 🚨 SL消失インシデント（2026-05-12）— Phase 87 着手の契機

### 機序（bitbank `fetch_order` 直接照会で確定）

```
05:55:45 SL stop注文配置（ID=57247842273, trigger=12,732,347）
10:31:45 SL健在確認（limit=1, stop=1）
10:39:21 GCPログ「価格急変検出: Zスコア=3.31」
10:41:10 SLトリガー到達 → 成行決済試行
         流動性不足/スリッページ過大で約定失敗
         bitbank が自動 CANCELED_UNFILLED に遷移
10:46:34 bot検出: stop=0（CANCELED状態は fetch_open_orders に返らない）
         botは検出する仕組みを持たず、ポジション裸放置
```

### 構造的正体

「過去にも繰り返されるSL配置漏れ」の3層欠陥:
1. bitbank stop注文がトリガー発火後に約定失敗する仕様（CANCELED_UNFILLED）
2. botがそれを検出する仕組みを一切持たない実装欠陥
3. Phase 78（stop_limit）↔ Phase 80（stop）の二択ループを抜け出していない設計

---

## 完了Phase

### Phase 87 全 Stage 完了 ✅（2026-05-14 本番デプロイ済・全Critical 5 + High 10 達成）

**Stage 1 + 1-R**: SL消失検出層構築（2026-05-13）
- Critical 4件: C1 SLMonitor 新規・C2 ML信頼度 predicted_class_proba 統一・C3 TP Maker _safe_cancel・C5 5分ループ SL health check
- High 4件: H1 SL 24h timeout・H2 起動時SL欠損サイレント失敗解消・H7 EXPECTED_FEATURE_COUNT 定数化・H9 6戦略アサート
- Stage 1-R 補強: 統合連携テスト7件 + エッジケース3件 + docstring + 数値同一性検証6件

**Stage 2 + 2-R**: 永続化基盤 + サーキットブレーカー（2026-05-14）
- C4 DummyModel サーキットブレーカー（MLHealthMonitor、3回連続失敗で EMERGENCY_STOP）
- H3 SL stop_limit + slippage_buffer 0.008 二重防衛（コード先行投入）
- H4-H5 Firestore 永続化（SL状態 / DrawdownManager / MLHealth）
- Stage 2-R 補強: C4 閉ループ完成 + silent failure 検知 + threshold config化

**Stage 3 + 3-R**: 品質フィルタ共通化 + 段階復帰 + 分析共通lib（2026-05-14）
- H10 QualityFilter モジュール（trading_cycle_manager と backtest_runner で同一判定）
- H6 レジーム別品質フィルタ閾値（tight 0.55 / normal 0.75 / trending 0.50）
- H8 RECOVERY_TESTING + 3回連続失敗で EMERGENCY_STOP（無限ループ防止）
- src/analysis/common/ 新規（sl_validators / canceled_unfilled_detector / tp_sl_helpers）
- Stage 3-R 補強: backtest regime 反映・normal_range 0.85→0.75 緩和・check_trading_allowed 修正

**実機検証**: 5/13 24h: 勝率25% -¥5,216 → 5/14 12h: **勝率100% +¥1,500**（+¥6,716 改善）
**詳細**: `docs/開発履歴/Phase_87.md`

### Phase 86: TP/SL/Entry根本再構築 ✅（2026-05-12 デプロイ）
- TPSLCalculator 単一実装化（旧4箇所分散を解消）
- bitbank API wrapper 強化（trigger_price 必須検証、配置後3秒×3回ポーリング）
- Atomic Entry 緊急成行決済（部分約定時のロールバック改善）
- 起動時SL自動修復（position_restorer.py 内）
- デプロイ後の実機検証: 現ポジへSL自動配置成功（trigger=12,732,347, 0.838%）

### Phase 85: レジーム別TP/SL再構築 ✅
- floor 0.7% 復活、trending エントリー停止
- レジーム別TP/SL（tight 1500/2000、normal 500/1500）
- sl_simulation.py の手数料加算バグ修正
- ML再学習（CV F1: LGB 0.602 / XGB 0.577 / RF 0.571）

### Phase 84: 品質フィルタ調整 ✅
- high_confidence_failure_threshold ハードコード→0.65 設定化
- confidence = max(p_0, p_1) 解釈に基づく閾値選定

### Phase 83A-3 / 83B / 83C: 固定金額TP/SL ✅
- 信頼度別TP/SL、SL floor 0.7% 強制
- 包括バグ修正13項目

### Phase 82: ゴーストポジション・SL異常値バグ修正 ✅
- ダスト検出ガード（min_valid_position_btc 0.001 BTC）
- SL極端値検出→配置中止

### Phase 81: stop_limit デッドコード削除 ✅
- Phase 62-68 構築の stop_limit 関連 818行削除

### Phase 80: SL注文タイプロールバック ✅
- stop_limit→stop（Phase 78 が逆効果と判明）
- Phase 69.8 の教訓を再確認

### Phase 71-79: パイプライン最適化・ML改善
（詳細は docs/開発履歴/Phase_71-81.md 参照）

---

## Phase 87 完了サマリ（全 Critical 5 + High 10 達成）

9エージェント並列調査で確定した全23欠陥（C1-C5 + H1-H10 + M1-M5 + L1-L3 + I1-I5）のうち、
**Critical 5 + High 10 を Phase 87 で完全達成**。Medium 5 + Low 3 + Infrastructure 5 は Phase 88 へ。

| カテゴリ | 完了Phase | 状態 |
|---------|----------|------|
| 🔴 Critical 5件（C1-C5） | Phase 87 Stage 1-2 | ✅ 全完了 |
| 🟠 High 10件（H1-H10） | Phase 87 Stage 1-3 | ✅ 全完了 |
| 🟡 Medium 5件（M1-M5） | Phase 88 P3 / P2 | ⏳ 未着手 |
| 🟢 Low 3件（L1-L3） | Phase 88 P1 / P3 | ⏳ 未着手 |
| 💰 Infrastructure 5件（I1-I5） | Phase 88 P0-P2 | ⏳ 未着手 |

詳細: `docs/開発履歴/Phase_87.md`

---

## 🔧 過去計画（Phase 87 + 88 完全リファクタリング・記録）

### 概要

ユーザー要望「古いシステムを廃止し、最新の問題なく稼働するロジックだけを残したい」を実現する大規模リファクタリング。9回のExploreエージェント並列調査で **全23欠陥** を確定。

### 確定方針

- ✅ **実装範囲**: Phase 87 + 88 完全リファクタリング（全23欠陥対応）
- ✅ **永続化**: Firestore（無料枠内・月額0円）
  - bot 想定使用量: 約576 write/day vs 無料枠20,000 write/day
- ✅ **stop型**: stop_limit + slippage_buffer 0.008 で二重防衛（Phase 78/80 ジレンマ完全解決）

---

## 全23欠陥の包括リスト（重大度別）

### 🔴 Critical（5項目: 4/5 完了 ✅ / 残 1）

| # | 欠陥 | 状態 | 完了Phase |
|---|------|------|---------|
| C1 | SL CANCELED_UNFILLED 検出未実装 | ✅ 完了 | Stage 1 |
| C2 | ML信頼度計算が `max(p_0, p_1, p_2)` | ✅ 完了 | Stage 1 |
| C3 | TP Maker タイムアウト時の自動キャンセル無し | ✅ 完了 | Stage 1 |
| C4 | DummyModel フォールバックが品質フィルタモードで全拒否 | ⏳ **未着手** | Stage 2 予定 |
| C5 | 5分ループ内 SL health check 無し | ✅ 完了 | Stage 1 |

### 🟠 High（10項目: 4/10 完了 ✅ / 残 6）

| # | 欠陥 | 状態 | 完了/予定Phase |
|---|------|------|---------|
| H1 | SLタイムアウト判定（24h超過→強制決済）未実装 | ✅ 完了 | Stage 1 |
| H2 | Phase 86 サイレント失敗 | ✅ 完了 | Stage 1 |
| H3 | slippage_buffer 0.008 が定義済だが未使用 | ⏳ **未着手** | Stage 2 予定 |
| H4 | Phase 68.4 永続化が Cloud Run で機能しない | ⏳ **未着手** | Stage 2 (要GCP) |
| H5 | DrawdownManager の状態がContainer再起動でリセット | ⏳ **未着手** | Stage 2 (要GCP) |
| H6 | 品質フィルタ閾値がレジーム別採算ラインと矛盾 | ⏳ **未着手** | Stage 3 予定 |
| H7 | feature_count 不一致の silent ML failure | ✅ 完了 | Stage 1 |
| H8 | 連敗保護の解除即リセット | ⏳ **未着手** | Stage 3 予定 |
| H9 | 戦略シグナル完全性チェック無し | ✅ 完了 | Stage 1 |
| H10 | バックテスト vs ライブ整合性未確認 | 🟡 部分完了 | Stage 1-R (R4数値同一性のみ) / Stage 3 E2E未着手 |

### 🟡 Medium（Phase 88 で計画的に・5項目）

| # | 欠陥 | 影響 | ファイル |
|---|------|------|---------|
| M1 | Kelly基準のゼロサイズ理由が不明示 | 期待値負時のサイズ0で原因不明 | kelly.py:222-254 |
| M2 | bitbank API レート制限の実装と設定が不一致 | hardcode 200ms vs config 35000ms | bitbank_client.py:87 |
| M3 | TP/SL価格の丸め処理が不明示 | banker's rounding 意図不明 | tpsl_calculator.py |
| M4 | 異常検知が時間帯別に未調整 | 深夜と日中で同じZスコア閾値 | anomaly.py |
| M5 | 税務 SQLite が Container 再起動で失われる | 確定申告データ永続化破綻 | tax/trade_history.db |

### 🟢 Low（保守性向上・3項目）

| # | 欠陥 | 影響 | ファイル |
|---|------|------|---------|
| L1 | Phase XXX コメントが200ファイルに分散 | 保守負荷 | 全Pythonファイル |
| L2 | README.md と CLAUDE.md の乖離 | ユーザー混乱 | README.md |
| L3 | Dead code 削除計画なし | 約500行残存 | executor.py:1436-1450 等 |

### 💰 Infrastructure（GCPコスト削減・5項目）

**現状の月額 GCP コストは約3,000円**（CLAUDE.md 想定 700-900円の約3-4倍）。
最大の原因は Cloud Run の常時稼働（min_instances=1）。Phase 87/88 で構造的に削減する。

| # | 項目 | 削減効果 | Phase | 前提条件 |
|---|------|---------|-------|---------|
| I1 | Cloud Logging LOG_LEVEL DEBUG → WARNING | **-100~200円/月** | 88 (P1先行可) | なし（即時実施可能） |
| I2 | Artifact Registry リテンションポリシー | **-20~50円/月** | 88 (P1先行可) | なし（即時実施可能） |
| I3 | min_instances 1 → 0 + Cloud Scheduler 起動 | **-2,400円/月** | 88 (P0) | **Phase 87 H4-5 完了必須**（Firestore永続化なしでは状態消失） |
| I4 | Cloud Run メモリ 1GB → 512MB | **-150円/月** | 88 (P1) | Phase 87 完了後（feature_count等の安定化後） |
| I5 | bitbank API 呼び出しキャッシュ徹底 | **-20~50円/月** (Egress) | 88 (P2) | なし |

**目標**: 月額 3,000円 → **約300-500円**（**約83%削減**）

---

## Phase 87 実装計画（1-2週間）

### P0a: SLMonitor 新規実装（C1, C5）

**新規ファイル**: `src/trading/execution/sl_monitor.py`

```python
class SLMonitor:
    """SL注文のhealth check + CANCELED_UNFILLED 検出"""
    async def monitor_sl(self, vp, bitbank_client, symbol="BTC/JPY"):
        sl_order_id = vp.get("sl_order_id")
        order = await asyncio.to_thread(
            bitbank_client.exchange.fetch_order, sl_order_id, symbol
        )
        info_status = order.get("info", {}).get("status", "")
        if info_status == "CANCELED_UNFILLED":
            # 即時緊急成行決済
            return await self._emergency_market_close(vp, bitbank_client, symbol)
        ...
```

**統合先**: `executor.check_stop_conditions()` で5分ごと全VPに対して実行

### P0b: ML信頼度計算修正（C2）

**修正ファイル**: trading_cycle_manager.py:309-310, backtest_runner.py:257

```python
# 旧: confidence = float(np.max(ml_probabilities[-1]))
# 新:
predicted_class = int(np.argmax(ml_probabilities[-1]))
confidence = float(ml_probabilities[-1][predicted_class])
```

### P0c: TP Maker タイムアウト時の自動キャンセル（C3）

**修正ファイル**: order_strategy.py:120-160

タイムアウト時に `cancel_order()` を呼ぶ。

### P0d: DummyModel フォールバック警告（C4）

**修正ファイル**: ml_adapter.py:51-110

品質フィルタモードで DummyModel になったら critical ログ + サーキットブレーカー検討。

### P0e: 5分ループ内 SL health check（C5）

**修正ファイル**: tp_sl_manager.py:ensure_tp_sl_for_existing_positions

5分ごとに全VPに対して fetch_order(id) で個別検証 → CANCELED_UNFILLED 検出 → SLMonitor 起動。

### H1: SLタイムアウト判定実装

sl_placed_at から24h超過のSL → 強制決済。

### H2: Phase 86 サイレント失敗解消

position_restorer.py:269-293 で `emergency_sl_order={"id": None}` 時に critical ログ + 緊急成行決済。

### H3: stop_limit + slippage_buffer 0.008（Phase 78/80 ジレンマ解決）

```python
# tp_sl_manager.place_stop_loss
if order_type == "stop_limit":
    slippage_buffer = get_threshold("position_management.stop_loss.slippage_buffer", 0.008)
    if side == "buy":
        limit_price = stop_loss_price * (1 - slippage_buffer)
    else:
        limit_price = stop_loss_price * (1 + slippage_buffer)
```

**二重防衛**: 通常時 stop_limit で確実約定 + 価格急変時 CANCELED_UNFILLED → SLMonitor 緊急成行決済。

### H4-5: Firestore 永続化（無料枠内・月額0円）

**新規ファイル**: `src/core/persistence/firestore_state.py`

```python
class FirestoreStatePersistence:
    def __init__(self, bot_id="default"):
        self.db = firestore.Client()
        self.doc = self.db.collection("bots").document(bot_id)
    def save_sl_state(...): ...
    def save_drawdown_state(...): ...
```

**移行先**:
- sl_state_persistence.py の内部実装を Firestore に変更（API互換維持）
- drawdown.py の _save_state/_load_state を Firestore 経由

**🔑 GCPコスト削減（I3: min_instances=0）の前提条件**:
H4-5 は Phase 87 の SL対策のみならず、**Phase 88 I3（Cloud Run min=0 化による月額-2,400円削減）の必要条件**。状態を Firestore に永続化することで、Container 再起動時の VP・ドローダウン状態消失リスクを排除し、安全に min=0 へ移行可能となる。

### H6: 品質フィルタ閾値のレジーム別化

```yaml
ml.quality_filter:
  regime_thresholds:
    tight_range: { high_confidence_failure_threshold: 0.55 }
    normal_range: { high_confidence_failure_threshold: 0.85 }
    trending: { high_confidence_failure_threshold: 0.50 }
```

### H7: feature_count 一致確認

`EXPECTED_FEATURE_COUNT = 37` 共有定数化、特徴量数アサーション。

### H8: 連敗保護の段階的復帰

`TradingStatus.RECOVERY_TESTING` 状態追加、2-3取引の成功確認後完全復帰。

### H9: 戦略シグナル完全性チェック

6戦略全て揃っていることをアサート、不足時 critical ログ。

### H10: バックテスト vs ライブ整合性検証

confidence 計算の一貫性を統合テストで確認。

### 分析スクリプト改修

1. **新規 `scripts/analysis/lib/`** - 共通ライブラリ化
   - `sl_validators.py` (SL検証)
   - `canceled_unfilled_detector.py` (新規)
   - `tp_sl_calculator.py` (Phase 85 修正版で統一)
2. **`scripts/live/standard_analysis.py` 改修**:
   - `missing_sl_detected` を金額ベース→件数ベースに修正
   - C1-C5 新規検出機能追加
3. **`scripts/backtest/standard_analysis.py` 改修**:
   - Phase 85 手数料修正適用
   - 共通ライブラリ使用

> 上記 Phase 87 計画詳細は **完了済**。記録として保持（実装内容は `docs/開発履歴/Phase_87.md`）。

---

## Phase 88 実装計画（確定版・2026-05-15 策定）

**目標**: GCP 月額コスト **¥3,000 → ¥300-500（83% 削減）** + 孤児SL再発防止 + 保守性向上
**所要**: 2-3週間（P0-P3 段階実装）
**前提**: Phase 87 全 Stage 完了済（Firestore永続化・SLMonitor 動作確認済）

### Phase 88 全項目（優先度別）

#### P0: 即時実施（リスク低・1-2日）

| ID | 内容 | 削減効果 | 実装ファイル |
|----|------|---------|-------------|
| **I1** | LOG_LEVEL `INFO` → `WARNING` | -¥100~200/月 | `.github/workflows/ci.yml:348-363` の env-vars |
| **I2** | Artifact Registry リテンション（30日以上前のイメージ削除） | -¥20~50/月 | `scripts/deployment/artifact-cleanup-policy.json` 新規 |

#### P1: 構造改善（1週目）

| ID | 内容 | 効果 | 実装規模 |
|----|------|------|---------|
| **H11** ⭐ | 孤児SL注文の再発防止（5分ループ検出 + 指数バックオフキャンセル） | 運用安定化（5/14 09:05事案の再発防止） | ~50行 |
| **I3** | min_instances=0 + Cloud Scheduler 起動 | **-¥2,400/月** | main.py に `/trigger` endpoint ~80行 |
| **L3** | Dead code 削除（executor.py:1436-1450 等） | 保守性 | ~100行削除 |
| **L2** | SUMMARY.md に Phase 83-87 追記 + Phase_88.md 新規 | ドキュメント整備 | ~200行追加 |

#### P2: 機能改善（2週目）

| ID | 内容 | 効果 |
|----|------|------|
| **M5** | 税務 SQLite を Firestore or GCS に永続化 | I3 (min=0) の前提クリア |
| **I4** | メモリ 1Gi → 512Mi | -¥150/月 |
| **I5** | bitbank API キャッシュ徹底（TTL見直し） | -¥20~50/月 (Egress) |

#### P3: 軽微改善（3週目）

| ID | 内容 |
|----|------|
| **M1** | Kelly基準のゼロサイズ理由を critical ログで明示 |
| **M2** | bitbank API rate_limit を thresholds.yaml 参照に統一（200msハードコード解消） |
| **M3** | TP/SL価格の丸め処理を明示化（コメント追加） |
| **M4** | 異常検知の時間帯別 Z スコア閾値（深夜 2.5 / 日中 3.0） |
| **L1** | Phase XXX コメント整理（一括スキャン + 古いものを削除） |

---

### Step 詳細

#### Step 88-P0a: I1 LOG_LEVEL 切替（即時 -¥100~200/月）

`.github/workflows/ci.yml:348-363` の `--update-env-vars` に `LOG_LEVEL=WARNING` を追加（現在 `INFO`）。
**リスクゼロ**（必要時 INFO に戻せる）。

#### Step 88-P0b: I2 Artifact Registry リテンション（即時 -¥20~50/月）

新規 `scripts/deployment/artifact-cleanup-policy.json`:
- 30日以上前のイメージ自動削除（`olderThan: "2592000s"`）
- 最新タグ10件は保持（`mostRecentVersions.keepCount: 10`）

適用: `gcloud artifacts repositories set-cleanup-policies crypto-bot-repo`

#### Step 88-P1a: H11 孤児SL注文の再発防止（最重要）

**背景**: 2026-05-14 09:05 TP約定後の SL キャンセル試行が bitbank エラー 70004（INACTIVE状態遷移中）で失敗し、12時間孤児SLとして残った。手動キャンセルで解決済。

**修正**: `src/trading/execution/tp_sl_manager.py:ensure_tp_sl_for_existing_positions`

既存の Phase 87 C5 health check ループ内に追加:
- ポジション無し かつ stop/stop_limit 注文有り → 孤児SL検出
- 指数バックオフ（1s/2s/4s）で cancel_order をリトライ
- 70004 エラー時は次サイクル（5分後）で再試行

**設定追加**: `config/core/thresholds.yaml`
```yaml
position_management.stop_loss.orphan_scan:
  enabled: true
  cancel_max_retries: 3
  cancel_base_delay_seconds: 1.0
```

#### Step 88-P1b: I3 min_instances=0 + Cloud Scheduler（-¥2,400/月）

**最大の変更**。`main.py` を「リクエスト駆動」に再構築:
- Flask アプリ追加（`/trigger` endpoint + `/health` endpoint）
- 既存の常時稼働モードは `MODE=continuous` で維持（ペーパー/開発用）
- `MODE=trigger` で Cloud Run + Cloud Scheduler 連携

Cloud Scheduler ジョブ作成（5分間隔）+ Cloud Run on-demand 化:
```bash
gcloud scheduler jobs create http crypto-bot-trigger ...
gcloud run services update crypto-bot-service-prod --min-instances=0 --max-instances=2 --timeout=300
```

**検証ガード**: 起動時 Firestore 接続失敗で `EMERGENCY_STOP` に遷移

#### Step 88-P1c: L3 Dead code 削除

**削除対象**:
- `src/trading/execution/executor.py:1436-1450` 移動済みコメント（15行）
- `logs/orphan_sl_orders.json`（Phase 59.6・H11 で対応済）
- `data/sl_state.json`（Phase 68.4・H4 で Firestore 化済）
- 0byte DB ファイル: `data/trades.db`, `data/live_trades.db`
- `.dockerignore` 新規作成（防御的）

**保留**: `src/data/bitbank_client.py:1197-1219` stop_limit フォールバック（Phase 87 H3 で再活用される可能性）

#### Step 88-P1d: L2 ドキュメント整備

- `docs/開発履歴/SUMMARY.md`: Phase 83-87 サマリー追加（~200行）
- `docs/開発履歴/Phase_88.md` 新規（Phase 88 完了後）
- `CLAUDE.md` / `README.md` のしおり更新

#### Step 88-P2: I4 / I5 / M5

**I4 (メモリ 1Gi → 512Mi)**: ペーパー30分稼働で <400MB 確認後に変更
**I5 (API キャッシュ徹底)**: `src/data/data_cache.py` の TTL 60s → 120s、重複呼び出し排除
**M5 (税務SQLite Firestore化)**: `tax/trade_history.db` を Firestore コレクション `tax_history` に移行（既存データマイグレーションスクリプト作成）

#### Step 88-P3: M1-M4 / L1 軽微改善

---

### Phase 88 リスクと緩和策

| 順位 | リスク | 緩和策 |
|------|--------|--------|
| **高** | I3 Cold start レイテンシ → 5分間隔の取引機会逸失 | ステージング 1週間検証 |
| **高** | I3 Firestore 接続失敗時の取引判断ミス | 起動時失敗で EMERGENCY_STOP に遷移するガード |
| **中** | H11 cancel リトライで bitbank API レート制限抵触 | 3回失敗時は記録のみ、次サイクルで再試行 |
| **中** | M5 税務DB移行で既存データ消失 | バックアップ後にマイグレーション、ステージング先行 |
| **低** | I4 メモリ 512Mi で OOM | ペーパー30分稼働で確認、問題あれば 1Gi に戻す |
| **低** | L3 Dead code 削除で参照エラー | 削除前 grep 確認、テストカバレッジ維持 |

---

### Phase 88 検証手順

```bash
# 共通: 品質チェック
bash scripts/testing/checks.sh

# P0 検証
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 \
  --format="value(spec.template.spec.containers[0].env)" | grep LOG_LEVEL

# P1 検証
gcloud logging read 'resource.type=cloud_run_revision AND textPayload=~"Phase 88 H11"' --limit=20
gcloud scheduler jobs list --location=asia-northeast1

# コスト削減効果
gcloud billing accounts get-spend-information --account=<ACCOUNT_ID> ...
```

**期待値**: Before ¥3,000/月 → After ¥300-500/月（**83% 削減**）

---

### Phase 88 想定スケジュール

| 段階 | 期間 | 内容 | 削減効果 |
|------|------|------|---------|
| **P0** | Day 1-2 | I1 + I2 即時削減 | -¥120~250/月 |
| **P1** | Day 3-9 | H11 + I3 + L2/L3 | -¥2,400/月 |
| **P2** | Day 10-15 | I4 + I5 + M5 | -¥170/月 |
| **P3** | Day 16-21 | M1-M4 + L1 | 保守性向上 |

→ **Phase 88 完了目標**: 着手から約 21 日（3週間）

完了後、Phase 89 (Webリサーチ統合: Purged K-Fold + Fractional Kelly + OFI + Funding Rate) へ進む。

詳細プラン: `~/.claude/plans/phase-nifty-pizza.md`

---

## 緊急対応（並行・ユーザー実施）

bitbank UI で手動SL設置:
- side: sell, type: stop, amount: 0.015
- trigger: 12,732,347 or 現価格ベースで再計算

→ Phase 87 実装中も裸ポジ解消

---

## 検証方法

### Phase 87 P0 実装後
```bash
bash scripts/testing/checks.sh
# 全テスト成功・75%+カバレッジ・新規テスト成功
```

### ペーパートレード統合検証
```bash
bash scripts/paper/run_paper.sh
# 意図的に bitbank UI で SL注文をキャンセル → 5分以内に bot が検出・再配置
# CANCELED_UNFILLED 検出動作確認
```

### 本番デプロイ後24-48時間観測
```bash
python3 scripts/live/standard_analysis.py --hours 24
# 期待: SLカバレッジ100%、CANCELED_UNFILLED自動復旧成功ログ
```

---

## 期待される効果

| 改善項目 | Before | After |
|---------|--------|------|
| SL CANCELED_UNFILLED 検出 | 完全未実装 | 5分以内に検出・即時成行決済 |
| 稼働中のSL消失対応 | 警告ログのみ | 自動再配置 or 緊急成行決済 |
| 価格急変時のSL約定 | stop で失敗 | stop_limit + buffer で確実 |
| SL超過タイムアウト | 未実装 | 24hで強制決済 |
| ML信頼度の意味 | max(p_0,p_1,p_2) で誤解 | predicted_class_proba で正確 |
| TP Maker タイムアウト | 重複TP配置リスク | 自動キャンセル → 次ループ新規 |
| ML予測失敗時 | サーキットブレーカー無し | DummyModel 検出 → critical ログ |
| 連敗保護 | 即解除→再連敗リスク | RECOVERY_TESTING 経由で段階復帰 |
| ドローダウン状態 | Container再起動でリセット | Firestore で永続化 |
| 品質フィルタ閾値 | 一律0.65 で採算ラインと矛盾 | レジーム別で採算と整合 |
| 戦略シグナル完全性 | 0埋め silent | アサート + critical ログ |
| 分析スクリプト | missing_sl_detected が誤検出 | 件数ベースで正確 |
| Dead code | ~500行残存 | コアロジックのみ |
| 構造的SL配置漏れ | 未解決 | 構造的に防止 |

---

## 詳細プラン

実装計画の詳細: `/Users/nao/.claude/plans/golden-spinning-liskov.md`

---

## Phase 89-β/γ/δ 中長期計画（Webリサーチ結果に基づく）

> **進め方（ユーザー確定方針）**:
> - Phase 87/88/89-α 完了 → 都度 Phase 89-β+ を再計画
> - まず基盤を固め、安定動作を確認してから拡張
> - Phase 90 (PPO 強化学習) は Phase 89-δ 完了時の Sharpe比達成状況で再検討
>
> **Phase 89 内の進め方**:
> - **89-α** (GCP コスト削減): Stage 1+3 完了済 / Stage 2 はコスト実測後判断
> - **89-β** (シグナル品質向上): 89-α 完了後着手・即時効果
> - **89-γ** (時系列予測 + センチメント): 89-β 完了後着手・中規模実装
> - **89-δ** (マーケットマイクロ構造): 89-γ 完了後着手・WebSocket 等

### 背景

最新MLbot技術（2024-2026）の Webリサーチで判明した既存botとのギャップを段階的に解消し、年利10% → 15-18% を目指す。

### 既存bot vs 最新MLbot ギャップ分析

| 領域 | 既存bot | 最新MLbot技術 | ギャップ | 追加コスト |
|------|---------|--------------|--------|----------|
| 特徴量 | OHLCV由来37個 | + オーダーブック (OFI/VPIN/OBI) + ファンダ (Funding/OI/Fear&Greed) + センチメント (LLM) | ⭐⭐⭐⭐ | 0円可 |
| 時系列予測 | LGB/XGB/RF アンサンブル | Transformer (Informer/Autoformer) / N-BEATS / TFT | ⭐⭐⭐⭐ | 0円可（軽量版） |
| 検証手法 | Walk-Forward 単一回 | Purged K-Fold CV + CPCV + DSR | ⭐⭐⭐ | 0円 |
| ポジションサイジング | Kelly基準（機能不全） | Fractional Kelly + Volatility Targeting + CVaR | ⭐⭐⭐ | 0円 |
| レジーム検出 | 4段階ルールベース | HMM (3-5状態) + BOCPD | ⭐⭐⭐ | 0円 |
| 取引戦略 | レンジ型重視（トレンド型重み0%） | 強化学習 (PPO/TD3/SAC) + マルチタイムフレーム融合 | ⭐⭐⭐⭐ | 0円可（PPOはGPU要） |
| モデル監視 | 手動 | Drift Detection (KL/KS) + Automated Retraining | ⭐⭐⭐ | 0円 |
| 約定戦略 | Maker実装も Taker率100% | Smart Routing + Queue Position Modeling | ⭐⭐⭐ | 0円 |
| データ取得 | REST polling (5分間隔) | WebSocket real-time depth stream | ⭐⭐⭐ | 0円 |
| クロスアセット | BTC/JPY単一 | BTC-ETH相関 + Funding rate arbitrage | ⭐⭐⭐ | 0円可 |

---

### Phase 89-β: シグナル品質向上（即時着手・月額0円・1ヶ月）

**前提**: Phase 89-α (GCP コスト削減) Stage 1+3 完了済・コスト目標 ¥1,500 以下達成見込み

最も費用対効果が高く、現スケール（証拠金50万円・月額予算 Phase 89-α 後 ¥1,200-1,700）で確実に効果が出る項目。

#### P1 必須項目

1. **Purged K-Fold CV 導入**（López de Prado）
   - lookahead bias 完全排除、CPCV で統計信頼性向上、DSR テスト
   - 工数: 2週間、効果: 検証信頼性 +30%

2. **Fractional Kelly + Volatility Targeting**
   - Full Kelly → 0.5倍 (Half Kelly) で安定性向上
   - target_vol=20% で動的レバレッジ調整
   - 工数: 1週間、効果: Max DD -20%

3. **Drift Detection 基本実装**
   - KL divergence / Kolmogorov-Smirnov test
   - Slack/Discord 通知 or Cloud Logging アラート
   - 工数: 2週間、効果: 自動アラート機能化

4. **OFI (Order Flow Imbalance) 特徴量追加**
   - 37 → 47-50 特徴量に拡張
   - 既存 `data/orderbook/` を活用
   - 過去研究で 65-87% の価格分散説明率
   - 工数: 3日、効果: リターン +0.8-1.5%

5. **外部シグナル統合（無料API）**
   - Binance Funding Rate（買い圧/売り圧の先行指標）
   - Open Interest 変化率
   - Fear & Greed Index（alternative.me free）
   - 工数: 3-5日、効果: シグナル精度 +10-15%

#### P2 検討項目
6. **Optuna ハイパーパラメータ自動最適化**
   - 工数: 2週間、効果: 戦略パラメータ最適化

---

### Phase 89-γ: 時系列予測モデル + センチメント（2-3ヶ月・月額~300円）

Cloud Run 環境（メモリ512MB）で動作可能な軽量最新技術。

1. **N-BEATS 軽量版 試験導入**
   - GPU不要、メモリ ~50MB、推論時間 ~100ms
   - 既存 ProductionEnsemble に4つ目モデルとして追加
   - 工数: 4週間、効果: リターン +5-10%

2. ~~**LLM センチメント統合（Claude API）**~~ ❌ **不採用確定（2026-05-15）**
   - トークン課金（月 ¥30-150）の従量課金がユーザー方針「追加課金なし」と矛盾
   - **代替: Phase 89-β で Fear & Greed Index（無料 API）採用済** → シグナル精度 +5-10% 確保

3. **HMM レジーム検出（4 → 3-5状態細分化）**
   - hmmlearn (Python) で Gaussian HMM
   - 既存ルールベースの**補強**
   - 研究事例: Sharpe Ratio 0.8 → 1.9
   - 工数: 4-5日、効果: 年利 +1.0-2.0%

4. **Automated Retraining Pipeline**
   - Drift Detection trigger 連動
   - Shadow Deployment、自動ロールバック
   - 工数: 2週間、効果: 自動最適化

5. **VPIN 計算**
   - 流動性悪化・toxic flow の早期検知
   - 工数: 2-3日、効果: リスク管理 +0.5-1.0%

---

### Phase 89-δ: マーケットマイクロ構造（オーダーブック活用・月額0円）

1. **WebSocket depth stream 接続**
   - Bitbank `wss://stream.bitbank.cc/...`
   - REST polling (5秒) → WebSocket (100ms バッファ)
   - 工数: 3-4日、効果: 反応速度3-5秒 → 200-500ms

2. **OFI/OBI/Weighted Mid-Price 統合**
   - 既存特徴量と組み合わせて 50-55 特徴量
   - 多層レベル OFI (MLOFI) で精度向上
   - 工数: 1-2週間、効果: リターン +1-3%

3. **Maker 戦略の真の実装化（現状 Taker 100%）**
   - Queue Position Modeling（hftbacktest 参考）
   - post_only 価格の動的最適化
   - 工数: 2-3週間、効果: 年利 +0.5-1%

4. **BTC-ETH 相関活用**
   - Binance ETH/USDT データから 30-60日 rolling 相関
   - 相関急低下 → market stress → ポジション縮小
   - 工数: 1週間、効果: ドローダウン制御強化

---

### ~~Phase 90: 高度化・条件付き実装~~ ❌ **見送り確定（2026-05-15）**

**見送り理由**:
1. **GPU 追加課金 月 ¥500-1,000**（ユーザー方針「追加課金なし」と矛盾）
2. PPO 強化学習は**期待値プラス bot 前提** — 現状期待値マイナス bot で学習すると誤った報酬信号で**損失加速リスク**
3. 元計画でも「Sharpe 比 > 2.0 達成後の条件付き再検討」と明記 → Phase 89-δ 完了後に Sharpe 比達成していれば再考の余地

**見送りでカバーできない領域**:
- PPO で +3-5% / マルチペア +2-5% / Transformer +α
- これらは「年利 17-20%」を目指す上振れシナリオで、Phase 89-δ で「年利 15-18%」達成すれば十分

**将来再検討する場合の条件**（参考・現時点では未定）:
- Phase 89-δ 完了時に Sharpe 比 > 2.0 達成
- 3 ヶ月実機で月利 1.5% 以上の安定運用
- 追加課金許容のユーザー判断

---

### 段階的導入ロードマップ（2026-05-15 確定版）

| 期間 | Phase | 内容 | 期待 Sharpe | 期待年利 |
|------|-------|------|------------|--------|
| Week 1-3 | **Phase 87** ✅ | 決済システム再構築（C1-C5, H1-H10） | 維持 | 維持 |
| Week 4-6 | **Phase 88** ✅ | 運用基盤・クリーンアップ（M1-M5, L1-L3） | 1.5 | 10% (現状) |
| Week 7 | **Phase 89-α** ⏳ | GCP コスト削減 (Stage 1+3 デプロイ済・Stage 2 pending) | 維持 | 維持 |
| Week 8-9 | **Phase 89-β** | シグナル品質向上 (Purged K-Fold + Fractional Kelly + OFI + Funding + **Fear & Greed**) | 1.8-2.0 | 12-13% |
| Week 10-12 | **Phase 89-γ** | N-BEATS + HMM + VPIN（~~LLM~~ 削除済・Fear & Greed で代替） | 2.0-2.3 | 14-16% |
| Week 13-15 | **Phase 89-δ** | WebSocket + Maker戦略 + BTC-ETH 相関 | 2.2-2.5 | **15-18%** ⭐ 最終目標 |
| ~~Month 10+~~ | ~~**Phase 90**~~ | ~~PPO / マルチペア / Transformer~~ | - | **見送り確定** |

---

### Phase 89-β/γ/δ で参照すべきオープンソース・論文

- **Marcos Lopez de Prado**「Advances in Financial Machine Learning」（Triple Barrier、Purged K-Fold の原典）
- **N-BEATS**: https://github.com/philipperemy/n-beats（軽量、Cloud Run動作可）
- **Microsoft Qlib**: https://github.com/microsoft/qlib（Alpha158 特徴セット参考）
- **FinRL**: https://github.com/AI4Finance-Foundation/FinRL（強化学習）
- **Freqtrade**: https://github.com/freqtrade/freqtrade（戦略パイプライン参考）
- **hftbacktest**: https://github.com/nkaz001/hftbacktest（Queue Position Modeling）
- **DeepLOB**: https://arxiv.org/abs/1808.03668（オーダーブック CNN）
- **VPIN**: https://www.quantresearch.org/VPIN.pdf

---

### Phase 87/88 への影響（保持すべき設計）

Phase 89-β/γ/δ で追加される機能は、Phase 87/88 の以下の設計を**前提**として動作:
- **Registry Pattern**: 新戦略・新ML モデルの追加が容易
- **thresholds.yaml 一元化**: 新特徴量・新閾値もここで管理
- **メタラベリング品質フィルタ**: 新モデルもメタラベリングで品質保証
- **Firestore 永続化（Phase 87 H4-5）**: HMM 状態、Drift Detection 結果も永続化
- **SLMonitor（Phase 87 P0a）**: 新戦略でも CANCELED_UNFILLED 検出が自動

→ Phase 87/88 を「土台」として、Phase 89-β/γ/δ は段階的に積み上げる構造

---

### Phase 89-β/γ/δ 期待効果サマリー（2026-05-15 確定版）

| 項目 | Phase 88完了時 | Phase 89-α 完了時 | Phase 89-β 完了時 | Phase 89-γ 完了時 | Phase 89-δ 完了時 |
|------|--------------|------------------|------------------|------------------|------------------|
| 年利 | 10% | 維持 | 12-13% | 14-16% | **15-18%** ⭐ |
| Sharpe比 | 1.5 | 維持 | 1.8-2.0 | 2.0-2.3 | 2.2-2.5 |
| Max DD | 8-10% | 維持 | 6-7% | 5-6% | 4-5% |
| 特徴量数 | 37 | 37 | 47-50 (+OFI+Funding+Fear&Greed) | 50-55 (+HMM+VPIN) | 55-60 (+OFI多層+BTC-ETH 相関) |
| **月額追加コスト** | **¥0** | **¥0** | **¥0**（無料 API のみ） | **¥0**（LLM 不採用） | **¥0** |
| GCP 月額 | ¥3,000 | ¥1,400-1,700 | 同 | 同 | 同 |

**Phase 90 (PPO 強化学習) は見送り確定** — GPU 課金 ¥500-1,000/月 + 期待値マイナス bot で逆効果リスクのため

---

**最終更新**: 2026年5月15日 - Phase 89-α Stage 1+3 デプロイ完了 + Phase 89-β/γ/δ 中長期計画
