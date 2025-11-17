# strategies.yaml 設定変更履歴

**Phase 52.4**

**注**: 具体的な設定値は`config/core/strategies.yaml`を参照

## 概要

このドキュメントは `config/core/strategies.yaml` の設定変更履歴を記録します。

## 変更履歴

### Phase 52.4 (2025-11-14)
**設定整理**: Phase参照統一・コメント簡潔化

- Phase参照を最新に統一
- 詳細履歴を本ドキュメントに移動
- 設定履歴ドキュメント作成

---

### Phase 51.7 Day 3-5 (2025-10-29-30)
**3戦略追加（3→6戦略）**: レンジ型・トレンド型強化

**追加戦略**:
- BB Reversal（レンジ型・BB反転検出）
- Stochastic Reversal（レンジ型・Stochastic + RSI）
- MACD EMA Crossover（トレンド型・MACD + EMA + ADX）

**期待効果**:
- レンジ相場対応強化
- トレンド相場対応強化
- 6戦略統合完了

---

### Phase 51.5-B (2025-10-27)
**動的戦略管理基盤実装**: Registry Pattern導入

**変更内容**:
- 戦略追加時の影響範囲93%削減（27ファイル → 2ファイル）
- Registry Pattern実装（自動戦略検出・ロード）
- strategies.yaml が唯一の戦略定義ソース

**期待効果**:
- 戦略追加: strategies.yaml編集のみ（1ファイル）
- 戦略実装: strategy実装ファイル追加のみ（1ファイル）
- 影響範囲: 27ファイル → 2ファイル（93%削減）

---

### Phase 51.5-A (2025-10-26)
**3戦略構成最適化**: 5戦略 → 3戦略削減

**削除戦略**: MochipoyAlert・MultiTimeframe

**残存戦略**: ATRBased・DonchianChannel・ADXTrendStrength

**期待効果**: システム簡素化・パフォーマンス向上

---

### Phase 41.8 (2025-10-17)
**Strategy-Aware ML**: 実戦略信号学習

**変更内容**: 戦略信号特徴量をML学習に統合

**期待効果**: ML訓練/推論一貫性確保・Look-ahead bias防止

---

### Phase 32 (2025-10-10)
**SignalBuilder統一**: 全戦略統一実装

**変更内容**: SignalBuilderパターン採用・15m ATR優先・動的信頼度計算統一

**期待効果**: 全戦略統一インターフェース・保守性向上

---

### Phase 29.5 (2025-10-08)
**ML予測統合**: 戦略70% + ML30%

**変更内容**: ML予測を戦略判断に統合・重み付け統合

**期待効果**: ML補完による精度向上

---

## 現在の設定 (Phase 52.4)

**注**: 具体的な設定値は `config/core/strategies.yaml` を参照してください。

### 主要構成
- **戦略数**: strategies.yamlに定義（レンジ型・トレンド型・ブレイクアウト型）
- **動的戦略管理**: Registry Pattern実装（93%影響削減）
- **設定ソース**: strategies.yaml（唯一の戦略定義）

---

## 参照

- 戦略設定ファイル: `config/core/strategies.yaml`
- 戦略パラメータ: `config/core/thresholds.yaml`
- 動的戦略管理: `src/strategies/strategy_loader.py`
- Registry Pattern: `src/strategies/strategy_config.py`
- Phase履歴: `docs/開発履歴/`

---

**最終更新**: 2025-11-15 (Phase 52.4)
