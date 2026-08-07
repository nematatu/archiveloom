# Changelog

All notable changes are documented here. ArchiveLoom follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Built-in Gofile adapter for authorized `gofile.io/d/<content-id>` folders through Gofile's
  official token-authenticated API, with bounded recursive discovery, media-only filtering,
  collision-resistant filenames, rate-limit handling, and fail-closed credential and URL checks.
- Built-in TweetFile adapter for authorized public `twimg.tweetfile.com` collections, including
  bounded pagination, deterministic filenames, highest-variant HLS selection, and fail-closed
  access, schema, redirect, encryption, and CDN checks.

### Fixed

- Validate exact sizes supplied for direct downloads, reuse fully transferred partial files, and
  reject mismatched `Content-Range` responses before appending resumed bytes.
- Render site-provided titles, filenames, and selection dimensions as plain terminal text instead
  of interpreting Rich/Textual markup.

## [0.1.0] - 2026-07-28

### Added

- Cross-platform CLI and interactive media selector.
- Direct HTTP(S), HLS, DASH, and JSON manifest adapters.
- Adapter plugin entry points and scaffold command.
- External-storage checks for macOS, Windows, and Linux.
- Resumable direct downloads, fixed progress UI, run locking, and ffprobe verification.
- English and Japanese documentation.
- Initial public alpha packaging, CI, CodeQL, and documentation site.
