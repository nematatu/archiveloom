<p align="center">
  <img src="assets/brand/logo.svg" width="520" alt="ArchiveLoom logo">
</p>

<p align="center"><strong>Weave web media into reliable local archives.</strong></p>

<p align="center">
  <a href="docs/README.ja.md">日本語</a> ·
  <a href="https://nematatu.github.io/archiveloom/">Documentation</a> ·
  <a href="docs/installation.md">Installation</a> ·
  <a href="docs/usage.md">Usage</a> ·
  <a href="docs/adapters.md">Build an adapter</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <a href="https://github.com/nematatu/archiveloom/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/nematatu/archiveloom/ci.yml?branch=main&style=flat-square&label=CI"></a>
  <a href="https://github.com/nematatu/archiveloom/releases"><img alt="Release" src="https://img.shields.io/github/v/release/nematatu/archiveloom?include_prereleases&style=flat-square"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-6C63FF?style=flat-square">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-2EA44F?style=flat-square"></a>
  <img alt="Alpha" src="https://img.shields.io/badge/status-alpha-F59E0B?style=flat-square">
</p>

> [!IMPORTANT]
> ArchiveLoom is in alpha. Its safety model and plugin API are usable, but the first stable release and signed standalone binaries are still on the roadmap.

## What ArchiveLoom is — and is not

**ArchiveLoom is a reusable engine for building reliable bulk media downloaders. It is not a universal website scraper.**

Its purpose is to stop every site integration from reimplementing the difficult operational parts: collection selection, bounded parallelism, restart handling, fixed progress, external-drive safeguards, FFmpeg execution, and output verification. Site-specific discovery stays in a small adapter that can be developed and reviewed independently.

| What you give ArchiveLoom | Does it work out of the box? |
|---|---|
| A direct media, HLS (`.m3u8`), or DASH (`.mpd`) URL | **Yes** |
| An ArchiveLoom JSON collection containing known media URLs | **Yes** |
| An ordinary webpage containing an unknown player or media catalog | **Only with a compatible site adapter** |
| DRM-protected media or access-control bypass | **No, and this is intentionally unsupported** |

If a site adapter does not exist, a developer—or an AI coding agent following the [engineering blueprint](docs/engineering-blueprint.ja.md)—must first inspect that site's authorized public interface and implement its discovery logic. Installing ArchiveLoom alone does not make arbitrary webpage URLs downloadable.

ArchiveLoom is a cross-platform CLI/TUI for archiving **collections** of media you own or are authorized to download. It separates a dependable download engine from small, reviewable site adapters, so one site changing does not destabilize the rest of the application.

It is designed for the awkward jobs that a browser download button does not solve: dozens of long recordings, multiple dates or categories, resumable overnight runs, external-drive-only storage, clear progress, and deterministic verification.

<p align="center">
  <img src="assets/screenshots/dashboard.svg" width="900" alt="ArchiveLoom fixed terminal dashboard">
</p>

## Why ArchiveLoom?

- **Collections first** — discover, review, filter, and archive many items as one run.
- **Adapter driven** — site knowledge lives in plugins, not in the core engine.
- **Safe by default** — no silent overwrite, no internal-disk fallback, no DRM bypass.
- **Restart-friendly** — verified files are skipped; direct downloads attempt HTTP Range resume.
- **Observable** — fixed terminal progress, per-item status, bounded retries, and explicit exit codes.
- **Verified output** — files become final only after `ffprobe` can read their media streams.
- **Cross-platform** — macOS, Windows, and Linux are tested in CI.
- **Multilingual foundation** — English and Japanese core prompts plus maintained documentation.
- **Extensible** — create an installable adapter package with one command.

## Quick start

### 1. Install FFmpeg

ArchiveLoom uses `ffmpeg` and `ffprobe` for HLS/DASH and final verification. See the [OS-specific installation guide](docs/installation.md).

### 2. Install ArchiveLoom from GitHub

With [`pipx`](https://pipx.pypa.io/):

```console
pipx install git+https://github.com/nematatu/archiveloom.git
```

With [`uv`](https://docs.astral.sh/uv/):

```console
uv tool install git+https://github.com/nematatu/archiveloom.git
```

### 3. Check the machine

```console
archiveloom doctor --output /path/to/archive
```

Require a physically external target when ArchiveLoom can verify it:

```console
archiveloom doctor --output /path/to/archive --external-only
```

### 4. Inspect before writing

```console
archiveloom inspect "https://cdn.example.org/event/master.m3u8"
archiveloom download "https://cdn.example.org/event/master.m3u8" \
  --output /path/to/archive \
  --check-only
```

### 5. Archive

```console
archiveloom download "https://cdn.example.org/event/master.m3u8" \
  --output /path/to/archive
```

For a collection manifest with keyboard selection:

```console
archiveloom download collection.json \
  --output /path/to/archive \
  --interactive \
  --jobs 2
```

Use `↑/↓` or `j/k` to move, `Space` to toggle, `a` to select all, and `Enter` to continue.

## Collection manifests

ArchiveLoom includes a portable JSON adapter for teams that already know the media URLs:

```json
{
  "version": 1,
  "items": [
    {
      "id": "day-1-stage-a",
      "title": "Day 1 · Stage A",
      "url": "https://cdn.example.org/day-1/stage-a/master.m3u8",
      "protocol": "hls",
      "filename": "2026-07-23_stage-a.mp4",
      "dimensions": {"date": "2026-07-23", "stage": "A"}
    }
  ]
}
```

See [examples/collection.json](examples/collection.json) and the [manifest reference](docs/usage.md#collection-manifest).

## Site adapters

Adapters discover normalized media items. They can represent sports courts, conference stages, lectures, cameras, playlists, or any other site-specific hierarchy without adding those assumptions to the core.

```console
archiveloom adapters list
archiveloom adapters scaffold my_site --output ./plugins
```

Third-party adapters are normal Python packages registered through the `archiveloom.adapters` entry-point group. Read [Building an adapter](docs/adapters.md) before opening a pull request.

## Platform support

| Capability | macOS | Windows | Linux |
|---|:---:|:---:|:---:|
| Python package | ✅ | ✅ | ✅ |
| Direct HTTP(S) media | ✅ | ✅ | ✅ |
| HLS/DASH through FFmpeg | ✅ | ✅ | ✅ |
| Interactive selector | ✅ | ✅ | ✅ |
| External-disk verification | `diskutil` | PowerShell | `findmnt` + `lsblk` |
| CI tests | ✅ | ✅ | ✅ |
| Standalone signed binary | Planned | Planned | Planned |

External-disk detection is intentionally conservative. `--external-only` fails closed when ArchiveLoom cannot prove the selected target is external. Windows and Linux behavior is covered by mocked platform tests locally, and the [first hosted matrix run](https://github.com/nematatu/archiveloom/actions/runs/30329505144) passed on all three operating systems.

## Project layout

```text
archiveloom/
├── src/archiveloom/       Core engine, TUI, adapters, platform checks
├── tests/                 Unit and integration tests
├── docs/                  English and Japanese documentation
├── examples/              Safe example manifests and plugin samples
├── assets/                Brand assets and terminal screenshots
├── scripts/               Maintainer and release utilities
└── .github/               CI, releases, issue forms, PR template
```

## Responsible use

ArchiveLoom is for content you own, public-domain content, or content you are authorized to download. It does not bypass DRM, paywalls, authentication, or access controls. Site terms and local law still apply. See [Responsible use](docs/responsible-use.md).

## Documentation

- [Installation](docs/installation.md)
- [Usage and exit codes](docs/usage.md)
- [Architecture](docs/architecture.md)
- [AI・実装者向け設計ブループリント（日本語）](docs/engineering-blueprint.ja.md)
- [Adapter development](docs/adapters.md)
- [Responsible use](docs/responsible-use.md)
- [Security policy](SECURITY.md)
- [Roadmap](ROADMAP.md)

## Community

Bug reports, adapter proposals, documentation improvements, translations, and platform testing are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md) first.

## License

ArchiveLoom is available under the [MIT License](LICENSE). Site adapters and bundled release dependencies may have their own licenses; contributors must document them.
