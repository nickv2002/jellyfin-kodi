"""Core repro for the shared-path removal bug (PR #1132, bug 2).

Real-world trigger: multiple movies in one flat directory share a single
Kodi `path` row. kodi/movies.delete() removes the movie and files rows,
then calls remove_path(), which used to delete the path row
unconditionally -- orphaning every other movie that still shares it and
making movieview return 0 rows for all of them. The fixture below mirrors
tests/fixtures/sample_library/movies-bug2/Shared Folder/ (3 real files
sharing one path) -- same library shape as the manual repro in that
directory's README, not a separate synthetic story.

Calls the REAL jellyfin_kodi.objects.kodi.kodi.Kodi.remove_path, not a
local re-implementation of the guard -- so this actually fails against an
unpatched checkout instead of always passing.
"""

import sqlite3
import unittest

from jellyfin_kodi.objects.kodi import queries as QU
from jellyfin_kodi.objects.kodi.kodi import Kodi

from tests.fixtures.sample_library import list_files

MOVIES = list_files("movies-bug2/Shared Folder")


def _make_db():
    """In-memory Kodi video DB, seeded from the real files in
    tests/fixtures/sample_library/movies-bug2/Shared Folder/."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE path (idPath INTEGER PRIMARY KEY, strPath TEXT);
        CREATE TABLE files (idFile INTEGER PRIMARY KEY, idPath INTEGER, strFileName TEXT);
        CREATE TABLE movie (idMovie INTEGER PRIMARY KEY, idFile INTEGER);
        -- mirrors Kodi's real movieview: only rows whose files->path join is
        -- intact appear here.
        CREATE VIEW movieview AS
            SELECT m.idMovie, f.idFile, p.idPath
            FROM   movie m
            JOIN   files f ON m.idFile = f.idFile
            JOIN   path  p ON f.idPath = p.idPath;
        """
    )
    conn.execute("INSERT INTO path VALUES (1, 'smb://video/')")
    for i, name in enumerate(MOVIES, start=1):
        conn.execute("INSERT INTO files VALUES (?, 1, ?)", (i, name))
        conn.execute("INSERT INTO movie VALUES (?, ?)", (i, i))
    conn.commit()
    return conn


class TestRemovePathGuard(unittest.TestCase):

    def setUp(self):
        self.conn = _make_db()

    def tearDown(self):
        self.conn.close()

    def test_removing_one_movie_preserves_the_shared_path(self):
        """The bug: deleting one of N shared-path movies (mirroring
        movies.py's delete(), then remove_path()) must not wipe the path
        record and orphan the other N-1."""
        cursor = self.conn.cursor()
        cursor.execute(QU.delete_movie, (1,))
        cursor.execute(QU.delete_file, (1,))

        kodi = object.__new__(Kodi)  # __init__ sets up artwork/people-cache state, irrelevant here
        kodi.cursor = cursor
        Kodi.remove_path(kodi, 1)

        path_exists = (
            self.conn.execute("SELECT count(*) FROM path WHERE idPath = 1").fetchone()[0]
            == 1
        )
        self.assertTrue(
            path_exists, "Path must survive while the other movies still reference it"
        )

        view_count = self.conn.execute("SELECT count(*) FROM movieview").fetchone()[0]
        self.assertEqual(
            view_count,
            len(MOVIES) - 1,
            "Only the deleted movie should disappear from the view",
        )


if __name__ == "__main__":
    unittest.main()
