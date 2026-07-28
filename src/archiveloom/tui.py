from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from archiveloom.models import MediaItem


class MediaRow(ListItem):
    def __init__(self, item: MediaItem) -> None:
        super().__init__()
        self.item = item
        self.selected = True

    def compose(self) -> ComposeResult:
        yield Label(self._label(), id="label")

    def toggle(self) -> None:
        self.selected = not self.selected
        self.query_one("#label", Label).update(self._label())

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.query_one("#label", Label).update(self._label())

    def _label(self) -> str:
        mark = "[x]" if self.selected else "[ ]"
        details = " · ".join(self.item.dimensions.values())
        suffix = f"  [dim]{details}[/]" if details else ""
        return f"{mark}  {self.item.title}{suffix}"


class SelectorApp(App[list[str]]):
    CSS = """
    Screen { background: #0b1020; color: #e8eefc; }
    #shell { width: 90%; max-width: 110; height: 90%; margin: 2 4; }
    #title { padding: 1 2; background: #17213d; color: #70d6ff; text-style: bold; }
    ListView { height: 1fr; border: round #3559a8; padding: 1; }
    ListItem { padding: 0 1; }
    ListItem.--highlight { background: #233664; }
    #hint { padding: 1 2; color: #a7b6d8; }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("j", "down", "Down", show=False),
        Binding("k", "up", "Up", show=False),
        Binding("space", "toggle_selection", "Toggle"),
        Binding("a", "toggle_all", "All"),
        Binding("enter", "submit", "Continue", priority=True),
        Binding("q", "cancel", "Cancel"),
    ]

    def __init__(self, items: list[MediaItem]) -> None:
        super().__init__()
        self.items = items

    def compose(self) -> ComposeResult:
        rows = [MediaRow(item) for item in self.items]
        with Vertical(id="shell"):
            yield Header(show_clock=True)
            yield Static("ArchiveLoom · Select media", id="title")
            yield ListView(*rows, id="media-list")
            yield Static(
                "↑↓/j/k move · Space toggle · a all · Enter continue · q cancel", id="hint"
            )
            yield Footer()

    def action_down(self) -> None:
        self.query_one("#media-list", ListView).action_cursor_down()

    def action_up(self) -> None:
        self.query_one("#media-list", ListView).action_cursor_up()

    def action_toggle_selection(self) -> None:
        row = self._current_row()
        if row:
            row.toggle()

    def action_toggle_all(self) -> None:
        rows = list(self.query(MediaRow))
        target = not all(row.selected for row in rows)
        for row in rows:
            row.set_selected(target)

    def action_submit(self) -> None:
        self.exit([row.item.stable_id for row in self.query(MediaRow) if row.selected])

    def action_cancel(self) -> None:
        self.exit([])

    def _current_row(self) -> MediaRow | None:
        view = self.query_one("#media-list", ListView)
        if view.index is None:
            return None
        child = view.children[view.index]
        return child if isinstance(child, MediaRow) else None


def select_items(items: list[MediaItem]) -> list[MediaItem]:
    selected_ids = SelectorApp(items).run()
    selected = set(selected_ids or [])
    return [item for item in items if item.stable_id in selected]
