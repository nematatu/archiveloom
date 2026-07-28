from __future__ import annotations

import re
import unicodedata
from pathlib import Path

CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
UNSAFE_RE = re.compile(r"[<>:\"/\\|?*]")
SPACE_RE = re.compile(r"\s+")
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_filename(value: str, limit: int = 180) -> str:
    leaf = value.replace("\\", "/").rsplit("/", 1)[-1]
    normalized = unicodedata.normalize("NFKC", leaf)
    normalized = CONTROL_RE.sub("", normalized)
    normalized = UNSAFE_RE.sub("_", normalized)
    normalized = SPACE_RE.sub(" ", normalized).strip(" .")
    if not normalized:
        normalized = "media"
    path = Path(normalized)
    stem, suffix = path.stem, path.suffix
    if stem.upper() in WINDOWS_RESERVED:
        stem = f"_{stem}"
    available = max(1, limit - len(suffix))
    return f"{stem[:available]}{suffix}"


def safe_child(root: Path, filename: str) -> Path:
    root = root.resolve()
    candidate = (root / safe_filename(filename)).resolve()
    if candidate.parent != root:
        raise ValueError("Output path escaped the selected root.")
    return candidate
