# Translations

English is the source language for code, CLI help, and technical documentation. Japanese is maintained as the first full translation.

## Adding a language

1. Add the locale key and user-facing messages to `src/archiveloom/i18n.py`.
2. Add a translated README under `docs/README.<locale>.md`.
3. Translate installation and safety notes before translating secondary pages.
4. Add CLI snapshot tests for the locale.
5. Ask a fluent reviewer to check terminology, tone, and safety instructions.

Do not silently machine-translate legal, safety, or destructive-operation text. A draft made with translation software must be marked as unreviewed until a fluent contributor approves it.
