"""
取引統合サービス
MLStrategy・ExecutionClient・統計システムの完全統合
"""

import logging
from datetime import datetime
from typing import Any, Dict

from .enhanced_status_manager import EnhancedStatusManager


class TradingIntegrationService:
    """取引統合サービスメインクラス"""

    def __init__(self, base_dir: str = ".", initial_balance: float = 100000.0):
        self.base_dir = base_dir
        self.initial_balance = initial_balance

        # 拡張ステータス管理システム初期化
        self.status_manager = EnhancedStatusManager(base_dir)

        # 内部状態
        self.active_trades: Dict[str, Dict[str, Any]] = {}
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}

        # ログ設定
        self.logger = logging.getLogger(__name__)

        # 監視開始
        self.status_manager.start_monitoring()

        self.logger.info("取引統合サービスを初期化しました")

    def integrate_with_ml_strategy(self, ml_strategy):
        """MLStrategyとの統合"""
        # MLStrategyのフック設定
        original_execute_trade = getattr(ml_strategy, "execute_trade", None)
        original_update_position = getattr(ml_strategy, "update_position", None)

        if original_execute_trade:

            def enhanced_execute_trade(*args, **kwargs):
                # オリジナルのexecute_trade実行
                result = original_execute_trade(*args, **kwargs)

                # 統計システムに記録
                self._record_ml_strategy_trade(ml_strategy, result, *args, **kwargs)

                return result

            # フック適用
            ml_strategy.execute_trade = enhanced_execute_trade

        if original_update_position:

            def enhanced_update_position(*args, **kwargs):
                # オリジナルのupdate_position実行
                result = original_update_position(*args, **kwargs)

                # 市場データ更新
                self._update_market_data_from_strategy(ml_strategy)

                return result

            # フック適用
            ml_strategy.update_position = enhanced_update_position

        self.logger.info("MLStrategyとの統合を完了しました")

    def integrate_with_execution_client(self, execution_client):
        """ExecutionClientとの統合"""
        # ExecutionClientのフック設定
        original_create_order = getattr(execution_client, "create_order", None)
        _ = getattr(execution_client, "cancel_order", None)

        if original_create_order:

            def enhanced_create_order(*args, **kwargs):
                # 取引エントリー記録
                trade_id = self._record_trade_entry(execution_client, *args, **kwargs)

                # オリジナルのcreate_order実行
                result = original_create_order(*args, **kwargs)

                # 結果に応じて取引状態更新
                self._update_trade_from_order_result(trade_id, result)

                return result

            # フック適用
            execution_client.create_order = enhanced_create_order

        self.logger.info("ExecutionClientとの統合を完了しました")

    def record_trade_signal(
        self,
        signal: str,
        confidence: float,
        strategy_type: str = "ML",
        expected_profit: float = 0.0,
        risk_level: str = "medium",
        market_conditions: Dict[str, Any] = None,
    ) -> str:
        """取引シグナル記録"""
        # シグナル強度計算（信頼度ベース）
        signal_strength = confidence

        # 追加パラメータ
        extra_params = {
            "expected_profit": expected_profit,
            "risk_assessment": risk_level,
        }

        if market_conditions:
            extra_params.update(market_conditions)

        # ステータス管理システムに記録
        self.status_manager.update_trading_signal(
            signal=signal,
            strength=signal_strength,
            confidence=confidence,
            source=strategy_type,
            **extra_params,
        )

        signal_id = f"signal_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        self.logger.info(
            f"取引シグナル記録: {signal_id} - {signal} (信頼度: {confidence})"
        )

        return signal_id

    def record_market_update(
        self,
        symbol: str,
        price: float,
        volume: float = None,
        bid: float = None,
        ask: float = None,
        **kwargs,
    ) -> None:
        """市場データ更新記録"""
        # ビッドアスクスプレッド計算
        bid_ask_spread = None
        if bid and ask:
            bid_ask_spread = ask - bid

        # 価格変動計算（前回価格との比較）
        price_change_24h = kwargs.get("price_change_24h", 0.0)
        price_change_percentage = kwargs.get("price_change_percentage", 0.0)

        # トレンド判定
        trend = "neutral"
        if price_change_percentage > 1.0:
            trend = "bullish"
        elif price_change_percentage < -1.0:
            trend = "bearish"

        # ステータス管理システムに記録
        self.status_manager.update_market_data(
            price=price,
            volume=volume,
            bid_ask_spread=bid_ask_spread,
            price_change_24h=price_change_24h,
            price_change_percentage=price_change_percentage,
            trend=trend,
            **kwargs,
        )

        self.logger.debug(f"市場データ更新: {symbol} @ {price}")

    def execute_integrated_trade(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float = None,
        strategy_type: str = "ML",
        confidence: float = 0.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """統合取引実行"""
        try:
            # 取引エントリー記録
            trade_id = self.status_manager.record_trade_entry(
                symbol=symbol,
                side=side,
                entry_price=price or 0.0,
                quantity=amount,
                strategy_type=strategy_type,
                confidence_score=confidence,
                entry_fee=kwargs.get("entry_fee", 0.0),
            )

            # アクティブ取引に追加
            self.active_trades[trade_id] = {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "entry_price": price,
                "strategy_type": strategy_type,
                "confidence": confidence,
                "timestamp": datetime.now(),
                "status": "open",
                **kwargs,
            }

            self.logger.info(f"統合取引実行: {trade_id} - {side} {amount} {symbol}")

            return {
                "success": True,
                "trade_id": trade_id,
                "message": f"取引エントリー成功: {trade_id}",
                "details": {
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "strategy": strategy_type,
                },
            }

        except Exception as e:
            self.logger.error(f"統合取引実行エラー: {e}")
            return {
                "success": False,
                "trade_id": None,
                "message": f"取引エントリーエラー: {str(e)}",
                "error": str(e),
            }

    def close_integrated_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_fee: float = 0.0,
        reason: str = "manual",
    ) -> Dict[str, Any]:
        """統合取引決済"""
        try:
            # 取引決済記録
            success = self.status_manager.record_trade_exit(
                trade_id, exit_price, exit_fee
            )

            if success and trade_id in self.active_trades:
                # アクティブ取引から削除
                trade_info = self.active_trades.pop(trade_id)

                # 決済情報追加
                trade_info.update(
                    {
                        "exit_price": exit_price,
                        "exit_fee": exit_fee,
                        "exit_reason": reason,
                        "exit_timestamp": datetime.now(),
                        "status": "closed",
                    }
                )

                self.logger.info(f"統合取引決済: {trade_id} @ {exit_price}")

                return {
                    "success": True,
                    "trade_id": trade_id,
                    "message": f"取引決済成功: {trade_id}",
                    "trade_info": trade_info,
                }
            else:
                return {
                    "success": False,
                    "trade_id": trade_id,
                    "message": f"取引決済失敗: {trade_id}",
                    "error": "取引が見つかりません",
                }

        except Exception as e:
            self.logger.error(f"統合取引決済エラー: {e}")
            return {
                "success": False,
                "trade_id": trade_id,
                "message": f"取引決済エラー: {str(e)}",
                "error": str(e),
            }

    def get_trading_status(self) -> Dict[str, Any]:
        """取引状況取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "active_trades": len(self.active_trades),
            "active_trade_details": self.active_trades,
            "comprehensive_status": self.status_manager.get_comprehensive_status(),
            "performance_summary": (
                self.status_manager.stats_manager.get_performance_summary()
            ),
        }

    def get_performance_report(self) -> str:
        """パフォーマンスレポート取得"""
        # 統計レポート
        stats_report = self.status_manager.stats_manager.generate_detailed_report()

        # ステータスレポート
        status_report = self.status_manager.generate_status_report()

        # 統合レポート
        integrated_report = []
        integrated_report.append("=" * 80)
        integrated_report.append("🎯 取引統合システム総合レポート")
        integrated_report.append("=" * 80)
        integrated_report.append(
            f"📅 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        integrated_report.append("")
        integrated_report.append("📊 アクティブ取引状況:")
        integrated_report.append(f"   アクティブ取引数: {len(self.active_trades)}")

        if self.active_trades:
            for trade_id, trade_info in self.active_trades.items():
                integrated_report.append(
                    f"   - {trade_id}: {trade_info['side']} "
                    f"{trade_info['amount']} {trade_info['symbol']}"
                )

        integrated_report.append("")
        integrated_report.append(status_report)
        integrated_report.append("")
        integrated_report.append(stats_report)

        return "\n".join(integrated_report)

    def _record_ml_strategy_trade(self, ml_strategy, result, *args, **kwargs):
        """MLStrategy取引記録"""
        try:
            # MLStrategyの結果から取引情報を抽出
            if result and isinstance(result, dict):
                symbol = result.get("symbol", "BTC/JPY")
                side = result.get("side", "buy")
                amount = result.get("amount", 0.0)
                price = result.get("price", 0.0)

                # 取引記録
                self.execute_integrated_trade(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=price,
                    strategy_type="ML_Strategy",
                    confidence=getattr(ml_strategy, "last_confidence", 0.0),
                )

        except Exception as e:
            self.logger.error(f"MLStrategy取引記録エラー: {e}")

    def _update_market_data_from_strategy(self, ml_strategy):
        """MLStrategyから市場データ更新"""
        try:
            # MLStrategyから市場データを取得
            if hasattr(ml_strategy, "current_price"):
                price = ml_strategy.current_price
                symbol = getattr(ml_strategy, "symbol", "BTC/JPY")

                self.record_market_update(symbol=symbol, price=price)

        except Exception as e:
            self.logger.error(f"市場データ更新エラー: {e}")

    def _record_trade_entry(self, execution_client, *args, **kwargs) -> str:
        """取引エントリー記録（ExecutionClient用）"""
        try:
            # ExecutionClientのパラメータから取引情報抽出
            symbol = kwargs.get("symbol", args[0] if len(args) > 0 else "BTC/JPY")
            side = kwargs.get("side", args[1] if len(args) > 1 else "buy")
            amount = kwargs.get("amount", args[2] if len(args) > 2 else 0.0)
            price = kwargs.get("price", args[3] if len(args) > 3 else 0.0)

            trade_id = self.status_manager.record_trade_entry(
                symbol=symbol,
                side=side,
                entry_price=price,
                quantity=amount,
                strategy_type="ExecutionClient",
                confidence_score=0.0,
                entry_fee=kwargs.get("fee", 0.0),
            )

            return trade_id

        except Exception as e:
            self.logger.error(f"取引エントリー記録エラー: {e}")
            return f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _update_trade_from_order_result(self, trade_id: str, order_result):
        """注文結果から取引状態更新"""
        try:
            if order_result and isinstance(order_result, dict):
                if order_result.get("status") == "filled":
                    # 約定済みの場合、決済として記録
                    exit_price = order_result.get("price", 0.0)
                    exit_fee = order_result.get("fee", 0.0)

                    self.status_manager.record_trade_exit(
                        trade_id, exit_price, exit_fee
                    )

        except Exception as e:
            self.logger.error(f"取引状態更新エラー: {e}")

    def shutdown(self):
        """サービス終了処理"""
        try:
            # 監視停止
            self.status_manager.stop_monitoring()

            # アクティブ取引の強制決済（オプション）
            if self.active_trades:
                self.logger.warning(
                    f"アクティブ取引が残っています: {len(self.active_trades)}"
                )

            self.logger.info("取引統合サービスを終了しました")

        except Exception as e:
            self.logger.error(f"サービス終了エラー: {e}")


def main():
    """テスト実行"""
    # 取引統合サービス初期化
    integration_service = TradingIntegrationService()

    # テストシグナル記録
    _ = integration_service.record_trade_signal(
        signal="buy",
        confidence=0.8,
        strategy_type="ML_Enhanced",
        expected_profit=1000.0,
        risk_level="medium",
    )

    # テスト取引実行
    result = integration_service.execute_integrated_trade(
        symbol="BTC/JPY",
        side="buy",
        amount=0.0001,
        price=3000000.0,
        strategy_type="Test_Strategy",
        confidence=0.8,
    )

    print(f"取引結果: {result}")

    # 取引決済
    if result["success"]:
        close_result = integration_service.close_integrated_trade(
            trade_id=result["trade_id"],
            exit_price=3005000.0,
            exit_fee=150.0,
            reason="test_close",
        )
        print(f"決済結果: {close_result}")

    # レポート生成
    print("\n" + integration_service.get_performance_report())

    # サービス終了
    integration_service.shutdown()


if __name__ == "__main__":
    main()
