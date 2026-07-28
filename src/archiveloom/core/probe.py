from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProbeResult:
    valid: bool
    duration_seconds: float | None
    size_bytes: int
    streams: tuple[str, ...]
    message: str = ""


def probe_media(path: Path, timeout: float = 30) -> ProbeResult:
    if not path.is_file() or path.stat().st_size <= 0:
        return ProbeResult(False, None, 0, (), "File is missing or empty")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return ProbeResult(False, None, path.stat().st_size, (), "ffprobe is not installed")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        return ProbeResult(False, None, path.stat().st_size, (), result.stderr.strip())
    try:
        payload = json.loads(result.stdout)
        duration_raw = payload.get("format", {}).get("duration")
        duration = float(duration_raw) if duration_raw is not None else None
        streams = tuple(
            stream["codec_type"]
            for stream in payload.get("streams", [])
            if stream.get("codec_type") in {"video", "audio"}
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return ProbeResult(False, None, path.stat().st_size, (), f"Invalid ffprobe data: {exc}")
    return ProbeResult(bool(streams), duration, path.stat().st_size, streams)
