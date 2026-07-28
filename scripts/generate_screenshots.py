"""Generate deterministic, sanitized README terminal artwork."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeRemainingColumn
from rich.table import Table


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "assets" / "screenshots" / "dashboard.svg"
    console = Console(record=True, width=104, height=30)
    console.print("[bold cyan]ArchiveLoom[/] 0.1.0  ·  manifest adapter  ·  2 parallel jobs")
    table = Table(show_header=True, header_style="bold blue", box=None)
    table.add_column("#", justify="right", width=3)
    table.add_column("Title", width=35)
    table.add_column("Protocol", width=10)
    table.add_column("Filename", width=32)
    table.add_row("1", "Opening ceremony", "hls", "2026-07-23_01.mp4")
    table.add_row("2", "Final court", "hls", "2026-07-23_02.mp4")
    table.add_row("3", "Highlights", "direct", "2026-07-23_highlights.mp4")
    console.print(table)
    progress = Progress(
        TextColumn("[bold]{task.description:<30}"),
        BarColumn(bar_width=28),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    progress.add_task("2026-07-23_01.mp4", total=100, completed=100)
    progress.add_task("2026-07-23_02.mp4", total=100, completed=64)
    progress.add_task("2026-07-23_highlights.mp4", total=100, completed=27)
    console.print(progress)
    console.print(
        Panel(
            "[green]Completed: 1[/]   Skipped: 0   [cyan]Active: 2[/]   Failed: 0\n"
            "Output: /media/archive/archiveloom-demo",
            title="Progress",
            border_style="cyan",
        )
    )
    console.save_svg(str(output), title="ArchiveLoom terminal preview", theme=None)
    rendered = "\n".join(line.rstrip() for line in output.read_text(encoding="utf-8").splitlines())
    rendered += "\n"
    output.write_text(rendered, encoding="utf-8")
    docs_output = root / "docs" / "assets" / "screenshots" / "dashboard.svg"
    docs_output.parent.mkdir(parents=True, exist_ok=True)
    docs_output.write_text(rendered, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
