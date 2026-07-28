# ArchiveLoom

ArchiveLoom is a cross-platform, adapter-driven CLI for building reliable local media archives from sources you are authorized to download.

It separates site discovery from download execution, keeps partial files isolated, verifies completed media with `ffprobe`, and renders progress in a fixed terminal region.

## Start here

- [Installation](installation.md)
- [Usage](usage.md)
- [Adapters](adapters.md)
- [Architecture](architecture.md)
- [Responsible use](responsible-use.md)
- [日本語 README](README.ja.md)

!!! warning "Early development"
    ArchiveLoom is currently alpha software. Review an adapter's output with `inspect` or `download --check-only` before starting a large archive job.
