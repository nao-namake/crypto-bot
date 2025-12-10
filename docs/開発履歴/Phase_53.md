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

### 陳腐化テスト削除

**問題**: CI失敗（test_fetch_ohlcv_is_async）
- Phase 51.5-Cで15分足直接API実装に変更
- テストはccxt.fetch_ohlcv経由を想定（旧実装）

**対応**:
| ファイル | 変更内容 |
|----------|----------|
| tests/unit/data/test_bitbank_client_async.py | 削除（陳腐化） |

### checks.sh POSIX互換性修正

**問題**: CI環境（Ubuntu）で`grep -oP`が正常に動作しない

**対応**:
| ファイル | 変更内容 |
|----------|----------|
| scripts/testing/checks.sh | `grep -oP` → `grep -E/sed -E/awk`（POSIX互換） |

### 結果

- プロジェクト全体でPython 3.11に統一完了
- GitHub Workflows + Dockerfile + 設定ファイル全て3.11
- pandas-ta削除によりCI/バックテスト正常実行可能
- **CI成功確認**（Run ID: 20112992193、1247テスト、65.85%カバレッジ）

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

- **コミット**: `30731095`（pandas-ta・テスト・checks.sh修正後）
- **GitHub Actions Run ID**: 20112697329
- **パラメータ**: Phase 53.2、180日間、初期残高1万円
- **目標**: PF 1.25以上（Phase 52ロールバック済みのためPF 1.34相当を期待）
- **予想実行時間**: 約2時間30分

### 結果

- 全モードで初期残高1万円に統一完了
- 180日間バックテスト実行開始

---

## Phase 53.4: GCPライブモード4重大バグ修正

**実施日**: 2025年12月11日
**目的**: GCPライブモードで発生していた4つの重大バグを修正

### 発見経緯

GCPログ分析で以下のエラーを発見:
1. `'coroutine' object has no attribute 'keys'`
2. `'coroutine' object has no attribute 'get'`
3. `bitbank API エラー: 20001`（API認証失敗）
4. 証拠金不足（available=0円）

アーカイブ版Phase 53で修正済みだったが、Phase 52へのロールバック時に未反映だった。

### 修正内容

| # | エラー | ファイル | 修正内容 |
|---|--------|----------|----------|
| 1 | coroutine has no attribute 'keys' | orchestrator.py:546 | `fetch_balance()` → `await fetch_balance()` |
| 2 | coroutine has no attribute 'get' | live_trading_runner.py:136 | `fetch_balance()` → `await fetch_balance()` |
| 3 | API認証エラー 20001 | bitbank_client.py:1613 | GET署名に`/v1`プレフィックス追加 |
| 4 | フィールド名不正 | bitbank_client.py:1500-1527 | bitbank API仕様に準拠したフィールド名に修正 |

### 修正詳細

#### 1. await漏れ修正（orchestrator.py）

```python
# 修正前（誤り）
balance_data = bitbank_client.fetch_balance()

# 修正後（正しい）
balance_data = await bitbank_client.fetch_balance()
```

#### 2. await漏れ修正（live_trading_runner.py）

```python
# 修正前（誤り）
balance_data = client.fetch_balance()

# 修正後（正しい）
balance_data = await client.fetch_balance()
```

#### 3. GET署名に/v1プレフィックス追加

```python
# 修正前（誤り）
message = f"{nonce}{endpoint}"

# 修正後（正しい - bitbank API仕様準拠）
message = f"{nonce}/v1{endpoint}"
```

**根拠（bitbank公式API仕様）**:
- GETリクエスト署名形式: `{nonce}/v1{endpoint}`
- 例: `1696723200000/v1/user/margin/status`
- これが欠落するとエラー20001（API認証失敗）が発生

#### 4. bitbank APIフィールド名修正

```python
# 修正前（誤り）
margin_data = {
    "margin_ratio": response.get("data", {}).get("maintenance_margin_ratio"),
    "available_balance": response.get("data", {}).get("available_margin"),
    ...
}

# 修正後（bitbank API仕様準拠）
margin_data = {
    "margin_ratio": data.get("total_margin_balance_percentage"),
    "available_balances": data.get("available_balances", {}),
    "total_margin_balance": data.get("total_margin_balance"),
    "unrealized_pnl": data.get("margin_position_profit_loss"),
    "status": data.get("status"),
    "maintenance_margin": data.get("total_position_maintenance_margin"),
    ...
}
```

### テスト修正

await変更に伴い、テストのMockをAsyncMockに変更:

```python
# 修正前
mock_client = Mock()

# 修正後
mock_client = AsyncMock()
```

対象テスト:
- `test_get_actual_balance_live_mode_success`
- `test_get_actual_balance_live_mode_zero_balance`
- `test_get_actual_balance_api_error`

### 結果

- **テスト**: 1282テスト全成功（100%）
- **カバレッジ**: 65.42%
- **コード品質**: flake8・black・isort全てPASS
- **コミット**: `dd777010`
- **CI**: Run ID 20114848616（実行中）

### 教訓

ロールバック時は関連する修正も確実にチェックすること。アーカイブ版の開発履歴を参照することで、修正済みの内容を再発見できた。

---

## Phase 53.5: GCP稼働率向上修正

**実施日**: 2025年12月11日
**目的**: アーカイブ（Phase 53-60）から発見した未適用の稼働率改善修正を適用

### 発見経緯

ユーザーリクエストでアーカイブ版（Phase 53-60）の開発履歴を調査。
以下の稼働率改善修正がPhase 52ロールバック時に未反映であった:

| # | 問題 | アーカイブ記録 | 効果 |
|---|------|---------------|------|
| 1 | RandomForest n_jobs=-1 | Phase 53.1 | 稼働率33%→99% |
| 2 | signal.alarm(900) | Phase 53.2 | 15分超の安定稼働 |

### 修正内容

#### 1. RandomForest n_jobs修正（2箇所）

**ファイル**: `scripts/ml/create_ml_models.py`

**理由**: GCP Cloud RunのgVisor環境ではfork()が制限されており、n_jobs=-1（全CPU使用）でRandomForestがクラッシュする

```python
# 修正前
"n_jobs": -1,

# 修正後
"n_jobs": 1,  # GCP gVisor環境でのfork()制限対応
```

対象行: Line 192, Line 708

#### 2. 自動タイムアウト無効化

**ファイル**: `main.py`

**理由**: ライブトレードは無限ループで24時間稼働する設計。15分タイムアウトは矛盾

```python
# 修正前
signal.alarm(timeout_seconds)
print(f"⏰ 自動タイムアウト設定: {timeout_seconds}秒")

# 修正後
# signal.alarm(timeout_seconds)  # 無効化: ライブトレードは無限ループで24時間稼働する設計
print(f"⏰ 自動タイムアウト設定: 無効（24時間稼働モード）")
```

### 結果

- **テスト**: 1282テスト全成功（100%）
- **カバレッジ**: 65.42%
- **コード品質**: flake8・black・isort全てPASS
- **コミット**: `20b292af`
- **期待効果**: 稼働率66%改善（33%→99%）・24時間安定稼働

### 教訓

アーカイブ版の開発履歴を定期的に参照し、ロールバック時に失われた重要な修正を再発見することが重要。

---

## 今後の予定

### Phase 53.6以降（検討中）
- GCPデプロイ・ログ監視で修正効果確認
- 稼働率99%維持の検証

---

**最終更新**: 2025年12月11日
