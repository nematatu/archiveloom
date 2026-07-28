from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from archiveloom import __version__
from archiveloom.adapters.base import AdapterError
from archiveloom.adapters.registry import AdapterRegistry
from archiveloom.core.doctor import run_doctor
from archiveloom.core.downloader import DownloadEngine
from archiveloom.core.locking import AlreadyRunningError
from archiveloom.core.paths import UnsafeMetadataError
from archiveloom.core.progress import ProgressBoard
from archiveloom.core.storage import StorageError, inspect_storage
from archiveloom.i18n import SUPPORTED_LANGUAGES, detect_language, translate
from archiveloom.models import DownloadResult, ItemStatus, MediaItem
from archiveloom.tui import select_items

app = typer.Typer(
    name="archiveloom",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
    help="Safe, adapter-driven bulk media archiving.",
)
adapters_app = typer.Typer(no_args_is_help=True, help="Inspect and create site adapters.")
app.add_typer(adapters_app, name="adapters")
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"ArchiveLoom {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    language: Annotated[
        str,
        typer.Option("--lang", help="UI language: auto, en, ja", envvar="ARCHIVELOOM_LANG"),
    ] = "auto",
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    del version
    if language != "auto" and language not in SUPPORTED_LANGUAGES:
        raise typer.BadParameter("--lang must be auto, en, or ja")
    ctx.ensure_object(dict)
    ctx.obj["lang"] = detect_language(language)


@app.command("doctor")
def doctor_command(
    ctx: typer.Context,
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    external_only: Annotated[bool, typer.Option("--external-only")] = False,
) -> None:
    lang = ctx.obj["lang"]
    table = Table(title=translate("doctor_title", lang))
    table.add_column("Status", no_wrap=True)
    table.add_column("Check")
    table.add_column("Detail")
    failed = False
    for check in run_doctor(output, external_only=external_only):
        color = {"OK": "green", "WARN": "yellow", "ERROR": "red"}[check.status]
        table.add_row(f"[{color}]{check.status}[/]", check.name, check.detail)
        failed |= check.status == "ERROR"
    console.print(table)
    if failed:
        raise typer.Exit(3)


@adapters_app.command("list")
def adapters_list(ctx: typer.Context) -> None:
    table = Table(title=translate("adapters_title", ctx.obj["lang"]))
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    for adapter in AdapterRegistry().all():
        table.add_row(adapter.name, adapter.description)
    console.print(table)


@adapters_app.command("scaffold")
def adapters_scaffold(
    name: Annotated[str, typer.Argument(help="Adapter package name")],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("."),
) -> None:
    normalized = name.lower().replace("-", "_")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", normalized):
        raise typer.BadParameter("Use letters, numbers, and underscores; start with a letter.")
    root = (output / f"archiveloom-{normalized.replace('_', '-')}").resolve()
    if root.exists():
        raise typer.BadParameter(f"Destination already exists: {root}")
    package = root / "src" / f"archiveloom_{normalized}"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("\n", encoding="utf-8")
    (package / "adapter.py").write_text(_adapter_template(normalized), encoding="utf-8")
    (root / "pyproject.toml").write_text(_adapter_pyproject(normalized), encoding="utf-8")
    (root / "README.md").write_text(
        f"# ArchiveLoom adapter: {normalized}\n\nSee the ArchiveLoom adapter guide.\n",
        encoding="utf-8",
    )
    console.print(f"[green]Created[/] {root}")


@app.command("inspect")
def inspect_command(
    sources: Annotated[list[str], typer.Argument(help="Media URLs or local manifests")],
    adapter: Annotated[str | None, typer.Option("--adapter")] = None,
) -> None:
    items = _discover(sources, adapter)
    _print_items(items)


@app.command("download")
def download_command(
    ctx: typer.Context,
    sources: Annotated[list[str], typer.Argument(help="Media URLs or local manifests")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")],
    adapter: Annotated[str | None, typer.Option("--adapter")] = None,
    jobs: Annotated[int, typer.Option("--jobs", "-j", min=1, max=16)] = 2,
    interactive: Annotated[bool, typer.Option("--interactive", "-i")] = False,
    check_only: Annotated[bool, typer.Option("--check-only")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
    external_only: Annotated[bool, typer.Option("--external-only")] = False,
) -> None:
    lang = ctx.obj["lang"]
    items = _discover(sources, adapter)
    console.print(translate("items_found", lang, count=len(items)))
    if interactive and len(items) > 1:
        if not sys.stdin.isatty():
            raise typer.BadParameter("--interactive requires a TTY")
        items = select_items(items)
    if not items:
        console.print(f"[yellow]{translate('no_items', lang)}[/]")
        raise typer.Exit(2)
    _print_items(items)
    storage = inspect_storage(output)
    free = (
        f"{storage.free_bytes / 1_000_000_000:.1f} GB"
        if storage.free_bytes is not None
        else "unknown"
    )
    console.print(f"Output: [bold]{storage.path}[/] · Free: {free} · {storage.detail}")
    if check_only:
        console.print(f"[green]{translate('check_only', lang)}[/]")
        return
    if not yes and not typer.confirm(translate("confirm", lang)):
        console.print(translate("cancelled", lang))
        raise typer.Exit(130)
    engine = DownloadEngine(output, jobs=jobs, external_only=external_only)
    try:
        with ProgressBoard(console, items) as board:
            results = engine.run(items, board)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Completed files remain reusable.[/]")
        raise typer.Exit(130) from None
    except (AlreadyRunningError, StorageError, UnsafeMetadataError) as exc:
        console.print(f"\n[red]Storage error:[/] {exc}")
        raise typer.Exit(7) from exc
    _print_summary(results, lang)
    failures = [
        result for result in results if result.status in {ItemStatus.FAILED, ItemStatus.UNSUPPORTED}
    ]
    if failures:
        raise typer.Exit(4)


def _discover(sources: list[str], adapter_name: str | None) -> list[MediaItem]:
    registry = AdapterRegistry()
    items: list[MediaItem] = []
    seen: set[str] = set()
    try:
        for source in sources:
            adapter = registry.resolve(source, adapter_name)
            for item in adapter.discover(source):
                if item.stable_id not in seen:
                    seen.add(item.stable_id)
                    items.append(item)
    except AdapterError as exc:
        console.print(f"[red]Adapter error:[/] {exc}")
        raise typer.Exit(6) from exc
    return items


def _print_items(items: list[MediaItem]) -> None:
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("#", justify="right")
    table.add_column("Title")
    table.add_column("Protocol")
    table.add_column("Filename")
    for index, item in enumerate(items, 1):
        table.add_row(str(index), item.title, item.protocol.value, item.filename)
    console.print(table)


def _print_summary(results: list[DownloadResult], lang: str) -> None:
    counts = {status: 0 for status in ItemStatus}
    for result in results:
        status = result.status
        counts[status] += 1
    lines = [
        f"Completed: {counts[ItemStatus.COMPLETED]}",
        f"Skipped: {counts[ItemStatus.SKIPPED]}",
        f"Failed: {counts[ItemStatus.FAILED]}",
        f"Unsupported: {counts[ItemStatus.UNSUPPORTED]}",
    ]
    console.print(Panel("\n".join(lines), title=translate("summary", lang), border_style="cyan"))


def _adapter_template(name: str) -> str:
    class_name = "".join(part.title() for part in name.split("_")) + "Adapter"
    return f'''from archiveloom.models import MediaItem


class {class_name}:
    name = "{name}"
    description = "Describe the supported site"

    def can_handle(self, source: str) -> bool:
        return False

    def discover(self, source: str) -> list[MediaItem]:
        raise NotImplementedError
'''


def _adapter_pyproject(name: str) -> str:
    class_name = "".join(part.title() for part in name.split("_")) + "Adapter"
    distribution = name.replace("_", "-")
    return f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "archiveloom-{distribution}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["archiveloom>=0.1"]

[project.entry-points."archiveloom.adapters"]
{name} = "archiveloom_{name}.adapter:{class_name}"
"""
