#!/bin/bash
# run_viewer.sh — serve windows/multicam_viewer.html at http://<jetson>:8090/
# Only the viewer page is served (copied into its own directory), nothing else.
SRC="${VIEWER_HTML:-$(dirname "$0")/../../windows/multicam_viewer.html}"
WEB=/tmp/relay_teleop_web
mkdir -p "$WEB" && cp "$SRC" "$WEB/index.html" || { echo "viewer page not found: $SRC"; exit 1; }
exec /usr/bin/python3 -m http.server "${VIEWER_PORT:-8090}" --directory "$WEB"
