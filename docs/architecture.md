# Architecture

ArchiveLoom uses a narrow core and explicit adapters. A site adapter discovers normalized `MediaItem` values; it never controls storage, retries, process management, verification, or the terminal UI.

```mermaid
flowchart LR
    URL["URL or manifest"] --> Registry["Adapter registry"]
    Registry --> Adapter["Site adapter"]
    Adapter --> Items["Normalized MediaItem list"]
    Items --> Select["Interactive selection"]
    Select --> Engine["Core download engine"]
    Engine --> Verify["ffprobe verification"]
    Verify --> State["Atomic final file + state"]
```

## Boundaries

### Adapters own

- URL matching
- Site/API/HTML discovery
- Pagination and stable IDs
- Media URLs, headers, expected duration, and dimensions
- Refreshing expiring URLs in future adapter API versions

### Core owns

- CLI/TUI behavior
- Path and filename safety
- Platform storage checks
- Output locking and state
- Concurrency, retries, cancellation, and progress
- FFmpeg invocation and ffprobe verification
- Atomic promotion from partial to final output

## Package layout

```text
src/archiveloom/
├── adapters/
│   ├── base.py
│   ├── registry.py
│   ├── direct.py
│   └── manifest.py
├── core/
│   ├── downloader.py
│   ├── doctor.py
│   ├── filenames.py
│   ├── locking.py
│   ├── probe.py
│   ├── progress.py
│   ├── state.py
│   └── storage.py
├── cli.py
├── i18n.py
├── models.py
└── tui.py
```

## Safety invariants

1. The core does not bypass DRM or authentication.
2. Site strings are never used as unsanitized filesystem paths.
3. Subprocesses receive argument arrays, not shell-interpolated command strings.
4. A final filename appears only after verification.
5. Temporary and state files remain under the selected output root.
6. `--external-only` never falls back to internal storage.
7. One failed item does not permanently block the remaining queue.

## Versioning

The package uses Semantic Versioning. Until 1.0, adapter interfaces can change between minor releases. Every breaking adapter change must appear in `CHANGELOG.md` and the adapter guide.
