import json
from pathlib import Path

import pytest

from archiveloom.adapters.base import AdapterError
from archiveloom.adapters.manifest import ManifestAdapter
from archiveloom.models import Protocol


def write_manifest(path: Path, items: list[object]) -> None:
    path.write_text(json.dumps({"version": 1, "items": items}), encoding="utf-8")


def test_manifest_discovers_and_sanitizes_items(tmp_path: Path) -> None:
    source = tmp_path / "collection.json"
    write_manifest(
        source,
        [
            {
                "id": "event-01",
                "title": "Event 01",
                "url": "https://media.example.org/master.m3u8",
                "protocol": "hls",
                "filename": "../2026-07-23_01.mp4",
                "headers": {"Referer": "https://example.org/"},
                "dimensions": {"date": "2026-07-23", "court": "01"},
                "duration_seconds": 42,
            }
        ],
    )

    items = ManifestAdapter().discover(str(source))

    assert len(items) == 1
    assert items[0].stable_id == "event-01"
    assert items[0].protocol is Protocol.HLS
    assert items[0].filename == "2026-07-23_01.mp4"
    assert items[0].dimensions == {"date": "2026-07-23", "court": "01"}


@pytest.mark.parametrize(
    "item",
    [
        {"title": "Missing URL"},
        {"title": "Local file", "url": "file:///tmp/video.mp4"},
        {"title": "Unsafe header", "url": "https://example.org/a.mp4", "headers": {"X": "a\nb"}},
        {"title": "Unknown", "url": "https://example.org/a", "protocol": "rtmp"},
    ],
)
def test_manifest_rejects_unsafe_items(tmp_path: Path, item: object) -> None:
    source = tmp_path / "collection.json"
    write_manifest(source, [item])
    with pytest.raises(AdapterError):
        ManifestAdapter().discover(str(source))


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"version": 2, "items": []},
        {"version": 1, "items": "not-a-list"},
        {"version": 1, "items": ["not-an-object"]},
        {"version": 1, "items": [{"url": "https://example.org/a.mp4"}]},
        {
            "version": 1,
            "items": [
                {
                    "title": "Bad dimensions",
                    "url": "https://example.org/a.mp4",
                    "dimensions": {"date": 1},
                }
            ],
        },
        {
            "version": 1,
            "items": [
                {
                    "title": "Bad duration",
                    "url": "https://example.org/a.mp4",
                    "duration_seconds": "many",
                }
            ],
        },
        {
            "version": 1,
            "items": [{"title": "Bad headers", "url": "https://example.org/a.mp4", "headers": []}],
        },
    ],
)
def test_manifest_rejects_invalid_shapes(tmp_path: Path, payload: object) -> None:
    source = tmp_path / "collection.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AdapterError):
        ManifestAdapter().discover(str(source))


def test_manifest_reports_invalid_json_and_missing_file(tmp_path: Path) -> None:
    source = tmp_path / "broken.json"
    source.write_text("{", encoding="utf-8")
    with pytest.raises(AdapterError, match="Cannot read"):
        ManifestAdapter().discover(str(source))
    with pytest.raises(AdapterError, match="does not exist"):
        ManifestAdapter().discover(str(tmp_path / "missing.json"))
