import json
from pathlib import Path

from archiveloom.core.state import StateStore
from archiveloom.models import DownloadResult, ItemStatus


def test_state_store_writes_atomic_result(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.initialize()
    result = DownloadResult("item-1", ItemStatus.COMPLETED, tmp_path / "video.mp4", 123, 4.5)

    store.record(result)

    payload = json.loads((tmp_path / ".archiveloom" / "state.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["items"]["item-1"]["status"] == "completed"
    assert payload["items"]["item-1"]["size_bytes"] == 123
    assert not list((tmp_path / ".archiveloom").glob("*.tmp"))
