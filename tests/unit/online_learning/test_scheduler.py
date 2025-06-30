# tests/unit/online_learning/test_scheduler.py
"""
Automatic retraining scheduler のテスト
"""

from unittest.mock import Mock

import pytest

from crypto_bot.online_learning.scheduler import (
    RetrainingJob,
    RetrainingTrigger,
    TriggerType,
)


class TestTriggerType:
    """TriggerType Enum のテストクラス"""

    def test_trigger_types(self):
        """トリガータイプのテスト"""
        assert TriggerType.PERFORMANCE_DEGRADATION.value == "performance_degradation"
        assert TriggerType.DRIFT_DETECTION.value == "drift_detection"
        assert TriggerType.SCHEDULED_TIME.value == "scheduled_time"
        assert TriggerType.SAMPLE_COUNT.value == "sample_count"
        assert TriggerType.MANUAL.value == "manual"

    def test_enum_members(self):
        """Enum メンバーのテスト"""
        expected_types = [
            "PERFORMANCE_DEGRADATION",
            "DRIFT_DETECTION",
            "SCHEDULED_TIME",
            "SAMPLE_COUNT",
            "MANUAL",
        ]

        actual_types = [member.name for member in TriggerType]

        for expected in expected_types:
            assert expected in actual_types


class TestRetrainingTrigger:
    """RetrainingTrigger のテストクラス"""

    def test_default_initialization(self):
        """デフォルト初期化のテスト"""
        trigger = RetrainingTrigger(trigger_type=TriggerType.PERFORMANCE_DEGRADATION)

        assert trigger.trigger_type == TriggerType.PERFORMANCE_DEGRADATION
        assert trigger.threshold is None
        assert trigger.schedule_cron is None
        assert trigger.sample_interval is None
        assert trigger.enabled is True
        assert trigger.priority == 1

    def test_performance_degradation_trigger(self):
        """パフォーマンス劣化トリガーのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.PERFORMANCE_DEGRADATION,
            threshold=0.1,
            enabled=True,
            priority=3,
        )

        assert trigger.trigger_type == TriggerType.PERFORMANCE_DEGRADATION
        assert trigger.threshold == 0.1
        assert trigger.enabled is True
        assert trigger.priority == 3

    def test_drift_detection_trigger(self):
        """ドリフト検出トリガーのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.DRIFT_DETECTION, threshold=0.05, priority=5
        )

        assert trigger.trigger_type == TriggerType.DRIFT_DETECTION
        assert trigger.threshold == 0.05
        assert trigger.priority == 5

    def test_scheduled_trigger(self):
        """スケジュールトリガーのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.SCHEDULED_TIME,
            schedule_cron="0 2 * * *",  # 毎日午前2時
            priority=2,
        )

        assert trigger.trigger_type == TriggerType.SCHEDULED_TIME
        assert trigger.schedule_cron == "0 2 * * *"
        assert trigger.priority == 2

    def test_sample_count_trigger(self):
        """サンプル数トリガーのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.SAMPLE_COUNT, sample_interval=1000, priority=1
        )

        assert trigger.trigger_type == TriggerType.SAMPLE_COUNT
        assert trigger.sample_interval == 1000
        assert trigger.priority == 1

    def test_manual_trigger(self):
        """手動トリガーのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.MANUAL, enabled=False  # 通常は無効
        )

        assert trigger.trigger_type == TriggerType.MANUAL
        assert trigger.enabled is False

    def test_disabled_trigger(self):
        """無効化されたトリガーのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.PERFORMANCE_DEGRADATION,
            threshold=0.1,
            enabled=False,
        )

        assert trigger.enabled is False
        assert trigger.trigger_type == TriggerType.PERFORMANCE_DEGRADATION

    def test_priority_ordering(self):
        """優先度順序のテスト"""
        low_priority = RetrainingTrigger(
            trigger_type=TriggerType.SAMPLE_COUNT, priority=1
        )
        high_priority = RetrainingTrigger(
            trigger_type=TriggerType.DRIFT_DETECTION, priority=5
        )

        assert high_priority.priority > low_priority.priority


class TestRetrainingJob:
    """RetrainingJob のテストクラス"""

    @pytest.fixture
    def mock_model(self):
        """モックモデル"""
        return Mock()

    @pytest.fixture
    def sample_trigger(self):
        """サンプルトリガー"""
        return RetrainingTrigger(
            trigger_type=TriggerType.PERFORMANCE_DEGRADATION, threshold=0.1
        )

    def test_initialization(self, mock_model, sample_trigger):
        """初期化のテスト"""
        from datetime import datetime

        job = RetrainingJob(
            job_id="test_job_001",
            trigger=sample_trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        assert job.job_id == "test_job_001"
        assert job.trigger == sample_trigger
        assert job.model == mock_model

    def test_job_id_uniqueness(self, mock_model, sample_trigger):
        """ジョブID一意性のテスト"""
        from datetime import datetime

        job1 = RetrainingJob(
            job_id="job_001",
            trigger=sample_trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        job2 = RetrainingJob(
            job_id="job_002",
            trigger=sample_trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        assert job1.job_id != job2.job_id

    def test_same_model_different_triggers(self, mock_model):
        """同一モデル・異なるトリガーのテスト"""
        trigger1 = RetrainingTrigger(
            trigger_type=TriggerType.PERFORMANCE_DEGRADATION, threshold=0.1
        )
        trigger2 = RetrainingTrigger(
            trigger_type=TriggerType.DRIFT_DETECTION, threshold=0.05
        )

        from datetime import datetime

        job1 = RetrainingJob(
            job_id="job1",
            trigger=trigger1,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )
        job2 = RetrainingJob(
            job_id="job2",
            trigger=trigger2,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        assert job1.model == job2.model
        assert job1.trigger != job2.trigger

    def test_job_with_scheduled_trigger(self, mock_model):
        """スケジュールトリガー付きジョブのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.SCHEDULED_TIME,
            schedule_cron="0 */6 * * *",  # 6時間毎
        )

        from datetime import datetime

        job = RetrainingJob(
            job_id="scheduled_job",
            trigger=trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        assert job.trigger.schedule_cron == "0 */6 * * *"
        assert job.trigger.trigger_type == TriggerType.SCHEDULED_TIME

    def test_job_with_sample_trigger(self, mock_model):
        """サンプル数トリガー付きジョブのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.SAMPLE_COUNT, sample_interval=5000
        )

        from datetime import datetime

        job = RetrainingJob(
            job_id="sample_job",
            trigger=trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        assert job.trigger.sample_interval == 5000
        assert job.trigger.trigger_type == TriggerType.SAMPLE_COUNT

    def test_job_with_disabled_trigger(self, mock_model):
        """無効トリガー付きジョブのテスト"""
        trigger = RetrainingTrigger(trigger_type=TriggerType.MANUAL, enabled=False)

        from datetime import datetime

        job = RetrainingJob(
            job_id="disabled_job",
            trigger=trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        assert job.trigger.enabled is False

    def test_high_priority_job(self, mock_model):
        """高優先度ジョブのテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.DRIFT_DETECTION, threshold=0.01, priority=10
        )

        from datetime import datetime

        job = RetrainingJob(
            job_id="urgent_job",
            trigger=trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=10,
            metadata={},
        )

        assert job.trigger.priority == 10

    def test_job_attributes_access(self, mock_model, sample_trigger):
        """ジョブ属性アクセスのテスト"""
        from datetime import datetime

        job = RetrainingJob(
            job_id="test_access",
            trigger=sample_trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        # 全ての属性にアクセス可能かテスト
        assert hasattr(job, "job_id")
        assert hasattr(job, "trigger")
        assert hasattr(job, "model")

        # 値が正しく設定されているかテスト
        assert job.job_id == "test_access"
        assert job.trigger == sample_trigger
        assert job.model == mock_model

    def test_job_string_representation(self, mock_model, sample_trigger):
        """ジョブ文字列表現のテスト"""
        from datetime import datetime

        job = RetrainingJob(
            job_id="repr_test",
            trigger=sample_trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        # 文字列表現が生成できるかテスト
        job_str = str(job)
        assert isinstance(job_str, str)
        assert len(job_str) > 0

    def test_multiple_jobs_creation(self, mock_model):
        """複数ジョブ作成のテスト"""
        triggers = [
            RetrainingTrigger(TriggerType.PERFORMANCE_DEGRADATION, threshold=0.1),
            RetrainingTrigger(TriggerType.DRIFT_DETECTION, threshold=0.05),
            RetrainingTrigger(TriggerType.SCHEDULED_TIME, schedule_cron="0 1 * * *"),
            RetrainingTrigger(TriggerType.SAMPLE_COUNT, sample_interval=2000),
        ]

        from datetime import datetime

        jobs = []
        for i, trigger in enumerate(triggers):
            job = RetrainingJob(
                job_id=f"job_{i}",
                trigger=trigger,
                model=mock_model,
                data_source=lambda: ([], []),
                timestamp=datetime.now(),
                priority=1,
                metadata={},
            )
            jobs.append(job)

        assert len(jobs) == 4
        assert all(job.model == mock_model for job in jobs)
        assert len(set(job.job_id for job in jobs)) == 4  # 全てユニーク

    def test_job_trigger_type_consistency(self, mock_model):
        """ジョブトリガータイプ一貫性のテスト"""
        for trigger_type in TriggerType:
            trigger = RetrainingTrigger(trigger_type=trigger_type)
            from datetime import datetime

            job = RetrainingJob(
                job_id=f"job_{trigger_type.value}",
                trigger=trigger,
                model=mock_model,
                data_source=lambda: ([], []),
                timestamp=datetime.now(),
                priority=1,
                metadata={},
            )

            assert job.trigger.trigger_type == trigger_type

    def test_job_with_complex_trigger(self, mock_model):
        """複雑なトリガー設定のテスト"""
        trigger = RetrainingTrigger(
            trigger_type=TriggerType.PERFORMANCE_DEGRADATION,
            threshold=0.05,
            enabled=True,
            priority=8,
        )

        from datetime import datetime

        job = RetrainingJob(
            job_id="complex_job",
            trigger=trigger,
            model=mock_model,
            data_source=lambda: ([], []),
            timestamp=datetime.now(),
            priority=1,
            metadata={},
        )

        assert job.trigger.threshold == 0.05
        assert job.trigger.enabled is True
        assert job.trigger.priority == 8
        assert job.trigger.trigger_type == TriggerType.PERFORMANCE_DEGRADATION
