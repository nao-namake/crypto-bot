# Phase 86: 対処療法からの脱却 - TP/SL/Entry アーキテクチャ根本再構築

**期間**: 2026年5月12日
**状態**: 実装完了・コミット待ち

---

## 背景: Phase 85 デプロイ後の発見

Phase 85 デプロイ後の24h観測でユーザーが bitbank UI を直接確認:

- **SL注文がポジションに対して存在しない**（ロング 0.015 BTC @¥12,840,001 にTPのみ）
- **過去48hエントリー43件中、Maker 0件 / Taker 43件**（API実測）
- 分析スクリプトは「最終判定: 🟢 正常」と表示し**実態を検出できていない**

ユーザー指摘: 「対処療法ではなく、確実にコードを調査し、根本から直して欲しい」

過去 Phase 62-85 で同様の TP/SL 関連修正が10回以上発生し、毎回個別バグ修正に終わっていた。
徹底調査の結果、**3層の構造的欠陥**が判明:

### レイヤー1: TP/SL計算の4箇所分散

| 計算箇所 | TP entry_fee | TP exit_fee | SL entry_fee | SL exit_fee | SL floor |
|---|---|---|---|---|---|
| `strategy_utils.calculate_fixed_amount_tp()` | ✅加算 | ✅加算 | - | - | - |
| `tp_sl_manager._calc_tp_for_position()` | ❌**欠落** | ✅加算 | - | - | - |
| `strategy_utils.calculate_stop_loss_take_profit()` (SL) | - | - | ✅控除 | ✅控除 | ❌**なし** |
| `tp_sl_manager._calc_sl_for_position()` | - | - | ✅控除 | ✅控除 | ✅**0.7%** |

同じポジでTP/SL価格が「いつ計算するか」で4通り → Phase 62→68→69→70→82→83A→83B→85 の往復修正の根本原因。

### レイヤー2: Atomic Entry の不完全性

- Entry → TP → SL の順発注、SL失敗時にロールバック試行
- Entry約定済みなら **キャンセル不可** → bitbank実ポジ残存
- TPだけキャンセル → **SLなし孤児ポジ** → 30分間ノーガード放置

### レイヤー3: ccxt が bitbank stop型未実装

- `ccxt.bitbank.create_order()` は market/limit のみサポート
- bot は `_create_order_direct()` で API直接呼び出し
- `trigger_price` 未指定 → エラー30101 で silent fail の可能性
- INACTIVE状態は `fetch_open_orders` で見えない

---

## 実装内容（4層・優先順）

### P3: bitbank API wrapper 強化（基盤）

ファイル: `src/data/bitbank_client.py:_create_order_direct`

1. **stop型注文の `trigger_price` 必須検証** - 未指定なら ExchangeAPIError
2. **配置後の実存在確認** - fetch_order を最大3秒×3回ポーリング、INACTIVE状態も成功扱い、API成功でも実際に注文されていない silent fail を検出
3. **bitbank エラーコード分類** - 30101 (trigger_price)、50061 (証拠金不足)、50062 (建玉超過)、50063 (ロット数上限)、70015 (発注停止中) を context に含めて raise

### P1: TPSLCalculator 単一実装

ファイル: `src/trading/execution/tpsl_calculator.py` (新規)

TP/SL計算の唯一の実装。純粋関数で副作用なし。

```python
TPSLCalculator.calculate_tp(action, entry_price, amount, target_net_profit,
                            entry_fee_rate=0.001, exit_fee_rate=0.0) -> float

TPSLCalculator.calculate_sl(action, entry_price, amount, target_max_loss,
                            entry_fee_rate=0.001, exit_fee_rate=0.001,
                            min_distance_ratio=0.007, enable_floor=True) -> float
```

**4箇所を全てこれに置換**:
- `strategy_utils.calculate_fixed_amount_tp()` → entry_fee加算済（変化なし、ロジック統一）
- `strategy_utils.calculate_stop_loss_take_profit()` (SL) → **floor強制が計算層に集約**
- `tp_sl_manager._calculate_fixed_amount_tp_for_position()` → **entry_fee 加算追加（バグ修正）**
- `tp_sl_manager._calculate_fixed_amount_sl_for_position()` → floor 統一

### P2: Atomic Entry 真の原子化

ファイル: `src/trading/execution/executor.py` ロールバック部 + `tp_sl_manager.py` 検証スケジュール

1. **部分約定でSL再配置失敗時の緊急成行決済** - 孤児ポジを発生させずに bitbank実ポジを即座に成行で閉じる（反対側market order）
2. **エントリー10秒後のSL存在即時検証** - 既存の10分後検証に加えて、即時検証を `_pending_verifications` にスケジュール

### P0: 起動時 missing-SL 自動修復

ファイル: `src/trading/execution/position_restorer.py:restore_positions_from_api`

ポジションあり・SL注文なしを検出したら、TPSLCalculator で SL価格を計算し緊急配置。
**Phase 86 デプロイ時、既存の 0.015 BTC ロングポジに自動でSL設定される。**

孤児ポジション定期スキャンも30分→**5分間隔**に短縮（`position_management.orphan_scan.interval_seconds: 300`）。

### P4: 分析スクリプトの API実態検証

ファイル: `scripts/live/standard_analysis.py`

1. **ポジションあり SL未設置 検出** - bitbank API でポジション数量 vs stop注文数量を比較。SL率<95%で `missing_sl_detected=True` を立て exit_code=1 (致命的)
2. **bitbank trades から Maker/Taker 集計** - `info.maker_taker` をエントリーのみ集計、Taker率>70%で警告
3. **新フィールド追加**: `missing_sl_detected`, `missing_sl_position_amount`, `missing_sl_order_amount`, `api_entry_maker_count`, `api_entry_taker_count`, `api_entry_taker_rate`, `high_taker_rate_warning`

---

## テスト

`tests/unit/trading/execution/test_tpsl_calculator.py` 新規作成（10テスト）:
- TP計算: BUY/SELL の対称性、entry_fee 加算の有効性
- SL計算: floor強制、floor無効時、手数料超過フォールバック
- TP/SL一括計算の一貫性
- Phase 86 リグレッション（旧バグの再発防止）

既存テスト修正: `test_tp_sl_manager.py::TestPhase686FixedAmountTPForPosition`
- Phase 86 で entry_fee が加算される挙動に合わせて期待値を 50,000 → 60,800 円距離に更新

---

## 変更ファイル一覧

| ファイル | 内容 |
|---|---|
| `src/trading/execution/tpsl_calculator.py` | **新規** TPSLCalculator |
| `src/data/bitbank_client.py` | _create_order_direct 強化（trigger_price検証・配置後確認・エラー分類） |
| `src/strategies/utils/strategy_utils.py` | TP/SL計算 を TPSLCalculator に置換 |
| `src/trading/execution/tp_sl_manager.py` | TP/SL計算 を TPSLCalculator に置換、10秒後SL検証スケジュール追加 |
| `src/trading/execution/executor.py` | ロールバック後の緊急成行決済追加 |
| `src/trading/execution/position_restorer.py` | 起動時SL自動修復、孤児スキャン5分化 |
| `src/trading/execution/tp_sl_config.py` | ORPHAN_SCAN_INTERVAL のパスを position_management 配下に |
| `config/core/thresholds.yaml` | orphan_scan.interval_seconds: 300 追加 |
| `scripts/live/standard_analysis.py` | missing_sl_detected, api Maker/Taker 集計追加、exit_code判定 |
| `tests/unit/trading/execution/test_tpsl_calculator.py` | **新規** 10テスト |
| `tests/unit/trading/execution/test_tp_sl_manager.py` | TPSL長/短ポジテストの期待値更新 |
| `docs/開発履歴/Phase_86.md` | **新規** |
| `docs/開発履歴/SUMMARY.md` | Phase 86 追記 |
| `CLAUDE.md` | しおりPhase 86、TP/SL計算式統一説明 |

---

## 期待効果

1. **TP/SL計算の4箇所分散 → 単一実装** → Phase 62-85 の往復修正地獄が解消
2. **Atomic Entry の真の原子化** → 孤児ポジ発生率を月1-2件 → ほぼ0に
3. **bitbank API wrapper強化** → SL配置失敗の silent fail 解消
4. **起動時自動修復** → 現在保有中の 0.015 BTC SL未設置がデプロイで即解決
5. **分析スクリプト実態化** → 「最終判定 🟢 正常」と実態の乖離解消

---

## 注意点とリスク

- TP計算で entry_fee が加算されるため、TP距離が**約+13%拡大**（0.779% → 0.879%）
  - tight_range TP1500 の場合、TP価格 ≈ entry + ¥112,840（旧 ¥100,000）
- TP距離拡大により TP到達率がわずかに低下する可能性（過去30日シミュ TP1500/SL2000で勝率67.9% → 微減見込み）
- ML再学習は段階的に判断（実運用結果を見て次フェーズで実施）

---

## デプロイ後の観測

```bash
python3 scripts/live/standard_analysis.py --hours 24
```

確認指標:
- `missing_sl_detected = False` （SL未設置が解消）
- `api_entry_taker_rate` が記録される
- 起動時SL自動配置ログ「Phase 86: 緊急SL配置成功」が出る
- TP/SL計算ログ「Phase 86: 固定金額TP計算（TPSLCalculator統一）」が出る
- 「Phase 86: 即時SL検証スケジュール - 10秒後」が各エントリーで出る
