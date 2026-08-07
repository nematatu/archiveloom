# Usage

## Command map

```text
archiveloom doctor             Diagnose the runtime and storage target
archiveloom adapters list      List built-in and installed adapters
archiveloom adapters scaffold  Create a third-party adapter project
archiveloom inspect            Discover and display items without downloading
archiveloom download           Select, download, verify, and record items
```

Use `archiveloom COMMAND --help` for the current option list.

## Safe preflight

```console
archiveloom doctor --output /archive --external-only
archiveloom download collection.json --output /archive --check-only
```

`--check-only` discovers and prints media items but does not create the output directory, state, logs, or partial files.

## Direct media

```console
archiveloom download "https://cdn.example.org/video.mp4" --output /archive
archiveloom download "https://cdn.example.org/master.m3u8" --output /archive
archiveloom download "https://cdn.example.org/manifest.mpd" --output /archive
```

ArchiveLoom copies compatible HLS/DASH audio and video streams with FFmpeg. It does not claim that every manifest, codec, encryption mode, subtitle layout, or multi-period stream is supported.

## Collection manifest

The local JSON manifest has a versioned schema:

```json
{
  "version": 1,
  "title": "My archive",
  "items": [
    {
      "id": "stable-id",
      "title": "Human title",
      "url": "https://cdn.example.org/media/master.m3u8",
      "protocol": "hls",
      "filename": "safe-output.mp4",
      "duration_seconds": 7200,
      "headers": {"Referer": "https://example.org/"},
      "dimensions": {"date": "2026-07-23", "stage": "A"}
    }
  ]
}
```

Required fields per item are `title` and an HTTP(S) `url`. Supported protocol values are `direct`, `hls`, and `dash`. Header keys and values containing CR or LF are rejected. Do not place long-lived secrets in a manifest committed to Git.

## Interactive selection

```console
archiveloom download collection.json --output /archive --interactive
```

| Key | Action |
|---|---|
| `↑`, `k` | Move up |
| `↓`, `j` | Move down |
| `Space` | Toggle current item |
| `a` | Select or clear all |
| `Enter` | Continue |
| `q` | Cancel |

The terminal is restored after normal exit, exceptions, and Ctrl+C by Textual.

## State and restart

ArchiveLoom stores operational files under the selected target:

```text
/archive/
├── final-media.mp4
└── .archiveloom/
    ├── state.json
    ├── run.lock
    └── partial/
```

- A final file is skipped only after `ffprobe` can read an audio or video stream.
- Direct HTTP downloads try Range resume when a partial file exists and append only after validating the server's `Content-Range` start, end, response length, and known total size. When an adapter supplies an exact expected size, ArchiveLoom validates it and can verify a fully transferred partial without downloading it again. A complete-sized partial that fails verification is preserved with `.invalid` in its name so the next run can start cleanly. ETag/Last-Modified validation is planned for 0.2, so the server may still force a clean restart and the final `ffprobe` check remains mandatory.
- An existing final file that fails verification is never overwritten automatically; move or remove it explicitly after inspection.
- HLS/DASH retries restart the current item in the initial alpha.
- A per-output lock prevents two writers from using the same directory.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Requested mode completed successfully |
| 2 | Invalid command input or empty selection |
| 3 | Environment or dependency check failed |
| 4 | Queue finished with failed/unsupported items |
| 6 | Adapter or site contract mismatch |
| 7 | Reserved for fatal storage failures |
| 10 | Reserved for an unclassified internal error |
| 130 | User interrupted the run |

## Languages

ArchiveLoom detects Japanese locales automatically.

```console
archiveloom --lang en doctor
archiveloom --lang ja doctor
```

Set `ARCHIVELOOM_LANG=en` or `ARCHIVELOOM_LANG=ja` for a persistent default.
