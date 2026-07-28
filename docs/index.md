# ArchiveLoom

ArchiveLoom is a cross-platform engine for building reliable bulk media downloaders for sources you are authorized to download. **It is not a universal website scraper.**

It can download direct media, HLS, and DASH URLs, or a JSON collection of known media URLs. An ordinary webpage works only when a compatible site adapter knows how to discover that site's media. DRM and access-control bypass are intentionally unsupported.

The project's purpose is to keep site-specific discovery small while reusing the difficult operational parts: selection, bounded parallelism, restart handling, external-drive safeguards, FFmpeg execution, fixed progress, and final verification.

## Start here

- [Installation](installation.md)
- [Usage](usage.md)
- [Adapters](adapters.md)
- [Architecture](architecture.md)
- [Responsible use](responsible-use.md)
- [日本語 README](README.ja.md)

!!! warning "Early development"
    ArchiveLoom is currently alpha software. Review an adapter's output with `inspect` or `download --check-only` before starting a large archive job.
