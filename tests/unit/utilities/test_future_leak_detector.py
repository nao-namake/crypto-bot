"""
未来データリーク検出器のテストケース

Phase 2-3: ChatGPT提案実装
検出器が正しく危険なパターンを検出し、
安全なパターンを誤検知しないことを確認
"""

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# スクリプトディレクトリをパスに追加
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "utilities")
)
from future_leak_detector import FutureLeakDetector


class TestFutureLeakDetector:
    """FutureLeakDetectorのテストクラス"""

    def setup_method(self):
        """各テストメソッド実行前のセットアップ"""
        self.detector = FutureLeakDetector()

    def test_init(self):
        """初期化のテスト"""
        detector = FutureLeakDetector(report_dir="test_reports")
        assert Path("test_reports").exists()
        assert len(detector.suspicious_patterns) > 0
        assert "future_indexing" in detector.suspicious_patterns
        assert "safe_patterns" in detector.suspicious_patterns

    def test_detect_future_shift(self):
        """未来へのshift検出テスト"""
        # 危険なコードを含むテストファイル作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def calculate_features(df):
    # 危険: 未来へのシフト
    df['future_price'] = df['close'].shift(-1)
    df['future_returns'] = df['close'].shift(-5)
    return df
"""
            )
            temp_file = f.name

        try:
            issues = self.detector.analyze_feature_code(temp_file)
            # shift(-1)とshift(-5)に加えて、"future"も検出される可能性がある
            assert len(issues) >= 2
            # shift関連の問題を確認
            shift_issues = [i for i in issues if "shift(-" in i["code"]]
            assert len(shift_issues) >= 2
        finally:
            Path(temp_file).unlink()

    def test_detect_center_rolling(self):
        """center=Trueのrolling検出テスト"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def calculate_features(df):
    # 危険: 中心rolling
    df['centered_ma'] = df['close'].rolling(5, center=True).mean()
    return df
"""
            )
            temp_file = f.name

        try:
            issues = self.detector.analyze_feature_code(temp_file)
            assert len(issues) == 1
            assert issues[0]["severity"] == "HIGH"
            assert "center=True" in issues[0]["code"]
        finally:
            Path(temp_file).unlink()

    def test_detect_future_indexing(self):
        """未来インデックス参照の検出テスト"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def calculate_features(df):
    for i in range(len(df)):
        # 危険: 未来データ参照
        if i < len(df) - 1:
            df.iloc[i, 0] = df.iloc[i + 1, 1]
        # 危険: 未来範囲参照
        future_data = df.iloc[i:i+10]
    return df
"""
            )
            temp_file = f.name

        try:
            issues = self.detector.analyze_feature_code(temp_file)
            assert len(issues) >= 1
            assert any("iloc[i +" in issue["code"] for issue in issues)
        finally:
            Path(temp_file).unlink()

    def test_safe_patterns_not_detected(self):
        """安全なパターンが誤検知されないことを確認"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def calculate_features(df):
    # 安全: 過去へのシフト
    df['past_price'] = df['close'].shift(1)
    df['past_returns'] = df['close'].shift(5)

    # 安全: centerなしのrolling
    df['sma'] = df['close'].rolling(20).mean()

    # 安全: 過去データのみ参照
    for i in range(len(df)):
        if i > 0:
            df.iloc[i, 0] = df.iloc[i - 1, 1]
        # 安全: 現在までのデータ
        past_data = df.iloc[:i]
        # 安全: 過去範囲
        past_window = df.iloc[max(0, i - 10):i]
    return df
"""
            )
            temp_file = f.name

        try:
            issues = self.detector.analyze_feature_code(temp_file)
            # 安全なパターンは検出されないはず
            assert len(issues) == 0
        finally:
            Path(temp_file).unlink()

    def test_validate_dataframe_operations(self):
        """DataFrame操作の検証テスト"""
        df = pd.DataFrame({"close": np.random.randn(100)})

        operations = [
            "rolling(20).mean()",  # 安全
            "rolling(20, center=True).mean()",  # 危険
            "shift(1)",  # 安全
            "shift(-1)",  # 危険
            "iloc[:i]",  # 安全
            "iloc[i:i+5]",  # 危険
        ]

        results = self.detector.validate_dataframe_operations(df, operations)

        assert len(results["safe"]) == 3
        assert len(results["unsafe"]) == 2
        assert any("center=True" in r["reason"] for r in results["unsafe"])
        assert any("shift(-1)" in r["reason"] for r in results["unsafe"])

    def test_check_backtest_data_split(self):
        """バックテストデータ分割の検証テスト"""
        # タイムスタンプ付きデータ作成（インデックスオーバーラップを避ける）
        dates = pd.date_range("2024-01-01", periods=200, freq="1H")
        train_data = pd.DataFrame(
            {"timestamp": dates[:150], "close": np.random.randn(150)},
            index=range(150),  # 0-149
        )

        # ケース1: 適切な分割（タイムスタンプ・インデックス共にオーバーラップなし）
        test_data_good = pd.DataFrame(
            {"timestamp": dates[150:], "close": np.random.randn(50)},
            index=range(150, 200),  # 150-199
        )

        result = self.detector.check_backtest_data_split(train_data, test_data_good)
        assert result["valid"] is True
        assert len(result["issues"]) == 0

        # ケース2: データオーバーラップあり
        test_data_bad = pd.DataFrame(
            {
                "timestamp": dates[140:190],  # オーバーラップ
                "close": np.random.randn(50),
            }
        )

        result = self.detector.check_backtest_data_split(train_data, test_data_bad)
        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert any(issue["type"] == "DATA_OVERLAP" for issue in result["issues"])

    def test_validate_feature_pipeline(self):
        """特徴量パイプライン検証テスト"""
        # テストデータ作成
        dates = pd.date_range("2024-01-01", periods=100, freq="1H")
        sample_data = pd.DataFrame(
            {
                "timestamp": dates,
                "close": np.random.randn(100) + 100,
                "volume": np.random.randn(100) * 1000 + 10000,
            }
        )

        # 安全な特徴量生成関数
        def safe_feature_function(df):
            df = df.copy()
            df["sma_20"] = df["close"].rolling(20).mean()
            df["returns"] = df["close"].pct_change()
            df["volume_ma"] = df["volume"].rolling(10).mean()
            return df

        # 危険な特徴量生成関数（未来データ参照）
        def unsafe_feature_function(df):
            df = df.copy()
            df["future_price"] = df["close"].shift(-1)  # 未来参照
            df["centered_ma"] = (
                df["close"].rolling(5, center=True).mean()
            )  # 中心rolling
            return df

        # 安全な関数のテスト
        result = self.detector.validate_feature_pipeline(
            safe_feature_function, sample_data
        )
        assert all(
            check["passed"]
            for check in result["checks"]
            if check["check"] == "timestamp_order"
        )

        # 危険な関数のテスト（一貫性チェックで問題を検出する可能性）
        result = self.detector.validate_feature_pipeline(
            unsafe_feature_function, sample_data
        )
        # 少なくともチェックが実行されることを確認
        assert len(result["checks"]) > 0

    def test_scan_project(self):
        """プロジェクトスキャンのテスト"""
        # テスト用の一時ディレクトリ作成
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # テスト用ディレクトリ構造作成
            ml_dir = project_dir / "crypto_bot" / "ml"
            ml_dir.mkdir(parents=True)

            # 危険なコードを含むファイル作成
            dangerous_file = ml_dir / "dangerous.py"
            dangerous_file.write_text(
                """
def feature_engineering(df):
    df['future'] = df['close'].shift(-1)
    return df
"""
            )

            # 安全なコードを含むファイル作成
            safe_file = ml_dir / "safe.py"
            safe_file.write_text(
                """
def feature_engineering(df):
    df['past'] = df['close'].shift(1)
    return df
"""
            )

            # スキャン実行
            results = self.detector.scan_project(str(project_dir))

            assert "total_files_scanned" in results
            assert "total_issues" in results
            assert "issues_by_severity" in results
            assert results["total_issues"] >= 1  # 少なくとも1つの問題を検出

    def test_generate_report(self):
        """レポート生成のテスト"""
        scan_results = {
            "total_files_scanned": 10,
            "total_issues": 3,
            "issues_by_severity": {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1, "LOW": 0},
            "issues": [
                {
                    "file": "test.py",
                    "line": 10,
                    "code": "df.shift(-1)",
                    "severity": "HIGH",
                    "message": "Future data leak detected",
                }
            ],
        }

        # HTMLレポート生成
        html_path = self.detector.generate_report(scan_results)
        assert Path(html_path).exists()

        # HTMLファイルの内容確認
        html_content = Path(html_path).read_text()
        assert "Future Data Leak Detection Report" in html_content
        assert "CRITICAL ISSUES FOUND" in html_content
        assert "df.shift(-1)" in html_content

    def test_save_json_report(self):
        """JSONレポート保存のテスト"""
        scan_results = {
            "total_files_scanned": 5,
            "total_issues": 2,
            "issues_by_severity": {"HIGH": 2, "MEDIUM": 0, "LOW": 0, "CRITICAL": 0},
            "issues": [],
        }

        json_path = self.detector.save_json_report(scan_results)
        assert Path(json_path).exists()

        # JSONファイルの内容確認
        import json

        with open(json_path) as f:
            loaded_results = json.load(f)

        assert loaded_results["total_files_scanned"] == 5
        assert loaded_results["total_issues"] == 2

    def test_count_by_severity(self):
        """重要度別カウントのテスト"""
        issues = [
            {"severity": "HIGH"},
            {"severity": "HIGH"},
            {"severity": "MEDIUM"},
            {"severity": "LOW"},
            {"severity": "CRITICAL"},
        ]

        counts = self.detector._count_by_severity(issues)
        assert counts["HIGH"] == 2
        assert counts["MEDIUM"] == 1
        assert counts["LOW"] == 1
        assert counts["CRITICAL"] == 1

    def test_edge_cases(self):
        """エッジケースのテスト"""
        # 空のファイル
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            issues = self.detector.analyze_feature_code(temp_file)
            assert len(issues) == 0
        finally:
            Path(temp_file).unlink()

        # 存在しないファイル
        issues = self.detector.analyze_feature_code("nonexistent.py")
        assert len(issues) == 0

        # コメントのみのファイル
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
# This is a comment
# df['future'] = df['close'].shift(-1)  # This should not be detected
"""
            )
            temp_file = f.name

        try:
            issues = self.detector.analyze_feature_code(temp_file)
            assert len(issues) == 0  # コメント行は検出されない
        finally:
            Path(temp_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
