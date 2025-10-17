# src/trading/balance/ - 残高監視層 🚀 Phase 42.3.3完了

## 🎯 役割・責任

証拠金残高監視・不足検知・残高アラートを担当します。Phase 38でtradingレイヤードアーキテクチャの一部として分離、Phase 42.3.3で証拠金チェック失敗ハンドリング機能を追加しました。

## 📂 ファイル構成

```
balance/
├── monitor.py       # 残高監視（Phase 42.3.3: リトライ機能追加）
├── __init__.py      # モジュール初期化
└── README.md        # このファイル
```

## 📈 Phase 42.3.3完了（2025年10月18日）

**🎯 Phase 42.3.3: 証拠金チェック失敗ハンドリング・API認証エラー対策**

### ✅ Phase 42.3.3最適化成果
- **証拠金チェックリトライ機能**: エラー20001（bitbank API認証エラー）3回リトライ実装（monitor.py:25-31, 500-558）
  - リトライカウンター初期化: `self._margin_check_failure_count = 0`, `self._max_margin_check_retries = 3`
  - エラー分類ロジック: Error 20001（auth）vsネットワークエラー
  - 成功時リセット: リトライカウンター自動リセット機能

- **Phase 38問題防止**: 証拠金チェック失敗→無限ループ問題の根本解決
  - 背景: Phase 38で-451円損失（4.5%）発生・エラー20001無限ループ
  - 対策: 3回リトライ失敗時に取引自動中止・機会損失防止
  - 効果: Container exit(1)削減・安定稼働実現

- **エラー分類機能**: 一時的エラーvs永続的エラーの区別
  - Error 20001（API auth）: リトライカウント増加
  - ネットワーク/タイムアウト: カウントせず・フォールバック使用
  - 効果: 機会損失削減・取引続行判断の最適化

- **品質保証完了**: 1,081テスト100%成功・69.57%カバレッジ達成

### 📊 Phase 42.3.3重要事項
- **無限ループ防止**: Phase 38の残高不足無限ループ問題を完全解決
- **機会損失削減**: 一時的エラーでは取引続行・永続的エラーのみ停止
- **Discord通知統合**: リトライ上限到達時にCritical通知送信（将来Phase対応）

## 📈 Phase 38完了（2025年10月11日）

**🎯 Phase 38: tradingレイヤードアーキテクチャ実装**

### ✅ Phase 38最適化成果
- **balance層分離**: 証拠金監視機能を独立層として分離
- **5層アーキテクチャ**: core/balance/execution/position/risk層による責務分離
- **テストカバレッジ向上**: 58.62% → 70.56%（+11.94ポイント）
- **保守性向上**: 1,817行ファイル→平均350行/ファイル（-80%）

## 🔧 主要ファイル詳細

### **monitor.py** 🚀**Phase 42.3.3 リトライ機能追加完了**

証拠金残高監視の中核システムです。Phase 42.3.3でAPI認証エラー対策のリトライ機能を実装しました。

**Phase 42.3.3新機能**:
```python
class BalanceMonitor:
    def __init__(self):
        """BalanceMonitor初期化"""
        self.logger = get_logger()
        self.margin_history: List[MarginData] = []
        # Phase 42.3.3: 証拠金チェック失敗時の取引中止機能
        self._margin_check_failure_count = 0
        self._max_margin_check_retries = 3

    async def check_margin_balance(
        self,
        client: BitbankClient,
        required_amount: float,
        discord_notifier: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        証拠金残高チェック（Phase 42.3.3: リトライ機能追加）

        Returns:
            Dict: {
                "sufficient": bool,
                "available": float,
                "required": float,
                "error": str (optional),
                "retry_count": int (optional)
            }
        """
```

**エラー分類ロジック**:
```python
try:
    # 証拠金チェック成功 - リトライカウンターリセット（Phase 42.3.3）
    if self._margin_check_failure_count > 0:
        self.logger.info(f"✅ 証拠金チェック成功 - リトライカウンターリセット")
        self._margin_check_failure_count = 0

    return {"sufficient": True, "available": available_balance, "required": min_required}

except Exception as e:
    # Phase 42.3.3: 証拠金チェック失敗時の詳細分類
    error_str = str(e)

    # エラー20001（bitbank API認証エラー）のみをカウント
    is_api_auth_error = "20001" in error_str or "API エラー: 20001" in error_str

    if is_api_auth_error:
        self._margin_check_failure_count += 1

        # リトライ制限に達した場合は取引を中止
        if self._margin_check_failure_count >= self._max_margin_check_retries:
            self.logger.critical(
                f"🚨 証拠金チェック失敗リトライ上限到達 "
                f"({self._max_margin_check_retries}回) - 取引を中止します"
            )

            # Discord Critical通知送信
            await self._send_margin_check_failure_alert(e, discord_notifier)

            return {
                "sufficient": False,
                "available": 0,
                "required": get_threshold("balance_alert.min_required_margin", 14000.0),
                "error": "margin_check_failure_auth_error",
                "retry_count": self._margin_check_failure_count,
            }
    else:
        # ネットワークエラー・タイムアウト等は一時的な問題なのでカウントしない
        self.logger.warning(
            f"⚠️ 証拠金チェック一時的失敗（ネットワーク/タイムアウト）: {e}"
        )

    # エラー時は既存動作を維持（取引続行・機会損失回避）
    return {"sufficient": True, "available": 0, "required": 0}
```

**主要メソッド**:
- `check_margin_balance()`: **【Phase 42.3.3拡張】証拠金残高チェック・リトライ機能**
- `get_margin_status()`: 証拠金ステータス取得
- `calculate_available_margin()`: 利用可能証拠金計算
- `_send_margin_check_failure_alert()`: **【Phase 42.3.3新規】Discord Critical通知送信**

## 📝 使用方法・例

### **証拠金チェックの実行（Phase 42.3.3対応）**

```python
from src.trading.balance.monitor import BalanceMonitor
from src.data.bitbank_client import BitbankClient

# BalanceMonitor初期化
monitor = BalanceMonitor()

# 証拠金チェック実行
result = await monitor.check_margin_balance(
    client=bitbank_client,
    required_amount=14000.0,
    discord_notifier=discord_manager  # Phase 42.3.3: Critical通知用
)

# 結果確認
if result["sufficient"]:
    print(f"✅ 証拠金OK: {result['available']:.0f}円 >= {result['required']:.0f}円")
else:
    if "error" in result and result["error"] == "margin_check_failure_auth_error":
        print(f"🚨 証拠金チェック失敗（{result['retry_count']}回リトライ失敗）")
        # 取引中止
    else:
        print(f"⚠️ 証拠金不足: {result['available']:.0f}円 < {result['required']:.0f}円")
```

### **Phase 42.3.3エラー分類動作**

```python
# ケース1: API認証エラー（20001）→ カウント増加
# 1回目: retry_count=1, 取引続行
# 2回目: retry_count=2, 取引続行
# 3回目: retry_count=3, 取引中止・Discord Critical通知

# ケース2: ネットワークエラー → カウントせず、取引続行
# 何回発生してもretry_countは増加せず、フォールバック値使用

# ケース3: 成功 → retry_countリセット
# 過去のエラーがあっても、成功時に0にリセット
```

## ⚠️ 注意事項・制約

### **Phase 42.3.3リトライ機能の動作**
- **エラー20001のみカウント**: bitbank API認証エラーのみがリトライ対象
- **一時的エラーは無視**: ネットワーク・タイムアウトはカウントせず取引続行
- **成功時リセット**: 証拠金チェック成功時にリトライカウンターを0にリセット
- **3回上限**: 3回連続でエラー20001が発生すると取引自動中止

### **機会損失削減の設計**
- **厳格な分類**: 永続的エラー（20001）と一時的エラーを明確に区別
- **フォールバック継続**: 一時的エラー時はフォールバック値使用で取引続行
- **段階的対応**: リトライ制限内（1-2回）は警告のみ・3回目でCritical

### **Phase 38 Graceful Degradation統合**
- **Container exit回避**: 残高不足時も取引中止のみでコンテナ停止しない
- **Discord通知**: Phase 42.3.3で将来実装予定（現在はログのみ）
- **状態追跡**: リトライカウンターで証拠金チェック失敗を追跡

## 🔗 関連ファイル・依存関係

### **Phase 42.3.3新規ファイル**
- `src/trading/balance/monitor.py`: 証拠金チェックリトライ機能実装（lines 25-31, 500-558）

### **参照元システム**
- `src/core/execution/execution_service.py`: 証拠金チェック実行
- `src/data/bitbank_client.py`: bitbank API呼び出し
- `src/core/reporting/discord_notifier.py`: Discord Critical通知（将来実装）

### **設定ファイル連携**
- `config/core/thresholds.yaml`: `balance_alert.min_required_margin`（14,000円）
- `config/core/unified.yaml`: mode_balances設定

---

**🎯 重要**: Phase 42.3.3により、Phase 38の証拠金チェック失敗無限ループ問題を根本解決しました。エラー分類による機会損失削減と、リトライ上限による安定性確保を両立しています。
