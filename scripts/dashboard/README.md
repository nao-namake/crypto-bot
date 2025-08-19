# Dashboard Scripts

Phase 12-2 取引成果ダッシュボード（可視化・レポート生成）

## 📂 スクリプト一覧

### **📊 trading_dashboard.py**

**取引成果・パフォーマンス可視化ダッシュボード（統合レポート生成版）**

リアルタイム取引統計・パフォーマンス指標・HTMLレポート生成システム。実データ収集・A/Bテスト結果の可視化とDiscord通知統合により、Phase 12-2データ収集基盤の最終的な成果物として包括的なダッシュボードを提供。

#### 主要機能

**データ統合・可視化**:
- **実データ収集結果**: CSV・JSON形式データの自動読み込み・解析
- **A/Bテスト結果**: テスト結果JSON・統計分析・改善効果可視化
- **HTMLダッシュボード**: Chart.js・レスポンシブデザイン・インタラクティブ表示

**統計分析・レポート**:
- **取引サマリー**: 総シグナル数・頻度・信頼度・高信頼シグナル分析
- **日次推移**: 時系列チャート・トレンド分析・パフォーマンス追跡
- **シグナル分布**: BUY/SELL/HOLD分布・戦略別分析・パターン認識

**通知・レポート自動化**:
- **Discord通知**: Markdown形式・統計サマリー・重要指標抽出
- **HTMLレポート**: 完全な可視化・詳細分析・ブラウザ表示対応
- **自動生成**: タイムスタンプ付きファイル・履歴管理・定期実行対応

#### データソース統合

**実データ収集連携**:
```python
# データ収集結果の自動読み込み
data_collection_dir = logs/data_collection/
├── trades_YYYYMMDD.csv          # 取引レコード
├── daily_stats_YYYYMMDD.csv     # 日次統計  
└── performance_metrics_YYYYMMDD.json  # パフォーマンス指標
```

**A/Bテスト結果連携**:
```python
# A/Bテスト結果の自動統合
ab_testing_dir = logs/ab_testing/
└── ab_test_*.json               # A/Bテスト結果
```

**出力ファイル**:
```python
# ダッシュボード生成結果
dashboard_dir = dashboard/
└── trading_dashboard_YYYYMMDD_HHMMSS.html  # HTMLダッシュボード
```

#### 使用方法

```bash
# 基本実行（自動データ読み込み・HTML生成）
python scripts/dashboard/trading_dashboard.py

# データディレクトリ指定
python scripts/dashboard/trading_dashboard.py \
  --data-dir logs \
  --output-dir dashboard_reports

# Discord通知メッセージ表示
python scripts/dashboard/trading_dashboard.py --discord

# カスタムディレクトリ指定
python scripts/dashboard/trading_dashboard.py \
  --data-dir /path/to/logs \
  --output-dir /path/to/dashboard \
  --discord
```

#### 統合ワークフロー

**Phase 12-2完全フロー**:
```bash
# 1. 実データ収集（24時間）
python scripts/data_collection/trading_data_collector.py --hours 24

# 2. A/Bテスト実行
python scripts/ab_testing/simple_ab_test.py --hours 24 --test-name "daily_performance"

# 3. ダッシュボード生成・通知
python scripts/dashboard/trading_dashboard.py --discord

# 期待結果:
# ✅ HTMLダッシュボード生成
# 📢 Discord通知メッセージ準備
# 📊 包括的な可視化レポート
```

**定期実行設定**:
```bash
# 毎日朝6時にダッシュボード更新・通知
0 6 * * * cd /path/to/bot && python scripts/dashboard/trading_dashboard.py --discord > /dev/null
```

#### ダッシュボード構成

**ヘッダー・概要**:
- **最終更新時刻**: リアルタイム情報・データ鮮度確認
- **データ期間**: 分析対象期間・収集範囲表示
- **Phase 12-2ブランディング**: システム識別・バージョン表示

**統計サマリー（カード形式）**:
```html
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   総シグナル数   │  シグナル頻度   │   平均信頼度    │ 高信頼シグナル  │
│      48         │    2.0/h       │     0.742      │      28        │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

**シグナル種別分布**:
```html
┌─────────────────┬─────────────────┬─────────────────┐
│   BUY シグナル   │  SELL シグナル  │  HOLD シグナル  │
│       18        │       15       │       15       │
│   ████████      │   ██████       │   ██████       │
└─────────────────┴─────────────────┴─────────────────┘
```

**日次推移チャート（Chart.js）**:
- **線グラフ**: 日次シグナル数推移・トレンド表示
- **インタラクティブ**: ホバー詳細・ズーム・期間選択
- **レスポンシブ**: モバイル対応・自動調整

**A/Bテスト結果セクション**:
```html
🧪 A/Bテスト結果
├── テスト1: new_ml_model_test
│   ├── 勝者: B ✅
│   ├── 改善率: +15.6%
│   ├── 信頼度: 95%
│   └── 推奨: バリアントBを採用推奨
└── テスト2: strategy_comparison
    ├── 勝者: No significant difference
    ├── 改善率: +2.1%
    └── 推奨: 現行システム維持推奨
```

#### Discord通知メッセージ

**コンパクト形式**:
```markdown
🚀 **Phase 12-2 取引成果レポート**

📊 **基本統計**
• 総シグナル数: 48
• シグナル頻度: 2.0/時間
• 平均信頼度: 0.742
• 高信頼シグナル: 28件

📈 **シグナル分布**
• BUY: 18 • SELL: 15 • HOLD: 15

ℹ️ **データ期間**: 24時間 | **分析日数**: 1日

🎯 **Phase 12-2**: 実データ収集・A/Bテスト・ダッシュボード稼働中
```

#### HTMLダッシュボード特徴

**モダンデザイン**:
- **グラデーション**: 美しいヘッダー・視覚的階層
- **カードレイアウト**: 情報整理・読みやすさ重視
- **カラーコーディング**: BUY(緑)・SELL(赤)・HOLD(黄)

**技術仕様**:
```html
<!-- Chart.js統合 -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- レスポンシブデザイン -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<!-- モダンCSS -->
body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

**パフォーマンス最適化**:
- **CDN活用**: Chart.js外部読み込み・高速表示
- **軽量HTML**: 最小限JavaScript・高速レンダリング
- **キャッシュ対応**: ブラウザキャッシュ・再表示高速化

## 🎯 Phase 12-2統合価値

### **データドリブン意思決定**

**包括的可視化**:
- **リアルタイム状況**: 最新パフォーマンス・現在の取引状況
- **歴史的トレンド**: 長期推移・改善効果・季節性分析
- **比較分析**: A/Bテスト結果・戦略効果・システム改善

**意思決定支援**:
- **定量的判断**: 統計データ・信頼区間・有意性検証
- **視覚的理解**: グラフ・チャート・カラーコーディング
- **アクション推奨**: 具体的改善案・優先順位・実装指針

### **運用効率化**

**自動化ワークフロー**:
```bash
# 毎日の運用サイクル
データ収集 → A/Bテスト → ダッシュボード → 意思決定 → 改善実装
```

**時間短縮効果**:
- **手動分析削減**: 数時間→数分・自動生成・即座確認
- **レポート作成**: 自動HTML・Discord通知・定期配信
- **意思決定迅速化**: 視覚化情報・統計的根拠・明確な推奨

### **品質保証**

**データ品質管理**:
- **欠損データ対応**: 空データチェック・エラーハンドリング・フォールバック
- **整合性確認**: CSV/JSON対応・型安全・検証ロジック
- **異常値検知**: 統計的外れ値・パフォーマンス劣化・システム異常

**信頼性確保**:
- **エラー対応**: 例外処理・ログ出力・復旧手順
- **フォールバック**: データ不足時の代替表示・最小限機能
- **検証機能**: 出力ファイル確認・データ整合性・レポート品質

## 🔧 カスタマイズ・拡張

### **表示項目追加**

```python
# TradingDashboard.generate_trading_summary()で拡張
summary = {
    # 既存項目...
    "profit_metrics": {
        "total_profit": 0.0,
        "average_profit_per_signal": 0.0,
        "profit_rate": 0.0
    },
    "risk_metrics": {
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "volatility": 0.0
    }
}
```

### **チャート追加**

```javascript
// HTMLテンプレート内で追加チャート
// 信頼度分布ヒストグラム
const confidenceChart = new Chart(ctx2, {
    type: 'bar',
    data: {
        labels: ['0.0-0.3', '0.3-0.5', '0.5-0.7', '0.7-1.0'],
        datasets: [{
            label: '信頼度分布',
            data: confidence_histogram
        }]
    }
});

// 戦略別パフォーマンス
const strategyChart = new Chart(ctx3, {
    type: 'doughnut',
    data: {
        labels: ['ATR Strategy', 'ML Strategy', 'Ensemble'],
        datasets: [{
            data: strategy_performance
        }]
    }
});
```

### **通知カスタマイズ**

```python
# Discord通知内容拡張
def generate_discord_notification_detailed(self, summary: Dict) -> str:
    message = f"""
🚀 **Phase 12-2 詳細レポート**

📊 **パフォーマンス指標**
• 成功率: {summary.get('success_rate', 0):.1f}%
• 平均利益: {summary.get('avg_profit', 0):.2f}円
• リスク調整リターン: {summary.get('risk_adjusted_return', 0):.3f}

⚠️ **アラート**
{self._generate_alerts(summary)}

📈 **改善提案**
{self._generate_recommendations(summary)}
"""
    return message.strip()
```

## 📊 活用シナリオ

### **日次運用**

```bash
# 朝の状況確認（過去24時間）
python scripts/dashboard/trading_dashboard.py
# → ブラウザでHTMLダッシュボード確認

# 異常時の詳細確認
python scripts/dashboard/trading_dashboard.py --discord
# → Discord通知内容確認・問題特定
```

### **週次レビュー**

```bash
# 1週間分のデータ収集→A/Bテスト→ダッシュボード
python scripts/data_collection/trading_data_collector.py --hours 168
python scripts/ab_testing/simple_ab_test.py --hours 168
python scripts/dashboard/trading_dashboard.py
```

### **月次分析**

```bash
# 月次総合レポート生成
python scripts/dashboard/trading_dashboard.py \
  --data-dir logs/monthly_data \
  --output-dir reports/monthly \
  --discord
```

### **A/Bテスト判定**

```bash
# A/Bテスト結果の可視化→意思決定
python scripts/ab_testing/simple_ab_test.py --hours 48 --test-name "strategy_test"
python scripts/dashboard/trading_dashboard.py  # A/Bテスト結果を自動統合表示
```

## 🚨 トラブルシューティング

### **データ読み込みエラー**

```bash
# データファイル確認
ls -la logs/data_collection/
ls -la logs/ab_testing/

# 手動データチェック
python -c "
import pandas as pd
df = pd.read_csv('logs/data_collection/trades_20250818.csv')
print(df.head())
print(f'データ件数: {len(df)}')
"
```

### **HTML表示問題**

```bash
# HTMLファイル確認
ls -la dashboard/
# ブラウザで直接開く
open dashboard/trading_dashboard_*.html

# Chart.js読み込み確認（ネットワーク接続必要）
curl -I https://cdn.jsdelivr.net/npm/chart.js
```

### **Discord通知設定**

```python
# Discord Webhook URL設定（将来拡張）
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."

# 通知テスト
python -c "
from scripts.dashboard.trading_dashboard import TradingDashboard
dashboard = TradingDashboard()
summary = {'total_signals': 10, 'signal_frequency_per_hour': 0.5}
print(dashboard.generate_discord_notification(summary))
"
```

## 🔮 Future Enhancements

### **リアルタイム対応**
- **WebSocket統合**: ライブデータ更新・リアルタイム表示
- **自動リフレッシュ**: 定期更新・ブラウザ自動更新・プッシュ通知
- **ストリーミングダッシュボード**: 継続的データフロー・即座反映

### **高度な可視化**
- **3D チャート**: パフォーマンス立体表示・多次元分析・インタラクティブ操作
- **アニメーション**: 時系列アニメーション・トレンド動画・変化強調
- **ドリルダウン**: 詳細分析・階層的表示・クリック展開

### **AI統合**
- **異常検知**: 機械学習・パターン認識・自動アラート
- **予測分析**: トレンド予測・パフォーマンス予想・リスク評価
- **自動コメント**: AI生成レポート・洞察提供・改善提案

### **統合プラットフォーム**
- **Grafana連携**: 本格的ダッシュボード・メトリクス統合・アラート管理
- **Slack/Teams統合**: チーム通知・レポート配信・コラボレーション
- **モバイルアプリ**: スマートフォン対応・プッシュ通知・外出先確認

---

**Phase 12-2実装完了**: 実データ収集・A/Bテスト・可視化を統合した包括的なダッシュボードシステムにより、データドリブンな取引システム運用を実現