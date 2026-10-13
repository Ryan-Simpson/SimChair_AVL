#!/bin/bash
# run_webrtc_cam.sh <camera_name> <frame_rate> <bitrate_bps> [side]
# "side": slows to a still frame every 2 s when run_rate_controller.sh
# pauses the side cameras (link too slow for all three).
# avros_webrtc node (NVENC H.264, CBR) for one camera -> MediaMTX path <camera_name>
# frame_rate must equal that camera's pub_frame_rate; IDR every ~1 s.
source "$(dirname "$0")/env.sh"
source "${WEBRTC_WS:-$HOME/IGVC_webrtc}/install/setup.bash"
exec nice -n 19 ros2 run avros_webrtc webrtc_node --ros-args -r __node:=webrtc_$1 \
  -p image_topic:=/$1/zed_node/rgb/color/rect/image -p rtsp_url:=rtsp://127.0.0.1:8554/$1 \
  -p frame_rate:=$2 -p bitrate_bps:=$3 -p idr_interval:=${2%.*} \
  -p pausable:=$([[ "$4" == side ]] && echo true || echo false)
