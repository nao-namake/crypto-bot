# ml/ - 機械学習パイプライン・特徴量エンジニアリング

## 📋 概要

**Machine Learning Pipeline & Feature Engineering System**  
本フォルダは crypto-bot の機械学習機能を提供し、特徴量生成、モデル訓練、アンサンブル学習、97特徴量システムの実装を担当します。

**🎊 Phase 16.9最適化完了**: 2025年8月8日  
**整理効果**: 22個→16個（27%削減）・6,901行除去・誤参照防止・保守性向上

**🆕 2025年8月13日重大更新 - Phase 18完了**:
- **🚨 RandomForest互換性エラー完全解決**:
  - ensemble.py内でRandomForest内部DecisionTree要素へのパッチ適用
  - estimators_属性経由でのmonotonic_cst属性自動設定
  - 5箇所すべての予測メソッドで統一実装
  
- **🔧 アンサンブル予測復活・トレード実行可能**:
  - Base model 3失敗問題の根本解決
  - フォールバック処理からの脱却・完全予測実現
  - confidence値正常化・エントリーシグナル生成復活

- **📊 ensemble.py最終最適化**:
  - RandomForest内部要素対応の完全実装
  - black自動フォーマット完全準拠
  - トレード予測パイプライン堅牢性確保

**🎊 ChatGPT提案採用（Phase 1-2完了）**:
- **ensemble.py改善**:
  - フォールバック処理強化 - simple_fallbackモード追加
  - 「Strategy does not use ensemble models」エラー根本解決
  - TradingEnsembleClassifier強制使用保証システム

## 🎯 主要機能

### **特徴量エンジニアリング**
- 97特徴量完全実装システム
- テクニカル指標計算（RSI、MACD、ボリンジャーバンド等）
- マルチタイムフレーム特徴量生成
- 特徴量順序管理・整合性保証

### **機械学習モデル**
- LightGBM、XGBoost、RandomForest対応
- アンサンブル学習実装
- ベイズ最適化によるハイパーパラメータ調整
- モデル保存・読み込み機能

### **前処理パイプライン**
- データクリーニング・正規化
- 欠損値処理・外れ値除去
- 特徴量スケーリング
- ターゲット生成（分類・回帰）

### **品質管理**
- データ品質監視
- 特徴量重要度分析
- モデル性能評価
- ドリフト検出統合

## 📁 ファイル構成

```
ml/                                   # Phase 16.9最適化後（16個・全て必要）
├── __init__.py                       # パッケージ初期化
├── README.md                         # 本ドキュメント
│
├── ✅ 主要機能ファイル（9個）
├── preprocessor.py                   # Phase 16.3-A互換性レイヤー（57行）
├── feature_master_implementation.py # Phase 16.3-B互換性レイヤー（30行）
├── ensemble.py                       # TradingEnsembleClassifier（1,259行・重要）
                                      # 3モデル統合(LGBM+XGB+RF)・trading_stacking
├── model.py                          # MLModel統合（583行）
├── optimizer.py                      # ハイパーパラメータ最適化（374行）
├── target.py                         # ターゲット生成（69行）
├── data_quality_manager.py           # データ品質管理（957行）
├── cross_timeframe_ensemble.py       # クロスタイムフレーム（718行）
└── timeframe_ensemble.py             # タイムフレーム統合（631行）
│
├── ✅ 特徴量管理ファイル（3個）
├── feature_order_manager.py          # 特徴量順序管理（170行）
├── feature_defaults.py               # デフォルト値管理（332行）
└── feature_order_97_unified.json     # 97特徴量定義（5KB）
│
├── ✅ Phase 16.3分割システム（3サブフォルダ）
├── preprocessing/                    # Phase 16.3-A分割（4ファイル・2,942行）
├── features/master/                  # Phase 16.3-B分割（3ファイル・1,785行）
└── feature_engines/                  # 特徴量エンジン（3ファイル・1,718行）

📦 archive/legacy_systems/移動済み（Phase 16.9）
├── ml_split_backups/                 # 分割前バックアップ（5,115行）
│   ├── feature_master_implementation.py.backup
│   └── preprocessor.py.backup
└── ml_unused_files/                  # 未使用ファイル（1,786行）
    ├── bayesian_strategy.py          # 参照ゼロ
    ├── feature_engineering_enhanced.py # archiveでのみ使用
    └── dynamic_weight_adjuster.py     # deprecatedテストでのみ使用
```

## 🔍 各ファイルの役割

### **preprocessor.py（Phase 16.3-A互換性レイヤー）**
- **現在**: 57行の統合エクスポート（3,314行から98.3%削減）
- **実装**: `crypto_bot.ml.preprocessing/`から統合import
- **互換性**: 既存import文は全て動作継続
- **推奨import**: `from crypto_bot.ml.preprocessing import FeatureEngineer`

### **model.py**
- `MLModel`クラス - 統一モデルインターフェース
- `create_model()` - モデルファクトリー
- LightGBM/XGBoost/RandomForest統合
- モデル永続化・読み込み

### **ensemble.py**
- `TradingEnsembleClassifier`クラス - アンサンブル実装
- スタッキング・投票・加重平均対応
- 信頼度ベース予測
- モデル動的追加・削除

### **feature_master_implementation.py（Phase 16.3-B互換性レイヤー）**
- **現在**: 30行の統合エクスポート（1,801行から98.3%削除）
- **実装**: `crypto_bot.ml.features.master/`から統合import
- **互換性**: 既存import文は全て動作継続
- **推奨import**: `from crypto_bot.ml.features.master import FeatureMasterImplementation`

### **feature_order_manager.py**
- `FeatureOrderManager`クラス - 特徴量順序管理
- 学習・推論時の一貫性保証
- 特徴量検証・整合性チェック
- JSON形式での永続化

### **optimizer.py**
- `MLOptimizer`クラス - ハイパーパラメータ最適化
- Optuna統合
- ベイズ最適化・グリッドサーチ
- 交差検証統合

### **target.py**
- `TargetGenerator`クラス - ターゲット生成
- 分類（上昇/下降）・回帰対応
- 複数時間軸ターゲット
- クラスバランス調整

## 🚀 使用方法

### **基本的な特徴量生成**
```python
from crypto_bot.ml.preprocessor import Preprocessor

preprocessor = Preprocessor(config)
features_df = preprocessor.process(ohlcv_df)
```

### **モデル訓練**
```python
from crypto_bot.ml.model import create_model

model = create_model(
    model_type="lgbm",
    model_params={
        "n_estimators": 100,
        "max_depth": 10
    }
)
model.fit(X_train, y_train)
```

### **アンサンブル学習（Phase 16.9検証済み）**
```python
# TradingEnsembleClassifier（1,259行・広く使用）
from crypto_bot.ml.ensemble import TradingEnsembleClassifier

ensemble = TradingEnsembleClassifier(
    models=["lgbm", "xgb", "rf"],
    method="stacking"
)
ensemble.fit(X_train, y_train)
predictions = ensemble.predict_proba(X_test)
```

### **Phase 16.3分割システム活用**
```python
# 新しい推奨import（分割後システム）
from crypto_bot.ml.preprocessing import FeatureEngineer
from crypto_bot.ml.features.master import FeatureMasterImplementation

# 既存import（互換性レイヤー経由・継続動作）
from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.ml.feature_master_implementation import FeatureMasterImplementation
```

## ✅ Phase 16.9最適化完了効果

### **構造最適化達成**
- **ファイル削減**: 22個→16個（27%削減）・必要ファイルのみ保持
- **サブフォルダ統合**: Phase 16.3分割システム（preprocessing/・features/master/・feature_engines/）完成
- **バックアップ整理**: 全バックアップファイルをarchive/legacy_systems/に移動
- **機能重複解消**: 未使用・重複ファイル除去完了

### **誤参照防止完了**
- **バックアップ移動**: 5,115行の分割前ファイルをarchive/に安全移動
- **未使用ファイル移動**: 1,786行の不要ファイルをarchive/に分類保管
- **互換性保証**: Phase 16.3互換性レイヤーにより既存import継続動作
- **トレーサビリティ**: README.md付きでarchive管理・復元可能性維持

### **保守性向上実現**
- **探しやすさ向上**: 必要なファイルのみが残り、開発者の混乱除去
- **import明確化**: Phase 16.3-A/16.3-B分割システムへの明確な移行パス
- **アーキテクチャ整合性**: 97特徴量システム・アンサンブル学習の一貫した構造

### **継続改善課題**
- 各特徴量の詳細説明充実
- 特徴量エンジニアリングのベストプラクティス文書化
- モデル選択ガイドライン策定

## 📝 今後の展開

### **Phase 16.9最適化完了後の発展方向**

1. **Phase 16.3分割システム活用**
   - preprocessing/モジュールの機能拡張
   - features/master/システムの高度化
   - feature_engines/の並列処理対応

2. **アンサンブル学習進化**
   - TradingEnsembleClassifier（1,259行）の深層学習統合
   - cross_timeframe_ensemble.pyの GPU対応
   - timeframe_ensemble.pyの自動重み調整

3. **品質管理強化**
   - data_quality_manager.pyのリアルタイム監視
   - feature_order_manager.pyの自動バリデーション
   - 97特徴量システムの継続的改善

4. **次世代機能統合**
   - 深層学習ベース特徴量（preprocessing/統合）
   - 自動特徴量生成（feature_engines/拡張）
   - 説明可能性（SHAP/LIME統合）
   - AutoML対応（optimizer.py拡張）

5. **archive管理システム**
   - legacy_systems/からの機能復元プロセス確立
   - 削除ファイルの再評価・現代化機能
   - バックアップファイルの定期的な整理自動化

---

**Phase 16.9完全達成**: crypto_bot/ml/フォルダが最適構成に整理され、Phase 16.3分割システムと統合して最高の保守性・拡張性を実現しました。🎊