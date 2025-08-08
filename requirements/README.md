# requirements/ - 依存関係管理システム

## 📋 概要

**Phase 12.5: Environment Parity & Dependency Management System**  
本フォルダは crypto-bot プロジェクトの依存関係管理を統一的に行う中央集約システムです。

## 🎯 設計原則

### **単一真実源 (Single Source of Truth)**
- `base.txt`: 本番環境の最小依存関係を定義
- `dev.txt`: 開発・CI環境の依存関係を定義（base.txtを継承）
- **手動管理排除**: Dockerfile での依存関係手動記述を廃止

### **環境統一 (Environment Parity)**
```
ローカル開発 ≈ CI環境 ≈ 本番環境
     ↓           ↓        ↓
  dev.txt → base.txt → Dockerfile
```

## 📁 ファイル構成

### `base.txt` - 本番環境最小依存関係
```bash
# 本番環境で動作に必要な最小限のパッケージ
# Docker本番イメージで使用
numpy>=1.24.0,<2.0      # 数値計算基盤
pandas>=1.5.0,<2.0      # データフレーム処理
scikit-learn==1.7.1     # 機械学習（バージョン固定）
ccxt>=2.10.0            # 取引所API
fastapi>=0.100.0        # Web APIフレームワーク
lightgbm>=4.0.0         # 機械学習モデル
xgboost>=1.7.0          # 機械学習モデル
# ... 他34パッケージ
```

### `dev.txt` - 開発・CI環境依存関係
```bash
# 本番依存関係を継承 + 開発専用ツール
-r base.txt

# テスト・品質保証
pytest>=7.0.0
flake8>=6.0.0
black>=24.3.0
mypy>=1.4.0

# 開発支援
ipython==8.18.1
matplotlib>=3.5.0
# ... 他27パッケージ
```

### `validate.py` - 依存関係一貫性チェッカー
```python
class DependencyValidator:
    """依存関係一貫性チェック・同期システム"""
    
    # 機能:
    # 1. base.txt ↔ Dockerfile 一貫性チェック
    # 2. バージョン不一致検出
    # 3. 同期情報表示
    # 4. 自動修正提案
```

## 🔧 使用方法

### **開発環境セットアップ**
```bash
# 開発用依存関係インストール（テスト・品質ツール込み）
pip install -r requirements/dev.txt
```

### **本番環境セットアップ**
```bash
# 本番用最小依存関係インストール
pip install -r requirements/base.txt
```

### **依存関係検証**
```bash
# 一貫性チェック実行
make validate-deps
# または直接実行
python requirements/validate.py

# 同期情報確認
make sync-deps  
# または直接実行
python requirements/validate.py --sync
```

## 🐳 Docker統合

### **自動統合仕様**
```dockerfile
# Dockerfile内での使用例
COPY requirements/base.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
```

### **validate.py による自動検証**
- Dockerfile内のpip install行を解析
- base.txtとの一貫性を自動チェック
- バージョン不一致・パッケージ不足を検出

## ⚙️ CI/CD統合

### **GitHub Actions 統合**
```yaml
# .github/workflows/ci.yml での使用
- name: Install dependencies
  run: pip install -r requirements/dev.txt

- name: Validate dependencies  
  run: make validate-deps
```

### **品質保証フロー**
```
1. ローカル開発: requirements/dev.txt
2. CI実行: requirements/dev.txt + validate.py
3. 本番デプロイ: requirements/base.txt → Docker
4. 一貫性保証: validate.py による自動チェック
```

## 📊 メリット・効果

### **運用効率向上**
- ✅ **手動管理排除**: Dockerfile内の手動依存関係記述廃止
- ✅ **ドリフト防止**: 環境間でのパッケージバージョン不一致防止
- ✅ **CI高速化**: 一貫した依存関係で安定したビルド時間

### **保守性向上**
- ✅ **中央集約管理**: 全依存関係をrequirements/で一元管理
- ✅ **自動検証**: validate.pyによる一貫性自動チェック
- ✅ **明確な責任分離**: 本番(base.txt) vs 開発(dev.txt)

### **品質保証**
- ✅ **Environment Parity**: Local ≈ CI ≈ Production
- ✅ **再現性保証**: 固定バージョンによる一貫した動作
- ✅ **セキュリティ**: 最小限のパッケージで攻撃面積削減

## 🚀 Phase 12.5 実装効果

### **従来の課題解決**
- ❌ **従来**: Dockerfile内に手動でpip install記述
- ❌ **従来**: 環境間でのバージョン不一致
- ❌ **従来**: 依存関係の重複管理

### **Phase 12.5で解決**
- ✅ **現在**: requirements.txt統一管理
- ✅ **現在**: validate.pyによる自動一貫性チェック  
- ✅ **現在**: 単一真実源による管理効率化

## 📋 メンテナンス指針

### **依存関係更新手順**
1. `requirements/base.txt` で本番依存関係更新
2. `requirements/dev.txt` で開発依存関係更新  
3. `make validate-deps` で一貫性チェック
4. CI/CDパイプラインでの自動検証確認

### **トラブルシューティング**
```bash
# 依存関係競合時
make validate-deps          # 問題箇所特定
make sync-deps             # 修正提案確認
# base.txtまたはDockerfile手動調整
```

---

**Phase 12.5: Environment Parity & Dependency Management System**により、crypto-botの依存関係管理は完全に自動化・統一されました。🎯