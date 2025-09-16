"""
Trading module __init__.py utility functions test
カバレッジ向上のための簡単なテストファイル
"""

import pytest

from src.trading import (
    DEFAULT_RISK_CONFIG,
    RISK_PROFILES,
    create_risk_manager,
    get_risk_profile_config,
    list_risk_profiles,
)


class TestTradingInitUtilities:
    """Trading __init__.py ユーティリティ関数テスト"""

    def test_create_risk_manager_default(self):
        """デフォルト設定でのリスク管理器作成テスト"""
        risk_manager = create_risk_manager()

        assert risk_manager is not None
        assert hasattr(risk_manager, "config")
        assert hasattr(risk_manager, "drawdown_manager")

    def test_create_risk_manager_with_profile(self):
        """リスクプロファイル指定でのリスク管理器作成テスト"""
        risk_manager = create_risk_manager(risk_profile="conservative")

        assert risk_manager is not None
        assert hasattr(risk_manager, "config")
        assert hasattr(risk_manager, "drawdown_manager")

    def test_create_risk_manager_with_custom_config(self):
        """カスタム設定でのリスク管理器作成テスト"""
        custom_config = {"kelly_criterion": {"max_position_ratio": 0.05}}
        risk_manager = create_risk_manager(config=custom_config, initial_balance=500000)

        assert risk_manager is not None
        assert hasattr(risk_manager, "config")
        assert hasattr(risk_manager, "drawdown_manager")

    def test_get_risk_profile_config_balanced(self):
        """バランス型プロファイル設定取得テスト"""
        config = get_risk_profile_config("balanced")

        assert isinstance(config, dict)
        assert "kelly_criterion" in config
        assert "risk_thresholds" in config
        assert "drawdown_manager" in config
        assert "anomaly_detector" in config

    def test_get_risk_profile_config_conservative(self):
        """保守型プロファイル設定取得テスト"""
        config = get_risk_profile_config("conservative")

        assert isinstance(config, dict)
        assert config["kelly_criterion"]["max_position_ratio"] == 0.05
        assert config["risk_thresholds"]["min_ml_confidence"] == 0.35

    def test_get_risk_profile_config_aggressive(self):
        """積極型プロファイル設定取得テスト"""
        config = get_risk_profile_config("aggressive")

        assert isinstance(config, dict)
        assert config["kelly_criterion"]["max_position_ratio"] == 0.20
        assert config["risk_thresholds"]["min_ml_confidence"] == 0.25

    def test_get_risk_profile_config_invalid(self):
        """無効プロファイル名エラーテスト"""
        with pytest.raises(ValueError, match="無効なリスクプロファイル"):
            get_risk_profile_config("invalid_profile")

    def test_list_risk_profiles(self):
        """リスクプロファイル一覧取得テスト"""
        profiles = list_risk_profiles()

        assert isinstance(profiles, dict)
        assert "conservative" in profiles
        assert "balanced" in profiles
        assert "aggressive" in profiles

        for profile_name, description in profiles.items():
            assert isinstance(profile_name, str)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_risk_profiles_constant(self):
        """RISK_PROFILES定数テスト"""
        assert isinstance(RISK_PROFILES, dict)
        assert len(RISK_PROFILES) == 3

        for profile_name in ["conservative", "balanced", "aggressive"]:
            assert profile_name in RISK_PROFILES
            assert "kelly_criterion" in RISK_PROFILES[profile_name]
            assert "risk_thresholds" in RISK_PROFILES[profile_name]
            assert "description" in RISK_PROFILES[profile_name]

    def test_default_risk_config_constant(self):
        """DEFAULT_RISK_CONFIG定数テスト"""
        assert isinstance(DEFAULT_RISK_CONFIG, dict)
        assert "kelly_criterion" in DEFAULT_RISK_CONFIG
        assert "drawdown_manager" in DEFAULT_RISK_CONFIG
        assert "anomaly_detector" in DEFAULT_RISK_CONFIG
        assert "risk_thresholds" in DEFAULT_RISK_CONFIG

        # Kelly基準設定確認
        kelly_config = DEFAULT_RISK_CONFIG["kelly_criterion"]
        assert kelly_config["max_position_ratio"] == 0.10
        assert kelly_config["safety_factor"] == 0.7
        assert kelly_config["min_trades_for_kelly"] == 5

        # ドローダウン管理設定確認
        drawdown_config = DEFAULT_RISK_CONFIG["drawdown_manager"]
        assert drawdown_config["max_drawdown_ratio"] == 0.20
        assert drawdown_config["consecutive_loss_limit"] == 5
        assert drawdown_config["cooldown_hours"] == 24
