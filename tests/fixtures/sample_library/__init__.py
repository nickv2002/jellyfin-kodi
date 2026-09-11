"""Real filenames from the sample library, for tests to build fixture rows
from instead of re-typing literal strings that drift from tests/fixtures/sample_library/."""

from pathlib import Path

SAMPLE_LIBRARY = Path(__file__).parent


def list_files(subdir):
    """Filenames (no extension) of the mp4s under tests/fixtures/sample_library/<subdir>,
    alphabetically sorted so callers get a stable order."""
    return sorted(p.stem for p in (SAMPLE_LIBRARY / subdir).glob("*.mp4"))
