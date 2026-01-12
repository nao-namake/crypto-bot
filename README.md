# Crypto-Bot - AI自動取引システム

**Phase 58.8完了・bitbank BTC/JPY専用・GCP本番稼働中**

[![Tests](https://img.shields.io/badge/tests-passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-64%25%2B-green)](coverage-reports/)
[![Phase](https://img.shields.io/badge/Phase%2058.8-Complete-blue)](docs/)

---

## クイックスタート

### ローカル実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境設定
cp config/secrets/.env.example config/secrets/.env
# → .envにbitbank API・Discord Webhook設定

# 品質チェック
bash scripts/testing/checks.sh  # 全テスト成功・64%+カバレッジ

# 実行
bash scripts/management/run_safe.sh local paper  # ペーパートレード
bash scripts/management/run_safe.sh local live   # ライブトレード
```

### GCP確認

```bash
# 稼働状況
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 --format="value(status.conditions[0].status,status.url)"

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

---

## システム概要

AI自動取引システムは、**bitbank信用取引専用のBTC/JPY自動取引ボット**です。

**6つの取引戦略**と**機械学習**を統合し、**55の特徴量**を総合分析することで24時間自動取引を実現。**真の3クラス分類**（BUY/HOLD/SELL）と**レジーム別動的戦略選択**により、市場状況に適応した取引を行います。

### 運用仕様

| 項目 | 値 |
|------|-----|
| **対象市場** | bitbank信用取引・BTC/JPY専用 |
| **資金規模** | 1万円スタート → 最大50万円 |
| **取引頻度** | 月100-200回・5分間隔実行 |
| **稼働体制** | 24時間・GCP Cloud Run |
| **月額コスト** | 700-900円 |

### 6戦略構成（Phase 55.2更新）

| 区分 | 戦略名 | 核心ロジック | 60日PF |
|------|--------|-------------|--------|
| **レンジ型** | BBReversal | BB上下限タッチ + RSI極端値 → 平均回帰 | 1.32 |
| **レンジ型** | StochasticDivergence | 価格とStochasticの乖離検出 → 反転 | 1.25 |
| **レンジ型** | ATRBased | ATR消尽率70%以上 → 反転期待 | 1.16 |
| **レンジ型** | DonchianChannel | チャネル端部反転（無効化） | 0.85 |
| **トレンド型** | MACDEMACrossover | MACDクロス + EMAトレンド確認 | 1.50 |
| **トレンド型** | ADXTrendStrength | ADX≥25 + DIクロス → トレンドフォロー | 1.01 |

### タイトレンジ重みづけ（Phase 55.2）

| 戦略 | 重み | 理由 |
|------|------|------|
| BBReversal | 0.40 | PF 1.32・タイトレンジ特化 |
| StochasticDivergence | 0.35 | PF 1.25・Divergence検出 |
| ATRBased | 0.25 | PF 1.16・消尽率ロジック |
| トレンド型 | 0.0 | タイトレンジで機能しない |

### レジーム別TP/SL設定（Phase 58.5/58.6更新）

| レジーム | 平日TP | 平日SL | 土日TP | 土日SL |
|---------|--------|--------|--------|--------|
| tight_range | 0.4% | 0.3% | 0.25% | 0.2% |
| normal_range | 0.6% | 0.4% | 0.4% | 0.25% |
| trending | 1.0% | 0.6% | 0.6% | 0.4% |

**土日縮小根拠**: 半年分CSV分析で土日ATRは平日の65%

---

## 主要機能

### AI取引システム

- **6戦略統合**: レンジ型4 + トレンド型2・Registry Pattern
- **動的戦略選択**: レジーム別重みづけ自動適用
- **55特徴量**: 49基本 + 6戦略シグナル
- **真の3クラス分類**: BUY / HOLD / SELL直接予測
- **3モデルアンサンブル**: LightGBM 50% / XGBoost 30% / RandomForest 20%
- **Graceful Degradation**: ensemble_full.pkl → ensemble_basic.pkl → DummyModel

### リスク管理

- **レジーム別動的TP/SL**: 市場状況に応じた自動調整
- **適応型ATR**: ボラティリティ別SL調整（低2.5x / 通常2.0x / 高1.5x）
- **完全指値オンリー**: 年間¥150,000削減・約定率90-95%
- **証拠金維持率80%遵守**: API直接取得・過剰レバレッジ防止

### 運用監視

- **24時間稼働**: GCP Cloud Run・ゼロダウンタイム
- **週間レポート**: Discord通知・損益曲線グラフ
- **確定申告システム**: SQLite取引記録・移動平均法

---

## システムアーキテクチャ

```
レイヤードアーキテクチャ設計
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Data Layer     │───▶│ Feature Layer   │───▶│ Strategy Layer  │
│  (Bitbank API)  │    │ (15 Indicators) │    │ (6 Strategies)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ML Layer       │───▶│ Risk Layer      │───▶│ExecutionService │
│ (3 Model Ens.)  │    │ (Kelly Crit.)   │    │(BitbankClient)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### ディレクトリ構成

```
src/
├── core/           # 基盤システム（設定・実行制御・レポート）
├── data/           # データ層（Bitbank API・キャッシュ）
├── features/       # 特徴量生成（15指標）
├── strategies/     # 6戦略（Registry Pattern）
├── ml/             # ML統合（3モデルアンサンブル）
├── trading/        # 取引管理層（5層アーキテクチャ）
├── backtest/       # バックテストシステム
└── monitoring/     # 週間レポート

tax/                # 確定申告システム
scripts/            # 運用スクリプト
config/core/        # 設定ファイル群
models/production/  # MLモデル（週次更新）
```

---

## 技術スタック

### 言語・フレームワーク

- **Python 3.13**: MLライブラリ互換性最適化
- **ccxt**: bitbank API統合・信用取引対応
- **pandas/numpy**: データ処理・特徴量生成
- **scikit-learn/XGBoost/LightGBM**: 機械学習モデル

### インフラストラクチャ（GCP）

- **Cloud Run**: 24時間稼働・1Gi・1CPU
- **Secret Manager**: API認証情報管理
- **Artifact Registry**: Dockerイメージ管理
- **Cloud Logging**: ログ管理・JST時刻対応

### CI/CD・品質管理

- **GitHub Actions**: 自動テスト・週次ML学習・デプロイ
- **pytest**: 全テスト成功
- **coverage**: 64%以上
- **flake8/black/isort**: コード品質統一

---

## 設定・カスタマイズ

### 設定ファイル

```
config/core/
├── unified.yaml      # 統合設定（残高・実行間隔）
├── thresholds.yaml   # 閾値・パラメータ（ML統合・レジーム別重み・TP/SL）
├── features.yaml     # 機能トグル
└── feature_order.json # 特徴量定義
```

### 実行モード

- **paper**: ペーパートレード（検証用）
- **live**: ライブトレード（本番取引）
- **backtest**: バックテスト（戦略検証）

---

## ドキュメント

### 開発者向け

- **[CLAUDE.md](CLAUDE.md)**: 開発ガイド・品質基準・Phase 57計画
- **[ToDo.md](docs/開発計画/ToDo.md)**: 開発計画・タスク管理

### 運用者向け

- **[統合運用ガイド](docs/運用ガイド/統合運用ガイド.md)**: デプロイ・監視・トラブル対応
- **[GCP運用ガイド](docs/運用ガイド/GCP運用ガイド.md)**: IAM権限・リソース管理
- **[システム機能一覧](docs/運用ガイド/システム機能一覧.md)**: 実装機能リファレンス
- **[開発履歴サマリー](docs/開発履歴/SUMMARY.md)**: Phase 1-53総括

---

## 開発状況

### Phase 58（完了）: TP/SL管理・運用安定化

| Phase | 内容 | 成果 |
|-------|------|------|
| 58.1-58.3 | TP/SL管理バグ修正 | 決済注文発行・保護ロジック・ポジション同期 |
| 58.4 | API修正 | fetch_margin_positions GETメソッド修正 |
| 58.5 | TP/SL縮小 | 0.8%/0.6% → 0.4%/0.3%（滞留問題対応） |
| 58.6 | バックテスト精度向上 | 手数料・利息追加、土日TP/SL縮小（62.5%） |
| 58.7 | 稼働率・維持率表示 | 検索パターン修正・N/A表示追加 |
| 58.8 | ポジションカウント・孤児SL防止 | BTC/JPYフィルタ・リトライ機能・孤児検出 |

### Phase 57（完了）: 年利10%目標・リスク最大化

| Phase | 内容 | 成果 |
|-------|------|------|
| 57.1-57.7 | リスク設定最適化・設定ファイル整理 | レバレッジ修正、ポジション拡大 |
| 57.10-57.14 | バックテスト・ライブ分析機能強化 | 84項目/35項目標準分析スクリプト |

### パフォーマンス指標

| 指標 | 値 |
|------|-----|
| **テスト成功率** | 100% |
| **カバレッジ** | 64%以上 |
| **月額コスト** | 700-900円 |
| **手数料削減** | 年間¥150,000 |

---

## リスク・免責事項

- **投資リスク**: 仮想通貨取引には元本割れのリスクがあります
- **システムリスク**: 自動取引システムの不具合による損失の可能性
- **市場リスク**: 急激な市場変動への対応限界
- **免責**: 本システムの使用による損失について作成者は責任を負いません

**推奨**: 少額資金（1万円）でのテスト運用から開始し、段階的拡大

---

## サポート

- **Issues**: GitHub Issuesでの問題報告
- **Discussion**: 機能要望・質問・フィードバック
- **Security**: セキュリティ問題は非公開で報告

---

**最終更新**: 2026年1月13日 - **Phase 58.8完了**（ポジションカウント修正・孤児SL防止）
