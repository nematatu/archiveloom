import io

from rich.console import Console

from archiveloom.core.progress import ProgressBoard
from archiveloom.models import ItemStatus, MediaItem, Protocol


def item(stable_id: str, protocol: Protocol, duration: float | None = None) -> MediaItem:
    return MediaItem(
        stable_id, stable_id, "https://example.org/a", protocol, f"{stable_id}.mp4", "x", duration
    )


def test_progress_board_updates_known_and_unknown_totals() -> None:
    console = Console(file=io.StringIO(), force_terminal=True, width=100)
    items = [item("hls", Protocol.HLS, 10), item("direct", Protocol.DIRECT)]
    board = ProgressBoard(console, items)
    with board:
        board.update("hls", 5, 10, "downloading")
        board.update("direct", 20, None, "downloading")
        board.finish("hls", ItemStatus.COMPLETED)
        board.finish("direct", ItemStatus.SKIPPED)
    assert board._finished == 2
    assert board._progress.tasks[board._overall].completed == 2


def test_progress_board_treats_site_filename_as_plain_text() -> None:
    console = Console(file=io.StringIO(), force_terminal=True, width=100)
    media = item("[red]spoof[/red]", Protocol.DIRECT)
    board = ProgressBoard(console, [media])
    task = board._progress.tasks[board._tasks[media.stable_id]]

    rendered = board._progress.columns[1].render(task)

    assert rendered.plain == "[red]spoof[/red].mp4"
