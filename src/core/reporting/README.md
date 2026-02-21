# src/core/reporting/ - レポート生成システム

## ファイル構成

```
src/core/reporting/
├── __init__.py               # エクスポート
├── base_reporter.py          # 基底レポーター（save_report / save_error_report）
└── paper_trading_reporter.py # ペーパートレードレポート生成
```

## クラス

### BaseReporter

レポート保存の共通インターフェース。`PaperTradingReporter`の親クラス。

```python
class BaseReporter:
    async def save_report(self, data, report_type, file_prefix="") -> Path
    async def save_error_report(self, error_message, context=None) -> Path
```

### PaperTradingReporter

ペーパートレードセッションの統計レポート生成（Markdown + JSON）。

```python
class PaperTradingReporter(BaseReporter):
    async def generate_session_report(self, session_stats) -> Path
    async def save_session_error_report(self, error_message, session_stats=None) -> Path
```

## 設定

`config/core/thresholds.yaml`:

```yaml
reporting:
  base_dir: logs/reports
  paper_trading_dir: logs/paper_trading_reports
```

## 使用箇所

- `src/core/execution/live_trading_runner.py` - `save_error_report()`
- `src/core/execution/backtest_runner.py` - `save_error_report()`
- `src/core/execution/paper_trading_runner.py` - `save_session_error_report()`
