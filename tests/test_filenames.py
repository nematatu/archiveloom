from pathlib import Path

import pytest

from archiveloom.core.filenames import safe_child, safe_filename


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("match 01.mp4", "match 01.mp4"),
        ("../secret.mp4", "secret.mp4"),
        ("a/b\\c?.mp4", "c_.mp4"),
        ("CON", "_CON"),
        ("  . ", "media"),
    ],
)
def test_safe_filename(raw: str, expected: str) -> None:
    assert safe_filename(raw) == expected


def test_safe_child_remains_below_output(tmp_path: Path) -> None:
    child = safe_child(tmp_path, "../../escape.mp4")
    assert child.parent == tmp_path.resolve()
    assert child.name == "escape.mp4"
