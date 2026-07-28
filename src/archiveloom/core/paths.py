from __future__ import annotations

from pathlib import Path


class UnsafeMetadataError(RuntimeError):
    pass


def ensure_metadata_dir(output_root: Path) -> Path:
    """Create the private metadata directory without following a directory symlink."""
    root = output_root.expanduser().resolve()
    metadata = root / ".archiveloom"
    if metadata.is_symlink():
        raise UnsafeMetadataError(f"Metadata path must not be a symlink: {metadata}")
    metadata.mkdir(parents=True, exist_ok=True)
    if metadata.resolve().parent != root:
        raise UnsafeMetadataError(f"Metadata path escaped the output directory: {metadata}")
    return metadata
