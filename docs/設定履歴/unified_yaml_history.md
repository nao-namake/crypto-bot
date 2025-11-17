# unified.yaml 設定変更履歴

**Phase 52.4**

**注**: 具体的な設定値は`config/core/unified.yaml`を参照

## 概要

このドキュメントは `config/core/unified.yaml` の設定変更履歴を記録します。

## 変更履歴

### Phase 52.4 (2025-11-14)
**設定整理**: Phase参照統一・コメント簡潔化

- Phase参照を最新に統一
- 詳細履歴を本ドキュメントに移動
- 設定履歴ドキュメント作成

---

### Phase 50.9 (2025-11-01)
**2段階Graceful Degradation実装**

**変更内容**:
- 外部API依存削除
- 動的モデル選択に移行（ensemble_full.pkl → ensemble_basic.pkl → DummyModel）
- ML設定を一元管理（thresholds.yamlに移動）

**期待効果**:
- システム安定性向上
- 保守性向上
- KISS原則徹底

---

### Phase 46 (2025-10-22)
**モード別初期残高設定**

**変更内容**:
- `mode_balances` セクション新設
- paper/live/backtest 各モードの初期残高を一元管理

**期待効果**:
- 残高変更時に一箇所修正で完結

---

### Phase 38.7.2 (2025-10-15)
**完全指値オンリー**

**変更内容**:
- デフォルト注文タイプを limit に変更

**期待効果**:
- 年間手数料削減: ¥150,000
- Maker手数料: -0.02%（リベート）

---

### Phase 37.3 (2025-10-10)
**実行間隔最適化**

**変更内容**:
- 5分間隔実行に変更

**期待効果**:
- GCP Cloud Runコスト削減: 35-45%
- 月額運用コスト: 700-900円達成

---

## 現在の設定 (Phase 52.4)

**注**: 具体的な設定値は `config/core/unified.yaml` を参照してください。

### 主要セクション
- **mode_balances**: モード別初期残高
- **ml**: ML設定（ensemble重み・fallback設定）
- **trading_constraints**: 取引制約
- **production**: 本番環境設定（実行間隔・注文サイズ）

---

## 参照

- 統一設定ファイル: `config/core/unified.yaml`
- 動的閾値設定: `thresholds_yaml_history.md`
- 戦略設定履歴: `strategies_yaml_history.md`
- Phase履歴: `docs/開発履歴/`

---

**最終更新**: 2025-11-15 (Phase 52.4)
