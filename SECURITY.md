# Security policy

## Supported versions

| Version | Security fixes |
|---|:---:|
| Latest `0.x` | ✅ Best effort |
| Older `0.x` | ❌ |

Before 1.0, upgrade to the latest release before reporting.

## Private reporting

Use GitHub's **Report a vulnerability** private security advisory flow for this repository. Do not open a public issue for vulnerabilities involving:

- Credential, cookie, token, or signed-URL exposure
- Shell or argument injection
- Unsafe redirects, local-network access, or protocol confusion
- Path traversal, symlink escape, or unintended overwrite
- External-only storage bypass
- Run-lock or state corruption that can damage user files
- Malicious manifests, adapter packages, or release artifacts

Include:

- ArchiveLoom version or commit
- Operating system and Python version
- FFmpeg/ffprobe version when relevant
- Minimal reproduction using non-sensitive dummy URLs and files
- Expected and actual behavior
- Security impact

Never include a real credential, private media URL, or personal data. Maintainers will acknowledge reports as time permits; no response-time guarantee is offered during alpha.

## Threat model

ArchiveLoom treats site responses, titles, manifests, filenames, URLs, headers, and third-party adapters as untrusted. The core aims to prevent path escape, shell interpolation, URL-secret logging, silent overwrite, internal-storage fallback when `--external-only` is selected, and concurrent writers.

The alpha direct downloader follows HTTP redirects and does not implement a local-network destination denylist. Use only URLs and adapters you trust; stronger redirect and network-boundary policies remain security-hardening work.

Third-party adapters execute Python code with the user's privileges. Install them only from sources you trust. Plugin discovery is not a sandbox.

## Release integrity

Until signed standalone artifacts are implemented, install from source and review the tag or commit. Future release workflows will publish checksums and provenance; the roadmap must not be read as a claim that those artifacts already exist.
