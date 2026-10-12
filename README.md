# Stock Trade

基于 AKShare 的 A 股日线缓存与选股工具。

## Storage

- `data/parquet/daily_bars/`: 每个股票一份日线 Parquet 文件，是 K 线数据的持久化载体。
- `data/market.duckdb`: K 线同步状态、策略运行记录与策略信号；DuckDB 直接查询 Parquet。
- MongoDB: 证券基础信息、财务数据、板块关系等非 K 线资料。

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Commands

```powershell
stock-trade sync --symbols 000001 600000
stock-trade screen --symbols 000001 600000
stock-trade validate --symbol 000001
stock-trade backtest --symbol 000001 --strategy StrategySlowRise
```

AKShare 及其上游公开数据仅用于研究和学习；策略输出不构成投资建议。
