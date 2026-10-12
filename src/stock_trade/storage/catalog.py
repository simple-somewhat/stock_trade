"""DuckDB catalog for local Parquet datasets and research outputs."""

from datetime import datetime
from uuid import UUID

import duckdb

from stock_trade.config import Settings


class DuckDBCatalog:
    """Manage metadata while leaving daily bars in Parquet files."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.ensure_directories()
        self.initialize()

    def connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.settings.database_path))

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_bar_sync_state (
                    symbol VARCHAR NOT NULL,
                    adjust VARCHAR NOT NULL,
                    source VARCHAR NOT NULL,
                    first_trade_date DATE,
                    last_trade_date DATE,
                    row_count BIGINT NOT NULL,
                    synced_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (symbol, adjust)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_runs (
                    run_id UUID PRIMARY KEY,
                    strategy_name VARCHAR NOT NULL,
                    run_at TIMESTAMP NOT NULL,
                    universe_size BIGINT NOT NULL,
                    selected_count BIGINT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_signals (
                    run_id UUID NOT NULL,
                    strategy_name VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    trade_date DATE NOT NULL,
                    PRIMARY KEY (run_id, strategy_name, symbol)
                )
                """
            )

    def record_sync_state(
        self,
        symbol: str,
        adjust: str,
        source: str,
        first_trade_date: object,
        last_trade_date: object,
        row_count: int,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO daily_bar_sync_state
                    (symbol, adjust, source, first_trade_date, last_trade_date, row_count, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol, adjust) DO UPDATE SET
                    source = excluded.source,
                    first_trade_date = excluded.first_trade_date,
                    last_trade_date = excluded.last_trade_date,
                    row_count = excluded.row_count,
                    synced_at = excluded.synced_at
                """,
                [
                    symbol,
                    adjust,
                    source,
                    first_trade_date,
                    last_trade_date,
                    row_count,
                    datetime.now(),
                ],
            )

    def record_strategy_run(
        self,
        run_id: UUID,
        strategy_name: str,
        universe_size: int,
        signals: list[tuple[str, object]],
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO strategy_runs
                    (run_id, strategy_name, run_at, universe_size, selected_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                [str(run_id), strategy_name, datetime.now(), universe_size, len(signals)],
            )
            if signals:
                connection.executemany(
                    """
                    INSERT INTO strategy_signals (run_id, strategy_name, symbol, trade_date)
                    VALUES (?, ?, ?, ?)
                    """,
                    [(str(run_id), strategy_name, symbol, trade_date) for symbol, trade_date in signals],
                )
