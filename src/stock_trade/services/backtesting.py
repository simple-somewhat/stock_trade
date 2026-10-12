"""Run screening strategies through a local daily-bar cache."""

import pandas as pd

from stock_trade.backtest.signal_backtest import BacktestResult, SignalBacktester
from stock_trade.storage.daily_bars import DailyBarStore
from stock_trade.strategies.stock_strategy import StrategyBase
from stock_trade.validation.daily_bars import DailyBarValidator


class StrategyBacktestService:
    """Generate close-time signals without using future market data."""

    def __init__(
        self,
        daily_bar_store: DailyBarStore,
        validator: DailyBarValidator | None = None,
        backtester: SignalBacktester | None = None,
    ) -> None:
        self.daily_bar_store = daily_bar_store
        self.validator = validator or DailyBarValidator()
        self.backtester = backtester or SignalBacktester()

    def run(
        self,
        symbol: str,
        strategy: StrategyBase,
        adjust: str = "qfq",
    ) -> BacktestResult:
        daily_bars = self.daily_bar_store.read_bars(symbol, adjust)
        report = self.validator.validate(daily_bars)
        if not report.is_valid:
            issues = "; ".join(issue.message for issue in report.issues)
            raise ValueError(f"Cannot backtest {symbol}: {issues}")

        bars_with_signals = daily_bars.copy()
        bars_with_signals["entry_signal"] = self._generate_signals(bars_with_signals, strategy)
        return self.backtester.run(bars_with_signals)

    @staticmethod
    def _generate_signals(daily_bars: pd.DataFrame, strategy: StrategyBase) -> list[bool]:
        signals = [False] * len(daily_bars)
        first_signal_index = strategy.minimum_history - 1
        for row_index in range(first_signal_index, len(daily_bars)):
            signals[row_index] = strategy.strategy_run(daily_bars.iloc[: row_index + 1])
        return signals