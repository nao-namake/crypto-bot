# Terminal 1: 統合問題分析レポート - API-onlyモード問題解決の糸口

## 🚨 **問題の核心: API-onlyモードで実行されてしまう問題**

### **現在の状況（2025年7月16日）**
暗号資産自動売買ボットをGoogle Cloud Run上で動作させているが、本来のライブトレードモードではなく、API-onlyモード（取引機能なし・APIサーバーのみ）で実行されてしまう。

---

## 📊 **4ターミナル並列調査で判明した事実**

### **1. システム構成**
- **プラットフォーム**: Google Cloud Run (マネージドコンテナサービス)
- **アーキテクチャ**: Docker コンテナ (Python 3.11-slim-bullseye)
- **取引所**: Bitbank (日本の暗号資産取引所)
- **MLモデル**: 101特徴量を使用したアンサンブル学習

### **2. 発見された根本原因**

#### **原因1: コンテナイメージのアーキテクチャ不一致**
```
エラー: Container manifest type 'application/vnd.oci.image.index.v1+json' must support amd64/linux
現状: ARM64イメージ（phase2-1752611639）をCloud Runにデプロイ試行
解決: AMD64イメージ（phase2-amd64-0027）への切り替えが必要
```

#### **原因2: Bitbank API認証エラー**
```
エラーコード: 40024
症状: AuthenticationError発生 → API-onlyモードへフォールバック
環境変数: BITBANK_API_KEY=null, BITBANK_API_SECRET=null
```

#### **原因3: 初期化時のATRハング問題**
```
問題箇所: INIT-5段階でのATR（Average True Range）計算
症状: データ取得でハング → タイムアウト → API-onlyモードへ
修正案: retry logic、timeout handling、fallback values実装
```

#### **原因4: 外部データフェッチャー依存関係エラー**
```
エラー: No module named 'yfinance'
影響: VIX・Macro・Fear&Greedデータ取得不可（0%成功率）
結果: 84特徴量中71個（85%）がデフォルト値
```

### **3. 現在のログ状況**
```
2025-07-15 20:45-20:54: API only mode: heartbeat (毎分ログ出力)
2025-07-15 20:37:27: Bitbank APIエラー40024検知
2025-07-15 20:33:04-20:33:43: INIT-1～INIT-8正常完了確認済み
```

---

## 🔍 **API-onlyモード発生のメカニズム**

### **通常の起動フロー（期待動作）**
```
1. コンテナ起動
2. 環境変数読み込み（MODE=live, EXCHANGE=bitbank）
3. API認証（Bitbank API_KEY/SECRET）
4. 初期データ取得（INIT-1～INIT-8）
5. MLモデルロード
6. ライブトレードループ開始
```

### **実際の起動フロー（問題発生）**
```
1. コンテナ起動 ✅
2. 環境変数読み込み ✅（MODE=liveは設定済み）
3. API認証 ❌（エラー40024でAuthenticationError）
4. エラーハンドリング → API-onlyモードへフォールバック ⚠️
5. APIサーバーのみ起動（取引機能なし）
6. heartbeatログ出力継続
```

---

## 💡 **試行済みの対策と結果**

### **1. Phase 2修正システム実装**
- INIT-5段階のATRハング対策（retry logic追加）
- 結果: ARM64イメージ問題で起動失敗

### **2. 環境変数設定確認**
- MODE="live"設定確認済み
- 結果: API認証情報（KEY/SECRET）がnullで設定されていない

### **3. サービス再デプロイ**
- 複数のサービス作成試行
- 結果: イメージ存在エラー・アーキテクチャ不一致

---

## ❓ **ChatGPTへの質問事項**

### **主要な質問**
1. **API-onlyモードへのフォールバック防止方法**
   - エラーハンドリングでAPI-onlyモードにフォールバックする仕組みを、完全に無効化する方法は？
   - 起動時のエラーで即座に失敗させる設定は可能か？

2. **Cloud Run環境でのシークレット管理**
   - 環境変数がnullになる原因と対策
   - Secret Managerとの連携でのベストプラクティス

3. **コンテナ起動時の依存関係解決**
   - yfinanceのような外部パッケージの確実なインストール方法
   - マルチステージビルドでの依存関係管理

4. **アーキテクチャ固定方法**
   - Docker buildxでAMD64限定ビルドの確実な方法
   - Cloud Runでのアーキテクチャ検証方法

### **技術詳細情報**
- Python起動コマンド: `python scripts/start_live_with_api.py`
- Dockerfile: Python 3.11-slim-bullseye ベース
- Cloud Run設定: memory=2Gi, cpu=1000m, timeout=3600
- 必要な環境変数: MODE, EXCHANGE, BITBANK_API_KEY, BITBANK_API_SECRET

---

## 🎯 **解決に向けた仮説**

1. **起動スクリプトの改修**
   - API-onlyモードを選択する条件分岐を削除
   - 認証エラー時は即座にexit(1)で終了

2. **環境変数の確実な注入**
   - Cloud Run サービス作成時の --set-secrets オプション使用
   - Secret Manager参照の明示的な設定

3. **ヘルスチェックの厳格化**
   - /health エンドポイントでモード確認
   - API-onlyモードの場合は503を返す

---

**このレポートをChatGPTに提示し、API-onlyモード問題の根本的な解決策についてアドバイスを求めたい。**