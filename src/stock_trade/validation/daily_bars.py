"""Validation rules for canonical daily bars."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ValidationReport:
    row_count: int
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


class DailyBarValidator:
    """Check structural and price-consistency invariants before strategy use."""

    required_columns = {"trade_date", "open", "close", "high", "low", "volume"}

    def validate(self, daily_bars: pd.DataFrame) -> ValidationReport:
        issues: list[ValidationIssue] = []
        missing_columns = self.required_columns - set(daily_bars.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            return ValidationReport(
                row_count=len(daily_bars),
                issues=(ValidationIssue("missing_columns", f"Missing required columns: {missing}"),),
            )

        if daily_bars.empty:
            issues.append(ValidationIssue("empty_dataset", "No daily bars available."))
            return ValidationReport(row_count=0, issues=tuple(issues))

        bars = daily_bars.copy()
        bars["trade_date"] = pd.to_datetime(bars["trade_date"], errors="coerce")
        if bars["trade_date"].isna().any():
            issues.append(ValidationIssue("invalid_trade_date", "One or more trade dates are invalid."))
        if bars["trade_date"].duplicated().any():
            issues.append(ValidationIssue("duplicate_trade_date", "Duplicate trade dates were found."))
        if not bars["trade_date"].is_monotonic_increasing:
            issues.append(ValidationIssue("unsorted_trade_date", "Trade dates are not sorted ascending."))

        prices = bars[["open", "close", "high", "low"]].apply(pd.to_numeric, errors="coerce")
        if prices.isna().any().any():
            issues.append(ValidationIssue("missing_price", "One or more OHLC prices are missing."))
        if (prices <= 0).any().any():
            issues.append(ValidationIssue("non_positive_price", "OHLC prices must be positive."))
        if (prices["high"] < prices[["open", "close", "low"]].max(axis=1)).any():
            issues.append(ValidationIssue("invalid_high", "High is below another OHLC price."))
        if (prices["low"] > prices[["open", "close", "high"]].min(axis=1)).any():
            issues.append(ValidationIssue("invalid_low", "Low is above another OHLC price."))

        volume = pd.to_numeric(bars["volume"], errors="coerce")
        if volume.isna().any():
            issues.append(ValidationIssue("missing_volume", "One or more volume values are missing."))
        if (volume < 0).any():
            issues.append(ValidationIssue("negative_volume", "Volume cannot be negative."))
        return ValidationReport(row_count=len(bars), issues=tuple(issues))
