"""
残高・保証金監視サービス - Phase 38リファクタリング
Phase 28/29: 保証金維持率監視システム

現在の59%という危険な維持率を可視化し、
将来的な制限機能の基盤を提供する。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ...core.config import get_threshold, is_backtest_mode
from ...core.logger import get_logger
from ...data.bitbank_client import BitbankClient
from ..core import MarginData, MarginPrediction, MarginStatus


class BalanceMonitor:
    """
    残高・保証金維持率監視サービス

    監視のみを行い、制限や強制決済は実装しない。
    """

    def __init__(self):
        """BalanceMonitor初期化"""
        self.logger = get_logger()
        self.margin_history: List[MarginData] = []

    async def calculate_margin_ratio(
        self,
        balance_jpy: float,
        position_value_jpy: float,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> float:
        """
        保証金維持率を計算（API優先・フォールバック付き）

        Args:
            balance_jpy: 口座残高（JPY）
            position_value_jpy: 建玉総額（JPY換算）
            bitbank_client: Bitbank APIクライアント

        Returns:
            保証金維持率（%）
        """
        # バックテストモード時はAPI呼び出しスキップ
        if is_backtest_mode():
            return self._calculate_margin_ratio_direct(balance_jpy, position_value_jpy)

        # API直接取得を試行
        if bitbank_client:
            api_ratio = await self._fetch_margin_ratio_from_api(bitbank_client)
            if api_ratio is not None:
                return api_ratio

        # フォールバック：計算方式
        return self._calculate_margin_ratio_direct(balance_jpy, position_value_jpy)

    def _calculate_margin_ratio_direct(
        self, balance_jpy: float, position_value_jpy: float
    ) -> float:
        """
        保証金維持率を直接計算

        Args:
            balance_jpy: 口座残高（JPY）
            position_value_jpy: 建玉総額（JPY換算）

        Returns:
            保証金維持率（%）
        """
        if position_value_jpy <= 0:
            return float("inf")

        # 異常値対策: 建玉が極小値の場合
        min_position_value = get_threshold("margin.min_position_value", 1000.0)
        if position_value_jpy < min_position_value:
            self.logger.debug(
                f"建玉極小値: {position_value_jpy:.0f}円 < {min_position_value:.0f}円 "
                f"→ 安全値500%として扱う"
            )
            return 500.0

        # 保証金維持率 = (受入保証金合計額 ÷ 建玉) × 100
        margin_ratio = (balance_jpy / position_value_jpy) * 100

        # 異常な高値のキャップ
        max_ratio = get_threshold("margin.max_ratio_cap", 10000.0)
        if margin_ratio > max_ratio:
            self.logger.warning(
                f"異常に高い維持率検出: {margin_ratio:.1f}% → {max_ratio:.0f}%にキャップ"
            )
            return max_ratio

        return max(0, margin_ratio)

    async def _fetch_margin_ratio_from_api(self, bitbank_client: BitbankClient) -> Optional[float]:
        """
        bitbank APIから保証金維持率を直接取得

        Args:
            bitbank_client: Bitbank APIクライアント

        Returns:
            保証金維持率（%）、取得失敗時はNone
        """
        try:
            margin_status = await bitbank_client.fetch_margin_status()

            api_margin_ratio = margin_status.get("margin_ratio")
            if api_margin_ratio is not None:
                self.logger.info(f"📡 API直接取得成功: 保証金維持率 {api_margin_ratio:.1f}%")
                return float(api_margin_ratio)
            else:
                self.logger.warning("⚠️ API応答に保証金維持率データなし")
                return None

        except Exception as e:
            self.logger.warning(f"⚠️ API直接取得失敗: {e}")
            return None

    def get_margin_status(self, margin_ratio: float) -> Tuple[MarginStatus, str]:
        """
        維持率に基づく状態判定

        Args:
            margin_ratio: 保証金維持率（%）

        Returns:
            (状態, メッセージ) のタプル
        """
        safe_threshold = get_threshold("margin.thresholds.safe", 200.0)
        caution_threshold = get_threshold("margin.thresholds.caution", 150.0)
        warning_threshold = get_threshold("margin.thresholds.warning", 100.0)

        if margin_ratio >= safe_threshold:
            return MarginStatus.SAFE, "✅ 安全な維持率です"
        elif margin_ratio >= caution_threshold:
            return MarginStatus.CAUTION, "⚠️ 維持率が低下しています"
        elif margin_ratio >= warning_threshold:
            return MarginStatus.WARNING, "⚠️ 警告: 維持率が低い状態です"
        else:
            return MarginStatus.CRITICAL, "🚨 危険: 追証発生レベルです"

    async def analyze_current_margin(
        self,
        balance_jpy: float,
        position_value_jpy: float,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> MarginData:
        """
        現在の保証金状況を分析

        Args:
            balance_jpy: 現在の口座残高（JPY）
            position_value_jpy: 現在の建玉総額（JPY換算）
            bitbank_client: Bitbank APIクライアント

        Returns:
            保証金分析結果
        """
        margin_ratio = await self.calculate_margin_ratio(
            balance_jpy, position_value_jpy, bitbank_client
        )

        status, message = self.get_margin_status(margin_ratio)

        margin_data = MarginData(
            current_balance=balance_jpy,
            position_value_jpy=position_value_jpy,
            margin_ratio=margin_ratio,
            status=status,
            message=message,
            timestamp=datetime.now(),
        )

        # 履歴に追加
        self._add_to_history(margin_data)

        # ログ出力
        self.logger.info(f"📊 保証金維持率: {margin_ratio:.1f}% - {message}")

        return margin_data

    async def predict_future_margin(
        self,
        current_balance_jpy: float,
        current_position_value_jpy: float,
        new_position_size_btc: float,
        btc_price_jpy: float,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> MarginPrediction:
        """
        新規ポジション追加後の維持率を予測

        Args:
            current_balance_jpy: 現在の残高（JPY）
            current_position_value_jpy: 現在の建玉総額（JPY）
            new_position_size_btc: 新規ポジションサイズ（BTC）
            btc_price_jpy: BTC価格（JPY）
            bitbank_client: Bitbank APIクライアント

        Returns:
            維持率予測結果
        """
        # 現在の状況
        current_margin = await self.analyze_current_margin(
            current_balance_jpy, current_position_value_jpy, bitbank_client
        )

        # 新規ポジション追加後の建玉総額
        new_position_value_jpy = new_position_size_btc * btc_price_jpy
        future_position_value = current_position_value_jpy + new_position_value_jpy

        # 予測維持率
        future_margin_ratio = self._calculate_margin_ratio_direct(
            current_balance_jpy, future_position_value
        )

        future_status, _ = self.get_margin_status(future_margin_ratio)

        # 推奨アクション
        recommendation = self._get_recommendation(future_margin_ratio)

        prediction = MarginPrediction(
            current_margin=current_margin,
            future_margin_ratio=future_margin_ratio,
            future_status=future_status,
            position_size_btc=new_position_size_btc,
            btc_price=btc_price_jpy,
            recommendation=recommendation,
        )

        # 警告ログ（バックテスト時は抑制）
        if not is_backtest_mode() and future_margin_ratio < current_margin.margin_ratio:
            self.logger.warning(
                f"⚠️ 維持率低下予測: {current_margin.margin_ratio:.1f}% "
                f"→ {future_margin_ratio:.1f}%"
            )

        return prediction

    def _get_recommendation(self, margin_ratio: float) -> str:
        """
        維持率に基づく推奨アクション

        Args:
            margin_ratio: 保証金維持率（%）

        Returns:
            推奨アクション
        """
        critical_threshold = get_threshold("margin.thresholds.warning", 100.0)
        warning_threshold = get_threshold("margin.thresholds.caution", 150.0)
        safe_threshold = get_threshold("margin.thresholds.safe", 200.0)

        if margin_ratio < critical_threshold:
            return "🚨 新規エントリー非推奨（追証リスク）"
        elif margin_ratio < warning_threshold:
            return "⚠️ ポジションサイズ削減を推奨"
        elif margin_ratio < safe_threshold:
            return "⚠️ 注意深く監視してください"
        else:
            return "✅ 問題なし"

    def _add_to_history(self, margin_data: MarginData) -> None:
        """
        履歴に追加（最新100件まで保持）

        Args:
            margin_data: 保証金データ
        """
        max_history = get_threshold("margin.max_history_count", 100)
        self.margin_history.append(margin_data)
        if len(self.margin_history) > max_history:
            self.margin_history = self.margin_history[-max_history:]

    def get_margin_summary(self) -> Dict[str, Any]:
        """
        保証金監視サマリーを取得

        Returns:
            監視サマリー情報
        """
        if not self.margin_history:
            return {"status": "no_data", "message": "データがありません"}

        latest = self.margin_history[-1]

        # 過去の推移
        recent_count = min(10, len(self.margin_history))
        recent_history = self.margin_history[-recent_count:]

        # トレンド分析
        trend = "insufficient_data"
        if len(recent_history) >= 2:
            first_ratio = recent_history[0].margin_ratio
            last_ratio = recent_history[-1].margin_ratio
            if last_ratio > first_ratio:
                trend = "improving"
            elif last_ratio < first_ratio:
                trend = "declining"
            else:
                trend = "stable"

        return {
            "current_status": {
                "margin_ratio": latest.margin_ratio,
                "status": latest.status.value,
                "message": latest.message,
                "timestamp": latest.timestamp.isoformat(),
            },
            "trend": trend,
            "history_count": len(self.margin_history),
            "recommendations": self._get_margin_recommendations(latest),
        }

    def _get_margin_recommendations(self, margin_data: MarginData) -> List[str]:
        """
        現在の維持率に基づく推奨アクション

        Args:
            margin_data: 保証金データ

        Returns:
            推奨アクションリスト
        """
        recommendations = []

        if margin_data.status == MarginStatus.CRITICAL:
            recommendations.extend(
                [
                    "🚨 緊急：追証が発生しています",
                    "💰 入金を検討してください",
                    "📉 ポジション縮小を検討してください",
                    "⏱️ 新規エントリーは控えめに",
                ]
            )
        elif margin_data.status == MarginStatus.WARNING:
            recommendations.extend(
                [
                    "⚠️ 維持率が低下しています",
                    "💰 追加入金を検討してください",
                    "📊 ポジションサイズを控えめに",
                    "👀 市場動向を注意深く監視",
                ]
            )
        elif margin_data.status == MarginStatus.CAUTION:
            recommendations.extend(
                ["⚠️ 維持率に注意してください", "📊 大きなポジションは避ける", "👀 価格変動を監視"]
            )
        else:  # SAFE
            recommendations.extend(["✅ 安全な維持率です", "💪 通常通りの取引が可能"])

        return recommendations

    def should_warn_user(self, margin_prediction: MarginPrediction) -> Tuple[bool, str]:
        """
        ユーザー警告が必要かを判定

        Args:
            margin_prediction: 維持率予測結果

        Returns:
            (警告必要, 警告メッセージ) のタプル
        """
        future_ratio = margin_prediction.future_margin_ratio
        current_ratio = margin_prediction.current_margin.margin_ratio

        critical_threshold = get_threshold("margin.thresholds.warning", 100.0)
        warning_threshold = get_threshold("margin.thresholds.caution", 150.0)
        large_drop_threshold = get_threshold("margin.large_drop_threshold", 50.0)

        # 100%を下回る予測の場合
        if future_ratio < critical_threshold:
            return (
                True,
                f"🚨 危険：このエントリーで維持率が{future_ratio:.1f}%に低下します（追証発生）",
            )

        # 大幅に維持率が低下する場合
        if current_ratio - future_ratio > large_drop_threshold:
            return (
                True,
                f"⚠️ 警告：維持率が大幅低下します（{current_ratio:.1f}% → {future_ratio:.1f}%）",
            )

        # 150%を下回る場合
        if future_ratio < warning_threshold:
            return (True, f"⚠️ 注意：エントリー後の維持率は{future_ratio:.1f}%になります")

        return False, ""

    async def check_balance_sufficiency(
        self,
        required_amount: float,
        current_balance: float,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> Dict[str, Any]:
        """
        残高充足性チェック

        Args:
            required_amount: 必要金額（JPY）
            current_balance: 現在残高（JPY）
            bitbank_client: Bitbank APIクライアント

        Returns:
            チェック結果
        """
        is_sufficient = current_balance >= required_amount

        # APIから利用可能残高を取得
        available_balance = current_balance
        if bitbank_client and not is_backtest_mode():
            try:
                margin_status = await bitbank_client.fetch_margin_status()
                if margin_status and "available_balance" in margin_status:
                    available_balance = float(margin_status["available_balance"])
            except Exception as e:
                self.logger.warning(f"⚠️ 利用可能残高取得失敗: {e}")

        is_available_sufficient = available_balance >= required_amount

        result = {
            "sufficient": is_sufficient and is_available_sufficient,
            "current_balance": current_balance,
            "available_balance": available_balance,
            "required_amount": required_amount,
            "shortage": max(0, required_amount - min(current_balance, available_balance)),
        }

        if not result["sufficient"]:
            self.logger.warning(
                f"⚠️ 残高不足: 必要 {required_amount:.0f}円, "
                f"現在 {current_balance:.0f}円, "
                f"利用可能 {available_balance:.0f}円"
            )

        return result
