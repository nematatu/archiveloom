from __future__ import annotations

import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from archiveloom.adapters.registry import AdapterRegistry
from archiveloom.core.storage import inspect_storage


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


def run_doctor(output: Path | None = None, *, external_only: bool = False) -> list[DoctorCheck]:
    checks = [
        DoctorCheck(
            "Operating system",
            "OK",
            f"{platform.system()} {platform.release()} ({platform.machine()})",
        ),
        DoctorCheck(
            "Python", "OK" if sys.version_info >= (3, 11) else "ERROR", platform.python_version()
        ),
        _tool_check("ffmpeg"),
        _tool_check("ffprobe"),
        DoctorCheck(
            "Adapters", "OK", ", ".join(adapter.name for adapter in AdapterRegistry().all())
        ),
    ]
    if output is not None:
        report = inspect_storage(output)
        status = (
            "OK" if report.writable and (not external_only or report.external is True) else "ERROR"
        )
        free = (
            f"{report.free_bytes / 1_000_000_000:.1f} GB free"
            if report.free_bytes is not None
            else "free space unknown"
        )
        checks.append(DoctorCheck("Storage", status, f"{report.path}; {free}; {report.detail}"))
    return checks


def _tool_check(name: str) -> DoctorCheck:
    path = shutil.which(name)
    return DoctorCheck(name, "OK" if path else "ERROR", path or "not found")
