# Building an adapter

Adapters turn a site-specific collection into ArchiveLoom's normalized `MediaItem` model. Keep them small, documented, and independently testable.

If you want an AI coding agent to investigate a target site and build the adapter, start with the complete [site-adapter agent prompt](AGENT_PROMPT.md). It links this contract with the investigation, safety, testing, and handoff requirements.

## Scaffold

```console
archiveloom adapters scaffold example_site --output ./plugins
cd plugins/archiveloom-example-site
python -m pip install -e .
archiveloom adapters list
```

The package registers an entry point under `archiveloom.adapters`.

## Contract

```python
class ExampleAdapter:
    name = "example_site"
    description = "Example Site public archives"

    def can_handle(self, source: str) -> bool:
        return source.startswith("https://media.example.org/events/")

    def discover(self, source: str) -> list[MediaItem]: ...
```

Each `MediaItem` needs:

- A stable ID that does not include an expiring signature
- A human title
- An HTTP(S) media URL
- `direct`, `hls`, or `dash` protocol
- A portable filename
- The page or manifest source URL

Optional duration and dimensions improve progress and selection.

## Rules

1. Match only the hosts and paths the adapter genuinely supports.
2. Prefer a documented API, then the site's own read API, embedded JSON, stable HTML, and finally browser automation.
3. Never commit cookies, tokens, signed URLs, personal data, or production responses.
4. Use bounded timeouts, pagination, retry-after, and a descriptive user agent.
5. Detect DRM and unsupported stream layouts before download.
6. Do not put dates, courts, lectures, stages, or other site taxonomy into the core.
7. Redact secrets from exceptions and fixtures.
8. Provide normal, malformed, empty, pagination, and changed-schema tests.

## Test fixture example

```python
def test_discovers_collection(fake_api_response):
    adapter = ExampleAdapter()
    items = adapter.discover("https://media.example.org/events/42")
    assert [item.stable_id for item in items] == ["event-42-stage-a"]
```

## Proposal checklist

- [ ] The site and authorization model are described
- [ ] URL matching is narrow
- [ ] Discovery has timeouts and pagination limits
- [ ] Credentials are not stored in Git or state
- [ ] Stable IDs and safe filenames are deterministic
- [ ] HLS/DASH capabilities and DRM behavior are documented
- [ ] Fixtures are anonymized
- [ ] Tests pass on macOS, Windows, and Linux where applicable
- [ ] User-facing documentation is updated
