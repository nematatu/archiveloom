from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

import archiveloom.adapters.gofile as gofile_module
from archiveloom.adapters.base import AdapterError
from archiveloom.adapters.gofile import GofileAdapter
from archiveloom.models import Protocol


def api_response(data: dict[str, object], *, status: str = "ok") -> httpx.Response:
    return httpx.Response(200, json={"status": status, "data": data})


def folder(
    folder_id: str,
    name: str,
    children: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "id": folder_id,
        "type": "folder",
        "name": name,
        "childrenCount": len(children),
        "children": {str(child["id"]): child for child in children},
    }


def media_file(
    file_id: str,
    name: str,
    *,
    mimetype: str = "video/mp4",
    link_host: str = "store1.gofile.io",
) -> dict[str, object]:
    return {
        "id": file_id,
        "type": "file",
        "name": name,
        "mimetype": mimetype,
        "link": f"https://{link_host}/download/web/{file_id}/{name}",
        "size": 1_024,
        "createTime": 1_700_000_000,
    }


def adapter_for(handler: Callable[[httpx.Request], httpx.Response]) -> GofileAdapter:
    return GofileAdapter(
        token="authorized-token",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )


@pytest.mark.parametrize(
    "source",
    [
        "http://gofile.io/d/ABC123",
        "https://example.org/d/ABC123",
        "https://gofile.io/ABC123",
        "https://gofile.io/d/",
        "https://gofile.io/d/a/b",
        "https://user:secret@gofile.io/d/ABC123",
    ],
)
def test_rejects_urls_outside_narrow_scope(source: str) -> None:
    adapter = adapter_for(lambda _: pytest.fail("unexpected request"))
    assert not adapter.can_handle(source)
    with pytest.raises(AdapterError):
        adapter.discover(source)


def test_requires_official_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARCHIVELOOM_GOFILE_TOKEN", raising=False)
    adapter = GofileAdapter(transport=httpx.MockTransport(lambda _: pytest.fail("unexpected")))

    with pytest.raises(AdapterError, match="ARCHIVELOOM_GOFILE_TOKEN"):
        adapter.discover("https://gofile.io/d/ABC123")


@pytest.mark.parametrize("token", ["line\nbreak", "cookie;injection", "全角トークン"])
def test_rejects_malformed_token(token: str) -> None:
    adapter = GofileAdapter(
        token=token,
        transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request")),
    )

    with pytest.raises(AdapterError, match="malformed"):
        adapter.discover("https://gofile.io/d/ABC123")


def test_discovers_media_recursively_and_filters_other_files() -> None:
    requests: list[httpx.Request] = []
    subfolder = {"id": "folder-sub", "type": "folder", "name": "Round 1"}
    text_file = {
        "id": "notes-001",
        "type": "file",
        "name": "notes.txt",
        "mimetype": "text/plain",
        "link": "https://store1.gofile.io/download/web/notes-001/notes.txt",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer authorized-token"
        if request.url.path.endswith("/ABC123"):
            return api_response(
                folder(
                    "root-folder",
                    "Tournament",
                    [media_file("video-001", "court.mp4"), subfolder, text_file],
                )
            )
        if request.url.path.endswith("/folder-sub"):
            return api_response(
                folder(
                    "folder-sub",
                    "Round 1",
                    [media_file("audio-001", "sound.m4a", mimetype="audio/mp4")],
                )
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    items = adapter_for(handler).discover("https://gofile.io/d/ABC123?utm_source=test")

    assert [item.stable_id for item in items] == ["gofile:video-001", "gofile:audio-001"]
    assert [item.protocol for item in items] == [Protocol.DIRECT, Protocol.DIRECT]
    assert [item.filename for item in items] == [
        "gofile_video-001__court.mp4",
        "gofile_audio-001__sound.m4a",
    ]
    assert items[0].dimensions == {"folder": "Tournament", "position": "0001"}
    assert items[1].dimensions == {
        "folder": "Tournament/Round 1",
        "position": "0002",
    }
    assert items[0].metadata["expected_size_bytes"] == 1_024
    assert items[0].source_url == "https://gofile.io/d/ABC123"
    assert items[0].headers == {
        "Cookie": "accountToken=authorized-token",
        "Referer": "https://gofile.io/",
    }
    assert len(requests) == 2


def test_long_duplicate_names_keep_stable_ids_in_unique_filenames() -> None:
    long_name = f"{'match-' * 60}.mp4"

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return api_response(
            folder(
                "root-folder",
                "Root",
                [
                    media_file("video-001", long_name),
                    media_file("video-002", long_name),
                ],
            )
        )

    items = adapter_for(handler).discover("https://gofile.io/d/ABC123")

    assert len({item.filename for item in items}) == 2
    assert items[0].filename.startswith("gofile_video-001__")
    assert items[1].filename.startswith("gofile_video-002__")
    assert all(len(item.filename) <= 180 for item in items)


def test_paginates_until_reported_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gofile_module, "PAGE_SIZE", 1)

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        child = media_file(f"video-00{page}", f"video-{page}.mp4")
        data = folder("root-folder", "Root", [child])
        data["childrenCount"] = 2
        return api_response(data)

    items = adapter_for(handler).discover("https://gofile.io/d/ABC123")

    assert [item.stable_id for item in items] == ["gofile:video-001", "gofile:video-002"]


def test_duplicate_pagination_ids_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gofile_module, "PAGE_SIZE", 1)

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        data = folder("root-folder", "Root", [media_file("video-001", "video.mp4")])
        data["childrenCount"] = 2
        return api_response(data)

    with pytest.raises(AdapterError, match="duplicate children"):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")


@pytest.mark.parametrize(
    ("status", "message"),
    [
        ("error-notFound", "not found"),
        ("error-notPremium", "Premium"),
        ("error-passwordRequired", "Password-protected"),
        ("error-notPublic", "private"),
    ],
)
def test_known_api_failures_are_clear(status: str, message: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return api_response({}, status=status)

    with pytest.raises(AdapterError, match=message):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")


def test_password_flag_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        data = folder("root-folder", "Root", [])
        data.update({"password": True, "passwordStatus": "passwordWrong"})
        return api_response(data)

    with pytest.raises(AdapterError, match="Password-protected"):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")


def test_inaccessible_content_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        data = folder("root-folder", "Root", [])
        data["canAccess"] = False
        return api_response(data)

    with pytest.raises(AdapterError, match="not accessible"):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")


@pytest.mark.parametrize(
    ("flag", "message"),
    [
        ("isFrozen", "cold storage"),
        ("overloaded", "server is busy"),
        ("isDeleted", "deleted file"),
    ],
)
def test_unavailable_files_fail_closed(flag: str, message: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        child = media_file("video-001", "a.mp4")
        child[flag] = True
        return api_response(folder("root-folder", "Root", [child]))

    with pytest.raises(AdapterError, match=message):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")


def test_rate_limit_retries_are_bounded_and_respect_retry_after() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return api_response(folder("root-folder", "Root", [media_file("video-001", "a.mp4")]))

    adapter = GofileAdapter(
        token="authorized-token",
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    )
    assert len(adapter.discover("https://gofile.io/d/ABC123")) == 1
    assert calls == 2
    assert sleeps == [0.0]


def test_api_response_size_is_bounded_while_streaming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gofile_module, "MAX_RESPONSE_BYTES", 10)

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, content=b"x" * 11)

    with pytest.raises(AdapterError, match="safe size limit"):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")


def test_folder_item_limit_applies_without_reported_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gofile_module, "MAX_ITEMS", 1)

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        data = folder(
            "root-folder",
            "Root",
            [media_file("video-001", "a.mp4"), media_file("video-002", "b.mp4")],
        )
        data.pop("childrenCount")
        return api_response(data)

    with pytest.raises(AdapterError, match="folder exceeds"):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")


def test_redirected_api_request_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(302, headers={"Location": "https://example.org/"})

    with pytest.raises(AdapterError, match="redirected"):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")


def test_download_url_outside_gofile_is_rejected_without_leaking_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return api_response(
            folder(
                "root-folder",
                "Root",
                [media_file("video-001", "a.mp4", link_host="evil.example")],
            )
        )

    with pytest.raises(AdapterError) as error:
        adapter_for(handler).discover("https://gofile.io/d/ABC123")
    assert "authorized-token" not in str(error.value)


def test_empty_media_collection_is_not_silent_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        data = folder(
            "root-folder",
            "Root",
            [
                {
                    "id": "notes-001",
                    "type": "file",
                    "name": "notes.txt",
                    "mimetype": "text/plain",
                    "link": "https://store1.gofile.io/download/web/notes-001/notes.txt",
                }
            ],
        )
        return api_response(data)

    with pytest.raises(AdapterError, match="no supported video or audio"):
        adapter_for(handler).discover("https://gofile.io/d/ABC123")
