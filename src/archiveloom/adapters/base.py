from __future__ import annotations

from typing import Protocol

from archiveloom.models import MediaItem


class AdapterError(RuntimeError):
    """A source cannot be safely discovered by an adapter."""


class Adapter(Protocol):
    name: str
    description: str

    def can_handle(self, source: str) -> bool: ...

    def discover(self, source: str) -> list[MediaItem]: ...
