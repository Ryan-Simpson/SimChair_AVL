#!/bin/bash
# run_rsp.sh — robot_state_publisher with the AVROS URDF (static TF only).
# Needed when sensors.launch.py is NOT running: the ZED wrappers block on
# "Waiting for valid static transformations..." without it.
# (Passing the URDF via -p on the command line aborts rcl arg parsing, so it
# goes through a params file.)
source "$(dirname "$0")/env.sh"
PARAMS=/tmp/relay_teleop_rsp_params.yaml
xacro "${IGVC_WS:-$HOME/IGVC}/install/avros_bringup/share/avros_bringup/urdf/avros.urdf.xacro" \
  | /usr/bin/python3 -c "import sys,yaml; yaml.safe_dump({'robot_state_publisher':{'ros__parameters':{'robot_description':sys.stdin.read()}}}, open('$PARAMS','w'))"
exec ros2 run robot_state_publisher robot_state_publisher --ros-args --params-file "$PARAMS"
