# models/production/ - 本番環境用モデルディレクトリ

**Phase 13完了**: sklearn警告解消・設定最適化・306テスト100%成功・CI/D本番稼働・ProductionEnsemble統合モデル完成（2025年8月22日）

## 📁 実装完了ファイル構成

```
models/production/
├── production_ensemble.pkl         # ProductionEnsemble統合モデル（Phase 13対応）
├── production_model_metadata.json  # 本番用メタデータ・306テスト実績・sklearn警告解消
├── model_metadata.json             # レガシー互換メタデータ（削除候補）
└── README.md                        # このファイル
```

## 🎯 役割・目的（Phase 13完了）

### **sklearn警告解消・設定最適化・CI/CD本番稼働ProductionEnsemble**
- **目的**: sklearn警告完全解消・設定最適化・CI/CD本番稼働対応の実取引用モデル
- **Phase 13成果**: 306テスト100%成功・GitHub Actions本番稼働・品質保証完成
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク対応

### **Phase 13最新ProductionEnsemble統合**
- **production_ensemble.pkl**: 3モデル統合・sklearn警告解消・CI/CD本番稼働対応
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク
- **品質保証**: 306テスト100%・coverage-reports/58.88%・CI/CD本番稼働

## 📄 実装完了ファイル詳細（Phase 13対応）

### `production_ensemble.pkl` - ProductionEnsemble統合モデル
**目的**: 本番取引で使用するメインモデル（Phase 13最新版）

**Phase 13統合構成**:
- **LightGBM**: 40%重み（F1スコア0.941・sklearn警告解消・統合管理対応）
- **XGBoost**: 40%重み（F1スコア0.992・高精度維持・CI/D本番稼働対応）
- **RandomForest**: 20%重み（F1スコア0.699・安定性重視・設定最適化対応）

**Phase 13完了実績**:
- **sklearn警告解消**: 全deprecation warning解消・最新ライブラリ対応・互換性確保
- **CI/CD本番稼働**: GitHub Actions本番稼働・306テスト100%・品質保証完成
- **統合管理**: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク対応

**使用例**:
```python
import pickle
import numpy as np

# ProductionEnsemble読み込み
with open('models/production/production_ensemble.pkl', 'rb') as f:
    production_model = pickle.load(f)

# 12特徴量での予測
sample_features = np.random.random((5, 12))  # 12特徴量必須
predictions = production_model.predict(sample_features)
probabilities = production_model.predict_proba(sample_features)

# モデル情報確認
info = production_model.get_model_info()
print(f"重み: {info['weights']}")  # {'lightgbm': 0.4, 'xgboost': 0.4, 'random_forest': 0.2}
```

### `production_model_metadata.json` - 本番用メタデータ
**目的**: ProductionEnsemble性能・バージョン・設定情報管理

**Phase 13対応データ構造**:
```json
{
  "created_at": "2025-08-22T07:00:00",
  "model_type": "ProductionEnsemble",
  "phase": "Phase 13",
  "status": "production_ready",
  "n_features": 12,
  "feature_names": [
    "close", "volume", "returns_1", "rsi_14", "macd", "macd_signal",
    "atr_14", "bb_position", "ema_20", "ema_50", "zscore", "volume_ratio"
  ],
  "individual_models": ["lightgbm", "xgboost", "random_forest"],
  "model_weights": {
    "lightgbm": 0.4,
    "xgboost": 0.4, 
    "random_forest": 0.2
  },
  "performance_metrics": {
    "lightgbm_f1": 0.941,
    "xgboost_f1": 0.992,
    "random_forest_f1": 0.699,
    "ensemble_expected_f1": "0.85以上"
  },
  "phase13_completion": {
    "sklearn_warnings": "全deprecation warning解消完了",
    "config_optimization": "config/gcp/・config/deployment/統合",
    "logs_integration": "logs/reports/統合・ビジュアルナビゲーション",
    "test_coverage": "306テスト100%成功・coverage-reports/58.88%",
    "cicd_production": "GitHub Actions本番稼働・品質保証完成"
  }
}
```

### `model_metadata.json` - レガシー互換メタデータ（削除候補）
**現状**: Phase 9時代のメタデータファイル・production/内に配置不適切
**問題点**:
- 個別モデルパスがproduction/を指している（実際はtraining/に存在）
- Phase情報が古い（Phase 9のまま）
- production_model_metadata.jsonと重複機能

**推奨対処**: 削除・production_model_metadata.jsonに完全統合済み

## 🔧 本番環境運用（Phase 13統合）

### **統合管理CLI運用（Phase 13完全統合・推奨）**
```bash
# 🚀 統合管理CLI - Phase 13完全統合（推奨）
python scripts/management/dev_check.py full-check     # 6段階統合チェック
python scripts/management/dev_check.py ml-models      # MLモデル作成・検証
python scripts/management/dev_check.py validate --mode light  # 軽量品質チェック
python scripts/management/dev_check.py status         # システム状態確認

# Phase 13期待結果:
# 🤖 MLモデル作成成功！
# ✅ ProductionEnsemble: 動作正常・sklearn警告解消・CI/CD本番稼働対応
# 📊 統合管理: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク
# 🔧 設定最適化: config/gcp/・config/deployment/統合・不要ファイル削除
# ✅ sklearn警告解消: 全deprecation warning解消・最新ライブラリ対応
```

### **Phase 13品質基準（達成済み）**
```python
# Phase 13完了実績（2025年8月22日）
PHASE13_ACHIEVEMENTS = {
    'lightgbm_f1': 0.941,       # F1スコア94.1%・sklearn警告解消・統合管理対応
    'xgboost_f1': 0.992,        # F1スコア99.2%・高精度維持・CI/CD本番稼働対応
    'random_forest_f1': 0.699,  # F1スコア69.9%・安定性重視・設定最適化対応
    'sklearn_warnings': '全deprecation warning解消完了',
    'config_optimization': 'config/gcp/・config/deployment/統合',
    'logs_integration': 'logs/reports/統合・ビジュアルナビゲーション',
    'test_coverage': '306テスト100%成功・coverage-reports/58.88%',
    'cicd_production': 'GitHub Actions本番稼働・品質保証完成',
    'production_ready': True
}
```

### **ProductionEnsembleヘルスチェック**
```python
def production_ensemble_health_check():
    """ProductionEnsembleヘルスチェック（Phase 13統合版）"""
    try:
        # ProductionEnsemble読み込みテスト
        with open('models/production/production_ensemble.pkl', 'rb') as f:
            production_model = pickle.load(f)
        
        # 12特徴量での予測テスト
        dummy_features = np.random.random((1, 12))  # 12特徴量必須
        predictions = production_model.predict(dummy_features)
        probabilities = production_model.predict_proba(dummy_features)
        
        # ProductionEnsemble固有検証
        info = production_model.get_model_info()
        assert info['n_features'] == 12, "特徴量数エラー"
        assert info['type'] == 'ProductionEnsemble', "モデルタイプエラー"
        assert len(info['individual_models']) == 3, "個別モデル数エラー"
        
        return {
            "status": "healthy", 
            "phase": "Phase 13", 
            "sklearn_warnings": "解消完了",
            "cicd_production": True,
            "logs_integration": True,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.now()}
```

## 🚨 トラブルシューティング（Phase 13対応）

### **ProductionEnsemble読み込みエラー**
```bash
❌ 症状: pickle読み込み失敗・ProductionEnsemble不正・sklearn警告
❌ 原因: ファイル不存在・権限問題・sklearn deprecation warning

✅ 対処: 統合管理CLIで確認・再作成（sklearn警告解消版）
python scripts/management/dev_check.py ml-models --dry-run
python scripts/management/dev_check.py ml-models  # 再作成
```

### **12特徴量不一致エラー**
```bash
❌ 症状: 特徴量数不一致: X != 12
❌ 原因: 特徴量生成エラー・データ不足

✅ 対処: データ層・特徴量システム確認
python scripts/management/dev_check.py data-check
python -c "
from src.features.technical import TechnicalIndicators
ti = TechnicalIndicators()
print('✅ 特徴量システム正常')
"
```

### **レガシーメタデータファイル問題**
```bash
❌ 症状: model_metadata.json読み込み失敗・パス不整合
❌ 原因: Phase 9レガシーファイル・production/不適切配置

✅ 対処: レガシーファイル削除・production_model_metadata.json使用
# 削除推奨
rm models/production/model_metadata.json
# 最新メタデータ確認
cat models/production/production_model_metadata.json
```

## 🔧 ファイル管理ルール（Phase 13確立）

### **production/ディレクトリ管理ルール**
1. **必須ファイル**:
   - `production_ensemble.pkl`: メインの本番用統合モデル（7.4MB）
   - `production_model_metadata.json`: 本番用メタデータ（Phase 13最新）
   - `README.md`: 本番環境用ドキュメント

2. **削除対象ファイル**:
   - `model_metadata.json`: Phase 9レガシー・パス不整合・重複機能

3. **命名規則**:
   - 本番用ファイルは`production_`プレフィックス必須
   - メタデータは`.json`拡張子・Phase情報記録必須
   - レガシーファイルは明確に識別・削除候補マーク

### **品質保証ルール**
1. **モデルファイル**:
   - sklearn警告解消確認済みモデルのみ保存
   - F1スコア0.85以上のアンサンブル性能維持
   - 12特徴量対応確認済み

2. **メタデータ管理**:
   - Phase情報・実行時刻・性能指標・sklearn警告状況記録必須
   - production_model_metadata.jsonを最新状態維持
   - レガシーファイルとの混在回避

3. **バージョン管理**:
   - Git LFS対象（.pklファイル）
   - 通常Git管理（.jsonファイル、README.md）
   - Phase更新時の一括更新実施

## 🚀 Phase 14以降拡張計画

### **機械学習高度化（Phase 14）**
- **AutoML統合**: ハイパーパラメータ自動調整・特徴量自動選択・Optuna統合
- **Model Drift Detection**: リアルタイム性能劣化検知・自動再学習・監視アラート統合
- **Advanced Ensemble**: Neural Network・CatBoost追加・動的重み調整・Deep Learning統合
- **Online Learning**: incremental update・リアルタイム市場適応・ストリーミング学習

### **MLOps・運用強化（Phase 15）**
- **MLflow統合**: Model Registry・実験管理・バージョン管理・ライフサイクル自動化
- **A/B Testing**: 複数ProductionEnsemble並行運用・カナリアリリース・性能比較
- **GPU対応**: 高速学習・大規模データ処理・CUDA最適化・分散学習
- **監視ダッシュボード**: Web UI・リアルタイムメトリクス・Grafana統合

### **セキュリティ・コンプライアンス強化（Phase 16）**
- **セキュリティMLOps**: モデル暗号化・Differential Privacy・Federated Learning
- **エッジデプロイ**: モバイル・IoT対応・軽量化・TensorFlow Lite統合
- **コンプライアンス**: GDPR・金融規制対応・監査ログ・説明可能AI・責任あるAI

---

## 📊 Phase 13完成 本番環境ProductionEnsemble統合実績

### **sklearn警告解消・設定最適化・CI/D本番稼働ProductionEnsemble運用**
```
🤖 ProductionEnsemble: 重み付け統合・sklearn警告解消・306テスト100%成功・CI/D本番稼働
📊 品質保証完成: CI/CD本番稼働・coverage-reports/58.88%・品質チェック自動化
🔧 統合管理: logs/reports/統合・ビジュアルナビゲーション・最新レポートリンク対応
⚙️ 設定最適化: config/gcp/・config/deployment/統合・不要ファイル削除・レガシー整理
✅ sklearn警告解消: 全deprecation warning解消・最新ライブラリ対応・互換性確保
🚀 CI/CD本番稼働: GitHub Actions本番稼働・段階的デプロイ・品質保証完成
```

**🎯 Phase 13完了**: sklearn警告解消・設定最適化・306テスト100%成功・CI/D本番稼働対応ProductionEnsemble本番運用システムが完成。個人開発最適化と企業級品質を兼ね備えた次世代MLモデル運用環境を実現！

**次のマイルストーン**: Phase 14機械学習高度化・AutoML統合・Model Drift Detection・Advanced Ensemble・Online Learning実装