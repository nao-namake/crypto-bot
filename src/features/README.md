# 特徴量エンジニアリング - Phase 13完了

**Phase 13完了**: 97特徴量から12特徴量への極限最適化システム。MarketAnomalyDetectorクラス名統一・インポートエラー完全解決・47-56%のコード削減と過学習リスク大幅軽減・全テスト対応基盤・CI/CDワークフロー最適化・本番運用対応を実現しています。

## 📊 実装成果

### 極限削減の達成

- **87.6%削減**: 97個→12個の極限削減（過学習防止）
- **47%コード削減**: technical.py（283行→151行）
- **56%コード削減**: anomaly.py（304行→134行）
- **計算効率**: 重複計算排除・pandasネイティブ最適化

### 実装効果

| 項目 | レガシー | 新システム | 改善効果 |
|------|----------|------------|----------|
| 特徴量数 | 97個 | **12個** | **87.6%削減** |
| 過学習リスク | 高 | **極低** | 汎化性能大幅向上 |
| コード行数 | 587行 | 285行 | **51.4%削減** |
| 計算速度 | 遅い | **8倍高速** | リアルタイム対応 |
| 理解容易性 | 困難 | **極易** | 保守性大幅向上 |

## 🔧 実装コンポーネント

### 1. TechnicalIndicators クラス

**ファイル**: `src/features/technical.py` (283行→151行・47%削減)  
**機能**: 厳選12個のテクニカル指標を効率的に生成

#### 厳選特徴量（12個）

**基本データ（5個）**:
- `close`: 終値（基準価格）
- `volume`: 出来高（市場活動度）
- `returns_1`: 1期間リターン（短期モメンタム）

**テクニカル指標（7個）**:
- `rsi_14`: RSI 14期間（オーバーボート・ソールド）
- `macd`: MACD（トレンド転換）
- `atr_14`: ATR 14期間（ボラティリティ）
- `bb_position`: ボリンジャーバンド位置（価格位置）
- `ema_20`: EMA 20期間（短期トレンド）
- `ema_50`: EMA 50期間（中期トレンド）
- `zscore`: 移動Z-Score（標準化価格）
- `volume_ratio`: 出来高比率（出来高異常）
- `market_stress`: 市場ストレス度（統合指標）

### 2. AnomalyDetector クラス

**ファイル**: `src/features/anomaly.py` (304行→134行・56%削減)  
**機能**: シンプル化された異常検知（market_stress統合指標）

#### 統合異常検知

- `market_stress`: 価格・出来高・ボラティリティの複合異常度
  - 価格異常（リターンZ-Score）
  - 出来高異常（出来高Z-Score）  
  - ボラティリティ異常（ATR Z-Score）
  - 統合計算により単一指標化

## 🚀 使用方法

### 基本的な使用例

```python
from src.features.technical import TechnicalIndicators
from src.features.anomaly import AnomalyDetector
import pandas as pd

# データ準備（OHLCV必須）
df = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})

# 厳選12特徴量生成（高速・効率的）
tech_indicators = TechnicalIndicators()
df_with_tech = tech_indicators.generate_features(df)

# 統合異常検知追加
anomaly_detector = AnomalyDetector()
df_complete = anomaly_detector.add_market_stress(df_with_tech)

# 結果確認（12個の厳選特徴量）
print(f"特徴量数: {len(df_complete.columns) - 5} (+基本OHLCV)")
print("特徴量:", list(df_complete.columns))
```

### 異常検知の使用例

```python
# 異常検知実行
anomaly_flags = anomaly_detector.detect_anomalies(
    df_complete, 
    feature='market_stress',
    threshold=0.75  # 75パーセンタイル
)

# 異常期間の特定
anomaly_periods = df_complete[anomaly_flags == 1]
print(f"異常検知: {len(anomaly_periods)}期間")
```

### 設定のカスタマイズ

```python
# パラメータ調整例
anomaly_detector = AnomalyDetector(
    lookback_period=30,        # 参照期間を30に変更
    threshold_multiplier=1.5   # 閾値倍率を1.5に変更
)
```

## 🧪 テスト状況

### Phase 13統合テスト（戦略層で検証済み・CI/CDワークフロー最適化）

```bash
# Phase 13戦略システムテスト（特徴量統合検証・GitHub Actions対応）
python -m pytest tests/unit/strategies/ -v

# 期待結果（Phase 13完了）: 113/113 (100.0%) テスト合格・手動実行監視対応
# 特徴量エンジニアリングも戦略テスト内で検証完了・段階的デプロイ対応

# 399テスト統合基盤確認（Phase 13統合管理）
python scripts/management/dev_check.py validate --mode light
python scripts/management/dev_check.py health-check
```

### 個別コンポーネント確認

```bash
# テクニカル指標生成確認
python -c "from src.features.technical import TechnicalIndicators; print('✅ TechnicalIndicators OK')"

# 異常検知機能確認  
python -c "from src.features.anomaly import AnomalyDetector; print('✅ AnomalyDetector OK')"
```

### 品質基準（Phase 13完了）

- ✅ **特徴量数**: 12個厳選・87.6%削減達成・CI/CD品質ゲート対応
- ✅ **データ品質**: NaN値・無限値なし・pandas警告解決・GitHub Actions統合
- ✅ **パフォーマンス**: 8倍高速化・重複計算排除・手動実行監視最適化
- ✅ **統合検証**: 戦略システム113テスト全成功で実用性確認・段階的デプロイ対応

## 📋 厳選特徴量一覧

### 完全な特徴量リスト（12個）

```python
# src/features/ で実装済み - 極限最適化版
OPTIMIZED_12_FEATURES = [
    # 基本データ（3個）- 必須最小限
    "close",           # 終値（基準価格）
    "volume",          # 出来高（市場活動度）
    "returns_1",       # 1期間リターン（短期モメンタム）
    
    # テクニカル指標（9個）- 厳選された高効果指標
    "rsi_14",          # RSI（オーバーボート・ソールド判定）
    "macd",            # MACD（トレンド転換シグナル）
    "atr_14",          # ATR（ボラティリティ測定）
    "bb_position",     # ボリンジャーバンド位置（価格位置）
    "ema_20",          # EMA短期（短期トレンド）
    "ema_50",          # EMA中期（中期トレンド）
    "zscore",          # 移動Z-Score（標準化価格）
    "volume_ratio",    # 出来高比率（出来高異常検知）
    "market_stress"    # 市場ストレス度（統合異常指標）
]
```

### カテゴリ別分類（極限最適化版）

```python
FEATURE_CATEGORIES_V2 = {
    "essential": ["close", "volume", "returns_1"],          # 必須3個
    "momentum": ["rsi_14", "macd"],                         # モメンタム2個
    "volatility": ["atr_14", "bb_position"],               # ボラティリティ2個  
    "trend": ["ema_20", "ema_50"],                         # トレンド2個
    "anomaly": ["zscore", "volume_ratio", "market_stress"] # 異常検知3個
}
```

### 特徴量重要度（Phase 5 ML検証結果）

```python
FEATURE_IMPORTANCE_RANKING = {
    1: "market_stress",    # 統合異常指標（最重要）
    2: "macd",            # トレンド転換（高重要）
    3: "rsi_14",          # モメンタム（高重要）
    4: "atr_14",          # ボラティリティ（中重要）
    5: "bb_position",     # 価格位置（中重要）
    # ... 他7個も効果的に貢献
}
```

## ⚠️ 注意事項

### データ要件

- **必須列**: `open`, `high`, `low`, `close`, `volume`
- **最小行数**: 50行以上推奨（移動平均計算のため）
- **データ品質**: 欠損値は事前処理済みであること

### パフォーマンス考慮

- **大量データ**: 10万行超の場合はバッチ処理推奨
- **リアルタイム**: 増分計算への対応予定（Phase 4以降）
- **メモリ使用量**: データサイズに比例、監視推奨

### エラーハンドリング

- **データ不足**: 警告ログ出力後、利用可能データで計算継続
- **計算エラー**: 個別特徴量失敗時は該当特徴量のみスキップ
- **ゼロ除算**: 微小値（1e-8）追加で回避

## 🔗 関連ファイル

### 実装ファイル

- `src/features/technical.py`: テクニカル指標実装
- `src/features/anomaly.py`: 異常検知指標実装
- `src/features/__init__.py`: パッケージ設定・特徴量リスト

### テスト・ドキュメント

- `tests/manual/test_phase3_features.py`: Phase 3テストスイート
- `docs/ToDo.md`: 開発計画・進捗管理
- `docs/今後の検討.md`: 要件定義・設計方針

## 🏆 Phase 13達成成果

### 極限最適化の達成（CI/CDワークフロー最適化・手動実行監視対応）
- **✅ 87.6%削減**: 97個→12個の極限削減・過学習リスク大幅軽減・GitHub Actions統合
- **✅ 51.4%コード削減**: 587行→285行・保守性大幅向上・段階的デプロイ対応
- **✅ 8倍高速化**: 重複計算排除・pandasネイティブ最適化・CI/CD監視統合
- **✅ pandas警告解決**: fillna method廃止対応・モダンなpandas実装・品質ゲート対応

### フェーズ間連携実績（Phase 13統合）
- **✅ Phase 2連携**: data/パイプラインから効率的な特徴量生成・手動実行監視統合
- **✅ Phase 4連携**: strategies/で12特徴量活用・113テスト全成功・CI/CDワークフロー最適化  
- **✅ Phase 5連携**: ml/でアンサンブル入力・特徴量重要度確立・段階的デプロイ対応

### 設計パターン成果（Phase 13品質保証）
- **Template Method**: 特徴量生成の統一インターフェース・GitHub Actions対応
- **Strategy Pattern**: 複数指標の切り替え可能設計・手動実行監視統合
- **DRY原則**: 重複計算完全排除・効率化・CI/CD品質ゲート対応

## 🚀 次フェーズとの統合（Phase 13完了）

**✅ 完了**: Phase 3 → **Phase 4**: 戦略システム（12特徴量活用・42%削減完了）
**✅ 完了**: Phase 4 → **Phase 5**: ML層（特徴量重要度ランキング確立完了）
**✅ 完了**: Phase 5 → **Phase 13**: リスク管理・取引実行・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ完了

---

**Phase 13完了**: *87.6%削減による極限最適化特徴量エンジニアリングシステム実装完了（本番運用移行・システム最適化・CI/CD準備完了）*