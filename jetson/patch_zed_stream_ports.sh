#!/bin/bash
# patch_zed_stream_ports.sh
# Adds unique stream_server.port to avros_bringup zed_*.yaml overrides.
# Run ON Jetson (does not restart cameras — you must relaunch ZEDs after).
#
#   bash ~/Documents/SimChair_Teleop/patch_zed_stream_ports.sh
#
set -euo pipefail

CFG="/home/dinosaur/IGVC/src/avros_bringup/config"
FRONT="${CFG}/zed_front.yaml"
LEFT="${CFG}/zed_left.yaml"
RIGHT="${CFG}/zed_right.yaml"

for f in "${FRONT}" "${LEFT}" "${RIGHT}"; do
  if [[ ! -f "${f}" ]]; then
    echo "[err] missing ${f}"
    exit 1
  fi
done

backup() {
  local f="$1"
  local bak="${f}.bak.simchair_$(date +%Y%m%d_%H%M%S)"
  cp -a "${f}" "${bak}"
  echo "[bak] ${bak}"
}

append_if_missing() {
  local f="$1"
  local port="$2"
  local bitrate="$3"

  if grep -qE '^[[:space:]]*stream_server:' "${f}"; then
    echo "[skip] ${f} already has stream_server — edit manually if port wrong"
    grep -A5 -E '^[[:space:]]*stream_server:' "${f}" || true
    return 0
  fi

  backup "${f}"
  cat >> "${f}" <<EOF

    # SimChair H.265 stream — unique UDP port per camera
    stream_server:
      port: ${port}
      bitrate: ${bitrate}
EOF
  echo "[ok] appended stream_server port=${port} bitrate=${bitrate} → ${f}"
}

append_if_missing "${FRONT}" 30000 6000
append_if_missing "${LEFT}"  30004 4000
append_if_missing "${RIGHT}" 30008 4000

echo ""
echo "Verify tails:"
tail -8 "${FRONT}"
echo "---"
tail -8 "${LEFT}"
echo "---"
tail -8 "${RIGHT}"

echo ""
echo "Next:"
echo "  cd /home/dinosaur/IGVC && colcon build --packages-select avros_bringup --symlink-install"
echo "  # then relaunch ZEDs the normal percept way (NOT orin_launch_all)"
echo "  ros2 param get /zed_left/zed_node stream_server.port   # want 30004"
echo "  ros2 param get /zed_right/zed_node stream_server.port  # want 30008"
