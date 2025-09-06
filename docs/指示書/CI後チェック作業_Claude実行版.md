# 🚀 CI完了後チェック指示書（Claude実行最適化版）

## 📋 基本方針（シンプル化）
- **エラー発見時**: 即座修正せず、都度ToDo.md記録して全チェック継続
- **全チェック完了後**: まとめて問題修正
- **承認回数最小化**: 関連チェックをバッチ処理化

---

## 🔄 実行手順（9セクション完全版）

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

## 🔍 セクション1: 時系列・デプロイ状況確認
```bash
echo "=== セクション1: 時系列・デプロイ状況確認 ==="
echo "最新CI実行:"
gh run list --limit=3 --json conclusion,createdAt,displayTitle | jq -r '.[] | "\(.conclusion) - \(.createdAt) - \(.displayTitle)"'
echo "最新Cloud Runリビジョン:"
TZ='Asia/Tokyo' gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=3 --format="table(metadata.name,metadata.creationTimestamp.date(tz='Asia/Tokyo'),status.conditions[0].status)"
echo "Git最新コミット:"
git log --oneline -3
echo "実行中イメージ:"
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.traffic[0].revisionName,spec.template.spec.containers[0].image)"
```

**確認ポイント**: CI成功・デプロイ時刻一致・イメージハッシュ一致

---

## 🖥️ セクション2: 基盤システム稼働確認
```bash
echo "=== セクション2: 基盤システム稼働確認 ==="
echo "サービス稼働状況（デプロイ時刻以降・最新10件）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=10 --format="table(timestamp.date(tz='Asia/Tokyo'),textPayload)"
echo "エラー・警告（デプロイ時刻以降・最新20件）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND severity>=WARNING AND timestamp>=\"$DEPLOY_TIME\"" --limit=20
```

**確認ポイント**: コンテナ正常稼働・異常終了なし・メモリ/CPU正常

---

## 📊 セクション3: データ処理・特徴量生成確認（最重要）
```bash
echo "=== セクション3: データ処理・特徴量生成確認 ==="
echo "マルチタイムフレームデータ取得:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"データ取得成功\" OR textPayload:\"マルチタイムフレーム取得完了\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "12特徴量生成確認（最重要）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"特徴量生成完了 - 総数:\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "特徴量不足検出確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"特徴量不足検出:\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=5
echo "フォールバック・エラー確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"フォールバック\" OR textPayload:\"特徴量生成エラー\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
```

**確認ポイント**: 12特徴量完全生成・不足なし・フォールバック少数

---

## 🤖 セクション4: 機械学習システム確認
```bash
echo "=== セクション4: 機械学習システム確認 ==="
echo "MLモデル読み込み状況:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"モデル読み込み\" OR textPayload:\"ProductionEnsemble\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5
echo "MLモデル学習状態確認（重要）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"is not fitted\" OR textPayload:\"Call fit() first\" OR textPayload:\"EnsembleModel is not fitted\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "予測・シグナル生成確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"予測実行\" OR textPayload:\"シグナル生成\" OR textPayload:\"信頼度\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
```

**確認ポイント**: ProductionEnsemble読み込み成功・fitted状態・予測実行成功

---

## 💰 セクション5: 取引実行・リスク管理確認
```bash
echo "=== セクション5: 取引実行・リスク管理確認 ==="
echo "BUY/SELLシグナル確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"統合シグナル生成: buy\" OR textPayload:\"統合シグナル生成: sell\" OR textPayload:\"エントリーシグナル\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "holdシグナル固定状態確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"統合シグナル生成: hold\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "Kelly基準・リスク管理確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"Kelly\" OR textPayload:\"リスク管理\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=5
```

**確認ポイント**: BUY/SELLシグナル生成・hold固定でない・リスク管理正常

---

## 📡 セクション6: 監視・通知システム確認
```bash
echo "=== セクション6: 監視・通知システム確認 ==="
echo "Discord通知成功・失敗確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"Discord\" OR textPayload:\"webhook\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=15
echo "Discord embed構造エラー確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"400\" OR textPayload:\"embed\" OR textPayload:\"Discord通知送信失敗\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
```

**確認ポイント**: Discord通知成功・embed構造正常・400エラーなし

---

## 📈 セクション7: パフォーマンス・安定性確認
```bash
echo "=== セクション7: パフォーマンス・安定性確認 ==="
echo "取引サイクル実行頻度確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"取引サイクル開始\" OR textPayload:\"Phase.*システム稼働中\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "システム停止検出・最新ログ確認:"
echo "現在時刻: $(TZ='Asia/Tokyo' date)"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\"" --limit=3 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
```

**確認ポイント**: 定期的サイクル実行・システム継続稼働・最新ログ10分以内

---

## 🔍 セクション8: 過去頻出問題・エラー連鎖パターン検出（統合版）
```bash
echo "=== セクション8: 過去頻出問題・エラー連鎖パターン検出 ==="
echo "ImportError・取引サイクルエラー確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"ImportError\" OR textPayload:\"取引サイクルエラー\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "Logger初期化・非同期エラー確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"CryptoBotLogger\" OR textPayload:\"event loop\" OR textPayload:\"Traceback\") AND severity=ERROR AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "IntegratedRiskManager引数不足エラー確認:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND (textPayload:\"IntegratedRiskManager.evaluate_trade_opportunity() missing\" OR textPayload:\"missing 3 required positional arguments\") AND timestamp>=\"$DEPLOY_TIME\"" --limit=10
echo "不正embed構造パターン確認:"
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"{\\\"embeds\\\": [\\\"0\\\"]}" AND timestamp>="'$DEPLOY_TIME'"' --limit=10
echo "エラー連鎖タイミング分析:"
echo "取引サイクルエラー（最新5件）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"取引サイクルエラー\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
echo "Discord通知エラー連鎖（最新5件）:"
TZ='Asia/Tokyo' gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"Discord通知送信失敗\" AND timestamp>=\"$DEPLOY_TIME\"" --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
```

**確認ポイント**: ImportErrorなし・Logger正常・IntegratedRiskManagerエラーなし・embed構造正常・エラー連鎖なし

---

## 🔧 エラー発見時の簡単記録方法

```bash
# エラー発見時は以下をコピペして実行
cat >> /Users/nao/Desktop/bot/docs/開発計画/ToDo.md << 'EOL'

## 🚨 CI後チェック発見エラー（[現在時刻JST]）
### エラー[番号]: [問題名]
- **セクション**: [セクション番号]
- **内容**: [具体的エラー]
- **影響度**: 🚨高/⚠️中/📝低
- **原因**: [推定原因]
- **修正箇所**: [修正必要ファイル]
- **優先度**: [最高/高/中/低]
---
EOL
```

---

## 📊 最終確認チェックリスト

**全セクション実行後にチェック**:
- [ ] セクション1: 時系列・デプロイ状況 → CI成功・デプロイ正常
- [ ] セクション2: 基盤システム → コンテナ正常稼働
- [ ] セクション3: データ・特徴量 → **12特徴量完全生成**
- [ ] セクション4: ML → ProductionEnsemble正常・予測成功
- [ ] セクション5: 取引 → BUY/SELLシグナル生成・hold固定でない
- [ ] セクション6: 通知 → Discord成功・embed構造正常
- [ ] セクション7: パフォーマンス → サイクル実行・最新ログあり
- [ ] セクション8: 統合エラー検出 → ImportError・Logger・連鎖エラーなし

**総合判定**:
- **✅ 全正常**: 実取引開始可能
- **⚠️ 軽微問題**: 優先度付け修正・段階的改善
- **🚨 重大問題**: 即座修正・緊急対応

---

## 🚀 全チェック完了後の対応手順

1. **記録エラー確認**: `grep "CI後チェック発見エラー" /Users/nao/Desktop/bot/docs/開発計画/ToDo.md`
2. **優先度付け**: 🚨最高 → ⚠️高 → 📝中 → 📝低
3. **バッチ修正**: 優先度順に関連問題をまとめて修正
4. **修正確認**: 重要セクション（3,4,5）の部分再チェック
5. **CI/CD実行**: 修正後のCI実行・デプロイ確認
6. **クイック再チェック**: セクション1,3,7のみ再実行で安定稼働確認

この構造なら8つのセクションを確実に順次実行し、全エラーを把握後にまとめて対応できます。