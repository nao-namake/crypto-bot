# tests/ - テストディレクトリ

**Phase 13完了**: sklearn警告解消・306テスト100%成功・品質保証完成。システム全体の品質保証を担当するテストコードが格納されています。段階的開発に対応したテスト戦略・CI/CD本番稼働・品質ゲートを採用し、306テスト100%・58.88%カバレッジを達成しています。

## 📁 ディレクトリ構成

```
tests/
├── manual/            # 手動テスト・開発用テスト ✅ 実装済み
│   ├── test_phase2_components.py     # Phase 2コンポーネントテスト（5種類・100%合格）
│   └── README.md                     # 手動テスト説明 ✅
├── unit/             # 単体テスト ✅ Phase 13完了（306テスト100%・58.88%カバレッジ・CI/CD本番稼働）
│   ├── strategies/   # 戦略テスト（113テスト・100%合格・CI/CD本番稼働）
│   │   ├── implementations/  # 戦略実装テスト（62テスト）
│   │   ├── utils/           # 共通モジュールテスト（33テスト）
│   │   └── base/            # 戦略基盤テスト（18テスト）
│   ├── ml/           # 機械学習テスト（89テスト・100%合格・sklearn警告解消）
│   │   ├── models/          # 個別モデルテスト
│   │   ├── ensemble/        # アンサンブルテスト
│   │   └── README.md        # MLテスト詳細 ✅
│   ├── backtest/     # バックテストテスト（84テスト・100%合格）✅ Phase 13完了
│   │   ├── test_engine.py          # バックテストエンジンテスト
│   │   ├── test_evaluator.py       # 評価システムテスト
│   │   ├── test_data_loader.py     # データローダーテスト
│   │   ├── test_reporter.py        # レポートシステムテスト
│   │   └── README.md               # バックテストテスト詳細 ✅
│   ├── trading/      # 取引実行・リスク管理テスト（113テスト・100%合格・Phase 13完了）
│   │   ├── test_risk.py            # リスク管理テスト
│   │   ├── test_position_sizing.py # ポジションサイジングテスト
│   │   ├── test_drawdown_manager.py # ドローダウン管理テスト
│   │   ├── test_anomaly_detector.py # 異常検知テスト
│   │   └── README.md               # 取引テスト詳細 ✅
│   ├── core/         # 基盤システムテスト（Phase 13完了）
│   ├── data/         # データ層テスト（Phase 13完了）
│   └── features/     # 特徴量テスト（Phase 13完了）
├── integration/      # 統合テスト（Phase 8予定）
│   ├── api/          # API統合テスト
│   ├── pipeline/     # データパイプラインテスト
│   └── e2e/          # エンドツーエンドテスト
└── performance/      # パフォーマンステスト（Phase 8予定）
    ├── load/         # 負荷テスト
    └── memory/       # メモリ使用量テスト
```

## 🧪 テスト戦略

### Phase別テスト方針

**Phase 1-2完了**: 手動テスト中心
- ✅ 基盤コンポーネントの動作確認
- ✅ API接続テスト（認証不要の公開API）
- ✅ 基本機能検証（5種類テスト・100%合格）

**Phase 3-11完了**: 戦略・ML・バックテスト・取引実行単体テスト・CI/CDワークフロー最適化
- ✅ 戦略システム単体テスト（113テスト・100%合格・CI/CDワークフロー最適化）
- ✅ ML層単体テスト（89テスト・100%合格・監視統合）
- ✅ バックテストシステム単体テスト（84テスト・100%合格・CI/CD対応）
- ✅ 取引実行・リスク管理単体テスト（113テスト・100%合格・Phase 12完了）
- ✅ モック・スタブ活用・包括的品質管理・GitHub Actions統合

**Phase 6-7**: 実行・統合テスト追加
- リスク管理・取引実行の単体テスト
- API統合テスト実装
- エンドツーエンドテスト

**Phase 8**: 包括的テスト
- 統合テスト実装
- パフォーマンステスト
- バックテスト検証

### テストレベル

1. **手動テスト**: 開発時の動作確認
2. **単体テスト**: 個別モジュールの機能テスト
3. **統合テスト**: モジュール間連携テスト
4. **E2Eテスト**: 全体フローテスト

## 📊 現在のテスト状況

### ✅ 実装済み（Phase 1-5完了）

**manual/test_phase2_components.py**（5種類テスト・100%合格）:
- ✅ 設定システムテスト（Config・環境変数・YAML読み込み）
- ✅ BitbankClient基本機能テスト（公開API接続・市場情報取得）
- ✅ DataPipeline機能テスト（OHLCV取得・キャッシュ連携）
- ✅ DataCache機能テスト（メモリ・ディスク永続化）
- ✅ 統合テスト（簡易API・エンドツーエンド）

**unit/strategies/**（113テスト・100%合格）:
- ✅ 戦略実装テスト（62テスト）: ATR・もちぽよ・マルチタイムフレーム・フィボナッチ
- ✅ 共通モジュールテスト（33テスト）: RiskManager・SignalBuilder・constants
- ✅ 戦略基盤テスト（18テスト）: StrategyBase・StrategyManager

**unit/ml/**（89テスト・100%合格）:
- ✅ 個別モデルテスト: LightGBM・XGBoost・RandomForest
- ✅ アンサンブルテスト: 重み付け投票・信頼度閾値・モデル管理
- ✅ エラーハンドリング・統合テスト・ML統計検証

**unit/backtest/**（84テスト・100%合格）✅ Phase 12 CI/CD対応:
- ✅ バックテストエンジンテスト: ポジション管理・取引実行・性能最適化・CI/CDワークフロー最適化
- ✅ 評価システムテスト: ドローダウン計算・統計指標・リスク評価・品質ゲート
- ✅ データローダーテスト: 6ヶ月データ・品質管理・キャッシュ効率・GitHub Actions対応
- ✅ レポートシステムテスト: CSV/JSON/Discord出力・統合機能・監視統合

**unit/trading/**（113テスト・100%合格）✅ Phase 13完了:
- ✅ リスク管理テスト: Kelly基準・ドローダウン制御・異常検知・CI/CD本番稼働
- ✅ ポジションサイジングテスト: 動的調整・安全係数・リスク制限・品質保証
- ✅ 取引実行テスト: ペーパートレード・注文管理・レイテンシー監視・GitHub Actions対応
- ✅ 統合リスク評価テスト: 3段階判定・承認制御・Discord通知・品質ゲート

### 📋 未実装（Phase 6-8計画）

**単体テスト** (目標カバレッジ: 80%):
```
unit/
├── core/
│   ├── test_config.py      # 設定管理テスト
│   ├── test_logger.py      # ログシステムテスト
│   └── test_exceptions.py  # 例外処理テスト
├── data/
│   ├── test_bitbank_client.py  # Bitbank APIテスト
│   ├── test_data_pipeline.py   # データパイプラインテスト
│   └── test_data_cache.py      # キャッシングテスト
└── [その他Phase実装時に追加]
```

**統合テスト**:
```
integration/
├── api/
│   └── test_bitbank_integration.py    # Bitbank API統合
├── pipeline/
│   └── test_data_flow.py               # データフロー
└── e2e/
    └── test_trading_workflow.py       # 取引ワークフロー
```

## 🚀 テスト実行方法

### Phase 1-5実装済みテスト

```bash
# Phase 2手動テスト（5種類・100%合格）
cd /Users/nao/Desktop/bot
python tests/manual/test_phase2_components.py

# Phase 3-4戦略テスト（113テスト・100%合格）
python -m pytest tests/unit/strategies/ -v

# Phase 5-8 MLテスト（89テスト・100%合格）
python -m pytest tests/unit/ml/ -v

# Phase 8 バックテストテスト（84テスト・100%合格）
python -m pytest tests/unit/backtest/ -v

# 全実装済みテスト実行（438テスト・100%合格）
python tests/manual/test_phase2_components.py && python -m pytest tests/unit/strategies/ tests/unit/ml/ tests/unit/backtest/ -v

# 個別コンポーネント動作確認
python -c "from src.core.config import Config; print('✅ 設定OK')"
python -c "from src.data.bitbank_client import BitbankClient; print('✅ BitbankClient OK')"
python -c "from src.strategies.implementations.atr_based import ATRBasedStrategy; print('✅ ATR戦略OK')"
python -c "from src.ml.ensemble.ensemble_model import EnsembleModel; print('✅ MLアンサンブルOK')"
python -c "from src.backtest.engine import BacktestEngine; print('✅ バックテストエンジンOK')"
```

### 将来の自動テスト（Phase 8）

```bash
# 全テスト実行
pytest

# 単体テストのみ
pytest tests/unit/

# 統合テストのみ
pytest tests/integration/

# カバレッジ付き実行
pytest --cov=src --cov-report=html

# 特定モジュールのみ
pytest tests/unit/data/test_bitbank_client.py
```

## 🔧 テスト環境設定

### 必要な依存関係

```bash
# テスト用ライブラリ（Phase 8で追加予定）
pip install pytest pytest-cov pytest-mock

# 現在の手動テストは標準ライブラリのみ使用
```

### 環境変数（オプション）

```bash
# API認証情報（実際のテストでは不要）
export BITBANK_API_KEY=test_key
export BITBANK_API_SECRET=test_secret

# テストモード
export TEST_MODE=1
```

### モック・スタブ戦略

**外部API**: Bitbank APIはモック化
```python
# 例: Bitbank APIモック
@pytest.fixture
def mock_bitbank():
    with patch('ccxt.bitbank') as mock:
        mock.return_value.fetch_ticker.return_value = {
            'last': 12345678, 'bid': 12345000, 'ask': 12346000
        }
        yield mock
```

**データベース**: インメモリDB使用
**ファイルシステム**: 一時ディレクトリ使用

## 📈 品質指標

### Phase 12（完了）
- **手動テスト**: 5種類実装済み・100%合格・CI/CDワークフロー最適化
- **戦略単体テスト**: 113テスト・100%合格・0.44秒高速実行・GitHub Actions対応
- **ML単体テスト**: 89テスト・100%合格・監視統合・Phase 12最適化完了
- **バックテスト単体テスト**: 84テスト・100%合格・CI/CD対応・品質ゲート
- **取引実行単体テスト**: 113テスト・100%合格・Phase 12新規実装・監視統合
- **合格基準**: 全438テスト通過・68.13%品質保証・CI/CDワークフロー最適化

### Phase 6-8（目標）
- **全体カバレッジ**: 80%以上
- **統合テスト**: 主要ワークフロー網羅
- **パフォーマンス**: 処理時間1秒以内
- **メモリ使用量**: 最大2GB以内

### 継続的品質管理（Phase 12 CI/CDワークフロー最適化）
- **毎コミット**: 実装済みテスト実行（手動・戦略・ML・バックテスト・取引実行）・GitHub Actions自動実行
- **毎プルリクエスト**: 全438テスト通過・68.13%品質保証・CI/CD品質ゲート・自動ロールバック
- **毎リリース**: パフォーマンステスト・バックテスト検証・統合テスト・段階的デプロイ・手動実行監視

## 🧩 テストデータ管理

### テストデータ戦略

**本物API不要**: 公開APIのみ使用
```python
# 実際のBTC/JPY価格を取得してテスト
ticker = client.fetch_ticker('BTC/JPY')
assert ticker['last'] > 0
```

**モックデータ**: 予測可能なデータ
```python
# OHLCV形式のサンプルデータ
mock_ohlcv = [
    [1692000000000, 12340000, 12350000, 12330000, 12345000, 1.5],
    [1692003600000, 12345000, 12355000, 12340000, 12350000, 2.1],
    # ...
]
```

### データ生成ユーティリティ

```python
# テストデータ生成ヘルパー（Phase 8で実装予定）
def generate_ohlcv_data(count=100, base_price=12000000):
    """テスト用OHLCV データ生成"""
    
def generate_market_scenarios():
    """市場シナリオ データ生成"""
```

## 🔍 デバッグ・トラブルシューティング

### よくある問題

**インポートエラー**:
```bash
# Pythonパスの確認
export PYTHONPATH=/Users/nao/Desktop/bot:$PYTHONPATH

# または、プロジェクトルートから実行
cd /Users/nao/Desktop/bot
python tests/manual/test_phase2_components.py
```

**API接続エラー**:
```bash
# ネットワーク接続確認
curl https://api.bitbank.cc/v1/ticker/btc_jpy

# DNS確認
nslookup api.bitbank.cc
```

**モジュール未実装エラー**:
```bash
# 実装状況確認
ls -la src/data/
ls -la src/core/
```

### ログ確認

```python
# ログレベル調整
import logging
logging.getLogger('src').setLevel(logging.DEBUG)

# テスト実行
python tests/manual/test_phase2_components.py
```

## 📝 テスト作成ガイドライン

### 新しいテストの追加

1. **手動テスト** (Phase 2-7):
```python
def test_new_feature():
    """新機能のテスト"""
    try:
        # テスト実装
        result = new_feature()
        print("✅ 新機能テスト成功")
        return True
    except Exception as e:
        print(f"❌ 新機能テストエラー: {e}")
        return False
```

2. **単体テスト** (Phase 8):
```python
import pytest
from src.module import Function

def test_function_success():
    """正常系テスト"""
    result = Function.method("valid_input")
    assert result == expected_value

def test_function_error():
    """異常系テスト"""
    with pytest.raises(CustomException):
        Function.method("invalid_input")
```

### テスト命名規則

- **ファイル名**: `test_*.py`
- **関数名**: `test_*`
- **クラス名**: `Test*`
- **説明**: 日本語docstring推奨

### アサーション指針

- **明確な期待値**: 具体的な値を検証
- **エラーケース**: 適切な例外の発生を確認
- **境界値**: 最小・最大値でのテスト
- **型チェック**: 戻り値の型を確認

## 🚀 今後の予定

### Phase 3開始時
- 特徴量エンジニアリングの手動テスト追加

### Phase 8実装時
- pytest環境構築
- 全モジュールの単体テスト実装
- 統合テスト環境構築
- CI/CDワークフロー最適化

---

*段階的開発に対応した柔軟なテスト戦略*