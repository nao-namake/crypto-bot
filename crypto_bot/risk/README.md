# risk/ - リスク管理・ポジションサイジング

## 📋 概要

**Risk Management & Position Sizing System**  
本フォルダは crypto-bot のリスク管理機能を提供し、ポジションサイジング、ストップロス計算、資金管理、Kelly基準実装を担当します。

## 🎯 主要機能

### **ポジションサイジング**
- 口座残高に対するリスク割合管理
- ATRベースの動的サイズ調整
- ボラティリティ連動ロット計算
- 最大ポジション制限

### **ストップロス管理**
- ATR倍数によるストップ幅計算
- トレーリングストップ対応
- 段階的利確レベル設定
- リスクリワード比最適化

### **Kelly基準実装**
- 最適投資比率計算
- 勝率・ペイオフ比考慮
- 過去実績ベース調整
- 最大Kelly制限（破産防止）

### **積極的リスク管理**
- 信頼度ベースサイジング
- 勝率ボーナス機能
- VIX連動リスク調整
- マルチファクター評価

## 📁 ファイル構成

```
risk/
├── __init__.py           # パッケージ初期化
├── manager.py           # 基本リスク管理実装
└── aggressive_manager.py # 積極的リスク管理実装
```

## 🔍 各ファイルの役割

### **manager.py**
- `RiskManager`クラス - 基本リスク管理
- ポジションサイズ計算（固定リスク%）
- ATRベースストップロス計算
- 動的ポジションサイジング
- バランス型リスク管理
- 破産リスク防止機能

### **aggressive_manager.py**
- `AggressiveRiskManager`クラス - 積極的リスク管理
- RiskManagerを継承・拡張
- 信頼度ベースサイジング（50-90%でスケール）
- 強化Kelly基準（勝率ボーナス付き）
- ボラティリティ適応型スケーリング
- 最大収益化戦略

## 🚀 使用方法

### **基本的なリスク管理**
```python
from crypto_bot.risk.manager import RiskManager

# リスク管理初期化
risk_manager = RiskManager(
    risk_per_trade=0.02,    # 1トレード2%リスク
    stop_atr_mult=2.0,      # ATRの2倍をストップ幅
    kelly_enabled=True,     # Kelly基準有効
    max_kelly_fraction=0.25 # 最大25%投資
)

# ポジションサイズ計算
position_size = risk_manager.calculate_position_size(
    balance=10000,
    entry_price=5000000,
    atr=50000,
    confidence=0.7
)
```

### **積極的リスク管理**
```python
from crypto_bot.risk.aggressive_manager import AggressiveRiskManager

# 積極的リスク管理
aggressive_rm = AggressiveRiskManager(
    base_risk_per_trade=0.02,
    confidence_scaling=True,
    volatility_adjustment=True,
    max_risk_per_trade=0.05  # 最大5%リスク
)

# 高信頼度時の積極的サイジング
position = aggressive_rm.calculate_enhanced_position(
    balance=10000,
    confidence=0.85,        # 高信頼度
    win_rate=0.65,         # 高勝率
    volatility_regime="low" # 低ボラティリティ
)
```

### **Kelly基準計算**
```python
# 過去の取引実績からKelly最適比率計算
trades_df = pd.DataFrame(trade_history)
kelly_fraction = risk_manager.calculate_kelly_criterion(
    trades_df,
    lookback_window=50
)

# Kelly基準でのポジションサイズ
kelly_position = risk_manager.apply_kelly_sizing(
    base_position_size=0.01,
    kelly_fraction=kelly_fraction
)
```

## ⚠️ 課題・改善点

### **ファイル数不足**
- リスク管理機能に対してファイル数が少ない
- より細分化されたリスクモジュール必要
- ポートフォリオリスク管理未実装

### **高度な機能不足**
- VaR（Value at Risk）計算
- モンテカルロシミュレーション
- ストレステスト機能
- 相関リスク管理

### **統合不足**
- 取引執行システムとの密結合
- リアルタイムリスク監視
- アラート機能統合

### **カスタマイズ性**
- より柔軟なリスクプロファイル
- ユーザー定義リスクルール
- 条件付きリスク調整

## 📝 今後の展開

1. **ポートフォリオリスク管理**
   - 複数ポジション統合管理
   - 相関リスク計算
   - 分散投資最適化
   - リスクパリティ実装

2. **高度なリスク指標**
   - VaR/CVaR計算
   - 最大ドローダウン予測
   - リスク調整後リターン
   - Sortino比率実装

3. **動的リスク調整**
   - 市場レジーム認識
   - 自動リスク削減
   - ボラティリティ予測
   - イベントリスク対応

4. **リスク可視化**
   - リアルタイムダッシュボード
   - リスクヒートマップ
   - シナリオ分析
   - What-if分析ツール