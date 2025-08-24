# config/environments/paper/ - ペーパートレード設定

**目的**: 完全にリスクフリーなペーパートレード環境での開発・テスト

## 📁 ファイル構成

```
paper/
├── README.md               # このファイル
└── local.yaml             # ローカル開発設定
```

## 🎯 ペーパートレードの特徴

### 完全安全な開発環境
- **実取引リスクゼロ**: 実際の資金を使わない仮想取引
- **高頻度ログ**: DEBUG レベル・詳細監視
- **最小リスク設定**: 0.1%ポジション・極めて保守的
- **高速テスト**: 30秒取引間隔・短期キャッシュ

### 使用場面
- 新機能開発・デバッグ
- アルゴリズム調整・パラメータテスト
- コード変更後の動作確認
- CI/CDパイプラインでの自動テスト

## 🔧 local.yaml - ローカル開発設定

**基本設定**:
```yaml
system:
  mode: "paper"              # ペーパートレードモード
  debug: true                # デバッグ有効
  log_level: "DEBUG"         # 詳細ログ

risk:
  risk_per_trade: 0.001      # 0.1%（極小）
  max_drawdown: 0.05         # 5%
  consecutive_loss_limit: 2  # 連続2損失で停止

development:
  trade_interval: 30         # 30秒間隔
  daily_trade_limit: 100     # 高頻度テスト
  discord_enabled: false     # 通知無効
```

## 🚀 使用方法

### ローカル開発
```bash
# ペーパートレードで開発環境テスト
python main.py --config config/environments/paper/local.yaml

# 設定確認
python3 -c "
from src.core.config import Config
config = Config.load_from_file('config/environments/paper/local.yaml')
print(f'モード: {config.system.mode}')
print(f'リスク: {config.risk.risk_per_trade*100}%')
"
```

### CI/CDでの自動テスト
```bash
# GitHub Actions CI/CDでのペーパーテスト
python main.py --mode paper --config config/environments/paper/local.yaml
```

## 🔒 安全機能

1. **完全ペーパートレード**: 実取引リスクゼロ
2. **Discord通知無効**: 開発中の無駄な通知防止
3. **極小ポジション**: 仮想取引でも最小リスク
4. **高頻度ログ**: 問題の早期発見

## 📊 開発効率向上

- **高速反復**: 実取引制約なしで高速テスト
- **詳細監視**: DEBUG ログで詳細な動作確認
- **リスクフリー**: 安心してアルゴリズム実験可能

---

**重要**: ペーパートレード環境は開発・テスト専用です。実取引への移行前に必ず `config/environments/live/` の設定を使用してください。