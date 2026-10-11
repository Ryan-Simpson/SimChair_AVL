#!/bin/bash
# run_actuator.sh — actuator_node only (no WebUI): /avros/actuator_command -> Teensy
# Commands motors as soon as a publisher sends non-estop ActuatorCommand.
source "$(dirname "$0")/env.sh"
exec ros2 launch avros_bringup actuator.launch.py
