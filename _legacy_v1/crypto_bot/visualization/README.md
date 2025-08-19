# visualization/ - 可視化・ダッシュボードシステム

## 📋 概要

**Visualization & Dashboard System**  
本フォルダは crypto-bot の可視化・ダッシュボード機能を提供し、Streamlitベースの分析ツール、取引結果の可視化、リアルタイム監視を担当します。

**Phase 16.5-E整理日**: 2025年8月8日  
**作成理由**: monitor.py → dashboard.py移動により、可視化機能専用フォルダとして分離

## 🎯 主要機能

### **Streamlitダッシュボード**
- 取引パフォーマンス可視化
- リアルタイム価格・指標表示
- バックテスト結果分析
- インタラクティブチャート生成

### **データ可視化**
- 時系列価格チャート
- 技術指標重ね表示
- 取引ポイントマーキング
- 統計レポート生成

### **監視・分析ツール**
- ポートフォリオパフォーマンス追跡
- リスク指標可視化  
- トレンド分析ダッシュボード
- エラー・異常値検出表示

## 📁 ファイル構成

```
visualization/
├── __init__.py      # パッケージ初期化・メタ情報
└── dashboard.py     # Phase 16.5-E: monitor.py移動版（631行）
```

## 🔍 各ファイルの役割

### **__init__.py**
- `__all__ = ["dashboard"]` - モジュールエクスポート定義
- `__reorganization_info__` - Phase 16.5-E移動履歴記録
- フォルダ目的・分離理由の明確化
- monitoring/フォルダとの差別化情報

### **dashboard.py（Phase 16.5-E移動）**
- **元の場所**: `crypto_bot/monitor.py`
- **移動理由**: 可視化機能の論理的集約・monitoring/との機能分離
- **主な機能**:
  - Streamlitベースのwebアプリケーション
  - 取引データの可視化・分析ダッシュボード
  - リアルタイムチャート表示
  - バックテスト結果の詳細分析（631行）

## 🚀 使用方法

### **Streamlitダッシュボード起動**
```bash
# ダッシュボード起動
streamlit run crypto_bot/visualization/dashboard.py

# カスタム設定でダッシュボード起動
streamlit run crypto_bot/visualization/dashboard.py -- --config config/production/production.yml
```

### **プログラム内からの使用**
```python
from crypto_bot.visualization.dashboard import main

# ダッシュボードのメイン関数実行
main()
```

### **可視化機能の統合利用**
```python
# 将来的な統合利用例（拡張予定）
from crypto_bot.visualization import dashboard

# 特定データの可視化処理
dashboard.visualize_trading_results(results_df)
dashboard.show_performance_metrics(metrics)
```

## 🎨 可視化の特徴

### **監視系との差別化**
- **visualization/**: ユーザー向け可視化・分析・インタラクティブ操作
- **monitoring/**: システム監視・品質管理・自動アラート

### **技術スタック**
- **Streamlit**: Webダッシュボードフレームワーク
- **Plotly**: インタラクティブチャートライブラリ  
- **Pandas**: データ操作・分析
- **Matplotlib**: 静的チャート生成（必要時）

### **対応データ形式**
- バックテスト結果CSV
- リアルタイム取引データ
- 技術指標時系列データ
- パフォーマンス統計JSON

## ⚠️ 課題・改善点

### **Phase 16.5-E移動完了後の課題**
- **依存関係確認**: plotly等の可視化ライブラリ依存の明確化
- **機能拡張**: 単一ファイルから複数ファイル構成への発展
- **テスト不足**: 可視化機能の自動テスト実装

### **monitoring/との連携**
- データ品質監視結果の可視化統合
- パフォーマンス監視データのダッシュボード表示
- アラート情報の視覚的通知

### **ユーザビリティ向上**
- より直感的なUIデザイン
- カスタマイズ可能なダッシュボード
- レスポンシブデザイン対応

## 📝 今後の展開

### **Phase 16.5-E完了後の発展計画**

1. **ファイル構成拡張**
   ```
   visualization/
   ├── __init__.py
   ├── dashboard.py          # メインダッシュボード（既存）
   ├── charts/              # チャート生成モジュール
   │   ├── price_charts.py   # 価格チャート特化
   │   ├── indicator_charts.py  # 技術指標特化
   │   └── performance_charts.py  # パフォーマンス特化
   ├── layouts/             # ダッシュボードレイアウト
   ├── components/          # 再利用可能コンポーネント
   └── themes/              # カスタムテーマ
   ```

2. **機能拡張**
   - 多通貨ペア対応ダッシュボード
   - カスタム指標追加機能
   - レポート自動生成・エクスポート
   - WebSocket対応リアルタイム更新

3. **integration強化**
   - ml/フォルダとの連携（予測結果可視化）
   - backtest/フォルダとの連携（結果自動可視化）
   - strategy/フォルダとの連携（戦略分析表示）

4. **ユーザーエクスペリエンス向上**
   - ダークモード対応
   - 多言語対応（日/英）
   - モバイルレスポンシブ対応
   - ショートカットキー対応

## 🔗 関連フォルダとの関係

### **monitoring/ との差別化**
- **monitoring/**: システム内部監視・品質管理・自動化
- **visualization/**: ユーザー分析・手動操作・インタラクティブ表示

### **backtest/ との連携**
- バックテスト結果の自動可視化
- メトリクス分析の視覚的表示
- 最適化結果の比較表示

### **ml/ との連携**
- 特徴量重要度の可視化
- 予測結果の時系列表示
- モデル性能の比較分析

---

**Phase 16.5-E整理効果**:  
monitor.py（631行）の適切配置により、可視化機能が論理的に集約され、今後の機能拡張・保守性向上の基盤が確立されました。monitoring/フォルダとの明確な差別化により、役割分担が明確化されています。