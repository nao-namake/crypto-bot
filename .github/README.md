# .github/

GitHub Actions CI/CD ワークフローの集約。リポジトリ運営の自動化（テスト・デプロイ・ML 学習・バックテスト・リソース管理・緊急停止）を担う。

## サブフォルダ

| サブフォルダ | 役割 |
|---|---|
| [workflows/](workflows/) | GitHub Actions ワークフロー定義（6 ファイル）|

詳細は [workflows/README.md](workflows/README.md) 参照。

## 整理方針

- **`.github/workflows/*.yml` は整理対象外**（CI 直結・変更は厳禁）
- README 更新のみ可（実体ファイルへの記述追加・削除）
- ワークフロー追加・削除は別途独立タスクとして扱う

## 関連リンク

- 親 README: [../README.md](../README.md)
- CLAUDE.md: [../CLAUDE.md](../CLAUDE.md)
- 統合運用ガイド: [../docs/運用ガイド/統合運用ガイド.md](../docs/運用ガイド/統合運用ガイド.md)
