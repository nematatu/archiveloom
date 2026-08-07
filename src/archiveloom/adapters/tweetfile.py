from __future__ import annotations

import re
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlsplit

import httpx

from archiveloom.adapters.base import AdapterError
from archiveloom.core.redaction import redact_text
from archiveloom.models import MediaItem, Protocol

SOURCE_HOST = "twimg.tweetfile.com"
API_ORIGIN = "https://rwzugqnp.fun800.click"
API_PREFIX = "/app-api"
MEDIA_HOST = "vid.fun800.click"
PAGE_SIZE = 20
MAX_PAGES = 100
MAX_ITEMS = 2_000
MAX_PLAYLIST_BYTES = 2_000_000
MAX_RETRY_DELAY_SECONDS = 30.0
SHORT_LINK_RE = re.compile(r"[A-Za-z0-9._-]{6,80}")
RESOLUTION_RE = re.compile(r"(?:^|,)RESOLUTION=(\d+)x(\d+)(?:,|$)", re.IGNORECASE)
BANDWIDTH_RE = re.compile(r"(?:^|,)BANDWIDTH=(\d+)(?:,|$)", re.IGNORECASE)
METHOD_RE = re.compile(r"(?:^|,)METHOD=([^,]+)", re.IGNORECASE)


class TweetFileAdapter:
    name = "tweetfile"
    description = "Public twimg.tweetfile.com video collections"

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport
        self._sleep = sleep

    def can_handle(self, source: str) -> bool:
        try:
            self._source_short_link(source)
        except AdapterError:
            return False
        return True

    def discover(self, source: str) -> list[MediaItem]:
        short_link = self._source_short_link(source)
        timeout = httpx.Timeout(connect=15, read=30, write=30, pool=30)
        headers = {
            "Accept": "application/json",
            "User-Agent": "ArchiveLoom/0.1 (+https://github.com/nematatu/archiveloom)",
        }
        with httpx.Client(
            transport=self._transport,
            timeout=timeout,
            headers=headers,
            follow_redirects=False,
        ) as client:
            root = self._get_info(client, short_link)
            summaries = self._discover_summaries(client, short_link, root)
            items = [
                self._resolve_summary(client, summary, position)
                for position, summary in enumerate(summaries, start=1)
            ]
        if not items:
            raise AdapterError("TweetFile discovery returned no downloadable videos.")
        return items

    @staticmethod
    def _source_short_link(source: str) -> str:
        parsed = urlsplit(source)
        try:
            port = parsed.port
        except ValueError as exc:
            raise AdapterError("TweetFile URL contains an invalid port.") from exc
        segments = [segment for segment in parsed.path.split("/") if segment]
        if (
            parsed.scheme.lower() != "https"
            or (parsed.hostname or "").lower() != SOURCE_HOST
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
            or len(segments) != 1
            or not SHORT_LINK_RE.fullmatch(segments[0])
        ):
            raise AdapterError(
                "The TweetFile adapter accepts only https://twimg.tweetfile.com/<short-link>."
            )
        return segments[0]

    def _discover_summaries(
        self,
        client: httpx.Client,
        root_short_link: str,
        root: dict[str, object],
    ) -> list[dict[str, object]]:
        info = self._mapping(root.get("info"), "TweetFile getInfo.info")
        net_disk = self._mapping(info.get("netDiskInfo"), "TweetFile netDiskInfo")
        extra = self._mapping(info.get("extraInfo"), "TweetFile extraInfo")
        is_folder = net_disk.get("isFolder") is True
        channel_short_link = self._safe_short_link(extra.get("externalLinks"))
        collection_short_link = root_short_link if is_folder else channel_short_link
        if collection_short_link:
            sort_order = str(extra.get("sortOrder") or "2")
            if not sort_order.isdigit():
                raise AdapterError("TweetFile sort order has an unexpected format.")
            return self._paginate(client, collection_short_link, sort_order)

        landing_page = self._safe_short_link(net_disk.get("landingPage")) or root_short_link
        stable_id = self._required_text(net_disk.get("id") or net_disk.get("guid"), "video ID")
        return [{"id": stable_id, "landingPage": landing_page, "isFolder": False}]

    def _paginate(
        self,
        client: httpx.Client,
        collection_short_link: str,
        sort_order: str,
    ) -> list[dict[str, object]]:
        summaries: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        expected_total: int | None = None
        for page_number in range(1, MAX_PAGES + 1):
            payload = self._request_data(
                client,
                "/flow/land-page/list_by_links_page",
                params={
                    "externalLinks": collection_short_link,
                    "domain": "tweetfile.com",
                    "pageNo": str(page_number),
                    "pageSize": str(PAGE_SIZE),
                    "sortOrder": sort_order,
                },
            )
            raw_items = payload.get("list")
            total = payload.get("total")
            if not isinstance(raw_items, list) or not isinstance(total, int) or total < 0:
                raise AdapterError("TweetFile list response changed shape.")
            if expected_total is None:
                expected_total = total
                if expected_total == 0:
                    raise AdapterError("TweetFile collection is empty.")
                if expected_total > MAX_ITEMS:
                    raise AdapterError(
                        f"TweetFile collection exceeds the safe limit of {MAX_ITEMS} items."
                    )
            elif total != expected_total:
                raise AdapterError("TweetFile collection total changed during pagination.")
            if not raw_items and len(summaries) < expected_total:
                raise AdapterError("TweetFile pagination ended before the reported total.")
            for raw in raw_items:
                summary = self._mapping(raw, "TweetFile list item")
                if summary.get("isFolder") is True:
                    raise AdapterError("Nested TweetFile folders are not supported.")
                stable_id = self._required_text(summary.get("id"), "list item ID")
                self._safe_short_link(summary.get("landingPage"), required=True)
                if stable_id in seen_ids:
                    raise AdapterError(f"TweetFile returned duplicate stable ID: {stable_id}")
                seen_ids.add(stable_id)
                summaries.append(summary)
            if len(summaries) >= expected_total:
                break
        if expected_total is None or len(summaries) != expected_total:
            raise AdapterError("TweetFile pagination did not reach the reported total safely.")
        return summaries

    def _resolve_summary(
        self,
        client: httpx.Client,
        summary: dict[str, object],
        position: int,
    ) -> MediaItem:
        stable_id = self._required_text(summary.get("id"), "list item ID")
        landing_page = self._safe_short_link(summary.get("landingPage"), required=True)
        payload = self._get_info(client, landing_page)
        info = self._mapping(payload.get("info"), "TweetFile getInfo.info")
        net_disk = self._mapping(info.get("netDiskInfo"), "TweetFile netDiskInfo")
        if net_disk.get("isFolder") is True:
            raise AdapterError("TweetFile list item unexpectedly resolved to a folder.")
        title = self._required_text(net_disk.get("name"), "video title")
        media_url = self._required_text(
            net_disk.get("fileUrl") or net_disk.get("originUrl"), "media URL"
        )
        protocol, resolved_url, resolution = self._resolve_media(client, media_url)
        duration = self._positive_float(net_disk.get("length"), "video duration")
        expected_size = self._positive_int(net_disk.get("fileSize"), "video size", required=False)
        filename = f"tweetfile_{stable_id}.mp4"
        metadata: dict[str, object] = {"original_name": title}
        if expected_size is not None:
            metadata["expected_size_bytes"] = expected_size
        if resolution:
            metadata["selected_resolution"] = resolution
        return MediaItem(
            stable_id=f"tweetfile:{stable_id}",
            title=title,
            media_url=resolved_url,
            protocol=protocol,
            filename=filename,
            source_url=f"https://{SOURCE_HOST}/{landing_page}",
            duration_seconds=duration,
            dimensions={"position": f"{position:03d}"},
            metadata=metadata,
        )

    def _get_info(self, client: httpx.Client, short_link: str) -> dict[str, object]:
        payload = self._request_data(
            client,
            "/flow/land-page/getInfo",
            params={"externalLinks": short_link, "domain": "tweetfile.com"},
        )
        rules = self._mapping(payload.get("rules"), "TweetFile rules")
        status = str(rules.get("status") or "0")
        if status in {"4", "5"}:
            raise AdapterError("TweetFile link is password protected; bypass is unsupported.")
        status_messages = {"1": "unavailable", "2": "not found", "3": "expired"}
        if status in status_messages:
            raise AdapterError(f"TweetFile link is {status_messages[status]}.")
        if status != "0":
            raise AdapterError("TweetFile returned an unknown access status.")
        return payload

    def _request_data(
        self,
        client: httpx.Client,
        path: str,
        *,
        params: dict[str, str],
    ) -> dict[str, object]:
        response = self._request(client, f"{API_PREFIX}{path}", params=params)
        try:
            payload = response.json()
        except ValueError as exc:
            raise AdapterError("TweetFile API returned malformed JSON.") from exc
        if not isinstance(payload, dict) or payload.get("code") != 0:
            raise AdapterError("TweetFile API returned an unsuccessful response.")
        return self._mapping(payload.get("data"), "TweetFile API data")

    def _request(
        self,
        client: httpx.Client,
        path_or_url: str,
        *,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        url = (
            urljoin(f"{API_ORIGIN}/", path_or_url.lstrip("/"))
            if path_or_url.startswith("/")
            else path_or_url
        )
        last_error = "request failed"
        for attempt in range(1, 4):
            try:
                response = client.get(url, params=params)
                if 300 <= response.status_code < 400:
                    raise AdapterError("TweetFile unexpectedly redirected a discovery request.")
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = f"HTTP {response.status_code}"
                    if attempt < 3:
                        self._sleep(self._retry_delay(response, attempt))
                        continue
                response.raise_for_status()
                return response
            except AdapterError:
                raise
            except httpx.HTTPError as exc:
                last_error = redact_text(str(exc))
                if attempt < 3:
                    self._sleep(min(float(attempt), MAX_RETRY_DELAY_SECONDS))
                    continue
        raise AdapterError(f"TweetFile request failed after bounded retries: {last_error}")

    def _resolve_media(self, client: httpx.Client, media_url: str) -> tuple[Protocol, str, str]:
        self._validate_media_url(media_url)
        suffix = PurePosixPath(urlsplit(media_url).path).suffix.lower()
        if suffix == ".m3u8":
            selected_url, resolution = self._select_hls(client, media_url, depth=0, seen=set())
            return Protocol.HLS, selected_url, resolution
        if suffix == ".mpd":
            raise AdapterError("TweetFile DASH streams are not yet verified and are unsupported.")
        if suffix in {".mp4", ".mov", ".webm"}:
            return Protocol.DIRECT, media_url, ""
        raise AdapterError("TweetFile returned an unsupported media URL type.")

    def _select_hls(
        self,
        client: httpx.Client,
        playlist_url: str,
        *,
        depth: int,
        seen: set[str],
    ) -> tuple[str, str]:
        if depth > 3 or playlist_url in seen:
            raise AdapterError("TweetFile HLS playlist nesting is unsafe.")
        seen.add(playlist_url)
        response = self._request(client, playlist_url)
        if len(response.content) > MAX_PLAYLIST_BYTES:
            raise AdapterError("TweetFile HLS playlist exceeds the safe size limit.")
        text = response.text.lstrip("\ufeff")
        if not text.startswith("#EXTM3U"):
            raise AdapterError("TweetFile returned a malformed HLS playlist.")
        self._reject_encrypted_hls(text)
        variants = self._hls_variants(playlist_url, text)
        if not variants:
            if "#EXTINF:" not in text:
                raise AdapterError("TweetFile HLS playlist contains no playable segments.")
            return playlist_url, ""
        _, selected_url, resolution = max(variants, key=lambda entry: entry[0])
        nested_url, nested_resolution = self._select_hls(
            client, selected_url, depth=depth + 1, seen=seen
        )
        return nested_url, nested_resolution or resolution

    def _hls_variants(self, playlist_url: str, text: str) -> list[tuple[tuple[int, int], str, str]]:
        lines = [line.strip() for line in text.splitlines()]
        variants: list[tuple[tuple[int, int], str, str]] = []
        for index, line in enumerate(lines):
            if not line.startswith("#EXT-X-STREAM-INF:"):
                continue
            target = next(
                (
                    candidate
                    for candidate in lines[index + 1 :]
                    if candidate and not candidate.startswith("#")
                ),
                "",
            )
            if not target:
                raise AdapterError("TweetFile HLS variant has no URI.")
            resolved = urljoin(playlist_url, target)
            self._validate_media_url(resolved)
            attributes = line.partition(":")[2]
            resolution_match = RESOLUTION_RE.search(attributes)
            bandwidth_match = BANDWIDTH_RE.search(attributes)
            width = int(resolution_match.group(1)) if resolution_match else 0
            height = int(resolution_match.group(2)) if resolution_match else 0
            bandwidth = int(bandwidth_match.group(1)) if bandwidth_match else 0
            label = f"{width}x{height}" if width and height else ""
            variants.append(((width * height, bandwidth), resolved, label))
        return variants

    @staticmethod
    def _reject_encrypted_hls(text: str) -> None:
        for line in text.splitlines():
            if not line.startswith(("#EXT-X-KEY:", "#EXT-X-SESSION-KEY:")):
                continue
            method_match = METHOD_RE.search(line.partition(":")[2])
            method = method_match.group(1).strip().upper() if method_match else "UNKNOWN"
            if method != "NONE":
                raise AdapterError(
                    f"TweetFile HLS encryption/DRM method '{method}' is unsupported."
                )

    @staticmethod
    def _validate_media_url(value: str) -> None:
        parsed = urlsplit(value)
        try:
            port = parsed.port
        except ValueError as exc:
            raise AdapterError("TweetFile media URL contains an invalid port.") from exc
        if (
            parsed.scheme.lower() != "https"
            or (parsed.hostname or "").lower() != MEDIA_HOST
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
            or parsed.fragment
        ):
            raise AdapterError("TweetFile returned a media URL outside the verified CDN scope.")

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
    def _required_text(value: object, label: str) -> str:
        text = str(value).strip() if value is not None else ""
        if not text or len(text) > 500:
            raise AdapterError(f"TweetFile {label} is missing or invalid.")
        return text

    @staticmethod
    def _safe_short_link(value: object, *, required: bool = False) -> str:
        text = str(value).strip() if value is not None else ""
        if text and SHORT_LINK_RE.fullmatch(text):
            return text
        if required:
            raise AdapterError("TweetFile short link is missing or invalid.")
        return ""

    @staticmethod
    def _positive_float(value: object, label: str) -> float:
        try:
            result = float(str(value))
        except (TypeError, ValueError) as exc:
            raise AdapterError(f"TweetFile {label} is missing or invalid.") from exc
        if result <= 0:
            raise AdapterError(f"TweetFile {label} must be positive.")
        return result

    @staticmethod
    def _positive_int(value: object, label: str, *, required: bool) -> int | None:
        if value is None and not required:
            return None
        try:
            result = int(str(value))
        except (TypeError, ValueError) as exc:
            raise AdapterError(f"TweetFile {label} is invalid.") from exc
        if result <= 0:
            raise AdapterError(f"TweetFile {label} must be positive.")
        return result
