"""Core repro for the SortWorker parent-cascade wipe (PR #1132, bug 1).

Real-world trigger: Jellyfin reports removal of a subfolder's own id
(Type=Folder, not in the view table) -- e.g. after a rename/move -- while
the movies inside it are untouched and still exist. The old code fell
through to get_media_by_parent_id, which returned every item under that id
and wiped them anyway, even though nothing was actually removed. The fixture below mirrors
tests/fixtures/sample_library/movies-bug1/Trilogy Boxset/ (5 real files in
one un-registered subfolder) -- same library shape as the manual repro in
that directory's README, not a separate synthetic story.

Runs the REAL jellyfin_kodi.library.SortWorker.run() end to end (only the
Database context manager is monkeypatched to an in-memory sqlite
connection, since it otherwise depends on xbmcvfs paths that don't exist in
a test environment) -- not a hand-copied reimplementation of the dispatch
if/else.
"""

import queue
import sqlite3
import unittest
from unittest.mock import patch

from jellyfin_kodi import library

from tests.fixtures.sample_library import list_files

SUBFOLDER_ID = "trilogy-boxset-folder-id"  # deliberately absent from `view`


class _FakeDatabaseContext:
    """Stand-in for jellyfin_kodi.database.Database("jellyfin") -- wraps a
    plain sqlite3 cursor instead of opening a real Kodi/xbmcvfs-backed file."""

    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def _make_conn():
    """In-memory DB with the real jellyfin.db schema (view + jellyfin tables),
    seeded from the real files in tests/fixtures/sample_library/movies-bug1/."""
    conn = sqlite3.connect(":memory:")
    # get_view() only checks whether a row exists, so this needs just the id.
    conn.execute("CREATE TABLE view (view_id TEXT PRIMARY KEY)")
    # Only the columns SortWorker's queries actually select -- see
    # get_media_by_id/get_media_by_parent_id in database/queries.py.
    conn.execute(
        """
        CREATE TABLE jellyfin (
            jellyfin_id        TEXT PRIMARY KEY,
            jellyfin_parent_id TEXT,
            jellyfin_type      TEXT,
            kodi_id            INTEGER,
            kodi_fileid        INTEGER
        )
    """
    )
    # SUBFOLDER_ID parents every movie below, but is itself not a `view` row --
    # the exact real-world shape of "Trilogy Boxset/" under the Movies library.
    # `view` stays empty: no test here needs a real one.
    for i, name in enumerate(list_files("movies-bug1/Trilogy Boxset"), start=1):
        conn.execute(
            "INSERT INTO jellyfin VALUES (?, ?, ?, ?, ?)",
            (name, SUBFOLDER_ID, "Movie", i, i),
        )
    conn.commit()
    return conn


class TestSortWorkerDeletion(unittest.TestCase):

    def setUp(self):
        self.conn = _make_conn()

    def tearDown(self):
        self.conn.close()

    def test_subfolder_removal_does_not_cascade_to_its_movies(self):
        """The bug: an un-registered subfolder id must not be treated as a
        parent whose children all get queued for removal."""
        in_queue = queue.Queue()
        in_queue.put(SUBFOLDER_ID)
        movie_queue = queue.Queue()
        worker = library.SortWorker(in_queue, {"Movie": movie_queue})

        with patch.object(
            library, "Database", return_value=_FakeDatabaseContext(self.conn.cursor())
        ):
            worker.run()

        self.assertTrue(
            movie_queue.empty(), "Subfolder id must not cascade -- it's not a view"
        )


if __name__ == "__main__":
    unittest.main()
