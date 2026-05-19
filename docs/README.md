# docs/

プロジェクトのドキュメント集約フォルダ。運用ガイド・開発履歴・開発計画・検証記録の 4 カテゴリ。

## サブフォルダ

| サブフォルダ | 役割 | 主要ファイル |
|---|---|---|
| [運用ガイド/](運用ガイド/) | 本番運用・GCP・API・税務の手順書 | `統合運用ガイド.md`（Auto Retraining セットアップ + N-BEATS rollback を内包） `GCP運用ガイド.md` `bitbank_APIリファレンス.md` `税務対応ガイド.md` `システムリファレンス.md` |
| [開発計画/](開発計画/) | 開発計画・ToDo | `ToDo.md`（セッション再開時の最優先タスク） |
| [開発履歴/](開発履歴/) | Phase 別の実装記録 | `SUMMARY.md`（全 Phase 総括）+ `Phase_01-10.md` ～ `Phase_90.md`（47 ファイル） |
| [検証記録/](検証記録/) | バックテスト・ライブ分析の出力先 | `analysis_history.csv`（履歴累積）+ `live/`（直近 1 週間のライブ分析）+ `walk_forward/`（WF 検証出力）+ `ci_downloads/`（CI 成果物 DL 先） |

## ファイル生成・保全方針

### git tracked（永続）
- `運用ガイド/*.md` — 運用ドキュメント
- `開発計画/ToDo.md` — 開発計画
- `開発履歴/*.md` — Phase 記録

### git ignored（実行時生成・整理対象）
`.gitignore:108-111` で除外:
- `docs/検証記録/live/` — `scripts/live/standard_analysis.py` 出力
- `docs/検証記録/analysis_*.json` / `analysis_*.md` — `scripts/backtest/standard_analysis.py` 出力
- `docs/検証記録/analysis_history.csv` — 履歴 CSV（蓄積用・整理対象外）

整理ツール: `/organize-folder docs/検証記録` で過去出力を承認制クリーンアップ。

## セッション再開時の参照順

1. **`../CLAUDE.md` しおりセクション**（現在地把握）
2. **[開発計画/ToDo.md](開発計画/ToDo.md)** セッション再開手順
3. 該当 Phase の **[開発履歴/Phase_NN.md](開発履歴/)**
4. 運用に関わるときは **[運用ガイド/統合運用ガイド.md](運用ガイド/統合運用ガイド.md)**

## 関連リンク

- 親 README: [../README.md](../README.md)
- 開発ガイド: [../CLAUDE.md](../CLAUDE.md)
