# モデルファイル管理

## ディレクトリ構造

```
models/
├── production/
│   └── model.pkl      # 本番環境用モデル（固定ファイル名）
└── development/
    └── model_dev.pkl  # 開発・テスト用モデル
```

## 使用方法

### 本番環境
- **ファイルパス**: `/app/models/production/model.pkl`（Docker内）
- **ローカルパス**: `models/production/model.pkl`
- **固定ファイル名**: 常に`model.pkl`を使用

### 開発環境
- **ファイルパス**: `models/development/model_dev.pkl`
- **用途**: 新しいモデルのテスト、実験用

## 重要事項

1. **本番モデルの更新**
   - 新しいモデルを本番環境に適用する場合は、必ず`models/production/model.pkl`に上書き保存
   - バックアップを作成してから更新することを推奨

2. **Docker環境での参照**
   - Dockerfile内で`COPY models/ /app/models/`でコピー
   - アプリケーション内では`/app/models/production/model.pkl`を参照

3. **Cloud Storage連携**
   - 必要に応じてCloud Storageからダウンロードして配置
   - ダウンロード先は常に`models/production/model.pkl`