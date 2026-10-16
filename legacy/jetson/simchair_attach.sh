#!/bin/bash
# simchair_attach.sh — attach sim-chair to the EXISTING car stack
#
# Perception / WebUI (carla-nav2-avl percept-stack + avros-webui) owns:
#   ZEDs, sensors, Argus, day-to-day Teensy (actuator_node)
#
# This script does NOT:
#   - kill zed_camera / Argus / percept tmux
#   - relaunch sensors or ZEDs
#   - touch /home/dinosaur/IGVC sources
#
# This script ONLY starts:
#   - UDP JPEG camera sender (subscribes to existing ZED topics)
#   - optional IMU → Windows bridge
#   - optional drive:
#       --ros-drive  PREFERRED: UDP → /avros/actuator_command (WebUI stays up)
#       --drive      LEGACY: steal Teensy via simchair_drive.sh (stops WebUI)
#
# Usage:
#   bash ~/Documents/SimChair_Teleop/simchair_attach.sh
#   bash ~/Documents/SimChair_Teleop/simchair_attach.sh --ros-drive
#   bash ~/Documents/SimChair_Teleop/simchair_attach.sh --ros-drive --no-cam   # H.265 / ZED streams only
#   bash ~/Documents/SimChair_Teleop/simchair_attach.sh --drive
#
# Kill ONLY our attach session (leaves perception alone):
#   tmux kill-session -t simchair
#   sudo pkill -f orin_simchair_ros_bridge
#   # only if --drive was used:
#   sudo pkill -f orin_vehicle_controller
#   sudo systemctl restart avros-webui

set -e

TELEOP_DIR="${TELEOP_DIR:-$HOME/Documents/SimChair_Teleop}"
IGVC_SETUP="/home/dinosaur/IGVC/install/setup.bash"
HUMBLE_SETUP="/opt/ros/humble/setup.bash"
CYCLONE_URI="file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml"
WINDOWS_IP="${WINDOWS_IP:-100.91.25.107}"
CAMERA_PROFILE="${CAMERA_PROFILE:-default}"
# Car stack is ALWAYS domain 0. Ignore a stale ROS_DOMAIN_ID=42 in the shell
# unless the user explicitly sets SIMCHAIR_ROS_DOMAIN.
ROS_DOMAIN_ID="${SIMCHAIR_ROS_DOMAIN:-0}"
# DEFAULT compressed: safe with percept-stack (raw 720p×3 re-encode crashed Orin 2026-08-24).
# Sharper opt-in (can overload Jetson): CAMERA_SOURCE=raw CAMERA_PROFILE=indoor|default
CAMERA_SOURCE="${CAMERA_SOURCE:-compressed}"
WITH_DRIVE=0
WITH_ROS_DRIVE=0
WITH_IMU="${WITH_IMU:-1}"
WITH_CAM=1

for arg in "$@"; do
    case "$arg" in
        --drive) WITH_DRIVE=1 ;;
        --ros-drive) WITH_ROS_DRIVE=1 ;;
        --no-cam|--no-camera|--zed-only) WITH_CAM=0 ;;
        --no-imu) WITH_IMU=0 ;;
        -h|--help)
            echo "Usage: $0 [--ros-drive|--drive] [--no-cam] [--no-imu]"
            echo "  Attaches to existing ZEDs (percept-stack)."
            echo "  --ros-drive  PREFERRED: wheel → ActuatorCommand (keeps WebUI/Teensy owner)"
            echo "  --drive      LEGACY: borrow Teensy (stops WebUI) via duty serial"
            echo "  --no-cam     skip JPEG UDP sender (use ZED H.265 streams instead)"
            exit 0
            ;;
    esac
done

if [[ "${WITH_DRIVE}" == "1" && "${WITH_ROS_DRIVE}" == "1" ]]; then
    echo "ERROR: use only one of --ros-drive or --drive"
    exit 1
fi

if [[ ! -f "${IGVC_SETUP}" ]]; then
    echo "ERROR: missing ${IGVC_SETUP}"
    exit 1
fi

echo "============================================"
echo " SimChair ATTACH (do not smash percept-stack)"
echo " ROS_DOMAIN_ID=${ROS_DOMAIN_ID}  profile=${CAMERA_PROFILE}"
echo " WINDOWS_IP=${WINDOWS_IP}  ros_drive=${WITH_ROS_DRIVE} serial_drive=${WITH_DRIVE}"
echo "============================================"

if ! pgrep -f zed_camera.launch.py >/dev/null 2>&1 \
    && ! pgrep -f component_container_isolated >/dev/null 2>&1; then
    echo "WARNING: no ZED processes found."
    echo "  Start car stack first: sudo systemctl start percept-stack"
    echo "  Continuing anyway (sender will wait for topics)..."
fi

for proto in tcp udp; do
    sudo iptables -C INPUT -p "${proto}" --dport 9001 -j ACCEPT 2>/dev/null \
        || sudo iptables -I INPUT -p "${proto}" --dport 9001 -j ACCEPT
    sudo iptables -C INPUT -p "${proto}" --dport 9002 -j ACCEPT 2>/dev/null \
        || sudo iptables -I INPUT -p "${proto}" --dport 9002 -j ACCEPT
    sudo iptables -C INPUT -p "${proto}" --dport 9003 -j ACCEPT 2>/dev/null \
        || sudo iptables -I INPUT -p "${proto}" --dport 9003 -j ACCEPT
done

tmux kill-session -t simchair 2>/dev/null || true
pkill -f orin_camera_sender_udp.py 2>/dev/null || true
pkill -f orin_camera_sender.py 2>/dev/null || true
pkill -f orin_simchair_ros_bridge.py 2>/dev/null || true
pkill -f "${TELEOP_DIR}/imu_bridge.py" 2>/dev/null || true
sleep 1

# conda OFF + system python — required for DDS discovery with WebUI
ros_env() {
    echo "conda deactivate 2>/dev/null; true; \
unset DISPLAY; \
source ${HUMBLE_SETUP}; \
source ${IGVC_SETUP}; \
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; \
export CYCLONEDDS_URI=${CYCLONE_URI}; \
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
}

ENV_CMD="$(ros_env)"

if [[ "${WITH_CAM}" == "1" ]]; then
    SOURCE_FLAG="--prefer-raw"
    if [[ "${CAMERA_SOURCE}" == "compressed" ]]; then
        SOURCE_FLAG="--prefer-compressed"
    fi

    tmux new-session -d -s simchair -n cam_sender \
        "bash -lc '${ENV_CMD}; \
        /usr/bin/python3 ${TELEOP_DIR}/orin_camera_sender_udp.py \
          --windows-ip ${WINDOWS_IP} \
          --profile ${CAMERA_PROFILE} \
          ${SOURCE_FLAG}; \
        exec bash'"
    echo "[ok] cam_sender → ${WINDOWS_IP}  profile=${CAMERA_PROFILE} source=${CAMERA_SOURCE}"
    echo " Windows JPEG: python windows_camera_receiver_udp.py"
else
    tmux new-session -d -s simchair -n drive_only "bash -lc 'echo simchair (no JPEG cam); exec bash'"
    echo "[ok] skipped JPEG cam_sender — use ZED H.265:"
    echo "  bash ${TELEOP_DIR}/simchair_enable_zed_streams.sh --all"
    echo "  Windows: py -3.8 windows_zed_stream_receiver.py --native-size"
fi

if [[ "${WITH_IMU}" == "1" ]]; then
    tmux new-window -t simchair -n imu_bridge \
        "bash -lc '${ENV_CMD}; \
        /usr/bin/python3 ${TELEOP_DIR}/imu_bridge.py --windows-ip ${WINDOWS_IP}; \
        exec bash'"
    echo "[ok] imu_bridge"
fi

echo ""
echo " Monitor:      tmux ls; tmux capture-pane -t simchair:ros_drive -p | tail -20"
echo " Kill attach:   tmux kill-session -t simchair"
echo ""

if [[ "${WITH_ROS_DRIVE}" == "1" ]]; then
    echo "[ok] ROS drive bridge — WebUI service STAYS UP; actuator_node keeps Teensy"
    echo "  Close Chrome joystick while using the wheel (one commander)."
    tmux new-window -t simchair -n ros_drive \
        "bash -lc '${ENV_CMD}; \
        /usr/bin/python3 ${TELEOP_DIR}/orin_simchair_ros_bridge.py; \
        exec bash'"
    echo "  Windows: .\\simchair_sender_dbox.exe   mode 1 = drive, 0 = park"
    echo "  Check:   ros2 topic echo /avros/actuator_command --once"
    echo "  Stop:    tmux kill-session -t simchair   # or pkill -f orin_simchair_ros_bridge"
elif [[ "${WITH_DRIVE}" == "1" ]]; then
    echo "LEGACY serial drive — stopping WebUI / borrowing Teensy..."
    bash "${TELEOP_DIR}/simchair_drive.sh"
else
    echo "Drive = Chrome WebUI (Teensy untouched)."
    echo "Preferred wheel path:"
    echo "  bash ${TELEOP_DIR}/simchair_attach.sh --ros-drive"
fi
