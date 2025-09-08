"""
バックテストエンジン - Phase 12・CI/CD統合・手動実行監視・段階的デプロイ対応

レガシーバックテストの良い部分を継承し、Phase 1-11システムと統合・GitHub Actions対応。
シンプルで高性能なバックテスト実行を実現。

レガシー継承機能:
- TradeRecord dataclass（取引記録管理）
- ポジション管理ロジック
- スリッページ・手数料計算

Phase 12新システム統合:
- Phase 1-11戦略システム統合・CI/CD統合
- Phase 5 MLアンサンブル統合・手動実行監視対応
- Phase 6リスク管理統合・GitHub Actions対応
- Phase 7-11実行システム共通化・段階的デプロイ対応.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..core.exceptions import CryptoBotError
from ..core.logger import get_logger
from ..data.data_pipeline import DataPipeline
from ..features.feature_generator import FeatureGenerator

# Phase 19: 循環インポート修正 - 遅延インポート
# from ..ml.model_manager import ModelManager
# from ..strategies.base.strategy_manager import StrategyManager  # 遅延インポートで解決
from ..trading.executor import OrderSide, VirtualPosition
from ..trading.risk_manager import IntegratedRiskManager, RiskDecision, TradeEvaluation


@dataclass
class TradeRecord:
    """
    取引記録（レガシーから継承・改良）

    バックテストとペーパートレードで共通利用する
    取引記録のデータクラス。統計分析・レポート生成に使用。.
    """

    # 基本情報
    entry_time: datetime
    exit_time: Optional[datetime]
    side: str  # "buy" or "sell"

    # 価格・数量
    entry_price: float
    exit_price: Optional[float]
    amount: float  # BTC数量

    # 損益情報
    profit_jpy: float = 0.0
    profit_rate: float = 0.0

    # 実行情報
    slippage: float = 0.0
    commission: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # メタ情報
    strategy_signal: str = ""
    ml_confidence: float = 0.0
    risk_score: float = 0.0
    market_conditions: Dict[str, Any] = field(default_factory=dict)

    def calculate_metrics(self) -> Dict[str, float]:
        """取引メトリクス計算."""
        duration_hours = 0.0
        if self.exit_time and self.entry_time:
            duration_hours = (self.exit_time - self.entry_time).total_seconds() / 3600

        return {
            "profit_jpy": self.profit_jpy,
            "profit_rate": self.profit_rate,
            "duration_hours": duration_hours,
            "slippage": self.slippage,
            "commission": self.commission,
            "net_profit": self.profit_jpy - self.commission,
        }


class BacktestEngine:
    """
    バックテストエンジン

    過去データを使用して戦略・ML・リスク管理の統合テストを実行。
    レガシーの良い部分を継承しつつ、新システムと完全統合。.
    """

    def __init__(
        self,
        initial_balance: float = 500000.0,  # 50万円（本番想定）
        slippage_rate: float = 0.0005,  # 0.05%
        commission_rate: float = 0.0012,  # 0.12%（Bitbank手数料）
        max_position_ratio: float = 0.05,  # 最大5%（Kelly基準と統一）
        risk_profile: str = "balanced",
    ):
        self.logger = get_logger(__name__)

        # 基本設定
        self.initial_balance = initial_balance
        self.slippage_rate = slippage_rate
        self.commission_rate = commission_rate
        self.max_position_ratio = max_position_ratio

        # システム統合
        self.data_pipeline = DataPipeline()
        self.feature_generator = FeatureGenerator()
        # 循環インポート回避のため遅延インポート
        from ..strategies.base.strategy_manager import StrategyManager

        self.strategy_manager = StrategyManager()

        # 戦略登録（本番と同じ戦略を使用）
        self._register_strategies()

        self.logger.info("BacktestEngineコンポーネント初期化完了")
        # Phase 19: 循環インポート修正 - 遅延インポート（エラーハンドリング強化）
        try:
            from ..ml.model_manager import ModelManager

            self.model_manager = ModelManager()
            self.logger.info("✅ ModelManager初期化完了")
        except ImportError as e:
            self.logger.error(f"ModelManager import failed: {e}")
            raise CryptoBotError(f"MLモジュールのインポートに失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"ModelManager initialization failed: {e}")
            raise CryptoBotError(f"MLモジュールの初期化に失敗しました: {e}")
        # 最適化されたリスク管理設定（Phase 8改善）
        default_risk_config = {
            "kelly_criterion": {
                "max_position_ratio": 0.05,  # 3%→5%に引き上げ（過度な保守性解消）
                "safety_factor": 0.5,
                "min_trades_for_kelly": 20,
            },
            "drawdown_manager": {
                "max_drawdown_ratio": 0.20,
                "consecutive_loss_limit": 5,
                "cooldown_hours": 24,
            },
            "anomaly_detector": {
                "spread_warning_threshold": 0.003,
                "spread_critical_threshold": 0.005,
                "api_latency_warning_ms": 1000,
                "api_latency_critical_ms": 3000,
                "price_spike_zscore_threshold": 3.0,
                "volume_spike_zscore_threshold": 3.0,
            },
            "min_ml_confidence": 0.5,  # 0.25→0.5に引き上げ（適切な精度確保）
            "risk_threshold_deny": 0.8,
            "risk_threshold_conditional": 0.6,
        }

        self.risk_manager = IntegratedRiskManager(
            config=default_risk_config, initial_balance=initial_balance
        )

        # 実行状態
        self.reset()

        self.logger.info(
            f"BacktestEngine初期化完了 - 初期残高: ¥{initial_balance:,.0f}, "
            f"最大ポジション比率: {self.max_position_ratio:.1%}, ML信頼度闾値: {default_risk_config['min_ml_confidence']}"
        )

    def reset(self):
        """バックテスト状態リセット."""
        self.current_balance = self.initial_balance
        self.position = VirtualPosition()
        self.trade_records: List[TradeRecord] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.current_data: Optional[pd.DataFrame] = None
        self.current_timestamp: Optional[datetime] = None

    async def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        symbol: str = "BTC/JPY",
        timeframes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        バックテスト実行

        Args:
            start_date: 開始日時
            end_date: 終了日時
            symbol: 通貨ペア
            timeframes: 対象タイムフレーム

        Returns:
            バックテスト結果辞書.
        """
        if timeframes is None:
            timeframes = ["15m", "4h"]  # 15分足と4時間足（15分足は制限あり）

        self.logger.info(f"バックテスト開始: {start_date} - {end_date}")

        try:
            # 1. データ取得（マルチタイムフレーム対応）
            multi_data = await self._load_data(start_date, end_date, symbol, timeframes)
            self.logger.debug(
                f"データ取得結果: {[(k, len(v) if hasattr(v, '__len__') and not v.empty else 'empty') for k, v in multi_data.items()]}"
            )

            # データ検証（空かどうかの適切なチェック）
            if not multi_data or "4h" not in multi_data or multi_data["4h"].empty:
                raise CryptoBotError(
                    f"バックテスト用データが不足しています: {symbol} {start_date}-{end_date}"
                )

            main_data_count = len(multi_data["4h"])
            if main_data_count < 50:
                self.logger.warning(f"データが不足しています: {main_data_count}件（最小50件必要）")
            elif main_data_count < 200:
                self.logger.info(f"データ量は十分です: {main_data_count}件（推奨200件以上）")

            self.logger.info(
                f"バックテスト開始: メイン({main_data_count:,}件)、マルチタイムフレーム({len(multi_data)}軸)で実行"
            )

            # 2. バックテスト実行（マルチタイムフレーム対応）
            await self._execute_backtest(multi_data)

            # 3. 結果生成
            results = self._generate_results()

            # 4. 結果検証
            if results["total_trades"] == 0:
                self.logger.warning("取引が1回も実行されませんでした")

            self.logger.info(
                f"バックテスト完了: {results['total_trades']}回取引, "
                f"最終残高: ¥{results['final_balance']:,.0f}"
            )
            return results

        except CryptoBotError:
            raise  # カスタム例外はそのまま再送出
        except Exception as e:
            self.logger.error(f"バックテスト予期せぬエラー: {type(e).__name__}: {e}")
            raise CryptoBotError(f"バックテスト実行中にエラーが発生しました: {e}")

    async def _load_data(
        self,
        start_date: datetime,
        end_date: datetime,
        symbol: str,
        timeframes: List[str],
    ) -> Dict[str, pd.DataFrame]:
        """データ取得・前処理."""
        # マルチタイムフレームデータ取得（エラーハンドリング強化）
        data_dict = {}
        failed_timeframes = []

        for timeframe in timeframes:
            try:
                tf_data = await self.data_pipeline.fetch_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=start_date,
                    limit=10000,
                )
                if not tf_data.empty:
                    data_dict[timeframe] = tf_data
                    self.logger.debug(f"タイムフレーム {timeframe}: {len(tf_data)}件取得")
                else:
                    failed_timeframes.append(timeframe)
                    self.logger.warning(f"タイムフレーム {timeframe}: データが空")
            except Exception as e:
                failed_timeframes.append(timeframe)
                self.logger.error(f"タイムフレーム {timeframe} データ取得エラー: {e}")

        # データ検証（最低限4時間足は必要）
        if "4h" not in data_dict or data_dict["4h"].empty:
            raise CryptoBotError(
                f"4時間足データが取得できません（必須）. " f"失敗: {failed_timeframes}"
            )

        # 15分足が利用できない場合の警告
        if "15m" not in data_dict or data_dict["15m"].empty:
            self.logger.warning("15分足データが利用できません - 4時間足のみでバックテスト実行")
            # 15分足が無い場合は空のDataFrameをセット（戦略が期待する構造を維持）
            data_dict["15m"] = pd.DataFrame()

        # 各タイムフレームの期間フィルタリング
        filtered_data_dict = {}
        for timeframe, data in data_dict.items():
            if not data.empty:
                filtered_data = data[(data.index >= start_date) & (data.index <= end_date)].copy()
                if not filtered_data.empty:
                    filtered_data_dict[timeframe] = filtered_data
                    self.logger.info(f"{timeframe}: {len(filtered_data)}件（期間フィルタ後）")
                else:
                    self.logger.warning(f"{timeframe}: 指定期間内にデータなし")
            else:
                filtered_data_dict[timeframe] = data  # 空のDataFrame

        # 最低限4時間足のフィルタ後データが必要
        if "4h" not in filtered_data_dict or filtered_data_dict["4h"].empty:
            raise CryptoBotError(f"指定期間の4時間足データがありません: {start_date} - {end_date}")

        return filtered_data_dict

    async def _execute_backtest(self, multi_data: Dict[str, pd.DataFrame]):
        """バックテスト実行ループ（マルチタイムフレーム対応版）."""
        self.logger.info("_execute_backtest開始")
        self.logger.debug(
            f"受信データ: {[(k, len(v) if not v.empty else 0) for k, v in multi_data.items()]}"
        )

        lookback_window = 200  # ウィンドウサイズ（固定）

        # メインタイムフレーム（4時間足）でループ実行
        main_data = multi_data["4h"]
        self.logger.info(f"メインデータ (4h): {len(main_data)}件でバックテスト実行開始")

        for i, (timestamp, row) in enumerate(main_data.iterrows()):
            self.current_timestamp = timestamp

            # 十分なデータが蓄積されるまで待機（50件から開始）
            if i < 50:
                continue

            # マルチタイムフレームウィンドウデータ作成
            start_idx = max(0, i - lookback_window)

            # 各タイムフレームのウィンドウデータを作成
            current_multi_data = {}
            for timeframe, tf_data in multi_data.items():
                if not tf_data.empty:
                    # 現在時刻以前のデータのみ取得（未来情報を避ける）
                    available_data = tf_data[tf_data.index <= timestamp]
                    if len(available_data) > 0:
                        # 適切なウィンドウサイズで切り取り
                        window_data = available_data.iloc[
                            max(0, len(available_data) - lookback_window) :
                        ].copy()
                        current_multi_data[timeframe] = window_data
                    else:
                        current_multi_data[timeframe] = pd.DataFrame()
                else:
                    current_multi_data[timeframe] = pd.DataFrame()

            # 特徴量生成（本番と同様のマルチタイムフレーム処理）
            try:
                # マルチタイムフレームデータが有効かチェック
                has_valid_data = any(
                    not df.empty if hasattr(df, "empty") else len(df) > 0
                    for df in current_multi_data.values()
                )

                self.logger.debug(
                    f"Step {i}: has_valid_data={has_valid_data}, multi_data_keys={list(current_multi_data.keys())}"
                )

                if current_multi_data and has_valid_data:
                    self.logger.debug(f"Using multi-timeframe feature generation")
                    self.current_data = await self.feature_generator.generate_features(
                        current_multi_data
                    )
                else:
                    # フォールバック: 4時間足のみで特徴量生成
                    self.logger.debug(f"Using fallback single-timeframe feature generation")
                    raw_data = main_data.iloc[start_idx : i + 1].copy()
                    self.current_data = self.feature_generator.generate_features_sync(raw_data)

                self.logger.debug(
                    f"Features generated successfully, shape: {self.current_data.shape}"
                )
            except Exception as e:
                self.logger.error(f"Feature generation error at step {i}: {e}")
                raise

            # 現在価格
            current_price = float(row["close"])

            # ポジション評価・更新
            await self._update_position(current_price)

            # エクイティカーブ更新
            current_equity = self._calculate_current_equity(current_price)
            self.equity_curve.append((timestamp, current_equity))

            # 新規取引判定
            if not self.position.exist:
                await self._evaluate_entry(current_price)
            else:
                await self._evaluate_exit(current_price)

    async def _update_position(self, current_price: float):
        """ポジション状態更新."""
        if not self.position.exist:
            return

        # 含み損益更新
        self.position.unrealized_pnl = self.position.calculate_pnl(current_price)

        # ストップロス・テイクプロフィット判定
        if self.position.stop_loss and current_price <= self.position.stop_loss:
            await self._close_position(current_price, "stop_loss")
        elif self.position.take_profit and current_price >= self.position.take_profit:
            await self._close_position(current_price, "take_profit")

    async def _evaluate_entry(self, current_price: float):
        """エントリー判定."""
        try:
            self.logger.debug(
                f"エントリー判定開始 - 価格: ¥{current_price:,.0f}, データ形状: {self.current_data.shape}"
            )

            # 戦略シグナル取得（エラーハンドリング強化）
            strategy_signal = self.strategy_manager.analyze_market(self.current_data)
            self.logger.debug(
                f"戦略シグナル取得: {strategy_signal.action if strategy_signal else 'None'} "
                f"(信頼度: {strategy_signal.confidence if strategy_signal else 0:.3f})"
            )

            # ML予測取得
            ml_prediction = await self.model_manager.predict(self.current_data)
            self.logger.debug(f"ML予測取得: {ml_prediction}")

            # 統合判定
            if not strategy_signal or strategy_signal.action == "hold":
                self.logger.debug("戦略シグナルなし or hold - エントリー見送り")
                return

            if not ml_prediction:
                self.logger.debug("ML予測なし")
                return

            # シグナルの有効性チェック
            if strategy_signal.action not in ["buy", "sell"]:
                self.logger.debug("有効なシグナルなし")
                return

            best_signal = strategy_signal

            # リスク評価
            self.logger.debug(
                f"リスク評価開始 - シグナル: {best_signal.action}, ML信頼度: {ml_prediction.get('confidence', 0):.3f}"
            )
            evaluation = await self._create_trade_evaluation(
                best_signal, ml_prediction, current_price
            )

            if evaluation is None:
                self.logger.warning("リスク評価の作成に失敗")
                return

            # IntegratedRiskManager正しい呼び出し形式に変更
            try:
                # bid/ask価格作成（スプレッド0.1%想定）
                bid_price = current_price * 0.999
                ask_price = current_price * 1.001

                # 戦略シグナルを辞書形式に変換
                strategy_signal_dict = {
                    "action": (
                        best_signal.action.value
                        if hasattr(best_signal.action, "value")
                        else str(best_signal.action)
                    ),
                    "confidence": best_signal.confidence,
                    "reasoning": getattr(best_signal, "reasoning", "バックテスト戦略シグナル"),
                }

                # 正しい引数でリスク管理評価実行
                risk_result = self.risk_manager.evaluate_trade_opportunity(
                    ml_prediction=ml_prediction,
                    strategy_signal=strategy_signal_dict,
                    market_data=self.current_data,
                    current_balance=self.current_balance,
                    bid=bid_price,
                    ask=ask_price,
                )
            except Exception as risk_error:
                self.logger.error(f"リスク管理評価エラー: {risk_error}")
                self.logger.warning("リスク管理評価失敗 - エントリー見送り")
                return
            self.logger.debug(
                f"リスク管理判定: {risk_result.decision} (理由: {getattr(risk_result, 'reason', 'N/A')})"
            )

            if risk_result.decision == RiskDecision.APPROVED:
                self.logger.info(
                    f"🎯 取引実行: {best_signal.action.upper()} @ ¥{current_price:,.0f}"
                )
                await self._open_position(
                    side=best_signal.action,
                    price=current_price,
                    evaluation=evaluation,
                    signal_info=best_signal,
                )
            else:
                self.logger.debug(f"リスク管理により取引拒否: {risk_result.decision}")

        except Exception as e:
            self.logger.error(f"エントリー判定中のエラー: {type(e).__name__}: {e}")

    async def _evaluate_exit(self, current_price: float):
        """エグジット判定（Phase 8改善実装）."""
        if not self.position.exist:
            return

        try:
            # 持続時間チェック（24時間超過で強制手仕舞い）
            holding_hours = (
                self.current_timestamp - self.position.entry_time
            ).total_seconds() / 3600
            if holding_hours > 24:
                await self._close_position(current_price, "time_limit")
                return

            # 戦略シグナルベースの手仕舞い判定
            strategy_signal = self.strategy_manager.analyze_market(self.current_data)

            if strategy_signal:
                # 現在のポジションと逆のシグナルが発生した場合
                if (
                    self.position.side == "buy"
                    and strategy_signal.action == "sell"
                    and strategy_signal.confidence > 0.6
                ) or (
                    self.position.side == "sell"
                    and strategy_signal.action == "buy"
                    and strategy_signal.confidence > 0.6
                ):
                    await self._close_position(current_price, "strategy_signal")
                    return

            # 损益ベースの手仕舞い判定（利食5%で強制手仕舞い）
            unrealized_pnl_rate = self.position.unrealized_pnl / (
                self.position.entry_price * self.position.amount
            )
            if unrealized_pnl_rate > 0.05:  # 5%利益
                await self._close_position(current_price, "profit_taking")

        except Exception as e:
            self.logger.warning(f"エグジット判定エラー: {e}")

    async def _create_trade_evaluation(
        self, signal, ml_prediction, current_price: float
    ) -> Optional[TradeEvaluation]:
        """取引評価オブジェクト作成（エラーハンドリング強化）."""
        try:
            # 入力検証
            if current_price <= 0:
                self.logger.error(f"無効な価格: {current_price}")
                return None

            if self.current_balance <= 0:
                self.logger.warning("残高不足で取引不可")
                return None

            # ポジションサイズ計算（一元化・二重制限解消）
            max_btc_amount = self.current_balance * self.max_position_ratio / current_price

            # 最小取引単位を考慮（通常 0.0001 BTC）
            min_trade_amount = 0.0001
            if max_btc_amount < min_trade_amount:
                self.logger.warning(
                    f"計算されたポジションサイズが小さすぎます: {max_btc_amount:.6f} BTC"
                )
                return None

            position_size = max_btc_amount

            # ストップロス・テイクプロフィット計算
            stop_loss_rate = 0.02  # 2%
            take_profit_rate = 0.04  # 4%

            if signal.action == "buy":
                stop_loss = current_price * (1 - stop_loss_rate)
                take_profit = current_price * (1 + take_profit_rate)
            else:  # sell
                stop_loss = current_price * (1 + stop_loss_rate)
                take_profit = current_price * (1 - take_profit_rate)

            return TradeEvaluation(
                decision=RiskDecision.APPROVED,  # 仮設定
                side=signal.action,  # 必須パラメータ追加
                risk_score=0.3,  # 中程度リスク
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence_level=signal.confidence,
                warnings=[],
                denial_reasons=[],
                evaluation_timestamp=self.current_timestamp,
                kelly_recommendation=position_size,
                drawdown_status="normal",
                anomaly_alerts=[],
                market_conditions={
                    "price": current_price,
                    "position_ratio": self.max_position_ratio,
                    "balance": self.current_balance,
                },
            )

        except Exception as e:
            self.logger.error(f"取引評価作成エラー: {e}")
            return None

    async def _open_position(
        self, side: str, price: float, evaluation: TradeEvaluation, signal_info
    ):
        """ポジションオープン."""
        amount = evaluation.position_size

        # スリッページ・手数料計算
        slippage = price * self.slippage_rate
        execution_price = price + slippage if side == "buy" else price - slippage
        commission = execution_price * amount * self.commission_rate

        # ポジション設定
        self.position.exist = True
        self.position.side = side
        self.position.entry_price = execution_price
        self.position.amount = amount
        self.position.stop_loss = evaluation.stop_loss
        self.position.take_profit = evaluation.take_profit
        self.position.entry_time = self.current_timestamp

        # 残高更新
        cost = execution_price * amount + commission
        self.current_balance -= cost

        self.logger.info(f"ポジションオープン: {side} {amount:.6f}BTC @ ¥{execution_price:,.0f}")

    async def _close_position(self, price: float, reason: str = "manual"):
        """ポジションクローズ."""
        if not self.position.exist:
            return

        # スリッページ・手数料計算
        slippage = price * self.slippage_rate
        execution_price = price - slippage if self.position.side == "buy" else price + slippage
        commission = execution_price * self.position.amount * self.commission_rate

        # 損益計算
        if self.position.side == "buy":
            profit_jpy = (execution_price - self.position.entry_price) * self.position.amount
        else:
            profit_jpy = (self.position.entry_price - execution_price) * self.position.amount

        profit_jpy -= commission
        profit_rate = profit_jpy / (self.position.entry_price * self.position.amount)

        # 取引記録作成
        trade_record = TradeRecord(
            entry_time=self.position.entry_time,
            exit_time=self.current_timestamp,
            side=self.position.side,
            entry_price=self.position.entry_price,
            exit_price=execution_price,
            amount=self.position.amount,
            profit_jpy=profit_jpy,
            profit_rate=profit_rate,
            slippage=slippage,
            commission=commission,
            stop_loss=self.position.stop_loss,
            take_profit=self.position.take_profit,
        )

        self.trade_records.append(trade_record)

        # 残高更新
        proceeds = execution_price * self.position.amount - commission
        self.current_balance += proceeds

        # ポジションリセット
        self.position = VirtualPosition()

        self.logger.info(
            f"ポジションクローズ({reason}): 損益 ¥{profit_jpy:,.0f} ({profit_rate:.2%})"
        )

    def _calculate_current_equity(self, current_price: float) -> float:
        """現在エクイティ計算."""
        equity = self.current_balance

        if self.position.exist:
            position_value = current_price * self.position.amount
            if self.position.side == "buy":
                equity += position_value
            else:
                # ショートポジションの場合の計算
                equity += (self.position.entry_price - current_price) * self.position.amount

        return equity

    def _generate_results(self) -> Dict[str, Any]:
        """バックテスト結果生成."""
        if not self.trade_records:
            return {
                "total_trades": 0,
                "total_profit": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "final_balance": self.current_balance,
            }

        # 基本統計
        profits = [trade.profit_jpy for trade in self.trade_records]
        win_trades = [p for p in profits if p > 0]

        total_profit = sum(profits)
        win_rate = len(win_trades) / len(profits) if profits else 0.0

        # エクイティカーブからドローダウン計算
        equity_values = [eq for _, eq in self.equity_curve]
        max_drawdown = self._calculate_max_drawdown(equity_values)

        return {
            "total_trades": len(self.trade_records),
            "total_profit": total_profit,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "final_balance": self.current_balance,
            "return_rate": (self.current_balance - self.initial_balance) / self.initial_balance,
            "trade_records": self.trade_records,
            "equity_curve": self.equity_curve,
        }

    def _calculate_max_drawdown(self, equity_values: List[float]) -> float:
        """最大ドローダウン計算（レガシーから継承）."""
        if not equity_values:
            return 0.0

        peak = equity_values[0]
        max_dd = 0.0

        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _register_strategies(self):
        """戦略登録（本番システムと同じ戦略を使用）"""
        try:
            self.logger.debug("🔧 戦略登録開始")
            from ..strategies.implementations.atr_based import ATRBasedStrategy
            from ..strategies.implementations.fibonacci_retracement import (
                FibonacciRetracementStrategy,
            )
            from ..strategies.implementations.mochipoy_alert import MochipoyAlertStrategy
            from ..strategies.implementations.multi_timeframe import MultiTimeframeStrategy

            # 戦略重み（config/backtest/base.yamlの設定に合わせる）
            strategy_weights = {
                "atr_based": 0.3,
                "mochipoy_alert": 0.3,
                "multi_timeframe": 0.25,
                "fibonacci_retracement": 0.15,
            }

            strategies = [
                (ATRBasedStrategy(), strategy_weights["atr_based"]),
                (MochipoyAlertStrategy(), strategy_weights["mochipoy_alert"]),
                (MultiTimeframeStrategy(), strategy_weights["multi_timeframe"]),
                (
                    FibonacciRetracementStrategy(),
                    strategy_weights["fibonacci_retracement"],
                ),
            ]

            registered_count = 0
            for strategy, weight in strategies:
                try:
                    self.strategy_manager.register_strategy(strategy, weight)
                    self.logger.info(
                        f"✅ 戦略登録: {strategy.name} (重み: {weight}, 有効: {strategy.is_enabled})"
                    )

                    # 必要特徴量の確認
                    required_features = strategy.get_required_features()
                    self.logger.debug(f"   必要特徴量: {required_features}")
                    registered_count += 1

                except Exception as strategy_error:
                    self.logger.error(f"❌ 戦略登録失敗 {strategy.name}: {strategy_error}")
                    continue

            self.logger.info(f"🎯 戦略登録完了: {registered_count}/{len(strategies)}戦略")

            # 戦略マネージャーの状態確認
            manager_stats = self.strategy_manager.get_manager_stats()
            self.logger.info(f"📊 戦略マネージャー状態: {manager_stats}")

        except ImportError as e:
            self.logger.error(f"戦略インポートエラー: {e}")
            raise CryptoBotError(f"戦略インポートに失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"戦略登録エラー: {e}")
            raise CryptoBotError(f"戦略登録に失敗しました: {e}")
