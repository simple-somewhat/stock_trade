import pandas as pd
import pytest

from stock_trade.backtest.signal_backtest import SignalBacktester
from stock_trade.services.backtesting import StrategyBacktestService
from stock_trade.strategies.stock_strategy import StrategySlowRise
from stock_trade.validation.daily_bars import DailyBarValidator


def test_validator_rejects_invalid_high_price() -> None:
    daily_bars = pd.DataFrame(
        {
            "trade_date": ["2025-01-02"],
            "open": [10.0],
            "close": [11.0],
            "high": [9.0],
            "low": [8.0],
            "volume": [100.0],
        }
    )

    report = DailyBarValidator().validate(daily_bars)

    assert not report.is_valid
    assert any(issue.code == "invalid_high" for issue in report.issues)


def test_backtest_uses_signal_from_the_previous_day() -> None:
    daily_bars = pd.DataFrame(
        {
            "trade_date": pd.date_range("2025-01-01", periods=3, freq="B"),
            "close": [100.0, 110.0, 121.0],
            "entry_signal": [True, False, False],
        }
    )

    result = SignalBacktester().run(daily_bars)

    assert result.equity_curve["position"].tolist() == [0, 1, 0]
    assert result.total_return == pytest.approx(0.1)


class FakeDailyBarStore:
    def __init__(self, daily_bars: pd.DataFrame) -> None:
        self.daily_bars = daily_bars

    def read_bars(self, symbol: str, adjust: str) -> pd.DataFrame:
        return self.daily_bars


def test_strategy_backtest_only_enters_after_minimum_history() -> None:
    close_prices = [100.0 + index for index in range(22)]
    daily_bars = pd.DataFrame(
        {
            "trade_date": pd.date_range("2025-01-01", periods=22, freq="B"),
            "open": close_prices,
            "close": close_prices,
            "high": close_prices,
            "low": close_prices,
            "volume": [100.0] * 22,
            "change_pct": [0.01] * 22,
        }
    )

    result = StrategyBacktestService(FakeDailyBarStore(daily_bars)).run("000001", StrategySlowRise())

    assert result.equity_curve["entry_signal"].tolist() == [False] * 19 + [True] * 3
    assert result.equity_curve["position"].tolist() == [0] * 20 + [1, 1]
