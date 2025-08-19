"""
JPY建て拡張バックテストエンジン
日本市場特性・税制考慮・JPY建て収益計算対応
"""

import logging
import os
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import pandas as pd

# Japanese market utilities import - crypto_botから使用
# プロジェクトルートからの相対パスでcrypto_bot.utilsディレクトリを追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from crypto_bot.utils.japanese_market import (
    JapaneseMarketCalendar,
    JPYBacktestEnhancer,
    JPYCalculator,
)
from .engine import BacktestEngine, TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class JPYTradeRecord(TradeRecord):
    """JPY建て取引記録（拡張版）"""

    # 追加のJPY建て情報
    gross_profit_jpy: float
    tax_amount_jpy: float
    net_profit_jpy: float
    fees_jpy: float
    market_activity_score: float
    is_japanese_holiday: bool
    is_business_hours: bool
    holding_period_days: int
    tax_classification: str
    exchange: str = "bitbank"


class JPYEnhancedBacktestEngine(BacktestEngine):
    """JPY建て拡張バックテストエンジン"""

    def __init__(
        self,
        price_df: Optional[pd.DataFrame] = None,
        strategy=None,
        starting_balance: float = 1_000_000,  # 100万円
        slippage_rate: float = 0.001,
        commission_rate: float = 0.0012,  # Bitbankテイカー手数料
        base_currency: str = "JPY",
        japanese_market_config: Optional[Dict] = None,
        tax_settings: Optional[Dict] = None,
        exchange: str = "bitbank",
    ):

        super().__init__(
            price_df, strategy, starting_balance, slippage_rate, commission_rate
        )

        self.base_currency = base_currency
        self.exchange = exchange
        self.japanese_market_config = japanese_market_config or {}
        self.tax_settings = tax_settings or {"enabled": True, "tax_rate": 0.20}

        # 親クラスの属性を確実に設定
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        # JPY建て拡張機能
        self.jpy_enhancer = JPYBacktestEnhancer()
        self.market_calendar = JapaneseMarketCalendar()
        self.jpy_calculator = JPYCalculator()

        # JPY建て取引記録
        self.jpy_trade_records: List[JPYTradeRecord] = []

        logger.info(
            f"JPY Enhanced Backtest Engine initialized: "
            f"base_currency={base_currency}, exchange={exchange}"
        )

    def enhance_price_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """価格データにJPY建て市場特性を追加"""
        if self.japanese_market_config.get("enabled", False):
            enhanced_df = self.jpy_enhancer.enhance_backtest_data(df)
            logger.info("Price data enhanced with Japanese market characteristics")
            return enhanced_df
        return df

    def should_trade_at_time(self, timestamp: pd.Timestamp) -> bool:
        """指定時刻での取引可否判定"""
        if not self.japanese_market_config.get("enabled", False):
            return True

        # 日本市場設定による判定
        if self.japanese_market_config.get("exclude_holidays", False):
            if self.market_calendar.is_japanese_holiday(timestamp):
                return False

        if self.japanese_market_config.get("exclude_year_end", False):
            if self.market_calendar.is_year_end_period(timestamp):
                return False

        if self.japanese_market_config.get("apply_activity_score", False):
            activity_score = self.market_calendar.get_market_activity_score(timestamp)
            min_score = self.japanese_market_config.get("min_activity_score", 0.5)
            if activity_score < min_score:
                return False

        return True

    def execute_trade(
        self,
        timestamp: pd.Timestamp,
        entry_price: float,
        exit_price: float,
        side: str,
        amount: float,
        duration_bars: int,
    ) -> Optional[JPYTradeRecord]:
        """JPY建て取引実行・記録"""
        if not self.should_trade_at_time(timestamp):
            logger.debug(
                f"Trade skipped due to Japanese market conditions: {timestamp}"
            )
            return None

        # 基本的な取引記録作成
        slippage = entry_price * self.slippage_rate
        commission = entry_price * amount * self.commission_rate

        # JPY建て利益計算
        gross_profit = self.jpy_calculator.calculate_profit_jpy(
            entry_price, exit_price, amount, side
        )

        # 税制考慮
        holding_period = duration_bars  # 簡易的に期間をバー数で表現
        tax_info = self.jpy_calculator.calculate_tax_implications(
            gross_profit, holding_period
        )

        # 取引コスト
        cost_info = self.jpy_calculator.calculate_transaction_costs(
            entry_price, amount, self.exchange
        )

        # 市場活動度スコア
        activity_score = self.market_calendar.get_market_activity_score(timestamp)

        # JPY建て取引記録作成
        exit_timestamp = timestamp + pd.Timedelta(hours=duration_bars)
        jpy_trade = JPYTradeRecord(
            entry_time=timestamp,
            exit_time=exit_timestamp,
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            profit=gross_profit,
            return_rate=gross_profit / (entry_price * amount),
            duration_bars=duration_bars,
            slippage=slippage,
            commission=commission,
            size=amount,
            # JPY建て拡張情報
            gross_profit_jpy=tax_info["gross_profit"],
            tax_amount_jpy=tax_info["tax_amount"],
            net_profit_jpy=tax_info["net_profit"],
            fees_jpy=cost_info["taker_fee"],
            market_activity_score=activity_score,
            is_japanese_holiday=self.market_calendar.is_japanese_holiday(timestamp),
            is_business_hours=self.market_calendar.is_japanese_business_hours(
                timestamp
            ),
            holding_period_days=holding_period,
            tax_classification=tax_info["tax_classification"],
            exchange=self.exchange,
        )

        self.jpy_trade_records.append(jpy_trade)
        logger.debug(
            f"JPY trade recorded: {side} {amount} BTC at {entry_price} JPY, "
            f"profit: {gross_profit:.2f} JPY"
        )

        return jpy_trade

    def calculate_jpy_statistics(self) -> Dict:
        """JPY建て統計情報計算"""
        if not self.jpy_trade_records:
            return {
                "total_trades": 0,
                "total_gross_profit_jpy": 0.0,
                "total_tax_amount_jpy": 0.0,
                "total_net_profit_jpy": 0.0,
                "total_fees_jpy": 0.0,
                "win_rate": 0.0,
                "avg_profit_per_trade_jpy": 0.0,
                "avg_tax_per_trade_jpy": 0.0,
                "effective_tax_rate": 0.0,
                "after_tax_return_rate": 0.0,
                "holiday_trades": 0,
                "business_hour_trades": 0,
                "avg_market_activity_score": 0.0,
            }

        total_trades = len(self.jpy_trade_records)
        winning_trades = sum(
            1 for t in self.jpy_trade_records if t.gross_profit_jpy > 0
        )

        total_gross_profit = sum(t.gross_profit_jpy for t in self.jpy_trade_records)
        total_tax_amount = sum(t.tax_amount_jpy for t in self.jpy_trade_records)
        total_net_profit = sum(t.net_profit_jpy for t in self.jpy_trade_records)
        total_fees = sum(t.fees_jpy for t in self.jpy_trade_records)

        holiday_trades = sum(1 for t in self.jpy_trade_records if t.is_japanese_holiday)
        business_hour_trades = sum(
            1 for t in self.jpy_trade_records if t.is_business_hours
        )
        avg_activity_score = (
            sum(t.market_activity_score for t in self.jpy_trade_records) / total_trades
        )

        return {
            "total_trades": total_trades,
            "total_gross_profit_jpy": total_gross_profit,
            "total_tax_amount_jpy": total_tax_amount,
            "total_net_profit_jpy": total_net_profit,
            "total_fees_jpy": total_fees,
            "win_rate": winning_trades / total_trades,
            "avg_profit_per_trade_jpy": total_gross_profit / total_trades,
            "avg_tax_per_trade_jpy": total_tax_amount / total_trades,
            "effective_tax_rate": (
                total_tax_amount / max(total_gross_profit, 1)
                if total_gross_profit > 0
                else 0
            ),
            "after_tax_return_rate": total_net_profit / self.starting_balance,
            "holiday_trades": holiday_trades,
            "business_hour_trades": business_hour_trades,
            "avg_market_activity_score": avg_activity_score,
            "base_currency": self.base_currency,
            "exchange": self.exchange,
        }

    def save_jpy_trade_log(self, csv_path: str):
        """JPY建て取引ログをCSVで保存"""
        if not self.jpy_trade_records:
            logger.warning("No JPY trade records to save")
            return

        # DataFrameに変換
        trade_data = [asdict(trade) for trade in self.jpy_trade_records]
        df = pd.DataFrame(trade_data)

        # CSVファイルに保存
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False)
        logger.info(
            f"JPY trade log saved to {csv_path}: {len(self.jpy_trade_records)} trades"
        )

    def generate_jpy_report(self, report_path: str):
        """JPY建て詳細レポート生成"""
        stats = self.calculate_jpy_statistics()

        report = f"""
=== JPY建てバックテスト結果詳細レポート ===
実行日時: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
取引所: {self.exchange}
基準通貨: {self.base_currency}
初期資金: {self.starting_balance:,.0f} JPY

== 取引統計 ==
総取引数: {stats['total_trades']:,}
勝率: {stats['win_rate']:.1%}
平均利益/取引: {stats['avg_profit_per_trade_jpy']:,.0f} JPY
平均税額/取引: {stats['avg_tax_per_trade_jpy']:,.0f} JPY

== 収益分析 ==
総利益（税引き前）: {stats['total_gross_profit_jpy']:,.0f} JPY
税金総額: {stats['total_tax_amount_jpy']:,.0f} JPY
純利益（税引き後）: {stats['total_net_profit_jpy']:,.0f} JPY
取引手数料総額: {stats['total_fees_jpy']:,.0f} JPY

== 税制影響分析 ==
実効税率: {stats['effective_tax_rate']:.1%}
税引き後リターン率: {stats['after_tax_return_rate']:.1%}
税制分類: 雑所得（暗号通貨取引）

== 日本市場特性分析 ==
祝日取引数: {stats['holiday_trades']}
営業時間内取引数: {stats['business_hour_trades']}
平均市場活動度スコア: {stats['avg_market_activity_score']:.2f}

== 最終評価 ==
投資効率: {stats['total_net_profit_jpy'] / self.starting_balance:.1%}
年間期待リターン: {stats['after_tax_return_rate'] * 365 / 30:.1%} (月次換算)
リスク調整後リターン: 要分析

== 推奨事項 ==
1. 税制最適化: 損益通算活用の検討
2. 取引タイミング: 市場活動度スコア0.7以上推奨
3. 手数料最適化: メイカー取引の活用検討
4. ポートフォリオ: 他通貨ペアとの分散投資検討

注意: 本レポートは過去データに基づくシミュレーション結果であり、
将来の投資成果を保証するものではありません。
"""

        # レポートファイルに保存
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"JPY backtest report generated: {report_path}")
        return report
