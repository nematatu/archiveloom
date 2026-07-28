import json
from pathlib import Path
from types import SimpleNamespace

import archiveloom.core.probe as probe


def test_probe_rejects_missing_and_empty_files(tmp_path: Path) -> None:
    assert not probe.probe_media(tmp_path / "missing.mp4").valid
    empty = tmp_path / "empty.mp4"
    empty.touch()
    assert not probe.probe_media(empty).valid


def test_probe_reports_missing_ffprobe(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    media = tmp_path / "media.mp4"
    media.write_bytes(b"x")
    monkeypatch.setattr(probe.shutil, "which", lambda _: None)
    result = probe.probe_media(media)
    assert not result.valid
    assert "not installed" in result.message


def test_probe_parses_streams(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    media = tmp_path / "media.mp4"
    media.write_bytes(b"content")
    monkeypatch.setattr(probe.shutil, "which", lambda _: "/usr/bin/ffprobe")
    payload = {
        "format": {"duration": "12.5"},
        "streams": [{"codec_type": "video"}, {"codec_type": "audio"}, {"codec_type": "data"}],
    }
    monkeypatch.setattr(
        probe.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=json.dumps(payload), stderr=""
        ),
    )
    result = probe.probe_media(media)
    assert result.valid
    assert result.duration_seconds == 12.5
    assert result.streams == ("video", "audio")


def test_probe_reports_process_and_json_failures(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    media = tmp_path / "media.mp4"
    media.write_bytes(b"content")
    monkeypatch.setattr(probe.shutil, "which", lambda _: "/usr/bin/ffprobe")
    monkeypatch.setattr(
        probe.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="bad file"),
    )
    assert probe.probe_media(media).message == "bad file"
    monkeypatch.setattr(
        probe.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="{", stderr=""),
    )
    assert "Invalid ffprobe data" in probe.probe_media(media).message
