# api/ - APIサーバー・ヘルスチェック管理

## 📋 概要

**API Server & Health Check System**  
本フォルダは crypto-bot のAPIサーバー機能を提供し、主にCloud Run環境でのヘルスチェックとシステム監視を担当します。

## 🎯 主要機能

### **ヘルスチェックAPI**
- Cloud Run/ロードバランサー向けヘルスチェックエンドポイント
- システム状態・依存関係の確認
- パフォーマンス指標の提供
- エラー耐性状態の報告

### **APIサーバー管理**
- FastAPIベースのRESTful API実装
- バックグラウンドでのAPIサーバー起動・停止
- 非同期処理対応
- グレースフルシャットダウン

## 📁 ファイル構成

```
api/
├── __init__.py      # パッケージ初期化・エクスポート管理
├── health.py        # ヘルスチェックエンドポイント実装  
├── server.py        # APIサーバー管理・追加エンドポイント
└── legacy.py        # Phase 16.5-B: 旧api.py機能（フォールバック用）
```

## 🔍 各ファイルの役割

### **__init__.py**
- FastAPI appインスタンスのエクスポート
- health_checkerのエクスポート
- ImportError対応（FastAPI未インストール時のフォールバック）

### **health.py**
- `/health` - 基本ヘルスチェックエンドポイント
- `/health/detailed` - 詳細システム状態エンドポイント
- `/health/resilience` - エラー耐性状態エンドポイント
- 各種システムコンポーネントの状態確認機能
- Cloud Run環境対応

### **server.py**
- 追加的なAPIエンドポイント実装（必要に応じて）
- APIサーバーの拡張機能
- カスタムミドルウェア・ハンドラー
- legacy.py機能の統合利用

### **legacy.py（Phase 16.5-B移動）**
- 旧crypto_bot/api.pyから移動した機能群
- `create_app()`関数等のレガシーAPI実装
- server.pyでフォールバック機能として使用
- 既存コード互換性保証のための移行措置

## 🚀 使用方法

### **ローカル環境での起動**
```python
from crypto_bot.api.health import start_api_server
start_api_server(host="0.0.0.0", port=8080)
```

### **Cloud Run環境**
- main.pyで自動的にバックグラウンド起動
- PORT環境変数で指定されたポートで起動
- K_SERVICE環境変数でCloud Run環境を検出

### **エンドポイント例**
```bash
# 基本ヘルスチェック
curl http://localhost:8080/health
# 期待: {"status": "healthy", "mode": "paper", "margin_mode": false}

# 詳細状態確認
curl http://localhost:8080/health/detailed
# 期待: システムコンポーネントの詳細状態

# エラー耐性状態
curl http://localhost:8080/health/resilience
# 期待: サーキットブレーカー・リトライ状態
```

## ⚠️ 課題・改善点

### **Phase 16.5-B整理効果**
- **crypto_bot直下整理**: api.py → api/legacy.py適切配置完了
- **機能保持**: 既存機能をlegacy.pyとして保持・フォールバック対応
- **段階的統合**: server.py軽量化後、health.pyとの統合検討可能
- **責任明確化**: APIサーバー機能のapi/フォルダ集約実現

### **依存関係**
- FastAPIはオプショナル依存（未インストール時も動作）
- uvicornも同様にオプショナル
- より明確な依存関係管理が必要

### **エラーハンドリング**
- FastAPI未インストール時の動作保証強化
- エラーレスポンスの標準化
- タイムアウト処理の実装

### **監視機能拡張**
- メトリクス収集エンドポイントの追加
- Prometheus形式のメトリクスエクスポート
- ログ集約エンドポイント

## 📝 今後の展開

### **Phase 16.5-B整理完了後の発展**
1. **legacy.py段階的統合**
   - server.pyとlegacy.py機能の統合検討
   - 重複機能の整理・最適化
   - より明確なAPI階層構造の確立

2. **APIサーバー機能拡張**
   - OpenAPI仕様書の自動生成
   - 認証・認可機能の追加
   - WebSocket対応（リアルタイム通知）
   - GraphQLエンドポイントの検討
   - レート制限・DoS対策の実装

3. **crypto_bot構造最適化連携**
   - utils/config.py移動との連携最適化
   - visualization/dashboard.py連携強化
   - 全体アーキテクチャ整合性確保