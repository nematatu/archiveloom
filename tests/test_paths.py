from pathlib import Path

import pytest

from archiveloom.core.paths import UnsafeMetadataError, ensure_metadata_dir


def test_metadata_directory_is_created_inside_output(tmp_path: Path) -> None:
    metadata = ensure_metadata_dir(tmp_path)
    assert metadata == tmp_path / ".archiveloom"
    assert metadata.is_dir()


def test_metadata_symlink_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    metadata = tmp_path / ".archiveloom"
    try:
        metadata.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are not available on this runner")
    with pytest.raises(UnsafeMetadataError, match="symlink"):
        ensure_metadata_dir(tmp_path)
