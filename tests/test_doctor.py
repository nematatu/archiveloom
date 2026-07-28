from pathlib import Path

import archiveloom.core.doctor as doctor
from archiveloom.core.storage import StorageReport


def test_doctor_reports_tools_and_storage(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/tools/{name}")
    monkeypatch.setattr(
        doctor,
        "inspect_storage",
        lambda path: StorageReport(path, True, True, 10_000_000_000, True, "external test disk"),
    )
    checks = doctor.run_doctor(tmp_path, external_only=True)
    assert {check.name for check in checks} >= {"Operating system", "Python", "ffmpeg", "Storage"}
    assert all(check.status == "OK" for check in checks)


def test_doctor_reports_missing_tool_and_internal_storage(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        doctor,
        "inspect_storage",
        lambda path: StorageReport(path, True, True, None, False, "internal"),
    )
    checks = doctor.run_doctor(tmp_path, external_only=True)
    statuses = {check.name: check.status for check in checks}
    assert statuses["ffmpeg"] == "ERROR"
    assert statuses["ffprobe"] == "ERROR"
    assert statuses["Storage"] == "ERROR"
