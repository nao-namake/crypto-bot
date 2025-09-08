# models/production_backup_20250904_055257/ - 本番モデルバックアップ

## 🎯 役割・責任

2025年9月4日 05:52:57時点での本番用機械学習モデルの完全バックアップを管理します。緊急時のロールバック、システム障害時の復旧、モデルの安全な管理を目的とした定期バックアップディレクトリとして機能し、システムの継続性と安定性を支援します。

## 📂 ファイル構成

```
models/production_backup_20250904_055257/
├── README.md                        # このファイル
├── production_ensemble.pkl          # バックアップされた本番モデル
└── production_model_metadata.json   # バックアップ時点のメタデータ
```

## 📋 主要ファイル・フォルダの役割

### **production_ensemble.pkl**
2025年9月4日 05:52:57時点での本番モデルのバックアップファイルです。
- 特定時点での完全なモデル状態を保存
- 緊急時のロールバック用として使用可能
- 約8.6MBのファイルサイズ（元モデルと同サイズ）
- pickle形式でシリアライズされた完全なモデルオブジェクト
- メタデータと組み合わせて完全な復旧が可能

### **production_model_metadata.json**
バックアップ時点でのモデル情報とメタデータです。
- バックアップ作成時刻の記録
- モデルの性能指標（バックアップ時点での値）
- 特徴量の定義と構成情報
- バージョン管理とGit情報
- モデルの設定とパラメーター
- 復旧時の整合性確認に使用

### **バックアップの特徴**
このバックアップディレクトリの重要な特徴：
- **タイムスタンプ**: ディレクトリ名に作成日時を記録
- **完全性**: モデルとメタデータの両方をセットで保存
- **復旧性**: 単体でのロールバック実行が可能
- **整合性**: バックアップ時点での完全な状態を保持

## 📝 使用方法・例

### **緊急時ロールバック手順**
```bash
# 現在の本番モデルをこのバックアップから復旧
cp models/production_backup_20250904_055257/production_ensemble.pkl models/production/
cp models/production_backup_20250904_055257/production_model_metadata.json models/production/

# ロールバック後の動作確認
python3 scripts/testing/dev_check.py ml-models --dry-run

# システム再起動（必要に応じて）
```

### **バックアップ内容の確認**
```python
import pickle
import json

# バックアップモデルの読み込みと確認
with open('models/production_backup_20250904_055257/production_ensemble.pkl', 'rb') as f:
    backup_model = pickle.load(f)

# バックアップメタデータの確認
with open('models/production_backup_20250904_055257/production_model_metadata.json', 'r') as f:
    backup_metadata = json.load(f)

print(f"バックアップ作成日時: {backup_metadata.get('created_at', 'N/A')}")
print(f"モデルタイプ: {backup_metadata.get('model_type', 'N/A')}")
print(f"性能指標: {backup_metadata.get('performance_metrics', {})}")
print(f"特徴量数: {len(backup_metadata.get('feature_names', []))}")
```

### **バックアップ検証テスト**
```python
def verify_backup_model():
    """バックアップモデルの動作検証"""
    import numpy as np
    
    try:
        # バックアップモデル読み込み
        with open('models/production_backup_20250904_055257/production_ensemble.pkl', 'rb') as f:
            model = pickle.load(f)
        
        # テストデータでの予測確認
        test_features = np.random.random((3, 12))
        predictions = model.predict(test_features)
        probabilities = model.predict_proba(test_features)
        
        print("✅ バックアップモデル検証成功")
        print(f"予測結果サンプル: {predictions[:2]}")
        return True
        
    except Exception as e:
        print(f"❌ バックアップモデル検証失敗: {e}")
        return False

verify_backup_model()
```

## ⚠️ 注意事項・制約

### **ロールバック実行時の注意**
- **互換性確認**: 現在のシステムとの互換性を事前に確認
- **テスト実行**: ロールバック後は必ず動作テストを実行
- **段階的復旧**: テスト環境での検証後に本番環境に適用
- **監視強化**: 復旧後は24-48時間の集中監視を実施

### **バックアップファイル管理**
- **読み取り専用**: 通常はバックアップファイルを変更しない
- **保存期間**: 定期的なクリーンアップによる古いバックアップの削除
- **容量管理**: 約8-10MBのファイルサイズによるディスク使用量
- **アクセス権限**: 適切なファイル権限設定の維持

### **復旧作業時の要件**
- **事前計画**: 復旧手順の事前確認と準備
- **ログ記録**: 復旧作業の詳細ログ記録
- **関係者通知**: 復旧作業の実施と完了の適切な通知
- **性能確認**: 復旧後のシステム性能と予測精度の確認

## 🔗 関連ファイル・依存関係

### **バックアップシステム**
- `models/production/`: 現在の本番モデル（バックアップ元）
- `models/archive/`: 長期アーカイブ（履歴管理）
- `scripts/testing/dev_check.py`: モデル検証・復旧確認スクリプト

### **運用・監視システム**
- `.github/workflows/`: 自動バックアップワークフロー
- `src/monitoring/discord_notifier.py`: バックアップ・復旧通知
- `logs/`: バックアップ・復旧作業のログ記録

### **設定・テストシステム**
- `config/core/unified.yaml`: 統一設定ファイル（全環境対応）
- `tests/unit/ml/`: モデルテスト・検証システム
- `src/ml/ensemble.py`: ProductionEnsemble実装（復旧対象）

### **復旧支援ツール**
- 現在のシステムとの差分比較ツール
- 性能指標の比較分析機能
- 段階的復旧のためのテスト環境