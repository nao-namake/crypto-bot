# Crypto-Bot - AI自動取引システム

**Phase 62・bitbank BTC/JPY専用・GCP本番稼働中**

[![Tests](https://img.shields.io/badge/tests-passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-63%25%2B-green)](coverage-reports/)
[![Phase](https://img.shields.io/badge/Phase%2062-In%20Progress-blue)](docs/)

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
bash scripts/testing/checks.sh  # 全テスト成功・62%+カバレッジ

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

### 6戦略構成（Phase 62.2更新）

| 区分 | 戦略名 | 核心ロジック | 備考 |
|------|--------|-------------|------|
| **レンジ型** | BBReversal | BB位置主導 + RSIボーナス → 平均回帰 | Phase 62.2: BB主導に変更 |
| **レンジ型** | StochasticDivergence | 価格とStochasticの乖離検出 → 反転 | Phase 62.2: 価格変化フィルタ追加 |
| **レンジ型** | ATRBased | ATR消尽率70%以上 → 反転期待 | 主力戦略 |
| **レンジ型** | DonchianChannel | チャネル端部反転 + RSIボーナス | Phase 62.2: RSIボーナス制度 |
| **トレンド型** | MACDEMACrossover | MACDクロス + EMAトレンド確認 | - |
| **トレンド型** | ADXTrendStrength | ADX≥25 + DIクロス → トレンドフォロー | - |

### タイトレンジ重みづけ（Phase 59.4-A）

| 戦略 | 重み | 理由 |
|------|------|------|
| BBReversal | 0.35 | レンジ型主力 |
| StochasticReversal | 0.35 | レンジ型主力 |
| ATRBased | 0.20 | 補助 |
| DonchianChannel | 0.10 | 補助 |
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
- **動的戦略選択**: レジーム別重みづけ自動適用（2票ルール無効化）
- **55特徴量**: 49基本 + 6戦略シグナル
- **真の3クラス分類**: BUY / HOLD / SELL直接予測
- **ProductionEnsemble**: LightGBM 40% / XGBoost 40% / RandomForest 20%（Stacking無効）
- **4段階Graceful Degradation**: Stacking無効 → ensemble_full.pkl → ensemble_basic.pkl → DummyModel

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
- **coverage**: 62%以上
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

- **[CLAUDE.md](CLAUDE.md)**: 開発ガイド・品質基準・Phase 62計画
- **[ToDo.md](docs/開発計画/ToDo.md)**: 開発計画・タスク管理

### 運用者向け

- **[統合運用ガイド](docs/運用ガイド/統合運用ガイド.md)**: デプロイ・監視・トラブル対応
- **[GCP運用ガイド](docs/運用ガイド/GCP運用ガイド.md)**: IAM権限・リソース管理
- **[システム機能一覧](docs/運用ガイド/システム機能一覧.md)**: 実装機能リファレンス
- **[開発履歴サマリー](docs/開発履歴/SUMMARY.md)**: Phase 1-62総括

---

## 開発状況

### Phase 62（進行中）: 戦略閾値緩和・条件型変更

| Phase | 内容 | 状態 |
|-------|------|------|
| **62.1** | **3戦略閾値一括緩和** | ✅完了 |
| **62.1-B** | **さらなる閾値緩和** | 📋バックテスト実行中 |
| **62.2** | **戦略条件型変更** | ✅実装完了（バックテスト待ち） |

**目標**: ATRBased一強問題解消（83%→65%以下）、取引数増加（332件→380件+）

**62.2主要変更**:
- DonchianChannel: RSIフィルタ→ボーナス制度
- BBReversal: AND条件→BB位置主導
- StochasticReversal: 最小価格変化フィルタ追加

### Phase 61（✅完了）: 500円TP採用・PF 2.68達成

| 指標 | Phase 60.7 | Phase 61最終 | 変化 |
|------|-----------|--------------|------|
| **総損益** | ¥86,639 | **¥149,195** | **+72%** |
| **PF** | 1.58 | **2.68** | **+70%** |
| **勝率** | 54.8% | **75.8%** | **+21pt** |

**主要成果**: 500円TP採用、低信頼度対策、固定金額TP、TP/SL自動執行検知、ポジションサイズ統一

### Phase 60（完了）: 実効レバレッジ最適化・MLモデル差別化

| Phase | 内容 | 成果 |
|-------|------|------|
| 60.1-60.2 | 実効レバレッジ0.5倍移行 | 14箇所設定変更・稼働率100% |
| 60.3-60.4 | Walk-Forward検証 | 過学習排除・一致率向上 |
| 60.5-60.6 | MLモデル差別化 | シード差別化・動的重み計算 |
| **60.7** | **pandas 3.0互換性修正** | **¥86,639・PF 1.58達成（61.5で更新）** |

### Phase 59（完了）: ML最適化・Stacking検証

| Phase | 内容 | 成果 |
|-------|------|------|
| 59.1-59.3 | BBReversal調整・信頼度対策 | normal_range無効化・penalty/bonus調整 |
| 59.4-A | 2票ルール無効化 | 勝率53.8%、PF 1.55、損益¥+44,506 |
| **59.10** | **Stacking無効化・PE採用** | **✅ 過去最高¥+54,526、PF 1.60** |

### パフォーマンス指標

| 指標 | 値 |
|------|-----|
| **テスト成功率** | 100% |
| **カバレッジ** | 62%以上 |
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

**最終更新**: 2026年1月31日 - **Phase 62.2実装完了**（RSIボーナス・BB主導・価格変化フィルタ）
