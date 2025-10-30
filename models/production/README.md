# models/production/ - 本番環境モデル管理（Phase 50.7完了時点）

## 🎯 役割・責任

実際の取引で使用される本番用機械学習モデルを管理します。**Phase 50.7: 3レベルモデルシステム**により、特徴量レベルに応じた最適なモデルを提供し、外部API障害時も安定した取引システム運用を実現します。

## 📂 ファイル構成（Phase 50.7完了版）

```
models/production/
├── README.md                        # このファイル（Phase 50.7完了版）
├── ensemble_level1.pkl              # Level 1: 70特徴量モデル（完全+外部API・1.5MB）
├── ensemble_level2.pkl              # Level 2: 62特徴量モデル（完全・外部APIなし・1.4MB）
├── ensemble_level3.pkl              # Level 3: 57特徴量モデル（基本のみ・1.3MB）
├── production_model_metadata.json   # モデル情報とメタデータ（2.7KB）
│
# 旧モデル名（Phase 50.7後方互換性維持）
├── production_ensemble_full.pkl     # → ensemble_level1.pkl（非推奨）
├── production_ensemble.pkl          # → ensemble_level2.pkl（非推奨）
└── production_ensemble_57.pkl       # → ensemble_level3.pkl（非推奨）
```

## 📋 主要ファイル・フォルダの役割

### **Phase 50.7: 3レベルモデルシステム**

#### **ensemble_level1.pkl** - Level 1: 完全+外部API（70特徴量）
最も高性能な完全装備モデルです。
- **特徴量構成**: 62基本特徴量 + 8外部API特徴量 = 70特徴量
- **外部API特徴量**（8個）:
  - マクロ経済: USD/JPY為替・日経225指数・米国10年債利回り
  - 市場センチメント: Fear & Greed Index・市場センチメント
  - 変化率: USD/JPY前日変化率・日経225前日変化率
  - 相関: USD/JPY-BTC相関係数
- **使用場面**:
  - 本番環境での通常運用（外部APIアクセス可能時）
  - バックテスト検証（外部API特徴量を0で埋めて環境一致）
- **フォールバック**: 外部API障害時は自動的にLevel 2にフォールバック
- **ファイルサイズ**: 約1.5MB

#### **ensemble_level2.pkl** - Level 2: 完全（62特徴量）
外部APIなしで動作する安定モデルです。
- **特徴量構成**: 62基本特徴量のみ（外部API特徴量8個を除外）
- **基本特徴量内訳**:
  - 価格・ボリューム: close・volume・volume_ratio等
  - モメンタム: RSI・MACD・ストキャスティクス等
  - ボラティリティ: ATR・ボリンジャーバンド等
  - トレンド: EMA・SMA・VWAP等
  - ブレイクアウト: ドンチャンチャネル等
  - レジーム: ADX・DI等
  - 戦略信号: 5戦略信号特徴量
- **使用場面**:
  - 外部API障害時の自動フォールバック
  - 外部APIコスト削減モード
- **フォールバック**: 読み込み失敗時はLevel 3にフォールバック
- **ファイルサイズ**: 約1.4MB

#### **ensemble_level3.pkl** - Level 3: 基本（57特徴量）
最小構成の軽量フォールバックモデルです。
- **特徴量構成**: 57基本特徴量のみ（外部API 8個 + 戦略信号 5個を除外）
- **基本特徴量のみ**:
  - 価格系指標・ボリューム系指標・テクニカル指標のみ
  - 戦略信号特徴量も除外（軽量化優先）
- **使用場面**:
  - Level 1・Level 2両方が使用不可の緊急時フォールバック
  - リソース制約環境での運用
- **フォールバック**: 読み込み失敗時はDummyModelにフォールバック
- **ファイルサイズ**: 約1.3MB

#### **後方互換性維持**（Phase 50.7）
旧モデル名から新モデル名への自動マッピング機能を実装。
- `production_ensemble_full.pkl` → `ensemble_level1.pkl`
- `production_ensemble.pkl` → `ensemble_level2.pkl`
- `production_ensemble_57.pkl` → `ensemble_level3.pkl`

既存システムは新モデルを探し、見つからない場合は旧モデルを自動的に使用します。

### **production_model_metadata.json**（Phase 49完了）
モデルの詳細情報とメタデータを管理するファイルです。
- モデルの性能指標（F1スコア、精度、再現率など）
- **55特徴量定義**（Phase 41.8実装）: 50基本特徴量 + 5戦略信号特徴量
  - ATRBased・MochipoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength
- 学習データとバリデーション情報（TimeSeriesSplit n_splits=5）
- バージョン管理とGit統合情報
- モデル作成日時と更新履歴
- 各アルゴリズムの重み設定（LightGBM: 0.4, XGBoost: 0.4, RandomForest: 0.2）
- Phase情報とステータス（Phase 49完了・production_ready）
- システム設定とパラメーター情報

### **モデル構成と特徴**（Phase 50.7完了）
ProductionEnsembleは複数のアルゴリズムを統合しています。

#### **Phase 50.7新機能: 3レベルモデルシステム**
- **レベル別特徴量選択**: 状況に応じた最適なモデル選択
  - Level 1（70特徴量）: 外部API統合による最高性能（バックテスト用）
  - Level 2（62特徴量）: 外部APIなしで安定動作（本番推奨）
  - Level 3（57特徴量）: 最小構成フォールバック（緊急時）
- **Graceful Degradation**: 4段階自動フォールバック
  - Level 1 → Level 2 → Level 3 → DummyModel
- **バックテスト環境一致**: Level 1（70特徴量）使用で実環境完全一致
- **設定駆動型モデル選択**: feature_order.json単一真実源管理

#### **アンサンブル学習基盤**（Phase 49完了）
- **アンサンブル手法**: 重み付き投票によるアンサンブル学習
- **実データ学習**: CSV実データ読み込み・過去180日分15分足データ
- **3クラス分類**: BUY/HOLD/SELL分類・閾値0.5%
- **TimeSeriesSplit**: n_splits=5による堅牢なCross Validation
- **Early Stopping**: rounds=20で過学習防止・LightGBM/XGBoost対応
- **SMOTE oversampling**: クラス不均衡対応・少数派クラス増強
- **Optunaハイパーパラメータ最適化**: TPESampler・3モデル自動最適化（Phase 40: 79パラメータ最適化統合）

#### **Strategy-Aware ML**（Phase 41.8実装）
実戦略信号を学習データに統合した高度なML学習システム。
- **訓練/推論一貫性**: 訓練時0-fill問題解決・実戦略信号を学習データに統合
- **Look-ahead bias防止**: 過去データのみ使用・未来データリーク防止
- **5戦略信号統合**: ATRBased・MochipoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength
- **信号エンコーディング**: action × confidence方式（buy=+1.0, hold=0.0, sell=-1.0）

#### **システム統合・運用**
- **特徴量管理**: 統一されたfeature_managerシステムとの連携・Phase 50.7: 3レベル対応
- **バージョン管理**: Git情報とモデルハッシュによる管理
- **性能監視**: 継続的な品質監視と自動アラート機能
- **週次自動学習**: GitHub Actions自動学習ワークフロー（毎週日曜18:00 JST）

## 📝 使用方法・例

### **モデルの基本使用方法**
```python
from src.ml.ensemble import ProductionEnsemble
from src.features.feature_manager import FeatureManager
import json

# システム初期化
feature_manager = FeatureManager()
model = ProductionEnsemble()

# メタデータ確認
with open('models/production/production_model_metadata.json', 'r') as f:
    metadata = json.load(f)
    print(f"モデルタイプ: {metadata['model_type']}")
    print(f"作成日時: {metadata['created_at']}")
    print(f"F1スコア: {metadata['performance_metrics']['f1_score']}")

# 市場データでの予測
market_data = get_market_data()
features = feature_manager.generate_features(market_data)
prediction = model.predict(features)
probabilities = model.predict_proba(features)
```

### **メタデータとバージョン確認**
```python
def check_model_info():
    """モデル情報の確認"""
    with open('models/production/production_model_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    print(f"モデルファイル: {metadata['model_file']}")
    print(f"特徴量数: {len(metadata['feature_names'])}")
    print(f"学習サンプル数: {metadata['training_info']['samples_count']}")
    
    # 性能指標表示
    metrics = metadata['performance_metrics']
    for metric, value in metrics.items():
        print(f"{metric}: {value}")

check_model_info()
```

### **Phase 50.7: 3レベルモデルの管理**
```bash
# Phase 50.7: 3レベルモデル学習（個別実行）
python3 scripts/ml/create_ml_models.py --level 1  # Level 1: 70特徴量
python3 scripts/ml/create_ml_models.py --level 2  # Level 2: 62特徴量
python3 scripts/ml/create_ml_models.py --level 3  # Level 3: 57特徴量

# Phase 50.7: 3レベルモデル並列学習（推奨）
python3 scripts/ml/create_ml_models.py --level 1 > /tmp/level1.log 2>&1 &
python3 scripts/ml/create_ml_models.py --level 2 > /tmp/level2.log 2>&1 &
python3 scripts/ml/create_ml_models.py --level 3 > /tmp/level3.log 2>&1 &

# モデルファイル確認（Phase 50.7: 新モデル名）
ls -lh models/production/ensemble_level*.pkl

# 旧モデル名との互換性確認
ls -lh models/production/production_ensemble*.pkl

# メタデータ確認
cat models/production/production_model_metadata.json | jq '.performance_metrics'

# 品質チェック（Phase 50.7完了版）
bash scripts/testing/checks.sh
```

## ⚠️ 注意事項・制約

### **ファイル管理要件**
- **読み取り専用**: 本番環境では基本的に読み取り専用として扱う
- **バックアップ**: 定期的なバックアップとarchiveフォルダへの保存
- **メタデータ同期**: モデル更新時はメタデータファイルも同時更新必須
- **バージョン管理**: Git情報とモデルハッシュによる厳密なバージョン管理

### **システムリソース制約**
- **メモリ使用量**: モデル読み込み時に約100-150MBのメモリを使用
- **ファイルサイズ**: モデルファイルは5-10MB程度の大容量
- **読み込み時間**: 初回読み込み時に数秒の待機時間が発生
- **同時アクセス**: 複数プロセスからの同時アクセス時の排他制御

### **品質保証要件**
- **性能監視**: 定期的な性能指標の監視と品質チェック
- **テスト実行**: モデル更新時の動作確認とテスト実行
- **ログ記録**: モデル使用状況とエラーの適切なログ記録
- **アラート機能**: 性能劣化や異常動作の検知と通知

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `src/features/feature_manager.py`: 特徴量生成と管理システム
- `src/ml/ensemble.py`: ProductionEnsemble実装クラス
- `scripts/ml/create_ml_models.py`: モデル学習・更新スクリプト

### **モデル管理システム**
- `models/training/`: 学習用個別モデル格納フォルダ
- `models/archive/`: 過去バージョン保存フォルダ
- `scripts/testing/checks.sh`: 品質チェック（Phase 39完了版）
- `scripts/ml/create_ml_models.py`: モデル学習・更新スクリプト

### **設定ファイル**
- `config/core/unified.yaml`: 統一設定ファイル（システム基本設定・本番環境設定・全環境対応）
- `config/core/thresholds.yaml`: 性能閾値設定

### **CI/CDとワークフロー**
- `.github/workflows/`: 自動学習・デプロイワークフロー
- `tests/unit/ml/`: 機械学習モジュールテスト

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク
- **LightGBM, XGBoost**: 勾配ブースティングライブラリ
- **imbalanced-learn**（Phase 39.4）: SMOTE oversamplingによるクラス不均衡対応
- **optuna**（Phase 39.5）: TPESamplerハイパーパラメータ最適化
- **pandas, numpy**: データ処理ライブラリ
- **pickle**: モデルシリアライゼーション