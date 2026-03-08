---
name: backtest-analysis
description: バックテスト結果を標準分析スクリプトで分析する。CIまたはローカルの結果を分析
allowed-tools: Bash, Read, Glob
argument-hint: [--from-ci | --local | <json_path>]
---

# Backtest Analysis

scripts/backtest/standard_analysis.py を使用してバックテスト結果を分析する。

## 手順

1. 引数に応じて分析を実行:
   - 引数なし or `--from-ci`: `python3 scripts/backtest/standard_analysis.py --from-ci`（CI最新結果を自動取得）
   - `--local`: `python3 scripts/backtest/standard_analysis.py --local`（ローカル最新結果）
   - ファイル指定: `python3 scripts/backtest/standard_analysis.py $ARGUMENTS`
2. 分析結果を以下の観点で報告:
   - 総損益・勝率・取引数
   - レジーム別パフォーマンス
   - 戦略別パフォーマンス
   - 最大ドローダウン
   - 平均ポジションサイズ
   - 改善提案（スクリプトが自動生成）

## 使用例

- `/backtest-analysis` - CI最新結果を分析
- `/backtest-analysis --from-ci` - 同上
- `/backtest-analysis --local` - ローカル結果を分析
- `/backtest-analysis results/backtest_result.json` - 指定ファイルを分析
