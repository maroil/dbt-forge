"""LLM provider abstraction for doc generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GeneratedDescription:
    """Result of LLM description generation."""

    model_name: str
    model_description: str = ""
    column_descriptions: dict[str, str] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate_descriptions(
        self,
        model_name: str,
        sql: str,
        columns: list[str],
        existing_descriptions: dict[str, str] | None = None,
    ) -> GeneratedDescription:
        """Generate descriptions for a model and its columns."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Return provider display name."""
        ...
