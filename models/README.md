# モデルファイル管理

## ディレクトリ構造

```
models/
├── production/
│   └── model.pkl           # 本番環境用モデル（固定ファイル名）
├── validation/
│   ├── *_97_features.pkl   # バックテスト・検証用モデル
│   ├── *_metadata.json     # モデルメタデータ
│   └── ...                 # 実験的・検証用ファイル
└── development/
    └── model_dev.pkl       # 開発・テスト用モデル（ローカル実験）
```

## 使用方法

### 本番環境
- **ファイルパス**: `/app/models/production/model.pkl`（Docker内）
- **ローカルパス**: `models/production/model.pkl`
- **固定ファイル名**: 常に`model.pkl`を使用

### 検証・バックテスト環境
- **ディレクトリ**: `models/validation/`
- **用途**: バックテスト・検証用モデル、実験的モデル
- **ファイル例**:
  - `lgbm_97_features.pkl` - 97特徴量LightGBMモデル
  - `xgb_97_features.pkl` - 97特徴量XGBoostモデル
  - `rf_97_features.pkl` - 97特徴量RandomForestモデル
  - `*_metadata.json` - モデル性能・設定メタデータ

### 開発環境
- **ファイルパス**: `models/development/model_dev.pkl`
- **用途**: ローカル実験・開発用モデル

## 重要事項

1. **モデル昇格ワークフロー**
   - **検証フェーズ**: `models/validation/`で新モデルのバックテスト・性能検証
   - **昇格フェーズ**: 優秀な結果が出たモデルを`models/production/model.pkl`にコピー
   - **バックアップ**: 更新前に既存`model.pkl`のバックアップを作成（推奨）

2. **本番モデルの更新**
   - 新しいモデルを本番環境に適用する場合は、必ず`models/production/model.pkl`に上書き保存
   - 例: `cp models/validation/xgb_97_features.pkl models/production/model.pkl`

3. **Docker環境での参照**
   - Dockerfile内で`COPY models/ /app/models/`でコピー
   - アプリケーション内では`/app/models/production/model.pkl`を参照

4. **Cloud Storage連携**
   - 必要に応じてCloud Storageからダウンロードして配置
   - ダウンロード先は常に`models/production/model.pkl`