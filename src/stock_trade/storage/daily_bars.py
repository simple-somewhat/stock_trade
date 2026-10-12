"""Incremental local cache for normalized daily bars."""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from stock_trade.config import Settings
from stock_trade.providers.akshare import DAILY_BAR_COLUMNS
from stock_trade.providers.base import DailyBarProvider
from stock_trade.storage.catalog import DuckDBCatalog


@dataclass(frozen=True)
class SyncResult:
    symbol: str
    adjust: str
    row_count: int
    fetched_rows: int
    last_trade_date: date | None


class DailyBarStore:
    """Store each symbol's canonical daily bars in a Parquet file."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_project_root()
        self.settings.ensure_directories()
        self.catalog = DuckDBCatalog(self.settings)

    def parquet_path(self, symbol: str, adjust: str) -> Path:
        normalized_symbol = symbol.zfill(6)
        adjustment = adjust or "none"
        return self.settings.daily_bars_dir / f"adjust={adjustment}" / f"symbol={normalized_symbol}.parquet"

    def read_bars(self, symbol: str, adjust: str = "qfq", limit: int | None = None) -> pd.DataFrame:
        parquet_path = self.parquet_path(symbol, adjust)
        if not parquet_path.exists():
            return pd.DataFrame(columns=DAILY_BAR_COLUMNS)

        limit_clause = "" if limit is None else f" LIMIT {int(limit)}"
        query = (
            "SELECT * FROM read_parquet(?) "
            "ORDER BY trade_date DESC"
            f"{limit_clause}"
        )
        with duckdb.connect(str(self.settings.database_path)) as connection:
            bars = connection.execute(query, [str(parquet_path)]).fetchdf()
        return bars.sort_values("trade_date").reset_index(drop=True)

    def sync_symbol(
        self,
        provider: DailyBarProvider,
        symbol: str,
        adjust: str = "qfq",
        lookback_days: int = 730,
        overlap_days: int = 7,
        end_date: date | None = None,
    ) -> SyncResult:
        existing_bars = self.read_bars(symbol, adjust)
        target_end_date = end_date or date.today()
        if existing_bars.empty:
            start_date = target_end_date - timedelta(days=lookback_days)
        else:
            last_trade_date = pd.Timestamp(existing_bars["trade_date"].max()).date()
            start_date = last_trade_date - timedelta(days=overlap_days)

        fetched_bars = provider.fetch_daily_bars(symbol, start_date, target_end_date, adjust)
        merged_bars = pd.concat([existing_bars, fetched_bars], ignore_index=True)
        merged_bars = merged_bars.drop_duplicates(subset=["trade_date"], keep="last")
        merged_bars = merged_bars.sort_values("trade_date").reset_index(drop=True)

        if not merged_bars.empty:
            self._write_bars(symbol, adjust, merged_bars)
            first_trade_date = pd.Timestamp(merged_bars["trade_date"].min()).date()
            last_trade_date = pd.Timestamp(merged_bars["trade_date"].max()).date()
        else:
            first_trade_date = None
            last_trade_date = None

        self.catalog.record_sync_state(
            symbol=symbol.zfill(6),
            adjust=adjust,
            source=getattr(provider, "source_name", provider.__class__.__name__),
            first_trade_date=first_trade_date,
            last_trade_date=last_trade_date,
            row_count=len(merged_bars),
        )
        return SyncResult(
            symbol=symbol.zfill(6),
            adjust=adjust,
            row_count=len(merged_bars),
            fetched_rows=len(fetched_bars),
            last_trade_date=last_trade_date,
        )

    def _write_bars(self, symbol: str, adjust: str, bars: pd.DataFrame) -> None:
        parquet_path = self.parquet_path(symbol, adjust)
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = parquet_path.with_suffix(".tmp.parquet")
        bars.to_parquet(temporary_path, engine="pyarrow", index=False)
        temporary_path.replace(parquet_path)
