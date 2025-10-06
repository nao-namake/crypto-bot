"""
保証金維持率監視システム（Phase 28完了・Phase 29最適化）

目的:
- 保証金維持率の計算と監視のみを行う（制限や強制決済は実装しない）
- 現在の59%という危険な維持率を可視化
- 将来的な制限機能の基盤を提供

設計思想:
- 安全優先：監視・警告のみで既存システムに影響を与えない
- 段階的実装：Phase 29最適化完了・制限機能基盤確立
- データ収集：実際の維持率推移を記録して改善策を検討

主要機能:
- 現在の保証金維持率計算
- 新規ポジション追加後の予測維持率計算
- 状態判定（SAFE/CAUTION/WARNING/CRITICAL）
- Discord通知連携準備
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..core.logger import get_logger
from ..data.bitbank_client import get_bitbank_client


class MarginStatus(Enum):
    """保証金維持率の状態."""

    SAFE = "safe"  # 200%以上 - 安全
    CAUTION = "caution"  # 150-200% - 注意
    WARNING = "warning"  # 100-150% - 警告
    CRITICAL = "critical"  # 100%未満 - 危険（追証発生レベル）


@dataclass
class MarginData:
    """保証金関連データ."""

    current_balance: float  # 現在の口座残高（JPY）
    position_value_jpy: float  # 建玉総額（JPY換算）
    margin_ratio: float  # 保証金維持率（%）
    status: MarginStatus  # 状態
    message: str  # 状態メッセージ
    timestamp: datetime = None  # 計算時刻


@dataclass
class MarginPrediction:
    """新規ポジション追加後の維持率予測."""

    current_margin: MarginData  # 現在の維持率
    future_margin_ratio: float  # 予測維持率（%）
    future_status: MarginStatus  # 予測状態
    position_size_btc: float  # 追加するポジションサイズ（BTC）
    btc_price: float  # BTC価格（JPY）
    recommendation: str  # 推奨アクション


class MarginMonitor:
    """
    保証金維持率監視システム.

    監視のみを行い、制限や強制決済は実装しない。
    既存のPhase 25機能（動的ポジションサイジング等）と統合して使用。
    """

    def __init__(self, use_api_direct: bool = True):
        self.logger = get_logger(__name__)
        self.margin_history: List[MarginData] = []
        self.use_api_direct = use_api_direct  # Phase 27: APIから直接取得するか

    def calculate_margin_ratio(self, balance_jpy: float, position_value_jpy: float) -> float:
        """
        保証金維持率を計算（改善版・異常値対策）.

        Args:
            balance_jpy: 口座残高（JPY）
            position_value_jpy: 建玉総額（JPY換算）

        Returns:
            保証金維持率（%）。建玉がない場合は無限大を返す。
        """
        if position_value_jpy <= 0:
            return float("inf")  # 建玉なしの場合

        # 異常値対策: 建玉が極小値（1000円未満）の場合は安全値を返す
        min_position_value = 1000.0  # 最小建玉閾値
        if position_value_jpy < min_position_value:
            self.logger.debug(
                f"建玉が極小値: {position_value_jpy:.0f}円 < {min_position_value:.0f}円 - "
                f"維持率を安全値500%として扱う"
            )
            return 500.0  # 安全な維持率として扱う

        # 保証金維持率 = (受入保証金合計額 ÷ 建玉) × 100
        margin_ratio = (balance_jpy / position_value_jpy) * 100

        # 異常な高値（10000%以上）の場合はキャップする
        if margin_ratio > 10000.0:
            self.logger.warning(
                f"異常に高い保証金維持率検出: {margin_ratio:.1f}% - "
                f"残高={balance_jpy:.0f}円, 建玉={position_value_jpy:.0f}円 - 10000%にキャップ"
            )
            return 10000.0

        return max(0, margin_ratio)  # 負の値は0とする

    async def fetch_margin_ratio_from_api(self) -> Optional[float]:
        """
        bitbank APIから保証金維持率を直接取得（Phase 35: バックテストモード対応）

        Returns:
            保証金維持率（%）、取得失敗時はNone
        """
        if not self.use_api_direct:
            return None

        # Phase 35: バックテストモード時はAPI呼び出しスキップ
        try:
            from ..core.config import is_backtest_mode

            if is_backtest_mode():
                self.logger.debug("🎯 バックテストモード: API呼び出しをスキップ")
                return None
        except Exception:
            pass

        try:
            client = get_bitbank_client()
            margin_status = await client.fetch_margin_status()

            api_margin_ratio = margin_status.get("margin_ratio")
            if api_margin_ratio is not None:
                self.logger.info(
                    f"📡 API直接取得成功: 保証金維持率 {api_margin_ratio:.1f}%",
                    extra_data={
                        "margin_ratio": api_margin_ratio,
                        "method": "api_direct",
                        "available_balance": margin_status.get("available_balance"),
                        "margin_call_status": margin_status.get("margin_call_status"),
                    },
                )
                return float(api_margin_ratio)
            else:
                self.logger.warning("⚠️ API応答に保証金維持率データが含まれていません")
                return None

        except Exception as e:
            self.logger.warning(
                f"⚠️ API直接取得失敗、計算方式にフォールバック: {e}",
                extra_data={"error_type": type(e).__name__},
            )
            return None

    def get_margin_status(self, margin_ratio: float) -> Tuple[MarginStatus, str]:
        """
        維持率に基づく状態判定.

        Args:
            margin_ratio: 保証金維持率（%）

        Returns:
            (状態, メッセージ) のタプル
        """
        if margin_ratio >= 200:
            return MarginStatus.SAFE, "✅ 安全な維持率です"
        elif margin_ratio >= 150:
            return MarginStatus.CAUTION, "⚠️ 維持率が低下しています"
        elif margin_ratio >= 100:
            return MarginStatus.WARNING, "⚠️ 警告: 維持率が低い状態です"
        else:
            return MarginStatus.CRITICAL, "🚨 危険: 追証発生レベルです"

    async def analyze_current_margin(
        self, balance_jpy: float, position_value_jpy: float
    ) -> MarginData:
        """
        現在の保証金状況を分析（Phase 27: API直接取得対応）

        Args:
            balance_jpy: 現在の口座残高（JPY）
            position_value_jpy: 現在の建玉総額（JPY換算）

        Returns:
            保証金分析結果
        """
        # Phase 27: まずAPIから直接取得を試行
        margin_ratio = await self.fetch_margin_ratio_from_api()

        # API取得失敗時は従来の計算方式にフォールバック
        if margin_ratio is None:
            margin_ratio = self.calculate_margin_ratio(balance_jpy, position_value_jpy)
            self.logger.debug("📐 保証金維持率: 計算方式使用")
        else:
            self.logger.debug("📡 保証金維持率: API直接取得使用")

        status, message = self.get_margin_status(margin_ratio)

        margin_data = MarginData(
            current_balance=balance_jpy,
            position_value_jpy=position_value_jpy,
            margin_ratio=margin_ratio,
            status=status,
            message=message,
            timestamp=datetime.now(),
        )

        # 履歴に追加（最新100件まで保持）
        self.margin_history.append(margin_data)
        if len(self.margin_history) > 100:
            self.margin_history = self.margin_history[-100:]

        # ログ出力（制限はしない）
        self.logger.info(
            f"📊 保証金維持率: {margin_ratio:.1f}% - {message}",
            extra_data={
                "margin_ratio": margin_ratio,
                "status": status.value,
                "balance": balance_jpy,
                "position_value": position_value_jpy,
            },
        )

        return margin_data

    async def predict_future_margin(
        self,
        current_balance_jpy: float,
        current_position_value_jpy: float,
        new_position_size_btc: float,
        btc_price_jpy: float,
    ) -> MarginPrediction:
        """
        新規ポジション追加後の維持率を予測（Phase 27: API直接取得対応）

        Args:
            current_balance_jpy: 現在の残高（JPY）
            current_position_value_jpy: 現在の建玉総額（JPY）
            new_position_size_btc: 新規ポジションサイズ（BTC）
            btc_price_jpy: BTC価格（JPY）

        Returns:
            維持率予測結果
        """
        # 現在の状況
        current_margin = await self.analyze_current_margin(
            current_balance_jpy, current_position_value_jpy
        )

        # 新規ポジション追加後の建玉総額
        new_position_value_jpy = new_position_size_btc * btc_price_jpy
        future_position_value = current_position_value_jpy + new_position_value_jpy

        # 予測維持率（残高は変わらない前提）
        future_margin_ratio = self.calculate_margin_ratio(
            current_balance_jpy, future_position_value
        )

        future_status, _ = self.get_margin_status(future_margin_ratio)

        # 推奨アクション
        if future_margin_ratio < 100:
            recommendation = "🚨 新規エントリー非推奨（追証リスク）"
        elif future_margin_ratio < 150:
            recommendation = "⚠️ ポジションサイズ削減を推奨"
        elif future_margin_ratio < 200:
            recommendation = "⚠️ 注意深く監視してください"
        else:
            recommendation = "✅ 問題なし"

        prediction = MarginPrediction(
            current_margin=current_margin,
            future_margin_ratio=future_margin_ratio,
            future_status=future_status,
            position_size_btc=new_position_size_btc,
            btc_price=btc_price_jpy,
            recommendation=recommendation,
        )

        # 警告ログ（制限はしない）
        # Phase 35.5: バックテストモードではログ抑制（不要なI/Oオーバーヘッド削減）
        import os

        is_backtest = os.environ.get("BACKTEST_MODE") == "true"

        if future_margin_ratio < current_margin.margin_ratio:
            if not is_backtest:  # Phase 35.5: バックテストモード時はログ出力しない
                self.logger.warning(
                    f"⚠️ 維持率低下予測: {current_margin.margin_ratio:.1f}% → {future_margin_ratio:.1f}%",
                    extra_data={
                        "current_ratio": current_margin.margin_ratio,
                        "future_ratio": future_margin_ratio,
                        "position_size": new_position_size_btc,
                        "recommendation": recommendation,
                    },
                )

        return prediction

    def get_margin_summary(self) -> Dict[str, Any]:
        """
        保証金監視サマリーを取得.

        Returns:
            監視サマリー情報
        """
        if not self.margin_history:
            return {"status": "no_data", "message": "データがありません"}

        latest = self.margin_history[-1]

        # 過去の推移（最新10件）
        recent_history = (
            self.margin_history[-10:] if len(self.margin_history) >= 10 else self.margin_history
        )

        # トレンド分析（簡易）
        if len(recent_history) >= 2:
            first_ratio = recent_history[0].margin_ratio
            last_ratio = recent_history[-1].margin_ratio
            trend = (
                "improving"
                if last_ratio > first_ratio
                else "declining" if last_ratio < first_ratio else "stable"
            )
        else:
            trend = "insufficient_data"

        return {
            "current_status": {
                "margin_ratio": latest.margin_ratio,
                "status": latest.status.value,
                "message": latest.message,
                "timestamp": latest.timestamp.isoformat(),
            },
            "trend": trend,
            "history_count": len(self.margin_history),
            "recommendations": self._get_recommendations(latest),
        }

    def _get_recommendations(self, margin_data: MarginData) -> List[str]:
        """
        現在の維持率に基づく推奨アクション.

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
        ユーザー警告が必要かを判定.

        Args:
            margin_prediction: 維持率予測結果

        Returns:
            (警告必要, 警告メッセージ) のタプル
        """
        future_ratio = margin_prediction.future_margin_ratio
        current_ratio = margin_prediction.current_margin.margin_ratio

        # 100%を下回る予測の場合は必ず警告
        if future_ratio < 100:
            return (
                True,
                f"🚨 危険：このエントリーで維持率が{future_ratio:.1f}%に低下します（追証発生）",
            )

        # 大幅に維持率が低下する場合（50%以上低下）
        if current_ratio - future_ratio > 50:
            return (
                True,
                f"⚠️ 警告：維持率が大幅低下します（{current_ratio:.1f}% → {future_ratio:.1f}%）",
            )

        # 150%を下回る場合は軽い警告
        if future_ratio < 150:
            return True, f"⚠️ 注意：エントリー後の維持率は{future_ratio:.1f}%になります"

        return False, ""
