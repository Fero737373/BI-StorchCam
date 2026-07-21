"""Provider contracts shared by state management and future integrations."""

from __future__ import annotations

from typing import Any, Protocol


class Provider(Protocol):
    name: str

    def fetch(self, config: dict[str, Any]) -> Any:
        """Return a serialisable provider snapshot or raise a useful exception."""


class UnsupportedRegionError(RuntimeError):
    """The configured location is outside a provider's declared service region."""
