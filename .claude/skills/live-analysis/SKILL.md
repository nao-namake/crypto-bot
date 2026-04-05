---
name: live-analysis
description: ライブ取引の成果を統合診断する。アカウント・ポジション・取引履歴・インフラ・Bot機能を一括分析
allowed-tools: Bash, Read
argument-hint: [--hours N | --quick]
---

# Live Trading Analysis

scripts/live/standard_analysis.py を使用してライブ運用を統合診断する。

## 手順

1. 引数に応じて分析を実行:
   - 引数なし: `python3 scripts/live/standard_analysis.py`（デフォルト24時間・全診断）
   - 時間指定: `python3 scripts/live/standard_analysis.py --hours $0`
   - クイック: `python3 scripts/live/standard_analysis.py --quick`（GCPログのみ・API呼出なし）
2. 分析結果を以下の観点で報告:
   - アカウント・ポジション・取引履歴
   - Cloud Run稼働状況・Container安定性
   - 37特徴量・ML予測・6戦略動作確認
   - TP/SL管理・SL超過チェック・緊急決済
   - Maker戦略・設定値検証
   - Silent Failure検出
   - 改善提案（あれば）
3. 終了コードを確認:
   - 0: 正常
   - 1: 致命的問題（即座対応必須）
   - 2: 要注意（詳細診断推奨）
   - 3: 監視継続（軽微な問題）

## 使用例

- `/live-analysis` - 直近24時間・全診断
- `/live-analysis --hours 48` - 直近48時間
- `/live-analysis --quick` - GCPログのみ簡易チェック
