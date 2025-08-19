import json
import os
from pathlib import Path

from crypto_bot.utils.status import update_status


def test_update_status(tmp_path):
    """Test status update functionality"""
    # Change to temporary directory to avoid conflicts
    original_cwd = Path.cwd()
    os.chdir(tmp_path)

    try:
        # Test basic status update
        update_status(
            total_profit=1000.0, trade_count=5, position="LONG", bot_state="running"
        )

        # Check if file was created
        status_file = tmp_path / "status.json"
        assert status_file.exists()

        # Check file contents
        with open(status_file, "r") as f:
            data = json.load(f)

        assert data["total_profit"] == 1000.0
        assert data["trade_count"] == 5
        assert data["position"] == "LONG"
        assert data["state"] == "running"
        assert "last_updated" in data

    finally:
        os.chdir(original_cwd)


def test_update_status_none_position(tmp_path):
    """Test status update with None position"""
    original_cwd = Path.cwd()
    os.chdir(tmp_path)

    try:
        # Test with None position
        update_status(total_profit=-500.0, trade_count=10, position=None)

        status_file = tmp_path / "status.json"
        with open(status_file, "r") as f:
            data = json.load(f)

        assert data["total_profit"] == -500.0
        assert data["trade_count"] == 10
        assert data["position"] == ""  # None becomes empty string
        assert data["state"] == "running"  # default value

    finally:
        os.chdir(original_cwd)


def test_update_status_overwrite(tmp_path):
    """Test that status updates overwrite previous data"""
    original_cwd = Path.cwd()
    os.chdir(tmp_path)

    try:
        # First update
        update_status(100.0, 1, "LONG")

        # Second update
        update_status(200.0, 2, "SHORT")

        status_file = tmp_path / "status.json"
        with open(status_file, "r") as f:
            data = json.load(f)

        # Should have the latest values
        assert data["total_profit"] == 200.0
        assert data["trade_count"] == 2
        assert data["position"] == "SHORT"

    finally:
        os.chdir(original_cwd)
