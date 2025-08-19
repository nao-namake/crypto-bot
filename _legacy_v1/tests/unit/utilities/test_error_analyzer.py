"""
エラー分析器のテストケース

Phase 3: ChatGPT提案実装
エラーパターン検出と修復提案生成のテスト
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# スクリプトディレクトリをパスに追加
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "utilities")
)
from error_analyzer import ErrorAnalyzer


class TestErrorAnalyzer:
    """ErrorAnalyzerのテストクラス"""

    def setup_method(self):
        """各テストメソッド実行前のセットアップ"""
        # 一時ディレクトリでテスト
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = ErrorAnalyzer(
            solutions_db_path=f"{self.temp_dir}/test_solutions.json",
            report_dir=f"{self.temp_dir}/reports",
        )

    def test_init(self):
        """初期化のテスト"""
        assert self.analyzer.error_patterns is not None
        assert "patterns" in self.analyzer.error_patterns
        assert len(self.analyzer.error_patterns["patterns"]) > 0
        assert Path(self.analyzer.report_dir).exists()

    def test_analyze_error_patterns_auth_error(self):
        """認証エラーパターンの検出テスト"""
        errors = [
            {"message": "401 Unauthorized: Invalid API key", "severity": "ERROR"},
            {"message": "Authentication failed", "severity": "CRITICAL"},
            {"message": "403 Forbidden", "severity": "ERROR"},
        ]

        analysis = self.analyzer.analyze_error_patterns(errors)

        assert "pattern_matches" in analysis
        assert "api_auth_error" in analysis["pattern_matches"]
        assert len(analysis["pattern_matches"]["api_auth_error"]) == 3
        assert analysis["statistics"]["matched_errors"] == 3

    def test_analyze_error_patterns_model_error(self):
        """モデルエラーパターンの検出テスト"""
        errors = [
            {
                "message": "FileNotFoundError: model.pkl not found",
                "severity": "ERROR",
            },
            {"message": "No such file or directory: 'model'", "severity": "ERROR"},
        ]

        analysis = self.analyzer.analyze_error_patterns(errors)

        assert "model_not_found" in analysis["pattern_matches"]
        assert len(analysis["pattern_matches"]["model_not_found"]) == 2

    def test_analyze_error_patterns_mixed(self):
        """複数のエラーパターン混在時のテスト"""
        errors = [
            {"message": "401 Unauthorized", "severity": "ERROR"},
            {"message": "FileNotFoundError: model.pkl", "severity": "ERROR"},
            {"message": "HTTPError: Connection refused", "severity": "ERROR"},
            {"message": "Unknown error occurred", "severity": "ERROR"},
        ]

        analysis = self.analyzer.analyze_error_patterns(errors)

        assert len(analysis["pattern_matches"]) >= 3
        assert analysis["statistics"]["unmatched_errors"] == 1
        assert analysis["statistics"]["total_errors"] == 4

    def test_generate_suggestions(self):
        """修復提案生成のテスト"""
        pattern_matches = {
            "api_auth_error": [{"message": "401"}, {"message": "403"}],
            "model_not_found": [{"message": "model.pkl not found"}],
        }

        suggestions = self.analyzer.generate_suggestions(pattern_matches)

        assert len(suggestions) == 2
        # 優先度順にソートされているか確認
        assert suggestions[0]["severity"] in ["CRITICAL", "HIGH"]
        assert "solutions" in suggestions[0]
        assert len(suggestions[0]["solutions"]) > 0
        assert suggestions[0]["error_count"] > 0

    def test_priority_calculation(self):
        """優先度計算のテスト"""
        # CRITICAL with 5 errors
        priority1 = self.analyzer._calculate_priority("CRITICAL", 5)
        # HIGH with 10 errors
        priority2 = self.analyzer._calculate_priority("HIGH", 10)
        # MEDIUM with 1 error
        priority3 = self.analyzer._calculate_priority("MEDIUM", 1)

        assert priority1 > priority3  # CRITICALは常に高優先度
        assert priority2 > priority3  # エラー数が多いHIGHも優先

    def test_learn_from_resolution(self):
        """解決結果学習のテスト"""
        initial_rate = self.analyzer.error_patterns["patterns"][0]["success_rate"]

        # 成功を記録
        self.analyzer.learn_from_resolution("api_auth_error", 0, True)
        new_rate = self.analyzer.error_patterns["patterns"][0]["success_rate"]

        # 成功率が上がることを確認
        assert new_rate >= initial_rate

        # 失敗を記録
        self.analyzer.learn_from_resolution("api_auth_error", 0, False)
        final_rate = self.analyzer.error_patterns["patterns"][0]["success_rate"]

        # 成功率が下がることを確認
        assert final_rate < new_rate

    def test_save_and_load_solutions_db(self):
        """データベース保存・読み込みのテスト"""
        # パターンを追加
        new_pattern = {
            "id": "test_pattern",
            "pattern": r"test error",
            "category": "Test",
            "severity": "LOW",
            "solutions": ["Test solution"],
            "success_rate": 0.5,
        }
        self.analyzer.error_patterns["patterns"].append(new_pattern)

        # 保存
        self.analyzer.save_solutions_db()

        # 新しいインスタンスで読み込み
        new_analyzer = ErrorAnalyzer(
            solutions_db_path=f"{self.temp_dir}/test_solutions.json"
        )

        # 追加したパターンが存在することを確認
        pattern_ids = [p["id"] for p in new_analyzer.error_patterns["patterns"]]
        assert "test_pattern" in pattern_ids

    def test_fetch_local_logs(self):
        """ローカルログ読み込みのテスト"""
        # テスト用ログファイル作成
        log_dir = Path(self.temp_dir) / "logs"
        log_dir.mkdir()

        log_file = log_dir / "test.log"
        log_file.write_text(
            "INFO: Normal operation\n"
            "ERROR: Test error message\n"
            "CRITICAL: Critical error\n"
            "DEBUG: Debug info\n"
        )

        errors = self.analyzer.fetch_local_logs(str(log_dir))

        assert len(errors) == 2
        assert any("Test error" in e["message"] for e in errors)
        assert any("Critical error" in e["message"] for e in errors)

    @patch("subprocess.run")
    def test_fetch_gcp_logs(self, mock_run):
        """GCPログ取得のテスト（モック）"""
        # モックレスポンス
        mock_logs = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "severity": "ERROR",
                "textPayload": "API authentication failed",
            },
            {
                "timestamp": "2024-01-01T00:01:00Z",
                "severity": "CRITICAL",
                "jsonPayload": {"error": "Database connection lost"},
            },
        ]

        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(mock_logs), stderr=""
        )

        errors = self.analyzer.fetch_gcp_logs(hours=1)

        assert len(errors) == 2
        assert errors[0]["message"] == "API authentication failed"
        mock_run.assert_called_once()

    def test_generate_report(self):
        """HTMLレポート生成のテスト"""
        analysis = {
            "statistics": {
                "total_errors": 10,
                "matched_errors": 8,
                "unmatched_errors": 2,
                "unique_patterns": 3,
                "top_patterns": [("api_auth_error", 5), ("model_not_found", 3)],
            },
            "pattern_matches": {
                "api_auth_error": [{"message": "401"}] * 5,
                "model_not_found": [{"message": "model.pkl"}] * 3,
            },
        }

        suggestions = [
            {
                "pattern_id": "api_auth_error",
                "category": "Authentication",
                "severity": "CRITICAL",
                "error_count": 5,
                "solutions": ["Check API keys", "Verify permissions"],
                "success_rate": 0.85,
                "priority": 125,
            }
        ]

        report_path = self.analyzer.generate_report(analysis, suggestions)

        assert report_path.exists()
        html_content = report_path.read_text()
        assert "Error Analysis & Recovery Suggestions" in html_content
        assert "api_auth_error" in html_content
        assert "Check API keys" in html_content

    def test_run_analysis(self):
        """分析実行の統合テスト"""
        # テスト用ログファイル作成
        log_dir = Path(self.temp_dir) / "logs"
        log_dir.mkdir()

        log_file = log_dir / "test.log"
        log_file.write_text(
            "ERROR: 401 Unauthorized\n"
            "ERROR: FileNotFoundError: model.pkl not found\n"
            "ERROR: Connection timeout\n"
        )

        # ローカルログのみで分析実行
        with patch.object(
            self.analyzer,
            "fetch_local_logs",
            return_value=self.analyzer.fetch_local_logs(str(log_dir)),
        ):
            analysis, suggestions = self.analyzer.run_analysis(source="local", hours=1)

        assert analysis is not None
        assert len(suggestions) > 0
        assert analysis["statistics"]["total_errors"] == 3

    def test_edge_cases(self):
        """エッジケースのテスト"""
        # 空のエラーリスト
        analysis = self.analyzer.analyze_error_patterns([])
        assert analysis["statistics"]["total_errors"] == 0
        assert len(analysis["pattern_matches"]) == 0

        # 空のパターンマッチ
        suggestions = self.analyzer.generate_suggestions({})
        assert len(suggestions) == 0

        # 不正な重要度
        priority = self.analyzer._calculate_priority("UNKNOWN", 1)
        assert priority >= 0  # デフォルト値が返される


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
