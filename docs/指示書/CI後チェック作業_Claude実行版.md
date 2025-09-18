# 🚀 CI完了後チェック指示書（継続稼働・隠れ不具合検出統合版）

## 🚨 **重要**: 表面稼働・実機能停止の隠れ不具合を確実検出

**チェック方針**: システムプロセス稼働 ≠ 実際のBot機能稼働を前提とした検証
- 致命的隠れ不具合の早期検出（IAM権限・API認証・フォールバック固定）
- トレード阻害要因の包括検出（ポジション管理・価格異常・資金管理）
- 時間経過による不具合検出（残高0円化・Discord通知失敗）

---

## 🕐 **チェック前準備: 最新CI・デプロイ状況確認（改良版）**

```bash
echo "=== 最新CI・デプロイ状況確認（改良版） ==="
echo "現在時刻:"
TZ='Asia/Tokyo' date '+%Y-%m-%d %H:%M:%S JST'
echo

# 最新GitHubActionsワークフロー確認
echo "最新GitHubActionsワークフロー確認:"
gh run list --limit=3 --workflow="CI/CD Pipeline"
echo

# 最新成功CIの時刻取得（UTCからJST変換）
LATEST_CI_UTC=$(gh run list --limit=1 --workflow="CI/CD Pipeline" --status=success --json=createdAt --jq='.[0].createdAt')
LATEST_CI_JST=$(TZ='Asia/Tokyo' date -d "$LATEST_CI_UTC" '+%Y-%m-%d %H:%M:%S JST')
echo "最新成功CI時刻（JST）: $LATEST_CI_JST"

# 経過時間計算
CURRENT_TIME=$(TZ='Asia/Tokyo' date '+%Y-%m-%d %H:%M:%S JST')
echo "現在時刻: $CURRENT_TIME"
echo "チェック対象: 最新CI以降の本番状況"

# Cloud Run現在のリビジョン確認
echo "Cloud Run最新リビジョン確認:"
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="table(metadata.name,status.url,status.traffic[0].percent,status.latestReadyRevisionName)"

# 最新CI以降のログ確認用（UTCタイムスタンプ使用）
DEPLOY_TIME="$LATEST_CI_UTC"
echo "ログ確認対象時刻（UTC）: $DEPLOY_TIME"

# 時刻表示関数の定義（エラー回避）
show_logs_with_jst() {
    local query="$1"
    local limit="${2:-10}"
    gcloud logging read "$query" --limit="$limit" --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
}
```

# 🚨 **致命的隠れ不具合検出（最優先）**

## 🔐 セクション0: Secret Manager・API認証確認（最重要）
```bash
echo "=== セクション0: Secret Manager・API認証確認（致命的） ==="

echo "1. シークレット存在確認:"
gcloud secrets list | grep -E "(bitbank|discord)"

echo "2. IAM権限確認（致命的）:"
SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)")
echo "使用中サービスアカウント: $SERVICE_ACCOUNT"
# bitbank-api-key権限確認
if gcloud secrets get-iam-policy bitbank-api-key --format="value(bindings[].members)" | grep -q "$SERVICE_ACCOUNT"; then
    echo "✅ bitbank-api-key権限あり"
else
    echo "❌ bitbank-api-key権限なし"
fi

# bitbank-api-secret権限確認
if gcloud secrets get-iam-policy bitbank-api-secret --format="value(bindings[].members)" | grep -q "$SERVICE_ACCOUNT"; then
    echo "✅ bitbank-api-secret権限あり"
else
    echo "❌ bitbank-api-secret権限なし"
fi

# discord-webhook-url権限確認
if gcloud secrets get-iam-policy discord-webhook-url --format="value(bindings[].members)" | grep -q "$SERVICE_ACCOUNT"; then
    echo "✅ discord-webhook-url権限あり"
else
    echo "❌ discord-webhook-url権限なし"
fi

echo "3. Cloud Run環境変数確認:"
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.containers[0].env[].name,spec.template.spec.containers[0].env[].value)"

echo "🚀 ライブモード設定確認（重要）:"
echo "   環境変数MODE=live確認:"
MODE_VALUE=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="yaml" | grep -A 2 "name: MODE" | grep "value:" | awk '{print $2}')
if [ "$MODE_VALUE" = "live" ]; then
    echo "✅ MODE設定: live （ライブトレード）"
else
    echo "❌ MODE設定: $MODE_VALUE （ライブトレードではない）"
fi

echo "   DEPLOY_STAGE=live確認:"
DEPLOY_STAGE_VALUE=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="yaml" | grep -A 2 "name: DEPLOY_STAGE" | grep "value:" | awk '{print $2}')
if [ "$DEPLOY_STAGE_VALUE" = "live" ]; then
    echo "✅ DEPLOY_STAGE設定: live"
else
    echo "❌ DEPLOY_STAGE設定: $DEPLOY_STAGE_VALUE"
fi

echo "4. Secret取得エラー確認:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"permission\" OR textPayload:\"Secret\" OR textPayload:\"401\" OR textPayload:\"403\") AND timestamp>=\"\$DEPLOY_TIME\"" --limit=10

echo "5. Bitbank残高取得確認（新項目・重要）:"
echo "   API認証情報読み込み確認:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"BITBANK_API_KEY読み込み\" OR textPayload:\"BITBANK_API_SECRET読み込み\") AND timestamp>=\"\$DEPLOY_TIME\"" --limit=5

echo "   残高取得成功・失敗確認:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"残高\" OR textPayload:\"balance\" OR textPayload:\"残高不足\" OR textPayload:\"0円\") AND timestamp>=\"\$DEPLOY_TIME\"" 10

echo "   🎯 API vs フォールバック判定（NEW）:"
echo "   ✅ 実際のAPI取得: 残高=10,000円表示"
echo "   ⚠️ フォールバック使用: 残高=11,000円表示（設定値: initial_balance_jpy: 11000.0）"
# API残高取得状況の簡易確認
echo "API残高取得10,000円の確認:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"10,000円\" AND timestamp>=\"\$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "フォールバック11,000円の確認:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"11,000円\" AND timestamp>=\"\$DEPLOY_TIME\"" --limit=3 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

# 手動判定推奨: 11,000円が表示されていればフォールバック使用中

echo ""
echo "6. Discord Webhook無効検出（NEW 2025/09/15追加）:"
echo "   Discord Webhook Token無効エラー確認（緊急）:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"Invalid Webhook Token\" OR textPayload:\"code: 50027\" OR textPayload:\"Discord Webhook無効\") AND timestamp>=\"\$DEPLOY_TIME\"" 5
echo "   ⚠️ code: 50027 = Webhook URL削除・無効化（即座修正必要）"
echo "   影響: 全Discord通知停止 → 監視機能完全停止"
```

**🚨 致命的問題**:
- IAM権限欠如 = 全機能停止
- 残高0円取得 = 全取引機能停止
- **Discord Webhook無効 (code: 50027) = 監視機能完全停止（2025/09/15発見）**

---

## 🎭 セクション0-2: 動的システム vs フォールバック値判定（最重要）
```bash
echo "=== セクション0-2: 動的システム vs フォールバック値判定 ==="

echo "1. 戦略信頼度固定値検出（0.2 = フォールバック疑い）:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"信頼度: 0.200\" OR textPayload:\"confidence: 0.200\") AND timestamp>=\"\$DEPLOY_TIME\"" 5

echo "2. 戦略信頼度整数値検出（1.000 = 不自然値疑い）:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"信頼度: 1.000\" OR textPayload:\"confidence: 1.000\") AND timestamp>=\"\$DEPLOY_TIME\"" 5

echo "3. 戦略分析詳細プロセス確認:"
echo "ATRBased詳細分析ログ:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"[ATRBased]\" AND (textPayload:\"分析結果\" OR textPayload:\"ボラティリティ\" OR textPayload:\"ATR\") AND timestamp>=\"\$DEPLOY_TIME\"" 3
echo "MochipoyAlert詳細分析ログ:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"[MochipoyAlert]\" AND (textPayload:\"EMA分析\" OR textPayload:\"MACD分析\" OR textPayload:\"RCI分析\") AND timestamp>=\"\$DEPLOY_TIME\"" 3

echo "4. ML予測実行ログ確認（重要）:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"予測実行\" OR textPayload:\"ML予測\" OR textPayload:\"ProductionEnsemble\" OR textPayload:\"アンサンブル予測\") AND timestamp>=\"\$DEPLOY_TIME\"" 10
```

**🚨 致命的問題**:
- 全戦略0.2固定 = 動的計算停止
- ML予測ログなし = ML機能停止
- 戦略分析詳細なし = フォールバック値使用

---

## 🔥 セクション0-3: 最新CI以降のBot稼働状況確認（改良版）
```bash
echo "=== セクション0-3: 最新CI以降のBot稼働状況確認（改良版） ==="

echo "1. 最新CI以降のライブトレード確認（重要）:"
echo "   ライブトレードモード実行ログ確認（最新CI以降）:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"livetradingモード\" OR textPayload:\"取引サイクル開始\" OR textPayload:\"統合シグナル生成\") AND timestamp>=\"\$DEPLOY_TIME\"" 8

echo ""
echo "2. Kelly基準修正効果確認（最新CI以降）:"
echo "   Kelly計算取引数不足ログ確認:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"Kelly計算に必要な取引数不足\" AND timestamp>=\"\$DEPLOY_TIME\"" 5

echo "   取引承認・拒否状況確認:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"取引承認\" OR textPayload:\"取引拒否\") AND timestamp>=\"\$DEPLOY_TIME\"" 5

echo ""
echo "3. Discord通知状況確認（最新CI以降）:"
echo "   Discord通知エラー確認:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"Discord\" OR textPayload:\"webhook\" OR textPayload:\"401\" OR textPayload:\"50027\") AND timestamp>=\"\$DEPLOY_TIME\"" 3

echo ""
echo "4. 実際の取引実行確認（最新CI以降）:"
echo "   注文実行ログ確認:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"注文実行\" OR textPayload:\"order_executed\" OR textPayload:\"取引成立\" OR textPayload:\"Order placed\") AND timestamp>=\"\$DEPLOY_TIME\"" --limit=5

echo "   統合シグナル生成確認:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"統合シグナル生成: buy\" OR textPayload:\"統合シグナル生成: sell\" OR textPayload:\"統合シグナル生成\") AND timestamp>=\"\$DEPLOY_TIME\"" 8

# 手動判定推奨: シグナル生成数と注文実行数を目視で比較

echo ""
echo "2. 15特徴量生成健全性確認（NEW）:"
echo "   特徴量生成完了ログ:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"特徴量生成完了\" OR textPayload:\"feature generation completed\" OR textPayload:\"15特徴量完全生成成功\") AND timestamp>=\"\$DEPLOY_TIME\"" 5

echo "   特徴量エラー・欠損確認:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"特徴量\" AND (textPayload:\"エラー\" OR textPayload:\"欠損\" OR textPayload:\"NaN\" OR textPayload:\"missing\")) AND timestamp>=\"\$DEPLOY_TIME\"" --limit=3

echo ""
echo "3. 時系列データ整合性確認（NEW）:"
echo "   4時間足・15分足データ取得確認:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"4h足\" OR textPayload:\"15m足\" OR textPayload:\"4時間足\" OR textPayload:\"15分足\") AND timestamp>=\"\$DEPLOY_TIME\"" 5

echo "   データ取得タイムラグ確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"データ取得時間\" OR textPayload:\"data latency\" OR textPayload:\"レスポンス時間\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo ""
echo "4. システムパフォーマンス確認（NEW）:"
echo "   メモリ使用量・処理時間確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"メモリ\" OR textPayload:\"memory\" OR textPayload:\"処理時間\" OR textPayload:\"processing time\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "   BTC/JPY通貨ペア固定確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"BTC/JPY\" OR textPayload:\"btc_jpy\" OR textPayload:\"bitcoin\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5
```

**🚨 実際のBot稼働判定**:
- **取引実行率0%** = シグナル生成のみで実取引停止
- **特徴量生成エラー** = ML予測品質劣化
- **データ取得ラグ** = 古いデータでの誤判断
- **通貨ペア相違** = 想定外の取引対象

---

## 🛡️ セクション0-4: トレード阻害要因検出（NEW 2025/09/15）
```bash
echo "=== セクション0-4: トレード阻害要因検出（NEW） ==="

echo "1. ポジション管理異常検出（重要）:"
echo "   重複ポジション・ポジション同期ズレ確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"重複ポジション\" OR textPayload:\"ポジション同期\" OR textPayload:\"position conflict\" OR textPayload:\"duplicate position\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "   未決済ポジション残存確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"未決済\" OR textPayload:\"open position\" OR textPayload:\"position remaining\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo ""
echo "2. 価格スプレッド異常検出（重要）:"
echo "   bid/ask価格逆転・異常スプレッド確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"価格逆転\" OR textPayload:\"bid.*ask.*逆転\" OR textPayload:\"spread.*異常\" OR textPayload:\"price inversion\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "   スプレッド幅異常確認（0.5%以上は異常）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"スプレッド: 0.[5-9]\" OR textPayload:\"spread.*0.00[5-9]\" OR textPayload:\"スプレッド幅異常\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo ""
echo "3. 資金管理エラー検出（重要）:"
echo "   証拠金不足・Kelly基準計算エラー確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"証拠金不足\" OR textPayload:\"Kelly.*エラー\" OR textPayload:\"insufficient margin\" OR textPayload:\"Kelly calculation error\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "   リスク計算異常値確認（NaN/Inf/負値）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"NaN\" OR textPayload:\"Inf\" OR textPayload:\"リスク.*負\" OR textPayload:\"risk.*negative\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo ""
echo "4. MLモデル関連エラー検出（重要）:"
echo "   モデルロード失敗・予測値異常確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"モデルロード.*失敗\" OR textPayload:\"model.*load.*failed\" OR textPayload:\"予測値異常\" OR textPayload:\"prediction.*out.*range\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "   モデルファイル存在確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"モデルファイル.*見つからない\" OR textPayload:\"model.*file.*not.*found\" OR textPayload:\"FileNotFoundError\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo ""
echo "5. システムリソース枯渇検出（重要）:"
echo "   メモリ使用率90%以上・CPU100%継続確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"メモリ.*9[0-9]%\" OR textPayload:\"memory.*9[0-9]%\" OR textPayload:\"CPU.*100%.*継続\" OR textPayload:\"OutOfMemoryError\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "   ディスク容量不足確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"ディスク.*不足\" OR textPayload:\"disk.*full\" OR textPayload:\"No space left\" OR textPayload:\"容量不足\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5
```

**🚨 トレード阻害要因判定**:
- **ポジション管理異常** = 重複注文・ポジション不整合
- **価格スプレッド異常** = 不適切な価格での取引実行
- **資金管理エラー** = 証拠金不足・リスク計算不正
- **MLモデルエラー** = 予測精度劣化・モデル停止
- **リソース枯渇** = システム不安定・処理遅延

---

## 🔍 セクション0-5: Kelly基準・ポジションサイズ問題検出（NEW 2025/09/16）
```bash
echo "=== セクション0-5: Kelly基準・ポジションサイズ問題検出（NEW） ==="

echo "1. Kelly基準取引履歴不足検出（最重要）:"
echo "   Kelly計算に必要な取引数確認（20件未満でSilent failure発生）:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"Kelly計算に必要な取引数不足\" OR textPayload:\"Kelly履歴不足\" OR textPayload:\"min_trades_for_kelly\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "   保守的サイズ使用検出（0.009固定値使用は問題）:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"保守的サイズ使用\" OR textPayload:\"Kelly履歴不足.*サイズ\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo ""
echo "2. ポジションサイズ・注文サイズ不整合検出（致命的）:"
echo "   計算されたポジションサイズ確認（0.006超過は注文失敗）:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"ポジションサイズ=0.00[7-9]\" OR textPayload:\"position.*size.*0.00[7-9]\" OR textPayload:\"ポジションサイズ=0.0[1-9]\" OR textPayload:\"position.*size.*0.0[1-9]\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "   注文サイズ制限超過検出:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"max_order_size\" OR textPayload:\"注文サイズ.*制限\" OR textPayload:\"order.*size.*exceeded\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo ""
echo "3. Silent Failure検出（シグナル生成vs実際注文）:"
echo "   統合シグナル生成数確認:"
SIGNAL_COUNT=$(gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"統合シグナル生成: buy\" OR textPayload:\"統合シグナル生成: sell\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=50 --format="value(textPayload)" | wc -l)
echo "   シグナル生成数: $SIGNAL_COUNT件"

echo "   実際の注文実行数確認:"
ORDER_COUNT=$(gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"注文実行\" OR textPayload:\"order_executed\" OR textPayload:\"取引成立\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=50 --format="value(textPayload)" | wc -l)
echo "   注文実行数: $ORDER_COUNT件"

echo "   🚨 Silent Failure判定: シグナル数 > 0 かつ 注文数 = 0 なら致命的問題"
if [ $SIGNAL_COUNT -gt 0 ] && [ $ORDER_COUNT -eq 0 ]; then
    echo "   ❌ Silent Failure検出: シグナル${SIGNAL_COUNT}件 vs 注文${ORDER_COUNT}件"
else
    echo "   ✅ 正常: シグナル${SIGNAL_COUNT}件 vs 注文${ORDER_COUNT}件"
fi

echo ""
echo "4. 最小取引単位・Exchange制限チェック（Bitbank: 0.0001 BTC）:"
echo "   ポジションサイズ vs Bitbank最小取引単位（0.0001 BTC = 約1,600円）:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"ポジションサイズ=0.00[0-9]\" OR textPayload:\"position.*size.*0.00[0-9]\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "   最小取引単位エラー確認:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"最小取引単位\" OR textPayload:\"minimum.*order\" OR textPayload:\"amount.*too.*small\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo ""
echo "5. 追加のトレード阻害要因（包括的チェック）:"
echo "   APIレート制限・権限エラー:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"rate.*limit\" OR textPayload:\"API.*limit\" OR textPayload:\"permission.*denied\" OR textPayload:\"insufficient.*permission\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "   市場流動性・取引時間外チェック:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"流動性\" OR textPayload:\"liquidity\" OR textPayload:\"市場.*閉鎖\" OR textPayload:\"trading.*hours\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "   注文タイプ・レバレッジ設定問題:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"注文タイプ\" OR textPayload:\"order.*type\" OR textPayload:\"レバレッジ\" OR textPayload:\"leverage\" OR textPayload:\"margin.*error\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
```

**🚨 Kelly基準・ポジションサイズ問題判定**:
- **Kelly履歴不足（<20件）** = 保守的サイズ使用→注文サイズ制限超過
- **Silent Failure** = シグナル生成あり・注文実行なし
- **ポジションサイズ制限超過** = max_order_size（0.006）超過
- **最小取引単位未満** = Bitbank 0.0001 BTC未満の注文
- **API・権限問題** = レート制限・権限不足
- **市場・時間制限** = 流動性不足・取引時間外

# 📊 **補完的チェック（基本システム・継続稼働確認）**

## 📈 基本システム稼働・エラー確認
```bash
echo "=== 基本システム稼働・エラー確認 ==="

echo "1. 重大エラー・警告確認:"
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND severity>=ERROR AND timestamp>=\"\$DEPLOY_TIME\"" --limit=10

echo "2. システム継続稼働確認:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"取引サイクル開始\" AND timestamp>=\"\$DEPLOY_TIME\"" 10

echo "3. 最新ログ生存確認:"
show_logs_with_jst "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\"" 3
```

---


## 📊 **最終判定基準（改良版）**

### 🚨 **致命的問題（即座修正必須）**
- **Secret Manager IAM権限なし** → 全機能停止
- **Bitbank残高0円取得** → 全取引機能停止
- **Discord Webhook無効 (code: 50027)** → 監視機能完全停止
- **フォールバック値20回以上/時間** → 動的計算停止
- **ML予測実行0回** → ML機能完全停止
- **BUY/SELLシグナル0回** → エントリー機能停止
- **API認証エラー継続** → 市場データ取得不可
- **取引実行率0%** → シグナル生成のみで実取引停止
- **ポジション管理異常** → 重複注文・不整合取引
- **価格スプレッド異常** → 不適切価格での取引実行
- **資金管理エラー** → 証拠金不足・リスク計算不正
- **MLモデルロード失敗** → 予測機能完全停止
- **システムリソース枯渇** → 全機能不安定化

### ⚠️ **重要問題（24時間以内修正）**
- **Discord通知失敗** → 監視機能停止
- **戦略分析詳細不足** → 一部戦略フォールバック使用
- **リアルデータ取得不安定** → 市場データ品質問題
- **特徴量生成エラー** → ML予測品質劣化
- **データ取得ラグ** → 古いデータでの誤判断

### 📝 **軽微問題（1週間以内改善）**
- **ログ品質向上** → より詳細な分析ログ
- **パフォーマンス最適化** → 実行時間短縮

---

## 🎯 **包括的Bot稼働判定マトリックス（NEW）**

| **チェック項目** | **✅ 正常状態** | **⚠️ 警告状態** | **🚨 異常状態** |
|---|---|---|---|
| **取引サイクル実行** | 5分間隔で継続 | 10分以上間隔 | 30分以上停止 |
| **実際の取引実行** | シグナルの20%以上実行 | 10-20%実行 | 10%未満 |
| **特徴量生成** | 15特徴量全て生成 | 10-14特徴量 | 10未満 |
| **ML予測実行** | 各サイクルで実行 | 2-3サイクル飛ばし | 未実行 |
| **フォールバック使用率** | 5%未満 | 5-20% | 20%以上 |
| **API残高取得** | 実際の残高取得 | フォールバック併用 | フォールバックのみ |
| **データ取得時間軸** | 4h足・15m足正常 | 一方のみ取得 | 両方とも古い |
| **Discord通知** | 正常送信 | 一部失敗 | 完全失敗 |
| **システムメモリ** | 使用率70%未満 | 70-90% | 90%以上 |
| **通貨ペア設定** | BTC/JPY固定 | 他通貨混在 | 未設定・エラー |
| **ポジション管理** | 同期正常・重複なし | 軽微なズレ | 重複・不整合 |
| **価格スプレッド** | 0.1%未満 | 0.1-0.5% | 0.5%以上・逆転 |
| **資金管理** | 証拠金・リスク計算正常 | 計算遅延 | エラー・NaN値 |
| **MLモデル状態** | ロード成功・予測正常 | 一部モデル失敗 | 全モデル失敗 |
| **リソース状態** | CPU/メモリ正常 | 高使用率 | 枯渇・OOM |

### **総合判定基準**:
- **🟢 完全正常**: 全項目が正常状態
- **🟡 監視継続**: 1-2項目が警告状態、異常なし
- **🟠 要注意**: 3項目以上警告 OR 1項目異常
- **🔴 緊急対応**: 2項目以上異常 OR 致命的項目1つ異常

### **自動判定スクリプト例**:
```bash
# 各チェック項目の結果を数値化して総合判定
NORMAL_COUNT=0
WARNING_COUNT=0
CRITICAL_COUNT=0

# 判定ロジック例
if [ $CYCLE_COUNT -ge 12 ]; then
    NORMAL_COUNT=$((NORMAL_COUNT + 1))
elif [ $CYCLE_COUNT -ge 6 ]; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
else
    CRITICAL_COUNT=$((CRITICAL_COUNT + 1))
fi

# 最終判定
if [ $CRITICAL_COUNT -ge 2 ] || [ $CRITICAL_COUNT -ge 1 -a "$CRITICAL_ITEM" = "true" ]; then
    echo "🔴 緊急対応必要"
elif [ $WARNING_COUNT -ge 3 ] || [ $CRITICAL_COUNT -ge 1 ]; then
    echo "🟠 要注意"
elif [ $WARNING_COUNT -le 2 ] && [ $CRITICAL_COUNT -eq 0 ]; then
    echo "🟡 監視継続"
else
    echo "🟢 完全正常"
fi
```

---

## 🔧 **隠れ不具合発見時の対応手順（改良版）**

### **緊急対応（致命的問題）**
```bash
# 1. Secret Manager IAM権限修正
SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)")
gcloud secrets add-iam-policy-binding bitbank-api-key --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding bitbank-api-secret --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding discord-webhook-url --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"

# 2. Discord Webhook URL修正（code: 50027対応・2025/09/15追加）
echo "新しいDiscord Webhook URL（有効なもの）をSecret Managerに更新:"
echo "YOUR_NEW_DISCORD_WEBHOOK_URL" | gcloud secrets versions add discord-webhook-url --data-file=-

# 3. 新リビジョンデプロイ（権限・Webhook適用）
gcloud run services update crypto-bot-service-prod --region=asia-northeast1 --set-env-vars="IAM_FIX_TIMESTAMP=$(date +%s)"

# 4. 15分後再チェック（段階1のみ）
```

### **問題記録方法（改良版）**
```bash
# 致命的隠れ不具合発見時
cat >> /Users/nao/Desktop/bot/docs/開発計画/ToDo.md << 'EOL'

## 🚨 隠れ不具合発見 ($(TZ='Asia/Tokyo' date '+%Y-%m-%d %H:%M:%S JST'))
### 致命的問題: [問題名]
- **種類**: Secret Manager権限/フォールバック値固定/ML停止/API認証失敗
- **症状**: [表面的症状 vs 実際の状態]
- **影響**: 🚨実取引不可/⚠️機能部分停止/📝品質低下
- **緊急度**: 即座修正/24時間以内/1週間以内
- **検出方法**: [今回の検出手順]
- **修正コマンド**: [具体的修正コマンド]
---
EOL
```

---

## 📊 **改良版最終確認チェックリスト**

**段階1（緊急度チェック）**:
- [ ] **Secret Manager IAM権限** → 全てのシークレットアクセス可能
- [ ] **Bitbank残高取得** → 10,000円正常取得（0円は致命的）
- [ ] **Discord Webhook有効性** → code: 50027エラーなし（2025/09/15追加）
- [ ] **フォールバック値検出** → 0.2固定使用が20回未満/時間
- [ ] **動的計算実行** → 戦略分析詳細ログ存在
- [ ] **ML予測実行** → 予測ログ存在
- [ ] **ポジション管理** → 重複・不整合なし（2025/09/15追加）
- [ ] **価格スプレッド** → 0.5%未満・逆転なし（2025/09/15追加）
- [ ] **資金管理** → 証拠金・リスク計算正常（2025/09/15追加）
- [ ] **MLモデル状態** → ロード成功・ファイル存在（2025/09/15追加）
- [ ] **システムリソース** → メモリ90%未満・容量充分（2025/09/15追加）

**段階2（実機能チェック）**:
- [ ] **リアルAPI接続** → Bitbank API接続成功ログ
- [ ] **市場データ取得** → モックデータ不使用
- [ ] **エントリーシグナル** → BUY/SELLシグナル生成
- [ ] **Discord通知** → 通知送信成功ログ

**段階3（詳細分析チェック）**:
- [ ] **基本稼働** → サイクル実行・最新ログ存在
- [ ] **エラー監視** → 重大エラーなし

### **総合判定（継続稼働強化版）**:
- **✅ 実取引開始可能**: 段階1-3全て正常・継続稼働確認済み
- **⚠️ 条件付き稼働**: 段階1-2正常・段階3一部問題（監視強化で稼働継続）
- **🚨 緊急修正必要**: 段階1に致命的問題 OR 段階3で完全停止
- **🆕 NEW継続稼働判定**: 残高再取得動作・システム停止3回以下・取引サイクル継続実行

---

## 🎯 **継続改良指針**

### **隠れ不具合検出の継続強化**
1. **新しい隠蔽パターン発見** → チェック項目追加
2. **フォールバック値の新パターン** → 検出ロジック拡張
3. **表面稼働・実機能停止の新ケース** → 実機能確認項目追加

### **予防的監視強化**
1. **定期自動チェック** → 4時間毎の段階1チェック
2. **アラート改良** → 致命的問題の即座通知
3. **品質メトリクス** → フォールバック率・ML予測成功率監視

**この改良版により、今回のような隠れた致命的不具合を確実に早期発見できます。**

**確認ポイント**: CI成功・デプロイ時刻一致・イメージハッシュ一致

---

## 📚 **過去の教訓・継続改良指針**

### **発見された主要問題パターン**
1. **Secret Manager IAM権限欠如** → 全機能停止・フォールバック固定化
2. **新デプロイ失敗・古バージョン稼働** → 修正未適用・根本問題継続
3. **表面稼働・実機能停止** → プロセス稼働でも機能価値ゼロ
4. **Discord Webhook無効** → 監視機能完全停止

### **予防的監視強化策**
- フォールバック使用率：<5%正常・>20%で警告
- ML予測成功率：>90%維持必須
- API認証成功率：100%維持必須
- 新隠蔽パターン発見時の即座チェック項目追加

---

# 🚀 **統合実行スクリプト（全チェック自動実行・自動判定）**

```bash
#!/bin/bash
# CI後チェック統合実行スクリプト - 全セクション自動実行・自動判定
# 使用方法: bash ci_check_script.sh

echo "🚀 CI後チェック統合実行開始: $(TZ='Asia/Tokyo' date '+%Y-%m-%d %H:%M:%S JST')"
echo "=============================================================="

# スコア初期化
CRITICAL_ISSUES=0
WARNING_ISSUES=0
NORMAL_CHECKS=0

# 最新CI・デプロイ状況確認（改良版）
echo "📋 最新CI・デプロイ状況確認（改良版）"
TZ='Asia/Tokyo' date '+現在時刻: %Y-%m-%d %H:%M:%S JST'

# 最新GitHubActionsワークフロー確認
echo "最新CI確認:"
LATEST_CI_UTC=$(gh run list --limit=1 --workflow="CI/CD Pipeline" --status=success --json=createdAt --jq='.[0].createdAt' 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$LATEST_CI_UTC" ]; then
    LATEST_CI_JST=$(TZ='Asia/Tokyo' date -d "$LATEST_CI_UTC" '+%Y-%m-%d %H:%M:%S JST')
    echo "✅ 最新成功CI時刻: $LATEST_CI_JST"
    DEPLOY_TIME="$LATEST_CI_UTC"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ 最新CI情報取得失敗"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# Cloud Run現在のリビジョン確認
LATEST_REVISION=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.traffic[0].revisionName)" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$LATEST_REVISION" ]; then
    echo "✅ 対象リビジョン: $LATEST_REVISION"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ Cloud Runサービスが見つかりません"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

echo ""
echo "🔐 Secret Manager・API認証確認"

# IAM権限確認
SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null)
if [ -n "$SERVICE_ACCOUNT" ]; then
    echo "✅ サービスアカウント: $SERVICE_ACCOUNT"

    # Secret Manager権限確認
    BITBANK_KEY_ACCESS=$(gcloud secrets get-iam-policy bitbank-api-key --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")
    BITBANK_SECRET_ACCESS=$(gcloud secrets get-iam-policy bitbank-api-secret --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")
    DISCORD_ACCESS=$(gcloud secrets get-iam-policy discord-webhook-url --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")

    if [ "$BITBANK_KEY_ACCESS" = "OK" ] && [ "$BITBANK_SECRET_ACCESS" = "OK" ] && [ "$DISCORD_ACCESS" = "OK" ]; then
        echo "✅ Secret Manager IAM権限: 正常"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    else
        echo "❌ Secret Manager IAM権限: 欠如 ($BITBANK_KEY_ACCESS/$BITBANK_SECRET_ACCESS/$DISCORD_ACCESS)"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi
else
    echo "❌ サービスアカウント取得失敗"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# ライブモード設定確認
echo ""
echo "🚀 ライブモード設定確認"
MODE_VALUE=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="yaml" 2>/dev/null | grep -A 2 "name: MODE" | grep "value:" | awk '{print $2}')
DEPLOY_STAGE_VALUE=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="yaml" 2>/dev/null | grep -A 2 "name: DEPLOY_STAGE" | grep "value:" | awk '{print $2}')

if [ "$MODE_VALUE" = "live" ] && [ "$DEPLOY_STAGE_VALUE" = "live" ]; then
    echo "✅ ライブモード設定: 正常 (MODE=live, DEPLOY_STAGE=live)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ ライブモード設定: 異常 (MODE=$MODE_VALUE, DEPLOY_STAGE=$DEPLOY_STAGE_VALUE)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# ライブトレード動作確認
if [ -n "$DEPLOY_TIME" ]; then
    LIVE_TRADING_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"livetradingモード\" OR textPayload:\"ライブトレード\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(textPayload)" 2>/dev/null | wc -l)

    if [ $LIVE_TRADING_COUNT -gt 0 ]; then
        echo "✅ ライブトレード動作: 正常 ($LIVE_TRADING_COUNT回確認)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    else
        echo "⚠️ ライブトレード動作: 未確認"
        WARNING_ISSUES=$((WARNING_ISSUES + 1))
    fi
fi

# API認証・残高確認
echo ""
echo "💰 Bitbank残高・API認証確認"
if [ -n "$DEPLOY_TIME" ]; then
    API_BALANCE_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"10,000円\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=20 --format="value(textPayload)" 2>/dev/null | wc -l)
    FALLBACK_BALANCE_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"11,000円\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=20 --format="value(textPayload)" 2>/dev/null | wc -l)

    if [ $API_BALANCE_COUNT -gt 0 ] && [ $FALLBACK_BALANCE_COUNT -eq 0 ]; then
        echo "✅ 残高取得: API正常 (10,000円 $API_BALANCE_COUNT回)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    elif [ $FALLBACK_BALANCE_COUNT -gt 0 ]; then
        echo "⚠️ 残高取得: フォールバック使用 (11,000円 $FALLBACK_BALANCE_COUNT回)"
        WARNING_ISSUES=$((WARNING_ISSUES + 1))
    else
        echo "❌ 残高取得: 確認できず"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi
fi

# Discord Webhook確認
echo ""
echo "📨 Discord Webhook確認"
if [ -n "$DEPLOY_TIME" ]; then
    DISCORD_ERROR_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"Invalid Webhook Token\" OR textPayload:\"code: 50027\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(textPayload)" 2>/dev/null | wc -l)

    if [ $DISCORD_ERROR_COUNT -eq 0 ]; then
        echo "✅ Discord Webhook: 正常"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    else
        echo "❌ Discord Webhook: 無効 (code: 50027エラー $DISCORD_ERROR_COUNT回)"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi
fi

# フォールバック値検出
echo ""
echo "🔄 フォールバック値・動的計算確認"
if [ -n "$DEPLOY_TIME" ]; then
    FALLBACK_CONFIDENCE_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"信頼度: 0.200\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=50 --format="value(textPayload)" 2>/dev/null | wc -l)

    if [ $FALLBACK_CONFIDENCE_COUNT -lt 5 ]; then
        echo "✅ フォールバック使用: 正常範囲 ($FALLBACK_CONFIDENCE_COUNT回)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    elif [ $FALLBACK_CONFIDENCE_COUNT -lt 20 ]; then
        echo "⚠️ フォールバック使用: 警告レベル ($FALLBACK_CONFIDENCE_COUNT回)"
        WARNING_ISSUES=$((WARNING_ISSUES + 1))
    else
        echo "❌ フォールバック使用: 異常多用 ($FALLBACK_CONFIDENCE_COUNT回) - 動的計算停止疑い"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi
fi

# Kelly基準修正効果・取引実行確認（最新CI以降）
echo ""
echo "🔧 Kelly基準修正効果・取引実行確認（最新CI以降）"
if [ -n "$DEPLOY_TIME" ]; then
    # Kelly基準確認
    KELLY_LOG_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"Kelly計算に必要な取引数不足\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(textPayload)" 2>/dev/null | wc -l)
    TRADE_APPROVAL_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"取引承認\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(textPayload)" 2>/dev/null | wc -l)

    if [ $KELLY_LOG_COUNT -gt 0 ] && [ $TRADE_APPROVAL_COUNT -gt 0 ]; then
        echo "✅ Kelly基準修正効果: 確認 (取引承認$TRADE_APPROVAL_COUNT回)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    elif [ $TRADE_APPROVAL_COUNT -gt 0 ]; then
        echo "✅ 取引承認: 正常 ($TRADE_APPROVAL_COUNT回)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    else
        echo "❌ 取引承認: 未確認"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi

    # ML予測確認
    ML_PREDICTION_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"ProductionEnsemble\" OR textPayload:\"ML予測\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=20 --format="value(textPayload)" 2>/dev/null | wc -l)
    TRADE_EXECUTION_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"注文実行\" OR textPayload:\"order_executed\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=20 --format="value(textPayload)" 2>/dev/null | wc -l)

    if [ $ML_PREDICTION_COUNT -gt 0 ]; then
        echo "✅ ML予測実行: 確認 ($ML_PREDICTION_COUNT回)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    else
        echo "❌ ML予測実行: 未確認"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi

    echo "📊 取引実行状況: $TRADE_EXECUTION_COUNT回"
fi

# 最終判定・スコア計算
echo ""
echo "=============================================================="
echo "📊 **最終判定結果**"
echo "✅ 正常項目: $NORMAL_CHECKS"
echo "⚠️ 警告項目: $WARNING_ISSUES"
echo "❌ 致命的問題: $CRITICAL_ISSUES"

TOTAL_SCORE=$((NORMAL_CHECKS * 10 - WARNING_ISSUES * 3 - CRITICAL_ISSUES * 20))
echo "🏆 総合スコア: $TOTAL_SCORE点"

if [ $CRITICAL_ISSUES -ge 2 ]; then
    echo "🔴 **緊急対応必要** - 複数の致命的問題検出"
    exit 1
elif [ $CRITICAL_ISSUES -ge 1 ]; then
    echo "🟠 **要注意** - 致命的問題1つ検出"
    exit 2
elif [ $WARNING_ISSUES -ge 3 ]; then
    echo "🟡 **監視継続** - 警告項目多数"
    exit 3
else
    echo "🟢 **完全正常** - Bot稼働良好"
    exit 0
fi
```

## 📋 **統合スクリプト使用方法**

### **実行方法**
```bash
# スクリプト作成
cat > ci_check_script.sh << 'EOF'
[上記のスクリプトをコピー]
EOF

# 実行権限付与・実行
chmod +x ci_check_script.sh
bash ci_check_script.sh

# 終了コードで判定
echo "終了コード: $?"
```

### **自動判定基準**
- **終了コード 0**: 🟢 完全正常 - Bot稼働良好
- **終了コード 1**: 🔴 緊急対応必要 - 複数致命的問題
- **終了コード 2**: 🟠 要注意 - 致命的問題1つ
- **終了コード 3**: 🟡 監視継続 - 警告項目多数

### **CI/CDパイプライン統合例**
```yaml
- name: CI後チェック実行
  run: |
    bash ci_check_script.sh
    CHECK_RESULT=$?
    if [ $CHECK_RESULT -eq 1 ]; then
      echo "::error::緊急対応必要 - 複数の致命的問題検出"
    elif [ $CHECK_RESULT -eq 2 ]; then
      echo "::warning::要注意 - 致命的問題1つ検出"
    fi
```

---

---

## 🔧 **コマンド修正履歴（2025/09/17更新）**

### **2025/09/17: 最新CI確認アプローチ追加（重要改良）**
1. **古いログ問題解決**: 固定デプロイ時刻 → 最新CI成功時刻動的取得
2. **GitHub Actions統合**: `gh run list`による最新CI状況確認
3. **時刻計算最適化**: UTC→JST変換自動化・経過時間正確計算
4. **Kelly基準修正効果確認**: 取引承認状況・Kelly計算ログ確認追加
5. **Discord通知状況確認**: code: 50027エラー検出強化

### **2025/09/16: コマンドエラー修正**
1. **TZ環境変数問題**: `TZ='Asia/Tokyo' gcloud...` → `show_logs_with_jst`関数使用
2. **複雑な変数代入エラー**: シェル構文エラーを起こす複雑な条件分岐を簡素化
3. **エスケープ問題**: `$DEPLOY_TIME` → `\$DEPLOY_TIME` でシェル変数エスケープ
4. **実用性向上**: 手動判定推奨箇所を明記、エラー発生しにくいシンプル構造に変更

### **新機能（改良版）**
- **最新CI動的確認**: `gh run list`による最新成功CI時刻取得
- **Kelly基準修正効果確認**: 取引承認数・Kelly計算ログ自動確認
- **Discord通知状況確認**: Webhook無効検出・エラーコード確認
- **show_logs_with_jst関数**: JST時刻表示でエラー回避
- **手動判定ガイド**: 自動計算エラーを避ける目視判定推奨

### **使用方法（改良版）**
```bash
# 最新CI確認（改良版の基本）
gh run list --limit=3 --workflow="CI/CD Pipeline"
LATEST_CI_UTC=$(gh run list --limit=1 --workflow="CI/CD Pipeline" --status=success --json=createdAt --jq='.[0].createdAt')
LATEST_CI_JST=$(TZ='Asia/Tokyo' date -d "$LATEST_CI_UTC" '+%Y-%m-%d %H:%M:%S JST')

# ログ確認（最新CI以降）
show_logs_with_jst "クエリ文字列 AND timestamp>=\"$LATEST_CI_UTC\"" 表示件数

# 関数定義
show_logs_with_jst() {
    local query="$1"
    local limit="${2:-10}"
    gcloud logging read "$query" --limit="$limit" --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
}
```

### **改良版メリット**
- ✅ **リアルタイム性**: 常に最新CI以降の状況確認
- ✅ **正確性**: 古いログによる誤判定防止
- ✅ **効率性**: 必要な時間範囲のみ確認・高速化
- ✅ **実用性**: Kelly基準修正効果など実際の改良項目確認
- ✅ **自動化**: 時刻計算・CI状況確認の完全自動化

**最終更新**: 2025年9月17日 06:50 JST - 最新CI確認アプローチ完全統合・Kelly基準修正効果確認・Discord通知状況確認追加完了