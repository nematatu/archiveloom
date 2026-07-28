from pathlib import Path
from types import SimpleNamespace

import pytest

import archiveloom.adapters.registry as registry_module
from archiveloom.adapters.base import AdapterError
from archiveloom.adapters.registry import AdapterRegistry


def test_builtin_adapters_are_registered() -> None:
    assert {adapter.name for adapter in AdapterRegistry().all()} >= {"direct", "manifest"}


def test_direct_adapter_is_selected_for_http_media() -> None:
    adapter = AdapterRegistry().resolve("https://example.org/video.mp4")
    assert adapter.name == "direct"


def test_manifest_adapter_is_selected_for_file(tmp_path: Path) -> None:
    source = tmp_path / "items.json"
    source.write_text('{"version": 1, "items": []}', encoding="utf-8")
    assert AdapterRegistry().resolve(str(source)).name == "manifest"


def test_unknown_explicit_adapter_fails() -> None:
    with pytest.raises(AdapterError, match="Unknown adapter"):
        AdapterRegistry().resolve("https://example.org/video.mp4", "missing")


def test_preferred_adapter_must_handle_source() -> None:
    with pytest.raises(AdapterError, match="cannot handle"):
        AdapterRegistry().resolve("https://example.org/page", "direct")


def test_no_adapter_fails() -> None:
    with pytest.raises(AdapterError, match="No installed adapter") as error:
        AdapterRegistry().resolve("https://example.org/page?token=secret")
    assert "secret" not in str(error.value)


def test_plugin_entry_point_is_loaded(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class Plugin:
        name = "sample"
        description = "sample plugin"

        def can_handle(self, source: str) -> bool:
            return source == "sample:one"

        def discover(self, source: str) -> list[object]:
            del source
            return []

    point = SimpleNamespace(name="sample", load=lambda: Plugin)
    monkeypatch.setattr(registry_module, "entry_points", lambda **_: [point])
    registry = AdapterRegistry()
    assert registry.get("sample").description == "sample plugin"
