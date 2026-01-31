"""
TradingLogger テスト - カバレッジ向上対応

Phase 14-B で分離された取引ログ機能のテストを実装。
カバレッジ60%達成のための追加テスト。
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.logger import CryptoBotLogger
from src.core.services.trading_logger import TradingLoggerService


class TestTradingLoggerService:
    """TradingLoggerService メインテストクラス"""

    @pytest.fixture
    def mock_logger(self):
        """モックロガー"""
        return MagicMock(spec=CryptoBotLogger)

    @pytest.fixture
    def mock_orchestrator(self):
        """モックオーケストレーター"""
        orchestrator = MagicMock()
        orchestrator.execution_service = MagicMock()
        return orchestrator

    @pytest.fixture
    def trading_logger(self, mock_orchestrator, mock_logger):
        """TradingLoggerServiceインスタンス"""
        return TradingLoggerService(mock_orchestrator, mock_logger)

    def test_init(self, mock_orchestrator, mock_logger):
        """初期化テスト"""
        logger = TradingLoggerService(mock_orchestrator, mock_logger)

        assert logger.orchestrator == mock_orchestrator
        assert logger.logger == mock_logger
        assert logger.decision_map == {
            "approved": "🟢 取引承認",
            "conditional": "🟡 条件付き承認",
            "denied": "🔴 取引拒否",
        }

    @pytest.mark.asyncio
    async def test_log_trade_decision_approved(self, trading_logger):
        """取引決定ログ - 承認テスト"""
        # テストデータ準備
        evaluation = MagicMock()
        evaluation.decision = "approved"
        evaluation.risk_score = 0.123
        cycle_id = "test-cycle-001"

        await trading_logger.log_trade_decision(evaluation, cycle_id)

        trading_logger.logger.info.assert_called_once_with(
            "🟢 取引承認 - サイクル: test-cycle-001, リスクスコア: 0.123", discord_notify=True
        )

    @pytest.mark.asyncio
    async def test_log_trade_decision_denied(self, trading_logger):
        """取引決定ログ - 拒否テスト"""
        # テストデータ準備
        evaluation = MagicMock()
        evaluation.decision = "denied"
        evaluation.risk_score = 0.890
        cycle_id = "test-cycle-002"

        await trading_logger.log_trade_decision(evaluation, cycle_id)

        trading_logger.logger.info.assert_called_once_with(
            "🔴 取引拒否 - サイクル: test-cycle-002, リスクスコア: 0.890", discord_notify=True
        )

    @pytest.mark.asyncio
    async def test_log_trade_decision_conditional(self, trading_logger):
        """取引決定ログ - 条件付き承認テスト"""
        # テストデータ準備
        evaluation = MagicMock()
        evaluation.decision = "conditional"
        evaluation.risk_score = 0.456
        cycle_id = "test-cycle-003"

        await trading_logger.log_trade_decision(evaluation, cycle_id)

        trading_logger.logger.info.assert_called_once_with(
            "🟡 条件付き承認 - サイクル: test-cycle-003, リスクスコア: 0.456", discord_notify=False
        )

    @pytest.mark.asyncio
    async def test_log_trade_decision_unknown(self, trading_logger):
        """取引決定ログ - 未知の決定テスト"""
        # テストデータ準備
        evaluation = MagicMock()
        evaluation.decision = "unknown_decision"
        evaluation.risk_score = 0.500
        cycle_id = "test-cycle-004"

        await trading_logger.log_trade_decision(evaluation, cycle_id)

        trading_logger.logger.info.assert_called_once_with(
            "❓ 不明 - サイクル: test-cycle-004, リスクスコア: 0.500", discord_notify=False
        )

    @pytest.mark.asyncio
    async def test_log_trade_decision_missing_attributes(self, trading_logger):
        """取引決定ログ - 属性不足テスト"""
        # テストデータ準備（属性不足）
        evaluation = MagicMock()
        del evaluation.decision
        del evaluation.risk_score
        cycle_id = "test-cycle-005"

        await trading_logger.log_trade_decision(evaluation, cycle_id)

        trading_logger.logger.info.assert_called_once_with(
            "❓ 不明 - サイクル: test-cycle-005, リスクスコア: 0.000", discord_notify=False
        )

    @pytest.mark.asyncio
    async def test_log_trade_decision_exception(self, trading_logger):
        """取引決定ログ - 例外処理テスト"""
        # loggerのinfoメソッドで例外発生をシミュレート
        trading_logger.logger.info.side_effect = Exception("logging error")

        evaluation = MagicMock()
        evaluation.decision = "approved"
        evaluation.risk_score = 0.5

        await trading_logger.log_trade_decision(evaluation, "test-cycle-006")

        trading_logger.logger.error.assert_called_once_with("❌ 取引決定ログエラー: logging error")

    @pytest.mark.asyncio
    async def test_log_execution_result_none(self, trading_logger):
        """実行結果ログ - None結果テスト"""
        await trading_logger.log_execution_result(None, "test-cycle")

        # Noneの場合は何もログ出力されない
        trading_logger.logger.info.assert_not_called()
        trading_logger.logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_execution_result_success(self, trading_logger):
        """実行結果ログ - 成功テスト"""
        execution_result = MagicMock()
        execution_result.success = True

        with patch.object(trading_logger, "_log_successful_execution") as mock_success:
            await trading_logger.log_execution_result(execution_result, "test-cycle")

            mock_success.assert_called_once_with(execution_result, "test-cycle", "", "✅")

    @pytest.mark.asyncio
    async def test_log_execution_result_failure(self, trading_logger):
        """実行結果ログ - 失敗テスト"""
        execution_result = MagicMock()
        execution_result.success = False

        with patch.object(trading_logger, "_log_failed_execution") as mock_failure:
            await trading_logger.log_execution_result(execution_result, "test-cycle")

            mock_failure.assert_called_once_with(execution_result, "test-cycle", "", "❌")

    @pytest.mark.asyncio
    async def test_log_execution_result_with_stop(self, trading_logger):
        """実行結果ログ - ストップ注文テスト"""
        execution_result = MagicMock()
        execution_result.success = True

        with patch.object(trading_logger, "_log_successful_execution") as mock_success:
            await trading_logger.log_execution_result(execution_result, "test-cycle", is_stop=True)

            mock_success.assert_called_once_with(
                execution_result, "test-cycle", "🛑 自動決済: ", "✅"
            )

    @pytest.mark.asyncio
    async def test_log_successful_execution_buy(self, trading_logger):
        """成功時実行ログ - 買い注文テスト"""
        execution_result = MagicMock()
        execution_result.side = "buy"
        execution_result.amount = 0.1234
        execution_result.price = 3500000
        execution_result.paper_pnl = 5000
        execution_result.fee = 1500

        with patch.object(trading_logger, "_check_and_log_statistics") as mock_stats:
            await trading_logger._log_successful_execution(execution_result, "test-cycle", "", "✅")

            expected_message = (
                "✅ 📈 注文実行成功 - サイクル: test-cycle, "
                "サイド: BUY, 数量: 0.1234 BTC, 価格: ¥3,500,000, "
                "PnL: 💰¥5,000, 手数料: ¥1,500.00"  # Phase 51.8-J4-D: .2f対応
            )
            trading_logger.logger.info.assert_called_once_with(
                expected_message, discord_notify=True
            )
            mock_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_successful_execution_sell_loss(self, trading_logger):
        """成功時実行ログ - 売り注文（損失）テスト"""
        execution_result = MagicMock()
        execution_result.side = "sell"
        execution_result.amount = 0.0500
        execution_result.price = 3400000
        execution_result.paper_pnl = -2000
        execution_result.fee = 1200

        with patch.object(trading_logger, "_check_and_log_statistics") as mock_stats:
            await trading_logger._log_successful_execution(
                execution_result, "test-cycle-sell", "🛑 自動決済: ", "✅"
            )

            expected_message = (
                "🛑 自動決済: ✅ 📉 注文実行成功 - サイクル: test-cycle-sell, "
                "サイド: SELL, 数量: 0.0500 BTC, 価格: ¥3,400,000, "
                "PnL: 💸¥-2,000, 手数料: ¥1,200.00"  # Phase 51.8-J4-D: .2f対応
            )
            trading_logger.logger.info.assert_called_once_with(
                expected_message, discord_notify=True
            )

    @pytest.mark.asyncio
    async def test_log_successful_execution_no_pnl_no_fee(self, trading_logger):
        """成功時実行ログ - PnL/手数料なしテスト"""
        execution_result = MagicMock()
        execution_result.side = "buy"
        execution_result.amount = 0.0800
        execution_result.price = 3300000
        del execution_result.paper_pnl
        del execution_result.fee

        with patch.object(trading_logger, "_check_and_log_statistics"):
            await trading_logger._log_successful_execution(execution_result, "test-cycle", "", "✅")

            expected_message = (
                "✅ 📈 注文実行成功 - サイクル: test-cycle, "
                "サイド: BUY, 数量: 0.0800 BTC, 価格: ¥3,300,000"
            )
            trading_logger.logger.info.assert_called_once_with(
                expected_message, discord_notify=True
            )

    @pytest.mark.asyncio
    async def test_log_failed_execution(self, trading_logger):
        """失敗時実行ログテスト"""
        execution_result = MagicMock()
        execution_result.error_message = "API Error: Insufficient funds"

        await trading_logger._log_failed_execution(
            execution_result, "test-cycle-fail", "🛑 自動決済: ", "❌"
        )

        expected_message = (
            "🛑 自動決済: ❌ 注文実行失敗 - サイクル: test-cycle-fail, "
            "エラー: API Error: Insufficient funds"
        )
        trading_logger.logger.warning.assert_called_once_with(expected_message, discord_notify=True)

    @pytest.mark.asyncio
    async def test_log_failed_execution_no_error_message(self, trading_logger):
        """失敗時実行ログ - エラーメッセージなしテスト"""
        execution_result = MagicMock()
        execution_result.error_message = None

        await trading_logger._log_failed_execution(execution_result, "test-cycle-fail", "", "❌")

        expected_message = "❌ 注文実行失敗 - サイクル: test-cycle-fail, エラー: 不明"
        trading_logger.logger.warning.assert_called_once_with(expected_message, discord_notify=True)

    @pytest.mark.asyncio
    async def test_check_and_log_statistics_no_service(self, trading_logger):
        """統計チェック - execution_serviceなしテスト"""
        trading_logger.orchestrator.execution_service = None

        await trading_logger._check_and_log_statistics()

        # execution_serviceがなければ何もしない

    @pytest.mark.asyncio
    async def test_check_and_log_statistics_not_multiple_of_10(self, trading_logger):
        """統計チェック - 10の倍数でないテスト"""
        stats = {"statistics": {"total_trades": 7}}
        trading_logger.orchestrator.execution_service.get_trading_statistics.return_value = stats

        with patch.object(trading_logger, "log_trading_statistics") as mock_log_stats:
            await trading_logger._check_and_log_statistics()

            mock_log_stats.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_log_statistics_multiple_of_10(self, trading_logger):
        """統計チェック - 10の倍数テスト"""
        stats = {"statistics": {"total_trades": 20}}
        trading_logger.orchestrator.execution_service.get_trading_statistics.return_value = stats

        with patch.object(trading_logger, "log_trading_statistics") as mock_log_stats:
            await trading_logger._check_and_log_statistics()

            mock_log_stats.assert_called_once_with(stats)

    @pytest.mark.asyncio
    async def test_check_and_log_statistics_exception(self, trading_logger):
        """統計チェック - 例外処理テスト"""
        trading_logger.orchestrator.execution_service.get_trading_statistics.side_effect = (
            Exception("stats error")
        )

        await trading_logger._check_and_log_statistics()

        trading_logger.logger.error.assert_called_once_with("❌ 統計チェックエラー: stats error")

    @pytest.mark.asyncio
    async def test_log_trading_statistics_success(self, trading_logger):
        """取引統計ログ出力テスト"""
        stats = {
            "statistics": {"total_trades": 50, "winning_trades": 32, "win_rate": 0.64},
            "current_balance": 1150000,
            "initial_balance": 1000000,
            "return_rate": 0.15,
        }

        await trading_logger.log_trading_statistics(stats)

        expected_message = (
            "📊 取引統計サマリー\n"
            "・総取引数: 50回\n"
            "・勝ち取引: 32回\n"
            "・勝率: 64.0%\n"
            "・現在残高: ¥1,150,000\n"
            "・リターン率: +15.00%"
        )
        trading_logger.logger.info.assert_called_once_with(expected_message, discord_notify=True)

    def test_format_performance_summary_success(self, trading_logger):
        """パフォーマンスサマリーフォーマット成功テスト"""
        stats = {
            "statistics": {"total_trades": 30, "winning_trades": 18, "win_rate": 0.6},
            "current_balance": 1200000,
            "initial_balance": 1000000,
            "return_rate": 0.2,
        }

        result = trading_logger.format_performance_summary(stats)

        expected = {
            "total_trades": 30,
            "winning_trades": 18,
            "win_rate_percent": 60.0,
            "current_balance": 1200000,
            "return_rate_percent": 20.0,
            "profit_loss": 200000,
        }

        assert result == expected

    def test_format_performance_summary_missing_data(self, trading_logger):
        """パフォーマンスサマリーフォーマット - データ不足テスト"""
        stats = {}

        result = trading_logger.format_performance_summary(stats)

        expected = {
            "total_trades": 0,
            "winning_trades": 0,
            "win_rate_percent": 0.0,
            "current_balance": 0,
            "return_rate_percent": 0.0,
            "profit_loss": -1000000,  # initial_balance (1000000) - current_balance (0)
        }

        assert result == expected

    def test_format_performance_summary_exception(self, trading_logger):
        """パフォーマンスサマリーフォーマット - 例外処理テスト"""
        stats = MagicMock()
        stats.get.side_effect = Exception("format error")

        result = trading_logger.format_performance_summary(stats)

        assert result == {}
        trading_logger.logger.error.assert_called_once_with(
            "❌ パフォーマンスサマリーフォーマットエラー: format error"
        )

    @pytest.mark.asyncio
    async def test_log_cycle_start(self, trading_logger):
        """サイクル開始ログテスト"""
        cycle_id = "cycle-start-001"

        await trading_logger.log_cycle_start(cycle_id)

        trading_logger.logger.debug.assert_called_once_with(
            "🔄 取引サイクル開始 - ID: cycle-start-001"
        )

    @pytest.mark.asyncio
    async def test_log_cycle_end(self, trading_logger):
        """サイクル終了ログテスト"""
        cycle_id = "cycle-end-001"
        duration = 15.67

        await trading_logger.log_cycle_end(cycle_id, duration)

        trading_logger.logger.debug.assert_called_once_with(
            "✅ 取引サイクル完了 - ID: cycle-end-001, 実行時間: 15.67秒"
        )

    # ========== 追加テストケース（カバレッジ向上用） ==========

    @pytest.mark.asyncio
    async def test_log_trade_decision_with_enum(self, trading_logger):
        """取引決定ログ - Enum型decisionテスト（Phase 57.2対応）"""
        # Enum型のdecisionをモック
        evaluation = MagicMock()
        mock_decision = MagicMock()
        mock_decision.value = "approved"
        evaluation.decision = mock_decision
        evaluation.risk_score = 0.250
        cycle_id = "test-cycle-enum"

        await trading_logger.log_trade_decision(evaluation, cycle_id)

        trading_logger.logger.info.assert_called_once_with(
            "🟢 取引承認 - サイクル: test-cycle-enum, リスクスコア: 0.250", discord_notify=True
        )

    @pytest.mark.asyncio
    async def test_log_execution_result_dict_success(self, trading_logger):
        """実行結果ログ - 辞書型成功テスト"""
        execution_result = {"success": True}

        with patch.object(trading_logger, "_log_successful_execution") as mock_success:
            await trading_logger.log_execution_result(execution_result, "test-cycle-dict")

            mock_success.assert_called_once_with(execution_result, "test-cycle-dict", "", "✅")

    @pytest.mark.asyncio
    async def test_log_execution_result_dict_failure(self, trading_logger):
        """実行結果ログ - 辞書型失敗テスト"""
        execution_result = {"success": False, "error_message": "API Error"}

        with patch.object(trading_logger, "_log_failed_execution") as mock_failure:
            await trading_logger.log_execution_result(execution_result, "test-cycle-dict-fail")

            mock_failure.assert_called_once_with(execution_result, "test-cycle-dict-fail", "", "❌")

    @pytest.mark.asyncio
    async def test_log_execution_result_unexpected_type(self, trading_logger):
        """実行結果ログ - 予期しない型テスト"""
        # success属性を持たず、辞書でもない型
        execution_result = "unexpected_string"

        with patch.object(trading_logger, "_log_failed_execution") as mock_failure:
            await trading_logger.log_execution_result(execution_result, "test-cycle-unexpected")

            # 予期しない型の場合、warningログ出力後、success=Falseとして処理
            trading_logger.logger.warning.assert_called_once()
            mock_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_execution_result_key_error(self, trading_logger):
        """実行結果ログ - KeyError例外テスト"""
        execution_result = MagicMock()
        execution_result.success = True

        with patch.object(
            trading_logger, "_log_successful_execution", side_effect=KeyError("missing_key")
        ):
            await trading_logger.log_execution_result(execution_result, "test-cycle-keyerror")

            trading_logger.logger.error.assert_called_once_with(
                "実行結果ログデータアクセスエラー: 'missing_key'"
            )

    @pytest.mark.asyncio
    async def test_log_execution_result_attribute_error(self, trading_logger):
        """実行結果ログ - AttributeError例外テスト"""
        execution_result = MagicMock()
        execution_result.success = True

        with patch.object(
            trading_logger,
            "_log_successful_execution",
            side_effect=AttributeError("missing_attr"),
        ):
            await trading_logger.log_execution_result(execution_result, "test-cycle-attrerror")

            trading_logger.logger.error.assert_called_once_with(
                "実行結果ログデータアクセスエラー: missing_attr"
            )

    @pytest.mark.asyncio
    async def test_log_execution_result_value_error(self, trading_logger):
        """実行結果ログ - ValueError例外テスト"""
        execution_result = MagicMock()
        execution_result.success = True

        with patch.object(
            trading_logger,
            "_log_successful_execution",
            side_effect=ValueError("invalid_value"),
        ):
            await trading_logger.log_execution_result(execution_result, "test-cycle-valerror")

            trading_logger.logger.error.assert_called_once_with(
                "実行結果ログデータ変換エラー: invalid_value"
            )

    @pytest.mark.asyncio
    async def test_log_execution_result_type_error(self, trading_logger):
        """実行結果ログ - TypeError例外テスト"""
        execution_result = MagicMock()
        execution_result.success = True

        with patch.object(
            trading_logger,
            "_log_successful_execution",
            side_effect=TypeError("type_mismatch"),
        ):
            await trading_logger.log_execution_result(execution_result, "test-cycle-typeerror")

            trading_logger.logger.error.assert_called_once_with(
                "実行結果ログデータ変換エラー: type_mismatch"
            )

    @pytest.mark.asyncio
    async def test_log_execution_result_general_exception(self, trading_logger):
        """実行結果ログ - 一般例外テスト"""
        execution_result = MagicMock()
        execution_result.success = True

        with patch.object(
            trading_logger,
            "_log_successful_execution",
            side_effect=RuntimeError("unexpected"),
        ):
            await trading_logger.log_execution_result(execution_result, "test-cycle-general")

            trading_logger.logger.error.assert_called_once_with(
                "実行結果ログ出力予期しないエラー: unexpected"
            )

    @pytest.mark.asyncio
    async def test_log_successful_execution_backtest_mode(self, trading_logger):
        """成功時実行ログ - バックテストモードテスト"""
        execution_result = MagicMock()
        execution_result.side = "buy"
        execution_result.amount = 0.1000
        execution_result.price = 3000000
        del execution_result.paper_pnl
        del execution_result.fee

        with patch.object(trading_logger, "_check_and_log_statistics"):
            with patch.dict("os.environ", {"BACKTEST_MODE": "true"}):
                await trading_logger._log_successful_execution(
                    execution_result, "test-cycle-backtest", "", "✅"
                )

                # バックテスト時はwarningレベルで出力
                trading_logger.logger.warning.assert_called_once()
                trading_logger.logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_successful_execution_exception(self, trading_logger):
        """成功時実行ログ - 例外処理テスト"""
        execution_result = MagicMock()
        # side属性アクセスで例外発生
        type(execution_result).side = property(
            lambda self: (_ for _ in ()).throw(Exception("side_error"))
        )

        with patch.object(trading_logger, "_check_and_log_statistics"):
            await trading_logger._log_successful_execution(
                execution_result, "test-cycle-exc", "", "✅"
            )

            trading_logger.logger.error.assert_called_once_with(
                "❌ 成功時実行ログエラー: side_error"
            )

    @pytest.mark.asyncio
    async def test_log_failed_execution_dict(self, trading_logger):
        """失敗時実行ログ - 辞書型テスト"""
        execution_result = {"error_message": "Connection timeout"}

        await trading_logger._log_failed_execution(
            execution_result, "test-cycle-dict-fail", "", "❌"
        )

        expected_message = (
            "❌ 注文実行失敗 - サイクル: test-cycle-dict-fail, エラー: Connection timeout"
        )
        trading_logger.logger.warning.assert_called_once_with(expected_message, discord_notify=True)

    @pytest.mark.asyncio
    async def test_log_failed_execution_dict_no_error_message(self, trading_logger):
        """失敗時実行ログ - 辞書型エラーメッセージなしテスト"""
        execution_result = {}

        await trading_logger._log_failed_execution(
            execution_result, "test-cycle-dict-no-err", "", "❌"
        )

        expected_message = "❌ 注文実行失敗 - サイクル: test-cycle-dict-no-err, エラー: 不明"
        trading_logger.logger.warning.assert_called_once_with(expected_message, discord_notify=True)

    @pytest.mark.asyncio
    async def test_log_failed_execution_exception(self, trading_logger):
        """失敗時実行ログ - 例外処理テスト"""
        execution_result = MagicMock()
        # error_message属性アクセスで例外発生
        type(execution_result).error_message = property(
            lambda self: (_ for _ in ()).throw(Exception("attr_error"))
        )

        await trading_logger._log_failed_execution(
            execution_result, "test-cycle-fail-exc", "", "❌"
        )

        trading_logger.logger.error.assert_called_once_with("❌ 失敗時実行ログエラー: attr_error")

    @pytest.mark.asyncio
    async def test_check_and_log_statistics_zero_trades(self, trading_logger):
        """統計チェック - 取引数0テスト"""
        stats = {"statistics": {"total_trades": 0}}
        trading_logger.orchestrator.execution_service.get_trading_statistics.return_value = stats

        with patch.object(trading_logger, "log_trading_statistics") as mock_log_stats:
            await trading_logger._check_and_log_statistics()

            # total_trades=0は10の倍数だが、0は出力対象外
            mock_log_stats.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_log_statistics_no_execution_service_attr(self, trading_logger):
        """統計チェック - execution_service属性なしテスト"""
        del trading_logger.orchestrator.execution_service

        # 例外が発生しないことを確認
        await trading_logger._check_and_log_statistics()

    @pytest.mark.asyncio
    async def test_log_trading_statistics_key_error(self, trading_logger):
        """取引統計ログ - KeyError例外テスト"""
        stats = MagicMock()
        stats.get.side_effect = KeyError("missing_key")

        await trading_logger.log_trading_statistics(stats)

        trading_logger.logger.error.assert_called_once_with(
            "統計ログデータアクセスエラー: 'missing_key'"
        )

    @pytest.mark.asyncio
    async def test_log_trading_statistics_attribute_error(self, trading_logger):
        """取引統計ログ - AttributeError例外テスト"""
        stats = MagicMock()
        stats.get.side_effect = AttributeError("missing_attr")

        await trading_logger.log_trading_statistics(stats)

        trading_logger.logger.error.assert_called_once_with(
            "統計ログデータアクセスエラー: missing_attr"
        )

    @pytest.mark.asyncio
    async def test_log_trading_statistics_value_error(self, trading_logger):
        """取引統計ログ - ValueError例外テスト"""
        stats = MagicMock()
        stats.get.side_effect = ValueError("invalid_value")

        await trading_logger.log_trading_statistics(stats)

        trading_logger.logger.error.assert_called_once_with(
            "統計ログデータ変換エラー: invalid_value"
        )

    @pytest.mark.asyncio
    async def test_log_trading_statistics_type_error(self, trading_logger):
        """取引統計ログ - TypeError例外テスト"""
        stats = MagicMock()
        stats.get.side_effect = TypeError("type_mismatch")

        await trading_logger.log_trading_statistics(stats)

        trading_logger.logger.error.assert_called_once_with(
            "統計ログデータ変換エラー: type_mismatch"
        )

    @pytest.mark.asyncio
    async def test_log_trading_statistics_zero_division_error(self, trading_logger):
        """取引統計ログ - ZeroDivisionError例外テスト"""
        stats = MagicMock()
        stats.get.side_effect = ZeroDivisionError("division by zero")

        await trading_logger.log_trading_statistics(stats)

        trading_logger.logger.error.assert_called_once_with("統計ログ計算エラー: division by zero")

    @pytest.mark.asyncio
    async def test_log_trading_statistics_arithmetic_error(self, trading_logger):
        """取引統計ログ - ArithmeticError例外テスト"""
        stats = MagicMock()
        stats.get.side_effect = ArithmeticError("arithmetic error")

        await trading_logger.log_trading_statistics(stats)

        trading_logger.logger.error.assert_called_once_with("統計ログ計算エラー: arithmetic error")

    @pytest.mark.asyncio
    async def test_log_trading_statistics_general_exception(self, trading_logger):
        """取引統計ログ - 一般例外テスト"""
        stats = MagicMock()
        stats.get.side_effect = RuntimeError("unexpected")

        await trading_logger.log_trading_statistics(stats)

        trading_logger.logger.error.assert_called_once_with(
            "統計ログ出力予期しないエラー: unexpected"
        )

    @pytest.mark.asyncio
    async def test_log_cycle_start_exception(self, trading_logger):
        """サイクル開始ログ - 例外処理テスト"""
        trading_logger.logger.debug.side_effect = Exception("debug_error")

        await trading_logger.log_cycle_start("test-cycle-exc")

        trading_logger.logger.error.assert_called_once_with(
            "❌ サイクル開始ログエラー: debug_error"
        )

    @pytest.mark.asyncio
    async def test_log_cycle_end_exception(self, trading_logger):
        """サイクル終了ログ - 例外処理テスト"""
        trading_logger.logger.debug.side_effect = Exception("debug_error")

        await trading_logger.log_cycle_end("test-cycle-exc", 10.5)

        trading_logger.logger.error.assert_called_once_with(
            "❌ サイクル終了ログエラー: debug_error"
        )

    @pytest.mark.asyncio
    async def test_log_successful_execution_pnl_zero(self, trading_logger):
        """成功時実行ログ - PnL=0テスト（エッジケース）"""
        execution_result = MagicMock()
        execution_result.side = "sell"
        execution_result.amount = 0.0500
        execution_result.price = 3200000
        execution_result.paper_pnl = 0  # PnL=0
        execution_result.fee = 500

        with patch.object(trading_logger, "_check_and_log_statistics"):
            await trading_logger._log_successful_execution(
                execution_result, "test-cycle-zero-pnl", "", "✅"
            )

            # PnL=0の場合、条件は False (0 > 0 は False) なので💸が使われる
            expected_message = (
                "✅ 📉 注文実行成功 - サイクル: test-cycle-zero-pnl, "
                "サイド: SELL, 数量: 0.0500 BTC, 価格: ¥3,200,000, "
                "PnL: 💸¥0, 手数料: ¥500.00"
            )
            trading_logger.logger.info.assert_called_once_with(
                expected_message, discord_notify=True
            )

    @pytest.mark.asyncio
    async def test_log_successful_execution_pnl_none(self, trading_logger):
        """成功時実行ログ - PnL=Noneテスト"""
        execution_result = MagicMock()
        execution_result.side = "buy"
        execution_result.amount = 0.0300
        execution_result.price = 3100000
        execution_result.paper_pnl = None  # 明示的にNone
        execution_result.fee = None  # 手数料もNone

        with patch.object(trading_logger, "_check_and_log_statistics"):
            await trading_logger._log_successful_execution(
                execution_result, "test-cycle-none-pnl", "", "✅"
            )

            # PnLがNoneの場合は出力されない
            expected_message = (
                "✅ 📈 注文実行成功 - サイクル: test-cycle-none-pnl, "
                "サイド: BUY, 数量: 0.0300 BTC, 価格: ¥3,100,000"
            )
            trading_logger.logger.info.assert_called_once_with(
                expected_message, discord_notify=True
            )

    def test_format_performance_summary_with_initial_balance(self, trading_logger):
        """パフォーマンスサマリーフォーマット - initial_balance指定ありテスト"""
        stats = {
            "statistics": {"total_trades": 100, "winning_trades": 65, "win_rate": 0.65},
            "current_balance": 550000,
            "initial_balance": 500000,
            "return_rate": 0.10,
        }

        result = trading_logger.format_performance_summary(stats)

        expected = {
            "total_trades": 100,
            "winning_trades": 65,
            "win_rate_percent": 65.0,
            "current_balance": 550000,
            "return_rate_percent": 10.0,
            "profit_loss": 50000,
        }

        assert result == expected
