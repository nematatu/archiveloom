from __future__ import annotations

import json
import os
import platform
import plistlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StorageReport:
    path: Path
    exists: bool
    writable: bool
    free_bytes: int | None
    external: bool | None
    detail: str


class StorageError(RuntimeError):
    pass


def inspect_storage(path: Path) -> StorageReport:
    resolved = path.expanduser().resolve()
    probe = resolved if resolved.exists() else _existing_parent(resolved)
    exists = resolved.exists()
    writable = probe is not None and os.access(probe, os.W_OK)
    free = shutil.disk_usage(probe).free if probe is not None else None
    external, detail = _external_status(probe) if probe is not None else (None, "No parent exists")
    return StorageReport(resolved, exists, writable, free, external, detail)


def require_storage(path: Path, *, external_only: bool) -> StorageReport:
    report = inspect_storage(path)
    if not report.writable:
        raise StorageError(f"Output directory is not writable: {report.path}")
    if external_only and report.external is not True:
        reason = report.detail if report.external is None else "The selected disk is internal"
        raise StorageError(f"Cannot verify an external storage target: {reason}")
    return report


def _existing_parent(path: Path) -> Path | None:
    current = path
    while current != current.parent:
        if current.exists():
            return current
        current = current.parent
    return current if current.exists() else None


def _external_status(path: Path) -> tuple[bool | None, str]:
    system = platform.system()
    if system == "Darwin":
        return _macos_external(path)
    if system == "Linux":
        return _linux_external(path)
    if system == "Windows":
        return _windows_external(path)
    return None, f"Unsupported operating system: {system}"


def _macos_external(path: Path) -> tuple[bool | None, str]:
    diskutil = shutil.which("diskutil")
    if diskutil is None:
        return None, "diskutil is not available"
    result = subprocess.run(
        [diskutil, "info", "-plist", str(path)],
        capture_output=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        return None, "diskutil could not inspect the path"
    try:
        data = plistlib.loads(result.stdout)
    except plistlib.InvalidFileException:
        return None, "diskutil returned invalid data"
    internal = data.get("Internal")
    device = data.get("DeviceIdentifier", "unknown device")
    return (
        (not internal, f"device={device}, internal={internal}")
        if isinstance(internal, bool)
        else (None, f"device={device}")
    )


def _linux_external(path: Path) -> tuple[bool | None, str]:
    findmnt = shutil.which("findmnt")
    lsblk = shutil.which("lsblk")
    if findmnt is None or lsblk is None:
        return None, "findmnt and lsblk are required to inspect Linux storage"
    mount = subprocess.run(
        [findmnt, "-J", "-T", str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if mount.returncode != 0:
        return None, "findmnt could not inspect the path"
    try:
        source = json.loads(mount.stdout)["filesystems"][0]["source"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None, "findmnt returned unexpected data"
    block = subprocess.run(
        [lsblk, "-J", "-o", "PATH,RM,TRAN", source],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if block.returncode != 0:
        return None, f"lsblk could not inspect {source}"
    try:
        device = json.loads(block.stdout)["blockdevices"][0]
        removable = bool(device.get("rm"))
        transport = str(device.get("tran") or "")
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None, "lsblk returned unexpected data"
    external = removable or transport in {"usb", "mmc", "sd"}
    return external, f"device={source}, removable={removable}, transport={transport or 'unknown'}"


def _windows_external(path: Path) -> tuple[bool | None, str]:
    drive = path.drive.rstrip(":")
    if len(drive) != 1 or not drive.isascii() or not drive.isalpha():
        return None, "The path has no drive letter"
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        return None, "PowerShell is not available"
    script = (
        f"Get-Partition -DriveLetter '{drive}' | Get-Disk | "
        "Select-Object BusType,IsBoot,IsSystem | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        return None, "PowerShell could not inspect the drive"
    try:
        data = json.loads(result.stdout)
        bus = str(data.get("BusType") or "")
        boot = bool(data.get("IsBoot"))
        system = bool(data.get("IsSystem"))
    except (AttributeError, json.JSONDecodeError):
        return None, "PowerShell returned unexpected data"
    external = bus.upper() in {"USB", "SD", "MMC", "IEEE1394"} and not boot and not system
    return external, f"drive={drive}:, bus={bus or 'unknown'}, boot={boot}, system={system}"
