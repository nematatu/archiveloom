from archiveloom.core.redaction import redact_text, redact_url


def test_redact_url_removes_userinfo_query_and_fragment() -> None:
    redacted = redact_url("HTTPS://user:pass@example.org:8443/path?q=secret#fragment")
    assert redacted == "https://example.org:8443/path?redacted"


def test_redact_text_preserves_non_urls_and_redacts_urls() -> None:
    text = redact_text("fetch https://example.org/a?token=secret failed")
    assert text == "fetch https://example.org/a?redacted failed"
    assert redact_url("not-a-url") == "not-a-url"
