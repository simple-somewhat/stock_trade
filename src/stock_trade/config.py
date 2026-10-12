"""Application paths and runtime configuration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Locations used by local market-data storage."""

    project_root: Path

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> "Settings":
        root = project_root or Path(__file__).resolve().parents[2]
        return cls(project_root=root)

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def daily_bars_dir(self) -> Path:
        return self.data_dir / "parquet" / "daily_bars"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "market.duckdb"

    def ensure_directories(self) -> None:
        self.daily_bars_dir.mkdir(parents=True, exist_ok=True)
