"""
Phase 86: TP/SL 計算の単一実装

過去 Phase 62-85 で TP/SL 計算が4箇所に分散し、修正の度に往復ロールバックが
発生していた問題を根本解決するため、唯一の計算実装として本クラスを導入。

設計原則:
1. 計算ロジックの単一実装（DRY）
2. TP/SL対称設計（fee扱いを統一）
3. floor強制を計算層で完結
4. 純粋関数（副作用なし）

すべてのTP/SL計算箇所（strategy_utils, tp_sl_manager, risk/manager,
position_restorer 等）は本クラスを使用する。

修正履歴:
- Phase 86: 新規作成（TP entry_fee加算欠落バグ、SL floor非対称の根本修正）
"""

from typing import Tuple


class TPSLCalculator:
    """TP/SL価格計算の唯一の実装。

    入力（純粋関数）:
        - action: "buy" or "sell"（エントリー方向）
        - entry_price: エントリー価格（または既存ポジションの平均建値）
        - amount: ポジションサイズ（BTC）
        - target: 目標純利益（TP） or 目標最大損失（SL）
        - fee_rate: 手数料率（Taker 0.001 / Maker 0.0）

    出力:
        - TP/SL価格（円）

    Phase 86 の対称設計:
        - TP: gross_needed = target + entry_fee + exit_fee（両方加算）
        - SL: gross_loss = target - entry_fee - exit_fee（両方控除）
        → 結果として「目標純利益/損失」を実現する最悪値を保証
    """

    @staticmethod
    def calculate_tp(
        action: str,
        entry_price: float,
        amount: float,
        target_net_profit: float,
        entry_fee_rate: float = 0.001,
        exit_fee_rate: float = 0.0,
    ) -> float:
        """TP価格を計算（手数料控除後の純利益が target_net_profit となる価格）

        Args:
            action: "buy"（ロングのTP=sell limit）or "sell"（ショートのTP=buy limit）
            entry_price: エントリー価格
            amount: ポジションサイズ（BTC）
            target_net_profit: 目標純利益（手数料控除後、円）
            entry_fee_rate: エントリー時手数料率（デフォルト Taker 0.1%）
            exit_fee_rate: TP決済時手数料率（デフォルト Maker 0%）

        Returns:
            TP価格（円）
        """
        entry_fee = entry_price * amount * entry_fee_rate
        exit_fee = entry_price * amount * exit_fee_rate
        gross_needed = target_net_profit + entry_fee + exit_fee
        tp_distance = gross_needed / amount
        if action == "buy":
            return entry_price + tp_distance
        else:
            return entry_price - tp_distance

    @staticmethod
    def calculate_sl(
        action: str,
        entry_price: float,
        amount: float,
        target_max_loss: float,
        entry_fee_rate: float = 0.001,
        exit_fee_rate: float = 0.001,
        min_distance_ratio: float = 0.007,
        enable_floor: bool = True,
    ) -> float:
        """SL価格を計算（手数料控除後の純損失が target_max_loss を超えない価格）

        Args:
            action: "buy"（ロング保有時のSL=sell stop）or "sell"（ショート保有時のSL=buy stop）
            entry_price: エントリー価格
            amount: ポジションサイズ（BTC）
            target_max_loss: 目標最大損失（手数料込み、円）
            entry_fee_rate: エントリー時手数料率（デフォルト Taker 0.1%）
            exit_fee_rate: SL決済時手数料率（デフォルト Taker 0.1%）
            min_distance_ratio: SL最低距離率（floor、デフォルト0.7%）
            enable_floor: floor強制有効化フラグ（デフォルト True）

        Returns:
            SL価格（円）

        Note:
            手数料合計 >= target_max_loss となる場合、target をそのまま
            distance として使用するフォールバック（Phase 83C相当）。
            floor が有効な場合、計算 distance が floor 未満なら floor 強制。
        """
        entry_fee = entry_price * amount * entry_fee_rate
        exit_fee = entry_price * amount * exit_fee_rate
        gross_loss = target_max_loss - entry_fee - exit_fee
        if gross_loss <= 0:
            # フォールバック: 手数料超過時は target をそのまま距離に
            sl_distance = target_max_loss / amount
        else:
            sl_distance = gross_loss / amount

        # Phase 86: floor強制（BTCノイズ越え保証）
        if enable_floor:
            min_offset = entry_price * min_distance_ratio
            sl_distance = max(sl_distance, min_offset)

        if action == "buy":
            return entry_price - sl_distance
        else:
            return entry_price + sl_distance

    @staticmethod
    def calculate_both(
        action: str,
        entry_price: float,
        amount: float,
        target_net_profit: float,
        target_max_loss: float,
        tp_entry_fee_rate: float = 0.001,
        tp_exit_fee_rate: float = 0.0,
        sl_entry_fee_rate: float = 0.001,
        sl_exit_fee_rate: float = 0.001,
        min_distance_ratio: float = 0.007,
        enable_floor: bool = True,
    ) -> Tuple[float, float]:
        """TP/SL両方を一括計算して返す。

        Returns:
            (tp_price, sl_price)
        """
        tp = TPSLCalculator.calculate_tp(
            action=action,
            entry_price=entry_price,
            amount=amount,
            target_net_profit=target_net_profit,
            entry_fee_rate=tp_entry_fee_rate,
            exit_fee_rate=tp_exit_fee_rate,
        )
        sl = TPSLCalculator.calculate_sl(
            action=action,
            entry_price=entry_price,
            amount=amount,
            target_max_loss=target_max_loss,
            entry_fee_rate=sl_entry_fee_rate,
            exit_fee_rate=sl_exit_fee_rate,
            min_distance_ratio=min_distance_ratio,
            enable_floor=enable_floor,
        )
        return tp, sl
