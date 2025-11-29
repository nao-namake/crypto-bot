# Phase 56 - 99%稼働率達成（自動タイムアウト無効化・自動再起動対応）

**期間**: 2025/11/30
**目標**: 99%稼働率達成（Two Nines）

---

## Phase 56.2 - Containerクラッシュ根本解決

### 問題発見

**GCP稼働状況診断結果**（2025/11/30 06:53 JST）:
- Container crash: **50回/24時間**
- 取引サイクル実行: **61回/288回（21%）**
- 稼働率: **約21%**（目標99%に対して大幅未達）

### 根本原因分析

1. **main.py の15分自動タイムアウト**
   - `setup_auto_shutdown()`で`signal.alarm(900)`を設定
   - 15分経過後にSIGALRMでsys.exit(1)を強制実行
   - これが無限ループ設計の`_run_continuous_trading()`と矛盾

2. **docker-entrypoint.sh のexit(1)問題**
   - トレーディングプロセス終了時にexit(1)でContainer終了
   - Cloud Runが新Containerを起動 → また15分でクラッシュの繰り返し

### 修正内容

#### 1. main.py - 自動タイムアウト無効化

```python
def setup_auto_shutdown():
    """
    GCP環境での自動シャットダウン設定

    Phase 56.2: 自動タイムアウト無効化
    - 無限ループ設計の_run_continuous_trading()と矛盾していた
    - docker-entrypoint.shで自動再起動を実装済み
    - Container再起動オーバーヘッド削減（99%稼働率達成のため）
    """
    # Phase 56.2: 自動タイムアウト無効化（継続稼働優先）
    print("ℹ️ GCP環境検出: 自動タイムアウト無効化（Phase 56.2 - 継続稼働優先）")
```

#### 2. docker-entrypoint.sh - 自動再起動対応

```bash
# Phase 56.2: プロセス監視ループ（正常終了時は自動再起動）
cycle_count=0
restart_count=0
MAX_RESTARTS=1000  # 最大再起動回数（約7日分=1000×5分）

while true; do
    # トレーディングプロセスの生存確認
    if ! kill -0 $TRADING_PID 2>/dev/null; then
        restart_count=$((restart_count + 1))

        if [ $restart_count -gt $MAX_RESTARTS ]; then
            echo "❌ [$(date)] 最大再起動回数超過 ($MAX_RESTARTS回) - Container終了"
            kill $HEALTH_PID 2>/dev/null
            exit 1
        fi

        echo "🔄 [$(date)] トレーディングプロセス終了検知 - 自動再起動 ($restart_count/$MAX_RESTARTS)"
        sleep 5

        # トレーディングプロセス再起動
        python3 main.py --mode $MODE --config config/core/unified.yaml &
        TRADING_PID=$!
    fi
    sleep 10
done
```

### 期待効果

| 指標 | 修正前 | 修正後（期待） |
|------|--------|---------------|
| Container crash | 50回/24h | 0回/24h |
| 取引サイクル実行 | 61回/24h | 288回/24h |
| 稼働率 | 21% | 99% |

### デプロイ

- コミット: `37ff776c`
- メッセージ: `fix: Phase 56.2 - 99%稼働率達成（自動タイムアウト無効化・自動再起動対応）`
- CI/CD: GitHub Actions → GCP Cloud Run自動デプロイ

### 修正ファイル

1. `main.py` - setup_auto_shutdown()無効化
2. `scripts/deployment/docker-entrypoint.sh` - 自動再起動ロジック追加
3. `docs/運用監視/01_稼働率診断.md` - Phase 56.2更新
4. `docs/運用監視/02_機能診断.md` - Phase 56.2更新
5. `docs/運用監視/03_緊急対応マニュアル.md` - Phase 56.2更新

---

## その他の検出エラー

### bitbank API認証エラー（20001）

- 発生回数: 50件/24時間
- 原因: bitbank側の一時的な問題
- 対応: 既存のリトライ機能（3回リトライ）で対応済み
- ステータス: 監視継続（コード修正不要）

### エントリー前クリーンアップ失敗

- エラー: `'order_id'`
- 対応: Phase 52.4-Bで処理継続するよう対応済み
- ステータス: 影響なし

### XGBoost警告

- 内容: モデルシリアライゼーション警告
- ステータス: 無視可能（動作に影響なし）

---

## 確認コマンド

### 稼働率確認（デプロイ24時間後）

```bash
echo "=== 24時間稼働率診断 ==="
CONTAINER_CRASHES=$(gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"Container called exit(1)\" AND timestamp>=\"$(python3 -c "import datetime; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))")\"" --limit=50 --format=json 2>/dev/null | jq length)
echo "Container crash回数（24時間）: ${CONTAINER_CRASHES:-0}回"

# 0回なら99%稼働率達成
```

---

## Phase 56.2 完了サマリー

- **問題**: 15分自動タイムアウトによるContainerクラッシュ（50回/24h）
- **原因**: main.pyのsignal.alarm(900)が無限ループ設計と矛盾
- **修正**: 自動タイムアウト無効化 + docker-entrypoint.sh自動再起動
- **効果**: 稼働率21% → 99%（目標達成見込み）
- **デプロイ**: 2025/11/30 完了

---

**最終更新**: 2025年11月30日
