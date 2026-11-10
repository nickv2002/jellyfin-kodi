# Sample library for PR #1132

Two tiny, real (but non-playable-length) Movies libraries reproducing the
two bugs this PR fixes. Neither bug's logic depends on media type, so both
use Movies for simplicity. Regenerate with `generate.sh` (requires
`ffmpeg`).

```
movies-bug1/
  Trilogy Boxset/     <- one un-registered "view" subfolder
    Movie One.mp4 .. Movie Five.mp4    (5 items)
movies-bug2/
  Shared Folder/       <- one flat, shared-path folder
    Movie A.mp4 .. Movie C.mp4         (3 items)
```

These shapes match `tests/test_sort_worker_deletion.py` (5 items under one
subfolder id) and `tests/test_remove_path_guard.py` (3 items sharing one
path) exactly, so the automated tests and this manual repro are the same
story, not two different ones.

## Setup

1. Point one Jellyfin **Movies** library at `movies-bug1/`.
2. Point a second Jellyfin **Movies** library at `movies-bug2/`.
3. In the Kodi addon settings, enable `useDirectPaths`.
4. Sync both libraries to Kodi. You should see 5 + 3 movies.

## Bug 1: SortWorker parent-cascade wipe

`Trilogy Boxset` is a subfolder, not a library section, so jellyfin-kodi
never registers its id as a `view`. The bug is a **false positive**: the 5
movies inside are never actually deleted from Jellyfin, but the unpatched
code wipes them anyway.

1. In Jellyfin, rename or move the `Trilogy Boxset` folder itself (not its
   contents). This makes Jellyfin emit an `ItemsRemoved` event for the
   folder's own id -- the 5 movies inside are untouched and still exist.
2. **Unpatched**: all 5 movies vanish from Kodi anyway (the folder id isn't
   recognized, so the old code falls back to treating it as a parent id and
   cascades the removal to every child -- even though nothing was actually
   removed).
3. **Patched**: nothing is removed; the log shows "could not find media."
   This is correct -- the movies are still in Jellyfin.

## Bug 2: shared-path removal

All 3 movies live in one flat folder, so they share a single Kodi `path`
row.

1. In Jellyfin, remove **one** of the three movies.
2. **Unpatched**: all 3 disappear from Kodi's `movieview` (the shared
   `path` row is deleted, orphaning the other two untouched files).
3. **Patched**: only the removed movie disappears; the other two remain.
