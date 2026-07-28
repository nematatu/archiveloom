from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from archiveloom.core.paths import ensure_metadata_dir
from archiveloom.models import DownloadResult


class StateStore:
    def __init__(self, output_root: Path) -> None:
        self.meta_dir = output_root / ".archiveloom"
        self.path = self.meta_dir / "state.json"
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {"schema_version": 1, "items": {}}

    def initialize(self) -> None:
        ensure_metadata_dir(self.meta_dir.parent)
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(loaded, dict) and loaded.get("schema_version") == 1:
            self._data = loaded

    def item(self, stable_id: str) -> dict[str, Any] | None:
        value = self._data.get("items", {}).get(stable_id)
        return value if isinstance(value, dict) else None

    def record(self, result: DownloadResult) -> None:
        with self._lock:
            self._data.setdefault("items", {})[result.item_id] = {
                "status": result.status.value,
                "path": str(result.path) if result.path else None,
                "size_bytes": result.size_bytes,
                "duration_seconds": result.duration_seconds,
                "message": result.message,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            self._write_atomic()

    def _write_atomic(self) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
