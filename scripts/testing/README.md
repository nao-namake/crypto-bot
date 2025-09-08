# scripts/testing/ - 品質保証・テストシステム

## 🎯 役割・責任

システム全体の品質保証、テスト実行、コード品質チェック、統合診断を担当するテストシステムです。単体テストから統合テスト、カバレッジ測定、コードスタイルチェック、機械学習モデル検証まで、包括的な品質保証機能を提供し、継続的な品質向上と回帰防止を支援します。

## 📂 ファイル構成

```
scripts/testing/
├── README.md              # このファイル
├── checks.sh              # 品質チェック・テスト実行スクリプト
└── dev_check.py           # 統合開発管理CLI・システム診断
```

## 📋 主要ファイル・フォルダの役割

### **checks.sh**
システム全体の品質チェックとテスト実行を管理するメインスクリプトです。
- **テスト実行**: pytest による全テストスイート実行・単体/統合テスト
- **カバレッジ測定**: coverage による網羅率測定・HTML/JSON/Term出力
- **コードスタイル**: flake8・black・isort によるPEP8準拠チェック
- **ディレクトリ構造確認**: プロジェクト構造・ファイル存在確認
- **品質ゲート**: 品質基準チェック・CI/CD統合・デプロイ前確認
- **レポート生成**: coverage-reports/への詳細レポート出力
- 約4.3KBの実装ファイル・約30秒で完了

### **dev_check.py**
開発・運用における統合管理とシステム診断を担当するCLIツールです。
- **統合品質チェック**: テスト・カバレッジ・コード品質の一括確認
- **機械学習検証**: モデル学習・ProductionEnsemble作成・性能評価
- **システム診断**: 設定確認・依存関係確認・環境検証
- **データ検証**: 市場データ取得・特徴量生成・データ品質確認
- **本番環境監視**: Cloud Run・GCP・Discord通知・ヘルスチェック
- **自動レポート**: Markdown形式・logs/reports/ci_checks/への保存
- **多機能CLI**: validate・ml-models・status・health-check等のサブコマンド
- 約62.3KBの大規模実装ファイル

### **主要機能と特徴**
- **継続的品質保証**: 開発サイクルでの品質維持・回帰防止・自動化
- **包括的診断**: システム全体の健全性確認・問題早期発見
- **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ対応
- **運用監視**: 本番環境・Cloud Run・Discord通知との統合
- **開発効率**: コマンド一つでの包括的確認・問題の迅速な特定

## 📝 使用方法・例

### **日常開発での品質チェック**
```bash
# 基本的な品質チェック（開発時必須）
bash scripts/testing/checks.sh

# 期待結果:
# ✅ 全テスト成功
# ✅ カバレッジ基準達成
# ✅ コードスタイル準拠
# ✅ 約30秒で完了

# カバレッジレポート確認
open coverage-reports/htmlcov/index.html
```

### **統合開発管理CLI**
```bash
# 包括的品質チェック（推奨）
python3 scripts/testing/dev_check.py full-check

# 個別機能チェック
python3 scripts/testing/dev_check.py validate       # 基本品質チェック
python3 scripts/testing/dev_check.py ml-models      # 機械学習モデル作成
python3 scripts/testing/dev_check.py data-check     # データ取得・確認
python3 scripts/testing/dev_check.py status         # システム状態確認

# 本番環境監視
python3 scripts/testing/dev_check.py health-check   # Cloud Run・GCP確認
```

### **CI/CD統合使用**
```bash
# CI前品質チェック（必須）
bash scripts/testing/checks.sh
if [ $? -eq 0 ]; then
    echo "✅ 品質チェック成功 - CI実行可能"
else
    echo "❌ 品質チェック失敗 - 修正必要"
    exit 1
fi

# デプロイ前最終確認
python3 scripts/testing/dev_check.py full-check --production
```

### **機械学習モデル管理**
```bash
# モデル学習・検証
python3 scripts/testing/dev_check.py ml-models --verbose

# ドライラン（実行前確認）
python3 scripts/testing/dev_check.py ml-models --dry-run

# 期待結果:
# ✅ 特徴量生成確認
# ✅ 個別モデル学習
# ✅ ProductionEnsemble作成
# ✅ 性能評価・品質確認
```

### **トラブルシューティング**
```python
import subprocess

def run_comprehensive_diagnosis():
    """包括的システム診断"""
    
    print("=== システム診断開始 ===")
    
    # 品質チェック
    result = subprocess.run(["bash", "scripts/testing/checks.sh"], 
                          capture_output=True, text=True)
    print(f"品質チェック: {'✅ 成功' if result.returncode == 0 else '❌ 失敗'}")
    
    # システム状態確認
    result = subprocess.run(["python3", "scripts/testing/dev_check.py", "status"], 
                          capture_output=True, text=True)
    print(f"システム状態: {'✅ 正常' if result.returncode == 0 else '❌ 異常'}")
    
    # 本番環境確認
    result = subprocess.run(["python3", "scripts/testing/dev_check.py", "health-check"], 
                          capture_output=True, text=True)
    print(f"本番環境: {'✅ 正常' if result.returncode == 0 else '❌ 異常'}")

# 診断実行
run_comprehensive_diagnosis()
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.8以上・pytest・coverage・flake8・black・isort
- **実行場所**: プロジェクトルートディレクトリからの実行必須
- **依存関係**: 全システムモジュール・機械学習ライブラリ・設定ファイル
- **権限**: テスト実行・ファイル作成・ネットワークアクセス権限

### **品質基準**
- **テスト成功率**: 全テスト100%成功・回帰防止・継続的品質維持
- **カバレッジ基準**: 50%以上維持・新機能でのテスト追加必須
- **コードスタイル**: PEP8準拠・flake8・black・isort通過必須
- **実行時間**: checks.sh約30秒・dev_check.py機能により1-10分

### **CI/CD統合制約**
- **品質ゲート**: 全チェック通過後のデプロイ実行・失敗時停止
- **自動実行**: GitHub Actions・CI/CD パイプライン統合
- **段階的デプロイ**: 各段階での品質確認・問題時ロールバック
- **監視統合**: Discord通知・アラート・レポート自動送信

### **機械学習検証制約**
- **データ要件**: 十分な学習データ・特徴量品質・時系列整合性
- **モデル品質**: 性能閾値・過学習防止・交差検証・品質評価
- **リソース制限**: メモリ使用量・計算時間・ストレージ容量管理
- **バージョン管理**: モデル保存・メタデータ・履歴追跡・ロールバック

## 🔗 関連ファイル・依存関係

### **テスト・品質保証システム**
- `tests/`: 単体テスト・統合テスト・機械学習テスト・全テストスイート
- `coverage-reports/`: カバレッジレポート・HTML・JSON・統計データ
- `logs/reports/ci_checks/`: 品質チェックレポート・履歴・分析データ

### **機械学習システム**
- `src/features/feature_generator.py`: 特徴量生成・データ前処理・品質確認
- `src/ml/ensemble.py`: ProductionEnsemble・モデル管理・性能評価
- `models/`: モデルファイル・メタデータ・学習結果・バージョン管理
- `scripts/ml/create_ml_models.py`: モデル学習・作成・品質検証

### **設定・環境管理**
- `config/`: システム設定・品質閾値・テスト設定・環境変数
- `.flake8`: コードスタイル設定・品質基準・除外ルール
- `pyproject.toml`: プロジェクト設定・依存関係・ツール設定

### **CI/CD・デプロイシステム**
- `.github/workflows/`: CI/CDパイプライン・自動テスト・品質ゲート
- `scripts/deployment/`: デプロイメント・本番環境・品質確認統合
- `src/monitoring/discord_notifier.py`: 通知・アラート・レポート送信

### **外部システム統合**
- **GitHub Actions**: CI/CDパイプライン・自動テスト・品質ゲート統合
- **GCP Cloud Run**: 本番環境・ヘルスチェック・監視・ログ確認
- **Discord API**: 通知システム・品質アラート・レポート配信
- **Bitbank API**: データ取得・取引システム・統合テスト

### **品質管理ツール**
- **pytest**: テストフレームワーク・単体/統合テスト・アサーション
- **coverage**: カバレッジ測定・HTML/JSON出力・品質指標
- **flake8**: コードスタイル・PEP8準拠・品質チェック
- **black・isort**: コード整形・インポート整理・一貫性確保