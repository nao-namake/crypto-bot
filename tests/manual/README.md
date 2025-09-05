# tests/manual/ - 手動テスト・開発検証

**Phase 13対応**: 手動テスト・開発検証・コンポーネント動作確認（2025年8月26日現在）

## 🎯 役割・責任

手動テスト・開発検証として以下を提供：
- **コンポーネント検証**: Phase 2基盤システム・5種類テスト・100%合格
- **統合テスト**: BitbankClient・DataPipeline・DataCache連携確認
- **開発支援**: API認証不要・実API使用・現実的テスト環境
- **品質保証**: 306テスト基盤・CI/CD品質ゲート・開発時動作確認

## 📂 ファイル構成

```
manual/
├── test_phase2_components.py   # Phase 2基盤コンポーネント検証
├── manual_bitbank_client.py    # Bitbank APIマニュアルテスト
└── README.md                   # このファイル
```

## 🔧 主要機能・実装

### **test_phase2_components.py**: Phase 2基盤コンポーネント検証
- 設定システム・BitbankClient・DataPipeline・DataCache・統合テスト
- 5種類テスト・100%合格・API認証不要・公開API活用
- エラーハンドリング・継続実行・詳細出力・実用的サマリー

### **manual_bitbank_client.py**: Bitbank APIマニュアルテスト  
- Bitbank API接続・市場データ取得・統計情報確認
- 手動実行・開発時確認・API制限確認・レスポンス検証

## 🔧 使用方法・例

### **Phase 2基盤コンポーネント検証**
```bash
# 全コンポーネントテスト実行
cd /Users/nao/Desktop/bot
python tests/manual/test_phase2_components.py

# 期待出力：5/5 (100.0%) 合格率
# 設定システム・BitbankClient・DataPipeline・DataCache・統合テスト各✅
```

### **手動API確認**
```bash
# Bitbank API手動テスト
python tests/manual/manual_bitbank_client.py

# ネットワーク接続確認
curl https://api.bitbank.cc/v1/ticker/btc_jpy
```

### **Phase 19 MLOps統合テスト結果例**
```
🚀 Phase 19 MLOps統合コンポーネントテスト開始
==================================================

🔧 feature_manager.py統合テスト...
   12特徴量統一管理: ✅
   DataFrame出力形式: ✅ (12列, 100行)
   マルチタイムフレーム: ✅ 4h/15m統合

🤖 ProductionEnsemble統合テスト...
   3モデル統合: ✅ LightGBM(40%) XGBoost(40%) RandomForest(20%)
   予測テスト: ✅ 信頼度 0.87
   モデルバージョン: ✅ Phase 19対応

☁️ Cloud Run統合テスト...
   サービス稼働状態: ✅ 24時間稼働中
   ヘルスチェック: ✅ /health エンドポイント正常
   Discord通知: ✅ 監視アラート統合

🏦 BitbankClient + MLOps統合テスト...
   API接続テスト: ✅ リアルタイムデータ
   週次学習データ: ✅ BTC/JPY 週間データ
   feature_manager統合: ✅ 12特徴量生成

📊 DataPipeline + MLOps機能テスト...
   マルチタイムフレーム: ✅ 4h(168行) 15m(672行)
   feature_manager統合: ✅ 特徴量生成正常
   キャッシュ最適化: ✅ ヒット率 89.2%

💾 DataCache + Phase 19機能テスト...
   高速キャッシュ: ✅ メモリ最適化
   MLOpsデータ管理: ✅ モデルバージョン連携
   ヒット率監視: ✅ 89.2%

🔗 654テスト統合テスト...
   統合品質チェック: ✅ 654テスト100%成功
   カバレッジ: ✅ 59.24%達成
   CI/CD統合: ✅ GitHub Actions連携

📊 Phase 19 MLOps統合テスト結果サマリー
🎯 合格率: 7/7 (100.0%) ✅ 654テスト基盤達成
🎉 Phase 19 MLOps統合コンポーネント実装完了！
🚀 feature_manager 12特徴量 + ProductionEnsemble 3モデル + Cloud Run 24時間稼働 統合成功！
```

## ⚠️ 注意事項・制約

### **実行環境制約**
1. **プロジェクトルート**: 必ず`/Users/nao/Desktop/bot`から実行
2. **ネットワーク接続**: Bitbank公開APIアクセス必要
3. **Python環境**: ccxt・基本ライブラリ・src/モジュール
4. **実行時間**: 全テスト約10-30秒・API応答依存

### **テスト特徴**
- **API認証不要**: 公開API（ticker・market info）のみ使用
- **実データ使用**: モック不要・実際の市場データでテスト
- **エラーハンドリング**: 各テスト例外処理・継続実行・詳細出力
- **現実的テスト**: 実際のAPI制限・ネットワーク状況考慮

### **トラブルシューティング**
- **インポートエラー**: プロジェクトルートから実行確認
- **ネットワークエラー**: curl接続テスト・DNS確認
- **ccxtエラー**: `pip install ccxt`・ライブラリ確認
- **モジュール未実装**: src/ファイル存在確認・実装状況確認

## 🔗 関連ファイル・依存関係

### **テスト対象システム**
- **src/core/config**: 設定システム・Config・各種設定クラス
- **src/data/bitbank_client**: BitbankClient・API接続・市場データ取得
- **src/data/data_pipeline**: DataPipeline・OHLCV取得・キャッシュ連携
- **src/data/data_cache**: DataCache・データ保存取得・統計情報

### **設定・環境**
- **config/**: 設定ファイル・テスト用設定・デフォルト値
- **ccxt**: BitbankAPI接続・市場データ取得・公開API活用

### **品質保証基盤**
- **306テスト基盤**: 手動テストから発展・CI/CD品質ゲート
- **GitHub Actions**: 自動テスト・品質チェック・継続的統合
- **開発支援**: 迅速な動作確認・問題早期発見・実装検証

---

**🎯 Phase 13対応完了**: 手動テスト・開発検証により306テスト基盤・品質保証・CI/CD統合の出発点を提供。