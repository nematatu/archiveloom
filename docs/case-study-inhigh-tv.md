# Real-world case study: InHigh TV

InHigh TV is not a fictional example created to explain ArchiveLoom. ArchiveLoom was born by generalizing the reusable core of a dedicated downloader built for a real collection of long-form tournament archives.

The reference implementation is [`downloader/download_inhigh_2026.command`](https://github.com/nematatu/inhigh-tv-tools/blob/codex/interactive-download-cli/downloader/download_inhigh_2026.command) in the public `nematatu/inhigh-tv-tools` repository. The facts below were verified on July 28, 2026 after confirming that the local file and public branch contain the same Git object. The website's live catalog may change later.

## The real workload

The dedicated tool targets the 2026 inter-high-school badminton archives. Its maintained validation snapshot expects:

| Date | Archives |
|---|---:|
| 2026-07-23 | 36 |
| 2026-07-24 | 16 |
| 2026-07-25 | 36 |
| 2026-07-26 | 36 |
| 2026-07-27 | 8 |
| Total | 132 |

Individual recordings can be several hours long. A manual browser workflow makes selection, completion tracking, interruption, retries, capacity planning, and progress visibility difficult.

## What the dedicated downloader already implements

- Single or multiple date and court selection.
- Keyboard multi-select with `j/k`, arrows, `Space`, `a`, and `Enter`.
- Bounded parallel downloads, defaulting to two jobs.
- Highest available quality up to a configurable 1080p ceiling.
- Deterministic names such as `2026-07-23_01.mp4`.
- Physical external-drive validation on macOS with no internal-disk fallback.
- Partial files, state, and logs stored on the selected external drive.
- Existing MP4 validation with `ffprobe` and completed-item exclusion.
- Fixed progress, media time, speed, remaining time, and expected finish.
- Stall detection, one automatic retry, and continuation of the remaining queue.
- Graceful `Ctrl+C` handling that allows FFmpeg to finalize MP4 output.
- Preflight archive counts, duration, estimated size, and free-space checks.
- A `--check-only` path that does not start media writes.

This is an operational reference implementation, not a proposed feature list.

## Inspect the dedicated tool

The current reference implementation is available on its public branch. This is a macOS-specific tool, so its setup is different from ArchiveLoom's cross-platform installation.

```console
git clone https://github.com/nematatu/inhigh-tv-tools.git
cd inhigh-tv-tools
git switch codex/interactive-download-cli
cd downloader
./download_inhigh_2026.command --interactive --check-only
```

With `--check-only`, the tool does not start media writes. It follows this verified flow:

```text
Read the site archive catalog
  ↓
Show archive counts by date
  ↓
Validate the physical external drive and free space
  ↓
Use ffprobe to remove verified completed MP4s from the choices
  ↓
Select dates and courts with the keyboard
  ↓
Preflight HLS, quality, total duration, and estimated size
  ↓
Exit after confirming that no files were created
```

After review, the user reruns without `--check-only`; media saving starts only after the final `START` confirmation.

## What is specific to InHigh TV

The implementation reads the site's paginated archive catalog, filters the intended competition and dates, extracts court numbers, validates media identifiers, resolves public player information to HLS, selects the best variant under the quality ceiling, and estimates VOD duration and size.

Those API fields, identifiers, title patterns, and playback steps belong in an InHigh TV adapter. They must not be hard-coded into ArchiveLoom's core or reused for an unrelated site.

## What became ArchiveLoom's core

| Requirement proven by the InHigh tool | ArchiveLoom responsibility |
|---|---|
| Discover dates, courts, and media | InHigh TV adapter |
| Resolve page/player data to HLS | InHigh TV adapter |
| Select discovered items | Shared TUI plus adapter dimensions |
| Run multiple downloads | Shared execution engine |
| Show progress and completion estimates | Shared progress engine |
| Save HLS as MP4 | Shared protocol/FFmpeg layer |
| Resume safely and skip completed output | Shared state and verification |
| Require external storage | Shared platform storage checks |
| Interrupt, retry, and continue | Shared execution control |
| Validate paths and completed media | Shared safety and `ffprobe` checks |

ArchiveLoom exists so that every new site implements only discovery and media resolution, not the operational behaviors in the right-hand column.

## Current status

| Component | Status |
|---|---|
| Dedicated InHigh TV downloader | Implemented in its separate public repository |
| ArchiveLoom reusable core | Implemented; supports direct URLs and JSON collections |
| InHigh TV adapter for ArchiveLoom | Not yet ported or bundled |
| Passing an InHigh TV page URL directly to ArchiveLoom | Not currently supported |

The existence of the dedicated downloader does not mean that its site logic is already installed as an ArchiveLoom plugin.

## Concrete AI porting request

Give an AI coding agent access to both repositories and use this request:

```text
Read ArchiveLoom's docs/AGENT_PROMPT.md completely.

Target URL:
https://inhightv.sportsbull.jp/summer/competition/9

Reference implementation:
https://github.com/nematatu/inhigh-tv-tools/blob/codex/interactive-download-cli/downloader/download_inhigh_2026.command

Goal:
Port only InHigh TV-specific catalog discovery, court extraction, media lookup,
and HLS resolution into an ArchiveLoom adapter. Reuse ArchiveLoom for selection,
parallelism, progress, storage checks, FFmpeg, state, locking, and verification.

Selection dimensions: date and court
Filename format: YYYY-MM-DD_CC.mp4

Allowed work:
Investigation, implementation, sanitized fixture tests, inspect, and check-only.
Do not change or stop the existing .command process.
Do not start the full download.

Re-check the current public site instead of assuming that the reference
implementation's upstream structure is unchanged. Separate verified and
unverified findings in the handoff.
```

## Intended commands after the port

The following demonstrates the target experience after an InHigh TV adapter is installed. These commands are **not supported by ArchiveLoom v0.1.0 today**.

```console
archiveloom inspect \
  "https://inhightv.sportsbull.jp/summer/competition/9"

archiveloom download \
  "https://inhightv.sportsbull.jp/summer/competition/9" \
  --output "/path/to/external-drive/inhigh-tv-archive" \
  --external-only \
  --interactive \
  --jobs 2 \
  --check-only
```

After reviewing discovery and storage, the user removes `--check-only` to start the full run.

## What this case proves

ArchiveLoom's core requirements came from an actual bulk archive job rather than a theoretical abstraction. Keeping InHigh-specific discovery outside the core also prevents one website change from destabilizing every other adapter and the shared download engine.
