"""
日本市場特性ユーティリティ
日本の営業時間・祝日・市場特性を考慮した取引システム
"""

import logging
from typing import List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class JapaneseMarketCalendar:
    """日本市場カレンダー・営業時間管理"""

    def __init__(self):
        # 日本の祝日リスト（2024-2025年）
        self.japanese_holidays = [
            # 2024年
            "2024-01-01",  # 元日
            "2024-01-08",  # 成人の日
            "2024-02-11",  # 建国記念の日
            "2024-02-12",  # 建国記念の日振替休日
            "2024-02-23",  # 天皇誕生日
            "2024-03-20",  # 春分の日
            "2024-04-29",  # 昭和の日
            "2024-05-03",  # 憲法記念日
            "2024-05-04",  # みどりの日
            "2024-05-05",  # こどもの日
            "2024-05-06",  # こどもの日振替休日
            "2024-07-15",  # 海の日
            "2024-08-11",  # 山の日
            "2024-08-12",  # 山の日振替休日
            "2024-09-16",  # 敬老の日
            "2024-09-22",  # 秋分の日
            "2024-09-23",  # 秋分の日振替休日
            "2024-10-14",  # スポーツの日
            "2024-11-03",  # 文化の日
            "2024-11-04",  # 文化の日振替休日
            "2024-11-23",  # 勤労感謝の日
            "2024-12-31",  # 年末
            # 2025年
            "2025-01-01",  # 元日
            "2025-01-13",  # 成人の日
            "2025-02-11",  # 建国記念の日
            "2025-02-23",  # 天皇誕生日
            "2025-02-24",  # 天皇誕生日振替休日
            "2025-03-20",  # 春分の日
            "2025-04-29",  # 昭和の日
            "2025-05-03",  # 憲法記念日
            "2025-05-04",  # みどりの日
            "2025-05-05",  # こどもの日
            "2025-05-06",  # こどもの日振替休日
            "2025-07-21",  # 海の日
            "2025-08-11",  # 山の日
            "2025-09-15",  # 敬老の日
            "2025-09-23",  # 秋分の日
            "2025-10-13",  # スポーツの日
            "2025-11-03",  # 文化の日
            "2025-11-23",  # 勤労感謝の日
            "2025-11-24",  # 勤労感謝の日振替休日
            "2025-12-31",  # 年末
        ]

        # 年末年始期間（流動性低下期間）
        self.year_end_periods = [
            ("2024-12-29", "2025-01-03"),
            ("2025-12-29", "2026-01-03"),
        ]

    def is_japanese_holiday(self, date: pd.Timestamp) -> bool:
        """指定日が日本の祝日かどうか判定"""
        date_str = date.strftime("%Y-%m-%d")
        return date_str in self.japanese_holidays

    def is_weekend(self, date: pd.Timestamp) -> bool:
        """土日判定"""
        return date.weekday() >= 5  # 土曜日(5)、日曜日(6)

    def is_year_end_period(self, date: pd.Timestamp) -> bool:
        """年末年始期間（流動性低下期間）判定"""
        date_str = date.strftime("%Y-%m-%d")
        for start, end in self.year_end_periods:
            if start <= date_str <= end:
                return True
        return False

    def is_trading_day(self, date: pd.Timestamp) -> bool:
        """取引日判定（暗号通貨は24/7だが、日本市場の活動度を考慮）"""
        # 暗号通貨は24時間取引可能だが、日本市場の活動度を考慮
        # 祝日・年末年始は流動性が低下する可能性
        return not (self.is_japanese_holiday(date) or self.is_year_end_period(date))

    def get_japanese_business_hours(self, date: pd.Timestamp) -> Tuple[int, int]:
        """日本のビジネス時間取得（JST）"""
        # 一般的な日本のビジネス時間: 9:00-17:00 JST
        return (9, 17)

    def is_japanese_business_hours(self, timestamp: pd.Timestamp) -> bool:
        """日本のビジネス時間内かどうか判定"""
        # タイムゾーン考慮（JST）
        jst_time = timestamp.tz_localize("UTC").tz_convert("Asia/Tokyo")
        business_start, business_end = self.get_japanese_business_hours(jst_time)
        return business_start <= jst_time.hour < business_end

    def get_market_activity_score(self, timestamp: pd.Timestamp) -> float:
        """市場活動度スコア算出（0.0-1.0）"""
        jst_time = timestamp.tz_localize("UTC").tz_convert("Asia/Tokyo")

        # 基本スコア
        score = 1.0

        # 祝日・年末年始の影響
        if self.is_japanese_holiday(jst_time):
            score *= 0.7  # 30%低下

        if self.is_year_end_period(jst_time):
            score *= 0.5  # 50%低下

        # 土日の影響
        if self.is_weekend(jst_time):
            score *= 0.8  # 20%低下

        # 時間帯の影響
        hour = jst_time.hour
        if 9 <= hour < 17:  # ビジネス時間
            score *= 1.0
        elif 17 <= hour < 21:  # 夕方
            score *= 0.9
        elif 21 <= hour < 24 or 0 <= hour < 6:  # 夜間
            score *= 0.7
        else:  # 早朝
            score *= 0.8

        return score


class JPYCalculator:
    """JPY建て収益計算・税制対応"""

    def __init__(self):
        self.consumption_tax_rate = 0.10  # 消費税率10%
        self.capital_gains_tax_rates = {
            "short_term": 0.20,  # 短期譲渡所得税率（20%）
            "long_term": 0.20,  # 長期譲渡所得税率（20%）
        }

    def calculate_profit_jpy(
        self, entry_price: float, exit_price: float, amount: float, side: str
    ) -> float:
        """JPY建て利益計算"""
        if side.upper() == "BUY":
            # ロング: 上昇で利益
            profit = (exit_price - entry_price) * amount
        else:
            # ショート: 下落で利益
            profit = (entry_price - exit_price) * amount

        return profit

    def calculate_tax_implications(
        self, profit: float, holding_period_days: int
    ) -> dict:
        """税制考慮計算"""
        # 暗号通貨は雑所得として扱われる
        tax_rate = self.capital_gains_tax_rates[
            "short_term"
        ]  # 暗号通貨は基本的に雑所得

        gross_profit = profit
        tax_amount = max(0, gross_profit * tax_rate) if gross_profit > 0 else 0
        net_profit = gross_profit - tax_amount

        return {
            "gross_profit": gross_profit,
            "tax_amount": tax_amount,
            "net_profit": net_profit,
            "tax_rate": tax_rate,
            "holding_period_days": holding_period_days,
            "tax_classification": "雑所得",
        }

    def calculate_transaction_costs(
        self, price: float, amount: float, exchange: str = "bitbank"
    ) -> dict:
        """取引コスト計算"""
        # 取引所別手数料
        fee_rates = {
            "bitbank": {
                "maker": -0.0002,  # メイカー手数料（リベート）
                "taker": 0.0012,  # テイカー手数料
            },
            "bitflyer": {
                "maker": 0.0001,
                "taker": 0.0015,
            },
            "okcoinjp": {
                "maker": -0.0003,
                "taker": 0.0005,
            },
        }

        fees = fee_rates.get(exchange, fee_rates["bitbank"])
        trade_value = price * amount

        return {
            "trade_value": trade_value,
            "maker_fee": trade_value * fees["maker"],
            "taker_fee": trade_value * fees["taker"],
            "maker_fee_rate": fees["maker"],
            "taker_fee_rate": fees["taker"],
        }


class JPYBacktestEnhancer:
    """JPY建てバックテスト拡張機能"""

    def __init__(self):
        self.market_calendar = JapaneseMarketCalendar()
        self.jpy_calculator = JPYCalculator()

    def enhance_backtest_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """バックテストデータにJPY建て市場特性を追加"""
        enhanced_df = df.copy()

        # 日本市場特性の追加
        enhanced_df["is_japanese_holiday"] = enhanced_df.index.map(
            self.market_calendar.is_japanese_holiday
        )
        enhanced_df["is_weekend"] = enhanced_df.index.map(
            self.market_calendar.is_weekend
        )
        enhanced_df["is_year_end_period"] = enhanced_df.index.map(
            self.market_calendar.is_year_end_period
        )
        enhanced_df["is_trading_day"] = enhanced_df.index.map(
            self.market_calendar.is_trading_day
        )
        enhanced_df["is_business_hours"] = enhanced_df.index.map(
            self.market_calendar.is_japanese_business_hours
        )
        enhanced_df["market_activity_score"] = enhanced_df.index.map(
            self.market_calendar.get_market_activity_score
        )

        logger.info(
            f"Enhanced backtest data with Japanese market characteristics: "
            f"{enhanced_df.shape}"
        )
        return enhanced_df

    def calculate_jpy_performance(self, trades: List[dict]) -> dict:
        """取引履歴からJPY建てパフォーマンス計算"""
        total_gross_profit = 0
        total_tax_amount = 0
        total_net_profit = 0
        total_fees = 0

        for trade in trades:
            # JPY建て利益計算
            profit = self.jpy_calculator.calculate_profit_jpy(
                trade["entry_price"],
                trade["exit_price"],
                trade["amount"],
                trade["side"],
            )

            # 税制考慮
            holding_period = (trade["exit_time"] - trade["entry_time"]).days
            tax_info = self.jpy_calculator.calculate_tax_implications(
                profit, holding_period
            )

            # 取引コスト
            cost_info = self.jpy_calculator.calculate_transaction_costs(
                trade["entry_price"], trade["amount"], trade.get("exchange", "bitbank")
            )

            total_gross_profit += tax_info["gross_profit"]
            total_tax_amount += tax_info["tax_amount"]
            total_net_profit += tax_info["net_profit"]
            total_fees += cost_info["taker_fee"]  # テイカー手数料想定

        return {
            "total_gross_profit_jpy": total_gross_profit,
            "total_tax_amount_jpy": total_tax_amount,
            "total_net_profit_jpy": total_net_profit,
            "total_fees_jpy": total_fees,
            "after_tax_return_rate": total_net_profit / max(abs(total_gross_profit), 1),
            "effective_tax_rate": (
                total_tax_amount / max(total_gross_profit, 1)
                if total_gross_profit > 0
                else 0
            ),
        }

    def generate_jpy_report(self, performance: dict) -> str:
        """JPY建てパフォーマンスレポート生成"""
        report = f"""
=== JPY建てバックテスト結果 ===

収益性分析:
- 総利益（税引き前）: {performance['total_gross_profit_jpy']:,.0f} JPY
- 税金額: {performance['total_tax_amount_jpy']:,.0f} JPY
- 純利益（税引き後）: {performance['total_net_profit_jpy']:,.0f} JPY
- 取引手数料: {performance['total_fees_jpy']:,.0f} JPY

税制影響:
- 実効税率: {performance['effective_tax_rate']:.1%}
- 税引き後リターン率: {performance['after_tax_return_rate']:.1%}

日本市場特性:
- 雑所得として20%課税
- 取引所手数料考慮済み
- 日本の祝日・年末年始期間考慮済み
"""
        return report
