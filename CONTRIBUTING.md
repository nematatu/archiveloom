# Contributing to ArchiveLoom

Thank you for improving ArchiveLoom. Contributions may be code, adapter research, tests, translations, documentation, design, or platform verification.

## Before you start

1. Search existing issues and pull requests.
2. Use a feature request for a cross-cutting design change.
3. Use the adapter request form before implementing support for a new site.
4. Do not post credentials, cookies, signed URLs, personal data, or copyrighted media fixtures.
5. Read the [Code of Conduct](CODE_OF_CONDUCT.md) and [Responsible use](docs/responsible-use.md).

## Development setup

```console
git clone https://github.com/nematatu/archiveloom.git
cd archiveloom
python -m venv .venv
```

Activate the virtual environment, then:

```console
python -m pip install --upgrade pip
python -m pip install -e ".[dev,docs]"
pre-commit install
```

## Checks

Run before opening a pull request:

```console
ruff check .
ruff format --check .
mypy src
pytest --cov=archiveloom --cov-report=term-missing
python -m build
```

CI repeats these checks across supported Python versions and operating systems.

## Pull requests

- Keep one coherent change per pull request.
- Add tests for behavior changes and bug fixes.
- Update English documentation first and Japanese documentation when user-visible behavior changes.
- Add a changelog entry under `Unreleased`.
- Avoid drive-by formatting or dependency churn.
- Explain what was verified and what remains unverified.
- Never weaken storage, path, TLS, authentication, DRM, or subprocess safety checks to make one site pass.

## Adapter contributions

Site adapters require extra review because sites change and automation can create operational or legal risk. Follow [docs/adapters.md](docs/adapters.md). Maintainers may recommend a separately distributed plugin instead of a built-in adapter.

## Translations

Runtime strings live in `src/archiveloom/i18n.py`. Documentation translations live under `docs/`. A translation must:

- Preserve commands, option names, paths, warnings, and safety meaning
- Link back to the English canonical page
- Include a reviewer who understands the target language when practical
- Avoid claiming features that are only planned

## Reporting security issues

Do not open a public issue for a vulnerability involving credential exposure, path escape, command execution, unsafe redirects, or overwrite. Follow [SECURITY.md](SECURITY.md).

## Maintainer response

ArchiveLoom is maintained on a best-effort basis. A respectful report with a minimal reproduction, sanitized logs, OS, Python version, FFmpeg version, and ArchiveLoom version is the fastest path to a useful response.
