#!/bin/bash
# orin_launch_all.sh
# Full sim-chair teleop stack (cameras + drive + IMU haptics).
#
# ZED cameras use serial numbers + publish_tf/urdf so positional tracking
# does not hang on "Waiting for valid static transformations".
# DISPLAY must be truly unset (not export DISPLAY=).
#
# Run: bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
#
# *** CONFLICT WARNING ***
# If carla-nav2-avl percept-stack / avros-webui already owns ZEDs (normal),
# DO NOT use this script — it kills ZED launches + restarts Argus.
# Use instead:
#   bash ~/Documents/SimChair_Teleop/simchair_attach.sh
#   bash ~/Documents/SimChair_Teleop/simchair_attach.sh --drive
#
# Drive (default): stops WebUI, starts orin_vehicle_controller --duty
# Cameras + WebUI only:  SIMCHAIR_DRIVE=0 bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
#
# Preflight kills leftover teleop / ZED watchdogs so dual stacks cannot fight.

set -e

if systemctl is-active --quiet percept-stack 2>/dev/null \
    || tmux -L percept has-session -t percept 2>/dev/null \
    || pgrep -f zed_camera.launch.py >/dev/null 2>&1; then
    if [[ "${FORCE_FULL_LAUNCH}" != "1" ]]; then
        echo "ERROR: percept / ZED stack looks active."
        echo "  orin_launch_all.sh would kill their cameras and break the car."
        echo "  Use:  bash ~/Documents/SimChair_Teleop/simchair_attach.sh"
        echo "  Or:   FORCE_FULL_LAUNCH=1 bash .../orin_launch_all.sh  (you mean it)"
        exit 1
    fi
    echo "WARNING: FORCE_FULL_LAUNCH=1 — killing existing ZED/percept pieces..."
fi

TELEOP_DIR="${TELEOP_DIR:-$HOME/Documents/SimChair_Teleop}"
IGVC_SETUP="/home/dinosaur/IGVC/install/setup.bash"
CYCLONE_URI="file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml"
SERIAL_PORT="${SERIAL_PORT:-/dev/ttyACM0}"
UDP_PORT="${UDP_PORT:-5006}"
# Default ON — overall launch = working sim-chair drive (open-loop duty).
SIMCHAIR_DRIVE="${SIMCHAIR_DRIVE:-1}"
# Vehicle mode that physically moves Sparks (velocity PID currently leaves LEDs purple).
VEHICLE_ARGS="${VEHICLE_ARGS:---duty}"
# Camera transport: udp (chunked JPEG, sharper defaults) or tcp (legacy verified path)
CAMERA_TRANSPORT="${CAMERA_TRANSPORT:-udp}"
WINDOWS_IP="${WINDOWS_IP:-100.91.25.107}"
# indoor = 960x540@30 q80 (less bitrate, fewer drops); default/hq = 720p
CAMERA_PROFILE="${CAMERA_PROFILE:-indoor}"
CAMERA_FPS="${CAMERA_FPS:-}"
CAMERA_QUALITY="${CAMERA_QUALITY:-}"
CAMERA_WIDTH="${CAMERA_WIDTH:-}"
CAMERA_HEIGHT="${CAMERA_HEIGHT:-}"

# Real unset — empty DISPLAY= breaks Argus/EGL on ZED X
unset DISPLAY
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="${CYCLONE_URI}"
export ROS_DOMAIN_ID=42

# shellcheck disable=SC1090
source "${IGVC_SETUP}"

echo "============================================"
echo " AVROS Teleoperation Stack"
echo " SIMCHAIR_DRIVE=${SIMCHAIR_DRIVE}  VEHICLE_ARGS=${VEHICLE_ARGS}"
echo " CAMERA_TRANSPORT=${CAMERA_TRANSPORT}  profile=${CAMERA_PROFILE}  → ${WINDOWS_IP}"
echo "============================================"

echo "[0/8] Preflight — clear leftover teleop / ZED contention..."
tmux kill-session -t teleop 2>/dev/null || true
sudo pkill -f orin_camera_sender 2>/dev/null || true
sudo pkill -f orin_vehicle_controller 2>/dev/null || true
sudo pkill -f imu_bridge.py 2>/dev/null || true
# Kill ANY zed_camera launches (IGVC watchdogs + prior teleop) before we start ours
sudo pkill -f zed_camera.launch.py 2>/dev/null || true
sudo pkill -f component_container_isolated 2>/dev/null || true
sleep 2
sudo systemctl restart nvargus-daemon 2>/dev/null || true
sleep 3
echo "      Cleared. Argus restarted."

echo "[1/8] Opening firewall ports..."
# Legacy TCP JPEG + new UDP JPEG (same port numbers)
for proto in tcp udp; do
    sudo iptables -I INPUT -p "${proto}" --dport 9001 -j ACCEPT
    sudo iptables -I INPUT -p "${proto}" --dport 9002 -j ACCEPT
    sudo iptables -I INPUT -p "${proto}" --dport 9003 -j ACCEPT
done
sudo iptables -I FORWARD -p tcp --dport 9001 -j ACCEPT
sudo iptables -I FORWARD -p udp --dport 9001 -j ACCEPT
echo "      Done."

echo "[2/8] Launching sensors (IMU, lidar, GPS)..."
tmux new-session -d -s teleop -n sensors \
    "bash -lc 'unset DISPLAY; source ${IGVC_SETUP}; \
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; \
    export CYCLONEDDS_URI=${CYCLONE_URI}; \
    export ROS_DOMAIN_ID=42; \
    ros2 launch avros_bringup sensors.launch.py; exec bash'"
echo "      Sensors launching in background..."
sleep 5

# serial, yaml basename (under avros_bringup/config), tmux window name
launch_zed() {
    local NAME=$1
    local SERIAL=$2
    local YAML=$3
    local WINDOW=$4
    local YAML_PATH="/home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/${YAML}"

    echo "      Launching ${NAME} (SN ${SERIAL})..."
    tmux new-window -t teleop -n "${WINDOW}" \
        "bash -lc 'unset DISPLAY; source ${IGVC_SETUP}; \
        export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; \
        export CYCLONEDDS_URI=${CYCLONE_URI}; \
        export ROS_DOMAIN_ID=42; \
        ros2 launch zed_wrapper zed_camera.launch.py \
          camera_model:=zedx \
          camera_name:=${NAME} \
          serial_number:=${SERIAL} \
          publish_tf:=true \
          publish_urdf:=true \
          ros_params_override_path:=${YAML_PATH}; \
        exec bash'"
    echo "      Waiting 25s for ${NAME} to initialize..."
    sleep 25
    echo "      ${NAME} ready."
}

echo "[3/8] Launching ZED front..."
launch_zed zed_front 42569280 zed_front.yaml zed_front

echo "[4/8] Launching ZED left..."
launch_zed zed_left 49910017 zed_left.yaml zed_left

echo "[5/8] Launching ZED right..."
launch_zed zed_right 43779087 zed_right.yaml zed_right

echo "[6/8] Launching camera sender (${CAMERA_TRANSPORT})..."
if [[ "${CAMERA_TRANSPORT}" == "udp" ]]; then
    CAM_ARGS="--windows-ip ${WINDOWS_IP} --profile ${CAMERA_PROFILE}"
    [[ -n "${CAMERA_FPS}" ]] && CAM_ARGS="${CAM_ARGS} --fps ${CAMERA_FPS}"
    [[ -n "${CAMERA_QUALITY}" ]] && CAM_ARGS="${CAM_ARGS} --quality ${CAMERA_QUALITY}"
    [[ -n "${CAMERA_WIDTH}" ]] && CAM_ARGS="${CAM_ARGS} --width ${CAMERA_WIDTH}"
    [[ -n "${CAMERA_HEIGHT}" ]] && CAM_ARGS="${CAM_ARGS} --height ${CAMERA_HEIGHT}"
    tmux new-window -t teleop -n cam_sender \
        "bash -lc 'unset DISPLAY; source ${IGVC_SETUP}; \
        export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; \
        export CYCLONEDDS_URI=${CYCLONE_URI}; \
        export ROS_DOMAIN_ID=42; \
        /usr/bin/python3 ${TELEOP_DIR}/orin_camera_sender_udp.py \
          ${CAM_ARGS}; exec bash'"
    echo "      UDP JPEG → ${WINDOWS_IP}  profile=${CAMERA_PROFILE} ${CAM_ARGS}"
    echo "      Windows: python windows_camera_receiver_udp.py"
else
    tmux new-window -t teleop -n cam_sender \
        "bash -lc 'unset DISPLAY; source ${IGVC_SETUP}; \
        export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; \
        export CYCLONEDDS_URI=${CYCLONE_URI}; \
        export ROS_DOMAIN_ID=42; \
        /usr/bin/python3 ${TELEOP_DIR}/orin_camera_sender.py; exec bash'"
    echo "      TCP JPEG sender running (legacy)."
    echo "      Windows: python windows_camera_receiver.py"
fi

if [[ "${SIMCHAIR_DRIVE}" == "1" ]]; then
    echo "[7/8] Sim-chair drive — stopping WebUI, starting vehicle (${VEHICLE_ARGS})..."
    sudo systemctl stop avros-webui 2>/dev/null || true
    sudo pkill -f actuator_node 2>/dev/null || true
    sudo pkill -f webui_node 2>/dev/null || true
    sleep 1

    if [[ ! -e "${SERIAL_PORT}" ]]; then
        echo "      WARNING: ${SERIAL_PORT} missing — vehicle window will error until Teensy is plugged in."
    fi

    if ss -ulnp 2>/dev/null | grep -q ":${UDP_PORT} "; then
        echo "      Clearing leftover UDP ${UDP_PORT} holders..."
        sudo pkill -f orin_vehicle_controller 2>/dev/null || true
        sudo pkill -f webui_node 2>/dev/null || true
        sleep 0.5
    fi

    # Quote VEHICLE_ARGS so --duty lands as a real argv (not word-split wrong in nested bash -lc)
    tmux new-window -t teleop -n vehicle \
        "bash -lc '/usr/bin/python3 ${TELEOP_DIR}/orin_vehicle_controller.py ${VEHICLE_ARGS}; exec bash'"
    echo "      Vehicle controller running (WebUI off, sole Teensy owner)."
    echo "      Check: sudo lsof ${SERIAL_PORT}"
    echo "      Expect drive_mode=duty and Sparks green/red under throttle."
else
    echo "[7/8] Skipping vehicle controller (SIMCHAIR_DRIVE=0 — WebUI keeps Teensy)."
    echo "      Sim chair later: bash ${TELEOP_DIR}/simchair_drive.sh"
    sudo systemctl start avros-webui 2>/dev/null || true
fi

echo "[8/8] Launching IMU haptic bridge..."
tmux new-window -t teleop -n imu_bridge \
    "bash -lc 'unset DISPLAY; source ${IGVC_SETUP}; \
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; \
    export CYCLONEDDS_URI=${CYCLONE_URI}; \
    export ROS_DOMAIN_ID=42; \
    /usr/bin/python3 ${TELEOP_DIR}/imu_bridge.py --windows-ip ${WINDOWS_IP}; exec bash'"
echo "      IMU bridge running."

echo ""
echo "============================================"
echo " Stack up."
if [[ "${SIMCHAIR_DRIVE}" == "1" ]]; then
    echo "   Drive = sim chair (orin_vehicle_controller ${VEHICLE_ARGS})"
    echo "   Windows: start_all.bat  (VIDEO_MODE=udp) + wheel mode 1"
    echo "   Restore WebUI later:"
    echo "     sudo pkill -f orin_vehicle_controller; sudo systemctl start avros-webui"
else
    echo "   Drive = Chrome WebUI (avros-webui)"
    echo "   Sim chair = bash ${TELEOP_DIR}/simchair_drive.sh"
fi
echo ""
echo " Monitor:"
echo "   tmux capture-pane -t teleop:cam_sender -p | tail -30"
echo "   tmux capture-pane -t teleop:vehicle -p | tail -30"
echo "   sudo lsof ${SERIAL_PORT}    # must be ONE owner only"
echo ""
echo " Windows cameras:"
echo "   cd \"C:\\Users\\VRX 226\\cursor-test\\windows\""
if [[ "${CAMERA_TRANSPORT}" == "udp" ]]; then
    echo "   python windows_camera_receiver_udp.py"
else
    echo "   python windows_camera_receiver.py"
fi
echo ""
echo " Kill stack: tmux kill-session -t teleop"
echo "============================================"
