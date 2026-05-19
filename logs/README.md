# logs/

ローカル実行時のログ・レポート・学習履歴の出力先。`.gitignore:102` で除外（git 管理外）。

## 目的

本番運用（GCP Cloud Run）は Cloud Logging に集約されるため、本フォルダは**ローカル実行時の補助記録**用途:
- ローカル bot 実行ログ（`crypto_bot.log`, `__main__.log`）
- ML 学習ログ（CI 経由・ローカル経由の両方）
- バックテスト結果（JSON・テキスト・グラフ）
- テスト実行で生成されるレポートフィクスチャ

## ディレクトリ構造

| パス | 役割 | 書き込み元 |
|---|---|---|
| `crypto_bot.log[.YYYY-MM-DD]` | bot メインログ（日次ローテーション） | `src.core.logger` |
| `__main__.log[.YYYY-MM-DD]` | エントリポイント実行ログ | `main.py` |
| `ml/` | CI ML 学習ログ（`.github/workflows/model-training.yml`） | `scripts/ml/create_ml_models.py` |
| `ml_local/` | ローカル ML 学習ログ | `scripts/ml/run_local_training.sh` |
| `backtest/` | バックテスト出力（JSON + テキスト + `graphs/`） | `scripts/backtest/run_backtest.sh` |
| `paper_trading_reports/` | ペーパートレード結果 | `src/core/reporting/paper_trading_reporter.py` |
| `reports/` | レポート出力（テスト経由でも書き込まれる） | `src/core/reporting/base_reporter.py` |

設定参照: `config/core/thresholds.yaml:638-640` (`reporting.base_dir`, `paper_trading_dir`, `error_dir`)

## ローテーション・整理方針

- **`crypto_bot.log` / `__main__.log`**: 日次ローテーション。直近 2-3 日分を保持、それ以前は削除可
- **ML 学習ログ**: 直近 Phase 対応分（v8c, v8e 等）は保全、失敗した試行のログ（v7 timeout, v8a/v8b ハング等）は削除可
- **バックテスト**: `graphs/` の最新セットは保全、JSON は 1 ヶ月以上前のものは削除可
- **`reports/` サブフォルダ**: `tests/unit/core/reporting/test_base_reporter.py` がテスト時に生成（`log_test`, `nested_test`, `special_chars` 等）→ テスト後削除可
- **整理ツール**: `/organize-folder logs` で 7 ステップ承認制クリーンアップ

## 関連リンク

- 親 README: [../README.md](../README.md)
- バックテスト: [../src/backtest/README.md](../src/backtest/README.md)
- ML 学習: [../scripts/ml/README.md](../scripts/ml/README.md)
- レポート出力: [../src/core/reporting/README.md](../src/core/reporting/README.md)
