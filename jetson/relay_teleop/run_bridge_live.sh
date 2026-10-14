#!/bin/bash
# run_bridge_live.sh — sim chair UDP :5006 -> /avros/actuator_command  (MARVIN MOVES)
# Watchdog e-stop OFF (--watchdog-ms 1e9): a manual remote e-stop operator is present.
# actuator_node's own 0.5 s cmd timeout still stops the motors if commands stop.
# Bridge starts latched: put the sender in park (mode 0) once to arm.
# DRIVE_MODE=gear (paddles: 1 = diff, 2 = ackermann, 0/3 = off), ackermann, or diff (default here).
# BRIDGE_ARGS passes extra flags, e.g. BRIDGE_ARGS="--min-radius 2 --max-speed 0.8".
source "$(dirname "$0")/env.sh"
BRIDGE="${BRIDGE:-$(dirname "$0")/../orin_simchair_ros_bridge.py}"
exec nice -n 10 /usr/bin/python3 "$BRIDGE" --topic /avros/actuator_command --watchdog-ms "${WATCHDOG_MS:-1e9}" \
  --drive-mode "${DRIVE_MODE:-diff}" $BRIDGE_ARGS
