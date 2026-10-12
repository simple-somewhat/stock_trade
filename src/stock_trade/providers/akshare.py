"""AKShare adapter that produces the project's canonical daily-bar schema."""

from datetime import date

import akshare as ak
import pandas as pd


DAILY_BAR_COLUMNS = [
    "symbol",
    "trade_date",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "change_pct",
    "turnover",
    "adjust",
    "source",
]


class AKShareProvider:
    """Read A-share daily data from AKShare's Eastmoney adapter."""

    source_name = "akshare.stock_zh_a_hist"

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        raw_bars = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust=adjust,
        )
        return self.normalize_daily_bars(raw_bars, symbol, adjust)

    def normalize_daily_bars(
        self,
        raw_bars: pd.DataFrame,
        symbol: str,
        adjust: str,
    ) -> pd.DataFrame:
        """Map AKShare's Chinese column names to stable internal names."""
        if raw_bars.empty:
            return pd.DataFrame(columns=DAILY_BAR_COLUMNS)

        renamed_bars = raw_bars.rename(
            columns={
                "日期": "trade_date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "涨跌幅": "change_pct",
                "换手率": "turnover",
            }
        )
        required_columns = {"trade_date", "open", "close", "high", "low", "volume"}
        missing_columns = required_columns - set(renamed_bars.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"AKShare daily bars missing required columns: {missing}")

        normalized_bars = renamed_bars.copy()
        for column in ("amount", "change_pct", "turnover"):
            if column not in normalized_bars:
                normalized_bars[column] = pd.NA

        normalized_bars["symbol"] = symbol.zfill(6)
        normalized_bars["trade_date"] = pd.to_datetime(normalized_bars["trade_date"])
        for column in ("open", "close", "high", "low", "volume", "amount", "change_pct", "turnover"):
            normalized_bars[column] = pd.to_numeric(normalized_bars[column], errors="coerce")

        # AKShare publishes percent fields in percentage points; strategies use decimal returns.
        normalized_bars["change_pct"] = normalized_bars["change_pct"] / 100
        normalized_bars["adjust"] = adjust
        normalized_bars["source"] = self.source_name
        normalized_bars = normalized_bars.dropna(subset=["trade_date", "close"])
        normalized_bars = normalized_bars.drop_duplicates(subset=["trade_date"], keep="last")
        return normalized_bars.loc[:, DAILY_BAR_COLUMNS].sort_values("trade_date").reset_index(drop=True)
