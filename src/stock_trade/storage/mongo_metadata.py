"""MongoDB storage for non-K-line market data."""

import os
from typing import Any

from pymongo import ASCENDING, MongoClient


class MongoMetadataStore:
    """Lazily connect to MongoDB for source-specific metadata documents."""

    def __init__(self, uri: str | None = None, database_name: str = "stock_trade") -> None:
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database_name
        self._client: MongoClient[dict[str, Any]] | None = None

    @property
    def database(self) -> Any:
        if self._client is None:
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=3_000)
        return self._client[self.database_name]

    def ensure_indexes(self) -> None:
        self.database["security_master"].create_index([("symbol", ASCENDING)], unique=True)
        self.database["financial_statements"].create_index(
            [("symbol", ASCENDING), ("report_date", ASCENDING), ("statement_type", ASCENDING)],
            unique=True,
        )
        self.database["sector_memberships"].create_index(
            [("symbol", ASCENDING), ("sector", ASCENDING), ("effective_date", ASCENDING)],
            unique=True,
        )

    def upsert_security(self, security: dict[str, Any]) -> None:
        symbol = str(security["symbol"]).zfill(6)
        self.database["security_master"].update_one(
            {"symbol": symbol},
            {"$set": {**security, "symbol": symbol}},
            upsert=True,
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
