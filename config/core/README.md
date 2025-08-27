# config/core/ - コア設定システム

**Phase 13完了**: 包括的問題解決・モード設定一元化・セキュリティ強化・本番運用準備完了により、全環境共通の基本設定システムが完成

## 🎯 役割・責任

全環境（paper/live）で共通して使用される基本設定とシステム定義を管理します。モード設定一元化システムの中核として、環境変数とコマンドライン引数による優先度制御を実装し、安全かつ効率的な設定管理を実現します。

## 📂 ファイル構成

```
core/
├── README.md               # このファイル（Phase 13完了版）
├── base.yaml              # 基本設定（全環境共通・モード一元化対応）
└── feature_order.json     # 特徴量定義（12個厳選システム・Phase 3完了）
```

## 🔧 主要機能・実装

### **base.yaml - 基本設定システム（モード一元化対応）**

**🎯 3層優先順位によるモード制御**:
1. **コマンドライン引数**（最優先）: `python3 main.py --mode live`
2. **環境変数**（中優先）: `export MODE=live`
3. **YAMLファイル**（デフォルト）: `mode: paper`

**主要設定カテゴリ**:
```yaml
# モード設定（一元化対応）
mode: paper  # デフォルト：安全な仮想取引

# 取引所設定
exchange:
  name: bitbank
  symbol: BTC/JPY
  rate_limit_ms: 30000

# 機械学習設定  
ml:
  confidence_threshold: 0.35
  ensemble_enabled: true
  models: [lgbm, xgb, rf]

# リスク管理設定
risk:
  risk_per_trade: 0.01
  kelly_max_fraction: 0.03
  max_drawdown: 0.20

# データ取得設定
data:
  timeframes: [15m, 4h]
  since_hours: 96
  cache_enabled: true
```

### **feature_order.json - 12個厳選特徴量システム**

**Phase 3完了成果**:
- **大幅削減**: 97個→12個特徴量（87.6%削減）
- **カテゴリ分類**: basic(3) + technical(6) + anomaly(3)
- **重要度管理**: critical/high/medium/low分類

**特徴量構成**:
```json
{
  "total_features": 12,
  "feature_categories": {
    "basic": ["close", "volume", "returns_1"],
    "technical": ["rsi_14", "macd", "atr_14", "bb_position", "ema_20", "ema_50"],
    "anomaly": ["zscore", "volume_ratio", "market_stress"]
  }
}
```

### **Phase 13統合機能**
- **包括的問題解決**: MochiPoyAlertStrategy名前統一・API環境変数保護
- **セキュリティ強化**: GCP Secret Manager統合・実キー流出防止
- **品質保証**: 306テスト100%合格・58.88%カバレッジ達成
- **本番運用対応**: 24時間稼働・自動取引開始可能状態

## 📝 使用方法・例

### **基本的な設定読み込み**
```python
from src.core.config import load_config

# モード設定一元化対応
config = load_config('config/core/base.yaml', cmdline_mode='live')

# 設定値取得
mode = config.mode  # 優先順位に従った最終モード
confidence = config.ml.confidence_threshold
risk_per_trade = config.risk.risk_per_trade
```

### **モード制御の実例**
```bash
# 1. デフォルト（paper）
python3 main.py --config config/core/base.yaml

# 2. 環境変数優先
export MODE=live
python3 main.py --config config/core/base.yaml

# 3. コマンドライン最優先
python3 main.py --config config/core/base.yaml --mode live
# → 最終的にliveモードで実行
```

### **特徴量定義の参照**
```python
import json

with open('config/core/feature_order.json', 'r') as f:
    feature_order = json.load(f)

print(f"使用特徴量数: {feature_order['total_features']}")  # 12
print(f"削減率: {feature_order['reduction_history']['phase3_reduction']['reduction_rate']}")  # 0.876
```

### **設定継承・拡張**
```yaml
# 他の環境設定での継承例
<<: *base_config  # base.yamlを基底として

# 環境固有の設定を追加・上書き
production:
  min_order_size: 0.0001
  max_order_size: 0.001
```

## ⚠️ 注意事項・制約

### **モード設定の重要性**
- **デフォルト安全設計**: base.yamlは`mode: paper`で安全
- **本番移行慎重**: `MODE=live`設定は十分な検証後
- **一貫性確保**: システム全体で単一Config.mode参照
- **ミストレード防止**: 設定不整合による予期しない動作防止

### **設定変更時の注意**
- **下位互換性**: 既存環境設定への影響確認必須
- **全環境検証**: development/staging/production全て確認
- **バックアップ**: 変更前の設定保存
- **段階的適用**: 重要な変更は段階的に適用

### **特徴量システム制約**
- **12個固定**: feature_order.jsonで定義された12個厳選使用
- **順序重要**: 特徴量の順序変更は予測性能に影響
- **型安全**: 各特徴量の定義済み型・範囲を遵守

### **セキュリティ考慮事項**
- **API認証**: base.yamlにはAPIキー記載禁止（環境変数使用）
- **機密情報**: 実際の認証情報はGCP Secret Manager管理
- **設定分離**: 本番用機密情報と設定ファイルの分離

## 🔗 関連ファイル・依存関係

### **重要な外部依存**
- **`src/core/config.py`**: 設定読み込みシステム・3層優先度実装
- **`src/core/orchestrator.py`**: 統合システム制御・設定適用
- **`main.py`**: エントリーポイント・コマンドライン引数解析
- **`.github/workflows/ci.yml`**: CI/CDパイプライン・環境変数設定

### **環境別設定ファイル**
- **`config/production/production.yaml`**: 本番環境設定（Phase 13本番運用）
- **base.yamlのmode設定**: ペーパートレード環境制御（デフォルト）
- **`config/development/`**: 開発環境設定
- **`config/staging/`**: ステージング環境設定

### **システム統合**
- **GCP Secret Manager**: API認証情報安全管理
- **GitHub Actions**: 環境変数`MODE`自動設定
- **Cloud Run**: 本番稼働時の設定適用
- **pytest**: テスト実行時の設定検証（306テスト対応）

---

**重要**: このディレクトリはPhase 13完了により、包括的問題解決・モード設定一元化・セキュリティ強化が完成した全環境の基盤となります。設定変更時は特に慎重に行い、全環境での動作確認を実施してください。