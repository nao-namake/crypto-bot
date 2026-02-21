# Phase 65: ライブ取引頻度回復 - 三重壁の包括的対策

**期間**: 2026年2月21日-22日
**状態**: 完了（デプロイ済み・ライブ検証待ち）
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

---

## バックテスト結果

### Phase 64 → Phase 65 比較

| 指標 | Phase 64 | Phase 65 | 変化 |
|------|---------|---------|------|
| **総取引数** | 303件 | **533件** | **+76%** |
| **勝率** | 89.2% | 85.4% | -3.8pt |
| **総損益** | ¥+102,135 | **¥+103,843** | +1.7% |
| **PF** | 2.47 | 1.87 | -24% |
| **最大DD** | ¥4,700 (0.94%) | ¥5,480 (1.07%) | +0.13pt |
| **期待値/件** | ¥+337 | ¥+195 | -42% |
| **SR** | — | 17.99 | — |

### 戦略別パフォーマンス

| 戦略 | 取引数 | 勝率 | 損益 |
|------|--------|------|------|
| **ATRBased** | 362件 | 87.0% | ¥+81,946 |
| **DonchianChannel** | 127件 | 81.9% | ¥+13,117 |
| **StochasticReversal** | 44件 | 81.8% | ¥+8,780 |

### レジーム別パフォーマンス

| レジーム | 取引数 | 勝率 | 損益 |
|---------|--------|------|------|
| tight_range | 476件 | 84.7% | ¥+87,826 |
| normal_range | 57件 | 91.2% | ¥+16,017 |

### ML予測別パフォーマンス

| ML予測 | 取引数 | 勝率 | 損益 |
|--------|--------|------|------|
| BUY | 310件 | 88.4% | ¥+75,206 |
| SELL | 149件 | 84.6% | ¥+29,051 |
| HOLD | 74件 | 74.3% | ¥-413 |

### SL決済パターン分析

| パターン | 件数 | 比率 |
|---------|------|------|
| 一直線損切り（MFE≤0） | 2件 | 2.6% |
| 微益後損切り（MFE<200） | 15件 | 19.2% |
| プラス圏経由（MFE 200-500） | 43件 | 55.1% |
| 500円以上経由 | 18件 | 23.1% |

### 評価

- **取引数+76%増加**（303→533件）: BBReversal再有効化 + min_strategy_confidence緩和の効果
- **総損益維持**: ¥+103,843（Phase 64比+1.7%）
- **PF低下は許容範囲**: 2.47→1.87（取引数増加に伴う自然な低下、1.87は十分高水準）
- **勝率85.4%**: 3.8pt低下だが85%超を維持
- **最大DD 1.07%**: Phase 64の0.94%から微増だが許容範囲内

### 次のステップ

- デプロイ後24時間で `python3 scripts/live/standard_analysis.py` を実行
- ライブ取引数 > 0 を確認
- API遅延ログで5000ms→拒否が消えたことを確認
