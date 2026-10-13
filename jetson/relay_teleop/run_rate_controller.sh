#!/bin/bash
# run_rate_controller.sh <base_total_bps> <front_bps>
# Adaptive bitrate: pings the sim chair over Tailscale and publishes
# /webrtc/bitrate_scale; every run_webrtc_cam.sh encoder runs at
# bitrate_bps * scale. If the link is still clogged at MIN_SCALE it
# pauses the "side" cameras (/webrtc/sides_enabled) until the front
# alone has headroom. Set MAX_SCALE / MIN_SCALE / START_SCALE to override.
source "$(dirname "$0")/env.sh"
source "${WEBRTC_WS:-$HOME/IGVC_webrtc}/install/setup.bash"
exec ros2 run avros_webrtc rate_controller --ros-args \
  -p target:=${VIEWER_IP:-100.91.25.107} -p base_total_bps:=${1:-1200000} -p front_bps:=${2:-500000} \
  -p max_scale:=${MAX_SCALE:-1.5} -p min_scale:=${MIN_SCALE:-0.25} \
  -p initial_scale:=${START_SCALE:-0.6}
