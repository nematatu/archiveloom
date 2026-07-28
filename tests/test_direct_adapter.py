import pytest

from archiveloom.adapters.base import AdapterError
from archiveloom.adapters.direct import DirectAdapter
from archiveloom.models import Protocol


@pytest.mark.parametrize(
    ("url", "protocol", "filename"),
    [
        ("https://EXAMPLE.org/media/clip.mp4?token=secret", Protocol.DIRECT, "clip.mp4"),
        ("https://example.org/live/master.m3u8", Protocol.HLS, "master.mp4"),
        ("https://example.org/live/manifest.mpd", Protocol.DASH, "manifest.mp4"),
    ],
)
def test_direct_adapter_discovers_known_media(url: str, protocol: Protocol, filename: str) -> None:
    item = DirectAdapter().discover(url)[0]
    assert item.protocol is protocol
    assert item.filename == filename
    assert item.media_url == url
    assert "secret" not in item.stable_id


@pytest.mark.parametrize("source", ["file:///tmp/a.mp4", "https://example.org/page", "not-a-url"])
def test_direct_adapter_rejects_unknown_sources(source: str) -> None:
    adapter = DirectAdapter()
    assert not adapter.can_handle(source)
    with pytest.raises(AdapterError):
        adapter.discover(source)
