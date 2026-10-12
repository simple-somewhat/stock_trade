"""The project's first two stock-screening strategies."""

from abc import ABC, abstractmethod

import pandas as pd


class StrategyBase(ABC):
    """Base contract for a daily-bar screening strategy."""

    minimum_history = 1

    @abstractmethod
    def strategy_run(self, daily_bars: pd.DataFrame) -> bool:
        """Return whether one security matches this strategy."""

    @property
    def name(self) -> str:
        return self.__class__.__name__


class StrategyTrendChange(StrategyBase):
    """Identify a large early pullback followed by a potential stabilization."""

    minimum_history = 30
    required_columns = {"close", "volume"}

    def strategy_run(self, daily_bars: pd.DataFrame) -> bool:
        if len(daily_bars) < 30 or not self.required_columns.issubset(daily_bars.columns):
            return False

        last_30 = daily_bars.tail(30).copy()
        if last_30["close"].isna().any() or last_30["volume"].isna().any():
            return False

        max_close = last_30["close"].max()
        min_close = last_30["close"].min()
        max_volume = last_30["volume"].max()
        min_volume = last_30["volume"].min()
        if min_close <= 0 or min_volume <= 0:
            return False
        if (max_close - min_close) / min_close <= 0.12:
            return False

        close_change = last_30["close"].diff(periods=-1)
        next_close = last_30["close"].shift(periods=-1)
        percentage_change = close_change / next_close
        percentage_change.iloc[-1] = 0.0
        max_percentage_change = percentage_change.max()

        if max_percentage_change < 0:
            return False
        if not percentage_change.iloc[:4].apply(
            lambda value: abs(value - max_percentage_change) <= 0.0001
        ).any():
            return False
        if (percentage_change < 0).sum() > 9:
            return False
        return max_volume / min_volume > 3


class StrategySlowRise(StrategyBase):
    """Identify a relatively stable twenty-day upward trend."""

    minimum_history = 20
    required_columns = {"change_pct"}

    def strategy_run(self, daily_bars: pd.DataFrame) -> bool:
        if len(daily_bars) < 20 or not self.required_columns.issubset(daily_bars.columns):
            return False

        last_20 = daily_bars.tail(20)
        change_pct = last_20["change_pct"]
        if change_pct.isna().any():
            return False
        if change_pct.max() > 0.065:
            return False
        if change_pct.sum() < 0:
            return False
        return (change_pct > 0).sum() >= 10


list_strategies: list[StrategyBase] = [StrategyTrendChange(), StrategySlowRise()]
