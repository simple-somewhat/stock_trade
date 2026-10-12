from datetime import date

import pandas as pd

from stock_trade.config import Settings
from stock_trade.storage.daily_bars import DailyBarStore


class FakeDailyBarProvider:
    source_name = "test.provider"

    def __init__(self) -> None:
        self.calls = 0

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust: str,
    ) -> pd.DataFrame:
        self.calls += 1
        second_close = 2.0 if self.calls == 1 else 2.5
        return pd.DataFrame(
            {
                "symbol": [symbol] * 3,
                "trade_date": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
                "open": [1.0, 2.0, 3.0],
                "close": [1.0, second_close, 3.0],
                "high": [1.0, 2.5, 3.0],
                "low": [1.0, 1.5, 3.0],
                "volume": [100.0, 200.0, 300.0],
                "amount": [100.0, 400.0, 900.0],
                "change_pct": [0.0, 1.0, 0.5],
                "turnover": [0.1, 0.2, 0.3],
                "adjust": [adjust] * 3,
                "source": [self.source_name] * 3,
            }
        )


def test_sync_overwrites_overlapping_trade_dates(tmp_path) -> None:
    store = DailyBarStore(Settings.from_project_root(tmp_path))
    provider = FakeDailyBarProvider()

    store.sync_symbol(provider, "000001", end_date=date(2025, 1, 6))
    result = store.sync_symbol(provider, "000001", end_date=date(2025, 1, 6))

    cached_bars = store.read_bars("000001")
    assert result.row_count == 3
    assert cached_bars["trade_date"].is_unique
    assert cached_bars.loc[cached_bars["trade_date"] == pd.Timestamp("2025-01-03"), "close"].item() == 2.5
