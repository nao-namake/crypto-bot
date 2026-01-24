# scripts/ - システム運用・管理スクリプト集（Phase 61版）

**最終更新**: 2026年1月25日 - Phase 61.2完了

## 役割・責任

システム開発・運用・監視・デプロイメント・バックテストの全工程を支援する統合ツール集を提供します。品質保証、機械学習モデル管理、本番環境デプロイ、バックテスト実行まで、包括的な自動化ツールでシステムの効率的な開発・運用を支援します。

**Phase 61成果**: 戦略分析・コードベース整理・レジーム判定最適化・62%+カバレッジ維持

## ディレクトリ構成

```
scripts/
├── README.md               # このファイル（Phase 61版）
├── analysis/               # 分析スクリプト
│   └── strategy_performance_analysis.py  # 戦略個別パフォーマンス分析（60日）
├── backtest/               # バックテスト実行システム [詳細: backtest/README.md]
│   ├── README.md                  # バックテスト実行ガイド（Phase 61版）
│   ├── run_backtest.sh            # バックテスト実行スクリプト
│   └── standard_analysis.py       # バックテスト標準分析（84指標）
├── deployment/             # デプロイメント・インフラ管理 [詳細: deployment/README.md]
│   ├── README.md                  # デプロイメントガイド（Phase 61版）
│   ├── docker-entrypoint.sh       # Dockerコンテナエントリーポイント
│   └── archive/                   # 初期セットアップ用スクリプト
├── live/                   # ライブモード分析 [詳細: live/README.md]
│   ├── README.md                  # ライブモード分析ガイド
│   └── standard_analysis.py       # ライブモード標準分析（39指標）
├── management/             # Bot管理スクリプト [詳細: management/README.md]
│   ├── README.md                  # Bot管理ガイド（Phase 61版）
│   └── run_paper.sh               # ペーパートレード実行スクリプト
├── ml/                     # 機械学習モデル学習・管理 [詳細: ml/README.md]
│   ├── README.md                  # ML管理ガイド（Phase 61版）
│   └── create_ml_models.py        # MLモデル学習スクリプト（55特徴量）
└── testing/                # 品質保証・テストシステム [詳細: testing/README.md]
    ├── README.md                  # テストシステムガイド（Phase 61版）
    ├── checks.sh                  # 品質チェック統合スクリプト（12項目）
    └── validate_ml_models.py      # ML検証スクリプト（8項目）
```

## 主要ディレクトリの役割

### **testing/ - 品質保証・テストシステム（Phase 61版）**

システム全体の品質保証とテスト実行を担当。

| ファイル | 役割 |
|----------|------|
| checks.sh | 品質チェック統合スクリプト（12項目・約60秒） |
| validate_ml_models.py | ML検証スクリプト（8項目・整合性+品質検証） |

**checks.sh 12項目**: ディレクトリ構造・Dockerfile整合性・特徴量数(55)・戦略整合性(6)・設定ファイル・モデルファイル・ML検証・flake8・isort・black・pytest・結果サマリー

### **ml/ - 機械学習モデル学習・管理（Phase 61版）**

機械学習モデルの学習・構築・品質保証を担当。

| ファイル | 役割 |
|----------|------|
| create_ml_models.py | 55特徴量MLモデル学習（LightGBM・XGBoost・RandomForest） |

**特徴量構成**: 49基本特徴量 + 6戦略信号 = 55特徴量

### **deployment/ - デプロイメント・インフラ管理（Phase 61版）**

本番環境デプロイとインフラ管理を担当。

| ファイル | 役割 |
|----------|------|
| docker-entrypoint.sh | Dockerコンテナ起動制御・ヘルスチェック |
| archive/ | 初期セットアップ用スクリプト（環境構築済みのため使用頻度低） |

### **management/ - Bot管理スクリプト（Phase 61版）**

Botの安全で効率的な実行・管理を支援。

| ファイル | 役割 |
|----------|------|
| run_paper.sh | ペーパートレード実行・停止・状況確認 |

### **backtest/ - バックテスト実行システム（Phase 61版）**

バックテストシステムの実行・管理を支援。

| ファイル | 役割 |
|----------|------|
| run_backtest.sh | バックテスト実行（quick/standard/full） |
| standard_analysis.py | バックテスト結果分析（84指標） |

### **live/ - ライブモード分析（Phase 61版）**

ライブトレードの分析・監視を支援。

| ファイル | 役割 |
|----------|------|
| standard_analysis.py | ライブモード標準分析（39指標） |

### **analysis/ - 分析スクリプト**

戦略・パフォーマンス分析を支援。

| ファイル | 役割 |
|----------|------|
| strategy_performance_analysis.py | 戦略個別パフォーマンス分析（60日） |

## 使用方法

### 日常開発ワークフロー（必須）

```bash
# 品質チェック（開発前後必須・約60秒）
bash scripts/testing/checks.sh

# 期待結果:
# ✅ システム整合性（6項目）
# ✅ ML検証通過（55特徴量・3クラス分類）
# ✅ コードスタイル準拠（flake8・black・isort）
# ✅ pytest成功（62%+カバレッジ）
```

### ペーパートレード実行

```bash
# 実行
bash scripts/management/run_paper.sh

# 停止
bash scripts/management/run_paper.sh stop

# 状況確認
bash scripts/management/run_paper.sh status
```

### バックテストワークフロー

```bash
# クイックバックテスト（7日間・動作確認用）
bash scripts/backtest/run_backtest.sh quick

# 標準バックテスト（30日間・通常検証用）
bash scripts/backtest/run_backtest.sh standard

# フルバックテスト（180日間・完全検証）
bash scripts/backtest/run_backtest.sh full

# 結果分析（CIの最新結果を取得）
python3 scripts/backtest/standard_analysis.py --from-ci
```

### ライブモード分析

```bash
# 基本実行（24時間分析）
python3 scripts/live/standard_analysis.py

# 期間指定（48時間）
python3 scripts/live/standard_analysis.py --hours 48
```

### 機械学習ワークフロー

```bash
# モデル学習・構築（基本実行）
python3 scripts/ml/create_ml_models.py --verbose

# Optunaハイパーパラメータ最適化
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50 --verbose

# ML検証（モデル更新後推奨）
python3 scripts/testing/validate_ml_models.py
```

### 本番デプロイワークフロー

```bash
# 1. 品質チェック（必須）
bash scripts/testing/checks.sh

# 2. デプロイ実行（GitHub Actions自動実行）
# .github/workflows/ci.yml が自動実行（main ブランチpush時）

# 3. デプロイ後確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
```

## 品質基準（Phase 61）

| 指標 | 基準 | 説明 |
|------|------|------|
| テスト成功率 | 100% | 全テスト成功必須 |
| カバレッジ | 62%以上 | 最低ライン維持 |
| コードスタイル | PASS | flake8/black/isort通過 |
| 特徴量数 | 55 | 49基本 + 6戦略信号 |
| 戦略数 | 6 | レンジ型4 + トレンド型2 |
| 3クラス分類 | 必須 | BUY/HOLD/SELL |

## 関連ファイル

### システム統合
- `src/`: メインシステム・特徴量生成・機械学習・取引システム
- `config/`: 設定管理（unified.yaml・thresholds.yaml・features.yaml）
- `models/`: 機械学習モデル（ensemble_full.pkl・ensemble_basic.pkl）
- `tests/`: 単体テスト・統合テスト

### CI/CD
- `.github/workflows/ci.yml`: CI品質ゲート
- `.github/workflows/model-training.yml`: 週次モデル再学習
- `.github/workflows/backtest.yml`: バックテスト実行
- `Dockerfile`: コンテナ化・実行環境

### ドキュメント
- `CLAUDE.md`: 開発ガイド（Phase 61版）
- `docs/運用ガイド/統合運用ガイド.md`: デプロイ・日常運用・緊急対応
- `docs/開発履歴/Phase_61.md`: Phase 61開発記録
