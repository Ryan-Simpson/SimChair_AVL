#!/bin/bash
# run_xsens.sh — Xsens MTi-680G driver only (sensors.launch.py is not running).
# Publishes /imu/data at 100 Hz plus /filter/free_acceleration, /filter/euler, GNSS.
# Uses the avros xsens.yaml (enable_deviceConfig: false, so it never reflashes).
# actuator_node also reads /imu/data for heading-hold, but heading_hold_deadband
# is 0.0 on Marvin, so drive behaviour is unchanged.
source "$(dirname "$0")/env.sh"
exec ros2 run xsens_mti_ros2_driver xsens_mti_node --ros-args \
  --params-file "${IGVC_WS:-$HOME/IGVC}/install/avros_bringup/share/avros_bringup/config/xsens.yaml"
