#!/bin/bash
# simchair_enable_zed_streams.sh
# Enable/disable ZED SDK native streaming on the EXISTING percept-stack cameras.
# Does NOT launch ZEDs, kill Argus, or stop WebUI.
#
# Usage:
#   bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --discover
#   bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --front-only
#   bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --all
#   bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --off
#
# Ports (Windows receiver expects these):
#   front 30000  left 30004  right 30008

set -e

CYCLONE_URI="file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml"
IGVC_SETUP="/home/dinosaur/IGVC/install/setup.bash"
HUMBLE_SETUP="/opt/ros/humble/setup.bash"

MODE="${1:---discover}"

ros_env() {
  # Don't fail the whole script if conda isn't present
  conda deactivate 2>/dev/null || true
  unset DISPLAY
  unset ROS_DOMAIN_ID
  # shellcheck disable=SC1090
  source "${HUMBLE_SETUP}"
  # shellcheck disable=SC1090
  source "${IGVC_SETUP}"
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export CYCLONEDDS_URI="${CYCLONE_URI}"
}

open_firewall() {
  echo "[fw] Opening UDP 30000,30004,30008 (ZED streams)..."
  for port in 30000 30004 30008; do
    sudo iptables -C INPUT -p udp --dport "${port}" -j ACCEPT 2>/dev/null \
      || sudo iptables -I INPUT -p udp --dport "${port}" -j ACCEPT
  done
  echo "[fw] Done (not persistent across reboot — re-run after reboot)."
}

discover() {
  echo "===== ZED nodes ====="
  ros2 node list | grep -i zed || echo "(no zed nodes — is percept-stack up?)"
  echo ""
  echo "===== enable_streaming services ====="
  ros2 service list | grep -i stream || echo "(none found — stream_server may be disabled in yaml)"
  echo ""
  echo "===== stream-related params (front) ====="
  ros2 param list /zed_front/zed_node 2>/dev/null | grep -i stream || echo "(no stream params on /zed_front/zed_node)"
}

call_enable() {
  local cam="$1"   # front|left|right
  local data="$2"  # true|false
  local svc="/zed_${cam}/zed_node/enable_streaming"
  if ! ros2 service list | grep -qx "${svc}"; then
    # some wrappers nest differently
    svc=$(ros2 service list | grep "zed_${cam}" | grep -i enable_streaming | head -1 || true)
  fi
  if [[ -z "${svc}" ]]; then
    echo "[err] No enable_streaming service for zed_${cam}"
    echo "      Percept/IGVC yaml likely needs stream_server block — see docs/H265_BRINGUP.md"
    return 1
  fi
  echo "[call] ros2 service call ${svc} std_srvs/srv/SetBool \"{data: ${data}}\""
  ros2 service call "${svc}" std_srvs/srv/SetBool "{data: ${data}}"
}

try_set_port() {
  local cam="$1"
  local port="$2"
  local node="/zed_${cam}/zed_node"
  # Best-effort; param names vary by zed_wrapper version
  for p in stream_server.port stream.port general.stream_port; do
    if ros2 param set "${node}" "${p}" "${port}" 2>/dev/null; then
      echo "[param] zed_${cam} ${p}=${port} (set ok)"
      break
    fi
  done
  # Verify — a lying "set ok" with stale 30000 causes Err Code 3 (port in use)
  local got
  got=$(ros2 param get "${node}" stream_server.port 2>/dev/null | awk '{print $NF}')
  if [[ "${got}" == "${port}" ]]; then
    echo "[param] zed_${cam} stream_server.port verified=${got}"
    return 0
  fi
  echo "[err] zed_${cam} still port=${got:-?} (want ${port})."
  echo "      Port is launch-time / read-only — edit percept yaml unique ports:"
  echo "      front 30000, left 30004, right 30008 — then restart that zed only (not Argus)."
  return 1
}

ros_env

case "${MODE}" in
  --discover|-d)
    discover
    ;;
  --front-only)
    open_firewall
    discover
    try_set_port front 30000
    call_enable front true
    echo ""
    echo "Front stream requested. On Windows:"
    echo "  python windows_zed_stream_receiver.py --front-only"
    echo "  (needs pyzed / ZED SDK)"
    ;;
  --all)
    open_firewall
    discover
    ports_ok=0
    try_set_port front 30000 || ports_ok=1
    try_set_port left 30004 || ports_ok=1
    try_set_port right 30008 || ports_ok=1
    if [[ "${ports_ok}" -ne 0 ]]; then
      echo ""
      echo "[abort] Unique stream ports not confirmed. Enabling left/right on 30000"
      echo "        while front owns 30000 → ZED Err Code 3. Fix yaml ports first."
      exit 1
    fi
    call_enable front true
    call_enable left true
    call_enable right true
    echo ""
    echo "All streams requested. On Windows:"
    echo "  python windows_zed_stream_receiver.py"
    echo "  or:  set VIDEO_MODE=zed && start_all.bat"
    ss -ulnp | grep -E '30000|30004|30008' || true
    ;;
  --off)
    call_enable front false || true
    call_enable left false || true
    call_enable right false || true
    echo "[ok] Streaming disable requested (percept/WebUI untouched)."
    ;;
  -h|--help)
    echo "Usage: $0 --discover | --front-only | --all | --off"
    exit 0
    ;;
  *)
    echo "Unknown mode: ${MODE}"
    echo "Usage: $0 --discover | --front-only | --all | --off"
    exit 1
    ;;
esac
