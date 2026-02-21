# Phase 65: ライブ取引頻度回復 - 三重壁の包括的対策

**期間**: 2026年2月21日
**状態**: 完了
**目的**: バックテスト（3.9件/日）に対しライブ本番で24h+取引ゼロが継続 → 三重の遮断壁を包括的に対策

---

## 背景

GCPログ72時間分析で**三重の遮断壁**を特定:

| 壁 | 内容 | 遮断率 |
|----|------|--------|
| **壁1** | 3戦略HOLD支配（ATRBased/StochasticReversal/DonchianChannelが全てHOLD） | 98.3% |
| **壁2** | min_strategy_confidence 0.250（信頼度0.246-0.248が僅差で遮断） | 75% |
| **壁3** | API遅延5000-7800ms（ccxt rateLimit 1000ms + 接続オーバーヘッド） | 100% |

---

## 対策内容

### 壁3修正: API遅延閾値緩和 + ccxtレート制限最適化

| ファイル | 変更 | 根拠 |
|---------|------|------|
| `src/trading/__init__.py` | api_latency_warning_ms: 2000→5000 | Cloud Run + ccxt rate limitingで5-8秒は正常範囲 |
| `src/trading/__init__.py` | api_latency_critical_ms: 5000→15000 | 15秒は真の異常のみ検出 |
| `src/data/bitbank_client.py` | ccxt rateLimit: 1000→200ms | bitbank APIは秒間制限ベース。200msで5回/秒に収まる |

### 壁2修正: min_strategy_confidence緩和

| ファイル | 変更 | 根拠 |
|---------|------|------|
| `config/core/thresholds.yaml` | min_strategy_confidence: 0.25→0.22 | 0.246-0.248のシグナルが通過。0.176等は引き続きフィルタ |

### 壁1修正: BBReversal再有効化 + 重み再配分

| ファイル | 変更 | 根拠 |
|---------|------|------|
| `config/core/thresholds.yaml` | tight_range BBReversal: 0.0→0.15 | Phase 62.2でBB主導ロジック変更済み。GCPログでBUY(0.550)連発確認 |
| `config/core/thresholds.yaml` | StochasticReversal: 0.35→0.30 | 再配分 |
| `config/core/thresholds.yaml` | ATRBased: 0.35→0.30 | 再配分 |
| `config/core/thresholds.yaml` | DonchianChannel: 0.30→0.25 | 再配分 |

合計重み: 0.15+0.30+0.30+0.25=1.0

### 戦略帰属バグ修正

| ファイル | 変更 | 効果 |
|---------|------|------|
| `src/strategies/base/strategy_manager.py` L330 | max()キーに重み考慮追加 | 重み0.0の戦略が帰属先にならない |
| `src/strategies/base/strategy_manager.py` L374 | 同上（_create_quorum_signal内） | 同上 |
| `src/strategies/base/strategy_manager.py` L438 | 同上（_integrate_consistent_signals内） | 同上 |

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/trading/__init__.py` | API遅延閾値 5000→15000ms、警告閾値 2000→5000ms |
| `src/data/bitbank_client.py` | ccxt rateLimit 1000→200ms |
| `config/core/thresholds.yaml` | min_strategy_confidence 0.25→0.22、BBReversal重み0.0→0.15 + 再配分 |
| `src/strategies/base/strategy_manager.py` | 戦略帰属バグ修正（3箇所） |
| `tests/unit/services/test_dynamic_strategy_selector.py` | tight_range重みテスト更新 |
| `CLAUDE.md` | Phase 65追加・重み記載更新 |
| `docs/開発計画/ToDo.md` | Phase 65更新 |
| `docs/開発履歴/Phase_65.md` | 新規作成 |
