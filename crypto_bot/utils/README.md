# utils/ - ユーティリティ・共通機能

## 📋 概要

**Utility Functions & Common Features**  
本フォルダは crypto-bot 全体で使用される共通ユーティリティ機能を提供し、エラー処理、ログ管理、設定検証、データ処理などの横断的機能を担当します。

## 🎯 主要機能

### **エラー処理・耐性**
- エラーリトライ機能
- サーキットブレーカー実装
- 包括的エラーハンドリング
- 自動リカバリ機能

### **ログ・状態管理**
- 統一ログシステム
- ステータス管理
- 進捗追跡
- デバッグ支援

### **設定・検証**
- 設定ファイル検証
- 環境変数管理
- パラメータ検証
- 型チェック

### **データ処理・最適化**
- データ変換ユーティリティ
- キャッシュ管理
- HTTPクライアント最適化
- 統計計算

## 📁 ファイル構成

```
utils/
├── __init__.py                      # パッケージ初期化
├── config.py                        # Phase 16.5-C: CLI重要依存設定管理
├── init_enhanced.py                 # Phase 16.5-D: 拡張INITシーケンス管理
├── error_resilience.py             # エラー耐性システム
├── api_retry.py                    # APIリトライ機能
├── logger.py                       # ログ管理
├── logging.py                      # ログ設定
├── status.py                       # ステータス管理
├── enhanced_status_manager.py      # 拡張ステータス管理
├── config_validator.py             # 設定検証
├── config_state.py                 # 設定状態管理
├── data.py                         # データ処理ユーティリティ
├── file.py                         # ファイル操作
├── model.py                        # モデル関連ユーティリティ
├── chart.py                        # チャート生成
├── pre_computed_cache.py           # 事前計算キャッシュ
├── ensemble_confidence.py          # アンサンブル信頼度計算
├── http_client_optimizer.py        # HTTPクライアント最適化
├── japanese_market.py              # 日本市場特有処理
├── cloud_run_api_diagnostics.py    # Cloud Run診断
├── trading_integration_service.py  # 取引統合サービス
├── trading_statistics_manager.py   # 取引統計管理
└── system/                         # システム管理サブモジュール
    ├── __init__.py
    ├── logging_system.py           # システムログ管理
    └── status_manager.py            # システムステータス管理
```

## 🔍 各ファイルの役割

### **error_resilience.py**
- `ErrorResilienceManager`クラス - エラー耐性管理
- `CircuitBreaker`実装 - 連続エラー時の自動遮断
- エラー記録・分析
- 自動リカバリ戦略
- Phase H.8.3実装

### **api_retry.py**
- `retry_with_backoff`デコレータ - 指数バックオフ
- API呼び出しリトライ
- カスタムリトライ戦略
- エラー種別判定

### **logger.py / logging.py**
- 統一ログフォーマット
- ログレベル管理
- ファイル/コンソール出力
- 構造化ログ対応

### **config.py（Phase 16.5-C移動）**
- `load_config()`関数 - YAML設定ファイル読み込み
- `deep_merge()`関数 - 設定データ統合
- **7個CLIモジュール依存**: backtest/live/optimize/validate等
- 旧crypto_bot/config.pyから統合配置で移動

### **init_enhanced.py（Phase 16.5-D移動）**
- `enhanced_init_sequence()`関数 - 拡張初期化シーケンス
- `enhanced_init_5_fetch_price_data()`関数 - INIT-5ステージ処理
- **Phase 12.2包括修正**: 部分データ救済システム実装
- 旧crypto_bot/init_enhanced.pyから移動（866行）

### **config_validator.py**
- `ConfigValidator`クラス - 設定検証
- スキーマベース検証
- 必須項目チェック
- 値範囲検証

### **pre_computed_cache.py**
- `PreComputedCache`クラス - 事前計算結果キャッシュ
- メモリ効率的な保存
- TTL管理
- スレッドセーフ実装

### **trading_statistics_manager.py**
- `TradingStatisticsManager`クラス - 取引統計
- パフォーマンスメトリクス計算
- 期間別集計
- レポート生成

### **japanese_market.py**
- 日本市場営業時間判定
- 祝日カレンダー統合
- タイムゾーン処理
- 市場固有ルール

## 🚀 使用方法

### **エラー耐性実装**
```python
from crypto_bot.utils.error_resilience import get_resilience_manager, with_resilience

# デコレータ使用
@with_resilience(max_retries=3, backoff_factor=2)
def risky_api_call():
    return external_api.fetch_data()

# マネージャー直接使用
resilience_mgr = get_resilience_manager()
circuit_breaker = resilience_mgr.get_circuit_breaker("api_service")
if circuit_breaker.is_open():
    # サービス一時停止
    return cached_data
```

### **Phase 16.5-C,D移動機能使用例**
```python
# CLIモジュールでの設定読み込み（Phase 16.5-C）
from crypto_bot.utils.config import load_config, deep_merge

# 7個CLIモジュールで使用中：backtest/live/optimize/validate等
cfg = load_config(config_path)
merged_cfg = deep_merge(base_config, user_config)

# 拡張初期化処理（Phase 16.5-D）
from crypto_bot.utils.init_enhanced import enhanced_init_5_fetch_price_data

# INIT-5ステージでのデータ取得強化
result = enhanced_init_5_fetch_price_data(config, exchange)
```

### **設定検証**
```python
from crypto_bot.utils.config_validator import ConfigValidator

validator = ConfigValidator()
errors = validator.validate_config(config_dict)
if errors:
    for error in errors:
        logger.error(f"Config error: {error}")
```

### **取引統計管理**
```python
from crypto_bot.utils.trading_statistics_manager import TradingStatisticsManager

stats_mgr = TradingStatisticsManager()
stats_mgr.record_trade(trade_result)

# 統計取得
daily_stats = stats_mgr.get_daily_statistics()
print(f"本日の勝率: {daily_stats['win_rate']:.2%}")
```

## ⚠️ 課題・改善点

### **Phase 16.5-C,D整理効果**
- **重要依存機能集約**: config.py（7個CLI依存）とinit_enhanced.py集約
- **crypto_bot直下整理**: 機能別適切配置で構造最適化実現
- **import互換性100%**: 既存CLIコード影響ゼロで移動完了
- **system/サブフォルダ存在**: システムレベル機能の組織化進展

### **重複機能**
- status.pyとenhanced_status_manager.pyの統合
- キャッシュ関連機能の一元化
- エラー処理の標準化

### **ドキュメント不足**
- 各ユーティリティの使用例
- ベストプラクティスガイド
- 依存関係図

### **テスト不足**
- ユニットテストカバレッジ
- エッジケーステスト
- パフォーマンステスト

## 📝 今後の展開

1. **Phase 16.5整理完了後の構造最適化**
   ```
   utils/
   ├── config.py 🆕        # Phase 16.5-C: CLI重要依存
   ├── init_enhanced.py 🆕   # Phase 16.5-D: INIT強化系
   ├── error/             # エラー処理関連統合
   ├── logging/           # ログ関連統合
   ├── config/            # 設定関連統合（config.py連携）
   ├── data/              # データ処理統合
   ├── trading/           # 取引関連統合
   └── system/ ✓          # システム関連（既存）
   ```

2. **機能拡張**
   - プロファイリングツール
   - メモリ最適化ユーティリティ
   - 並列処理ヘルパー
   - イベント駆動システム

3. **標準化**
   - エラー処理パターン統一
   - ログフォーマット標準化
   - 設定スキーマ定義
   - 型定義強化

4. **パフォーマンス**
   - Cython実装
   - メモリプール
   - 遅延評価
   - キャッシュ最適化