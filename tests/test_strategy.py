import pandas as pd

from stock_trade.strategies.stock_strategy import StrategySlowRise


def test_slow_rise_accepts_stable_positive_series() -> None:
    daily_bars = pd.DataFrame(
        {
            "trade_date": pd.date_range("2025-01-01", periods=20, freq="B"),
            "change_pct": [0.01] * 12 + [0.0] * 8,
        }
    )

    assert StrategySlowRise().strategy_run(daily_bars)


def test_slow_rise_rejects_single_day_gain_above_six_point_five_percent() -> None:
    daily_bars = pd.DataFrame(
        {
            "trade_date": pd.date_range("2025-01-01", periods=20, freq="B"),
            "change_pct": [0.01] * 19 + [0.066],
        }
    )

    assert not StrategySlowRise().strategy_run(daily_bars)
