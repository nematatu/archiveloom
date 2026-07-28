from __future__ import annotations

import locale
import os
from typing import Final

SUPPORTED_LANGUAGES: Final = {"en", "ja"}

MESSAGES: Final[dict[str, dict[str, str]]] = {
    "en": {
        "app_help": "Safely archive media collections with site-specific adapters.",
        "doctor_title": "ArchiveLoom system check",
        "adapters_title": "Available adapters",
        "items_found": "Discovered {count} item(s).",
        "check_only": "Check-only mode: no files were written.",
        "confirm": "Start archiving these items?",
        "cancelled": "Cancelled.",
        "no_items": "No supported media items were found.",
        "summary": "Run summary",
        "all_ok": "All selected items completed successfully.",
        "partial": "The queue finished with failed or unsupported items.",
        "output_required": "Choose an output directory with --output.",
    },
    "ja": {
        "app_help": "サイト別アダプターでメディアコレクションを安全に保存します。",
        "doctor_title": "ArchiveLoom システム診断",
        "adapters_title": "利用可能なアダプター",
        "items_found": "{count}件の項目を検出しました。",
        "check_only": "確認専用モードです。ファイルは書き込んでいません。",
        "confirm": "選択した項目の保存を開始しますか?",
        "cancelled": "キャンセルしました。",
        "no_items": "対応するメディア項目が見つかりませんでした。",
        "summary": "実行結果",
        "all_ok": "選択した全項目が正常に完了しました。",
        "partial": "キューは終了しましたが、失敗または非対応項目があります。",
        "output_required": "--output で保存先を指定してください。",
    },
}


def detect_language(explicit: str | None = None) -> str:
    if explicit and explicit != "auto":
        return explicit if explicit in SUPPORTED_LANGUAGES else "en"
    for candidate in (os.getenv("ARCHIVELOOM_LANG"), locale.getlocale()[0]):
        if candidate and candidate.lower().startswith("ja"):
            return "ja"
    return "en"


def translate(key: str, lang: str, **values: object) -> str:
    template = MESSAGES.get(lang, MESSAGES["en"]).get(key, MESSAGES["en"].get(key, key))
    return template.format(**values)
