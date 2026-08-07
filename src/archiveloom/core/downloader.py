from __future__ import annotations

import hashlib
import os
import queue
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TextIO
from urllib.parse import urlsplit

import httpx

from archiveloom.core.filenames import safe_child
from archiveloom.core.locking import RunLock
from archiveloom.core.paths import ensure_metadata_dir
from archiveloom.core.probe import probe_media
from archiveloom.core.progress import ProgressBoard
from archiveloom.core.redaction import redact_text
from archiveloom.core.state import StateStore
from archiveloom.core.storage import require_storage
from archiveloom.models import DownloadResult, ItemStatus, MediaItem, Protocol

ProgressCallback = Callable[[str, float, float | None, str], None]
CONTENT_RANGE_RE = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", re.IGNORECASE)


class DownloadEngine:
    def __init__(
        self,
        output: Path,
        *,
        jobs: int = 2,
        external_only: bool = False,
        attempts: int = 2,
        stall_timeout: float = 180,
    ) -> None:
        if jobs < 1 or jobs > 16:
            raise ValueError("jobs must be between 1 and 16")
        self.output = output.expanduser().resolve()
        self.jobs = jobs
        self.external_only = external_only
        self.attempts = attempts
        self.stall_timeout = stall_timeout
        self.cancelled = threading.Event()
        self.state = StateStore(self.output)

    def run(self, items: list[MediaItem], board: ProgressBoard) -> list[DownloadResult]:
        require_storage(self.output, external_only=self.external_only)
        self.output.mkdir(parents=True, exist_ok=True)
        self.state.initialize()
        results: list[DownloadResult] = []
        with RunLock(self.output), ThreadPoolExecutor(max_workers=self.jobs) as pool:
            futures: dict[Future[DownloadResult], MediaItem] = {
                pool.submit(self._run_item, item, board.update): item for item in items
            }
            try:
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = DownloadResult(
                            item.stable_id,
                            ItemStatus.FAILED,
                            message=redact_text(str(exc)),
                        )
                    self.state.record(result)
                    board.finish(item.stable_id, result.status)
                    results.append(result)
            except KeyboardInterrupt:
                self.cancelled.set()
                for future in futures:
                    future.cancel()
                raise
        return results

    def _run_item(self, item: MediaItem, progress: ProgressCallback) -> DownloadResult:
        final_path = safe_child(self.output, item.filename)
        expected_size = _expected_direct_size(item)
        if final_path.exists():
            existing = probe_media(final_path)
            size_matches = expected_size is None or existing.size_bytes == expected_size
            if existing.valid and size_matches:
                return DownloadResult(
                    item.stable_id,
                    ItemStatus.SKIPPED,
                    final_path,
                    existing.size_bytes,
                    existing.duration_seconds,
                    "verified existing file",
                )
            if existing.valid:
                return DownloadResult(
                    item.stable_id,
                    ItemStatus.FAILED,
                    final_path,
                    existing.size_bytes,
                    existing.duration_seconds,
                    "An existing final file has an unexpected size; move or remove it explicitly.",
                )
            return DownloadResult(
                item.stable_id,
                ItemStatus.FAILED,
                final_path,
                existing.size_bytes,
                existing.duration_seconds,
                "An existing final file failed verification; move or remove it explicitly.",
            )
        partial_dir = ensure_metadata_dir(self.output) / "partial"
        partial_dir.mkdir(parents=True, exist_ok=True)
        partial_key = hashlib.sha256(item.stable_id.encode("utf-8")).hexdigest()
        part_path = partial_dir / f"{partial_key}.part{final_path.suffix}"
        last_error = "unknown failure"
        for attempt in range(1, self.attempts + 1):
            if self.cancelled.is_set():
                return DownloadResult(item.stable_id, ItemStatus.CANCELLED, message="cancelled")
            try:
                complete_partial = (
                    expected_size is not None
                    and part_path.is_file()
                    and part_path.stat().st_size == expected_size
                )
                if item.protocol is Protocol.DIRECT and not complete_partial:
                    self._download_direct(item, part_path, progress)
                elif item.protocol is not Protocol.DIRECT:
                    self._download_ffmpeg(item, part_path, progress)
                if expected_size is not None and part_path.stat().st_size != expected_size:
                    raise RuntimeError(
                        "download size mismatch: "
                        f"expected {expected_size} bytes, got {part_path.stat().st_size}"
                    )
                progress(item.stable_id, 0, None, "verifying")
                verified = probe_media(part_path)
                if not verified.valid:
                    raise RuntimeError(f"ffprobe verification failed: {verified.message}")
                if item.duration_seconds is not None and verified.duration_seconds is not None:
                    tolerance = max(3.0, item.duration_seconds * 0.002)
                    if abs(verified.duration_seconds - item.duration_seconds) > tolerance:
                        raise RuntimeError(
                            "duration mismatch: "
                            f"expected {item.duration_seconds:.3f}s, "
                            f"got {verified.duration_seconds:.3f}s"
                        )
                os.replace(part_path, final_path)
                return DownloadResult(
                    item.stable_id,
                    ItemStatus.COMPLETED,
                    final_path,
                    verified.size_bytes,
                    verified.duration_seconds,
                )
            except Exception as exc:
                last_error = redact_text(str(exc))
                complete_but_invalid = (
                    expected_size is not None
                    and part_path.is_file()
                    and part_path.stat().st_size == expected_size
                )
                if complete_but_invalid:
                    if attempt < self.attempts and not self.cancelled.is_set():
                        part_path.unlink()
                    else:
                        rejected_path = part_path.with_name(
                            f"{part_path.stem}.invalid{part_path.suffix}"
                        )
                        os.replace(part_path, rejected_path)
                if attempt < self.attempts and not self.cancelled.is_set():
                    progress(item.stable_id, 0, None, f"retrying {attempt}/{self.attempts}")
                    time.sleep(min(5 * attempt, 15))
        return DownloadResult(item.stable_id, ItemStatus.FAILED, message=last_error)

    def _download_direct(
        self,
        item: MediaItem,
        part_path: Path,
        progress: ProgressCallback,
    ) -> None:
        offset = part_path.stat().st_size if part_path.exists() else 0
        expected_size = _expected_direct_size(item)
        if expected_size is not None and offset > expected_size:
            offset = 0
        headers = dict(item.headers)
        if offset:
            headers["Range"] = f"bytes={offset}-"
        timeout = httpx.Timeout(connect=15, read=30, write=30, pool=30)
        event_hooks: dict[str, list[Callable[[httpx.Request], None]]] | None = None
        download_scope = item.metadata.get("download_url_scope")
        if isinstance(download_scope, dict):
            event_hooks = {
                "request": [lambda request: _require_download_url_scope(request, download_scope)]
            }
        with (
            httpx.Client(
                follow_redirects=True,
                timeout=timeout,
                event_hooks=event_hooks,
            ) as client,
            client.stream("GET", item.media_url, headers=headers) as response,
        ):
            response.raise_for_status()
            append = offset > 0 and response.status_code == 206
            length_header = response.headers.get("content-length")
            try:
                length = int(length_header) if length_header is not None else None
            except ValueError as exc:
                raise RuntimeError("server returned an invalid Content-Length") from exc
            if length is not None and length < 0:
                raise RuntimeError("server returned an invalid Content-Length")
            range_total: int | None = None
            range_length: int | None = None
            if append:
                content_range = response.headers.get("content-range", "")
                match = CONTENT_RANGE_RE.fullmatch(content_range.strip())
                if match is None:
                    raise RuntimeError("server returned an invalid Content-Range for resume")
                range_start = int(match.group(1))
                range_end = int(match.group(2))
                total_text = match.group(3)
                range_total = int(total_text) if total_text != "*" else None
                range_length = range_end - range_start + 1
                if (
                    range_start != offset
                    or range_end < range_start
                    or (length is not None and range_length != length)
                    or (range_total is not None and range_end >= range_total)
                    or (
                        expected_size is not None
                        and range_total is not None
                        and range_total != expected_size
                    )
                ):
                    raise RuntimeError("server returned an invalid Content-Range for resume")
            completed = offset if append else 0
            total = (
                expected_size or range_total or (completed + length if length is not None else None)
            )
            mode = "ab" if append else "wb"
            with part_path.open(mode) as handle:
                response_start = completed
                for chunk in response.iter_bytes(1024 * 1024):
                    if self.cancelled.is_set():
                        raise RuntimeError("cancelled")
                    handle.write(chunk)
                    completed += len(chunk)
                    progress(item.stable_id, completed, total, "downloading")
                if range_length is not None and completed - response_start != range_length:
                    handle.seek(response_start)
                    handle.truncate()
                    raise RuntimeError("server response length did not match Content-Range")
                handle.flush()
                os.fsync(handle.fileno())

    def _download_ffmpeg(
        self,
        item: MediaItem,
        part_path: Path,
        progress: ProgressCallback,
    ) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is required for HLS and DASH inputs")
        part_path.unlink(missing_ok=True)
        command = [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "warning",
            "-nostats",
            "-progress",
            "pipe:1",
            "-protocol_whitelist",
            "file,http,https,tcp,tls,crypto",
            "-rw_timeout",
            "30000000",
            "-reconnect",
            "1",
            "-reconnect_streamed",
            "1",
            "-reconnect_on_network_error",
            "1",
        ]
        if item.headers:
            command.extend(
                ["-headers", "\r\n".join(f"{key}: {value}" for key, value in item.headers.items())]
            )
        command.extend(
            [
                "-i",
                item.media_url,
                "-map",
                "0:v:0?",
                "-map",
                "0:a:0?",
                "-c",
                "copy",
                "-y",
                str(part_path),
            ]
        )
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if process.stdout is None or process.stderr is None:
            _stop_process(process)
            raise RuntimeError("ffmpeg progress pipes were not created")
        lines: queue.Queue[str | None] = queue.Queue()
        stderr_parts: list[str] = []
        output_reader = threading.Thread(
            target=_read_lines, args=(process.stdout, lines), daemon=True
        )
        error_reader = threading.Thread(
            target=_collect_lines, args=(process.stderr, stderr_parts), daemon=True
        )
        output_reader.start()
        error_reader.start()
        last_progress = time.monotonic()
        media_seconds = 0.0
        try:
            while process.poll() is None or not lines.empty():
                if self.cancelled.is_set():
                    _stop_process(process)
                    raise RuntimeError("cancelled")
                try:
                    line = lines.get(timeout=1)
                except queue.Empty:
                    if time.monotonic() - last_progress > self.stall_timeout:
                        _stop_process(process)
                        raise RuntimeError(
                            f"ffmpeg made no progress for {self.stall_timeout:.0f}s"
                        ) from None
                    continue
                if line is None:
                    continue
                key, _, value = line.strip().partition("=")
                if key in {"out_time_us", "out_time_ms"}:
                    raw = int(value or 0)
                    media_seconds = raw / 1_000_000
                    last_progress = time.monotonic()
                    progress(
                        item.stable_id,
                        media_seconds,
                        item.duration_seconds,
                        "downloading + muxing",
                    )
                elif key == "total_size":
                    last_progress = time.monotonic()
            output_reader.join(timeout=2)
            error_reader.join(timeout=2)
            if process.returncode != 0:
                detail = redact_text("".join(stderr_parts)[-4000:].strip())
                raise RuntimeError(f"ffmpeg failed with code {process.returncode}: {detail}")
        finally:
            if process.poll() is None:
                _stop_process(process)


def _read_lines(stream: TextIO, destination: queue.Queue[str | None]) -> None:
    try:
        for line in stream:
            destination.put(line)
    finally:
        destination.put(None)


def _expected_direct_size(item: MediaItem) -> int | None:
    if item.protocol is not Protocol.DIRECT:
        return None
    value = item.metadata.get("expected_size_bytes")
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _require_download_url_scope(request: httpx.Request, raw_scope: dict[object, object]) -> None:
    scheme = raw_scope.get("scheme")
    host_suffix = raw_scope.get("host_suffix")
    path_prefix = raw_scope.get("path_prefix")
    if (
        not isinstance(scheme, str)
        or not scheme
        or not isinstance(host_suffix, str)
        or not host_suffix
        or not isinstance(path_prefix, str)
        or not path_prefix
    ):
        raise RuntimeError("adapter supplied an invalid download URL scope")
    parsed = urlsplit(str(request.url))
    host = (parsed.hostname or "").lower()
    normalized_suffix = host_suffix.lower()
    if (
        parsed.scheme.lower() != scheme.lower()
        or not (host == normalized_suffix or host.endswith(f".{normalized_suffix}"))
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or not parsed.path.startswith(path_prefix)
    ):
        raise RuntimeError("download redirect left the adapter's verified URL scope")


def _collect_lines(stream: TextIO, destination: list[str]) -> None:
    for line in stream:
        destination.append(line)


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
