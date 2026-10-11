#!/bin/bash
# run_mediamtx.sh — stock MediaMTX (RTSP in :8554, WebRTC/WHEP out :8889)
cd "${MEDIAMTX_DIR:-$HOME/IGVC_webrtc/.mediamtx}" && exec ./mediamtx ./mediamtx.yml
