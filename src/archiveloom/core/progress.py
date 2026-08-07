from __future__ import annotations

import threading

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from archiveloom.models import ItemStatus, MediaItem


class ProgressBoard:
    def __init__(self, console: Console, items: list[MediaItem]) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}", style="bold", markup=False),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TextColumn("{task.fields[status]}"),
            console=console,
            transient=False,
            refresh_per_second=6,
        )
        self._tasks: dict[str, TaskID] = {}
        self._lock = threading.Lock()
        self._overall = self._progress.add_task(
            "Overall", total=len(items), status=f"0/{len(items)}"
        )
        for item in items:
            total = (
                item.duration_seconds
                if item.duration_seconds and item.protocol.value != "direct"
                else None
            )
            self._tasks[item.stable_id] = self._progress.add_task(
                item.filename, total=total, status="queued"
            )
        self._finished = 0
        self._total_items = len(items)

    def __enter__(self) -> ProgressBoard:
        self._progress.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._progress.stop()

    def update(self, item_id: str, completed: float, total: float | None, status: str) -> None:
        with self._lock:
            task = self._tasks[item_id]
            if total is not None:
                self._progress.update(task, total=total)
            self._progress.update(task, completed=completed, status=status)

    def finish(self, item_id: str, status: ItemStatus) -> None:
        with self._lock:
            task = self._tasks[item_id]
            current = self._progress.tasks[task]
            if current.total is None:
                self._progress.update(task, total=1, completed=1)
            else:
                self._progress.update(task, completed=current.total)
            self._progress.update(task, status=status.value)
            self._finished += 1
            self._progress.update(
                self._overall,
                completed=self._finished,
                status=f"{self._finished}/{self._total_items}",
            )
