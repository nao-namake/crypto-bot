# scripts/live/ - ライブモード統合診断ツール（Phase 61.2）

**最終更新**: 2026年1月24日

## 役割

本番運用（GCP Cloud Run）の稼働状況を診断するツールを提供します。
Phase 61.2で `scripts/monitoring/` の機能を統合し、単一スクリプトで完全な診断を実現。

## ファイル構成

```
scripts/live/
├── README.md              # このファイル
└── standard_analysis.py   # 統合診断スクリプト（39指標 + インフラ診断 + Bot機能診断）
```

## standard_analysis.py

ライブ運用の標準化された分析とインフラ・Bot機能診断を統合実行。

### 使用方法

```bash
# 基本実行（全診断 + 39指標）
python3 scripts/live/standard_analysis.py

# 期間指定（48時間）
python3 scripts/live/standard_analysis.py --hours 48

# 出力先指定
python3 scripts/live/standard_analysis.py --output results/live/

# CI/CD連携（終了コード返却）
python3 scripts/live/standard_analysis.py --exit-code

# 簡易チェック（GCPログのみ、API呼び出しなし）
python3 scripts/live/standard_analysis.py --quick
```

### 終了コード（--exit-code オプション使用時）

| コード | 状態 | 説明 |
|--------|------|------|
| 0 | 正常 | 全診断項目が正常 |
| 1 | 致命的問題 | 即座対応必須（Silent Failure等） |
| 2 | 要注意 | 詳細診断推奨 |
| 3 | 監視継続 | 軽微な問題 |

### 分析項目

#### 39指標（LiveAnalyzer）

| カテゴリ | 指標数 | 内容 |
|---------|--------|------|
| アカウント状態 | 5 | 証拠金維持率、利用可能残高、未実現損益等 |
| ポジション状態 | 7 | オープンポジション、未約定注文、孤児SL検出等 |
| 取引履歴分析 | 9 | 取引数、勝率、損益、戦略別統計等 |
| システム健全性 | 6 | API応答時間、エラー数、サービス状態等 |
| TP/SL適切性 | 4 | TP/SL距離、設置状態等 |
| 稼働率 | 5 | 稼働時間率、ダウンタイム、再起動回数等 |
| MLモデル状態 | 4 | モデルタイプ、フォールバックレベル、特徴量数等 |

#### インフラ基盤診断（InfrastructureChecker）

| 項目 | 内容 |
|------|------|
| Cloud Run稼働状況 | サービス状態・最新リビジョン確認 |
| Secret Manager権限 | 3シークレットのIAM権限確認 |
| Container安定性 | exit(1)・RuntimeWarning検出 |
| Discord通知 | Webhookエラー検出 |
| API残高取得 | 残高取得ログ・フォールバック使用状況 |
| ポジション復元 | Container再起動時の復元動作確認 |
| 取引阻害エラー | NoneType・APIエラー検出 |

#### Bot機能診断（BotFunctionChecker）

| 項目 | 内容 |
|------|------|
| 55特徴量システム | 特徴量セット・フォールバック状況確認 |
| Silent Failure検出 | シグナル生成 vs 注文実行の比率 |
| 6戦略動作確認 | 各戦略のログ検出 |
| ML予測確認 | ProductionEnsemble動作確認 |
| レジーム別TP/SL | tight_range/normal_range/trending検出 |
| Kelly基準確認 | Kelly計算実行確認 |
| Atomic Entry確認 | 成功・ロールバック頻度 |

### 出力

| ファイル | 内容 |
|---------|------|
| `live_analysis_YYYYMMDD_HHMMSS.json` | 全指標 + 診断結果のJSON |
| `live_analysis_YYYYMMDD_HHMMSS.md` | Markdownレポート（診断結果含む） |
| `live_analysis_history.csv` | 履歴追記（変更前後比較用） |

### MLモデル状態確認

ダミーモデルが使用されていないか確認可能：

| 指標 | 正常値 | 異常値 |
|------|--------|--------|
| `ml_model_type` | ProductionEnsemble | DummyModel |
| `ml_model_level` | 0-1 | 3 |
| `ml_feature_count` | 55 | 0 |

## 前提条件

- **bitbank APIキー**: `config/secrets/.env`に設定
- **gcloud CLI**: GCPログ取得に必要（ローカル実行時はスキップ）
- **gh CLI**: 最新CI時刻取得に必要（オプション）
- **取引履歴DB**: `tax/trade_history.db`（取引履歴分析用）

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `docs/検証記録/live/` | 分析結果の保存先 |
| `config/secrets/.env` | APIキー設定 |
| `tax/trade_history.db` | 取引履歴データベース |

## 移行元（Phase 61.2で統合・削除）

以下のスクリプトは `standard_analysis.py` に統合され、削除されました：

| 削除ファイル | 統合先 |
|-------------|--------|
| `scripts/monitoring/check_infrastructure.sh` | InfrastructureChecker クラス |
| `scripts/monitoring/check_bot_functions.sh` | BotFunctionChecker クラス |
| `scripts/monitoring/emergency_fix.sh` | 削除（手動gcloudコマンド使用） |
