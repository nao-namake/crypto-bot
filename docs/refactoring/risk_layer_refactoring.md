# trading/risk層リファクタリング完全ガイド

**Phase 38: risk_manager.py分割 - 企業級コード品質実現**

## 概要

大きな`risk_manager.py`（1815行）を5つの専門ファイルに分割し、保守性・テスタビリティ・可読性を向上させます。

## ファイル構成

```
src/trading/risk/
├── __init__.py           # 公開API・エクスポート
├── manager.py            # メインリスク管理ロジック（IntegratedRiskManager）
├── kelly.py              # Kelly基準計算（完成）
├── sizer.py              # ポジションサイジング統合（完成）
├── anomaly.py            # 異常検出（risk_monitor.pyから移動）
└── drawdown.py           # ドローダウン管理（risk_monitor.pyから移動）
```

## 完了済みファイル

### 1. risk/kelly.py ✅
- **責務**: Kelly基準によるポジションサイジング計算
- **クラス**: `KellyCriterion`, `TradeResult`, `KellyCalculationResult`
- **主要機能**:
  - Kelly公式による最適ポジション比率計算
  - 取引履歴からの動的Kelly値計算
  - ML予測信頼度を考慮した最適サイズ計算
  - ボラティリティ連動ダイナミックポジションサイジング
  - 複数レベルフォールバック機能
- **設定ファイル化**: 完全対応（ハードコード値0）

### 2. risk/sizer.py ✅
- **責務**: Kelly基準と既存RiskManagerの統合
- **クラス**: `PositionSizeIntegrator`
- **主要機能**:
  - 統合ポジションサイズ計算（Dynamic, Kelly, RiskManagerの最小値採用）
  - ML信頼度に基づく動的ポジションサイジング
  - 信頼度カテゴリー別比率調整（低/中/高）
  - 資金規模別調整
- **設定ファイル化**: 完全対応（thresholds.yamlから動的取得）

## 作成が必要なファイル

### 3. risk/anomaly.py（TODO）
**現在の場所**: `src/trading/risk_monitor.py`
**移動対象クラス**:
- `TradingAnomalyDetector`
- `AnomalyAlert`
- `AnomalyLevel`

**実装手順**:
```python
# src/trading/risk/anomaly.py
"""
異常検出システム

Phase 28完了・市場異常検知機能：
- スプレッド異常検知（Warning/Critical閾値）
- API遅延監視
- 価格スパイク検出
- ボリューム異常検出
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

import pandas as pd

from ...core.config import get_threshold
from ...core.logger import get_logger


class AnomalyLevel(Enum):
    """異常レベル."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AnomalyAlert:
    """異常アラート."""
    timestamp: datetime
    level: AnomalyLevel
    message: str
    details: dict


class TradingAnomalyDetector:
    """市場異常検知システム"""

    def __init__(
        self,
        spread_warning_threshold: float = None,
        spread_critical_threshold: float = None,
        api_latency_warning_ms: float = None,
        api_latency_critical_ms: float = None,
        price_spike_zscore_threshold: float = None,
        volume_spike_zscore_threshold: float = None,
    ):
        """
        異常検知器初期化

        Args:
            spread_warning_threshold: スプレッド警告閾値
            spread_critical_threshold: スプレッド危険閾値
            api_latency_warning_ms: API遅延警告閾値
            api_latency_critical_ms: API遅延危険閾値
            price_spike_zscore_threshold: 価格スパイクZスコア閾値
            volume_spike_zscore_threshold: ボリュームスパイクZスコア閾値
        """
        self.spread_warning_threshold = spread_warning_threshold or get_threshold(
            "risk.anomaly_detector.spread_warning_threshold", 0.003
        )
        self.spread_critical_threshold = spread_critical_threshold or get_threshold(
            "risk.anomaly_detector.spread_critical_threshold", 0.005
        )
        self.api_latency_warning_ms = api_latency_warning_ms or get_threshold(
            "risk.anomaly_detector.api_latency_warning", 1.0
        ) * 1000
        self.api_latency_critical_ms = api_latency_critical_ms or get_threshold(
            "risk.anomaly_detector.api_latency_critical", 3.0
        ) * 1000
        self.price_spike_zscore_threshold = price_spike_zscore_threshold or get_threshold(
            "risk.anomaly_detector.price_spike_zscore_threshold", 3.0
        )
        self.volume_spike_zscore_threshold = volume_spike_zscore_threshold or get_threshold(
            "risk.anomaly_detector.volume_spike_zscore_threshold", 3.0
        )

        self.anomaly_history: List[AnomalyAlert] = []
        self.logger = get_logger()

    def comprehensive_anomaly_check(
        self,
        bid: float,
        ask: float,
        last_price: float,
        volume: float,
        api_latency_ms: float,
        market_data: pd.DataFrame,
    ) -> List[AnomalyAlert]:
        """
        包括的異常チェック

        Args:
            bid: 買い価格
            ask: 売り価格
            last_price: 最終取引価格
            volume: 出来高
            api_latency_ms: API応答時間（ミリ秒）
            market_data: 市場データ履歴

        Returns:
            検出された異常アラートリスト
        """
        alerts = []

        # 1. スプレッド異常チェック
        spread_alert = self._check_spread_anomaly(bid, ask, last_price)
        if spread_alert:
            alerts.append(spread_alert)

        # 2. API遅延チェック
        latency_alert = self._check_api_latency(api_latency_ms)
        if latency_alert:
            alerts.append(latency_alert)

        # 3. 価格スパイクチェック
        price_alert = self._check_price_spike(last_price, market_data)
        if price_alert:
            alerts.append(price_alert)

        # 4. ボリューム異常チェック
        volume_alert = self._check_volume_anomaly(volume, market_data)
        if volume_alert:
            alerts.append(volume_alert)

        # 履歴に追加
        for alert in alerts:
            self.anomaly_history.append(alert)

        # 古い履歴削除（24時間以上前）
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.anomaly_history = [
            a for a in self.anomaly_history if a.timestamp >= cutoff_time
        ]

        return alerts

    def _check_spread_anomaly(
        self, bid: float, ask: float, last_price: float
    ) -> Optional[AnomalyAlert]:
        """スプレッド異常チェック"""
        if last_price <= 0:
            return None

        spread_pct = (ask - bid) / last_price

        if spread_pct >= self.spread_critical_threshold:
            return AnomalyAlert(
                timestamp=datetime.now(),
                level=AnomalyLevel.CRITICAL,
                message=f"危険なスプレッド: {spread_pct:.2%}",
                details={"bid": bid, "ask": ask, "spread_pct": spread_pct}
            )
        elif spread_pct >= self.spread_warning_threshold:
            return AnomalyAlert(
                timestamp=datetime.now(),
                level=AnomalyLevel.WARNING,
                message=f"広いスプレッド: {spread_pct:.2%}",
                details={"bid": bid, "ask": ask, "spread_pct": spread_pct}
            )

        return None

    def _check_api_latency(self, api_latency_ms: float) -> Optional[AnomalyAlert]:
        """API遅延チェック"""
        if api_latency_ms >= self.api_latency_critical_ms:
            return AnomalyAlert(
                timestamp=datetime.now(),
                level=AnomalyLevel.CRITICAL,
                message=f"重大なAPI遅延: {api_latency_ms:.0f}ms",
                details={"latency_ms": api_latency_ms}
            )
        elif api_latency_ms >= self.api_latency_warning_ms:
            return AnomalyAlert(
                timestamp=datetime.now(),
                level=AnomalyLevel.WARNING,
                message=f"API遅延: {api_latency_ms:.0f}ms",
                details={"latency_ms": api_latency_ms}
            )

        return None

    def _check_price_spike(
        self, last_price: float, market_data: pd.DataFrame
    ) -> Optional[AnomalyAlert]:
        """価格スパイクチェック"""
        try:
            if len(market_data) < 20:
                return None

            recent_prices = market_data["close"].tail(20)
            price_mean = recent_prices.mean()
            price_std = recent_prices.std()

            if price_std > 0:
                z_score = abs((last_price - price_mean) / price_std)

                if z_score >= self.price_spike_zscore_threshold:
                    return AnomalyAlert(
                        timestamp=datetime.now(),
                        level=AnomalyLevel.CRITICAL,
                        message=f"価格急変検出: Zスコア={z_score:.2f}",
                        details={
                            "last_price": last_price,
                            "mean_price": price_mean,
                            "z_score": z_score
                        }
                    )
        except Exception as e:
            self.logger.error(f"価格スパイクチェックエラー: {e}")

        return None

    def _check_volume_anomaly(
        self, volume: float, market_data: pd.DataFrame
    ) -> Optional[AnomalyAlert]:
        """ボリューム異常チェック"""
        try:
            if len(market_data) < 20 or "volume" not in market_data.columns:
                return None

            recent_volumes = market_data["volume"].tail(20)
            volume_mean = recent_volumes.mean()
            volume_std = recent_volumes.std()

            if volume_std > 0:
                z_score = abs((volume - volume_mean) / volume_std)

                if z_score >= self.volume_spike_zscore_threshold:
                    return AnomalyAlert(
                        timestamp=datetime.now(),
                        level=AnomalyLevel.WARNING,
                        message=f"ボリューム異常: Zスコア={z_score:.2f}",
                        details={
                            "current_volume": volume,
                            "mean_volume": volume_mean,
                            "z_score": z_score
                        }
                    )
        except Exception as e:
            self.logger.error(f"ボリューム異常チェックエラー: {e}")

        return None

    def get_anomaly_statistics(self) -> dict:
        """異常検出統計取得"""
        try:
            recent_time = datetime.now() - timedelta(hours=24)
            recent_alerts = [a for a in self.anomaly_history if a.timestamp >= recent_time]

            return {
                "total_alerts_24h": len(recent_alerts),
                "critical_alerts": len([a for a in recent_alerts if a.level == AnomalyLevel.CRITICAL]),
                "warning_alerts": len([a for a in recent_alerts if a.level == AnomalyLevel.WARNING]),
                "info_alerts": len([a for a in recent_alerts if a.level == AnomalyLevel.INFO]),
            }
        except Exception as e:
            self.logger.error(f"異常統計取得エラー: {e}")
            return {}
```

### 4. risk/drawdown.py（TODO）
**現在の場所**: `src/trading/risk_monitor.py`
**移動対象クラス**:
- `DrawdownManager`
- `TradingStatus`

**実装手順**:
```python
# src/trading/risk/drawdown.py
"""
ドローダウン管理システム

Phase 26完了・Phase 36 Graceful Degradation統合：
- 最大ドローダウン監視（20%制限）
- 連続損失管理（8回制限・Phase 26最適化）
- クールダウン機能（6時間・Phase 26短縮）
- 状態永続化（Local + GCS）
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import os

from ...core.config import get_threshold, load_config
from ...core.logger import get_logger


class TradingStatus(Enum):
    """取引状態."""
    ACTIVE = "active"
    PAUSED_DRAWDOWN = "paused_drawdown"
    PAUSED_CONSECUTIVE_LOSS = "paused_consecutive_loss"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class TradeRecord:
    """取引記録."""
    timestamp: datetime
    profit_loss: float
    strategy: str


class DrawdownManager:
    """
    ドローダウン管理システム

    機能:
    - 最大ドローダウン監視
    - 連続損失カウント
    - クールダウン期間管理
    - 状態永続化（ローカル + GCS）
    """

    def __init__(
        self,
        max_drawdown_ratio: float = None,
        consecutive_loss_limit: int = None,
        cooldown_hours: float = None,
        config: Dict[str, Any] = None,
        mode: str = "live",
    ):
        """
        ドローダウンマネージャー初期化

        Args:
            max_drawdown_ratio: 最大ドローダウン比率
            consecutive_loss_limit: 連続損失制限
            cooldown_hours: クールダウン時間（時間）
            config: 設定辞書
            mode: 実行モード（paper/live/backtest）
        """
        self.max_drawdown_ratio = max_drawdown_ratio or get_threshold(
            "risk.drawdown_manager.max_drawdown_ratio", 0.2
        )
        self.consecutive_loss_limit = consecutive_loss_limit or get_threshold(
            "risk.drawdown_manager.consecutive_loss_limit", 8
        )
        self.cooldown_hours = cooldown_hours or get_threshold(
            "risk.drawdown_manager.cooldown_hours", 6
        )
        self.mode = mode
        self.config = config or {}

        # 状態変数
        self.initial_balance = 10000.0
        self.peak_balance = 10000.0
        self.current_balance = 10000.0
        self.consecutive_losses = 0
        self.trading_status = TradingStatus.ACTIVE
        self.cooldown_until: Optional[datetime] = None
        self.trade_history: List[TradeRecord] = []

        self.logger = get_logger()

        # 状態永続化設定
        persistence_config = self.config.get("persistence", {})
        self.local_state_path = persistence_config.get(
            "local_path", "src/core/state/drawdown_state.json"
        )
        self.gcs_bucket = persistence_config.get("gcs_bucket")
        self.gcs_path = persistence_config.get("gcs_path")

        # 状態復元
        self._load_state()

    def initialize_balance(self, initial_balance: float) -> None:
        """初期残高設定"""
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.current_balance = initial_balance
        self.logger.info(f"初期残高設定: ¥{initial_balance:,.0f}")

    def update_balance(self, current_balance: float) -> None:
        """現在残高更新"""
        self.current_balance = current_balance

        # ピーク残高更新
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
            self.logger.debug(f"ピーク残高更新: ¥{self.peak_balance:,.0f}")

    def record_trade_result(
        self, profit_loss: float, strategy: str = "default"
    ) -> None:
        """
        取引結果記録

        Args:
            profit_loss: 損益（正値=利益、負値=損失）
            strategy: 戦略名
        """
        try:
            # 取引記録追加
            trade_record = TradeRecord(
                timestamp=datetime.now(),
                profit_loss=profit_loss,
                strategy=strategy,
            )
            self.trade_history.append(trade_record)

            # 連続損失カウント更新
            if profit_loss < 0:
                self.consecutive_losses += 1
                self.logger.warning(
                    f"連続損失更新: {self.consecutive_losses}/{self.consecutive_loss_limit}"
                )
            else:
                if self.consecutive_losses > 0:
                    self.logger.info(f"連続損失リセット（勝ち取引）")
                self.consecutive_losses = 0

            # ドローダウンチェック
            current_drawdown = self.calculate_current_drawdown()
            if current_drawdown >= self.max_drawdown_ratio:
                self._enter_cooldown(TradingStatus.PAUSED_DRAWDOWN)
            elif self.consecutive_losses >= self.consecutive_loss_limit:
                self._enter_cooldown(TradingStatus.PAUSED_CONSECUTIVE_LOSS)

            # 状態保存
            self._save_state()

        except Exception as e:
            self.logger.error(f"取引結果記録エラー: {e}")

    def calculate_current_drawdown(self) -> float:
        """現在のドローダウン比率計算"""
        if self.peak_balance <= 0:
            return 0.0

        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        return max(0.0, drawdown)

    def check_trading_allowed(self) -> bool:
        """取引許可チェック"""
        # クールダウン期間チェック
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.now()).total_seconds() / 3600
            self.logger.debug(f"クールダウン中: 残り{remaining:.1f}時間")
            return False

        # クールダウン解除
        if self.cooldown_until and datetime.now() >= self.cooldown_until:
            self._exit_cooldown()

        return self.trading_status == TradingStatus.ACTIVE

    def _enter_cooldown(self, status: TradingStatus) -> None:
        """クールダウン開始"""
        self.trading_status = status
        self.cooldown_until = datetime.now() + timedelta(hours=self.cooldown_hours)

        self.logger.warning(
            f"クールダウン開始: {status.value}, "
            f"解除予定: {self.cooldown_until.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 状態保存
        self._save_state()

    def _exit_cooldown(self) -> None:
        """クールダウン解除"""
        self.logger.info("クールダウン解除、取引再開")
        self.trading_status = TradingStatus.ACTIVE
        self.cooldown_until = None
        self.consecutive_losses = 0

        # 状態保存
        self._save_state()

    def get_drawdown_statistics(self) -> Dict[str, Any]:
        """ドローダウン統計取得"""
        return {
            "initial_balance": self.initial_balance,
            "peak_balance": self.peak_balance,
            "current_balance": self.current_balance,
            "current_drawdown": self.calculate_current_drawdown(),
            "max_drawdown_ratio": self.max_drawdown_ratio,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_loss_limit": self.consecutive_loss_limit,
            "trading_status": self.trading_status.value,
            "trading_allowed": self.check_trading_allowed(),
            "cooldown_until": (
                self.cooldown_until.isoformat() if self.cooldown_until else None
            ),
        }

    def _save_state(self) -> None:
        """状態保存（ローカル + GCS）"""
        try:
            # バックテストモードでは保存しない
            if self.mode == "backtest":
                return

            state = {
                "initial_balance": self.initial_balance,
                "peak_balance": self.peak_balance,
                "current_balance": self.current_balance,
                "consecutive_losses": self.consecutive_losses,
                "trading_status": self.trading_status.value,
                "cooldown_until": (
                    self.cooldown_until.isoformat() if self.cooldown_until else None
                ),
                "last_updated": datetime.now().isoformat(),
            }

            # ローカル保存
            os.makedirs(os.path.dirname(self.local_state_path), exist_ok=True)
            with open(self.local_state_path, "w") as f:
                json.dump(state, f, indent=2)

            self.logger.debug(f"状態保存完了: {self.local_state_path}")

        except Exception as e:
            self.logger.error(f"状態保存エラー: {e}")

    def _load_state(self) -> None:
        """状態復元（ローカル読み込み）"""
        try:
            # バックテストモードでは復元しない
            if self.mode == "backtest":
                return

            if not os.path.exists(self.local_state_path):
                self.logger.info("状態ファイル未存在、新規作成")
                return

            with open(self.local_state_path, "r") as f:
                state = json.load(f)

            self.initial_balance = state.get("initial_balance", 10000.0)
            self.peak_balance = state.get("peak_balance", 10000.0)
            self.current_balance = state.get("current_balance", 10000.0)
            self.consecutive_losses = state.get("consecutive_losses", 0)
            self.trading_status = TradingStatus(
                state.get("trading_status", TradingStatus.ACTIVE.value)
            )

            cooldown_until_str = state.get("cooldown_until")
            if cooldown_until_str:
                self.cooldown_until = datetime.fromisoformat(cooldown_until_str)

            self.logger.info(f"状態復元完了: {self.local_state_path}")

        except Exception as e:
            self.logger.error(f"状態復元エラー: {e}")
```

### 5. risk/manager.py（TODO - メインファイル）
**責務**: 統合リスク管理ロジック
**クラス**: `IntegratedRiskManager`, `TradeEvaluation`, `RiskMetrics`, `RiskDecision`

**実装手順**:
- `risk_manager.py`から`IntegratedRiskManager`クラスを抽出
- 上記で作成した`kelly.py`, `sizer.py`, `anomaly.py`, `drawdown.py`をインポート
- データクラス（`TradeEvaluation`, `RiskMetrics`, `ExecutionResult`等）を`../core/types.py`に移動

### 6. risk/__init__.py（TODO）
```python
"""
trading/risk層 - 統合リスク管理システム

Phase 38リファクタリング完了版
"""

from .anomaly import AnomalyAlert, AnomalyLevel, TradingAnomalyDetector
from .drawdown import DrawdownManager, TradingStatus
from .kelly import KellyCalculationResult, KellyCriterion, TradeResult
from .manager import IntegratedRiskManager, RiskDecision, RiskMetrics, TradeEvaluation
from .sizer import PositionSizeIntegrator

__all__ = [
    # Kelly基準
    "KellyCriterion",
    "TradeResult",
    "KellyCalculationResult",
    # ポジションサイジング
    "PositionSizeIntegrator",
    # 異常検出
    "TradingAnomalyDetector",
    "AnomalyAlert",
    "AnomalyLevel",
    # ドローダウン管理
    "DrawdownManager",
    "TradingStatus",
    # 統合リスク管理
    "IntegratedRiskManager",
    "TradeEvaluation",
    "RiskMetrics",
    "RiskDecision",
]
```

## インポート更新が必要なファイル

1. **src/core/orchestration/trading_orchestrator.py**
   ```python
   # 変更前
   from ..trading.risk_manager import IntegratedRiskManager

   # 変更後
   from ..trading.risk import IntegratedRiskManager
   ```

2. **src/trading/execution_service.py**
   ```python
   # 変更前
   from .risk_manager import IntegratedRiskManager, TradeEvaluation

   # 変更後
   from .risk import IntegratedRiskManager, TradeEvaluation
   ```

3. **tests/**内の全テストファイル**
   - `tests/trading/test_risk_manager.py`
   - その他risk_managerを参照するテスト

## 実装チェックリスト

- [x] risk/kelly.py作成
- [x] risk/sizer.py作成
- [ ] risk/anomaly.py作成（risk_monitor.pyから移動）
- [ ] risk/drawdown.py作成（risk_monitor.pyから移動）
- [ ] risk/manager.py作成（IntegratedRiskManager抽出）
- [ ] risk/__init__.py作成
- [ ] データクラスをcore/types.pyに移動
- [ ] 依存ファイルのインポート更新
- [ ] テストファイル更新
- [ ] `bash scripts/testing/checks.sh`実行・全テスト通過確認

## 設定ファイル対応状況

### ✅ 完全対応
- `kelly.py`: すべての設定値を`thresholds.yaml`から動的取得
- `sizer.py`: すべての設定値を`thresholds.yaml`から動的取得

### ⚠️ 要対応
- `anomaly.py`: 設定ファイル対応実装済み（上記サンプル）
- `drawdown.py`: 設定ファイル対応実装済み（上記サンプル）
- `manager.py`: 既存コードを確認して設定ファイル化

## 品質基準

1. **コード品質**
   - flake8チェック通過
   - black・isortフォーマット適用
   - ハードコード値0（すべて設定ファイルから取得）

2. **テストカバレッジ**
   - 既存テストの動作維持
   - 新規テストは必要に応じて追加

3. **ドキュメント**
   - Docstring完備
   - 型ヒント完全対応

## 期待効果

1. **保守性向上**: 1ファイル1815行 → 5ファイル平均350行
2. **テスタビリティ向上**: 各モジュール独立テスト可能
3. **可読性向上**: 責務明確化・ナビゲーション容易
4. **拡張性向上**: 新機能追加時の影響範囲明確化

---

**Phase 37.4完了時点のシステム品質**: 653テスト100%成功・58.62%カバレッジ・CI/CD統合完了
