import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

import archiveloom.cli as cli
from archiveloom import __version__
from archiveloom.cli import app
from archiveloom.core.doctor import DoctorCheck
from archiveloom.core.storage import StorageError
from archiveloom.models import DownloadResult, ItemStatus

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"ArchiveLoom {__version__}" in result.stdout


def test_adapter_list() -> None:
    result = runner.invoke(app, ["adapters", "list"])
    assert result.exit_code == 0
    assert "direct" in result.stdout
    assert "manifest" in result.stdout


def test_manifest_check_only(tmp_path: Path) -> None:
    manifest = tmp_path / "collection.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {
                        "title": "Public sample",
                        "url": "https://example.org/video.mp4",
                        "filename": "sample.mp4",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "--lang",
            "ja",
            "download",
            str(manifest),
            "--output",
            str(tmp_path / "out"),
            "--check-only",
        ],
    )
    assert result.exit_code == 0
    assert "1件" in result.stdout
    assert "確認専用" in result.stdout


def test_adapter_scaffold(tmp_path: Path) -> None:
    result = runner.invoke(app, ["adapters", "scaffold", "sample-site", "--output", str(tmp_path)])
    assert result.exit_code == 0
    root = tmp_path / "archiveloom-sample-site"
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "archiveloom_sample_site" / "adapter.py").is_file()


def test_invalid_language_and_scaffold_name(tmp_path: Path) -> None:
    assert runner.invoke(app, ["--lang", "xx", "adapters", "list"]).exit_code != 0
    result = runner.invoke(app, ["adapters", "scaffold", "1bad", "--output", str(tmp_path)])
    assert result.exit_code != 0


def test_inspect_direct_url() -> None:
    result = runner.invoke(app, ["inspect", "https://example.org/video.mp4"])
    assert result.exit_code == 0
    assert "video.mp4" in result.stdout


def test_empty_and_broken_manifest_exit_cleanly(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text('{"version":1,"items":[]}', encoding="utf-8")
    result = runner.invoke(app, ["download", str(empty), "--output", str(tmp_path / "out")])
    assert result.exit_code == 2
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    result = runner.invoke(app, ["inspect", str(broken)])
    assert result.exit_code == 6
    assert "Adapter error" in result.stdout


def test_doctor_exit_codes(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        cli, "run_doctor", lambda *args, **kwargs: [DoctorCheck("test", "OK", "fine")]
    )
    assert runner.invoke(app, ["doctor"]).exit_code == 0
    monkeypatch.setattr(
        cli, "run_doctor", lambda *args, **kwargs: [DoctorCheck("test", "ERROR", "bad")]
    )
    assert runner.invoke(app, ["doctor"]).exit_code == 3


class FakeBoard:
    def __init__(self, *args: object) -> None:
        del args

    def __enter__(self) -> "FakeBoard":
        return self

    def __exit__(self, *args: object) -> None:
        del args


class FakeEngine:
    result_status = ItemStatus.COMPLETED

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def run(self, items, board):  # type: ignore[no-untyped-def]
        del board
        return [DownloadResult(item.stable_id, self.result_status) for item in items]


def test_download_success_and_failure_exit_codes(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "DownloadEngine", FakeEngine)
    monkeypatch.setattr(cli, "ProgressBoard", FakeBoard)
    source = "https://example.org/video.mp4"
    output = str(tmp_path / "out")
    FakeEngine.result_status = ItemStatus.COMPLETED
    result = runner.invoke(app, ["download", source, "--output", output, "--yes"])
    assert result.exit_code == 0
    assert "Completed: 1" in result.stdout
    FakeEngine.result_status = ItemStatus.FAILED
    result = runner.invoke(app, ["download", source, "--output", output, "--yes"])
    assert result.exit_code == 4


def test_download_reports_fatal_storage_error(monkeypatch: Any, tmp_path: Path) -> None:
    class BrokenEngine(FakeEngine):
        def run(self, items, board):  # type: ignore[no-untyped-def]
            del items, board
            raise StorageError("external disk unavailable")

    monkeypatch.setattr(cli, "DownloadEngine", BrokenEngine)
    monkeypatch.setattr(cli, "ProgressBoard", FakeBoard)
    result = runner.invoke(
        app,
        [
            "download",
            "https://example.org/video.mp4",
            "--output",
            str(tmp_path / "out"),
            "--yes",
        ],
    )
    assert result.exit_code == 7
    assert "external disk unavailable" in result.stdout


def test_download_cancelled_at_confirmation(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["download", "https://example.org/video.mp4", "--output", str(tmp_path / "out")],
        input="n\n",
    )
    assert result.exit_code == 130


def test_interactive_requires_terminal(tmp_path: Path) -> None:
    manifest = tmp_path / "two.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {"title": "One", "url": "https://example.org/one.mp4"},
                    {"title": "Two", "url": "https://example.org/two.mp4"},
                ],
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["download", str(manifest), "--output", str(tmp_path / "out"), "--interactive"],
    )
    assert result.exit_code != 0
