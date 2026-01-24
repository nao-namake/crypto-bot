# scripts/backtest/ - バックテストシステム

**Phase 61** - バックテスト実行・分析・検証ツール

---

## ファイル構成

```
scripts/backtest/
├── README.md                      # このファイル
├── run_backtest.sh                # ローカルバックテスト実行
├── standard_analysis.py           # 標準分析（84項目・CI連携）
├── generate_markdown_report.py    # Markdownレポート生成
└── walk_forward_validation.py     # Walk-Forward検証（過学習検出）
```

---

## 各スクリプトの役割

### run_backtest.sh

**ローカルバックテスト実行スクリプト**

```bash
# 基本実行（設定ファイル参照）
bash scripts/backtest/run_backtest.sh

# 日数指定
bash scripts/backtest/run_backtest.sh --days 60

# 固定期間指定
bash scripts/backtest/run_backtest.sh --start 2025-07-01 --end 2025-12-31

# 既存CSV使用（高速）
bash scripts/backtest/run_backtest.sh --skip-collect
```

**処理フロー**:
1. CSVデータ収集（Bitbank API）
2. バックテスト実行
3. Markdownレポート生成
4. 結果をdocs/検証記録/に保存

---

### standard_analysis.py

**標準分析スクリプト（84項目固定指標）**

```bash
# CIの最新結果を分析
python3 scripts/backtest/standard_analysis.py --from-ci

# Phase指定付き
python3 scripts/backtest/standard_analysis.py --from-ci --phase 61

# ローカル結果を分析
python3 scripts/backtest/standard_analysis.py --local

# 特定ファイルを分析
python3 scripts/backtest/standard_analysis.py <json_path>
```

**出力**:
- コンソール: サマリー表示
- JSON: `docs/検証記録/analysis_*.json`
- Markdown: `docs/検証記録/analysis_*.md`
- CSV: `docs/検証記録/analysis_history.csv`（履歴追記）

---

### generate_markdown_report.py

**JSONレポート→Markdown変換**

```bash
python3 scripts/backtest/generate_markdown_report.py <json_path>
```

**機能**:
- 日毎損益分析
- ASCII損益曲線
- 月別パフォーマンス
- 戦略×レジーム クロス集計

**使用箇所**: `run_backtest.sh`およびCI（backtest.yml）から自動呼び出し

---

### walk_forward_validation.py

**Walk-Forward検証（過学習検出）**

```bash
# ローカル実行（数時間かかる）
python3 scripts/backtest/walk_forward_validation.py

# ドライラン（ウィンドウ確認のみ）
python3 scripts/backtest/walk_forward_validation.py --dry-run

# CIの最新結果を分析
python3 scripts/backtest/walk_forward_validation.py --from-ci
```

**機能**:
- ローリングウィンドウ方式で訓練・テスト分離
- 各ウィンドウでMLモデル訓練→バックテスト
- 安定性評価（PF標準偏差、過学習リスク判定）

**設定ファイル**: `config/core/wf_config.yaml`

---

## CI連携

| スクリプト | CI結果取得 | 用途 |
|-----------|-----------|------|
| `standard_analysis.py --from-ci` | backtest.yml | バックテスト結果分析 |
| `walk_forward_validation.py --from-ci` | walk_forward.yml | WF結果分析 |

---

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `src/backtest/engine.py` | バックテストエンジン |
| `src/backtest/trade_tracker.py` | 取引ペアリング・損益計算 |
| `config/core/thresholds.yaml` | TP/SL・レジーム設定 |
| `.github/workflows/backtest.yml` | CIバックテスト |
| `.github/workflows/walk_forward.yml` | CI Walk-Forward検証 |

---

**最終更新**: 2026年1月24日 - Phase 61
