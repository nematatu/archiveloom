from __future__ import annotations

from importlib.metadata import entry_points

from archiveloom.adapters.base import Adapter, AdapterError
from archiveloom.adapters.direct import DirectAdapter
from archiveloom.adapters.manifest import ManifestAdapter
from archiveloom.core.redaction import redact_url


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, Adapter] = {}
        self.register(ManifestAdapter())
        self.register(DirectAdapter())
        self._load_plugins()

    def register(self, adapter: Adapter) -> None:
        self._adapters[adapter.name] = adapter

    def all(self) -> list[Adapter]:
        return sorted(self._adapters.values(), key=lambda adapter: adapter.name)

    def get(self, name: str) -> Adapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise AdapterError(f"Unknown adapter: {name}") from exc

    def resolve(self, source: str, preferred: str | None = None) -> Adapter:
        if preferred:
            adapter = self.get(preferred)
            if not adapter.can_handle(source):
                raise AdapterError(f"Adapter '{preferred}' cannot handle this source.")
            return adapter
        for adapter in self.all():
            if adapter.can_handle(source):
                return adapter
        raise AdapterError(f"No installed adapter can handle: {redact_url(source)}")

    def _load_plugins(self) -> None:
        for point in entry_points(group="archiveloom.adapters"):
            if point.name in self._adapters:
                continue
            loaded = point.load()
            adapter = loaded() if isinstance(loaded, type) else loaded
            self.register(adapter)
