import pytest

from archiveloom.models import MediaItem, Protocol
from archiveloom.tui import MediaRow, SelectorApp


def make_item(stable_id: str) -> MediaItem:
    return MediaItem(
        stable_id,
        f"Item {stable_id}",
        "https://example.org/a.mp4",
        Protocol.DIRECT,
        f"{stable_id}.mp4",
        "https://example.org/",
        dimensions={"date": "2026-07-23"},
    )


@pytest.mark.anyio
async def test_selector_keyboard_workflow(anyio_backend: str) -> None:
    del anyio_backend
    app = SelectorApp([make_item("one"), make_item("two")])
    async with app.run_test() as pilot:
        rows = list(app.query(MediaRow))
        assert all(row.selected for row in rows)
        await pilot.press("space")
        assert not rows[0].selected
        await pilot.press("a")
        assert all(row.selected for row in rows)
        await pilot.press("j", "k")
        await pilot.press("enter")
        await pilot.pause()
    assert app.return_value == ["one", "two"]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
