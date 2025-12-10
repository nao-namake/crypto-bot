# Phase 53 開発履歴

**開始日**: 2025年12月11日
**ベース**: Phase 52（PF 1.34、勝率51.4%）
**方針**: 戦略・取引ロジックは維持し、周辺機能を強化

---

## Phase 53.1: GitHub Actions改修・フォルダ整理

**実施日**: 2025年12月11日
**目的**: アーカイブ版Phase 53の改善をmainブランチに取り込み

### 実施内容

#### 1. docsフォルダリネーム

| 変更前 | 変更後 |
|--------|--------|
| docs/バックテスト記録 | docs/検証記録 |
| docs/運用手順 | docs/運用ガイド |
| docs/稼働チェック | docs/運用監視 |

#### 2. GitHub Actionsワークフロー改修

| ファイル | 変更内容 |
|----------|----------|
| backtest.yml | weekly_backtest.yml からリネーム・完全手動制（スケジュール削除）・Python 3.11 |
| cleanup.yml | 月次実行（第1日曜日）・SHA256ダイジェストベース削除・--delete-tags追加 |
| model-training.yml | 簡素化（334→135行）・データ収集ステップ追加・Python 3.11 |
| weekly-report.yml | weekly_report.yml からリネーム・Cloud Storage統合・Python 3.11 |
| emergency-stop.yml | 新規作成・iPhoneワンタップ緊急停止対応・stop/resume/status |
| ci.yml | paths-ignore削除・Python 3.11統一・特徴量数55固定 |

#### 3. ドキュメント整理（運用ガイド統合）

| 変更前 | 変更後 |
|--------|--------|
| `docs/運用ガイド/bitbank API.md` | 削除 |
| `docs/開発計画/GCPクリーンアップ指示.md` | 削除 |
| `docs/運用ガイド/GCP権限.md` | 削除 |
| `docs/開発計画/要件定義.md` | 削除 |
| - | `docs/運用ガイド/bitbank_APIリファレンス.md`（新規作成） |
| - | `docs/運用ガイド/GCP運用ガイド.md`（新規作成・IAM権限統合） |
| - | `docs/運用ガイド/システム要件定義.md`（新規作成） |
| - | `docs/運用ガイド/システム機能一覧.md`（新規作成） |

**bitbank_APIリファレンス.md**:
- GET署名に`/v1`プレフィックス必須を明記
- エラーコード20001（署名不正）追加
- 目次追加・絵文字削除

**GCP運用ガイド.md**:
- IAM権限管理（サービスアカウント・権限マトリックス・禁止権限）
- リソース管理・クリーンアップ（安全/完全/デプロイ前の3方式）
- 絵文字削除・シンプル化

**システム要件定義.md**:
- 目次追加（6セクション）
- Python 3.11明記（GCP gVisor互換性）
- 絵文字削除・シンプル化

**システム機能一覧.md**:
- 11セクション構成（コア機能・取引・リスク管理・ML・戦略・市場分析・税務・バックテスト等）
- アンサンブル重み更新（50/30/20）
- 設定ファイル早見表・実装ファイル一覧付録

#### 4. ci.yml詳細変更

| 項目 | 変更前（Phase 52） | 変更後（Phase 53.1） |
|------|-------------------|---------------------|
| paths-ignore | あり（多数） | 削除（簡素化） |
| Python | 3.13 | 3.11（GCP gVisor安定性） |
| 特徴量数 | 動的取得（feature_manager） | 55固定（CI環境安定性） |
| Phase番号 | 52.4 | 53.1 |

### 技術的判断

**Python 3.11を選択した理由**:
- GCP Cloud RunのgVisor環境での安定性
- Phase 53アーカイブで実績あり（稼働率33%→99%）

**特徴量数55固定を選択した理由**:
- CI環境ではfeature_managerのimportが失敗する可能性
- テスト用メタデータ作成のみなので固定値で十分
- 実際のモデル訓練・推論は本番コードで動的処理

**paths-ignoreを削除した理由**:
- 簡素化・すべての変更でCIを実行する方が安全
- ドキュメント変更のみでもテストを実行して品質担保

### 結果

- GitHub Actionsワークフロー6ファイル改修完了
- docsフォルダ3ディレクトリリネーム完了
- ドキュメント整理完了（運用ガイド4ファイル新規作成・旧ファイル4件削除）
- Phase 53.1基盤整備完了

---

## Phase 53.2: Python 3.11統一・pandas-ta削除

**実施日**: 2025年12月11日
**目的**: プロジェクト全体をPython 3.11に統一（GCP gVisor安定性）

### GCP互換性確認

- Python 3.11はGCP Cloud RunでGA（General Availability）サポート
- gVisor環境での安定性が確認済み（Phase 53アーカイブで実績あり：稼働率33%→99%）

### 変更内容

| ファイル | 変更前 | 変更後 |
|----------|--------|--------|
| Dockerfile | `python:3.13-slim-bullseye` | `python:3.11-slim-bullseye` |
| pyproject.toml | `requires-python = ">=3.13"` | `requires-python = ">=3.11"` |
| pyproject.toml | `target-version = ["py313"]` | `target-version = ["py311"]` |
| mypy.ini | `python_version = 3.13` | `python_version = 3.11` |
| CLAUDE.md | `Python 3.13・MLライブラリ互換性` | `Python 3.11・GCP gVisor安定性` |

### pandas-ta削除（CI/バックテスト失敗修正）

**問題**: CI/バックテストが`pandas-ta>=0.3.14b0`インストール失敗で停止
- pandas-ta 0.4.x系はPython >=3.12必須
- 0.3.14b0はPyPIに存在せず

**調査結果**: pandas-taはコードベースで未使用（importなし）

**対応**:
| ファイル | 変更内容 |
|----------|----------|
| requirements.txt | `pandas-ta>=0.3.14b0` 削除 |
| requirements.txt | ヘッダー更新（v53・2025年12月） |

### 結果

- プロジェクト全体でPython 3.11に統一完了
- GitHub Workflows + Dockerfile + 設定ファイル全て3.11
- pandas-ta削除によりCI/バックテスト正常実行可能

---

## Phase 53.3: バックテスト初期残高統一

**実施日**: 2025年12月11日
**目的**: バックテスト初期残高を1万円に統一し、全モード統一

### 調査結果

| モード | 変更前 | 変更後 |
|--------|--------|--------|
| paper | 10,000円 | 10,000円（変更なし） |
| live | 10,000円 | 10,000円（変更なし） |
| **backtest** | **100,000円** | **10,000円** |

### 変更内容

| ファイル | 変更箇所 |
|----------|----------|
| config/core/unified.yaml | `mode_balances.backtest.initial_balance: 100000.0` → `10000.0` |
| src/core/execution/backtest_runner.py | フォールバック値 `100000.0` → `10000.0` |

### バックテスト実行

- **コミット**: `bc41ba87`
- **GitHub Actions Run ID**: 20112043050
- **パラメータ**: Phase 53.3、180日間、初期残高1万円
- **目標**: PF 1.25以上（Phase 52ロールバック済みのためPF 1.34相当を期待）
- **予想実行時間**: 約2時間30分

### 結果

- 全モードで初期残高1万円に統一完了
- 180日間バックテスト実行開始

---

## 今後の予定

### Phase 53.4以降（検討中）
- GCP安定稼働修正（n_jobs=1・API署名・タイムアウト無効化）
- その他アーカイブ版Phase 53の改善取り込み

---

**最終更新**: 2025年12月11日
