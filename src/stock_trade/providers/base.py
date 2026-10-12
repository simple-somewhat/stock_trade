"""Protocols shared by market-data providers."""

from datetime import date
from typing import Protocol

import pandas as pd


class DailyBarProvider(Protocol):
    """Fetch normalized daily price bars for a security."""

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust: str,
    ) -> pd.DataFrame:
        """Return daily bars ordered by ascending trade date."""
