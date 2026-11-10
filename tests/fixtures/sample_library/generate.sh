#!/bin/sh
# Regenerates the tiny sample library in this directory. Each file is a
# real, valid, 1-second solid-color MP4 (a few KB) -- not meant to be
# watched, just enough for Jellyfin's scanner to accept it without error.
#
# Shapes mirror the two bugs fixed by PR #1132 (both are Movies libraries --
# neither bug's logic depends on the media type):
#   movies-bug1/Trilogy Boxset/  -- 5 movies in one un-registered subfolder
#   movies-bug2/Shared Folder/   -- 3 movies flat in one shared-path folder
set -eu
cd "$(dirname "$0")"

make_clip() {
  ffmpeg -y -loglevel error -f lavfi -i "color=c=$2:s=64x64:d=1" \
    -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$1"
}

mkdir -p "movies-bug1/Trilogy Boxset"
make_clip "movies-bug1/Trilogy Boxset/Movie One.mp4" red
make_clip "movies-bug1/Trilogy Boxset/Movie Two.mp4" green
make_clip "movies-bug1/Trilogy Boxset/Movie Three.mp4" blue
make_clip "movies-bug1/Trilogy Boxset/Movie Four.mp4" yellow
make_clip "movies-bug1/Trilogy Boxset/Movie Five.mp4" purple

mkdir -p "movies-bug2/Shared Folder"
make_clip "movies-bug2/Shared Folder/Movie A.mp4" cyan
make_clip "movies-bug2/Shared Folder/Movie B.mp4" magenta
make_clip "movies-bug2/Shared Folder/Movie C.mp4" orange

echo "Generated $(find movies-bug1 movies-bug2 -name '*.mp4' | wc -l) files ($(du -sh . | cut -f1) total)"
