# tests/manual/ - 手動テスト・開発検証

## 🎯 役割・責任

手動テスト・開発検証スクリプトを管理し、開発時の動作確認、コンポーネント検証、API接続テストを支援します。自動テストでカバーできない実際のAPI接続や統合動作を手動で確認し、開発品質の向上と問題の早期発見を支援します。

## 📂 ファイル構成

```
tests/manual/
├── README.md                   # このファイル
└── manual_bitbank_client.py    # Bitbank APIクライアント手動テスト
```

## 📋 主要ファイルの役割

### **manual_bitbank_client.py**
Bitbank APIクライアントの動作確認を行う手動テストスクリプトです。
- **基本API接続テスト**: 公開APIを使用したクライアント初期化・接続確認
- **統計情報取得**: クライアント設定・レバレッジ・サポート時間軸の確認
- **エラーハンドリング**: API接続エラー・認証エラーの適切な処理
- **ログ統合**: setup_loggingによる構造化ログ・エラー追跡
- **開発支援**: 実際のAPI動作確認・デバッグ支援・問題特定
- 約5.4KBのテストスクリプト

### **主要機能と特徴**
- **認証不要テスト**: 公開APIのみ使用・API認証情報なしでのテスト実行
- **実API接続**: モックではない実際のBitbank APIでの動作確認
- **統合テスト**: src/data/bitbank_client.pyとの実際の統合動作確認
- **開発時確認**: 新機能実装時の動作確認・問題の早期発見
- **トラブルシューティング**: API制限・ネットワーク問題・設定エラーの特定

## 📝 使用方法・例

### **基本的なAPI接続テスト**
```bash
# プロジェクトルートから実行
cd /Users/nao/Desktop/bot
python tests/manual/manual_bitbank_client.py

# 期待結果:
# ✅ クライアント初期化成功
# 📊 サポート時間軸: ['1m', '5m', '15m', '30m', '1h', '4h', '8h', '12h', '1d', '1w']
# 📈 クライアント統計情報
# 🎉 基本テスト完了
```

### **開発時の動作確認**
```python
# Python対話環境での手動テスト
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src.data.bitbank_client import BitbankClient

# 基本クライアント作成
client = BitbankClient(leverage=1.5)

# 接続テスト
connection_ok = client.test_connection()
print(f"接続状態: {connection_ok}")

# 統計情報確認
stats = client.get_stats()
print(f"クライアント統計: {stats}")
```

### **トラブルシューティング**
```bash
# ネットワーク接続確認
curl -I https://api.bitbank.cc/v1/ticker/btc_jpy

# モジュールインポート確認
python -c "from src.data.bitbank_client import BitbankClient; print('✅ インポート成功')"

# ログファイル確認
tail -f logs/crypto_bot.log
```

### **API制限・レスポンス確認**
```bash
# 詳細ログ付きテスト実行
python tests/manual/manual_bitbank_client.py --verbose

# 特定機能のみテスト
python -c "
from tests.manual.manual_bitbank_client import test_bitbank_basic
test_bitbank_basic()
"
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **実行場所**: プロジェクトルートディレクトリ（/Users/nao/Desktop/bot）から実行必須
- **Python環境**: Python 3.8以上・src/モジュール・依存関係完全インストール
- **ネットワーク**: Bitbank API（https://api.bitbank.cc）への接続必須
- **実行時間**: 各テスト10-30秒・API応答時間に依存

### **API使用制約**
- **公開APIのみ**: 認証不要・ticker・market info・統計情報のみ使用
- **レート制限**: Bitbank API制限内での実行・過度な頻繁実行回避
- **エラー処理**: ネットワークエラー・API制限・タイムアウトの適切な処理
- **実データ使用**: モック不使用・実際の市場データでのテスト

### **開発時注意事項**
- **設定分離**: テスト用設定・本番設定の明確な分離
- **ログ管理**: テストログ・本番ログの適切な分離・クリーンアップ
- **状態管理**: テスト実行後のクリーンアップ・状態リセット
- **エラー報告**: 問題発見時の適切な報告・ログ保存・再現手順

### **手動テストの限界**
- **自動化不可**: CI/CDパイプラインでの自動実行困難
- **人的依存**: 手動実行・結果確認・判断の人的リソース依存
- **再現性**: 実API使用による結果のばらつき・時間依存の結果
- **スケール制約**: 大量テスト・継続的テストには不適切

## 🔗 関連ファイル・依存関係

### **テスト対象システム**
- `src/data/bitbank_client.py`: Bitbank APIクライアント・接続・データ取得
- `src/core/logger.py`: ログシステム・構造化ログ・エラー追跡
- `src/data/data_pipeline.py`: データパイプライン・OHLCV取得・統合処理
- `src/data/data_cache.py`: データキャッシュ・保存・統計情報

### **設定・環境管理**
- `config/`: システム設定・API設定・環境変数・認証情報
- `logs/`: テストログ・エラーログ・API接続ログ・デバッグ情報
- 環境変数・API認証・ネットワーク設定・プロキシ設定

### **品質保証との統合**
- `tests/unit/`: 単体テスト・モックテスト・回帰テスト・自動品質保証
- `scripts/testing/checks.sh`: 品質チェック（Phase 39完了版）・テスト統合・CI/CD品質ゲート

### **外部システム統合**
- **Bitbank API**: 公開API・市場データ・レート制限・エラーレスポンス
- **ネットワーク**: DNS・プロキシ・SSL/TLS・接続タイムアウト
- **ログ統合**: Discord通知・Cloud Run監視・アラート・レポート

### **開発・デバッグ支援**
- **IDE統合**: VSCode・PyCharm・デバッガー・ブレークポイント
- **Python REPL**: 対話的テスト・動的確認・プロトタイピング
- **curl/HTTPie**: HTTP接続確認・API直接テスト・レスポンス確認
- **ネットワークツール**: ping・traceroute・nslookup・接続診断

### **継続的改善**
- **フィードバック**: 手動テスト結果の単体テストへの反映
- **自動化**: 手動テストから自動テストへの段階的移行
- **品質向上**: 問題パターンの特定・予防・改善提案
- **知識蓄積**: トラブルシューティング・ベストプラクティス・ドキュメント化