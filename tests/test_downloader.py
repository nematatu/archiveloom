from pathlib import Path
from typing import Any, ClassVar

import pytest

import archiveloom.core.downloader as downloader
from archiveloom.core.downloader import DownloadEngine
from archiveloom.core.probe import ProbeResult
from archiveloom.models import DownloadResult, ItemStatus, MediaItem, Protocol


def media_item(
    stable_id: str = "item-1",
    protocol: Protocol = Protocol.DIRECT,
    duration: float | None = None,
) -> MediaItem:
    return MediaItem(
        stable_id,
        stable_id,
        "https://example.org/video.mp4",
        protocol,
        f"{stable_id}.mp4",
        "https://example.org/",
        duration,
    )


class Board:
    def __init__(self) -> None:
        self.updates: list[tuple[object, ...]] = []
        self.finishes: list[tuple[str, ItemStatus]] = []

    def update(self, *args: object) -> None:
        self.updates.append(args)

    def finish(self, item_id: str, status: ItemStatus) -> None:
        self.finishes.append((item_id, status))


@pytest.mark.parametrize("jobs", [0, 17])
def test_engine_rejects_unsafe_parallelism(tmp_path: Path, jobs: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 16"):
        DownloadEngine(tmp_path, jobs=jobs)


def test_engine_keeps_state_inside_output(tmp_path: Path) -> None:
    engine = DownloadEngine(tmp_path, jobs=1)
    assert engine.output == tmp_path.resolve()
    assert engine.state.path == tmp_path.resolve() / ".archiveloom" / "state.json"


def test_run_records_success_and_worker_failure(monkeypatch: Any, tmp_path: Path) -> None:
    engine = DownloadEngine(tmp_path, jobs=2)
    board = Board()

    def fake_run(item: MediaItem, progress: object) -> DownloadResult:
        del progress
        if item.stable_id == "bad":
            raise RuntimeError("worker failed")
        return DownloadResult(item.stable_id, ItemStatus.COMPLETED, tmp_path / item.filename)

    monkeypatch.setattr(engine, "_run_item", fake_run)
    results = engine.run([media_item("good"), media_item("bad")], board)  # type: ignore[arg-type]
    assert {result.status for result in results} == {ItemStatus.COMPLETED, ItemStatus.FAILED}
    assert len(board.finishes) == 2
    assert engine.state.item("bad")["message"] == "worker failed"  # type: ignore[index]


def test_run_item_skips_verified_existing(monkeypatch: Any, tmp_path: Path) -> None:
    final = tmp_path / "item-1.mp4"
    final.write_bytes(b"video")
    monkeypatch.setattr(
        downloader,
        "probe_media",
        lambda path: ProbeResult(True, 3.0, path.stat().st_size, ("video",)),
    )
    result = DownloadEngine(tmp_path, attempts=1)._run_item(media_item(), lambda *args: None)
    assert result.status is ItemStatus.SKIPPED
    assert result.path == final


def test_run_item_never_overwrites_invalid_existing(monkeypatch: Any, tmp_path: Path) -> None:
    final = tmp_path / "item-1.mp4"
    final.write_bytes(b"keep me")
    monkeypatch.setattr(
        downloader,
        "probe_media",
        lambda path: ProbeResult(False, None, path.stat().st_size, (), "invalid"),
    )
    result = DownloadEngine(tmp_path, attempts=1)._run_item(media_item(), lambda *args: None)
    assert result.status is ItemStatus.FAILED
    assert final.read_bytes() == b"keep me"
    assert "never" not in result.message


def test_run_item_downloads_verifies_and_moves(monkeypatch: Any, tmp_path: Path) -> None:
    engine = DownloadEngine(tmp_path, attempts=1)

    def fake_download(item: MediaItem, path: Path, progress: object) -> None:
        del item, progress
        path.write_bytes(b"video")

    monkeypatch.setattr(engine, "_download_direct", fake_download)
    monkeypatch.setattr(
        downloader,
        "probe_media",
        lambda path: ProbeResult(True, 4.0, path.stat().st_size, ("video",)),
    )
    result = engine._run_item(media_item(duration=4.0), lambda *args: None)
    assert result.status is ItemStatus.COMPLETED
    assert result.path == tmp_path / "item-1.mp4"
    assert result.path.read_bytes() == b"video"


def test_hostile_stable_id_cannot_escape_partial_directory(
    monkeypatch: Any, tmp_path: Path
) -> None:
    engine = DownloadEngine(tmp_path, attempts=1)
    observed: list[Path] = []

    def fake_download(item: MediaItem, path: Path, progress: object) -> None:
        del item, progress
        observed.append(path)
        path.write_bytes(b"video")

    monkeypatch.setattr(engine, "_download_direct", fake_download)
    monkeypatch.setattr(
        downloader,
        "probe_media",
        lambda path: ProbeResult(True, 1.0, path.stat().st_size, ("video",)),
    )
    item = media_item(stable_id="../../escape")
    result = engine._run_item(item, lambda *args: None)
    assert result.status is ItemStatus.COMPLETED
    assert observed[0].parent == tmp_path / ".archiveloom" / "partial"
    assert ".." not in observed[0].name


def test_run_item_retries_then_fails(monkeypatch: Any, tmp_path: Path) -> None:
    engine = DownloadEngine(tmp_path, attempts=2)
    messages: list[str] = []
    monkeypatch.setattr(
        engine, "_download_direct", lambda *args: (_ for _ in ()).throw(OSError("offline"))
    )
    monkeypatch.setattr(downloader.time, "sleep", lambda _: None)
    result = engine._run_item(
        media_item(), lambda _id, _done, _total, message: messages.append(message)
    )
    assert result.status is ItemStatus.FAILED
    assert result.message == "offline"
    assert any("retrying" in message for message in messages)


def test_worker_error_redacts_signed_url(monkeypatch: Any, tmp_path: Path) -> None:
    engine = DownloadEngine(tmp_path, jobs=1)
    board = Board()

    def fail(item: MediaItem, progress: object) -> DownloadResult:
        del item, progress
        raise RuntimeError("failed at https://cdn.example.org/a.m3u8?token=very-secret")

    monkeypatch.setattr(engine, "_run_item", fail)
    result = engine.run([media_item()], board)[0]  # type: ignore[arg-type]
    assert "very-secret" not in result.message
    assert "redacted" in result.message


def test_run_item_detects_duration_mismatch(monkeypatch: Any, tmp_path: Path) -> None:
    engine = DownloadEngine(tmp_path, attempts=1)

    def fake_download(item: MediaItem, path: Path, progress: object) -> None:
        del item, progress
        path.write_bytes(b"video")

    monkeypatch.setattr(engine, "_download_direct", fake_download)
    monkeypatch.setattr(
        downloader,
        "probe_media",
        lambda path: ProbeResult(True, 40.0, path.stat().st_size, ("video",)),
    )
    result = engine._run_item(media_item(duration=10.0), lambda *args: None)
    assert result.status is ItemStatus.FAILED
    assert "duration mismatch" in result.message


def test_run_item_honors_cancellation(tmp_path: Path) -> None:
    engine = DownloadEngine(tmp_path, attempts=1)
    engine.cancelled.set()
    result = engine._run_item(media_item(), lambda *args: None)
    assert result.status is ItemStatus.CANCELLED


class FakeResponse:
    def __init__(self, status_code: int, chunks: list[bytes]) -> None:
        self.status_code = status_code
        self.chunks = chunks
        self.headers = {"content-length": str(sum(map(len, chunks)))}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self, size: int):  # type: ignore[no-untyped-def]
        del size
        yield from self.chunks


class FakeClient:
    response = FakeResponse(200, [b"new"])
    received_headers: ClassVar[dict[str, str]] = {}

    def __init__(self, **kwargs: object) -> None:
        del kwargs

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def stream(self, method: str, url: str, headers: dict[str, str]) -> FakeResponse:
        del method, url
        type(self).received_headers = headers
        return type(self).response


def test_direct_download_restarts_when_server_ignores_range(
    monkeypatch: Any, tmp_path: Path
) -> None:
    part = tmp_path / "part.mp4"
    part.write_bytes(b"old")
    FakeClient.response = FakeResponse(200, [b"new"])
    monkeypatch.setattr(downloader.httpx, "Client", FakeClient)
    DownloadEngine(tmp_path)._download_direct(media_item(), part, lambda *args: None)
    assert part.read_bytes() == b"new"
    assert FakeClient.received_headers["Range"] == "bytes=3-"


def test_direct_download_appends_partial_range(monkeypatch: Any, tmp_path: Path) -> None:
    part = tmp_path / "part.mp4"
    part.write_bytes(b"old")
    FakeClient.response = FakeResponse(206, [b"new"])
    monkeypatch.setattr(downloader.httpx, "Client", FakeClient)
    updates: list[tuple[object, ...]] = []
    DownloadEngine(tmp_path)._download_direct(
        media_item(), part, lambda *args: updates.append(args)
    )
    assert part.read_bytes() == b"oldnew"
    assert updates[-1][1:3] == (6, 6)


class ImmediateThread:
    def __init__(self, *, target, args, daemon):  # type: ignore[no-untyped-def]
        del daemon
        self.target = target
        self.args = args

    def start(self) -> None:
        self.target(*self.args)

    def join(self, timeout: float) -> None:
        del timeout


class FakeProcess:
    def __init__(self, returncode: int = 0) -> None:
        import io

        self.stdout = io.StringIO("out_time_us=2000000\ntotal_size=100\n")
        self.stderr = io.StringIO("simulated ffmpeg error\n" if returncode else "")
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    def poll(self) -> int:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float) -> int:
        del timeout
        return self.returncode


def test_ffmpeg_download_reports_progress(monkeypatch: Any, tmp_path: Path) -> None:
    process = FakeProcess()
    monkeypatch.setattr(downloader.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr(downloader.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(downloader.threading, "Thread", ImmediateThread)
    updates: list[tuple[object, ...]] = []
    item = media_item(protocol=Protocol.HLS, duration=10)
    DownloadEngine(tmp_path)._download_ffmpeg(
        item, tmp_path / "partial.mp4", lambda *args: updates.append(args)
    )
    assert updates[-1][1:3] == (2.0, 10)


def test_ffmpeg_download_reports_missing_binary_and_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    engine = DownloadEngine(tmp_path)
    item = media_item(protocol=Protocol.HLS)
    monkeypatch.setattr(downloader.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="required"):
        engine._download_ffmpeg(item, tmp_path / "a.mp4", lambda *args: None)

    process = FakeProcess(returncode=1)
    monkeypatch.setattr(downloader.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr(downloader.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(downloader.threading, "Thread", ImmediateThread)
    with pytest.raises(RuntimeError, match="simulated"):
        engine._download_ffmpeg(item, tmp_path / "a.mp4", lambda *args: None)


def test_stop_process_terminates_and_kills_after_timeout(monkeypatch: Any) -> None:
    process = FakeProcess()
    process.returncode = None  # type: ignore[assignment]

    def wait(timeout: float) -> int:
        if timeout == 10:
            raise downloader.subprocess.TimeoutExpired("ffmpeg", timeout)
        return 0

    process.wait = wait  # type: ignore[method-assign]
    monkeypatch.setattr(process, "poll", lambda: None)
    downloader._stop_process(process)  # type: ignore[arg-type]
    assert process.terminated
    assert process.killed
