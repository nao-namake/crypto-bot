# Phase 19 src/core/config - MLOps統合設定システム管理

Phase 19 MLOps統合設定システム。feature_manager 12特徴量設定・ProductionEnsemble 3モデル設定・週次学習設定・Cloud Run設定・654テスト設定のMLOps完全統合を実現。

## 📂 フォルダ構成

```
src/core/config/
├── __init__.py           # 統合設定ローダー（412行）
├── config_classes.py     # 全設定dataclass統合（5クラス）
├── threshold_manager.py  # 閾値・動的設定管理（211行）
└── README.md            # 本ファイル
```

## 🎯 フォルダの役割

### **設定の一元管理**
- **ハードコーディング完全排除**: 160個の固定値をYAML化
- **3層優先順位**: コマンドライン > 環境変数 > YAMLファイル
- **動的設定変更**: YAML編集のみで再デプロイ不要

### **Phase 19 MLOps設定の階層化**
- **MLOps基本設定**: `config/core/base.yaml` - feature_manager + ProductionEnsemble設定
- **週次学習設定**: `config/core/thresholds.yaml` - GitHub Actions週次学習パラメータ
- **本番MLOps設定**: `config/production/` - Cloud Run 24時間稼働・本番環境設定

## 🏗 設計原則

### **1. 単一責任の原則**
```python
# 各設定クラスは明確な責任を持つ
- ExchangeConfig: 取引所接続設定
- MLConfig: 機械学習設定  
- RiskConfig: リスク管理設定
- DataConfig: データ取得設定
- LoggingConfig: ログ設定
```

### **2. 設定の外部化**
```python
# dataclassは全てOptional - 外部設定を強制
@dataclass
class MLConfig:
    confidence_threshold: Optional[float] = None  # YAMLから読み込み
    models: Optional[List[str]] = None
```

### **3. 深いマージ戦略**
```python
# base.yaml + thresholds.yaml の統合
config_data = merge_config_with_thresholds(base_config, thresholds)
```

## 🚀 使用方法

### **基本的な使用パターン**

```python
# 1. 設定読み込み
from src.core.config import load_config

config = load_config('config/core/base.yaml', cmdline_mode='paper')

# 2. 設定値アクセス
print(f"ML信頼度: {config.ml.confidence_threshold}")
print(f"取引所: {config.exchange.name}")
print(f"リスク: {config.risk.risk_per_trade}")

# 3. 動的閾値アクセス
from src.core.config import get_threshold

default_confidence = get_threshold('ml.default_confidence', 0.5)
max_errors = get_threshold('monitoring.max_consecutive_errors', 5)
```

### **設定妥当性チェック**

```python
# 設定の妥当性を検証
is_valid = config.validate()
if not is_valid:
    raise ValueError("設定エラーが発生しました")
```

## ⚙️ 拡張ルール

### **新しい設定クラス追加**

1. **config_classes.py** に新しいdataclassを追加:
```python
@dataclass 
class NewServiceConfig:
    param1: Optional[str] = None
    param2: Optional[int] = None
```

2. **__init__.py** のimportとcreate methodを追加:
```python
from .config_classes import NewServiceConfig

def _create_new_service_config(config_data: dict) -> NewServiceConfig:
    # デフォルト値補完ロジック
```

3. **base.yaml** または **thresholds.yaml** に設定追加

### **新しい閾値パラメータ追加**

1. **thresholds.yaml** に新セクション追加:
```yaml
new_service:
  param1: "default_value"
  param2: 100
```

2. **threshold_manager.py** に専用アクセサー追加:
```python
def get_new_service_config():
    return get_threshold('new_service', {})
```

## 🧪 テストパターン

### **設定読み込みテスト**
```python
def test_config_loading():
    config = Config.load_from_file('config/core/base.yaml')
    assert config.exchange.name == 'bitbank'
    assert config.ml.confidence_threshold == 0.65
```

### **閾値アクセステスト**  
```python
def test_threshold_access():
    value = get_threshold('ml.default_confidence', 0.5)
    assert isinstance(value, float)
```

## 📋 メンテナンスルール

### **1. ハードコーディング禁止**
- dataclassにデフォルト値を書かない（全てOptional）
- 固定値は必ずYAMLファイルで外部化

### **2. バックワード互換性**
- 設定名変更時は正規化ルールで対応
- 古い設定名も一定期間サポート

### **3. 設定検証**
- 新しい設定追加時は必ず`validate()`メソッド拡張
- 不正値の早期検出とエラーメッセージ改善

## 🔄 Phase 19 MLOps統合完了成果

- **MLOps設定統合**: feature_manager + ProductionEnsemble + 週次学習設定一元化
- **654テスト品質保証**: 59.24%カバレッジ・MLOps統合テスト完備
- **Cloud Run統合**: 24時間稼働設定・Discord 3階層監視設定
- **GitHub Actions統合**: 週次学習・CI/CD品質ゲート・段階的デプロイ設定

---
*Phase 19 MLOps統合完了: 2025年9月4日*