# 🚀 CI完了後チェック指示書（隠れた不具合検出強化版）

## 🚨 **重要**: 表面稼働・実機能停止の検出に特化

**過去の教訓**: システムが「正常稼働」を装いながら、実機能が完全停止していた事例が頻発
- Secret Manager IAM権限欠如 → API認証失敗 → 全機能停止
- フォールバック値固定使用 → 動的計算停止 → エントリーシグナル皆無
- 表面的ログ出力継続 → 実質機能停止の隠蔽

## 📋 **新基本方針**: 3段階深度チェック
1. **🚨 緊急度チェック**: 致命的隠れ不具合を最優先検出
2. **🔍 実機能チェック**: プロセス稼働ではなく実際の機能動作確認
3. **📊 詳細分析チェック**: 従来の表面的ログ確認

---

## 🕐 **最優先: 現在時刻とデプロイ時間の正確な確認**

**重要**: GCPはUTC表記のため、UTC表記で確認して過去のサービスを最新のものと誤認し、正確な稼働状況を把握できなかったことがありました。

```bash
echo "=== 時刻確認・デプロイ状況確認 ==="

# 1. 現在の日本時間を取得
echo "現在の日本時間:"
TZ='Asia/Tokyo' date '+%Y-%m-%d %H:%M:%S JST'

# 2. CIデプロイ時間を確認（UTC → JST変換）
echo "最新Cloud Runリビジョン（UTC→JST変換）:"
TZ='Asia/Tokyo' gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=3 --format="table(metadata.name,metadata.creationTimestamp.date(tz='Asia/Tokyo'),status.conditions[0].status)"

# 3. デプロイ時刻を環境変数に設定（JST → UTC変換）
echo "最新稼働リビジョンのデプロイ時刻を確認..."
LATEST_ACTIVE_REVISION=$(gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --filter="status.conditions[0].status=True" --limit=1 --format="value(metadata.name)")
DEPLOY_TIME=$(gcloud run revisions describe $LATEST_ACTIVE_REVISION --service=crypto-bot-service-prod --region=asia-northeast1 --format="value(metadata.creationTimestamp)")
echo "稼働中リビジョン: $LATEST_ACTIVE_REVISION"
echo "デプロイ時刻（UTC): $DEPLOY_TIME"
echo "デプロイ時刻（JST): $(TZ='Asia/Tokyo' date -d "$DEPLOY_TIME" '+%Y-%m-%d %H:%M:%S JST')"

# 4. 時刻差確認（重要）
echo "現在時刻とデプロイ時刻の差分:"
CURRENT_EPOCH=$(date +%s)
DEPLOY_EPOCH=$(date -d "$DEPLOY_TIME" +%s)
TIME_DIFF=$((CURRENT_EPOCH - DEPLOY_EPOCH))
echo "経過時間: $((TIME_DIFF / 3600))時間 $((TIME_DIFF % 3600 / 60))分"
```

**🚨 時刻確認で以下を確認**:
- 稼働中リビジョンが最新のものか？（古いリビジョンが稼働継続していないか）
- 最新デプロイメントのステータスがTrueか？（起動失敗していないか）
- 経過時間が適切か？（予想より古いデプロイが稼働していないか）

---

## 🎯 **チェック優先順位**
- **最優先**: Secret Manager・API認証・動的計算確認
- **高優先**: ML予測実行・戦略分析詳細・取引機能
- **中優先**: 従来の基盤システム・ログ確認

---

## 🔄 実行手順（3段階深度チェック）

### 📋 チェック前準備
```bash
# 対象デプロイ時刻を一度だけ取得・全セクションで使用
LATEST_REVISION=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.traffic[0].revisionName)")
DEPLOY_TIME=$(gcloud run revisions describe $LATEST_REVISION --region=asia-northeast1 --format="value(metadata.creationTimestamp)")
echo "チェック対象リビジョン: $LATEST_REVISION"
echo "チェック対象デプロイ時刻: $DEPLOY_TIME"
echo "現在時刻: $(TZ='Asia/Tokyo' date '+%Y年%m月%d日 %H:%M:%S JST')"
```

---

# 🚨 **段階1: 緊急度チェック（致命的隠れ不具合検出）**

## 🔐 セクション0: Secret Manager・API認証確認（最重要）
```bash
echo "=== セクション0: Secret Manager・API認証確認（致命的） ==="

echo "1. シークレット存在確認:"
gcloud secrets list --filter="name~(bitbank|discord)"

echo "2. IAM権限確認（致命的）:"
SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)")
echo "使用中サービスアカウント: $SERVICE_ACCOUNT"
gcloud secrets get-iam-policy bitbank-api-key --format="value(bindings[].members)" | grep -q "$SERVICE_ACCOUNT" && echo "✅ bitbank-api-key権限あり" || echo "❌ bitbank-api-key権限なし"
gcloud secrets get-iam-policy bitbank-api-secret --format="value(bindings[].members)" | grep -q "$SERVICE_ACCOUNT" && echo "✅ bitbank-api-secret権限あり" || echo "❌ bitbank-api-secret権限なし" 
gcloud secrets get-iam-policy discord-webhook-url --format="value(bindings[].members)" | grep -q "$SERVICE_ACCOUNT" && echo "✅ discord-webhook-url権限あり" || echo "❌ discord-webhook-url権限なし"

echo "3. Cloud Run環境変数確認:"
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.containers[0].env[].name,spec.template.spec.containers[0].env[].value)"

echo "4. Secret取得エラー確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"permission\" OR textPayload:\"Secret\" OR textPayload:\"401\" OR textPayload:\"403\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
```

**🚨 致命的問題**: IAM権限欠如 = 全機能停止

---

## 🎭 セクション0-2: 動的システム vs フォールバック値判定（最重要）
```bash
echo "=== セクション0-2: 動的システム vs フォールバック値判定 ==="

echo "1. 戦略信頼度固定値検出（0.3 = フォールバック疑い）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"信頼度: 0.300\" OR textPayload:\"confidence: 0.300\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=20 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "2. 戦略信頼度整数値検出（1.000 = 不自然値疑い）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"信頼度: 1.000\" OR textPayload:\"confidence: 1.000\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "3. 戦略分析詳細プロセス欠如確認:"
echo "ATRBased詳細分析ログ:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"[ATRBased]\" AND (textPayload:\"分析結果\" OR textPayload:\"ボラティリティ\" OR textPayload:\"ATR\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5
echo "MochipoyAlert詳細分析ログ:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"[MochipoyAlert]\" AND (textPayload:\"EMA分析\" OR textPayload:\"MACD分析\" OR textPayload:\"RCI分析\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "4. ML予測実行ログ確認（重要）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"予測実行\" OR textPayload:\"ML予測\" OR textPayload:\"ProductionEnsemble予測\" OR textPayload:\"アンサンブル予測\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
```

**🚨 致命的問題**: 
- 全戦略0.3固定 = 動的計算停止
- ML予測ログなし = ML機能停止
- 戦略分析詳細なし = フォールバック値使用

# 🔍 **段階2: 実機能チェック（プロセスではなく実際の機能動作確認）**

## 🌐 セクション1: リアルAPI接続・市場データ取得確認
```bash
echo "=== セクション1: リアルAPI接続・市場データ取得確認 ==="

echo "1. Bitbank API接続成功確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"データ取得成功\" OR textPayload:\"API接続成功\" OR textPayload:\"Bitbank\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10

echo "2. リアル市場データ確認（モックデータ検出）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"mock\" OR textPayload:\"test\" OR textPayload:\"dummy\" OR textPayload:\"sample\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "3. API認証エラー・レート制限確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"authentication\" OR textPayload:\"rate limit\" OR textPayload:\"API key\" OR textPayload:\"unauthorized\") AND (severity>=ERROR OR textPayload:\"エラー\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10

echo "4. Discord通知実送信確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"Discord通知送信成功\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=5
```

**🚨 実機能停止判定**:
- リアルAPI接続ログなし = API認証失敗
- モックデータ使用 = 本番環境未稼働
- Discord通知成功なし = 監視機能停止

---

## 🤖 セクション2: ML予測・戦略動的計算実行確認
```bash
echo "=== セクション2: ML予測・戦略動的計算実行確認 ==="

echo "1. ProductionEnsemble予測実実行確認（最重要）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"ProductionEnsemble\" AND (textPayload:\"予測\" OR textPayload:\"predict\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10

echo "2. 各戦略の動的計算プロセス確認:"
echo "戦略計算詳細ログ（フォールバック以外）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"分析開始\" OR textPayload:\"分析結果\" OR textPayload:\"計算完了\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=15 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "3. 信頼度動的変動確認（0.3以外の多様な値）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"信頼度\" AND NOT textPayload:\"0.300\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=15 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "4. エントリーシグナル生成確認（BUY/SELL）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"統合シグナル生成: buy\" OR textPayload:\"統合シグナル生成: sell\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
```

**🚨 実機能停止判定**:
- ML予測実行ログなし = ML機能停止
- 戦略計算詳細なし = フォールバック値固定使用
- 信頼度0.3のみ = 動的計算停止
- BUY/SELLシグナルなし = エントリー機能停止

---

# 📊 **段階3: 詳細分析チェック（従来の表面的ログ確認・簡素化版）**

## 📈 セクション3: 基本システム稼働・時系列確認
```bash
echo "=== セクション3: 基本システム稼働・時系列確認 ==="

echo "1. デプロイ・CI状況:"
gh run list --limit=3 --json conclusion,createdAt,displayTitle | jq -r '.[] | "\(.conclusion) - \(.createdAt) - \(.displayTitle)"'
TZ='Asia/Tokyo' gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=2 --format="table(metadata.name,metadata.creationTimestamp.date(tz='Asia/Tokyo'),status.conditions[0].status)"

echo "2. システム稼働継続確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"取引サイクル開始\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

echo "3. 重大エラー・警告確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND severity>=ERROR AND timestamp>=\"$DEPLOY_TIME\"" --limit=10

echo "4. 最新ログ生存確認:"
echo "現在時刻: $(TZ='Asia/Tokyo' date)"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\"" --limit=3 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
```

---

## 🚨 セクション4: 新しい隠れ不具合パターン検出
```bash
echo "=== セクション4: 新しい隠れ不具合パターン検出 ==="

echo "1. Secret Manager権限エラー（新項目）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"Permission denied\" OR textPayload:\"Access denied\" OR textPayload:\"Forbidden\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5

echo "2. フォールバック値多用検出（新項目）:"
FALLBACK_COUNT=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"0.300\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=50 --format="value(textPayload)" | wc -l)
echo "フォールバック値0.300使用回数: $FALLBACK_COUNT"
[ $FALLBACK_COUNT -gt 20 ] && echo "⚠️ フォールバック値多用（動的計算停止疑い）" || echo "✅ フォールバック値使用正常範囲"

echo "3. 戦略分析スキップ検出（新項目）:"
echo "分析開始ログ vs シグナル生成ログ比較:"
ANALYSIS_START=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"分析開始\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=50 --format="value(textPayload)" | wc -l)
SIGNAL_GEN=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"シグナル生成完了\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=50 --format="value(textPayload)" | wc -l)
echo "分析開始: $ANALYSIS_START 回 vs シグナル生成: $SIGNAL_GEN 回"
[ $ANALYSIS_START -lt $((SIGNAL_GEN / 2)) ] && echo "⚠️ 分析スキップ多発（フォールバック疑い）" || echo "✅ 分析プロセス正常"

echo "4. ML予測停止検出（新項目）:"
ML_PREDICTION=$(TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"予測\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=20 --format="value(textPayload)" | wc -l)
echo "ML予測実行回数: $ML_PREDICTION"
[ $ML_PREDICTION -eq 0 ] && echo "🚨 ML予測完全停止" || echo "✅ ML予測実行確認"
```

## 📊 **最終判定基準（改良版）**

### 🚨 **致命的問題（即座修正必須）**
- **Secret Manager IAM権限なし** → 全機能停止
- **フォールバック値20回以上/時間** → 動的計算停止
- **ML予測実行0回** → ML機能完全停止
- **BUY/SELLシグナル0回** → エントリー機能停止
- **API認証エラー継続** → 市場データ取得不可

### ⚠️ **重要問題（24時間以内修正）**
- **Discord通知失敗** → 監視機能停止
- **戦略分析詳細不足** → 一部戦略フォールバック使用
- **リアルデータ取得不安定** → 市場データ品質問題

### 📝 **軽微問題（1週間以内改善）**
- **ログ品質向上** → より詳細な分析ログ
- **パフォーマンス最適化** → 実行時間短縮

---

## 🔧 **隠れ不具合発見時の対応手順（改良版）**

### **緊急対応（致命的問題）**
```bash
# 1. Secret Manager IAM権限修正
SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)")
gcloud secrets add-iam-policy-binding bitbank-api-key --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding bitbank-api-secret --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding discord-webhook-url --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"

# 2. 新リビジョンデプロイ（権限適用）
gcloud run services update crypto-bot-service-prod --region=asia-northeast1 --set-env-vars="IAM_FIX_TIMESTAMP=$(date +%s)"

# 3. 15分後再チェック（段階1のみ）
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
- [ ] **フォールバック値検出** → 0.3固定使用が20回未満/時間
- [ ] **動的計算実行** → 戦略分析詳細ログ存在
- [ ] **ML予測実行** → 予測ログ存在

**段階2（実機能チェック）**:
- [ ] **リアルAPI接続** → Bitbank API接続成功ログ
- [ ] **市場データ取得** → モックデータ不使用
- [ ] **エントリーシグナル** → BUY/SELLシグナル生成
- [ ] **Discord通知** → 通知送信成功ログ

**段階3（詳細分析チェック）**:
- [ ] **基本稼働** → サイクル実行・最新ログ存在
- [ ] **エラー監視** → 重大エラーなし

### **総合判定（改良版）**:
- **✅ 実取引開始可能**: 段階1-2全て正常
- **⚠️ 条件付き稼働**: 段階1正常・段階2一部問題
- **🚨 緊急修正必要**: 段階1に致命的問題

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

## 🎓 **今回の重要な教訓と継続的改良指針**

### **🔍 発見された隠れた致命的問題パターン**

#### **1. Secret Manager IAM権限完全欠如**
- **症状**: システム稼働ログ正常・実機能完全停止
- **実態**: サービスアカウントに全シークレットアクセス権限なし
- **影響**: API認証失敗 → 全戦略フォールバック値固定 → エントリーシグナル皆無
- **検出方法**: IAM権限明示確認・フォールバック値使用頻度監視

#### **2. 新デプロイメント起動失敗・古バージョン継続稼働**
- **症状**: デプロイ成功表示・最新機能未適用
- **実態**: 最新リビジョンStatus=False・古リビジョン稼働継続
- **影響**: IAM修正未適用 → 根本問題継続
- **検出方法**: UTC/JST時刻変換・稼働リビジョンのステータス確認

#### **3. 表面稼働・実機能停止の検出困難性**
- **症状**: ログ出力継続・プロセス稼働・監視正常
- **実態**: 動的計算停止・ML予測不実行・戦略分析スキップ
- **影響**: botとしての価値完全消失・資金リスクなし偽装
- **検出方法**: 実機能動作ログの詳細確認・フォールバック率監視

### **🔧 改良されたチェックアプローチ**

#### **段階1: 緊急度チェック（最重要）**
- Secret Manager IAM権限 → 全機能の基盤
- フォールバック値多用検出 → 動的計算停止検出
- API認証状態 → 市場データ取得可否
- リアルデータ vs モックデータ使用状況

#### **段階2: 実機能チェック**
- ML予測実行ログ → 機械学習機能動作確認
- 戦略分析詳細ログ → 各戦略の動的計算確認
- エントリーシグナル生成 → BUY/SELL判定機能確認
- Discord通知実送信 → 監視機能確認

#### **段階3: 詳細分析チェック（従来手法）**
- プロセス稼働状態 → コンテナレベル監視
- 基本ログ確認 → システムレベル監視

### **🚨 予防的監視強化策**

#### **定期自動チェック項目**
```bash
# 4時間毎実行推奨
1. Secret Manager IAM権限状態
2. フォールバック値使用率（20回以上/時間で警告）
3. ML予測実行回数（0回で致命的警告）
4. BUY/SELLシグナル生成状況（hold固定状態検出）
```

#### **アラート改良**
- 致命的問題：即座Discord Critical通知
- 重要問題：1時間以内Warning通知
- 軽微問題：24時間以内Info通知

#### **品質メトリクス監視**
- フォールバック使用率：<5%が正常範囲
- ML予測成功率：>90%維持必須
- API認証成功率：100%維持必須
- エントリーシグナル多様性：HOLD固定率<70%

### **🎯 継続改良方針**

1. **新隠蔽パターン発見** → チェック項目即座追加
2. **フォールバック検出拡張** → 新しい固定値パターン監視
3. **実機能確認項目拡充** → 機能追加時の検証項目同時追加
4. **時刻誤認防止** → UTC/JST変換の自動化・明示化

**この改良版により、今後の隠れた致命的不具合を早期確実検出し、実用的なAI取引botの品質を保証します。**

---

**最終更新**: 2025年9月7日 15:50 JST - Secret Manager IAM権限問題発見・時刻確認強化・隠れ不具合検出改良完成