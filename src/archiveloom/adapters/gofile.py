from __future__ import annotations

import json
import os
import re
import time
from collections import deque
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import httpx

from archiveloom.adapters.base import AdapterError
from archiveloom.core.filenames import safe_filename
from archiveloom.core.redaction import redact_text
from archiveloom.models import MediaItem, Protocol

SOURCE_HOSTS = {"gofile.io", "www.gofile.io"}
API_ORIGIN = "https://api.gofile.io"
TOKEN_ENV = "ARCHIVELOOM_GOFILE_TOKEN"  # noqa: S105 - this is an environment variable name
PAGE_SIZE = 1_000
MAX_PAGES_PER_FOLDER = 100
MAX_FOLDERS = 1_000
MAX_ITEMS = 10_000
MAX_DEPTH = 32
MAX_RESPONSE_BYTES = 20_000_000
MAX_RETRY_DELAY_SECONDS = 30.0
CONTENT_ID_RE = re.compile(r"[A-Za-z0-9_-]{6,128}")
MEDIA_SUFFIXES = {
    ".3gp",
    ".aac",
    ".avi",
    ".flac",
    ".m2ts",
    ".m4a",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".ogg",
    ".opus",
    ".ts",
    ".wav",
    ".webm",
}


class GofileAdapter:
    name = "gofile"
    description = "Authorized Gofile folders through the official token-authenticated API"

    def __init__(
        self,
        *,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token = token
        self._transport = transport
        self._sleep = sleep

    def can_handle(self, source: str) -> bool:
        try:
            self._source_content_id(source)
        except AdapterError:
            return False
        return True

    def discover(self, source: str) -> list[MediaItem]:
        root_id = self._source_content_id(source)
        canonical_source = f"https://gofile.io/d/{root_id}"
        token = self._validated_token(self._token or os.environ.get(TOKEN_ENV, ""))
        timeout = httpx.Timeout(connect=15, read=30, write=30, pool=30)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "ArchiveLoom/0.1 (+https://github.com/nematatu/archiveloom)",
        }
        with httpx.Client(
            transport=self._transport,
            timeout=timeout,
            headers=headers,
            follow_redirects=False,
        ) as client:
            items = self._walk_folders(client, root_id, token, canonical_source)
        if not items:
            raise AdapterError("Gofile folder contains no supported video or audio files.")
        return items

    @staticmethod
    def _source_content_id(source: str) -> str:
        parsed = urlsplit(source)
        try:
            port = parsed.port
        except ValueError as exc:
            raise AdapterError("Gofile URL contains an invalid port.") from exc
        segments = [segment for segment in parsed.path.split("/") if segment]
        if (
            parsed.scheme.lower() != "https"
            or (parsed.hostname or "").lower() not in SOURCE_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
            or len(segments) != 2
            or segments[0] != "d"
            or not CONTENT_ID_RE.fullmatch(segments[1])
        ):
            raise AdapterError("The Gofile adapter accepts only https://gofile.io/d/<content-id>.")
        return segments[1]

    @staticmethod
    def _validated_token(value: str) -> str:
        token = value.strip()
        if not token:
            raise AdapterError(
                f"Gofile requires an official API token. Set {TOKEN_ENV} from your Gofile "
                "profile, then retry."
            )
        if (
            len(token) > 512
            or not token.isascii()
            or any(character.isspace() or character in ";," for character in token)
        ):
            raise AdapterError(f"{TOKEN_ENV} is malformed.")
        return token

    def _walk_folders(
        self,
        client: httpx.Client,
        root_id: str,
        token: str,
        source: str,
    ) -> list[MediaItem]:
        queue: deque[tuple[str, tuple[str, ...], int]] = deque([(root_id, (), 0)])
        seen_folders: set[str] = set()
        seen_contents: set[str] = set()
        items: list[MediaItem] = []
        while queue:
            folder_id, parent_path, depth = queue.popleft()
            if depth > MAX_DEPTH:
                raise AdapterError(f"Gofile folder nesting exceeds the safe depth of {MAX_DEPTH}.")
            if folder_id in seen_folders:
                raise AdapterError(f"Gofile returned a duplicate or cyclic folder ID: {folder_id}")
            seen_folders.add(folder_id)
            if len(seen_folders) > MAX_FOLDERS:
                raise AdapterError(f"Gofile share exceeds the safe limit of {MAX_FOLDERS} folders.")
            folder_name, children = self._fetch_folder(client, folder_id)
            folder_path = parent_path + ((folder_name,) if folder_name else ())
            for child in children:
                child_id = self._required_id(child.get("id"), "child ID")
                if child_id in seen_contents:
                    raise AdapterError(f"Gofile returned duplicate content ID: {child_id}")
                seen_contents.add(child_id)
                if len(seen_contents) > MAX_ITEMS:
                    raise AdapterError(f"Gofile share exceeds the safe limit of {MAX_ITEMS} items.")
                child_type = self._required_text(child.get("type"), "content type", limit=32)
                if child_type == "folder":
                    queue.append((child_id, folder_path, depth + 1))
                    continue
                if child_type != "file":
                    raise AdapterError("Gofile returned an unknown content type.")
                item = self._media_item(child, token, source, folder_path, len(items) + 1)
                if item is not None:
                    items.append(item)
        return items

    def _fetch_folder(
        self,
        client: httpx.Client,
        folder_id: str,
    ) -> tuple[str, list[dict[str, object]]]:
        children: list[dict[str, object]] = []
        page_ids: set[str] = set()
        expected_count: int | None = None
        folder_name = ""
        resolved_folder_id = ""
        for page in range(1, MAX_PAGES_PER_FOLDER + 1):
            data = self._request_data(
                client,
                folder_id,
                params={
                    "page": str(page),
                    "pageSize": str(PAGE_SIZE),
                    "sortField": "createTime",
                    "sortDirection": "1",
                    "contentFilter": "",
                },
            )
            if self._required_text(data.get("type"), "root content type", limit=32) != "folder":
                raise AdapterError("Gofile content URL did not resolve to a folder.")
            current_id = self._required_id(data.get("id"), "resolved folder ID")
            if resolved_folder_id and current_id != resolved_folder_id:
                raise AdapterError("Gofile folder identity changed during pagination.")
            resolved_folder_id = current_id
            current_name = self._required_text(data.get("name"), "folder name")
            if folder_name and current_name != folder_name:
                raise AdapterError("Gofile folder name changed during pagination.")
            folder_name = current_name
            count = data.get("childrenCount")
            if count is not None:
                if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                    raise AdapterError("Gofile children count changed shape.")
                if expected_count is not None and count != expected_count:
                    raise AdapterError("Gofile children count changed during pagination.")
                expected_count = count
                if expected_count > MAX_ITEMS:
                    raise AdapterError(
                        f"Gofile folder exceeds the safe limit of {MAX_ITEMS} children."
                    )
            raw_children = data.get("children")
            if not isinstance(raw_children, dict) or not all(
                isinstance(key, str) for key in raw_children
            ):
                raise AdapterError("Gofile children response changed shape.")
            page_children = [self._mapping(raw, "Gofile child") for raw in raw_children.values()]
            for child in page_children:
                child_id = self._required_id(child.get("id"), "child ID")
                if child_id in page_ids:
                    raise AdapterError("Gofile pagination returned duplicate children.")
                page_ids.add(child_id)
                children.append(child)
                if len(children) > MAX_ITEMS:
                    raise AdapterError(
                        f"Gofile folder exceeds the safe limit of {MAX_ITEMS} children."
                    )
            if expected_count is not None:
                if len(children) > expected_count:
                    raise AdapterError("Gofile pagination exceeded its reported child count.")
                if len(children) == expected_count:
                    return folder_name, children
                if not page_children:
                    raise AdapterError("Gofile pagination ended before its reported child count.")
            elif len(page_children) < PAGE_SIZE:
                return folder_name, children
        raise AdapterError("Gofile pagination exceeded the safe page limit.")

    def _request_data(
        self,
        client: httpx.Client,
        folder_id: str,
        *,
        params: dict[str, str],
    ) -> dict[str, object]:
        response_body = self._request(client, f"{API_ORIGIN}/contents/{folder_id}", params=params)
        try:
            payload = json.loads(response_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError("Gofile API returned malformed JSON.") from exc
        if not isinstance(payload, dict):
            raise AdapterError("Gofile API response changed shape.")
        status = payload.get("status")
        if status != "ok":
            messages = {
                "error-notFound": "Gofile content was not found or has expired.",
                "error-notPremium": (
                    "Gofile requires a Premium/API-enabled account for this request."
                ),
                "error-passwordRequired": (
                    "Password-protected Gofile folders are not yet supported."
                ),
                "error-passwordWrong": "The Gofile folder password was rejected.",
                "error-notPublic": "The Gofile folder is private or unavailable to this token.",
                "error-rateLimit": "Gofile rate limit was reached; retry later.",
            }
            message = messages.get(str(status), "Gofile API returned an unsuccessful status.")
            raise AdapterError(message)
        data = self._mapping(payload.get("data"), "Gofile API data")
        if data.get("canAccess") is False:
            raise AdapterError("Gofile content is not accessible to this API token.")
        if data.get("password") is True and data.get("passwordStatus") != "passwordOk":
            raise AdapterError("Password-protected Gofile folders are not yet supported.")
        return data

    def _request(
        self,
        client: httpx.Client,
        url: str,
        *,
        params: dict[str, str],
    ) -> bytes:
        last_error = "request failed"
        for attempt in range(1, 4):
            try:
                retry_delay: float | None = None
                with client.stream("GET", url, params=params) as response:
                    if 300 <= response.status_code < 400:
                        raise AdapterError("Gofile unexpectedly redirected an API request.")
                    if response.status_code == 429 or response.status_code >= 500:
                        last_error = f"HTTP {response.status_code}"
                        if attempt < 3:
                            retry_delay = self._retry_delay(response, attempt)
                        else:
                            response.raise_for_status()
                    elif response.status_code in {401, 403}:
                        raise AdapterError("Gofile API token is invalid or lacks access.")
                    elif 400 <= response.status_code < 500:
                        raise AdapterError(
                            f"Gofile API request failed with HTTP {response.status_code}."
                        )
                    else:
                        response.raise_for_status()
                        body = bytearray()
                        for chunk in response.iter_bytes(64 * 1024):
                            body.extend(chunk)
                            if len(body) > MAX_RESPONSE_BYTES:
                                raise AdapterError(
                                    "Gofile API response exceeds the safe size limit."
                                )
                        return bytes(body)
                if retry_delay is not None:
                    self._sleep(retry_delay)
                    continue
            except AdapterError:
                raise
            except httpx.HTTPError as exc:
                last_error = redact_text(str(exc))
                if attempt < 3:
                    self._sleep(min(float(attempt), MAX_RETRY_DELAY_SECONDS))
                    continue
        raise AdapterError(f"Gofile request failed after bounded retries: {last_error}")

    def _media_item(
        self,
        raw: dict[str, object],
        token: str,
        source: str,
        folder_path: tuple[str, ...],
        position: int,
    ) -> MediaItem | None:
        media_id = self._required_id(raw.get("id"), "file ID")
        name = self._required_text(raw.get("name"), "file name")
        mimetype = self._required_text(raw.get("mimetype"), "MIME type", limit=200).lower()
        suffix = PurePosixPath(name).suffix.lower()
        if not (
            mimetype.startswith(("video/", "audio/"))
            or mimetype == "application/vnd.mts"
            or suffix in MEDIA_SUFFIXES
        ):
            return None
        if raw.get("isFrozen") is True:
            raise AdapterError("Gofile file is in cold storage and cannot be downloaded directly.")
        if raw.get("overloaded") is True:
            raise AdapterError("Gofile file is temporarily unavailable because its server is busy.")
        if raw.get("isDeleted") is True:
            raise AdapterError("Gofile returned a deleted file in the folder listing.")
        link = self._required_text(raw.get("link"), "download link", limit=4_000)
        self._validate_download_url(link)
        path = Path(name)
        output_suffix = (
            path.suffix
            if path.suffix.lower() in MEDIA_SUFFIXES and len(path.suffix) <= 16
            else ".media"
        )
        unique_filename = safe_filename(f"gofile_{media_id}__{path.stem}{output_suffix}")
        metadata: dict[str, object] = {
            "original_name": name,
            "gofile_folder": "/".join(folder_path),
            "download_url_scope": {
                "scheme": "https",
                "host_suffix": "gofile.io",
                "path_prefix": "/download/",
            },
        }
        size = raw.get("size")
        if size is not None:
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                raise AdapterError("Gofile file size is invalid.")
            metadata["expected_size_bytes"] = size
        created = raw.get("createTime")
        if created is not None:
            if not isinstance(created, int) or isinstance(created, bool) or created < 0:
                raise AdapterError("Gofile creation time is invalid.")
            metadata["created_at"] = created
        return MediaItem(
            stable_id=f"gofile:{media_id}",
            title=name,
            media_url=link,
            protocol=Protocol.DIRECT,
            filename=unique_filename,
            source_url=source,
            headers={
                "Cookie": f"accountToken={token}",
                "Referer": "https://gofile.io/",
            },
            dimensions={
                "folder": "/".join(folder_path),
                "position": f"{position:04d}",
            },
            metadata=metadata,
        )

    @staticmethod
    def _validate_download_url(value: str) -> None:
        parsed = urlsplit(value)
        try:
            port = parsed.port
        except ValueError as exc:
            raise AdapterError("Gofile download URL contains an invalid port.") from exc
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme.lower() != "https"
            or not (host == "gofile.io" or host.endswith(".gofile.io"))
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
            or not parsed.path.startswith("/download/")
            or parsed.fragment
        ):
            raise AdapterError("Gofile returned a download URL outside the verified host scope.")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After", "").strip()
        if value:
            try:
                return min(max(float(value), 0.0), MAX_RETRY_DELAY_SECONDS)
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value)
                    delay = retry_at.timestamp() - time.time()
                    return min(max(delay, 0.0), MAX_RETRY_DELAY_SECONDS)
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(float(attempt), MAX_RETRY_DELAY_SECONDS)

    @staticmethod
    def _mapping(value: object, label: str) -> dict[str, object]:
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise AdapterError(f"{label} changed shape.")
        return value

    @staticmethod
    def _required_text(value: object, label: str, *, limit: int = 500) -> str:
        text = str(value).strip() if value is not None else ""
        if (
            not text
            or len(text) > limit
            or any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in text)
        ):
            raise AdapterError(f"Gofile {label} is missing or invalid.")
        return text

    @staticmethod
    def _required_id(value: object, label: str) -> str:
        text = str(value).strip() if value is not None else ""
        if not CONTENT_ID_RE.fullmatch(text):
            raise AdapterError(f"Gofile {label} is missing or invalid.")
        return text
