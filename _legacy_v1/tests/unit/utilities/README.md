# tests/unit/utilities/ - ユーティリティツールのユニットテスト

## 📋 概要

`scripts/utilities/` ディレクトリのユーティリティツールに対するユニットテストを管理するディレクトリです。  
Phase 2-3およびPhase 3で実装された高度な検証・監視・修復機能のテストケースを提供します。

## 🎯 テストファイル一覧

### **test_error_analyzer.py** (Phase 3)

エラー分析・自動修復システムのテストケース。

**テスト内容:**
- エラーパターンの検出精度
- 修復提案の生成
- 成功率学習機能
- ローカル/GCPログの取得
- HTMLレポート生成

**主要テストケース:**
```python
def test_analyze_error_patterns_auth_error()  # 認証エラー検出
def test_analyze_error_patterns_model_error()  # モデルエラー検出
def test_generate_suggestions()                # 修復提案生成
def test_learn_from_resolution()               # 学習機能
def test_save_and_load_solutions_db()          # DB永続化
```

### **test_future_leak_detector.py** (Phase 2-3)

未来データリーク検出器のテストケース。

**テスト内容:**
- 危険なコードパターンの検出
- DataFrame操作の検証
- バックテストデータ分割チェック
- レポート生成機能

**主要テストケース:**
```python
def test_detect_negative_shift()               # shift(-1)検出
def test_detect_center_rolling()               # center=True検出
def test_validate_dataframe_operations()       # DataFrame検証
def test_check_backtest_data_split()          # データ分割検証
def test_generate_report()                     # レポート生成
```

## 🚀 テスト実行方法

### **個別テスト実行**

```bash
# エラー分析器のテスト
pytest tests/unit/utilities/test_error_analyzer.py -v

# 未来データリーク検出器のテスト
pytest tests/unit/utilities/test_future_leak_detector.py -v

# 特定のテストケースのみ実行
pytest tests/unit/utilities/test_error_analyzer.py::TestErrorAnalyzer::test_analyze_error_patterns_auth_error -v
```

### **統合テスト実行**

```bash
# utilities全体のテスト
pytest tests/unit/utilities/ -v

# カバレッジ測定付き
pytest tests/unit/utilities/ --cov=scripts/utilities --cov-report=html

# 並列実行（高速化）
pytest tests/unit/utilities/ -n auto
```

## 📊 テストカバレッジ目標

| モジュール | 現在のカバレッジ | 目標 |
|-----------|-----------------|------|
| error_analyzer.py | 85% | 90% |
| future_leak_detector.py | 82% | 90% |

## 🛠️ テストデータ

### **エラーログサンプル**

`test_error_analyzer.py` で使用：
```python
errors = [
    {"message": "401 Unauthorized", "severity": "ERROR"},
    {"message": "FileNotFoundError: model.pkl", "severity": "ERROR"},
    {"message": "HTTPError: Connection refused", "severity": "ERROR"}
]
```

### **DataFrameサンプル**

`test_future_leak_detector.py` で使用：
```python
df = pd.DataFrame({
    'close': np.random.randn(100),
    'volume': np.random.randn(100),
    'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h')
})
```

## ⚠️ 注意事項

### **モック使用**

- GCPログ取得はモックを使用（実際のAPIコールは行わない）
- subprocess呼び出しはパッチを使用

### **一時ファイル**

- テスト中に生成される一時ファイルは自動削除
- `tempfile.mkdtemp()` を使用して隔離環境で実行

### **インポートパス**

スクリプトディレクトリを動的に追加：
```python
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "utilities")
)
```

## 🔍 トラブルシューティング

### **インポートエラー**

```bash
# パスが見つからない場合
export PYTHONPATH=$PYTHONPATH:/Users/nao/Desktop/bot
```

### **テスト失敗時のデバッグ**

```bash
# 詳細なエラー出力
pytest tests/unit/utilities/ -v -s --tb=short

# 最初のエラーで停止
pytest tests/unit/utilities/ -x

# pdbデバッガを起動
pytest tests/unit/utilities/ --pdb
```

## 📝 新規テスト追加ガイドライン

1. **命名規則**: `test_[モジュール名].py`
2. **クラス構造**: `TestClassName` 形式
3. **セットアップ**: `setup_method()` で初期化
4. **アサーション**: 明確で具体的なアサーション
5. **モック**: 外部依存は必ずモック化

---

*最終更新: 2025年8月11日 - Phase 2-3/Phase 3テスト実装*