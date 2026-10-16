#!/bin/bash
# simchair_launch_clean.sh — one-shot teleop attach that DOES NOT fight itself
#
# Starts:
#   1) ZED H.265 streams (ports 30000/30004/30008)
#   2) Wheel ROS bridge only (UDP → /avros/actuator_command)
#   3) Optional IMU → Windows
#
# Does NOT start JPEG cam_sender (that + H.265 saturated the link).
# Does NOT kill percept-stack / Argus / WebUI.
#
# Usage:
#   bash ~/Documents/SimChair_Teleop/simchair_launch_clean.sh
#   bash ~/Documents/SimChair_Teleop/simchair_launch_clean.sh --no-imu
#   bash ~/Documents/SimChair_Teleop/simchair_launch_clean.sh --front-only
#
# Stop:
#   tmux kill-session -t simchair
#   bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --off
#
set -euo pipefail

TELEOP_DIR="${TELEOP_DIR:-$HOME/Documents/SimChair_Teleop}"
IGVC_SETUP="/home/dinosaur/IGVC/install/setup.bash"
HUMBLE_SETUP="/opt/ros/humble/setup.bash"
CYCLONE_URI="file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml"
WINDOWS_IP="${WINDOWS_IP:-100.91.25.107}"
WITH_IMU=1
STREAM_MODE="--all"

for arg in "$@"; do
  case "$arg" in
    --no-imu) WITH_IMU=0 ;;
    --front-only) STREAM_MODE="--front-only" ;;
    -h|--help)
      echo "Usage: $0 [--front-only] [--no-imu]"
      exit 0
      ;;
  esac
done

echo "============================================"
echo " SimChair CLEAN launch (H.265 + wheel, no JPEG)"
echo " WINDOWS_IP=${WINDOWS_IP}  streams=${STREAM_MODE}"
echo "============================================"

if ! systemctl is-active --quiet percept-stack; then
  echo "WARNING: percept-stack not active — start it first:"
  echo "  sudo systemctl start percept-stack"
fi

# Kill prior simchair bits only
tmux kill-session -t simchair 2>/dev/null || true
pkill -f orin_camera_sender_udp.py 2>/dev/null || true
pkill -f orin_camera_sender.py 2>/dev/null || true
pkill -f orin_simchair_ros_bridge.py 2>/dev/null || true
pkill -f "${TELEOP_DIR}/imu_bridge.py" 2>/dev/null || true
sleep 1

# H.265 streams on existing ZED nodes
bash "${TELEOP_DIR}/simchair_enable_zed_streams.sh" ${STREAM_MODE}
echo ""
ss -ulnp | grep -E '30000|30004|30008' || echo "WARNING: no stream ports listening yet"

ENV_INNER="conda deactivate 2>/dev/null; true; \
unset DISPLAY; \
unset ROS_DOMAIN_ID; \
source ${HUMBLE_SETUP}; \
source ${IGVC_SETUP}; \
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; \
export CYCLONEDDS_URI=${CYCLONE_URI}; \
export ROS_DOMAIN_ID=0"

# Wheel bridge (no JPEG)
tmux new-session -d -s simchair -n ros_drive \
  "bash -lc '${ENV_INNER}; \
  /usr/bin/python3 ${TELEOP_DIR}/orin_simchair_ros_bridge.py; \
  exec bash'"
echo "[ok] ros_drive bridge (close Chrome stick — one commander)"

if [[ "${WITH_IMU}" == "1" ]]; then
  tmux new-window -t simchair -n imu_bridge \
    "bash -lc '${ENV_INNER}; \
    /usr/bin/python3 ${TELEOP_DIR}/imu_bridge.py --windows-ip ${WINDOWS_IP}; \
    exec bash'"
  echo "[ok] imu_bridge → ${WINDOWS_IP}"
fi

echo ""
echo "Verify:"
echo "  tmux ls"
echo "  pgrep -af orin_simchair_ros_bridge"
echo "  ss -ulnp | grep -E '30000|30004|30008'"
echo ""
echo "Windows (Command Prompt):"
echo "  cd /d \"C:\\Users\\VRX 226\\simchair_teleop\\windows\""
echo "  set VIDEO_MODE=zed"
echo "  start_all.bat"
echo "  → banner must say VIDEO_MODE=zed ; wheel mode 1 = drive"
echo ""
echo "Stop: tmux kill-session -t simchair"
echo "      bash ${TELEOP_DIR}/simchair_enable_zed_streams.sh --off"
