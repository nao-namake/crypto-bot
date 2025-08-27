# 🚀 CI完了後 自動取引システム稼働状況チェック指示書

## 📋 基本方針
- **時刻表記**: 必ずJST（日本標準時）で確認・記載
- **最新確認**: CI通過後の最新デプロイ版を確実にチェック
- **過去頻出問題**: 特に重点的に確認・根本解決
- **包括的診断**: システム全体の安定稼働を総合判定
- **🚨 エラー発見時の対応方針（重要）**:
  1. **即座修正禁止**: エラーを発見してもチェック作業を中断しない
  2. **都度記録必須**: 発見したエラーを即座にToDo.mdに記録
  3. **チェック継続**: 全項目のチェックを最後まで完了
  4. **まとめて修正**: チェック完了後に記録されたエラーをまとめて修正

### 🔧 エラー発見時の記録手順
**エラーを発見した場合、以下の手順で即座に記録してチェックを継続**:

```bash
# 1. エラー発見時の記録コマンド（都度実行）
echo "## 🚨 CI後チェック発見エラー（$(TZ='Asia/Tokyo' date '+%Y年%m月%d日 %H:%M JST')）

### エラー[番号]: [簡潔な問題名]
- **発見セクション**: [チェック項目番号・名称]
- **エラー内容**: 
\`\`\`
[具体的なエラーメッセージ・ログ出力]
\`\`\`
- **影響度**: 🚨高 / ⚠️中 / 📝低
- **原因推定**: [推定される原因]
- **修正必要箇所**: [修正が必要なファイル・設定]
- **優先度**: 最高 / 高 / 中 / 低

---
" >> /Users/nao/Desktop/bot/docs/開発計画/ToDo.md
```

**記録後**: チェック作業を中断せず次の項目に進む

---

## 🔍 1. 前提確認・最新状態検証

### ✅ CI/CDデプロイ状況確認
```bash
# 最新コミット確認
git log --oneline -3
gh run list --limit=3

# Cloud Run最新リビジョン確認（JST表示）
TZ='Asia/Tokyo' gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=5

# 実際に動作中のイメージハッシュ確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.traffic[0].revisionName,spec.template.spec.template.spec.containers[0].image)"
```

### 🎯 確認ポイント
- [ ] CI通過時刻とCloud Run最新リビジョン時刻が一致
- [ ] 実行中イメージが最新コミットハッシュと一致
- [ ] リビジョン作成時刻が予想時刻（JST）と一致

**🚨 エラー発見時**: 上記記録コマンドで即座にToDo.mdに記録し、次項目へ継続

---

## 🖥️ 2. 基盤システム稼働確認

### ✅ Cloud Runサービス状態
```bash
# サービス稼働状況（JST表示）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND timestamp>=date("%Y-%m-%d", "-1d")' --limit=10 --format="table(timestamp.date(tz='Asia/Tokyo'),textPayload)"

# 直近30分のエラー・警告確認（JST表示）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND severity>=WARNING AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-30m")' --limit=20
```

### 🎯 確認ポイント
- [ ] コンテナ正常起動・継続稼働中
- [ ] メモリ・CPU使用率が適正範囲内
- [ ] 異常終了・再起動が発生していない
- [ ] Phase情報が最新（Phase 13.x）で表示

**🚨 エラー発見時**: エラー記録コマンドで即座にToDo.mdに記録し、次項目へ継続

---

## 📊 3. データ処理・特徴量生成確認

### ✅ マルチタイムフレームデータ取得
```bash
# データ取得成功ログ確認（JST・直近1時間）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"データ取得成功" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10

# マルチタイムフレーム取得状況
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"マルチタイムフレーム取得完了" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5
```

### ✅ 特徴量生成状況（重要・12特徴量必須確認）

#### 📋 必要特徴量12個リスト（Phase 13.6対応）
```
🎯 基本特徴量（3個）: close, volume, returns_1
🎯 テクニカル指標（6個）: rsi_14, macd, atr_14, bb_position, ema_20, ema_50  
🎯 異常検知指標（3個）: zscore, volume_ratio, market_stress
```

#### 🔍 特徴量生成確認コマンド
```bash
# 🚨 Phase 13.6修正: 統合特徴量生成ログ確認（12個完全確認）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"特徴量生成完了 - 総数:" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10

# 個別特徴量グループ確認（従来）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"テクニカル指標生成完了" OR textPayload:"異常検知指標生成完了") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10

# 🚨 特徴量不足検出ログ確認（新機能）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"特徴量不足検出:" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5

# フォールバック・エラー確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"フォールバック" OR textPayload:"特徴量生成エラー") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10
```

### 🎯 確認ポイント（Phase 13.6強化版）
- [ ] 15分足・1時間足・4時間足すべて正常取得
- [ ] **🚨 12特徴量完全生成確認**: 「特徴量生成完了 - 総数: 12/12個」ログ存在
- [ ] **🚨 不足特徴量ゼロ確認**: 「特徴量不足検出」ログが存在しない
- [ ] **🚨 基本特徴量3個含む**: close, volume, returns_1 が生成されている
- [ ] **🚨 テクニカル指標6個**: rsi_14, macd, atr_14, bb_position, ema_20, ema_50 が生成
- [ ] **🚨 異常検知指標3個**: zscore, volume_ratio, market_stress が生成
- [ ] フォールバック使用が異常に多くない（全体の10%以下）
- [ ] データ品質チェック通過・型安全性確保

### ⚠️ 特徴量不足発見時の対応（Phase 13.6追加）
**9個生成の場合**: 基本特徴量3個（close, volume, returns_1）が不足
**6個生成の場合**: テクニカル指標のみ、基本特徴量・異常検知指標が不足  
**3個生成の場合**: 異常検知指標のみ、基本特徴量・テクニカル指標が不足

→ **不足特徴量発見時**: エラー記録コマンドで即座にToDo.mdに記録し、次項目へ継続

**🚨 エラー発見時**: エラー記録コマンドで即座にToDo.mdに記録し、次項目へ継続

---

## 🤖 4. 機械学習・戦略システム確認

### ✅ MLモデル読み込み・予測
```bash
# モデル読み込み状況
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"モデル読み込み" OR textPayload:"ProductionEnsemble") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=5

# ⚠️ MLモデル学習状態確認（重要・今回見逃し防止）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"is not fitted" OR textPayload:"Call fit() first" OR textPayload:"EnsembleModel is not fitted") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=10

# 予測・シグナル生成確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"予測実行" OR textPayload:"シグナル生成" OR textPayload:"信頼度") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10

# ML予測実行成功確認（今回見逃し防止）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"予測結果" AND NOT textPayload:"エラー") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-30m")' --limit=5
```

### 🎯 確認ポイント（Phase 13.6強化版）
- [ ] ProductionEnsemble（統合モデル）正常読み込み
- [ ] **🚨 MLモデル学習済み状態（fitted）である（今回見逃し防止）**
- [ ] **🚨 12特徴量完全セットでの予測実行成功（Phase 13.6対応）**
  - 基本特徴量3個 + テクニカル指標6個 + 異常検知指標3個 = 計12個
- [ ] **🚨 ML予測が実際に実行され結果を出力している（今回見逃し防止）**
- [ ] シグナル生成・信頼度計算正常動作
- [ ] sklearn警告・非推奨API使用なし

### 📋 12特徴量予測確認（Phase 13.6追加）
```bash
# 🚨 12特徴量での予測確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"12特徴量完全生成成功" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5

# ML予測実行時の特徴量数確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"予測実行" AND textPayload:"特徴量") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5
```

**🚨 エラー発見時**: エラー記録コマンドで即座にToDo.mdに記録し、次項目へ継続

---

## 💰 5. 取引実行・リスク管理確認

### ✅ エントリーシグナル・取引実行準備
```bash
# エントリーシグナル確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"エントリーシグナル" OR textPayload:"BUY" OR textPayload:"SELL") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-6h")' --limit=5

# ⚠️ 実際のBUY/SELLシグナル確認（hold固定検出・今回見逃し防止）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"統合シグナル生成: buy" OR textPayload:"統合シグナル生成: sell") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=5

# ⚠️ holdシグナル固定状態確認（今回見逃し防止）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"統合シグナル生成: hold" AND textPayload:"0.500" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10

# リスク管理・Kelly基準確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"Kelly" OR textPayload:"リスク管理" OR textPaylog:"ポジションサイズ") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=5
```

### 🎯 確認ポイント
- [ ] エントリーシグナル検出・判定ロジック正常動作
- [ ] **🚨 実際にBUY/SELLシグナルが生成されている（今回見逃し防止）**
- [ ] **🚨 holdシグナル固定状態でない（信頼度0.500固定でない）（今回見逃し防止）**
- [ ] Kelly基準ポジションサイズ計算実行
- [ ] リスク管理パラメータ適正設定
- [ ] 取引実行準備状態（MODE=live確認）

**🚨 エラー発見時**: エラー記録コマンドで即座にToDo.mdに記録し、次項目へ継続

---

## 📡 6. 監視・通知システム確認

### ✅ Discord通知状況（重点確認）
```bash
# Discord通知成功・失敗確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"Discord" OR textPayload:"webhook") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=15

# Discord初期化・設定確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"🔍" OR textPayload:"🔗" OR textPayload:"Discord初期化") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=10
```

### 🎯 確認ポイント
- [ ] Discord webhook URL正常読み取り（Secret Manager）
- [ ] Discord通知送信成功（401エラーなし）
- [ ] デバッグ情報での環境変数読み取り確認
- [ ] 通知レベル（INFO/WARNING/CRITICAL）正常動作

**🚨 エラー発見時**: エラー記録コマンドで即座にToDo.mdに記録し、次項目へ継続

---

## 🚨 7. 過去頻出問題・重点確認

### ✅ 特定エラーパターン確認
```bash
# asyncio関連エラー
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"event loop" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5

# データ型エラー
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"dict.*empty" OR textPayload:"データ型エラー" OR textPayload:"型不整合") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5

# インポートエラー
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"ImportError" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5

# 取引サイクルエラー
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"取引サイクルエラー" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5

# ⚠️ Logger初期化エラー確認（新発見エラー対応・2025年8月27日追加）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"CryptoBotLogger" OR textPayload:"logger.py") AND severity=ERROR AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=10

# ⚠️ 非同期処理チェーンエラー確認（新発見エラー対応・2025年8月27日追加）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"data_pipeline.py" AND textPayload:"fetch_multi_timeframe") AND severity=ERROR AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=10

# ⚠️ トレースバック・スタックエラー全般確認（新発見エラー対応・2025年8月27日追加）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"Traceback" OR textPayload:"File \"/app/src/") AND severity=ERROR AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=15
```

### 🎯 確認ポイント
- [ ] asyncioイベントループ競合エラーなし
- [ ] DataFrame型安全性エラーなし  
- [ ] インポート・依存関係エラーなし
- [ ] 取引サイクル正常完了

---

## 📈 8. パフォーマンス・安定性確認

### ✅ システムリソース・稼働状況
```bash
# 取引サイクル実行頻度確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"取引サイクル開始" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10

# システム正常稼働確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"Phase.*システム稼働中" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=5
```

### 🎯 確認ポイント
- [ ] 取引サイクル定期実行（2-3分間隔目安）
- [ ] システム継続稼働（再起動なし）
- [ ] メモリリーク・リソース枯渇なし
- [ ] レスポンス時間適正

---

## 🔄 8.5. システム継続稼働確認（今回見逃し防止）

### ✅ システム停止検出・取引サイクル完了確認
```bash
# ⚠️ 最新ログ時刻確認（システム停止検出・今回見逃し防止）
echo "現在時刻: $(TZ='Asia/Tokyo' date)"
echo "最新ログ:"
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-10m")' --limit=1 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"

# 取引サイクル正常完了確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"取引サイクル完了" OR textPayload:"サイクル正常終了") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-30m")' --limit=5

# ⚠️ 取引サイクルエラー確認（今回見逃し防止）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"取引サイクルエラー" OR textPayload:"EnsembleModel is not fitted") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=10

# 統合シグナル生成頻度確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"統合シグナル生成" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10
```

### 🎯 確認ポイント
- [ ] **🚨 最新ログが10分以内（システム停止していない）（今回見逃し防止）**
- [ ] **🚨 取引サイクルがエラーなく正常完了している（今回見逃し防止）**
- [ ] **🚨 「EnsembleModel is not fitted」エラーが発生していない（今回見逃し防止）**
- [ ] 統合シグナル生成が定期的に実行されている（1時間に複数回）
- [ ] 取引サイクルが継続的に動作している

---

## 🔍 9.5. 隠れたエラー連鎖パターン検出（今回追加・重要）

### ✅ IntegratedRiskManager引数エラー確認（新発見エラー）
```bash
# ⚠️ IntegratedRiskManager引数不足エラー確認（今回見逃し防止）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"IntegratedRiskManager.evaluate_trade_opportunity() missing" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=10 --project=my-crypto-bot-project

# 引数不足の詳細エラーメッセージ確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"missing 3 required positional arguments" OR textPayload:"current_balance" OR textPayload:"bid" OR textPayload:"ask") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=15 --project=my-crypto-bot-project

# 取引サイクルエラー発生頻度確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"取引サイクルエラー" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10 --project=my-crypto-bot-project
```

### ✅ Discord通知embed構造エラー確認（継続問題）
```bash
# ⚠️ Discord embed構造エラー確認（今回見逃し防止）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"Discord通知送信失敗" OR textPayload:"400") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=20 --project=my-crypto-bot-project

# 不正embed構造「["0"]」パターン確認
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"{\"embeds\": [\"0\"]}" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=15 --project=my-crypto-bot-project

# Discord通知成功・失敗比率確認
echo "Discord通知成功件数:"
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"Discord送信成功" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=20 --project=my-crypto-bot-project | wc -l
echo "Discord通知失敗件数:"
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"Discord通知送信失敗" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=20 --project=my-crypto-bot-project | wc -l
```

### ✅ エラー連鎖パターン分析（新発見・重要）
```bash
# ⚠️ エラー連鎖タイミング分析（今回見逃し防止）
echo "=== エラー連鎖パターン確認 ==="
echo "1. 取引サイクルエラー発生："
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"取引サイクルエラー" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-30m")' --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)" --project=my-crypto-bot-project

echo -e "\n2. 直後のサイクルエラー記録："
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"サイクルエラー記録" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-30m")' --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)" --project=my-crypto-bot-project

echo -e "\n3. 連鎖するDiscord通知エラー："
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"Discord通知送信失敗" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-30m")' --limit=5 --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)" --project=my-crypto-bot-project

# 連鎖間隔確認（通常1-3分以内で連鎖発生）
echo -e "\n⚠️ エラー連鎖が7-8分間隔で定期発生している場合は根本的問題"
```

### ✅ 取引実行阻害要因確認（新発見・クリティカル）
```bash
# ⚠️ 取引実行が実際に阻害されているか確認（今回見逃し防止）
echo "=== 取引実行阻害状況確認 ==="
echo "1. ML予測成功後の取引評価失敗確認："
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"ML予測成功" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h"))' --limit=5 --project=my-crypto-bot-project

echo -e "\n2. 同時刻帯のリスク評価エラー："
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND textPayload:"IntegratedRiskManager" AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=5 --project=my-crypto-bot-project

echo -e "\n3. 実際のBUY/SELL実行確認（期待：定期的な実行）:"
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (textPayload:"注文実行" OR textPayload:"取引実行") AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-2h")' --limit=5 --project=my-crypto-bot-project
```

### 🎯 隠れたエラー検出確認ポイント（今回追加）
- [ ] **🚨 IntegratedRiskManager引数エラー**: 取引実行を完全阻害する重要エラー
- [ ] **🚨 Discord embed構造エラー**: 監視・通知機能停止の原因
- [ ] **🚨 エラー連鎖パターン**: 1つのエラーが複数の障害を引き起こす連鎖反応
- [ ] **🚨 表面稼働vs実機能停止**: システム稼働中でも核心機能が停止している状況
- [ ] **🚨 定期エラー発生**: 7-8分間隔の定期エラーは根本的設計問題

### 📋 隠れたエラー発見時の対応（今回追加）
1. **IntegratedRiskManager引数エラー**: 
   - 即座にorchestrator.pyのevaluate_trade_opportunity呼び出し修正
   - ticker情報・残高取得処理の追加
2. **Discord embed構造エラー**:
   - discord.py内のembed生成処理の根本修正
   - logger.pyのDiscord通知呼び出し処理確認
3. **エラー連鎖対策**:
   - 各エラーの独立性確保・互いに影響しない設計
   - 通知エラーが取引実行に影響しない分離

---

## 🎯 9. 総合判定・次回アクション

### ✅ 最終チェックリスト（Phase 13.6強化版）
- [ ] **基盤**: Cloud Run最新版正常稼働・JST時刻表示
- [ ] **データ**: マルチタイムフレーム取得・**🚨12特徴量完全生成（12/12個）**（Phase 13.6対応）
  - 基本特徴量3個（close, volume, returns_1）+ テクニカル指標6個 + 異常検知指標3個
- [ ] **ML**: モデル読み込み・**🚨fitted状態・12特徴量セット予測実行成功**（今回見逃し防止）
- [ ] **取引**: エントリー準備・**🚨BUY/SELLシグナル生成・hold固定でない**（今回見逃し防止）
- [ ] **通知**: Discord webhook 401エラー解決・通知成功
- [ ] **継続稼働**: **🚨最新ログ10分以内・システム停止なし・取引サイクルエラーなし**（今回見逃し防止）
- [ ] **安定性**: 過去頻出問題ゼロ・**EnsembleModel fitted エラーなし**

### 📋 問題発見時の対応
1. **🚨Critical問題**: 即座に根本原因分析・緊急修正実施
   - **MLモデル未学習**: MLモデル再作成・デプロイ
   - **システム停止**: サービス再起動・根本原因分析
   - **hold固定**: 戦略・ML予測システム修復
2. **Warning問題**: 監視強化・次回CI前に修正予定
3. **Info確認事項**: 将来改善・最適化候補として記録

### 🚨 今回見逃し防止の教訓
- **表面的な稼働確認だけでは不十分**
- **実際のエントリーシグナル生成まで確認必要**
- **MLモデルの学習状態まで詳細チェック必要**
- **最新ログ時刻でシステム停止を早期検出**

### 🚀 正常時の次回アクション
- 実取引開始判断（全チェック✅の場合）
- パフォーマンス監視継続
- 追加改善項目の検討・実装

---

## 📝 確認結果記録テンプレート

```
## 🕒 チェック実施時刻: [JST時刻記載]

### ✅ 正常確認項目
- [ ] Cloud Run稼働: 詳細
- [ ] データ取得・特徴量生成: 詳細
- [ ] Discord通知: 詳細

### 🚨 今回見逃し防止チェック結果
- [ ] **MLモデル学習状態**: ✅fitted / 🚨not fitted
- [ ] **BUY/SELLシグナル生成**: ✅生成中 / 🚨hold固定
- [ ] **最新ログ時刻**: [最新ログ時刻] - ✅10分以内 / 🚨停止検出
- [ ] **取引サイクルエラー**: ✅なし / 🚨EnsembleModel エラー

### ⚠️ 要注意項目
- [ ] 項目: 詳細・対応予定

### 🚨 Critical問題
- [ ] 問題: 詳細・即座対応必要

### 🎯 総合判定
- **稼働状況**: ✅正常 / ⚠️注意 / 🚨問題
- **取引準備**: ✅準備完了 / ⚠️要調整 / 🚨未完了
- **実トレード可否**: ✅可能 / 🚨システム修復必要
- **発見エラー数**: [ToDo.mdに記録したエラー数]個
- **次回アクション**: [具体的アクション記載]
```

---

## 🔧 チェック完了後のまとめて修正フロー

### ✅ 全項目チェック完了後の手順

1. **記録エラー確認**:
```bash
# ToDo.mdに記録されたエラーを確認
grep -A 20 "CI後チェック発見エラー" /Users/nao/Desktop/bot/docs/開発計画/ToDo.md
```

2. **エラー優先順位付け**:
   - 🚨**最高優先**: システム停止・取引実行阻害
   - 🚨**高優先**: ML予測・Discord通知・API認証エラー
   - ⚠️**中優先**: パフォーマンス・監視機能問題
   - 📝**低優先**: ログ出力・設定微調整

3. **まとめて修正実行**:
   - 最高・高優先エラーから順次修正
   - 修正後は該当部分の再チェック実施
   - 完了したエラーはToDo.mdから削除または完了マーク

4. **修正完了確認**:
   - 修正版のCI/CD実行・デプロイ確認
   - 重要部分の部分的再チェック実施
   - システム安定稼働確認

**📋 この方式の利点**:
- チェック作業の中断なし・全項目網羅確保
- エラーの見落とし防止・体系的な問題管理
- 優先順位に基づく効率的修正・影響度考慮
- 修正履歴の記録・再発防止対策確立