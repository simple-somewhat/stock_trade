"""A minimal single-security signal backtester."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    total_return: float
    max_drawdown: float


class SignalBacktester:
    """Apply close-generated entry signals from the next trading day onward."""

    def run(self, daily_bars: pd.DataFrame, signal_column: str = "entry_signal") -> BacktestResult:
        required_columns = {"trade_date", "close", signal_column}
        missing_columns = required_columns - set(daily_bars.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Backtest data missing required columns: {missing}")

        bars = daily_bars.sort_values("trade_date").copy()
        bars["close"] = pd.to_numeric(bars["close"], errors="coerce")
        if bars["close"].isna().any() or (bars["close"] <= 0).any():
            raise ValueError("Backtest close prices must be positive numeric values.")

        bars["asset_return"] = bars["close"].pct_change().fillna(0.0)
        bars["position"] = bars[signal_column].fillna(False).astype(bool).shift(1).fillna(False).astype(int)
        bars["strategy_return"] = bars["position"] * bars["asset_return"]
        bars["equity"] = (1 + bars["strategy_return"]).cumprod()
        running_peak = bars["equity"].cummax()
        bars["drawdown"] = bars["equity"] / running_peak - 1
        return BacktestResult(
            equity_curve=bars,
            total_return=float(bars["equity"].iloc[-1] - 1),
            max_drawdown=float(bars["drawdown"].min()),
        )
