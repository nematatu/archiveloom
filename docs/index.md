# ArchiveLoom

ArchiveLoom is the cross-platform bulk-download core generalized from an InHigh TV-specific downloader and released as open-source software. It provides reusable selection, parallel download, restart, progress, storage-safety, FFmpeg, and verification behavior.

The project is working toward a simple experience: give ArchiveLoom a supported video-site page URL, review the discovered videos, and download your selection. Because each site exposes its catalog and player differently, an ordinary webpage currently works only when a compatible site adapter exists. DRM and access-control bypass are intentionally unsupported.

The project's purpose is to keep site-specific discovery small while reusing the difficult operational parts: selection, bounded parallelism, restart handling, external-drive safeguards, FFmpeg execution, fixed progress, and final verification.

## Unknown site? Give it to an AI coding agent

Open this repository in your coding agent, provide the target site URL, and tell it to read the [site-adapter agent prompt](AGENT_PROMPT.md). The prompt directs the agent through site investigation, adapter implementation, tests, dry-run validation, and a user-controlled handoff. The user—not the agent—starts the full archive run unless explicitly authorized otherwise.

This AI-assisted adapter step is the current bridge from an unknown webpage to ArchiveLoom's reusable downloader. The long-term goal is to make more URLs work immediately as the official and community adapter catalog grows.

InHigh TV is the concrete reference behind this architecture. The separate public downloader is already implemented and used; its site discovery has simply not yet been packaged as an ArchiveLoom adapter. See the [InHigh TV case study](case-study-inhigh-tv.md) for the verified boundary and migration example.

## Can I use it right now?

Yes, if you already have a direct media, HLS, or DASH URL:

```console
archiveloom download "https://example.com/video/master.m3u8" \
  --output "/path/to/external-drive/archive" \
  --check-only
```

You can also put several known URLs in a [collection file](usage.md#collection-manifest) and choose them interactively:

```console
archiveloom download collection.json \
  --output "/path/to/external-drive/archive" \
  --interactive \
  --jobs 2
```

If all you have is a normal website page, check whether a compatible adapter exists. If it does not, the site's discovery logic must be implemented first. The [adapter guide](adapters.md) explains that boundary.

## Start here

- [Installation](installation.md)
- [Usage](usage.md)
- [Adapters](adapters.md)
- [Architecture](architecture.md)
- [AI site-adapter prompt](AGENT_PROMPT.md)
- [InHigh TV case study](case-study-inhigh-tv.md)
- [Responsible use](responsible-use.md)
- [日本語 README](README.ja.md)

!!! warning "Early development"
    ArchiveLoom is currently alpha software. Review an adapter's output with `inspect` or `download --check-only` before starting a large archive job.
