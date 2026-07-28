from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def redact_url(value: str) -> str:
    """Remove credentials, query values, and fragments from an HTTP(S) URL."""
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or parsed.hostname is None:
        return value
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        parsed_port = parsed.port
    except ValueError:
        parsed_port = None
    port = f":{parsed_port}" if parsed_port is not None else ""
    query = "redacted" if parsed.query else ""
    return urlunsplit((parsed.scheme.lower(), f"{host}{port}", parsed.path, query, ""))


def redact_text(value: str) -> str:
    """Redact URL secrets in an exception or tool diagnostic."""
    return URL_RE.sub(lambda match: redact_url(match.group(0)), value)
