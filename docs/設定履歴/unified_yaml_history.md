# unified.yaml 設定状態記録

**最終更新**: 2025-11-18

---

## このファイルの目的

`config/core/unified.yaml`の現在の設定状態を記録し、設定の意味・構造・使われ方を文書化する。

---

## 現在の設定状態

### モード別初期残高設定 (mode_balances)

**各モードの初期残高**:

| モード | JPY残高 | BTC残高 | 用途 |
|--------|---------|---------|------|
| `paper` | 10,000円 | 0 BTC | ペーパートレード（仮想取引） |
| `live` | 10,000円 | 0 BTC | ライブトレード（実取引） |
| `backtest` | 100,000円 | 0 BTC | バックテスト（過去データ検証） |

**設定変更箇所**: 残高変更時に一箇所修正で全モード対応

### MLアンサンブル設定 (ml.ensemble)

**3モデルアンサンブル重み**:

| モデル | 重み | 説明 |
|--------|------|------|
| `lightgbm` | 0.5（50%） | LightGBM - 勾配ブースティング |
| `xgboost` | 0.3（30%） | XGBoost - 勾配ブースティング |
| `random_forest` | 0.2（20%） | RandomForest - アンサンブル学習 |

**合計重み**: 1.0（100%）

### MLフォールバック設定 (ml.fallback)

**2段階Graceful Degradation**:

| レベル | モデルファイル | 特徴量数 | 説明 |
|--------|--------------|---------|------|
| **Level 1（デフォルト）** | `ensemble_full.pkl` | 55特徴量 | 完全特徴量セット（49基本 + 6戦略信号） |
| **Level 2（フォールバック）** | `ensemble_basic.pkl` | 49特徴量 | 基本特徴量のみ（戦略信号なし） |
| **Level 3（最終）** | DummyModel | - | 全holdシグナル・システム継続動作保証 |

**フォールバック戦略**: 自動降格による安定稼働保証

### 取引制約設定 (trading_constraints)

**エントリークールダウン**:
- `entry_cooldown_minutes`: 15（15分間隔）
- **目的**: 過剰取引防止・手数料削減

**ポジション制限**:
- `max_positions`: 1（最大同時ポジション数）
- **目的**: リスク集中回避・シンプル管理

**信用取引設定**:
- `leverage`: 2（レバレッジ2倍）
- **目的**: bitbank信用取引・証拠金効率向上

### 本番環境設定 (production)

**実行設定**:
- `execution_interval_minutes`: 5（5分間隔実行）
- `timezone`: "Asia/Tokyo"（日本時間）

**注文設定**:
- `order_type`: "limit"（指値注文）
- `default_order_size_jpy`: 5000（デフォルト注文サイズ5,000円）

**最小注文サイズ**:
- `min_order_size_jpy`: 500（最小注文500円）

### リスク管理設定 (risk_management)

**Kelly基準設定**:
- `use_kelly_criterion`: true（Kelly基準使用）
- `kelly_fraction`: 0.25（Kelly割合25%・保守的設定）
- `max_position_size_ratio`: 0.3（最大ポジションサイズ30%）

**その他リスク設定**:
- 詳細設定は `config/core/thresholds.yaml` を参照

### ログ設定 (logging)

**ログレベル**:
- `level`: "INFO"（情報レベル）
- `structured_logging`: true（構造化ログ有効）

**ログ出力**:
- `log_to_file`: true（ファイル出力有効）
- `log_to_console`: true（コンソール出力有効）

**ログディレクトリ**:
- `log_directory`: "logs"（ログ保存先）

---

## 使用箇所

| 項目 | 使用箇所 |
|------|---------|
| モード別残高 | `src/core/orchestration/orchestrator.py` (初期化時) |
| MLアンサンブル重み | `src/ml/ensemble.py` (ProductionEnsemble) |
| MLフォールバック | `src/core/orchestration/ml_fallback.py` |
| 取引制約 | `src/trading/position/cooldown.py`, `src/trading/position/limits.py` |
| 本番環境設定 | `main.py`, `src/core/execution/*.py` |
| Kelly基準 | `src/trading/risk/kelly.py` |
| ログ設定 | `src/core/logger.py` (CryptoBotLogger) |

---

## 設定値の意味

### モード別残高の考え方

**paper/live: 10,000円**:
- 1万円スタート → 最大50万円（段階的拡大計画）
- リスク最小化・少額実験フェーズ

**backtest: 100,000円**:
- 十分な検証用資金
- 統計的有意性確保

### MLアンサンブル重みの考え方

**LightGBM 50%（最大重み）**:
- 高速・高精度・メモリ効率良好
- メインモデルとして採用

**XGBoost 30%（中重み）**:
- 汎化性能・安定性重視
- サブモデルとして補完

**RandomForest 20%（低重み）**:
- 過学習耐性・ロバスト性
- アンサンブル多様性確保

### 2段階Graceful Degradationの考え方

**Level 1 → Level 2**:
- 戦略信号特徴量なしでも動作可能
- 55特徴量 → 49特徴量に自動降格

**Level 2 → Level 3**:
- MLモデル完全障害時でもシステム継続
- DummyModel（全hold）で安全停止状態維持

**目的**: ゼロダウンタイム保証・システム安定性向上

### 取引制約の考え方

**15分間隔クールダウン**:
- 過剰取引防止（1日最大96回 → 実質10-20回）
- 手数料削減効果

**最大1ポジション**:
- シンプル管理・リスク集中回避
- デイトレード特化設計

**レバレッジ2倍**:
- bitbank信用取引標準設定
- 証拠金効率向上・強制ロスカット回避

### 本番環境設定の考え方

**5分間隔実行**:
- GCP Cloud Runコスト削減35-45%
- 月額700-900円達成
- 取引機会確保とコストのバランス

**完全指値オンリー**:
- Maker手数料 -0.02%（リベート）
- 年間¥150,000削減
- 約定率90-95%

**注文サイズ5,000円**:
- 1万円残高の50%
- Kelly基準25%との整合性

---

## 設定変更時の注意点

1. **モード別残高変更**: 実運用資金拡大時に一箇所修正
2. **MLアンサンブル重み変更**: 合計1.0維持必須・バックテスト検証
3. **MLフォールバック変更**: モデルファイル存在確認必須
4. **取引制約変更**: bitbank API制限・手数料への影響評価
5. **本番環境設定変更**: GCPコスト・取引機会への影響評価
6. **Kelly基準変更**: リスク許容度・資金管理戦略との整合性

---

## 開発履歴との関係

このファイルは**現在の設定状態**を記録します。

設定変更の**履歴**（いつ・なぜ変更したか）は以下を参照:
- **Phase別変更履歴**: `docs/開発履歴/Phase_*.md`
- **CI/CD履歴**: `docs/設定履歴/ci_cd_history.md`

---

## 参照

- **統一設定ファイル**: `config/core/unified.yaml`
- **動的閾値設定**: `config/core/thresholds.yaml`
- **戦略設定**: `config/core/strategies.yaml`
- **機能トグル**: `config/core/features.yaml`
- **開発履歴**: `docs/開発履歴/`

---

**最終更新**: 2025-11-18
