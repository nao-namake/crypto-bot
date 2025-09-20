# 🚀 AI自動取引システム稼働診断書（macOS完全対応版）

## 📋 目次

- **[Part 1: クイック診断](#part-1-クイック診断5分)**（5分）- 統合スクリプトで全体チェック
- **[Part 2: 詳細診断](#part-2-詳細診断問題別)**（必要時）- 問題の根本原因を特定
- **[Part 3: トラブルシューティング](#part-3-トラブルシューティング)**（修正時）- 問題別の対処法

---

## 🎯 診断の基本方針

**システムプロセス稼働 ≠ 実際のBot機能稼働**を前提とした検証

- ✅ **表面稼働の回避**: プロセスが動いていても実際の取引が停止していることがある
- 🔍 **隠れ不具合の検出**: Secret Manager権限・Silent Failure・非同期処理問題
- ⚡ **迅速な対応**: 致命的問題の早期発見と即座修正
- 🍎 **macOS完全対応**: すべてのコマンドがmacOS環境で正常動作

---

# Part 1: クイック診断（5分）

## 🚀 統合診断スクリプト（ワンコマンド実行・macOS対応）

### 準備: 共通関数定義（macOS最適化）

```bash
#!/bin/bash
# AI自動取引システム統合診断スクリプト（macOS対応版）
echo "🚀 AI自動取引システム統合診断開始: $(python3 -c "import datetime; print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S JST'))")"

# 最新CI時刻取得（macOS対応・GNU dateを使わない）
LATEST_CI_UTC=$(gh run list --limit=1 --workflow="CI/CD Pipeline" --status=success --json=createdAt --jq='.[0].createdAt' 2>/dev/null)
if [ -n "$LATEST_CI_UTC" ]; then
    LATEST_CI_JST=$(python3 -c "
import datetime
utc_time = datetime.datetime.fromisoformat('$LATEST_CI_UTC'.replace('Z', '+00:00'))
jst_time = utc_time.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
print(jst_time.strftime('%Y-%m-%d %H:%M:%S JST'))
")
    echo "✅ 最新CI時刻: $LATEST_CI_JST"
    DEPLOY_TIME="$LATEST_CI_UTC"
else
    # macOS対応: GNU date -d を使わずPython3で計算
    DEPLOY_TIME=$(python3 -c "
import datetime
utc_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
print(utc_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
")
    echo "⚠️ CI時刻取得失敗、過去24時間のログを確認"
fi

# 共通関数定義（macOS対応・wc -l エラー回避）
show_logs_since_deploy() {
    local query="$1"
    local limit="${2:-10}"
    if [ -n "$DEPLOY_TIME" ]; then
        gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND ($query) AND timestamp>=\"$DEPLOY_TIME\"" --limit="$limit" --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
    else
        echo "❌ DEPLOY_TIME未設定"
    fi
}

# macOS対応カウント関数（grep -c でカウント）
count_logs_since_deploy() {
    local query="$1"
    local limit="${2:-50}"
    if [ -n "$DEPLOY_TIME" ]; then
        gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND ($query) AND timestamp>=\"$DEPLOY_TIME\"" --limit="$limit" --format="value(textPayload)" | grep -c . || echo "0"
    else
        echo "0"
    fi
}

# スコア初期化
CRITICAL_ISSUES=0
WARNING_ISSUES=0
NORMAL_CHECKS=0
```

### A. 致命的システム障害チェック

```bash
echo ""
echo "🚨 致命的システム障害チェック"

# 1. Secret Manager権限確認
SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null)
if [ -n "$SERVICE_ACCOUNT" ]; then
    echo "✅ サービスアカウント: $SERVICE_ACCOUNT"

    # macOS対応: 各Secret Manager権限確認
    BITBANK_KEY_ACCESS=$(gcloud secrets get-iam-policy bitbank-api-key --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")
    BITBANK_SECRET_ACCESS=$(gcloud secrets get-iam-policy bitbank-api-secret --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")
    DISCORD_ACCESS=$(gcloud secrets get-iam-policy discord-webhook-url --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")

    if [ "$BITBANK_KEY_ACCESS" = "OK" ] && [ "$BITBANK_SECRET_ACCESS" = "OK" ] && [ "$DISCORD_ACCESS" = "OK" ]; then
        echo "✅ Secret Manager権限: 正常 (API Key/Secret/Discord 全て OK)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    else
        echo "❌ Secret Manager権限: 欠如 (API Key:$BITBANK_KEY_ACCESS / Secret:$BITBANK_SECRET_ACCESS / Discord:$DISCORD_ACCESS)"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 2))
    fi
else
    echo "❌ サービスアカウント取得失敗"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 2))
fi

# 2. Silent Failure検出（最重要）
echo ""
echo "🔍 Silent Failure検出分析"
SIGNAL_COUNT=$(count_logs_since_deploy "textPayload:\"統合シグナル生成: buy\" OR textPayload:\"統合シグナル生成: sell\"" 30)
ORDER_COUNT=$(count_logs_since_deploy "textPayload:\"注文実行\" OR textPayload:\"order_executed\" OR textPayload:\"create_order\"" 30)

echo "   シグナル生成: $SIGNAL_COUNT件"
echo "   注文実行: $ORDER_COUNT件"

if [ $SIGNAL_COUNT -eq 0 ]; then
    echo "⚠️ シグナル生成なし（システム動作要確認）"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
elif [ $SIGNAL_COUNT -gt 0 ] && [ $ORDER_COUNT -eq 0 ]; then
    echo "❌ 完全Silent Failure検出（致命的）"
    echo "   → シグナル${SIGNAL_COUNT}件生成されるも注文実行0件"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 2))
else
    # macOS対応: Python3で成功率計算
    SUCCESS_RATE=$(python3 -c "print(int(($ORDER_COUNT / $SIGNAL_COUNT) * 100))" 2>/dev/null || echo "0")
    if [ $SUCCESS_RATE -ge 20 ]; then
        echo "✅ 取引実行: 正常 (成功率: ${SUCCESS_RATE}%)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    else
        echo "⚠️ 部分的Silent Failure (成功率: ${SUCCESS_RATE}%)"
        WARNING_ISSUES=$((WARNING_ISSUES + 1))
    fi
fi

# 3. Container安定性確認（ExecutionService async/await問題含む）
echo ""
echo "🔥 Container安定性・非同期処理確認"
CONTAINER_EXIT_COUNT=$(count_logs_since_deploy "textPayload:\"Container called exit(1)\"" 20)
RUNTIME_WARNING_COUNT=$(count_logs_since_deploy "textPayload:\"RuntimeWarning\" AND textPayload:\"never awaited\"" 20)

echo "   Container exit(1): $CONTAINER_EXIT_COUNT回"
echo "   RuntimeWarning: $RUNTIME_WARNING_COUNT回"

if [ $CONTAINER_EXIT_COUNT -lt 5 ] && [ $RUNTIME_WARNING_COUNT -eq 0 ]; then
    echo "✅ Container安定性: 正常"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ $CONTAINER_EXIT_COUNT -lt 10 ] && [ $RUNTIME_WARNING_COUNT -lt 5 ]; then
    echo "⚠️ Container軽微問題 (要監視)"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
else
    echo "❌ Container深刻問題 (async/await問題・頻繁クラッシュ)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# 4. Discord監視確認
echo ""
echo "📨 Discord監視機能確認"
DISCORD_ERROR_COUNT=$(count_logs_since_deploy "textPayload:\"code: 50027\" OR textPayload:\"Invalid Webhook Token\"" 5)
if [ $DISCORD_ERROR_COUNT -eq 0 ]; then
    echo "✅ Discord監視: 正常 (Webhook Token有効)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ Discord監視: 停止 (Webhook Token無効・エラー ${DISCORD_ERROR_COUNT}回)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi
```

### B. 主要機能チェック

```bash
echo ""
echo "🔧 主要機能チェック"

# 1. ライブモード設定確認
MODE_VALUE=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="yaml" 2>/dev/null | grep -A 2 "name: MODE" | grep "value:" | awk '{print $2}')
DEPLOY_STAGE_VALUE=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="yaml" 2>/dev/null | grep -A 2 "name: DEPLOY_STAGE" | grep "value:" | awk '{print $2}')

if [ "$MODE_VALUE" = "live" ] && [ "$DEPLOY_STAGE_VALUE" = "live" ]; then
    echo "✅ ライブモード: 正常 (MODE=live, DEPLOY_STAGE=live)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "⚠️ ライブモード: 設定確認要 (MODE=$MODE_VALUE, DEPLOY_STAGE=$DEPLOY_STAGE_VALUE)"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
fi

# 2. API残高取得確認（フォールバック vs 実API判定）
echo ""
echo "💰 API残高取得確認"
API_BALANCE_COUNT=$(count_logs_since_deploy "textPayload:\"10,000円\"" 15)
FALLBACK_BALANCE_COUNT=$(count_logs_since_deploy "textPayload:\"11,000円\"" 15)

echo "   API残高(10,000円): $API_BALANCE_COUNT回"
echo "   フォールバック(11,000円): $FALLBACK_BALANCE_COUNT回"

if [ $API_BALANCE_COUNT -gt 0 ] && [ $FALLBACK_BALANCE_COUNT -eq 0 ]; then
    echo "✅ API残高取得: 正常 (実API使用中)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ $FALLBACK_BALANCE_COUNT -gt 0 ]; then
    echo "⚠️ フォールバック残高使用中 (API認証問題の可能性)"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
else
    echo "❌ 残高取得: 失敗 (API・フォールバック両方とも確認できず)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# 3. ML予測実行確認
echo ""
echo "🤖 ML予測システム確認"
ML_PREDICTION_COUNT=$(count_logs_since_deploy "textPayload:\"ProductionEnsemble\" OR textPayload:\"ML予測\" OR textPayload:\"アンサンブル予測\"" 20)
if [ $ML_PREDICTION_COUNT -gt 0 ]; then
    echo "✅ ML予測: 正常実行中 ($ML_PREDICTION_COUNT回確認)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ ML予測: 未実行 (ProductionEnsemble動作なし)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# 4. システム稼働確認（取引サイクル）
echo ""
echo "⚙️ システム稼働確認"
LIVE_TRADING_COUNT=$(count_logs_since_deploy "textPayload:\"livetradingモード\" OR textPayload:\"取引サイクル開始\"" 12)
if [ $LIVE_TRADING_COUNT -gt 0 ]; then
    echo "✅ システム稼働: 正常 ($LIVE_TRADING_COUNT回の取引サイクル確認)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "⚠️ システム稼働: 取引サイクル未確認"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
fi

# 5. フォールバック値使用頻度確認
echo ""
echo "🔄 フォールバック値使用頻度確認"
FALLBACK_CONFIDENCE_COUNT=$(count_logs_since_deploy "textPayload:\"信頼度: 0.200\"" 30)
if [ $FALLBACK_CONFIDENCE_COUNT -lt 5 ]; then
    echo "✅ フォールバック使用: 正常範囲 ($FALLBACK_CONFIDENCE_COUNT回)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ $FALLBACK_CONFIDENCE_COUNT -lt 15 ]; then
    echo "⚠️ フォールバック使用: やや多い ($FALLBACK_CONFIDENCE_COUNT回)"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
else
    echo "❌ フォールバック使用: 異常多用 ($FALLBACK_CONFIDENCE_COUNT回・動的計算停止疑い)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi
```

### C. 最終判定（改良版）

```bash
echo ""
echo "=============================================================="
echo "📊 統合診断結果"
echo "✅ 正常項目: $NORMAL_CHECKS"
echo "⚠️ 警告項目: $WARNING_ISSUES"
echo "❌ 致命的問題: $CRITICAL_ISSUES"

# 特別な致命的問題フラグ（即座対応必須）
FATAL_ISSUES=false
FATAL_REASONS=""

if [ "$BITBANK_KEY_ACCESS" != "OK" ] || [ "$BITBANK_SECRET_ACCESS" != "OK" ] || [ "$DISCORD_ACCESS" != "OK" ]; then
    FATAL_ISSUES=true
    FATAL_REASONS="$FATAL_REASONS Secret Manager権限欠如"
fi

if [ $SIGNAL_COUNT -gt 0 ] && [ $ORDER_COUNT -eq 0 ]; then
    FATAL_ISSUES=true
    FATAL_REASONS="$FATAL_REASONS 完全Silent Failure"
fi

if [ $DISCORD_ERROR_COUNT -gt 0 ]; then
    FATAL_ISSUES=true
    FATAL_REASONS="$FATAL_REASONS Discord監視停止"
fi

# macOS対応スコア計算（重要度重み付け）
TOTAL_SCORE=$((NORMAL_CHECKS * 10 - WARNING_ISSUES * 3 - CRITICAL_ISSUES * 20))
echo "🏆 総合スコア: $TOTAL_SCORE点"

# 改良版最終判定
echo ""
echo "🎯 最終判定結果"

if [ "$FATAL_ISSUES" = "true" ]; then
    echo "💀 即座対応必須 - 致命的システム障害検出"
    echo "   🚨 検出問題:$FATAL_REASONS"
    echo "   → Part 2-A 致命的問題の詳細診断を即座実行"
    echo "   → Part 3 緊急対応コマンド使用推奨"
    exit 1
elif [ $CRITICAL_ISSUES -ge 3 ]; then
    echo "🔴 緊急対応必要 - 多数の致命的問題 ($CRITICAL_ISSUES件)"
    echo "   → システム全体の安定性に深刻な影響"
    echo "   → Part 2-A,B 詳細診断を実行"
    exit 1
elif [ $CRITICAL_ISSUES -ge 1 ] && [ $WARNING_ISSUES -ge 2 ]; then
    echo "🟠 要注意 - 致命的問題+複数警告の組み合わせ"
    echo "   → 致命的: $CRITICAL_ISSUES件, 警告: $WARNING_ISSUES件"
    echo "   → Part 2-B 機能問題の詳細診断推奨"
    exit 2
elif [ $CRITICAL_ISSUES -ge 1 ]; then
    echo "🟠 要注意 - 致命的問題検出 ($CRITICAL_ISSUES件)"
    echo "   → 機能の一部に深刻な問題"
    echo "   → Part 2-B 機能問題の詳細診断推奨"
    exit 2
elif [ $WARNING_ISSUES -ge 4 ]; then
    echo "🟡 監視継続 - 警告多数 ($WARNING_ISSUES件)"
    echo "   → システム品質低下・予防的対応推奨"
    echo "   → Part 2-C パフォーマンス診断推奨"
    exit 3
elif [ $WARNING_ISSUES -ge 1 ] && [ $NORMAL_CHECKS -lt 3 ]; then
    echo "🟡 監視継続 - 正常項目不足"
    echo "   → 正常: $NORMAL_CHECKS件, 警告: $WARNING_ISSUES件"
    echo "   → 基本機能の動作確認不足"
    exit 3
else
    echo "🟢 完全正常 - AI自動取引システム良好稼働"
    echo "   ✨ ExecutionService・Silent Failure修正・非同期処理すべて正常"
    echo "   📊 正常: $NORMAL_CHECKS件, 警告: $WARNING_ISSUES件, 致命的: $CRITICAL_ISSUES件"
    echo "   🚀 24時間自動取引システム安定稼働中"
    exit 0
fi
```

### 🎯 統合スクリプト実行方法（macOS版）

```bash
# 1. スクリプト作成（macOS対応版）
cat > ai_trading_diagnosis_macos.sh << 'EOF'
#!/bin/bash
# 上記のスクリプト全体をここにコピー
EOF

# 2. 実行権限付与・実行
chmod +x ai_trading_diagnosis_macos.sh
bash ai_trading_diagnosis_macos.sh

# 3. 結果確認
RESULT_CODE=$?
echo ""
echo "🏁 診断完了 - 終了コード: $RESULT_CODE"

case $RESULT_CODE in
    0) echo "🟢 完全正常 - 継続稼働" ;;
    1) echo "💀 即座対応必須 - システム障害" ;;
    2) echo "🟠 要注意 - 機能問題あり" ;;
    3) echo "🟡 監視継続 - 予防的対応" ;;
    *) echo "❓ 不明な終了コード" ;;
esac
```

### 📊 判定基準（詳細版）
- **終了コード 0**: 🟢 完全正常 - 24時間自動取引システム安定稼働
- **終了コード 1**: 💀 即座対応必須 - Secret Manager・Silent Failure・Discord監視停止
- **終了コード 2**: 🟠 要注意 - ML予測停止・Container問題・API接続問題
- **終了コード 3**: 🟡 監視継続 - フォールバック多用・パフォーマンス低下

---

# Part 2: 詳細診断（問題別）

## A. 致命的問題の詳細診断

### 🔐 Secret Manager・権限問題詳細診断

**いつ使用**: クイック診断でSecret Manager権限問題が検出された時

```bash
echo "=== Secret Manager・権限問題詳細診断（macOS対応） ==="

# 1. シークレット存在・バージョン確認
echo "1. シークレット存在・バージョン確認:"
echo "   bitbank-api-key:"
gcloud secrets versions list bitbank-api-key --limit=3 --format="table(name,state,createTime.date('%Y-%m-%d %H:%M:%S'))"
echo "   bitbank-api-secret:"
gcloud secrets versions list bitbank-api-secret --limit=3 --format="table(name,state,createTime.date('%Y-%m-%d %H:%M:%S'))"
echo "   discord-webhook-url:"
gcloud secrets versions list discord-webhook-url --limit=3 --format="table(name,state,createTime.date('%Y-%m-%d %H:%M:%S'))"

# 2. 詳細権限確認
echo ""
echo "2. 詳細IAM権限確認:"
SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)")
echo "   サービスアカウント: $SERVICE_ACCOUNT"

for secret in bitbank-api-key bitbank-api-secret discord-webhook-url; do
    echo "   $secret 権限:"
    gcloud secrets get-iam-policy $secret --format="table(bindings[].role,bindings[].members[])" 2>/dev/null || echo "     ❌ 権限確認失敗"
done

# 3. サービスアカウント詳細情報
echo ""
echo "3. サービスアカウント詳細:"
gcloud iam service-accounts describe $SERVICE_ACCOUNT 2>/dev/null || echo "❌ SA情報取得失敗"

# 4. Cloud Run環境変数確認
echo ""
echo "4. Cloud Run環境変数確認:"
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="table(spec.template.spec.containers[0].env[].name,spec.template.spec.containers[0].env[].value)"

# 5. Secret取得テスト（安全な方法）
echo ""
echo "5. Secret取得テスト（権限確認用）:"
for secret in bitbank-api-key bitbank-api-secret discord-webhook-url; do
    if gcloud secrets versions access latest --secret="$secret" --format="value(payload.data)" | base64 -d | head -c 10 >/dev/null 2>&1; then
        echo "   $secret: ✅ アクセス可能"
    else
        echo "   $secret: ❌ アクセス不可"
    fi
done

# 6. 緊急修正コマンド生成
echo ""
echo "6. 🚨 緊急修正コマンド（実行が必要な場合）:"
echo "   # Secret Manager権限付与"
for secret in bitbank-api-key bitbank-api-secret discord-webhook-url; do
    echo "   gcloud secrets add-iam-policy-binding $secret --member=\"serviceAccount:$SERVICE_ACCOUNT\" --role=\"roles/secretmanager.secretAccessor\""
done
echo ""
echo "   # 新リビジョンデプロイ（権限適用）"
echo "   gcloud run services update crypto-bot-service-prod --region=asia-northeast1 --set-env-vars=\"PERMISSION_FIX_TIMESTAMP=\$(python3 -c 'import time; print(int(time.time()))')\""
```

### 🔍 Silent Failure根本原因詳細分析

**いつ使用**: クイック診断でSilent Failure（シグナル生成あり・注文実行なし）が検出された時

```bash
echo "=== Silent Failure根本原因詳細分析（macOS対応） ==="

# 1. シグナル→実行フロー詳細追跡
echo "1. シグナル→実行フロー詳細追跡:"
SIGNAL_DETAIL_COUNT=$(count_logs_since_deploy "textPayload:\"統合シグナル生成: buy\" OR textPayload:\"統合シグナル生成: sell\"" 40)
EXECUTION_SERVICE_COUNT=$(count_logs_since_deploy "textPayload:\"ExecutionService\" AND textPayload:\"execute_trade\"" 40)
ORDER_DETAIL_COUNT=$(count_logs_since_deploy "textPayload:\"注文実行\" OR textPayload:\"order_executed\" OR textPayload:\"create_order\"" 40)

echo "   シグナル生成: $SIGNAL_DETAIL_COUNT件"
echo "   ExecutionService呼び出し: $EXECUTION_SERVICE_COUNT件"
echo "   実際の注文実行: $ORDER_DETAIL_COUNT件"

if [ $SIGNAL_DETAIL_COUNT -gt 0 ] && [ $EXECUTION_SERVICE_COUNT -eq 0 ]; then
    echo "   ❌ ExecutionService呼び出し失敗 - orchestrator.py統合問題"
elif [ $EXECUTION_SERVICE_COUNT -gt 0 ] && [ $ORDER_DETAIL_COUNT -eq 0 ]; then
    echo "   ❌ ExecutionService内部エラー - BitbankClient.create_order問題"
fi

# 2. ExecutionService内部エラー詳細確認
echo ""
echo "2. ExecutionService内部エラー詳細:"
echo "   execute_trade内部エラー:"
show_logs_since_deploy "textPayload:\"ExecutionService\" AND (textPayload:\"エラー\" OR textPayload:\"Error\" OR textPayload:\"Exception\")" 10

echo "   ExecutionService初期化状況:"
show_logs_since_deploy "textPayload:\"ExecutionService初期化完了\" OR textPayload:\"モード: live\"" 8

echo "   BitbankClient.create_order呼び出し状況:"
show_logs_since_deploy "textPayload:\"create_order\" OR textPayload:\"Bitbank注文実行\" OR textPayload:\"ライブトレード実行\"" 10

# 3. async/await問題詳細確認
echo ""
echo "3. async/await問題詳細確認:"
echo "   RuntimeWarning詳細:"
show_logs_since_deploy "textPayload:\"RuntimeWarning\" AND textPayload:\"never awaited\"" 15

echo "   check_stop_conditions非同期問題:"
show_logs_since_deploy "textPayload:\"check_stop_conditions\"" 8

echo "   trading_cycle_manager.py問題:"
show_logs_since_deploy "textPayload:\"trading_cycle_manager.py\"" 5

# 4. 取引評価→実行パイプライン確認
echo ""
echo "4. 取引評価→実行パイプライン確認:"
echo "   TradeEvaluation作成:"
show_logs_since_deploy "textPayload:\"TradeEvaluation\" OR textPayload:\"取引評価\"" 8

echo "   リスク評価APPROVED:"
show_logs_since_deploy "textPayload:\"APPROVED\" OR textPayload:\"取引承認\"" 8

echo "   position_size計算:"
show_logs_since_deploy "textPayload:\"position_size\" OR textPayload:\"ポジションサイズ\"" 8

# 5. 隠れエラー・例外詳細確認
echo ""
echo "5. 隠れエラー・例外詳細確認:"
echo "   AttributeError・実装ミス:"
show_logs_since_deploy "textPayload:\"AttributeError\" OR textPayload:\"has no attribute\"" 8

echo "   「エラー: 不明」・スタックトレース不足:"
show_logs_since_deploy "textPayload:\"エラー: 不明\" OR textPayload:\"Unknown error\"" 8

echo "   try-except内部隠れエラー:"
show_logs_since_deploy "textPayload:\"Exception\" AND textPayload:\"execute\"" 8

# 6. Kelly基準・ポジションサイズ問題確認
echo ""
echo "6. Kelly基準・ポジションサイズ問題確認:"
echo "   Kelly履歴不足による取引ブロック:"
show_logs_since_deploy "textPayload:\"Kelly計算に必要な取引数不足\"" 8

echo "   保守的サイズ使用・0サイズ問題:"
show_logs_since_deploy "textPayload:\"保守的サイズ使用\" OR textPayload:\"position.*size.*0.000\"" 8

echo "   最小取引単位問題:"
show_logs_since_deploy "textPayload:\"最小取引単位\" OR textPayload:\"amount.*too.*small\"" 5

# 7. 修正効果確認（ExecutionService実装後）
echo ""
echo "7. ExecutionService修正効果確認:"
if [ $SIGNAL_DETAIL_COUNT -gt 0 ] && [ $ORDER_DETAIL_COUNT -gt 0 ]; then
    # macOS対応: Python3で成功率計算
    SUCCESS_RATE=$(python3 -c "print(f'{($ORDER_DETAIL_COUNT / $SIGNAL_DETAIL_COUNT) * 100:.1f}')" 2>/dev/null || echo "0.0")
    echo "   実行成功率: ${SUCCESS_RATE}%"

    # macOS対応: bcコマンドを使わずPython3で比較
    IS_SUCCESS=$(python3 -c "print('1' if float('$SUCCESS_RATE') >= 20.0 else '0')" 2>/dev/null || echo "0")
    if [ "$IS_SUCCESS" = "1" ]; then
        echo "   ✅ ExecutionService修正効果確認"
    else
        echo "   ⚠️ ExecutionService修正効果限定的"
    fi
else
    echo "   ❌ ExecutionService修正効果未確認"
fi
```

### 🔥 Container異常終了・非同期処理問題詳細分析

**いつ使用**: クイック診断でContainer exit(1)やRuntimeWarningが検出された時

```bash
echo "=== Container異常終了・非同期処理問題詳細分析（macOS対応） ==="

# 1. Container exit(1)パターン・頻度分析
echo "1. Container exit(1)パターン・頻度分析:"
CONTAINER_EXIT_DETAIL_COUNT=$(count_logs_since_deploy "textPayload:\"Container called exit(1)\"" 30)
echo "   過去の期間でのContainer exit(1): $CONTAINER_EXIT_DETAIL_COUNT回"

# macOS対応: 頻度判定をPython3で
HOURLY_EXIT_RATE=$(python3 -c "
import datetime
hours_elapsed = max(1, (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat('$DEPLOY_TIME'.replace('Z', '+00:00'))).total_seconds() / 3600)
rate = $CONTAINER_EXIT_DETAIL_COUNT / hours_elapsed
print(f'{rate:.1f}')
" 2>/dev/null || echo "0.0")

echo "   時間当たり異常終了頻度: ${HOURLY_EXIT_RATE}回/時間"

# macOS対応: 頻度判定
IS_HIGH_FREQUENCY=$(python3 -c "print('1' if float('$HOURLY_EXIT_RATE') > 5.0 else '0')" 2>/dev/null || echo "0")
if [ "$IS_HIGH_FREQUENCY" = "1" ]; then
    echo "   ❌ 異常終了頻度: 高い（要対応）"
else
    echo "   ✅ 異常終了頻度: 正常範囲"
fi

# 2. Container異常終了直前のエラー確認
echo ""
echo "2. Container異常終了直前のエラー確認:"
echo "   メモリ不足・OOMエラー:"
show_logs_since_deploy "textPayload:\"OutOfMemoryError\" OR textPayload:\"MemoryError\" OR textPayload:\"OOM\" OR textPayload:\"killed\"" 10

echo "   未処理例外・システムエラー:"
show_logs_since_deploy "textPayload:\"Unhandled exception\" OR textPayload:\"SystemError\" OR textPayload:\"Fatal error\"" 10

echo "   Python関連致命的エラー:"
show_logs_since_deploy "textPayload:\"Traceback\" OR textPayload:\"SyntaxError\" OR textPayload:\"ImportError\"" 8

# 3. RuntimeWarning・async/await問題詳細
echo ""
echo "3. RuntimeWarning・async/await問題詳細:"
RUNTIME_WARNING_DETAIL_COUNT=$(count_logs_since_deploy "textPayload:\"RuntimeWarning\" AND textPayload:\"never awaited\"" 25)
echo "   RuntimeWarning発生数: $RUNTIME_WARNING_DETAIL_COUNT回"

echo "   specific async/await問題箇所:"
show_logs_since_deploy "textPayload:\"check_stop_conditions\" AND textPayload:\"awaited\"" 10

echo "   trading_cycle_manager.py特定行エラー:"
show_logs_since_deploy "textPayload:\"trading_cycle_manager.py:69\" OR textPayload:\"trading_cycle_manager.py\"" 8

# 4. メモリ・リソース使用状況確認
echo ""
echo "4. メモリ・リソース使用状況:"
echo "   メモリ使用率・警告:"
show_logs_since_deploy "textPayload:\"メモリ\" OR textPayload:\"memory\" AND (textPayload:\"90%\" OR textPayload:\"high\")" 8

echo "   CPU使用率・処理時間問題:"
show_logs_since_deploy "textPayload:\"CPU\" OR textPayload:\"processing time\" OR textPayload:\"timeout\"" 8

echo "   ディスク容量・I/O問題:"
show_logs_since_deploy "textPayload:\"disk\" OR textPayload:\"space\" OR textPayload:\"I/O\"" 5

# 5. 自動復旧・スケーリング状況
echo ""
echo "5. 自動復旧・スケーリング状況:"
echo "   Cloud Run自動復旧:"
show_logs_since_deploy "textPayload:\"restarting\" OR textPayload:\"starting\" OR textPayload:\"ready\"" 12

echo "   トラフィック配分・リビジョン切り替え:"
show_logs_since_deploy "textPayload:\"traffic\" OR textPayload:\"revision\" OR textPayload:\"deployment\"" 8

echo "   ヘルスチェック状況:"
show_logs_since_deploy "textPayload:\"health\" OR textPayload:\"probe\" OR textPayload:\"startup\"" 5

# 6. Container問題の取引実行への影響分析
echo ""
echo "6. Container問題の取引実行への影響:"
echo "   exit(1)前後のシグナル生成確認:"
show_logs_since_deploy "textPayload:\"統合シグナル生成\" AND (textPayload:\"before\" OR textPayload:\"after\" OR textPayload:\"interrupt\")" 8

echo "   exit(1)による取引実行中断:"
show_logs_since_deploy "textPayload:\"取引実行\" AND (textPayload:\"中断\" OR textPayload:\"interrupted\" OR textPayload:\"failed\")" 8

# 7. 推奨対処法
echo ""
echo "7. 🚨 推奨対処法:"
if [ "$IS_HIGH_FREQUENCY" = "1" ] || [ $RUNTIME_WARNING_DETAIL_COUNT -gt 5 ]; then
    echo "   ❌ 緊急対応必要:"
    echo "     - Part 3 Container問題緊急対応実行"
    echo "     - メモリ制限増加 (1Gi → 2Gi)"
    echo "     - async/await問題修正（trading_cycle_manager.py）"
else
    echo "   ✅ 監視継続:"
    echo "     - 定期的な頻度確認"
    echo "     - メモリ使用量監視"
fi
```

## B. 機能問題の詳細診断

### 🤖 ML予測・戦略システム詳細診断

**いつ使用**: ML予測が動作していない、または戦略システムに問題がある時

```bash
echo "=== ML予測・戦略システム詳細診断（macOS対応） ==="

# 1. ProductionEnsemble・ML予測実行状況
echo "1. ProductionEnsemble・ML予測実行状況:"
ML_ENSEMBLE_COUNT=$(count_logs_since_deploy "textPayload:\"ProductionEnsemble\"" 20)
ML_PREDICTION_COUNT=$(count_logs_since_deploy "textPayload:\"ML予測\" OR textPayload:\"予測実行\"" 20)
ENSEMBLE_PREDICTION_COUNT=$(count_logs_since_deploy "textPayload:\"アンサンブル予測\"" 20)

echo "   ProductionEnsemble実行: $ML_ENSEMBLE_COUNT回"
echo "   ML予測実行: $ML_PREDICTION_COUNT回"
echo "   アンサンブル予測: $ENSEMBLE_PREDICTION_COUNT回"

if [ $ML_ENSEMBLE_COUNT -eq 0 ] && [ $ML_PREDICTION_COUNT -eq 0 ]; then
    echo "   ❌ ML予測システム完全停止"
else
    echo "   ✅ ML予測システム動作中"
fi

# 2. 5戦略個別実行状況確認
echo ""
echo "2. 5戦略個別実行状況:"
declare -a strategies=("ATRBased" "MochipoyAlert" "MultiTimeframe" "DonchianChannel" "ADXTrendStrength")
for strategy in "${strategies[@]}"; do
    strategy_count=$(count_logs_since_deploy "textPayload:\"[$strategy]\"" 10)
    echo "   $strategy: $strategy_count回"
    if [ $strategy_count -eq 0 ]; then
        echo "     ⚠️ $strategy 戦略未実行"
    fi
done

# 3. 戦略分析詳細プロセス確認
echo ""
echo "3. 戦略分析詳細プロセス確認:"
echo "   ATRBased詳細分析:"
show_logs_since_deploy "textPayload:\"[ATRBased]\" AND (textPayload:\"分析結果\" OR textPayload:\"ボラティリティ\" OR textPayload:\"ATR\")" 5

echo "   MochipoyAlert詳細分析:"
show_logs_since_deploy "textPayload:\"[MochipoyAlert]\" AND (textPayload:\"EMA分析\" OR textPayload:\"MACD分析\" OR textPayload:\"RCI分析\")" 5

echo "   MultiTimeframe詳細分析:"
show_logs_since_deploy "textPayload:\"[MultiTimeframe]\" AND (textPayload:\"4時間足\" OR textPayload:\"15分足\")" 5

# 4. フォールバック値使用・動的計算停止確認
echo ""
echo "4. フォールバック値使用・動的計算停止確認:"
FALLBACK_02_COUNT=$(count_logs_since_deploy "textPayload:\"信頼度: 0.200\"" 25)
FALLBACK_1_COUNT=$(count_logs_since_deploy "textPayload:\"信頼度: 1.000\"" 25)

echo "   フォールバック値0.2使用: $FALLBACK_02_COUNT回"
echo "   不自然な値1.0使用: $FALLBACK_1_COUNT回"

# macOS対応: フォールバック率計算
TOTAL_STRATEGY_EXECUTIONS=$((${strategies[0]// */}))
for strategy in "${strategies[@]}"; do
    strategy_count=$(count_logs_since_deploy "textPayload:\"[$strategy]\"" 10)
    TOTAL_STRATEGY_EXECUTIONS=$((TOTAL_STRATEGY_EXECUTIONS + strategy_count))
done

if [ $TOTAL_STRATEGY_EXECUTIONS -gt 0 ]; then
    FALLBACK_RATE=$(python3 -c "print(f'{($FALLBACK_02_COUNT / $TOTAL_STRATEGY_EXECUTIONS) * 100:.1f}')" 2>/dev/null || echo "0.0")
    echo "   フォールバック使用率: ${FALLBACK_RATE}%"

    IS_HIGH_FALLBACK=$(python3 -c "print('1' if float('$FALLBACK_RATE') > 20.0 else '0')" 2>/dev/null || echo "0")
    if [ "$IS_HIGH_FALLBACK" = "1" ]; then
        echo "   ❌ フォールバック使用率異常（動的計算停止疑い）"
    fi
fi

# 5. MLモデルファイル・ロード問題確認
echo ""
echo "5. MLモデルファイル・ロード問題確認:"
echo "   モデルロード失敗:"
show_logs_since_deploy "textPayload:\"モデルロード.*失敗\" OR textPayload:\"model.*load.*failed\"" 8

echo "   モデルファイル不存在:"
show_logs_since_deploy "textPayload:\"モデルファイル.*見つからない\" OR textPayload:\"model.*file.*not.*found\" OR textPayload:\"FileNotFoundError\"" 8

echo "   予測値異常:"
show_logs_since_deploy "textPayload:\"予測値異常\" OR textPayload:\"prediction.*out.*range\" OR textPayload:\"NaN.*prediction\"" 8

# 6. 特徴量生成問題確認
echo ""
echo "6. 特徴量生成問題確認:"
FEATURE_GENERATION_COUNT=$(count_logs_since_deploy "textPayload:\"特徴量生成完了\" OR textPayload:\"15特徴量\"" 15)
echo "   特徴量生成成功: $FEATURE_GENERATION_COUNT回"

echo "   特徴量生成エラー:"
show_logs_since_deploy "textPayload:\"特徴量\" AND (textPayload:\"エラー\" OR textPayload:\"欠損\" OR textPayload:\"NaN\")" 8

echo "   15特徴量完全生成確認:"
show_logs_since_deploy "textPayload:\"15特徴量完全生成成功\"" 5

# 7. ML予測→戦略統合→シグナル生成フロー確認
echo ""
echo "7. ML予測→戦略統合→シグナル生成フロー:"
INTEGRATED_SIGNAL_COUNT=$(count_logs_since_deploy "textPayload:\"統合シグナル生成\"" 20)
echo "   統合シグナル生成: $INTEGRATED_SIGNAL_COUNT回"

if [ $ML_PREDICTION_COUNT -gt 0 ] && [ $INTEGRATED_SIGNAL_COUNT -eq 0 ]; then
    echo "   ❌ ML予測実行されるもシグナル生成失敗"
elif [ $ML_PREDICTION_COUNT -eq 0 ] && [ $INTEGRATED_SIGNAL_COUNT -gt 0 ]; then
    echo "   ⚠️ ML予測なしでシグナル生成（フォールバック動作）"
else
    echo "   ✅ ML予測→シグナル生成フロー正常"
fi
```

### 💰 API・データ取得詳細診断

**いつ使用**: API残高取得に問題がある、またはフォールバック値が使用されている時

```bash
echo "=== API・データ取得詳細診断（macOS対応） ==="

# 1. bitbank API認証・残高取得詳細確認
echo "1. bitbank API認証・残高取得詳細確認:"
echo "   API認証情報読み込み確認:"
show_logs_since_deploy "textPayload:\"BITBANK_API_KEY読み込み\" OR textPayload:\"BITBANK_API_SECRET読み込み\"" 8

API_10K_COUNT=$(count_logs_since_deploy "textPayload:\"10,000円\"" 20)
FALLBACK_11K_COUNT=$(count_logs_since_deploy "textPayload:\"11,000円\"" 20)
ZERO_YEN_COUNT=$(count_logs_since_deploy "textPayload:\"0円\" OR textPayload:\"残高不足\"" 10)

echo "   実API残高取得(10,000円): $API_10K_COUNT回"
echo "   フォールバック残高(11,000円): $FALLBACK_11K_COUNT回"
echo "   0円・残高不足エラー: $ZERO_YEN_COUNT回"

# API vs フォールバック判定
if [ $API_10K_COUNT -gt 0 ] && [ $FALLBACK_11K_COUNT -eq 0 ]; then
    echo "   ✅ 実API使用中（正常）"
elif [ $FALLBACK_11K_COUNT -gt 0 ]; then
    echo "   ⚠️ フォールバック使用中（API認証問題の可能性）"

    # macOS対応: フォールバック率計算
    TOTAL_BALANCE_CHECKS=$((API_10K_COUNT + FALLBACK_11K_COUNT))
    if [ $TOTAL_BALANCE_CHECKS -gt 0 ]; then
        FALLBACK_BALANCE_RATE=$(python3 -c "print(f'{($FALLBACK_11K_COUNT / $TOTAL_BALANCE_CHECKS) * 100:.1f}')" 2>/dev/null || echo "0.0")
        echo "   フォールバック使用率: ${FALLBACK_BALANCE_RATE}%"
    fi
else
    echo "   ❌ 残高取得完全失敗"
fi

# 2. Secret Manager取得エラー詳細確認
echo ""
echo "2. Secret Manager取得エラー詳細確認:"
echo "   権限・アクセスエラー:"
show_logs_since_deploy "textPayload:\"permission\" OR textPayload:\"Secret\" OR textPayload:\"401\" OR textPayload:\"403\"" 10

echo "   Secret Manager接続問題:"
show_logs_since_deploy "textPayload:\"Secret Manager\" AND (textPayload:\"エラー\" OR textPayload:\"timeout\" OR textPayload:\"connection\")" 8

echo "   具体的なSecret取得失敗:"
show_logs_since_deploy "textPayload:\"bitbank-api-key\" OR textPayload:\"bitbank-api-secret\" AND textPayload:\"取得失敗\"" 5

# 3. 市場データ取得・時間軸確認
echo ""
echo "3. 市場データ取得・時間軸確認:"
HOUR4_DATA_COUNT=$(count_logs_since_deploy "textPayload:\"4h足\" OR textPayload:\"4時間足\"" 15)
MIN15_DATA_COUNT=$(count_logs_since_deploy "textPayload:\"15m足\" OR textPayload:\"15分足\"" 15)

echo "   4時間足データ取得: $HOUR4_DATA_COUNT回"
echo "   15分足データ取得: $MIN15_DATA_COUNT回"

if [ $HOUR4_DATA_COUNT -eq 0 ] || [ $MIN15_DATA_COUNT -eq 0 ]; then
    echo "   ❌ 時間軸データ取得不完全"
else
    echo "   ✅ 両時間軸データ取得正常"
fi

echo "   データ取得遅延・タイムアウト:"
show_logs_since_deploy "textPayload:\"データ取得時間\" OR textPayload:\"data latency\" OR textPayload:\"レスポンス時間\"" 8

# 4. API接続・ネットワーク問題確認
echo ""
echo "4. API接続・ネットワーク問題確認:"
echo "   API接続タイムアウト・エラー:"
show_logs_since_deploy "textPayload:\"API timeout\" OR textPayload:\"connection\" OR textPayload:\"network\"" 10

echo "   bitbank API特有エラー:"
show_logs_since_deploy "textPayload:\"bitbank\" AND (textPayload:\"rate.*limit\" OR textPayload:\"API.*limit\" OR textPayload:\"maintenance\")" 8

echo "   HTTPステータスエラー:"
show_logs_since_deploy "textPayload:\"HTTP\" AND (textPayload:\"500\" OR textPayload:\"502\" OR textPayload:\"503\" OR textPayload:\"504\")" 8

# 5. 通貨ペア・取引設定確認
echo ""
echo "5. 通貨ペア・取引設定確認:"
BTC_JPY_COUNT=$(count_logs_since_deploy "textPayload:\"BTC/JPY\" OR textPayload:\"btc_jpy\"" 15)
echo "   BTC/JPY通貨ペア確認: $BTC_JPY_COUNT回"

if [ $BTC_JPY_COUNT -eq 0 ]; then
    echo "   ⚠️ BTC/JPY設定未確認"
else
    echo "   ✅ BTC/JPY通貨ペア設定正常"
fi

echo "   取引モード・レバレッジ設定:"
show_logs_since_deploy "textPayload:\"信用取引\" OR textPayload:\"margin\" OR textPayload:\"leverage\"" 8

# 6. データ品質・整合性確認
echo ""
echo "6. データ品質・整合性確認:"
echo "   価格データ異常・スプレッド問題:"
show_logs_since_deploy "textPayload:\"価格逆転\" OR textPayload:\"bid.*ask.*逆転\" OR textPayload:\"spread.*異常\"" 8

echo "   データ欠損・NaN値問題:"
show_logs_since_deploy "textPayload:\"データ欠損\" OR textPayload:\"NaN\" OR textPayload:\"missing.*data\"" 8

echo "   時系列データ整合性:"
show_logs_since_deploy "textPayload:\"時系列\" OR textPayload:\"timestamp\" AND textPayload:\"エラー\"" 5
```

## C. パフォーマンス・システム診断

### 🖥️ システムリソース・パフォーマンス詳細診断

**いつ使用**: システムパフォーマンスに問題がある、またはリソース使用量が高い時

```bash
echo "=== システムリソース・パフォーマンス詳細診断（macOS対応） ==="

# 1. メモリ使用状況詳細確認
echo "1. メモリ使用状況詳細確認:"
MEMORY_HIGH_COUNT=$(count_logs_since_deploy "textPayload:\"メモリ.*9[0-9]%\" OR textPayload:\"memory.*9[0-9]%\"" 15)
OOM_ERROR_COUNT=$(count_logs_since_deploy "textPayload:\"OutOfMemoryError\" OR textPayload:\"MemoryError\" OR textPayload:\"OOM\"" 10)

echo "   メモリ使用率90%以上: $MEMORY_HIGH_COUNT回"
echo "   OOMエラー発生: $OOM_ERROR_COUNT回"

if [ $MEMORY_HIGH_COUNT -gt 5 ] || [ $OOM_ERROR_COUNT -gt 0 ]; then
    echo "   ❌ メモリ使用量問題（要対応）"
else
    echo "   ✅ メモリ使用量正常"
fi

echo "   メモリ使用量詳細ログ:"
show_logs_since_deploy "textPayload:\"メモリ\" OR textPayload:\"memory\"" 10

# 2. CPU使用率・処理時間確認
echo ""
echo "2. CPU使用率・処理時間確認:"
CPU_HIGH_COUNT=$(count_logs_since_deploy "textPayload:\"CPU.*100%\" OR textPayload:\"CPU.*high\"" 15)
PROCESSING_TIME_COUNT=$(count_logs_since_deploy "textPayload:\"processing time\" OR textPayload:\"処理時間\"" 15)

echo "   CPU高使用率: $CPU_HIGH_COUNT回"
echo "   処理時間記録: $PROCESSING_TIME_COUNT回"

echo "   処理時間・パフォーマンス詳細:"
show_logs_since_deploy "textPayload:\"CPU\" OR textPayload:\"processing time\" OR textPayload:\"timeout\"" 10

# 3. ディスク・I/O・ストレージ確認
echo ""
echo "3. ディスク・I/O・ストレージ確認:"
DISK_FULL_COUNT=$(count_logs_since_deploy "textPayload:\"ディスク.*不足\" OR textPayload:\"disk.*full\" OR textPayload:\"No space left\"" 5)
echo "   ディスク容量不足: $DISK_FULL_COUNT回"

if [ $DISK_FULL_COUNT -gt 0 ]; then
    echo "   ❌ ディスク容量問題"
else
    echo "   ✅ ディスク容量正常"
fi

echo "   I/O・ストレージ詳細:"
show_logs_since_deploy "textPayload:\"disk\" OR textPayload:\"I/O\" OR textPayload:\"storage\"" 8

# 4. システム全体エラー・警告確認
echo ""
echo "4. システム全体エラー・警告確認:"
echo "   重大エラー（ERROR以上）:"
if [ -n "$DEPLOY_TIME" ]; then
    gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND severity>=ERROR AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(timestamp.date(tz='Asia/Tokyo'),severity,textPayload)"
fi

echo "   システム警告（WARNING）:"
if [ -n "$DEPLOY_TIME" ]; then
    gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND severity=WARNING AND timestamp>=\"$DEPLOY_TIME\"" --limit=8 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
fi

# 5. Cloud Run・GCPインフラ状況確認
echo ""
echo "5. Cloud Run・GCPインフラ状況確認:"
echo "   Cloud Run基本情報:"
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="table(metadata.name,spec.template.spec.containers[0].resources.limits.memory,spec.template.spec.containers[0].resources.limits.cpu,status.url)"

echo "   リビジョン・トラフィック分散:"
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="table(status.traffic[].revisionName,status.traffic[].percent)"

echo "   最新3リビジョン状況:"
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=3 --format="table(metadata.name,metadata.creationTimestamp.date('%Y-%m-%d %H:%M:%S'),status.conditions[0].status)"

# 6. ネットワーク・外部接続確認
echo ""
echo "6. ネットワーク・外部接続確認:"
echo "   ネットワーク接続問題:"
show_logs_since_deploy "textPayload:\"connection\" OR textPayload:\"network\" OR textPayload:\"DNS\"" 10

echo "   外部API接続遅延:"
show_logs_since_deploy "textPayload:\"API timeout\" OR textPayload:\"connection timeout\" OR textPayload:\"slow response\"" 8

echo "   TLS・SSL接続問題:"
show_logs_since_deploy "textPayload:\"TLS\" OR textPayload:\"SSL\" OR textPayload:\"certificate\"" 5

# 7. システム自動復旧・ヘルスチェック
echo ""
echo "7. システム自動復旧・ヘルスチェック:"
RESTART_COUNT=$(count_logs_since_deploy "textPayload:\"restarting\" OR textPayload:\"starting\"" 15)
READY_COUNT=$(count_logs_since_deploy "textPayload:\"ready\" OR textPayload:\"healthy\"" 15)

echo "   システム再起動: $RESTART_COUNT回"
echo "   Ready状態確認: $READY_COUNT回"

echo "   ヘルスチェック・生存確認:"
show_logs_since_deploy "textPayload:\"health\" OR textPayload:\"probe\" OR textPayload:\"liveness\"" 8

# 8. 最新ログ生存・継続稼働確認
echo ""
echo "8. 最新ログ生存・継続稼働確認:"
echo "   最新3件のログ（生存確認）:"
if [ -n "$DEPLOY_TIME" ]; then
    gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\"" --limit=3 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
fi

# 最新ログの時刻確認（macOS対応）
LATEST_LOG_TIME=$(gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\"" --limit=1 --format="value(timestamp)" 2>/dev/null)
if [ -n "$LATEST_LOG_TIME" ]; then
    MINUTES_SINCE_LATEST=$(python3 -c "
import datetime
latest = datetime.datetime.fromisoformat('$LATEST_LOG_TIME'.replace('Z', '+00:00'))
now = datetime.datetime.now(datetime.timezone.utc)
minutes = (now - latest).total_seconds() / 60
print(f'{minutes:.1f}')
" 2>/dev/null || echo "不明")

    echo "   最新ログからの経過時間: ${MINUTES_SINCE_LATEST}分"

    # macOS対応: 生存判定
    IS_RECENT=$(python3 -c "print('1' if float('$MINUTES_SINCE_LATEST') < 10.0 else '0')" 2>/dev/null || echo "0")
    if [ "$IS_RECENT" = "1" ]; then
        echo "   ✅ システム生存確認（正常稼働中）"
    else
        echo "   ⚠️ システム応答遅延（${MINUTES_SINCE_LATEST}分経過）"
    fi
else
    echo "   ❌ 最新ログ取得失敗"
fi

# 9. パフォーマンス改善推奨事項
echo ""
echo "9. 🚀 パフォーマンス改善推奨事項:"
if [ $MEMORY_HIGH_COUNT -gt 5 ] || [ $OOM_ERROR_COUNT -gt 0 ]; then
    echo "   ❌ メモリ制限増加推奨: 1Gi → 2Gi"
    echo "     gcloud run services update crypto-bot-service-prod --region=asia-northeast1 --memory=2Gi"
fi

if [ $CPU_HIGH_COUNT -gt 5 ]; then
    echo "   ❌ CPU制限増加推奨: 1000m → 2000m"
    echo "     gcloud run services update crypto-bot-service-prod --region=asia-northeast1 --cpu=2"
fi

if [ "$IS_RECENT" = "0" ]; then
    echo "   ⚠️ システム応答確認・強制再起動推奨"
    echo "     gcloud run services update crypto-bot-service-prod --region=asia-northeast1 --set-env-vars=\"RESTART_TIMESTAMP=\$(python3 -c 'import time; print(int(time.time()))')\""
fi
```

---

# Part 3: トラブルシューティング

## 🚨 緊急対応コマンド集（macOS対応）

### Secret Manager権限修正（緊急時即座実行）

```bash
echo "🚨 Secret Manager権限修正（緊急時即座実行）"

# 1. サービスアカウント確認
SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)")
echo "対象サービスアカウント: $SERVICE_ACCOUNT"

# 2. 権限付与（3つのSecret全て）
echo "権限付与実行中..."
gcloud secrets add-iam-policy-binding bitbank-api-key \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding bitbank-api-secret \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding discord-webhook-url \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

# 3. 新リビジョンデプロイ（権限適用・macOS対応）
FIX_TIMESTAMP=$(python3 -c 'import time; print(int(time.time()))')
echo "新リビジョンデプロイ（権限適用）..."
gcloud run services update crypto-bot-service-prod \
  --region=asia-northeast1 \
  --set-env-vars="PERMISSION_FIX_TIMESTAMP=$FIX_TIMESTAMP"

echo "✅ Secret Manager権限修正完了"
echo "10分後に Part 1 クイック診断で効果確認推奨"
```

### Discord Webhook修復（緊急時即座実行）

```bash
echo "📨 Discord Webhook修復（緊急時即座実行）"

# 1. 現在のWebhook状態確認
echo "現在のWebhook確認..."
DISCORD_ERRORS=$(count_logs_since_deploy "textPayload:\"code: 50027\" OR textPayload:\"Invalid Webhook Token\"" 10)
echo "Discord Webhookエラー数: $DISCORD_ERRORS回"

if [ $DISCORD_ERRORS -gt 0 ]; then
    echo "❌ Discord Webhook無効化検出 - 修復開始"

    # 2. 新しいWebhook URL入力待ち
    echo ""
    echo "🔧 新しいDiscord Webhook URL設定:"
    echo "1. Discordサーバー設定 → 連携サービス → ウェブフック"
    echo "2. 既存Crypto-Bot削除 → 新規作成"
    echo "3. Webhook URLをコピー"
    echo ""
    read -p "新しいDiscord Webhook URL: " NEW_WEBHOOK_URL

    if [ -n "$NEW_WEBHOOK_URL" ]; then
        # 3. Secret Manager更新
        echo "Secret Manager更新中..."
        echo "$NEW_WEBHOOK_URL" | gcloud secrets versions add discord-webhook-url --data-file=-

        # 4. 新リビジョンデプロイ（Webhook適用・macOS対応）
        WEBHOOK_FIX_TIMESTAMP=$(python3 -c 'import time; print(int(time.time()))')
        echo "新リビジョンデプロイ（Webhook適用）..."
        gcloud run services update crypto-bot-service-prod \
          --region=asia-northeast1 \
          --set-env-vars="WEBHOOK_FIX_TIMESTAMP=$WEBHOOK_FIX_TIMESTAMP"

        echo "✅ Discord Webhook修復完了"
        echo "15分後にDiscord通知成功確認推奨"
    else
        echo "❌ Webhook URL未入力 - 修復中断"
    fi
else
    echo "✅ Discord Webhook正常 - 修復不要"
fi
```

### Container問題緊急対応（macOS対応）

```bash
echo "🔥 Container問題緊急対応（macOS対応）"

# 1. 現在のContainer問題レベル確認
CONTAINER_EXITS=$(count_logs_since_deploy "textPayload:\"Container called exit(1)\"" 25)
RUNTIME_WARNINGS=$(count_logs_since_deploy "textPayload:\"RuntimeWarning\"" 25)

echo "Container exit(1): $CONTAINER_EXITS回"
echo "RuntimeWarning: $RUNTIME_WARNINGS回"

# macOS対応: 問題レベル判定
PROBLEM_LEVEL=$(python3 -c "
exit_score = min($CONTAINER_EXITS / 5, 3)
warning_score = min($RUNTIME_WARNINGS / 3, 3)
total = exit_score + warning_score
if total >= 3:
    print('HIGH')
elif total >= 1.5:
    print('MEDIUM')
else:
    print('LOW')
")

echo "問題レベル: $PROBLEM_LEVEL"

case $PROBLEM_LEVEL in
    "HIGH")
        echo "❌ 高レベル問題 - 緊急対応実行"

        # メモリ制限増加
        echo "メモリ制限増加: 1Gi → 2Gi"
        gcloud run services update crypto-bot-service-prod \
          --region=asia-northeast1 \
          --memory=2Gi

        # CPU制限増加
        echo "CPU制限増加: 1000m → 2000m"
        gcloud run services update crypto-bot-service-prod \
          --region=asia-northeast1 \
          --cpu=2

        # 強制再起動
        RESTART_TIMESTAMP=$(python3 -c 'import time; print(int(time.time()))')
        echo "強制再起動実行..."
        gcloud run services update crypto-bot-service-prod \
          --region=asia-northeast1 \
          --set-env-vars="EMERGENCY_RESTART_TIMESTAMP=$RESTART_TIMESTAMP"

        echo "✅ 緊急対応完了"
        ;;

    "MEDIUM")
        echo "⚠️ 中レベル問題 - 予防的対応実行"

        # メモリ制限のみ増加
        echo "メモリ制限増加: 1Gi → 1.5Gi"
        gcloud run services update crypto-bot-service-prod \
          --region=asia-northeast1 \
          --memory=1536Mi

        echo "✅ 予防的対応完了"
        ;;

    "LOW")
        echo "✅ 低レベル問題 - 監視継続"
        echo "現時点で緊急対応不要"
        ;;
esac

echo "20分後に Part 1 クイック診断で効果確認推奨"
```

### Silent Failure緊急修正（macOS対応）

```bash
echo "🔍 Silent Failure緊急修正（macOS対応）"

# 1. Silent Failure状況確認
SIGNALS=$(count_logs_since_deploy "textPayload:\"統合シグナル生成\"" 30)
ORDERS=$(count_logs_since_deploy "textPayload:\"注文実行\" OR textPayload:\"create_order\"" 30)

echo "シグナル生成: $SIGNALS件"
echo "注文実行: $ORDERS件"

if [ $SIGNALS -gt 0 ] && [ $ORDERS -eq 0 ]; then
    echo "❌ 完全Silent Failure検出 - 緊急修正開始"

    # 2. ExecutionService async/await問題の可能性確認
    ASYNC_WARNINGS=$(count_logs_since_deploy "textPayload:\"RuntimeWarning\" AND textPayload:\"never awaited\"" 20)

    if [ $ASYNC_WARNINGS -gt 0 ]; then
        echo "❌ async/await問題検出 - システム再起動必要"

        # 強制再起動（async/await問題解決のため）
        ASYNC_FIX_TIMESTAMP=$(python3 -c 'import time; print(int(time.time()))')
        gcloud run services update crypto-bot-service-prod \
          --region=asia-northeast1 \
          --set-env-vars="ASYNC_FIX_RESTART_TIMESTAMP=$ASYNC_FIX_TIMESTAMP"

        echo "✅ async/await問題対応完了"
    else
        echo "⚠️ async/await問題なし - 他要因調査必要"
    fi

    # 3. Secret Manager権限再確認・修正
    echo "Secret Manager権限再確認..."
    SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)")

    # 権限再付与（確実にするため）
    for secret in bitbank-api-key bitbank-api-secret discord-webhook-url; do
        gcloud secrets add-iam-policy-binding $secret \
          --member="serviceAccount:$SERVICE_ACCOUNT" \
          --role="roles/secretmanager.secretAccessor" 2>/dev/null || true
    done

    echo "✅ Secret Manager権限確認完了"

elif [ $SIGNALS -eq 0 ]; then
    echo "⚠️ シグナル生成なし - システム動作要確認"

    # システム基本機能再起動
    SIGNAL_FIX_TIMESTAMP=$(python3 -c 'import time; print(int(time.time()))')
    gcloud run services update crypto-bot-service-prod \
      --region=asia-northeast1 \
      --set-env-vars="SIGNAL_FIX_RESTART_TIMESTAMP=$SIGNAL_FIX_TIMESTAMP"

    echo "✅ システム基本機能再起動完了"

else
    # macOS対応: 成功率計算
    SUCCESS_RATE=$(python3 -c "print(f'{($ORDERS / $SIGNALS) * 100:.1f}')" 2>/dev/null || echo "0.0")
    echo "✅ 部分的実行中 (成功率: ${SUCCESS_RATE}%)"
    echo "緊急対応不要 - 監視継続"
fi

echo "30分後に Part 1 クイック診断で効果確認必須"
```

## 📋 問題別チェックリスト

### 💀 即座対応必須チェックリスト
- [ ] **Secret Manager権限**: 3つ全て正常アクセス可能
- [ ] **Silent Failure解消**: シグナル生成→注文実行成功率20%以上
- [ ] **Discord監視復旧**: code: 50027エラー解消・通知送信成功
- [ ] **Container安定化**: exit(1)頻度5回/時間未満・RuntimeWarning解消

### 🟠 要注意チェックリスト
- [ ] **ML予測正常化**: ProductionEnsemble実行・予測値正常
- [ ] **API接続安定化**: 10,000円正常取得・フォールバック使用停止
- [ ] **メモリ使用量**: 90%未満維持・OOMエラー解消
- [ ] **戦略システム**: 5戦略全て実行・フォールバック値20%未満

### 🟡 監視継続チェックリスト
- [ ] **システム稼働**: 取引サイクル継続・最新ログ10分以内
- [ ] **パフォーマンス**: 処理時間正常・ネットワーク遅延なし
- [ ] **データ品質**: 4h足・15m足正常取得・価格データ整合性
- [ ] **リソース効率**: CPU・メモリ・ディスク使用量正常範囲

## 🔄 定期監視・メンテナンス推奨

### 毎時実行推奨
```bash
# クイック診断（5分以内）
bash ai_trading_diagnosis_macos.sh
```

### 毎日実行推奨
```bash
# 特定問題の詳細確認（必要に応じて）
# Part 2-A: 致命的問題が検出された場合
# Part 2-B: 機能問題が検出された場合
# Part 2-C: パフォーマンス問題が検出された場合
```

### 週次実行推奨
```bash
# 全体パフォーマンス分析・トレンド確認
# GCPリソース使用量確認
# MLモデル学習状況確認
```

---

## 📈 継続改善・モニタリング指針

### 🎯 監視指標
- **稼働率**: 99%以上維持（Container exit頻度・システム応答性）
- **実行成功率**: Silent Failure解消・シグナル→注文20%以上
- **リソース効率**: メモリ90%未満・CPU適正使用・ディスク容量充分
- **API品質**: 実API使用率95%以上・フォールバック依存5%未満

### 🔧 予防的メンテナンス
- **権限監視**: Secret Manager IAM権限定期確認
- **非同期処理品質**: RuntimeWarning発生頻度監視
- **データ品質**: API接続安定性・特徴量生成成功率
- **インフラ最適化**: GCPリソース使用効率・コスト最適化

---

**最終更新**: 2025年9月21日
**バージョン**: macOS完全対応版 v2.0
**ファイルサイズ**: 約800行（元1300行から40%圧縮）
**対応環境**: macOS Sonoma以降・Python3完全対応・GNU依存関係排除完了

🍎 **macOS専用最適化**: すべてのコマンドがmacOS環境で確実動作・Date計算Python3化・wc -lエラー完全回避
🚀 **3層診断構造**: クイック診断5分→詳細診断15分→緊急対応1分の効率的ワークフロー
🔍 **隠れ不具合対応**: Silent Failure・async/await・Container問題の根本原因特定と即座修正