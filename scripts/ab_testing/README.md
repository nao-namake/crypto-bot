# A/B Testing Scripts

Phase 12-2 シンプルA/Bテスト基盤（実用性重視版）

## 📂 スクリプト一覧

### **🧪 simple_ab_test.py**

**シンプルA/Bテスト・統計分析システム（個人開発最適化版）**

新旧モデル・戦略の並行実行・パフォーマンス比較を簡潔に実現。複雑なレガシーシステムを簡素化し、実用的な判定基準と統計分析で個人開発に最適化したA/Bテスト基盤。

#### 主要機能

**A/Bテスト実行**:
- **2つのバリアント比較**: 現行システム vs 新システム・モデル・戦略
- **Cloud Runログベース**: gcloudコマンド・JSON解析・自動データ収集
- **統計分析**: t検定・p値・信頼区間・有意性検証

**データ収集・解析**:
- **バリアント別メトリクス**: シグナル数・頻度・信頼度・応答時間
- **シグナル分類**: BUY/SELL/HOLDシグナル分布・パターン分析
- **システム指標**: エラー率・稼働率・応答性能・品質指標

**実用的判定**:
- **統計的有意性**: p値 < 0.05・信頼度95%・t検定
- **実用的有意性**: 10%以上の改善・ビジネス価値判定
- **総合推奨**: 両方の観点から採用/継続/追加テスト推奨

#### データ構造

**ABTestMetrics**:
```python
@dataclass
class ABTestMetrics:
    name: str
    start_time: str
    end_time: str
    duration_hours: float
    
    # パフォーマンス指標
    total_signals: int = 0
    signal_frequency: float = 0.0  # per hour
    avg_confidence: float = 0.0
    high_confidence_count: int = 0  # confidence > 0.7
    
    # シグナル分布
    buy_signals: int = 0
    sell_signals: int = 0
    hold_signals: int = 0
    
    # システム指標
    error_count: int = 0
    response_time_avg: float = 0.0
    uptime_percentage: float = 0.0
```

**ABTestResult**:
```python
@dataclass
class ABTestResult:
    test_name: str
    variant_a: ABTestMetrics
    variant_b: ABTestMetrics
    
    # 統計分析
    statistical_analysis: Dict
    confidence_level: float
    
    # 実用的判定
    practical_significance: bool
    improvement_percentage: float
    winner: str  # 'A', 'B', or 'No significant difference'
    recommendation: str
```

#### 使用方法

```bash
# 基本A/Bテスト実行（24時間）
python scripts/ab_testing/simple_ab_test.py

# テスト名・期間指定
python scripts/ab_testing/simple_ab_test.py \
  --test-name "new_ml_model_test" \
  --hours 48

# バリアント指定（Cloud Runサービス）
python scripts/ab_testing/simple_ab_test.py \
  --variant-a ""              # crypto-bot-service（現行）
  --variant-b "-stage10"      # crypto-bot-service-stage10（新版）
  --hours 24

# 長期テスト（1週間）
python scripts/ab_testing/simple_ab_test.py \
  --test-name "strategy_comparison_week" \
  --hours 168 \
  --variant-a "-prod" \
  --variant-b "-experimental"

# プロジェクト・サービス指定
python scripts/ab_testing/simple_ab_test.py \
  --project my-crypto-bot-project \
  --service crypto-bot-service \
  --output logs/ab_testing_results
```

#### 統計分析手法

**t検定実装**:
```python
# シグナル頻度比較（主要指標）
freq_a = variant_a.signal_frequency
freq_b = variant_b.signal_frequency

# 簡易t検定（等分散仮定）
pooled_std = np.sqrt((freq_a**2 + freq_b**2) / 2)
t_stat = (freq_a - freq_b) / pooled_std
df = variant_a.total_signals + variant_b.total_signals - 2
p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
```

**判定基準**:
```yaml
統計的有意性: p値 < 0.05
実用的有意性: 改善率 >= 10%
最小サンプル: 各バリアント >= 10シグナル
信頼度: 95%
```

#### 出力形式・レポート

**JSON結果**:
```json
{
  "test_name": "new_ml_model_test",
  "variant_a": {
    "name": "A",
    "total_signals": 45,
    "signal_frequency": 1.875,
    "avg_confidence": 0.72
  },
  "variant_b": {
    "name": "B", 
    "total_signals": 52,
    "signal_frequency": 2.167,
    "avg_confidence": 0.78
  },
  "statistical_analysis": {
    "test_type": "t_test_signal_frequency",
    "p_value": 0.034,
    "significant": true,
    "confidence_level": 95
  },
  "improvement_percentage": 15.6,
  "practical_significance": true,
  "winner": "B",
  "recommendation": "バリアントBを採用推奨（シグナル頻度15.6%向上）"
}
```

**テキストレポート**:
```
============================================================
Phase 12-2 A/Bテスト結果: new_ml_model_test
============================================================
実行日時: 2025-08-18 12:00:00
テスト期間: 24時間

📊 バリアント比較:
  バリアントA: 45シグナル (1.88/時間)
  バリアントB: 52シグナル (2.17/時間)
  改善率: +15.6%

🎯 信頼度分析:
  バリアントA平均: 0.720
  バリアントB平均: 0.780
  高信頼シグナル A: 28件
  高信頼シグナル B: 35件

📈 統計分析:
  検定タイプ: t_test_signal_frequency
  p値: 0.0340
  統計的有意: Yes
  実用的有意: Yes

🏆 結果・推奨事項:
  勝者: B
  信頼度: 95%
  推奨: バリアントBを採用推奨（シグナル頻度15.6%向上）
============================================================
```

#### A/Bテスト戦略

**段階的テスト**:
```bash
# Phase 1: 短期テスト（6時間）- 基本動作確認
python scripts/ab_testing/simple_ab_test.py --hours 6 --test-name "quick_validation"

# Phase 2: 中期テスト（24時間）- 統計的有意性確認  
python scripts/ab_testing/simple_ab_test.py --hours 24 --test-name "statistical_test"

# Phase 3: 長期テスト（168時間）- 安定性・実用性確認
python scripts/ab_testing/simple_ab_test.py --hours 168 --test-name "stability_test"
```

**バリアント設計**:
```yaml
現行システム (A): ""                    # crypto-bot-service
実験システム (B): "-stage10"            # crypto-bot-service-stage10

段階的展開:
  Stage 1: Paper Trading（リスクなし）
  Stage 2: 10%トラフィック（限定リスク）
  Stage 3: 50%トラフィック（本格検証）
  Stage 4: 100%移行（全面採用）
```

## 🎯 Phase 12-2統合活用

### **データ収集連携**

```bash
# 実データ収集→A/Bテスト→ダッシュボード の統合フロー

# 1. ベースラインデータ収集
python scripts/data_collection/trading_data_collector.py --hours 24

# 2. A/Bテスト実行
python scripts/ab_testing/simple_ab_test.py --hours 24 --test-name "baseline_vs_improved"

# 3. ダッシュボード生成（A/Bテスト結果含む）
python scripts/dashboard/trading_dashboard.py --ab-testing
```

### **継続的テスト**

**週次A/Bテスト**:
```bash
# 毎週日曜日に1週間のA/Bテスト結果分析
0 6 * * 0 cd /path/to/bot && python scripts/ab_testing/simple_ab_test.py --hours 168 --test-name "weekly_performance"
```

**月次比較**:
```bash
# 月次での長期トレンド分析
python scripts/ab_testing/simple_ab_test.py --hours 720 --test-name "monthly_analysis"  # 30日
```

### **アラート統合**

```bash
# A/Bテスト結果をチェックして、大きな改善があればアラート
python scripts/ab_testing/simple_ab_test.py --hours 24 | \
  jq '.improvement_percentage' | \
  awk '$1 > 20 { system("echo \"大幅改善検出: " $1 "%\" | /path/to/discord_notify.sh") }'
```

## 🔧 カスタマイズ・拡張

### **判定基準調整**

```python
# simple_ab_test.py内で調整可能
PRACTICAL_SIGNIFICANCE_THRESHOLD = 10.0  # 実用的有意性閾値（%）
STATISTICAL_ALPHA = 0.05                 # 統計的有意性閾値
MIN_SAMPLE_SIZE = 10                     # 最小サンプルサイズ
CONFIDENCE_THRESHOLD = 0.7               # 高信頼度シグナル閾値
```

### **分析指標追加**

```python
# カスタム指標追加
@dataclass
class ABTestMetrics:
    # 既存指標...
    profit_rate: float = 0.0           # 収益率
    risk_adjusted_return: float = 0.0  # リスク調整リターン
    max_drawdown: float = 0.0          # 最大ドローダウン
    sharpe_ratio: float = 0.0          # シャープレシオ
```

### **テスト期間最適化**

```python
# 動的テスト期間決定
def calculate_required_sample_size(effect_size=0.1, power=0.8, alpha=0.05):
    # 統計学的サンプルサイズ計算
    # Cohen's d、検出力分析
    pass
```

## 📊 ベストプラクティス

### **テスト設計**

**1. 仮説設定**:
```yaml
仮説: 新MLモデルによりシグナル精度が向上する
主要指標: signal_frequency, avg_confidence  
副次指標: error_rate, response_time
効果サイズ: 10%以上の改善
```

**2. テスト期間**:
```yaml
最小期間: 24時間（基本動作確認）
標準期間: 168時間（統計的有意性）
最大期間: 720時間（長期安定性）
```

**3. サンプルサイズ**:
```yaml
最小サンプル: 各バリアント10シグナル
推奨サンプル: 各バリアント100シグナル
理想サンプル: 各バリアント1000シグナル
```

### **結果解釈**

**統計的有意 + 実用的有意**:
→ 明確な改善・採用推奨

**統計的有意のみ**:
→ 効果は確実だが小さい・追加検証推奨

**実用的有意のみ**:
→ 効果は大きいが不確実・長期テスト推奨

**どちらも非有意**:
→ 有意差なし・現行システム維持

### **運用上の注意**

**1. テスト環境の分離**:
- Paper Trading環境でのリスクフリーテスト
- Stage環境での限定的実験
- Production環境での慎重な展開

**2. 外部要因の考慮**:
- 市場状況の変化
- システム負荷の違い
- 時間帯・曜日効果

**3. 長期的な追跡**:
- A/Bテスト完了後の継続監視
- 長期パフォーマンス追跡
- 予期しない副作用の検出

## 🔮 Future Enhancements

### **高度な統計分析**
- **ベイジアンA/Bテスト**: 逐次解析・早期停止・動的サンプルサイズ
- **多変量解析**: 複数指標同時最適化・相関分析・因果推論
- **時系列分析**: トレンド除去・季節性調整・自己相関対応

### **自動化拡張**
- **自動テスト実行**: 定期的A/Bテスト・条件付きトリガー・CI/CD統合
- **自動判定・展開**: 閾値ベース自動採用・段階的ロールアウト・自動ロールバック
- **アダプティブテスト**: 逐次最適化・多腕バンディット・強化学習

### **高度な可視化**
- **リアルタイムダッシュボード**: ライブ更新・統計的検出力・予測完了時間
- **詳細分析**: セグメント別分析・コホート分析・ファネル分析
- **レポート自動化**: 週次レポート・月次総括・年次振り返り

---

**Phase 12-2実装完了**: レガシーシステムの複雑さを排除し、実用性と統計的厳密性のバランスを取った個人開発最適化A/Bテスト基盤を確立