# デプロイ戦略ガイド

## 🚀 推奨デプロイメント手順

### 1. 初回起動（軽量モード）
```bash
# 環境変数設定
export FEATURE_MODE=lite  # 3特徴量モードで高速起動
export BITBANK_API_KEY=your_api_key
export BITBANK_API_SECRET=your_api_secret
```

### 2. 初期化状況確認
```bash
# ヘルスチェックで基本状態確認
curl https://your-service.run.app/health

# 初期化進捗の詳細確認
curl https://your-service.run.app/health/init

# 期待レスポンス（初期化完了時）
{
  "phase": "complete",
  "is_complete": true,
  "components": {
    "api_server": true,
    "basic_system": true,
    "statistics_system": true,
    "feature_system": true,
    "trading_loop": true
  }
}
```

### 3. 完全版への切り替え
初期化が完了し、システムが安定したら完全版に切り替え：

```bash
# Cloud Runで環境変数を更新
gcloud run services update crypto-bot-service-prod \
  --update-env-vars FEATURE_MODE=full \
  --region asia-northeast1
```

## 📊 モニタリング

### 初期化段階の監視
```bash
# 継続的な初期化状況監視
watch -n 5 'curl -s https://your-service.run.app/health/init | jq .'
```

### Phase 8統計システム確認
```bash
# 詳細ヘルスチェック
curl https://your-service.run.app/health/detailed

# status.jsonファイルの生成確認
# "trading": {"status": "healthy"} が表示されれば正常
```

## 🛠 トラブルシューティング

### 症状: 継続的な再起動
**対策**: 軽量モード（FEATURE_MODE=lite）で起動

### 症状: Phase 8統計システムが初期化されない
**確認事項**:
1. `/health/init`で各コンポーネントの状態確認
2. エラーログの確認
3. メモリ使用量の確認

### 症状: エントリーシグナルが発生しない
**確認事項**:
1. trading_loopがtrueになっているか確認
2. 151特徴量システムが正常に動作しているか確認
3. 市場条件がエントリー基準を満たしているか確認

## 🔧 設定ファイル

### 軽量版（高速起動用）
- **ファイル**: `config/production/production_lite.yml`
- **特徴量**: 3個（rsi_14, macd, sma_50）
- **用途**: 初期起動、動作確認

### 完全版（本番運用）
- **ファイル**: `config/production/production.yml`
- **特徴量**: 151個（VIX, Fear&Greed, Macro, Phase 3.2A-D高度特徴量含む）
- **用途**: 本番取引

## 📝 運用チェックリスト

### デプロイ前
- [ ] モデルファイルが`models/production/model.pkl`に配置されている
- [ ] APIキーが環境変数に設定されている
- [ ] 設定ファイルが正しく配置されている

### デプロイ後
- [ ] ヘルスチェックが正常応答
- [ ] 初期化が完了（/health/init確認）
- [ ] Phase 8統計システムが稼働
- [ ] メイントレーディングループが開始
- [ ] エントリーシグナル監視が動作

### 本番移行
- [ ] 軽量版で安定稼働確認
- [ ] 完全版への切り替え実施
- [ ] 151特徴量システム正常動作確認
- [ ] 取引実行能力確認