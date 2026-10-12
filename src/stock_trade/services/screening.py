"""Run strategies from the local daily-bar cache."""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pandas as pd

from stock_trade.storage.daily_bars import DailyBarStore
from stock_trade.strategies.stock_strategy import StrategyBase
from stock_trade.validation.daily_bars import DailyBarValidator


@dataclass(frozen=True)
class ScreeningResult:
    run_ids: dict[str, UUID]
    selected_symbols: dict[str, list[str]]
    rejected_symbols: dict[str, str]


class ScreeningService:
    """Use validated cached bars to screen a stock universe."""

    def __init__(self, daily_bar_store: DailyBarStore, validator: DailyBarValidator | None = None) -> None:
        self.daily_bar_store = daily_bar_store
        self.validator = validator or DailyBarValidator()

    def run(
        self,
        symbols: list[str],
        strategies: list[StrategyBase],
        adjust: str = "qfq",
    ) -> ScreeningResult:
        selected: dict[str, list[tuple[str, object]]] = {strategy.name: [] for strategy in strategies}
        rejected: dict[str, str] = {}

        for symbol in symbols:
            daily_bars = self.daily_bar_store.read_bars(symbol, adjust)
            report = self.validator.validate(daily_bars)
            if not report.is_valid:
                rejected[symbol] = "; ".join(issue.message for issue in report.issues)
                continue
            self._run_strategies(symbol, daily_bars, strategies, selected)

        run_ids: dict[str, UUID] = {}
        selected_symbols: dict[str, list[str]] = {}
        for strategy in strategies:
            run_id = uuid4()
            strategy_signals = selected[strategy.name]
            self.daily_bar_store.catalog.record_strategy_run(
                run_id=run_id,
                strategy_name=strategy.name,
                universe_size=len(symbols),
                signals=strategy_signals,
            )
            run_ids[strategy.name] = run_id
            selected_symbols[strategy.name] = [symbol for symbol, _ in strategy_signals]
        return ScreeningResult(run_ids, selected_symbols, rejected)

    @staticmethod
    def _run_strategies(
        symbol: str,
        daily_bars: pd.DataFrame,
        strategies: list[StrategyBase],
        selected: dict[str, list[tuple[str, object]]],
    ) -> None:
        trade_date = pd.Timestamp(daily_bars["trade_date"].max()).date()
        for strategy in strategies:
            if strategy.strategy_run(daily_bars):
                selected[strategy.name].append((symbol.zfill(6), trade_date))
