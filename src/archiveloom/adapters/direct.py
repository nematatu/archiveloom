from __future__ import annotations

import hashlib
from pathlib import PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from archiveloom.adapters.base import AdapterError
from archiveloom.core.filenames import safe_filename
from archiveloom.models import MediaItem, Protocol

DIRECT_SUFFIXES = {".mp4", ".webm", ".mkv", ".mov", ".mp3", ".m4a", ".flac", ".wav"}


class DirectAdapter:
    name = "direct"
    description = "Direct HTTP(S), HLS (.m3u8), and DASH (.mpd) media URLs"

    def can_handle(self, source: str) -> bool:
        parsed = urlsplit(source)
        if parsed.scheme not in {"http", "https"}:
            return False
        suffix = PurePosixPath(parsed.path).suffix.lower()
        return suffix in DIRECT_SUFFIXES | {".m3u8", ".mpd"}

    def discover(self, source: str) -> list[MediaItem]:
        if not self.can_handle(source):
            raise AdapterError("The direct adapter only accepts known HTTP(S) media URLs.")
        parsed = urlsplit(source)
        normalized = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))
        suffix = PurePosixPath(parsed.path).suffix.lower()
        protocol = (
            Protocol.HLS
            if suffix == ".m3u8"
            else Protocol.DASH
            if suffix == ".mpd"
            else Protocol.DIRECT
        )
        stem = PurePosixPath(parsed.path).stem or "media"
        output_suffix = ".mp4" if protocol in {Protocol.HLS, Protocol.DASH} else suffix
        stable_id = hashlib.sha256(normalized.encode()).hexdigest()[:20]
        return [
            MediaItem(
                stable_id=stable_id,
                title=stem,
                media_url=source,
                protocol=protocol,
                filename=safe_filename(f"{stem}{output_suffix}"),
                source_url=source,
            )
        ]
