"""Command-line entry points for daily data operations."""

import argparse

from stock_trade.providers.akshare import AKShareProvider
from stock_trade.services.backtesting import StrategyBacktestService
from stock_trade.services.screening import ScreeningService
from stock_trade.storage.daily_bars import DailyBarStore
from stock_trade.strategies.stock_strategy import list_strategies
from stock_trade.validation.daily_bars import DailyBarValidator


def main() -> None:
    parser = argparse.ArgumentParser(description="Local A-share research data tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Incrementally cache daily bars from AKShare")
    sync_parser.add_argument("--symbols", nargs="+", required=True)
    sync_parser.add_argument("--adjust", default="qfq", choices=("", "qfq", "hfq"))

    screen_parser = subparsers.add_parser("screen", help="Run local stock-screening strategies")
    screen_parser.add_argument("--symbols", nargs="+", required=True)
    screen_parser.add_argument("--adjust", default="qfq", choices=("", "qfq", "hfq"))

    validate_parser = subparsers.add_parser("validate", help="Validate one cached daily-bar dataset")
    validate_parser.add_argument("--symbol", required=True)
    validate_parser.add_argument("--adjust", default="qfq", choices=("", "qfq", "hfq"))

    backtest_parser = subparsers.add_parser("backtest", help="Backtest one strategy with cached daily bars")
    backtest_parser.add_argument("--symbol", required=True)
    backtest_parser.add_argument("--strategy", required=True, choices=[strategy.name for strategy in list_strategies])
    backtest_parser.add_argument("--adjust", default="qfq", choices=("", "qfq", "hfq"))

    arguments = parser.parse_args()
    store = DailyBarStore()
    if arguments.command == "sync":
        provider = AKShareProvider()
        for symbol in arguments.symbols:
            result = store.sync_symbol(provider, symbol, arguments.adjust)
            print(f"{result.symbol}: {result.row_count} cached rows, {result.fetched_rows} fetched rows")
    elif arguments.command == "screen":
        result = ScreeningService(store).run(arguments.symbols, list_strategies, arguments.adjust)
        for strategy_name, symbols in result.selected_symbols.items():
            print(f"{strategy_name}: {', '.join(symbols) or 'no matches'}")
        for symbol, reason in result.rejected_symbols.items():
            print(f"{symbol}: rejected because {reason}")
    elif arguments.command == "validate":
        report = DailyBarValidator().validate(store.read_bars(arguments.symbol, arguments.adjust))
        print(f"valid={report.is_valid}, rows={report.row_count}")
        for issue in report.issues:
            print(f"{issue.severity}: {issue.code}: {issue.message}")
    else:
        strategy = next(strategy for strategy in list_strategies if strategy.name == arguments.strategy)
        result = StrategyBacktestService(store).run(arguments.symbol, strategy, arguments.adjust)
        print(f"strategy={strategy.name}, total_return={result.total_return:.2%}, max_drawdown={result.max_drawdown:.2%}")


if __name__ == "__main__":
    main()
