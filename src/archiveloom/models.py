from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Protocol(StrEnum):
    DIRECT = "direct"
    HLS = "hls"
    DASH = "dash"


class ItemStatus(StrEnum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class MediaItem:
    stable_id: str
    title: str
    media_url: str
    protocol: Protocol
    filename: str
    source_url: str
    duration_seconds: float | None = None
    headers: dict[str, str] = field(default_factory=dict)
    dimensions: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProgressSnapshot:
    item_id: str
    completed: int = 0
    total: int | None = None
    media_seconds: float = 0.0
    speed: float | None = None
    status: ItemStatus = ItemStatus.QUEUED
    message: str = ""


@dataclass(frozen=True, slots=True)
class DownloadResult:
    item_id: str
    status: ItemStatus
    path: Path | None = None
    size_bytes: int = 0
    duration_seconds: float | None = None
    message: str = ""
