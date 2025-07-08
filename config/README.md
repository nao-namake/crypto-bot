# 設定ファイル管理

## 📁 現在の設定ファイル構成

### 🏆 **主要運用設定**

#### `simple_2025_test.yml` **[推奨・最優秀実績]**
- **目的**: 実証済み最優秀パフォーマンス設定
- **実績**: 100%勝率、年7-8%収益（2025年H1）
- **特徴**: 8特徴量、threshold=0.052、安定性重視
- **用途**: **実運用推奨**、Bitbank本番移行ベース

#### `bitbank_production_optimized.yml` **[本番運用版]**
- **目的**: Bitbank本番取引専用設定
- **特徴**: Bitbank API対応、手数料考慮、保守的設定
- **用途**: 実資金投入時の基本設定

#### `optimized_final_65feat.yml` **[高度設定]**
- **目的**: 65特徴量システム完全活用版
- **特徴**: VIX+DXY+Funding Rate+高度テクニカル指標
- **用途**: 高性能追求時、研究開発用

### 🔧 **基本・開発設定**

#### `default.yml` **[基本設定]**
- **目的**: システム標準設定、開発ベース
- **用途**: 新機能テスト、基本動作確認

#### `bitbank_production.yml` **[シンプル本番設定]**
- **目的**: Bitbank基本本番設定
- **用途**: シンプルな本番運用、バックアップ設定

### 📊 **補助ファイル**

#### `api_versions.json`
- **目的**: API version管理
- **内容**: 各取引所APIバージョン情報

---

## 🎯 **用途別推奨設定**

### **実運用開始時**
```bash
# 最優秀実績設定でバックテスト確認
python -m crypto_bot.main backtest --config config/simple_2025_test.yml

# 本番移行準備
python -m crypto_bot.main backtest --config config/bitbank_production_optimized.yml
```

### **高性能追求時**
```bash
# 65特徴量システム活用
python -m crypto_bot.main backtest --config config/optimized_final_65feat.yml
```

### **開発・テスト時**
```bash
# 基本機能確認
python -m crypto_bot.main backtest --config config/default.yml
```

---

## 📈 **性能比較表**

| 設定ファイル | 勝率 | 年間収益率 | 特徴量数 | 用途 |
|-------------|------|------------|----------|------|
| `simple_2025_test.yml` | **100%** | **7-8%** | 8 | 実運用推奨 |
| `optimized_final_65feat.yml` | 79% | 15-30% | 65+ | 高性能追求 |
| `bitbank_production_optimized.yml` | - | 7-8% | 8-12 | 本番運用 |

---

## 🗂️ **設定ファイル履歴**

**2025年7月8日**: configディレクトリ大幅整理
- **削除**: 30+個の重複・テスト用設定ファイル
- **保持**: 6個の必要最小限設定のみ
- **目的**: メンテナンス性向上、混乱防止

**主要削除ファイル**:
- `pattern_*_65feat.yml` (5個) - 統合済み
- `bitbank_*_test.yml` (8個) - テスト完了
- `dxy_*.yml` (4個) - optimized_final_65feat.ymlに統合
- `aggressive_*.yml`, `enhanced_*.yml` 等 - 実績未確認設定群

---

## ⚠️ **注意事項**

1. **新設定追加前**: 既存設定での対応可能性を確認
2. **実運用時**: `simple_2025_test.yml`を第一選択
3. **テスト後**: 不要になったテスト設定は即座に削除
4. **命名規則**: `用途_特徴_バージョン.yml`形式を推奨