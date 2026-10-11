#!/bin/bash
# run_bridge_dry.sh — DRY RUN: publishes to a test topic actuator_node does NOT
# subscribe to -> no motion. Use to check steering/throttle/mode from the chair:
#   ros2 topic echo /simchair_test/actuator_command
source "$(dirname "$0")/env.sh"
BRIDGE="${BRIDGE:-$(dirname "$0")/../orin_simchair_ros_bridge.py}"
exec nice -n 10 /usr/bin/python3 "$BRIDGE" --topic /simchair_test/actuator_command
