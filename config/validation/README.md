# config/validation/ - 検証環境設定ディレクトリ

**Phase 12完了**: 本番移行前最終検証・CI/CDワークフロー最適化・自動品質保証・段階的デプロイ準備完了

## 📁 ファイル構成

```
validation/
├── README.md                    # このファイル
└── phase9_validation.yaml       # 本番移行前検証設定
```

## 🎯 検証環境の位置づけ

**実資金**: Bitbank口座の1万円を使用した最終検証

```
Development (ペーパー) → Validation (1万円実資金) → Staging → Production
        ↓                     ↓                    ↓         ↓
   CI/CD品質保証        Phase 12統合確認       段階的拡大   本番運用
```

**Phase 12検証目的**:
- 1万円の実資金での動作確認
- CI/CDワークフロー最適化統合確認
- 450テスト品質保証システム動作確認
- dev_check統合管理システム確認
- 本番移行前の最終性能検証
- リスク管理システムの実証
- API・注文実行の実環境確認

## 🔧 phase9_validation.yaml - 検証設定詳細

**資金前提**: Bitbank口座残高 10,000円

### 安全性重視の設定
```yaml
# リスク管理（1万円対応・極めて保守的）
risk:
  risk_per_trade: 0.005         # 0.5%（50円リスク）
  kelly_max_fraction: 0.01      # 1%（100円上限）
  max_drawdown: 0.10           # 10%（1,000円損失上限）
  consecutive_loss_limit: 3    # 連続3損失で停止

# 注文実行（最小単位）
validation:
  min_order_size: 0.0001       # 最小取引単位（約1,000円）
  max_order_size: 0.0003       # 最大0.0003 BTC（約3,000円）
  daily_trade_limit: 20        # 1日最大20回
  max_daily_loss: 0.02         # 1日最大2%（200円）損失
  emergency_stop_loss: 0.05    # 緊急停止5%（500円）
```

### 1万円運用の現実的目標
```yaml
targets:
  # 検証成功条件（1万円ベース）
  min_total_trades: 30         # 最低30取引
  min_win_rate: 0.55          # 勝率55%
  max_drawdown: 0.08          # ドローダウン8%以内（800円）
  min_profit_jpy: 500         # 最低500円利益（5%収益）
  
  evaluation_period_days: 7    # 7日間検証
  min_trades_for_evaluation: 30 # 最低30取引必要
```

## 💰 1万円運用の収益試算

### 現実的な収益予想
- **1取引平均利益**: 50-100円
- **1日取引回数**: 3-5回
- **日次利益目標**: 150-500円
- **週間利益目標**: 1,000-3,500円
- **検証期間利益**: 500-2,000円（5-20%）

### リスク管理
- **最大損失**: 1取引50円・1日200円・緊急時500円
- **資産保護**: 8,000円は常に保護（80%保全）
- **取引停止**: 連続3損失または500円損失で自動停止

## 🚀 検証実行手順

### Phase 9-2: 1万円実資金テスト

```bash
# 1. 残高確認
echo "Bitbank残高確認: 10,000円"

# 2. 検証設定確認
python3 -c "
from src.core.config import Config
config = Config.load_from_file('config/validation/phase9_validation.yaml')
assert config.validate()
print('✅ 検証設定OK')
print(f'リスク/取引: {config.risk.risk_per_trade*100}%')
print(f'最大注文: {config.validation.max_order_size} BTC')
"

# 3. 実取引テスト開始
python scripts/test_live_trading.py --mode single --config config/validation/phase9_validation.yaml

# 4. 連続取引テスト（4時間）
python scripts/test_live_trading.py --mode continuous --duration 4 --config config/validation/phase9_validation.yaml
```

### 7日間検証プロセス

**Day 1-2: 慎重開始**
```bash
# 単発テスト（1日2-3回）
python scripts/test_live_trading.py --mode single --config config/validation/phase9_validation.yaml

# 結果確認
echo "取引結果確認:"
echo "  取引回数: X回"
echo "  勝率: XX%"
echo "  収益: ¥XXX"
echo "  残高: ¥X,XXX"
```

**Day 3-5: 通常運用**
```bash
# 連続取引（1日4-6回）
python scripts/test_live_trading.py --mode continuous --duration 8 --config config/validation/phase9_validation.yaml
```

**Day 6-7: 最終評価**
```bash
# 手動実行監視テスト
python scripts/test_live_trading.py --mode monitoring --config config/validation/phase9_validation.yaml
```

## 📊 1万円検証の評価基準

### 成功条件（7日間）
- ✅ **安全性**: 最大ドローダウン800円以内
- ✅ **収益性**: 最低500円利益（5%以上）
- ✅ **安定性**: 勝率55%以上達成
- ✅ **信頼性**: 重大エラー・システム停止なし
- ✅ **効率性**: 30取引以上実行

### 1万円運用の現実的シナリオ

**保守的シナリオ（成功率80%）**:
- 7日間取引: 25回
- 勝率: 56%
- 平均利益: 30円/取引
- 総利益: 750円
- 最終残高: 10,750円

**標準シナリオ（成功率60%）**:
- 7日間取引: 35回
- 勝率: 60%
- 平均利益: 50円/取引
- 総利益: 1,750円
- 最終残高: 11,750円

**積極的シナリオ（成功率40%）**:
- 7日間取引: 45回
- 勝率: 65%
- 平均利益: 70円/取引
- 総利益: 3,150円
- 最終残高: 13,150円

## 🔍 監視・分析

### リアルタイム監視
```bash
# 残高・ポジション確認
curl "https://api.bitbank.cc/v1/user/assets" -H "ACCESS-KEY: ${BITBANK_API_KEY}"

# 取引履歴確認
python3 -c "
from src.data.bitbank_client import BitbankClient
client = BitbankClient()
trades = client.fetch_my_trades('BTC/JPY', limit=10)
for trade in trades:
    print(f'{trade[\"datetime\"]}: {trade[\"side\"]} {trade[\"amount\"]} BTC @ ¥{trade[\"price\"]:,.0f}')
"
```

### 日次レポート
```bash
# 検証進捗確認
echo "=== 1万円検証 Day X レポート ==="
echo "開始残高: ¥10,000"
echo "現在残高: ¥XX,XXX"
echo "収益: ¥XXX (XX.X%)"
echo "取引回数: XX回"
echo "勝率: XX.X%"
echo "最大ドローダウン: ¥XXX (X.X%)"
echo "今日の取引: X回"
echo "今日の収益: ¥XXX"
```

## 🚨 1万円運用のリスク管理

### 自動停止条件
1. **累積損失**: 500円（5%）で緊急停止
2. **日次損失**: 200円（2%）で当日取引停止
3. **連続損失**: 3回連続で18時間停止
4. **システムエラー**: 連続3エラーで停止

### 手動監視ポイント
- **残高確認**: 取引前後の残高変動
- **スプレッド監視**: 0.3%超のスプレッドで取引見送り
- **レイテンシー確認**: 2秒超で異常判定
- **API制限**: 30秒間隔遵守

## 📈 段階移行の判定

### 次段階移行条件
```bash
# 検証成功確認
if [ 勝率 >= 55% ] && [ 利益 >= 500円 ] && [ ドローダウン <= 800円 ]; then
    echo "✅ 検証成功 - staging 10%段階に移行可能"
else
    echo "❌ 検証継続 - 条件未達成"
fi
```

### 1万円→段階的拡大
- **検証成功**: 10%段階（staging）へ移行
- **10%成功**: 実資金増額・50%段階
- **50%成功**: フル本番運用

## 💡 1万円運用のコツ

### 効率的な取引
- **最小スプレッド時**: 早朝・深夜の流動性高い時間帯
- **指値注文優先**: maker手数料-0.02%活用
- **小額積み重ね**: 1取引50-100円の確実な利益

### リスク最小化
- **1回0.5%ルール**: 1取引最大50円リスク
- **感情排除**: 自動停止条件の厳守
- **記録重視**: 全取引の詳細記録・分析

---

**重要**: 1万円という限られた資金での検証は、リスク管理能力とシステムの信頼性を証明する重要なステップです。安全性を最優先に進めてください。