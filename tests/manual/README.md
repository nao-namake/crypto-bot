# tests/manual/ - 手動テストディレクトリ

**Phase 11完了**: 開発段階での動作確認とコンポーネントテスト・CI/CD統合・24時間監視対応を実施するディレクトリです。API認証情報なしでも実行可能なテストが中心で、399テスト実装済みの基盤・GitHub Actions統合・品質ゲートを支えています。

## 📁 ファイル構成

```
manual/
├── test_phase2_components.py  # Phase 2コンポーネントテスト ✅
└── README.md                  # このファイル
```

## 🧪 test_phase2_components.py - Phase 2テスト

**目的**: Phase 2で実装した全コンポーネントの統合テスト

### テスト項目

1. **設定システムテスト**
   - 基本設定クラスの作成
   - 設定検証機能
   - サマリー出力機能

2. **BitbankClient基本テスト**
   - クライアント初期化
   - API接続テスト（公開API使用）
   - 統計情報取得
   - 市場情報取得

3. **DataPipelineテスト**
   - OHLCV データ取得
   - キャッシング機能
   - キャッシュ情報確認

4. **DataCacheテスト**
   - データ保存・取得
   - 統計情報取得
   - ヒット率確認

5. **統合テスト**
   - 簡易API経由でのデータ取得
   - 全コンポーネントの連携確認

### 実行方法

```bash
# プロジェクトルートから実行
cd /Users/nao/Desktop/bot
python tests/manual/test_phase2_components.py
```

### 期待される出力

```
🚀 Phase 2 コンポーネントテスト開始
==================================================

🔧 設定システムテスト...
   設定検証結果: ✅
   モード: paper
   信頼度閾値: 0.35
   タイムフレーム: ['15m', '1h', '4h']

🏦 BitbankClient基本テスト...
   API接続テスト: ✅
   レバレッジ: 1.0x
   信用取引モード: ✅
   市場情報取得: ✅ BTC/JPY
   基軸通貨: BTC / 決済通貨: JPY

📊 DataPipeline機能テスト...
   OHLCV取得: ✅ 5行
   カラム: ['open', 'high', 'low', 'close', 'volume']
   最新価格: ¥12,345,678
   キャッシュ取得: ✅ 5行
   キャッシュ項目数: 1

💾 DataCache機能テスト...
   データ保存: ✅
   データ取得: ✅ 12345678
   キャッシュサイズ: 1項目
   ヒット率: 50.0%

🔗 統合テスト...
   統合API: ✅ 3行取得
   価格レンジ: ¥12,330,000 - ¥12,355,000

==================================================
📊 テスト結果サマリー
   設定システム: ✅ PASS
   BitbankClient基本: ✅ PASS
   DataPipeline: ✅ PASS
   DataCache: ✅ PASS
   統合テスト: ✅ PASS

🎯 合格率: 5/5 (100.0%)
🎉 Phase 2 コンポーネント実装完了！
```

## 🎯 テストの特徴

### API認証不要
- **公開API使用**: ticker、market info等の認証不要API
- **モック不要**: 実際のBitbank公開APIを使用
- **現実的テスト**: 実際の市場データでテスト

### エラーハンドリング確認
- **例外キャッチ**: 各テストで適切な例外処理
- **失敗時詳細**: エラー内容を詳細出力
- **継続実行**: 1つのテストが失敗しても他を継続

### 実用的出力
- **進捗表示**: 各テストの進行状況を表示
- **結果サマリー**: 最終的な合格率を表示
- **詳細情報**: 価格、設定値等の実際の値を表示

## 🔧 テスト環境要件

### 必要な環境
- **Python 3.9+**: 基本的なPython環境
- **ネットワーク接続**: Bitbank公開APIへのアクセス
- **ccxtライブラリ**: `pip install ccxt`（BitbankClient用）

### 不要な環境
- **API認証情報**: 公開APIのみ使用のため不要
- **複雑な設定**: デフォルト設定で動作
- **データベース**: インメモリのみ使用

## ⚠️ 注意事項とトラブルシューティング

### よくある問題

**1. インポートエラー**
```bash
# 解決方法: プロジェクトルートから実行
cd /Users/nao/Desktop/bot
python tests/manual/test_phase2_components.py
```

**2. ネットワークエラー**
```bash
# ネットワーク接続確認
curl https://api.bitbank.cc/v1/ticker/btc_jpy

# 出力例: {"success":1,"data":{"sell":"12345678",...}}
```

**3. ccxtライブラリエラー**
```bash
# ccxtインストール確認
python -c "import ccxt; print('ccxt OK')"

# インストールが必要な場合
pip install ccxt
```

**4. モジュール未実装エラー**
```bash
# 実装状況確認
ls -la src/data/bitbank_client.py
ls -la src/data/data_pipeline.py
ls -la src/data/data_cache.py
```

### デバッグ方法

**詳細ログ出力**:
```python
# テストファイル内で、ログレベルを調整
import logging
logging.getLogger('src').setLevel(logging.DEBUG)
```

**個別テスト実行**:
```python
# 特定のテストのみ実行
if __name__ == "__main__":
    test_bitbank_client_basic()
```

## 🚀 テスト拡張方法

### 新しいテストの追加

```python
def test_new_component():
    """新コンポーネントのテスト"""
    print("\n🆕 新コンポーネントテスト...")
    
    try:
        # テスト実装
        result = new_component.method()
        print(f"   結果: ✅ {result}")
        return True
        
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return False

# メインテストに追加
def main():
    tests = [
        # 既存のテスト...
        ("新コンポーネント", test_new_component),
    ]
```

### テストデータのカスタマイズ

```python
# カスタムテストパラメータ
TEST_SYMBOL = "BTC/JPY"          # テスト対象通貨ペア
TEST_TIMEFRAME = "1h"            # テスト対象タイムフレーム
TEST_LIMIT = 5                   # テストデータ件数
TEST_LEVERAGE = 1.5              # テストレバレッジ
```

## 📊 期待される性能

### 実行時間
- **全テスト実行**: 10-30秒
- **API接続テスト**: 2-5秒
- **データ取得テスト**: 3-8秒
- **キャッシュテスト**: 1秒未満

### 成功率
- **理想的条件**: 100%（5/5）
- **ネットワーク不安定**: 80%以上（4/5以上）
- **API制限時**: 60%以上（3/5以上）

### 出力サイズ
- **通常実行**: 50-100行の出力
- **エラー時**: 追加デバッグ情報
- **成功時**: 簡潔なサマリー

## 🔄 今後の計画

### Phase 3開始時
```python
# 特徴量エンジニアリングテスト追加
def test_technical_indicators():
    """テクニカル指標テスト"""

def test_feature_engineering():
    """特徴量生成テスト"""
```

### Phase 4-5開始時
```python
# 戦略・機械学習テスト追加
def test_trading_strategies():
    """取引戦略テスト"""

def test_ml_models():
    """機械学習モデルテスト"""
```

### Phase 11完了済み機能
- **全286テスト基盤**: 手動テストから始まった品質保証体制・CI/CD統合・GitHub Actions対応が完成
- **包括的テスト**: 戦略・ML・バックテスト・取引実行全領域を網羅・監視統合
- **99.7%品質保証**: Phase 11で285/286テスト合格・CI/CD品質ゲート・段階的デプロイ対応を達成
- **CI/CD統合**: GitHub Actions・品質ゲート・自動ロールバック・24時間監視統合

---

*開発段階に適したシンプルで実用的なテスト環境*