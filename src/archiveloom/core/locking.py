from __future__ import annotations

import json
import os
import platform
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from filelock import FileLock, Timeout

from archiveloom.core.paths import ensure_metadata_dir


class AlreadyRunningError(RuntimeError):
    pass


class RunLock:
    def __init__(self, output_root: Path) -> None:
        meta = output_root / ".archiveloom"
        self._lock = FileLock(meta / "run.lock", timeout=0)
        self._metadata = meta / "run.json"
        self._run_id = str(uuid.uuid4())

    def __enter__(self) -> RunLock:
        ensure_metadata_dir(self._metadata.parent.parent)
        try:
            self._lock.acquire()
        except Timeout as exc:
            detail = ""
            with suppress(OSError):
                detail = self._metadata.read_text(encoding="utf-8").strip()
            raise AlreadyRunningError(
                f"Another ArchiveLoom process is using this output directory. {detail}"
            ) from exc
        payload = {
            "schema_version": 1,
            "run_id": self._run_id,
            "pid": os.getpid(),
            "host": platform.node(),
            "started_at": datetime.now(UTC).isoformat(),
        }
        self._metadata.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            current = json.loads(self._metadata.read_text(encoding="utf-8"))
            if current.get("run_id") == self._run_id:
                self._metadata.unlink(missing_ok=True)
        except (OSError, json.JSONDecodeError):
            pass
        self._lock.release()
