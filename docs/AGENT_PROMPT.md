# ArchiveLoom site-adapter implementation prompt

This file is an implementation brief for an AI coding agent. A user can open the ArchiveLoom repository in an agent, provide a target site URL and the variables below, and ask the agent to follow this document from beginning to end.

The desired result is a tested site adapter that turns an authorized website page into ArchiveLoom media items. It is not permission to start a full archive download.

## Instructions to the AI agent

You are adapting ArchiveLoom to one specific media website. Work inside the user's ArchiveLoom checkout. Do not build a second downloader and do not copy assumptions from an unrelated site.

Before making changes, read these files completely:

1. `docs/engineering-blueprint.ja.md`
2. `docs/adapters.md`
3. `docs/architecture.md`
4. `docs/responsible-use.md`
5. `CONTRIBUTING.md`
6. The adapter interfaces and models under `src/archiveloom/`

Repository instructions supplied by the user or environment take precedence over this document.

## User-supplied variables

Treat missing information as unknown. Ask only when the answer changes authorization, storage safety, authentication, destructive behavior, or the required implementation.

```text
Target site URL: <required>
Authorized content and basis: <required>
Desired scope: <dates, categories, channels, pages, or all authorized items>
Selection dimensions: <date, venue, stage, lecture, camera, etc.>
Preferred quality: <best / maximum resolution / other>
Filename format: <required format>
Output policy: <any writable path / external drive only>
Authentication: <none / existing authorized session / unknown>
Allowed work: <investigation only / implementation and tests / representative test>
Explicit permission to start the full download: <no unless the user says yes>
```

## Required workflow

### 1. Confirm scope and safety

- Verify the exact starting URL and requested collection boundaries.
- Confirm that the user states they own the media or are authorized to download it.
- Do not bypass DRM, payment, login, CAPTCHA, geographic controls, or other access controls.
- Do not begin a full download unless the user explicitly authorizes that separate action.
- Do not write test media or temporary state outside the user-approved output location.

### 2. Inspect the real site

Use read-only investigation first. Prefer, in order:

1. A documented public API or feed.
2. Structured page data, JSON-LD, or embedded application state.
3. Stable semantic HTML attributes and links.
4. The site's own browser network requests.
5. Browser automation only when the earlier methods are insufficient.

Record what was directly verified and what remains unknown. Determine:

- Supported host and path boundaries.
- Collection hierarchy and pagination termination.
- Stable item IDs.
- Title and selection dimensions.
- The route from page URL to direct, HLS, or DASH media URL.
- Required non-secret headers.
- URL expiry and re-resolution behavior.
- DRM, authentication, regional, deleted-item, empty-list, and rate-limit signals.

Never invent an endpoint, DOM selector, media ID, date, count, quality, or URL pattern.

### 3. Design the adapter

- Keep site discovery in a narrowly scoped adapter.
- Reuse ArchiveLoom for selection, parallelism, progress, retries, storage checks, FFmpeg, state, locking, and verification.
- Match only URLs that the adapter genuinely supports.
- Return normalized `MediaItem` values with deterministic stable IDs and portable filenames.
- Put site-specific groupings in `dimensions`; do not add courts, stages, dates, or similar taxonomy to the core.
- Keep credentials, cookies, signed URLs, personal data, and production responses out of Git.
- Explain and test any core change separately; do not modify the core merely to avoid implementing the adapter contract.

Use the scaffold when appropriate:

```console
archiveloom adapters scaffold example_site --output ./plugins
```

### 4. Implement tests before a bulk run

Create sanitized, deterministic fixtures and tests for at least:

- URL matching and rejection.
- Normal discovery.
- Multiple pages or cursors when applicable.
- Duplicate stable IDs.
- Empty collections.
- Malformed or changed upstream data.
- Rate limiting and bounded retries where applicable.
- Safe filename generation and secret redaction.
- DRM or unsupported stream detection when the site exposes those signals.

Run the repository's formatter, linter, type checker, test suite, package check, and documentation check. Do not claim platform support that was not verified.

### 5. Validate in increasing-risk stages

Use this order and stop at the user's authorized level:

1. Unit tests with sanitized fixtures.
2. Adapter discovery through `archiveloom inspect`.
3. `archiveloom download <URL> --output <PATH> --check-only`.
4. One representative download only when explicitly authorized.
5. A full collection run only when separately and explicitly authorized.

Verify that discovered counts, labels, filenames, protocols, and exclusions match the inspected source. Do not describe an adapter as complete when only fixture tests passed.

### 6. Hand the result to the user

Report the following separately:

- Verified facts, with the investigation time where external state can change.
- Unverified or unsupported behavior.
- Files added or changed.
- Test and check results.
- Exact adapter installation command.
- Exact `inspect` command.
- Exact `--check-only` command.
- Exact user-controlled download command.
- Safe recovery instructions for interruption or upstream changes.

Do not include cookies, tokens, signed query strings, or other secrets in the report.

## Completion gate

The task is complete only when:

- The adapter recognizes only its intended site scope.
- Discovery is bounded and does not silently interpret schema changes as an empty result.
- Results use stable IDs, portable filenames, and useful selection dimensions.
- Tests cover normal and failure paths without committing sensitive data.
- `inspect` and `--check-only` have been exercised against the authorized site when live validation is allowed.
- The user receives reproducible installation and execution commands.
- Full downloading remains under explicit user control.

If the site cannot be supported safely or reliably, stop and explain the verified blocker. Do not bypass it.
