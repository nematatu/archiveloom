from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from archiveloom.adapters.base import AdapterError
from archiveloom.core.filenames import safe_filename
from archiveloom.models import MediaItem, Protocol


class ManifestAdapter:
    name = "manifest"
    description = "Local ArchiveLoom JSON collection manifests"

    def can_handle(self, source: str) -> bool:
        return source.lower().endswith((".json", ".archiveloom")) and Path(source).is_file()

    def discover(self, source: str) -> list[MediaItem]:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise AdapterError(f"Manifest does not exist: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AdapterError(f"Cannot read manifest: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise AdapterError("Manifest must be an object with version: 1.")
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise AdapterError("Manifest items must be a list.")
        return [self._parse_item(raw, index, path) for index, raw in enumerate(raw_items)]

    def _parse_item(self, raw: Any, index: int, path: Path) -> MediaItem:
        if not isinstance(raw, dict):
            raise AdapterError(f"Manifest item {index + 1} must be an object.")
        url = raw.get("url")
        title = raw.get("title")
        if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"}:
            raise AdapterError(f"Manifest item {index + 1} has an unsafe or missing URL.")
        if not isinstance(title, str) or not title.strip():
            raise AdapterError(f"Manifest item {index + 1} has no title.")
        protocol_raw = str(raw.get("protocol", "direct")).lower()
        try:
            protocol = Protocol(protocol_raw)
        except ValueError as exc:
            raise AdapterError(
                f"Manifest item {index + 1} has unknown protocol: {protocol_raw}"
            ) from exc
        raw_id = raw.get("id")
        stable_id = str(raw_id) if raw_id else hashlib.sha256(url.encode()).hexdigest()[:20]
        extension = (
            ".mp4"
            if protocol in {Protocol.HLS, Protocol.DASH}
            else Path(urlsplit(url).path).suffix or ".bin"
        )
        filename = raw.get("filename") or f"{title}{extension}"
        headers = self._headers(raw.get("headers", {}), index)
        dimensions = raw.get("dimensions", {})
        if not isinstance(dimensions, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in dimensions.items()
        ):
            raise AdapterError(f"Manifest item {index + 1} dimensions must be string pairs.")
        duration = raw.get("duration_seconds")
        if duration is not None and not isinstance(duration, (int, float)):
            raise AdapterError(f"Manifest item {index + 1} duration must be numeric.")
        return MediaItem(
            stable_id=stable_id,
            title=title.strip(),
            media_url=url,
            protocol=protocol,
            filename=safe_filename(str(filename)),
            source_url=str(path),
            duration_seconds=float(duration) if duration is not None else None,
            headers=headers,
            dimensions=dict(dimensions),
        )

    @staticmethod
    def _headers(raw: Any, index: int) -> dict[str, str]:
        if not isinstance(raw, dict):
            raise AdapterError(f"Manifest item {index + 1} headers must be an object.")
        headers: dict[str, str] = {}
        for key, value in raw.items():
            if (
                not isinstance(key, str)
                or not isinstance(value, str)
                or "\n" in key + value
                or "\r" in key + value
            ):
                raise AdapterError(f"Manifest item {index + 1} contains an unsafe header.")
            headers[key] = value
        return headers
