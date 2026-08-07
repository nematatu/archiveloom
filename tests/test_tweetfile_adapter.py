from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from archiveloom.adapters.base import AdapterError
from archiveloom.adapters.tweetfile import TweetFileAdapter
from archiveloom.models import Protocol


def response(data: dict[str, object]) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "data": data})


def root_payload(*, short_link: str = "channel1", status: str = "0") -> dict[str, object]:
    return {
        "rules": {"status": status},
        "info": {
            "netDiskInfo": {
                "name": "Example root.mov",
                "isFolder": False,
                "guid": "root-guid",
                "landingPage": "root001",
                "fileUrl": "https://vid.fun800.click/root/playlist.m3u8",
                "length": "60",
                "fileSize": 1_000,
            },
            "extraInfo": {"externalLinks": short_link, "sortOrder": "2"},
        },
    }


def item_payload(short_link: str, number: int) -> dict[str, object]:
    return {
        "rules": {"status": "0"},
        "info": {
            "netDiskInfo": {
                "name": f"Example {number}.mov",
                "isFolder": False,
                "guid": f"guid-{number}",
                "landingPage": short_link,
                "fileUrl": f"https://vid.fun800.click/item-{number}/playlist.m3u8",
                "length": str(60 + number),
                "fileSize": 1_000 + number,
            },
            "extraInfo": {},
        },
    }


MASTER = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=640x360
360p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=1280x720
720p/video.m3u8
"""
MEDIA = """#EXTM3U
#EXT-X-TARGETDURATION:10
#EXTINF:10,
segment-1.ts
#EXT-X-ENDLIST
"""


def normal_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/getInfo"):
        short_link = request.url.params["externalLinks"]
        if short_link == "root001":
            return response(root_payload())
        number = {"item001": 1, "item002": 2}[short_link]
        return response(item_payload(short_link, number))
    if request.url.path.endswith("/list_by_links_page"):
        page = int(request.url.params["pageNo"])
        items = (
            [{"id": "101", "landingPage": "item001", "isFolder": False}]
            if page == 1
            else [{"id": "102", "landingPage": "item002", "isFolder": False}]
        )
        return response({"list": items, "total": 2})
    if request.url.host == "vid.fun800.click" and request.url.path.endswith("playlist.m3u8"):
        return httpx.Response(200, text=MASTER)
    if request.url.host == "vid.fun800.click" and request.url.path.endswith("720p/video.m3u8"):
        return httpx.Response(200, text=MEDIA)
    raise AssertionError(f"Unexpected request path: {request.url.path}")


def adapter_for(handler: Callable[[httpx.Request], httpx.Response]) -> TweetFileAdapter:
    return TweetFileAdapter(transport=httpx.MockTransport(handler), sleep=lambda _: None)


@pytest.mark.parametrize(
    "source",
    [
        "http://twimg.tweetfile.com/root001",
        "https://tweetfile.com/root001",
        "https://twimg.tweetfile.com/",
        "https://twimg.tweetfile.com/a/b",
        "https://user:secret@twimg.tweetfile.com/root001",
    ],
)
def test_rejects_urls_outside_narrow_scope(source: str) -> None:
    adapter = adapter_for(normal_handler)
    assert not adapter.can_handle(source)
    with pytest.raises(AdapterError):
        adapter.discover(source)


def test_discovers_pages_and_selects_highest_hls_variant() -> None:
    items = adapter_for(normal_handler).discover("https://twimg.tweetfile.com/root001")

    assert [item.stable_id for item in items] == ["tweetfile:101", "tweetfile:102"]
    assert [item.filename for item in items] == ["tweetfile_101.mp4", "tweetfile_102.mp4"]
    assert all(item.protocol is Protocol.HLS for item in items)
    assert all(item.media_url.endswith("/720p/video.m3u8") for item in items)
    assert items[0].duration_seconds == 61
    assert items[0].dimensions == {"position": "001"}
    assert items[0].metadata["selected_resolution"] == "1280x720"


def test_empty_collection_is_not_silent_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getInfo"):
            return response(root_payload())
        return response({"list": [], "total": 0})

    with pytest.raises(AdapterError, match="empty"):
        adapter_for(handler).discover("https://twimg.tweetfile.com/root001")


def test_duplicate_ids_are_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getInfo"):
            return response(root_payload())
        return response(
            {
                "list": [
                    {"id": "101", "landingPage": "item001", "isFolder": False},
                    {"id": "101", "landingPage": "item002", "isFolder": False},
                ],
                "total": 2,
            }
        )

    with pytest.raises(AdapterError, match="duplicate stable ID"):
        adapter_for(handler).discover("https://twimg.tweetfile.com/root001")


def test_changed_api_shape_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return response({"rules": {"status": "0"}, "info": []})

    with pytest.raises(AdapterError, match="changed shape"):
        adapter_for(handler).discover("https://twimg.tweetfile.com/root001")


def test_password_protected_link_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return response(root_payload(status="4"))

    with pytest.raises(AdapterError, match="password protected"):
        adapter_for(handler).discover("https://twimg.tweetfile.com/root001")


def test_rate_limit_retries_are_bounded_and_respect_retry_after() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/getInfo") and calls == 0:
            calls += 1
            return httpx.Response(429, headers={"Retry-After": "0"})
        return normal_handler(request)

    adapter = TweetFileAdapter(
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    )
    assert len(adapter.discover("https://twimg.tweetfile.com/root001")) == 2
    assert sleeps == [0.0]


def test_encrypted_hls_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "vid.fun800.click" and request.url.path.endswith("720p/video.m3u8"):
            return httpx.Response(
                200,
                text='#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI="key"\n#EXTINF:10,\na.ts\n',
            )
        return normal_handler(request)

    with pytest.raises(AdapterError, match="encryption/DRM"):
        adapter_for(handler).discover("https://twimg.tweetfile.com/root001")
