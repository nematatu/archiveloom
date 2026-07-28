from pathlib import Path

import pytest

from archiveloom.core.locking import AlreadyRunningError, RunLock


def test_second_run_cannot_lock_same_output(tmp_path: Path) -> None:
    with RunLock(tmp_path), pytest.raises(AlreadyRunningError), RunLock(tmp_path):
        pass


def test_lock_metadata_is_cleaned(tmp_path: Path) -> None:
    with RunLock(tmp_path):
        assert (tmp_path / ".archiveloom" / "run.json").exists()
    assert not (tmp_path / ".archiveloom" / "run.json").exists()
