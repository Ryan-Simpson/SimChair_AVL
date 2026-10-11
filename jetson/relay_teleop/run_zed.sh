#!/bin/bash
# run_zed.sh <camera_name> <serial> — one ZED X, same args as sensors.launch.py
#   zed_front 42569280 | zed_left 43779087 | zed_right 49910017
# Uses the team's config/<camera_name>.yaml unchanged (SVGA grab, downscale 2
# -> 480x300; front publishes 7.5 Hz, sides 15 Hz).
source "$(dirname "$0")/env.sh"
CFG="${IGVC_WS:-$HOME/IGVC}/install/avros_bringup/share/avros_bringup/config/$1.yaml"
exec ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zedx camera_name:="$1" \
  serial_number:="$2" publish_tf:=false publish_urdf:=false ros_params_override_path:="$CFG"
