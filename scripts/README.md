# scripts/ - 運用・管理スクリプト集

開発・運用・監視・デプロイ・バックテスト・ML 学習の自動化ツール群。

## ディレクトリ構成

| サブフォルダ | 役割 | 主要ファイル |
|---|---|---|
| [analysis/](analysis/) | 戦略・シグナル・SL の事後分析 | `unified_strategy_analyzer.py` `signal_simulation.py` `sl_simulation.py` `diagnose_trade_drop.py` `full_entry_simulation.py` |
| [backtest/](backtest/) | バックテスト実行 + 結果分析 | `run_backtest.sh` `standard_analysis.py` `generate_markdown_report.py` `walk_forward_validation.py` `sl_pattern_analysis.py` |
| [deployment/](deployment/) | デプロイ補助（CI 経由が主・手動構築は廃止）| `docker-entrypoint.sh` `artifact-cleanup-policy.json` |
| [live/](live/) | ライブモード分析 + 取引履歴同期 | `standard_analysis.py` `sync_exit_records.py` |
| [ml/](ml/) | ML モデル学習・HMM レジーム学習 | `create_ml_models.py` `run_local_training.sh`（ローカル wrapper・caffeinate）`train_hmm_regime.py` |
| [paper/](paper/) | ペーパートレード起動・停止 | `run_paper.sh` |
| [testing/](testing/) | 品質チェック・ML 整合性検証 | `checks.sh`（統合品質ゲート 12 項目）`validate_ml_models.py` |

## 主要ワークフロー

### 1. 日常開発（必須）

```bash
# 品質チェック（開発前後・約 4 分）
bash scripts/testing/checks.sh
# 期待: 2426+ tests PASS / カバレッジ 73%+ / flake8 + black + isort PASS
```

### 2. ペーパートレード

```bash
bash scripts/paper/run_paper.sh         # 起動
bash scripts/paper/run_paper.sh stop    # 停止
bash scripts/paper/run_paper.sh status  # 状況確認
```

### 3. バックテスト

```bash
bash scripts/backtest/run_backtest.sh                # 基本実行
bash scripts/backtest/run_backtest.sh --days 30      # 30 日間
python3 scripts/backtest/standard_analysis.py --from-ci   # CI 結果分析
```

### 4. ML 学習

```bash
# CI: GitHub Actions（週次 + Drift 検知時 Auto Retraining）
gh workflow run model-training.yml --ref main -f n_trials=50

# ローカル: wrapper（caffeinate + n_jobs=-1 + 自動 backup）
bash scripts/ml/run_local_training.sh 50

# HMM レジーム学習
python3 scripts/ml/train_hmm_regime.py --days 365 --symbol BTC/JPY
```

### 5. ライブ運用分析

```bash
python3 scripts/live/standard_analysis.py --hours 24    # 24 時間統合診断
python3 scripts/live/sync_exit_records.py               # GCP ログから決済記録を税務 DB に同期
```

### 6. 事後分析

```bash
python3 scripts/analysis/unified_strategy_analyzer.py --mode theoretical  # 理論分析
python3 scripts/analysis/unified_strategy_analyzer.py --mode full         # 完全実証
python3 scripts/analysis/signal_simulation.py                              # シグナル事後検証
python3 scripts/analysis/full_entry_simulation.py                          # 真の運用シミュレーション（旧 sl_simulation.py の後継・母集団バイアス解消）
```

## 品質基準（Phase 90α・2026-05-18 時点）

| 指標 | 基準 |
|------|------|
| テスト成功率 | 100%（2426+ tests）|
| カバレッジ | **73%+** |
| コードスタイル | flake8 / black / isort PASS |
| 特徴量数 | **55**（Phase 89-β/γ/δ で 37→55） |
| 戦略数 | 6（レンジ型 4 + トレンド型 2）|
| 分類 | **2 クラス（success / failure）メタラベリング**（Phase 90α）|

## 整理方針

| 対象 | 整理ルール |
|---|---|
| `__pycache__/` | 自動生成・全削除可（.gitignore 対象）|
| `*.py` `*.sh` | 全て現役・参照確認後に削除判断 |
| サブフォルダ README | 各サブフォルダで個別維持（[テンプレ](README.md 参照)）|

整理ツール: `/organize-folder scripts/<sub>` で各サブフォルダを順次精査可能。

## 関連リンク

- 親 README: [../README.md](../README.md)
- 開発ガイド: [../CLAUDE.md](../CLAUDE.md)
- 統合運用ガイド: [../docs/運用ガイド/統合運用ガイド.md](../docs/運用ガイド/統合運用ガイド.md)

---

**最終更新**: 2026年5月18日（Phase 90α: 55 特徴量・2 クラスメタラベリング対応・全サブフォルダ実態反映）
