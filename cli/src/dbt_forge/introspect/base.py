"""Abstract base classes and metadata dataclasses for warehouse introspection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ColumnMetadata:
    name: str
    data_type: str
    is_nullable: bool = True
    comment: str = ""


@dataclass
class TableMetadata:
    schema_name: str
    table_name: str
    table_type: str  # "TABLE" or "VIEW"
    columns: list[ColumnMetadata] = field(default_factory=list)
    row_count: int | None = None
    comment: str = ""


class WarehouseIntrospector(ABC):
    """Abstract interface for warehouse introspection."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def list_schemas(self) -> list[str]: ...

    @abstractmethod
    def list_tables(self, schema: str) -> list[TableMetadata]: ...

    @abstractmethod
    def get_columns(self, schema: str, table: str) -> list[ColumnMetadata]: ...

    @abstractmethod
    def close(self) -> None: ...

    def get_query_stats(self, days: int = 30) -> list | None:
        """Get query statistics. Override in adapters that support it."""
        return None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
