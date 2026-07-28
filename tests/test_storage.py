import plistlib
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from typing import Any

import pytest

import archiveloom.core.storage as storage


def test_missing_child_uses_existing_parent(tmp_path: Path) -> None:
    report = storage.inspect_storage(tmp_path / "new" / "archive")
    assert report.path == (tmp_path / "new" / "archive").resolve()
    assert report.writable
    assert report.free_bytes is not None


def test_unknown_platform_does_not_claim_external(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(storage.platform, "system", lambda: "MysteryOS")
    report = storage.inspect_storage(tmp_path)
    assert report.external is None
    assert "Unsupported" in report.detail


def test_require_storage_enforces_writable_and_external(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        storage,
        "inspect_storage",
        lambda _: storage.StorageReport(tmp_path, True, False, 1, None, "not writable"),
    )
    with pytest.raises(RuntimeError, match="not writable"):
        storage.require_storage(tmp_path, external_only=False)
    monkeypatch.setattr(
        storage,
        "inspect_storage",
        lambda _: storage.StorageReport(tmp_path, True, True, 1, False, "internal"),
    )
    with pytest.raises(RuntimeError, match="external"):
        storage.require_storage(tmp_path, external_only=True)


def test_macos_external_parses_diskutil(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(storage.shutil, "which", lambda _: "/usr/sbin/diskutil")
    payload = plistlib.dumps({"Internal": False, "DeviceIdentifier": "disk4s2"})
    monkeypatch.setattr(
        storage.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=payload),
    )
    assert storage._macos_external(tmp_path) == (True, "device=disk4s2, internal=False")


def test_macos_external_handles_tool_errors(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(storage.shutil, "which", lambda _: None)
    assert storage._macos_external(tmp_path)[0] is None
    monkeypatch.setattr(storage.shutil, "which", lambda _: "/usr/sbin/diskutil")
    monkeypatch.setattr(
        storage.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=b""),
    )
    assert storage._macos_external(tmp_path)[0] is None


def test_linux_external_parses_mount_and_block(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(storage.shutil, "which", lambda name: f"/usr/bin/{name}")
    responses = iter(
        [
            SimpleNamespace(returncode=0, stdout='{"filesystems":[{"source":"/dev/sdb1"}]}'),
            SimpleNamespace(
                returncode=0,
                stdout='{"blockdevices":[{"path":"/dev/sdb1","rm":false,"tran":"usb"}]}',
            ),
        ]
    )
    monkeypatch.setattr(storage.subprocess, "run", lambda *args, **kwargs: next(responses))
    external, detail = storage._linux_external(tmp_path)
    assert external is True
    assert "transport=usb" in detail


def test_linux_external_handles_missing_tools(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(storage.shutil, "which", lambda _: None)
    assert storage._linux_external(tmp_path)[0] is None


def test_windows_external_parses_powershell(monkeypatch: Any) -> None:
    monkeypatch.setattr(storage.shutil, "which", lambda _: "C:/pwsh.exe")
    monkeypatch.setattr(
        storage.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout='{"BusType":"USB","IsBoot":false,"IsSystem":false}',
        ),
    )
    external, detail = storage._windows_external(PureWindowsPath("E:/archive"))  # type: ignore[arg-type]
    assert external is True
    assert "drive=E:" in detail


def test_windows_external_rejects_missing_drive() -> None:
    assert storage._windows_external(Path("relative"))[0] is None
