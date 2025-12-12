# Phase 52 開発記録

**期間**: 2025/11/12 - 2025/12/13
**状況**: ✅ **Phase 52完了**（Phase 52.0-52.2）

---

## 📋 Phase 52 概要

### 目的
- **Phase 52.0**: レジームベース動的TP/SL実装（市場状況に応じた最適なTP/SL配置）
- **Phase 52.1**: 週次バックテスト自動化（GitHub Actions・Markdownレポート生成）
- **Phase 52.2**: GitHub Actionsワークフロー整理・緊急停止機能追加

### 背景
**Phase 51.10-B問題点**:
- バックテスト結果: +5.47%収益・-29.84%最大ドローダウン
- 本番環境: -20%で取引停止（DrawdownManager制限）
- **矛盾**: バックテストで-29.84%まで損失を許容しているが、本番では-20%で停止
- **影響**: バックテスト結果が本番環境で再現不可能

### Phase 52.1実績（2025/11/12）
| 指標 | 値 |
|------|-----|
| PF | **1.34** |
| エントリー数 | **716件** |
| 勝率 | 49.7% |
| 最大DD | 0.37% |
| リスクリワード比 | 1.28:1 |

---

## 🎯 Phase 52.0: レジームベース動的TP/SL【実装済み】

### 実装内容

#### 1. thresholds.yaml設定
**ファイル**: `config/core/thresholds.yaml`

```yaml
# レジーム別TP設定（Line 595-604）
take_profit:
  regime_based:
    tight_range:
      min_profit_ratio: 0.008   # TP 0.8%
    normal_range:
      min_profit_ratio: 0.010   # TP 1.0%
    trending:
      min_profit_ratio: 0.015   # TP 1.5%

# レジーム別SL設定（Line 626-631）
stop_loss:
  regime_based:
    tight_range:
      max_loss_ratio: 0.006     # SL 0.6%
    normal_range:
      max_loss_ratio: 0.007     # SL 0.7%
    trending:
      max_loss_ratio: 0.010     # SL 1.0%
```

#### 2. strategy_utils.py実装
**ファイル**: `src/strategies/utils/strategy_utils.py` (Line 200-234)

```python
# Phase 52.0: レジーム別TP/SL設定の適用
if regime and get_threshold("position_management.take_profit.regime_based.enabled", False):
    # レジーム別TP設定取得
    regime_tp = get_threshold(
        f"position_management.take_profit.regime_based.{regime}.min_profit_ratio", None
    )
    # レジーム別SL設定取得
    regime_sl = get_threshold(
        f"position_management.stop_loss.regime_based.{regime}.max_loss_ratio", None
    )

    if regime_tp and regime_sl:
        config["min_profit_ratio"] = regime_tp
        config["max_loss_ratio"] = regime_sl
        logger.info(f"🎯 Phase 52.0: レジーム別TP/SL適用 - {regime}")
```

### レジーム別設定サマリー

| レジーム | TP | SL | RR比 | 用途 |
|---------|-----|-----|------|------|
| tight_range | 0.8% | 0.6% | 1.33:1 | レンジ相場・こまめ利確 |
| normal_range | 1.0% | 0.7% | 1.43:1 | 通常相場・標準設定 |
| trending | 1.5% | 1.0% | 1.50:1 | トレンド相場・利益最大化 |

---

## 🤖 Phase 52.1: 週次バックテスト自動化【実装済み】

### 実装内容

#### 1. GitHub Actionsワークフロー
**ファイル**: `.github/workflows/backtest.yml`（手動実行専用）

**機能**:
- 手動実行（workflow_dispatch）
- Phase名・バックテスト日数の入力パラメータ
- 履歴データ自動収集（15分足・4時間足）
- バックテスト実行（タイムアウト5時間）
- Markdownレポート生成・Git自動コミット

**実行ステップ**:
1. コードチェックアウト
2. Python 3.13環境セットアップ
3. 依存関係インストール
4. **履歴データ収集**（Phase 52.1追加）
5. バックテスト環境準備
6. バックテスト実行
7. Markdownレポート生成
8. Git設定・コミット・プッシュ

#### 2. Markdownレポート生成スクリプト
**ファイル**: `scripts/backtest/generate_markdown_report.py`

**機能**:
- JSONレポート → Phase 51.10-B形式Markdown変換
- フォーマット:
  - 実行概要（期間・データソース・初期残高）
  - エントリー統計（総数・勝率・勝ち/負け数）
  - レジーム別パフォーマンス
  - パフォーマンス指標（損益・PF・DD・リスクリワード）
  - 自動結論生成

**出力先**: `docs/バックテスト記録/Phase_{phase_name}_{YYYYMMDD}.md`

#### 3. 手動実行方法
```bash
# Phase名・日数指定で手動実行
gh workflow run backtest.yml -f phase_name="52.1" -f backtest_days=180

# 実行状況確認
gh run list --workflow=backtest.yml --limit=5

# ログ確認
gh run view <RUN_ID> --log
```

---

## 🔄 Phase 52.1 ロールバック記録（2025/12/13）

### ロールバック理由

Phase 53-60で発生したパフォーマンス悪化を解消するため、安定稼働していたPhase 52.1に戻した。

#### パフォーマンス悪化の経緯

| 日付 | Phase | PF | エントリー数 | 問題 |
|------|-------|-----|------------|------|
| 2025/11/12 | **Phase 52.1** | **1.34** | **716件** | 安定稼働（ベースライン） |
| 2025/12/07 | Phase 53-60 | 1.00 | - | PF悪化 → Phase 52にロールバック |
| 2025/12/10 | Phase 53 | 1.03 | - | 同一期間比較でPF悪化（1.27→1.03） |
| 2025/12/13 | Phase 53.8 | - | **15件** | エントリー716件→15件に激減 |

#### 根本原因分析

Phase 53-60で追加された以下の変更がパフォーマンスを悪化させた：

| 変更内容 | 問題 |
|---------|------|
| トレンドフィルター追加 | バックテストで効果なし（削除済み） |
| 戦略条件緩和（AND→OR） | 発火増・精度低下 |
| MeanReversion追加 | Phase 52に存在しない戦略 |
| TP/SL変更（0.8%→1.5%） | TP到達率低下 |

### ロールバック実施内容

#### 1. Phase 53.8アーカイブ作成
```
archive/phase53.8_backup_20251213/
├── config/           # 設定ファイル
├── src/              # ソースコード
├── scripts/          # スクリプト
├── tests/            # テスト
├── models/           # MLモデル
├── CLAUDE.md         # 開発ガイド
└── requirements.txt  # 依存関係
```

#### 2. Phase 52.1完全復元
- **復元コミット**: `6afa3244`
- **復元コマンド**: `git checkout 6afa3244 -- .`

#### 3. 復元後の調整
- **feature_flagsインポートエラー修正**: 存在しない`feature_flags`モジュールを既存の`get_features_config()`で代替
- **flake8エラー修正**: E226（算術演算子スペース）
- **blackフォーマット修正**: 2ファイル

### 実装確認結果（2025/12/13）

| 機能 | ファイル | 状態 |
|------|---------|------|
| レジーム別TP/SL設定 | `config/core/thresholds.yaml` | ✅ 実装済み |
| レジーム別TP/SL適用 | `src/strategies/utils/strategy_utils.py` | ✅ 実装済み |
| バックテストワークフロー | `.github/workflows/backtest.yml` | ✅ 実装済み |
| Markdownレポート生成 | `scripts/backtest/generate_markdown_report.py` | ✅ 実装済み |

---

## 📊 現在の実装状態まとめ

### 実装済み機能（Phase 52.0-52.1）

1. **Phase 52.0: レジームベース動的TP/SL**
   - `config/core/thresholds.yaml`: レジーム別TP/SL設定
   - `src/strategies/utils/strategy_utils.py`: レジーム別TP/SL適用ロジック

2. **Phase 52.1: バックテスト自動化（手動実行）**
   - `.github/workflows/backtest.yml`: GitHub Actions（手動実行）
   - `scripts/backtest/generate_markdown_report.py`: Markdownレポート生成

3. **6戦略・55特徴量システム**
   - レンジ型: ATRBased, DonchianChannel, BBReversal
   - トレンド型: ADXTrendStrength, StochasticReversal, MACDEMACrossover
   - 3モデルアンサンブル: LightGBM 50% + XGBoost 30% + RandomForest 20%

---

## 🔧 Phase 52.2: GitHub Actionsワークフロー整理【実装済み】

### 実施日
2025年12月13日

### 実装内容

#### 1. ワークフロー更新（6ファイル）

| ファイル | 変更内容 |
|---------|---------|
| `ci.yml` | Phase 52.2参照・55特徴量対応 |
| `model-training.yml` | データ収集ステップ追加・MIN_FEATURE_COUNT環境変数・331→208行に簡略化 |
| `backtest.yml` | リネーム（weekly_backtest.yml→backtest.yml）・手動実行専用 |
| `cleanup.yml` | SHA256ダイジェストベース削除・月次スケジュール・環境変数化 |
| `weekly_report.yml` | Cloud Storage統合・BUCKET_NAME/DB_PATH環境変数 |
| `emergency-stop.yml` | **新規追加** - iPhoneワンタップ緊急停止/復旧 |

#### 2. 緊急停止機能（emergency-stop.yml）

**アクション**:
- `stop`: トラフィック0%（即時停止・復旧簡単）
- `resume`: トラフィック100%（復旧）
- `status`: 状態確認のみ

**使い方**: iPhoneのGitHubアプリ → Actions → 🚨 Emergency Stop → Run workflow

#### 3. 環境変数によるマジックナンバー排除

| ワークフロー | 環境変数 |
|------------|---------|
| model-training.yml | `MIN_FEATURE_COUNT: 50` |
| cleanup.yml | `IMAGE_RETENTION_COUNT: 5`, `REVISION_RETENTION_COUNT: 3` |
| weekly_report.yml | `BUCKET_NAME: crypto-bot-trade-data`, `DB_PATH: tax/trade_history.db` |

#### 4. README.md更新
- 6ワークフロー構成に更新
- 手動実行コマンド追加
- Phase 52.2改善点を記載

---

## ⚠️ Phase 53で適用予定の必須修正（GCP稼働に必要）

Phase 53以降で発見・修正されたGCPバグを適用する必要がある：

### 1. RandomForest n_jobs修正（稼働率33%→99%）
- **問題**: GCP gVisorでfork()制限によりクラッシュ
- **修正**: `scripts/ml/create_ml_models.py` - `n_jobs=-1` → `n_jobs=1`
- **備考**: モデル再訓練が必要

### 2. 自動タイムアウト無効化（15分毎の再起動防止）
- **問題**: signal.alarm(900)で15分後にシステム終了
- **修正**: `main.py` - signal.alarm無効化

### 3. bitbank API署名修正（エラー20001解消）
- **問題**: GETリクエスト署名に/v1プレフィックス欠落
- **修正**: `src/data/bitbank_client.py:1592` - `{nonce}/v1{endpoint}`

### 4. await漏れ修正（0エントリー問題解消）
- **問題**: 非同期メソッドのawait漏れ
- **修正**:
  - `orchestrator.py:546` - `await bitbank_client.fetch_balance()`
  - `live_trading_runner.py:136` - `await self.bitbank_client.fetch_balance()`

### 5. 証拠金キー名修正（0エントリー問題解消）
- **問題**: bitbank API仕様と異なるフィールド名
- **修正**: `bitbank_client.py:1483-1527` - APIレスポンスキー名統一

### 6. SMOTEオプション追加（推奨）
- **問題**: 訓練データのクラス不均衡（HOLD 92.1%）
- **修正**: `.github/workflows/model-training.yml` - `--smote`追加

---

## 🧪 バックテスト検証

### 検証実行（2025/12/13）
- **GitHub Actions Run ID**: 20179512143
- **期間**: 180日間
- **ステータス**: 実行中

### 期待結果
| 指標 | 目標 | Phase 52.1実績（2025/11/12） |
|------|------|------------------------------|
| PF | ≥1.25 | 1.27-1.34 |
| エントリー数 | ≥700件 | 716件 |
| 勝率 | ~50% | 49.7% |

### 検証チェックリスト
- [ ] バックテストPF ≥ 1.25
- [ ] バックテストエントリー数 ≥ 700件
- [ ] 必須修正1-5適用完了
- [ ] モデル再訓練（n_jobs=1）
- [ ] GCPデプロイ成功
- [ ] GCP稼働率 ≥ 99%
- [ ] APIエラー20001なし

---

## 📁 参考: アーカイブ一覧

| アーカイブ | 日付 | 内容 |
|-----------|------|------|
| `archive/phase60_20251207/` | 2025/12/07 | Phase 53-60（PF悪化） |
| `archive/phase53.8_backup_20251213/` | 2025/12/13 | Phase 53.8（エントリー激減） |

---

**📅 最終更新**: 2025年12月13日
**✅ ステータス**: Phase 52完了（Phase 52.0-52.2）・Phase 53で必須修正適用予定
