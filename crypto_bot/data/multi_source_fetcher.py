"""
MultiSourceDataFetcher - 複数データソース統合管理システム
ChatGPTアドバイス反映版：段階的・品質重視アプローチ

複数データソースの統合管理・自動フォールバック・データ品質検証
Phase A3: 外部データキャッシュ最適化・グローバルキャッシュ統合
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .global_cache_manager import get_global_cache

logger = logging.getLogger(__name__)


class DataSourceStatus(Enum):
    """データソース状態管理"""

    ACTIVE = "active"
    FAILING = "failing"
    DISABLED = "disabled"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class DataSourceConfig:
    """データソース設定"""

    name: str
    enabled: bool = True
    priority: int = 1  # 1が最高優先度
    timeout: int = 10
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300  # 5分
    quality_threshold: float = 0.7


@dataclass
class DataSourceResult:
    """データソース取得結果"""

    source_name: str
    data: Optional[pd.DataFrame]
    quality_score: float
    error: Optional[str] = None
    fetch_time: float = 0.0
    success: bool = False


class MultiSourceDataFetcher(ABC):
    """
    複数データソース統合管理ベースクラス

    機能：
    - 複数データソースの順次試行
    - 自動フォールバック機能
    - データ品質検証・閾値管理
    - 24時間キャッシュシステム
    - サーキットブレーカー機能
    - 設定ベース初期化
    """

    def __init__(
        self, config: Optional[Dict[str, Any]] = None, data_type: str = "unknown"
    ):
        self.config = config or {}
        self.data_type = data_type
        self.data_config = self.config.get("external_data", {}).get(data_type, {})

        # 基本設定
        self.cache_hours = self.data_config.get("cache_hours", 24)
        self.quality_threshold = self.data_config.get("quality_threshold", 0.7)
        self.enabled = self.data_config.get("enabled", True)

        # グローバルキャッシュマネージャー統合（Phase A3）
        self.global_cache = get_global_cache()

        # データソース状態管理
        self.source_states: Dict[str, DataSourceStatus] = {}
        self.source_failure_counts: Dict[str, int] = {}
        self.source_circuit_breaker_times: Dict[str, datetime] = {}

        # データソース設定初期化
        self._initialize_data_sources()

        logger.info(f"🔧 MultiSourceDataFetcher initialized for {data_type}")
        logger.info(f"  - Sources: {[ds.name for ds in self.data_sources]}")
        logger.info(f"  - Cache hours: {self.cache_hours}")
        logger.info(f"  - Quality threshold: {self.quality_threshold}")
        logger.info(f"  - Global cache integrated: {self.global_cache is not None}")

    def _initialize_data_sources(self) -> None:
        """データソース設定初期化"""
        sources_config = self.data_config.get("sources", [])
        self.data_sources: List[DataSourceConfig] = []

        for i, source_name in enumerate(sources_config):
            source_config = DataSourceConfig(
                name=source_name,
                priority=i + 1,
                enabled=True,
                timeout=self.data_config.get("timeout", 10),
                max_retries=self.data_config.get("max_retries", 3),
                circuit_breaker_threshold=self.data_config.get(
                    "circuit_breaker_threshold", 5
                ),
                circuit_breaker_timeout=self.data_config.get(
                    "circuit_breaker_timeout", 300
                ),
                quality_threshold=self.quality_threshold,
            )

            self.data_sources.append(source_config)
            self.source_states[source_name] = DataSourceStatus.ACTIVE
            self.source_failure_counts[source_name] = 0

        # 優先度でソート
        self.data_sources.sort(key=lambda x: x.priority)

    def _get_cache_key(self, **kwargs) -> str:
        """キャッシュキー生成"""
        return self.global_cache.get_cache_key(self.data_type, kwargs)

    def _is_cache_valid(self, **kwargs) -> Tuple[Optional[pd.DataFrame], bool]:
        """グローバルキャッシュ有効性チェック（Phase A3対応）"""
        cache_key = self._get_cache_key(**kwargs)
        cached_data = self.global_cache.get(cache_key)
        
        if cached_data is not None:
            logger.debug(f"📋 Global cache hit for {self.data_type}: {cache_key}")
            return cached_data, True
        
        logger.debug(f"❌ Global cache miss for {self.data_type}: {cache_key}")
        return None, False

    def _update_cache(self, data: pd.DataFrame, quality_score: float, **kwargs) -> None:
        """グローバルキャッシュ更新（Phase A3対応）"""
        cache_key = self._get_cache_key(**kwargs)
        ttl = timedelta(hours=self.cache_hours)
        
        success = self.global_cache.put(
            cache_key,
            data,
            source=self.data_type,
            ttl=ttl,
            quality_score=quality_score
        )
        
        if success:
            logger.info(
                f"✅ {self.data_type} global cache updated: {len(data)} records, "
                f"quality={quality_score:.3f}, ttl={self.cache_hours}h"
            )
        else:
            logger.warning(f"⚠️ Failed to update global cache for {self.data_type}")

    def _check_circuit_breaker(self, source_name: str) -> bool:
        """サーキットブレーカー状態チェック"""
        if source_name not in self.source_circuit_breaker_times:
            return False

        circuit_time = self.source_circuit_breaker_times[source_name]
        timeout_seconds = next(
            (
                ds.circuit_breaker_timeout
                for ds in self.data_sources
                if ds.name == source_name
            ),
            300,
        )

        if datetime.now() - circuit_time > timedelta(seconds=timeout_seconds):
            # サーキットブレーカー解除
            self.source_states[source_name] = DataSourceStatus.ACTIVE
            self.source_failure_counts[source_name] = 0
            del self.source_circuit_breaker_times[source_name]
            logger.info(f"🔄 Circuit breaker reset for {source_name}")
            return False

        return True

    def _update_source_state(self, source_name: str, success: bool) -> None:
        """データソース状態更新"""
        if success:
            self.source_failure_counts[source_name] = 0
            self.source_states[source_name] = DataSourceStatus.ACTIVE
        else:
            self.source_failure_counts[source_name] += 1

            # サーキットブレーカー判定
            threshold = next(
                (
                    ds.circuit_breaker_threshold
                    for ds in self.data_sources
                    if ds.name == source_name
                ),
                5,
            )

            if self.source_failure_counts[source_name] >= threshold:
                self.source_states[source_name] = DataSourceStatus.CIRCUIT_BREAKER
                self.source_circuit_breaker_times[source_name] = datetime.now()
                logger.warning(f"🚨 Circuit breaker activated for {source_name}")
            else:
                self.source_states[source_name] = DataSourceStatus.FAILING

    def get_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """
        複数データソースからデータ取得（品質監視統合版）

        Args:
            **kwargs: 各データソース固有のパラメータ

        Returns:
            取得されたデータのDataFrame
        """
        start_time = time.time()

        try:
            # 機能無効チェック
            if not self.enabled:
                logger.info(f"⚠️ {self.data_type} fetcher is disabled")
                return None

            # 品質監視システム取得
            try:
                from ..monitoring.data_quality_monitor import get_quality_monitor

                quality_monitor = get_quality_monitor(self.config)
            except ImportError:
                quality_monitor = None

            # グローバルキャッシュ有効性チェック（Phase A3対応）
            cached_data, cache_hit = self._is_cache_valid(**kwargs)
            if cache_hit and cached_data is not None:
                logger.info(
                    f"✅ Using global cached {self.data_type} data "
                    f"({len(cached_data)} records)"
                )

                # 品質監視記録（キャッシュ使用）
                if quality_monitor:
                    quality_monitor.record_quality_metrics(
                        source_type=self.data_type,
                        source_name="global_cache",
                        quality_score=1.0,  # キャッシュデータは品質保証済み
                        default_ratio=0.0,  # キャッシュはデフォルト値なし
                        success=True,
                        latency_ms=(time.time() - start_time) * 1000,
                    )

                return cached_data

            logger.info(f"🔍 Fetching {self.data_type} data from multiple sources")

            # 有効なデータソースを順次試行
            for source_config in self.data_sources:
                if not source_config.enabled:
                    continue

                # サーキットブレーカーチェック
                if self._check_circuit_breaker(source_config.name):
                    logger.warning(
                        f"🚨 {source_config.name} circuit breaker active, skipping"
                    )
                    continue

                # データ取得試行
                result = self._fetch_from_source(source_config, **kwargs)

                # 品質監視記録
                if quality_monitor:
                    quality_monitor.record_quality_metrics(
                        source_type=self.data_type,
                        source_name=source_config.name,
                        quality_score=result.quality_score,
                        default_ratio=self._calculate_default_ratio(result.data),
                        success=result.success,
                        latency_ms=result.fetch_time * 1000,
                        error_count=1 if not result.success else 0,
                    )

                # 結果評価
                if result.success and result.data is not None:
                    logger.info(
                        f"✅ {self.data_type} data from {source_config.name}: "
                        f"{len(result.data)} records, "
                        f"quality={result.quality_score:.3f}"
                    )

                    # 品質閾値チェック
                    if result.quality_score >= source_config.quality_threshold:
                        # 成功処理
                        self._update_source_state(source_config.name, True)
                        self._update_cache(result.data, result.quality_score, **kwargs)
                        return result.data
                    else:
                        logger.warning(
                            f"⚠️ Low quality {self.data_type} data from "
                            f"{source_config.name}: {result.quality_score:.3f} < "
                            f"{source_config.quality_threshold}"
                        )
                else:
                    logger.warning(
                        f"❌ Failed to fetch {self.data_type} data from "
                        f"{source_config.name}: {result.error}"
                    )

                # 失敗処理
                self._update_source_state(source_config.name, False)

            # すべてのソースが失敗
            logger.warning(f"❌ All {self.data_type} data sources failed")

            # フォールバック処理
            fallback_data = self._generate_fallback_data(**kwargs)
            if fallback_data is not None and not fallback_data.empty:
                logger.info(
                    f"✅ Using {self.data_type} fallback data: "
                    f"{len(fallback_data)} records"
                )

                # フォールバック品質監視記録
                if quality_monitor:
                    quality_monitor.record_quality_metrics(
                        source_type=self.data_type,
                        source_name="fallback",
                        quality_score=0.3,  # フォールバックは低品質
                        default_ratio=1.0,  # フォールバックは100%デフォルト
                        success=True,
                        latency_ms=(time.time() - start_time) * 1000,
                    )

                # 低品質でもキャッシュ更新
                self._update_cache(fallback_data, 0.3)
                return fallback_data

            logger.error(f"❌ All {self.data_type} data sources and fallback failed")

            # 完全失敗の品質監視記録
            if quality_monitor:
                quality_monitor.record_quality_metrics(
                    source_type=self.data_type,
                    source_name="all_sources",
                    quality_score=0.0,
                    default_ratio=1.0,
                    success=False,
                    latency_ms=(time.time() - start_time) * 1000,
                    error_count=len(self.data_sources),
                )

            return None

        except Exception as e:
            logger.error(f"❌ {self.data_type} data fetch failed: {e}")

            # 例外時の品質監視記録
            if quality_monitor:
                quality_monitor.record_quality_metrics(
                    source_type=self.data_type,
                    source_name="exception",
                    quality_score=0.0,
                    default_ratio=1.0,
                    success=False,
                    latency_ms=(time.time() - start_time) * 1000,
                    error_count=1,
                )

            return None

    def _fetch_from_source(
        self, source_config: DataSourceConfig, **kwargs
    ) -> DataSourceResult:
        """特定データソースからデータ取得"""
        start_time = time.time()

        try:
            # 抽象メソッド呼び出し
            data = self._fetch_data_from_source(source_config.name, **kwargs)
            fetch_time = time.time() - start_time

            if data is None or data.empty:
                return DataSourceResult(
                    source_name=source_config.name,
                    data=None,
                    quality_score=0.0,
                    error="No data returned",
                    fetch_time=fetch_time,
                    success=False,
                )

            # データ品質検証
            quality_score = self._validate_data_quality(data)

            return DataSourceResult(
                source_name=source_config.name,
                data=data,
                quality_score=quality_score,
                error=None,
                fetch_time=fetch_time,
                success=True,
            )

        except Exception as e:
            fetch_time = time.time() - start_time
            return DataSourceResult(
                source_name=source_config.name,
                data=None,
                quality_score=0.0,
                error=str(e),
                fetch_time=fetch_time,
                success=False,
            )

    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """データソース状態取得"""
        status = {}
        for source_config in self.data_sources:
            status[source_config.name] = {
                "status": self.source_states.get(
                    source_config.name, DataSourceStatus.ACTIVE
                ).value,
                "failure_count": self.source_failure_counts.get(source_config.name, 0),
                "enabled": source_config.enabled,
                "priority": source_config.priority,
                "circuit_breaker_active": self._check_circuit_breaker(
                    source_config.name
                ),
            }
        return status

    def get_cache_info(self) -> Dict[str, Any]:
        """キャッシュ情報取得"""
        return {
            "cache_valid": self._is_cache_valid(),
            "cache_age_hours": (
                (datetime.now() - self.cache_timestamp).total_seconds() / 3600
                if self.cache_timestamp
                else None
            ),
            "cache_records": (
                len(self.cache_data) if self.cache_data is not None else 0
            ),
            "cache_quality_score": self.cache_quality_score,
            "cache_hours_limit": self.cache_hours,
        }

    def _calculate_default_ratio(self, data: Optional[pd.DataFrame]) -> float:
        """デフォルト値比率計算（30%ルール用）"""
        if data is None or data.empty:
            return 1.0  # データがない場合は100%デフォルト

        try:
            # データソース特有のデフォルト値判定ロジック
            # 基本的には0値、NaN値、特定のデフォルト値をチェック
            total_values = data.size
            if total_values == 0:
                return 1.0

            # NaN値のカウント
            nan_count = data.isnull().sum().sum()

            # 0値のカウント（数値カラムのみ）
            zero_count = 0
            for col in data.select_dtypes(include=["number"]).columns:
                zero_count += (data[col] == 0).sum()

            # データソース特有のデフォルト値判定
            default_count = self._count_default_values(data)

            # 総デフォルト値（NaN + 0 + 特有デフォルト）
            total_default = nan_count + zero_count + default_count

            # 比率計算
            default_ratio = min(total_default / total_values, 1.0)

            return default_ratio

        except Exception as e:
            logger.error(f"❌ Failed to calculate default ratio: {e}")
            return 1.0  # エラー時は100%デフォルト扱い

    def _count_default_values(self, data: pd.DataFrame) -> int:
        """データソース特有のデフォルト値カウント（継承クラスでオーバーライド可能）"""
        # 基本実装では0を返す
        # 継承クラスで特有のデフォルト値判定を実装
        return 0

    # 抽象メソッド（継承クラスで実装）

    @abstractmethod
    def _fetch_data_from_source(
        self, source_name: str, **kwargs
    ) -> Optional[pd.DataFrame]:
        """特定データソースからデータ取得（継承クラスで実装）"""
        pass

    @abstractmethod
    def _validate_data_quality(self, data: pd.DataFrame) -> float:
        """データ品質検証（継承クラスで実装）"""
        pass

    @abstractmethod
    def _generate_fallback_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """フォールバックデータ生成（継承クラスで実装）"""
        pass
